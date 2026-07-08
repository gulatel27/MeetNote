import { useEffect, useState } from "react";

import { getMeeting, markdownDownloadUrl, processMeeting, updateMeetingReport } from "../api/client.js";
import MarkdownReport from "../components/MarkdownReport.jsx";
import StatusBadge, { StatusSteps } from "../components/StatusBadge.jsx";

export default function MeetingResultPage({ meetingId }) {
  const [meeting, setMeeting] = useState(null);
  const [draftMarkdown, setDraftMarkdown] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadMeeting = async () => {
    setIsLoading(true);
    setError("");
    try {
      const loadedMeeting = await getMeeting(meetingId);
      setMeeting(loadedMeeting);
      setDraftMarkdown(loadedMeeting.report_markdown || "");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMeeting();
  }, [meetingId]);

  const retryProcess = async () => {
    setIsProcessing(true);
    setMessage("");
    setError("");
    try {
      await processMeeting(meetingId);
      await loadMeeting();
      setIsEditing(false);
      setMessage("보고서를 다시 생성했습니다.");
    } catch (err) {
      setError(err.message);
      await loadMeeting();
    } finally {
      setIsProcessing(false);
    }
  };

  const startEdit = () => {
    setDraftMarkdown(meeting.report_markdown || "");
    setIsEditing(true);
    setMessage("");
    setError("");
  };

  const cancelEdit = () => {
    setDraftMarkdown(meeting.report_markdown || "");
    setIsEditing(false);
    setMessage("");
    setError("");
  };

  const saveReport = async () => {
    setIsSaving(true);
    setMessage("");
    setError("");
    try {
      const updatedMeeting = await updateMeetingReport(meetingId, draftMarkdown);
      setMeeting(updatedMeeting);
      setDraftMarkdown(updatedMeeting.report_markdown || "");
      setIsEditing(false);
      setMessage("수정한 보고서를 저장했습니다.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const copyReport = async () => {
    setMessage("");
    setError("");
    try {
      await navigator.clipboard.writeText(meeting.report_markdown || "");
      setMessage("보고서 내용을 클립보드에 복사했습니다.");
    } catch {
      setError("브라우저에서 클립보드 복사를 허용하지 않았습니다. 보고서 본문을 직접 선택해 복사하세요.");
    }
  };

  if (isLoading) {
    return <p className="notice">요약 정보를 불러오는 중...</p>;
  }

  if (error && !meeting) {
    return <p className="error">{error}</p>;
  }

  const shownMarkdown = isEditing ? draftMarkdown : meeting.report_markdown;
  const isSeminar = meeting.report_type === "seminar";

  return (
    <section className="result-layout">
      <div className="result-header">
        <div>
          <h1>{meeting.title}</h1>
          <p className="meta">
            {meeting.meeting_date} · {isSeminar ? "세미나 요약" : meeting.meeting_type} ·{" "}
            {meeting.project_name || "프로젝트/주제 미정"}
          </p>
        </div>
        <StatusBadge status={meeting.status} />
      </div>

      <StatusSteps status={meeting.status} />

      {meeting.error_message ? <p className="error">처리 오류: {meeting.error_message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="notice">{message}</p> : null}

      <div className="actions">
        <button disabled={!meeting.report_markdown || isEditing} onClick={copyReport} type="button">
          <span aria-hidden="true">⧉</span>
          보고서 복사
        </button>
        <a
          aria-disabled={!meeting.report_markdown || isEditing}
          className={`button-link ${meeting.report_markdown && !isEditing ? "" : "is-disabled"}`}
          href={meeting.report_markdown && !isEditing ? markdownDownloadUrl(meeting.id) : "#"}
        >
          <span aria-hidden="true">↓</span>
          Markdown 다운로드
        </a>

        {isEditing ? (
          <>
            <button disabled={isSaving} onClick={saveReport} type="button">
              <span aria-hidden="true">✓</span>
              {isSaving ? "저장 중..." : "수정 저장"}
            </button>
            <button className="secondary-button" disabled={isSaving} onClick={cancelEdit} type="button">
              취소
            </button>
          </>
        ) : (
          <>
            <button disabled={!meeting.report_markdown} onClick={startEdit} type="button">
              <span aria-hidden="true">✎</span>
              보고서 편집
            </button>
            <button disabled={isProcessing} onClick={retryProcess} type="button">
              <span aria-hidden="true">↻</span>
              {isProcessing ? "처리 중..." : meeting.status === "completed" ? "보고서 재생성" : "분석 실행"}
            </button>
          </>
        )}
      </div>

      {isEditing ? (
        <p className="edit-hint">오탈자나 표현을 수정한 뒤 저장하면 다운로드되는 Markdown에도 반영됩니다.</p>
      ) : null}

      <div className="content-grid">
        <article className="report-card">
          <MarkdownReport isEditing={isEditing} markdown={shownMarkdown} onChange={setDraftMarkdown} />
        </article>

        <article className="transcript-card">
          <h2>{isSeminar ? "전체 녹음 Transcript" : "Transcript"}</h2>
          <pre className="transcript-view">{meeting.transcript || "변환된 transcript가 없습니다."}</pre>
        </article>
      </div>
    </section>
  );
}
