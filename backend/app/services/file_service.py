import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings


ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
CHUNK_SIZE = 1024 * 1024


def ensure_storage_dirs() -> None:
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.image_path.mkdir(parents=True, exist_ok=True)
    settings.report_path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    raw_name = Path(filename or "audio").name.replace("\x00", "")
    stem = Path(raw_name).stem.strip() or "audio"
    suffix = Path(raw_name).suffix.lower()
    safe_stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._")
    if not safe_stem:
        safe_stem = "audio"
    return f"{safe_stem}{suffix}"


def validate_audio_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 파일 형식입니다. 허용 확장자: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return suffix


def validate_image_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 이미지 형식입니다. 허용 확장자: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
        )
    return suffix


def safe_child_path(base_dir: Path, filename: str) -> Path:
    base = base_dir.resolve()
    target = (base / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="허용되지 않은 파일 경로입니다.",
        ) from exc
    return target


async def save_audio_upload(upload_file: UploadFile) -> Path:
    settings = get_settings()
    ensure_storage_dirs()

    safe_name = sanitize_filename(upload_file.filename or "audio")
    validate_audio_extension(safe_name)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    destination = safe_child_path(settings.upload_path, stored_name)

    total_size = 0
    try:
        with destination.open("wb") as out_file:
            while True:
                chunk = await upload_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > settings.max_upload_bytes:
                    out_file.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="업로드 가능한 최대 파일 크기 500MB를 초과했습니다.",
                    )
                out_file.write(chunk)
    finally:
        await upload_file.close()

    if total_size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 파일은 업로드할 수 없습니다.",
        )

    return destination


async def save_image_uploads(upload_files: list[UploadFile] | None) -> list[Path]:
    settings = get_settings()
    ensure_storage_dirs()
    if not upload_files:
        return []

    destinations: list[Path] = []
    try:
        for upload_file in upload_files:
            if not upload_file.filename:
                continue
            safe_name = sanitize_filename(upload_file.filename)
            validate_image_extension(safe_name)
            stored_name = f"{uuid.uuid4().hex}_{safe_name}"
            destination = safe_child_path(settings.image_path, stored_name)

            total_size = 0
            try:
                with destination.open("wb") as out_file:
                    while True:
                        chunk = await upload_file.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        total_size += len(chunk)
                        if total_size > settings.max_image_bytes:
                            out_file.close()
                            destination.unlink(missing_ok=True)
                            raise HTTPException(
                                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail="업로드 가능한 이미지 파일 크기를 초과했습니다. 이미지당 최대 20MB입니다.",
                            )
                        out_file.write(chunk)
            finally:
                await upload_file.close()

            if total_size == 0:
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="빈 이미지 파일은 업로드할 수 없습니다.",
                )
            destinations.append(destination)
    except Exception:
        for destination in destinations:
            destination.unlink(missing_ok=True)
        raise

    return destinations


def save_report_markdown(meeting_id: int, report_markdown: str) -> Path:
    settings = get_settings()
    ensure_storage_dirs()
    filename = f"meeting_{meeting_id}.md"
    destination = safe_child_path(settings.report_path, filename)
    destination.write_text(report_markdown, encoding="utf-8")
    return destination
