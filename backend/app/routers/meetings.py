import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Meeting, MeetingStatus
from app.schemas import MeetingDetail, MeetingListItem, ProcessResponse, UploadResponse
from app.services.file_service import sanitize_filename, save_audio_upload, save_report_markdown
from app.services.report_service import generate_report_markdown
from app.services.stt_service import transcribe_audio
from app.services.summary_service import generate_meeting_summary


router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_meeting(
    audio_file: UploadFile = File(...),
    title: str = Form(...),
    meeting_date: str = Form(...),
    participants: str = Form(...),
    project_name: str = Form(""),
    meeting_type: str = Form(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    audio_path = await save_audio_upload(audio_file)
    meeting = Meeting(
        title=title.strip(),
        meeting_date=meeting_date.strip(),
        participants=participants.strip(),
        project_name=project_name.strip() or None,
        meeting_type=meeting_type.strip(),
        audio_file_path=str(audio_path),
        status=MeetingStatus.UPLOADED.value,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return UploadResponse(meeting_id=meeting.id, status=meeting.status)


@router.post("/{meeting_id}/process", response_model=ProcessResponse)
def process_meeting(meeting_id: int, db: Session = Depends(get_db)) -> ProcessResponse:
    meeting = get_meeting_or_404(db, meeting_id)

    try:
        update_status(db, meeting, MeetingStatus.STT_PROCESSING)
        transcript = transcribe_audio(meeting.audio_file_path)
        meeting.transcript = transcript
        db.commit()
        db.refresh(meeting)

        update_status(db, meeting, MeetingStatus.SUMMARIZING)
        summary = generate_meeting_summary(meeting, transcript)
        report = generate_report_markdown(meeting, summary, transcript)

        meeting.summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
        meeting.report_markdown = report
        meeting.error_message = None
        meeting.status = MeetingStatus.COMPLETED.value
        save_report_markdown(meeting.id, report)
        db.commit()
        db.refresh(meeting)

        return ProcessResponse(meeting_id=meeting.id, status=meeting.status, report=report)
    except Exception as exc:
        meeting.status = MeetingStatus.FAILED.value
        meeting.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회의 처리 중 오류가 발생했습니다: {exc}",
        ) from exc


@router.get("", response_model=list[MeetingListItem])
def list_meetings(db: Session = Depends(get_db)) -> list[Meeting]:
    return db.query(Meeting).order_by(Meeting.created_at.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> MeetingDetail:
    meeting = get_meeting_or_404(db, meeting_id)
    return serialize_meeting_detail(meeting)


@router.get("/{meeting_id}/download/markdown")
def download_markdown(meeting_id: int, db: Session = Depends(get_db)) -> Response:
    meeting = get_meeting_or_404(db, meeting_id)
    if not meeting.report_markdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="생성된 Markdown 보고서가 없습니다.",
        )

    filename = sanitize_filename(f"meeting_{meeting.id}_{meeting.title}.md")
    return Response(
        content=meeting.report_markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{meeting_id}/download/docx")
def download_docx(meeting_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="DOCX 다운로드는 MVP 이후 TODO입니다. 현재는 Markdown 다운로드를 사용하세요.",
    )


def get_meeting_or_404(db: Session, meeting_id: int) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"meeting_id={meeting_id} 회의를 찾을 수 없습니다.",
        )
    return meeting


def update_status(db: Session, meeting: Meeting, status_value: MeetingStatus) -> None:
    meeting.status = status_value.value
    meeting.error_message = None
    db.commit()
    db.refresh(meeting)


def serialize_meeting_detail(meeting: Meeting) -> MeetingDetail:
    summary = None
    if meeting.summary_json:
        try:
            summary = json.loads(meeting.summary_json)
        except json.JSONDecodeError:
            summary = {"raw": meeting.summary_json}

    return MeetingDetail(
        id=meeting.id,
        title=meeting.title,
        meeting_date=meeting.meeting_date,
        participants=meeting.participants,
        project_name=meeting.project_name,
        meeting_type=meeting.meeting_type,
        status=meeting.status,
        error_message=meeting.error_message,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        transcript=meeting.transcript,
        summary_json=summary,
        report_markdown=meeting.report_markdown,
    )
