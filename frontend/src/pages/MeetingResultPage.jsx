import { useEffect, useState } from "react";

import { getMeeting, markdownDownloadUrl, processMeeting } from "../api/client.js";
import StatusBadge, { StatusSteps } from "../components/StatusBadge.jsx";

export default function MeetingResultPage({ meetingId }) {
  const [meeting, setMeeting] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState("");

  const loadMeeting = async () => {
    setIsLoading(true);
    setError("");
    try {
      setMeeting(await getMeeting(meetingId));
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
    setError("");
    try {
      await processMeeting(meetingId);
      await loadMeeting();
    } catch (err) {
      setError(err.message);
      await loadMeeting();
    } finally {
      setIsProcessing(false);
    }
  };

  if (isLoading) {
    return <p className="notice">회의 정보를 불러오는 중...</p>;
  }

  if (error && !meeting) {
    return <p className="error">{error}</p>;
  }

  return (
    <section className="result-layout">
      <div className="result-header">
        <div>
          <h1>{meeting.title}</h1>
          <p className="meta">
            {meeting.meeting_date} · {meeting.meeting_type} · {meeting.project_name || "프로젝트 미정"}
          </p>
        </div>
        <StatusBadge status={meeting.status} />
      </div>

      <StatusSteps status={meeting.status} />

      {meeting.error_message ? <p className="error">처리 오류: {meeting.error_message}</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <div className="actions">
        <a
          aria-disabled={!meeting.report_markdown}
          className={`button-link ${meeting.report_markdown ? "" : "is-disabled"}`}
          href={meeting.report_markdown ? markdownDownloadUrl(meeting.id) : "#"}
        >
          Markdown 다운로드
        </a>
        {meeting.status !== "completed" ? (
          <button disabled={isProcessing} onClick={retryProcess} type="button">
            {isProcessing ? "처리 중..." : "분석 실행"}
          </button>
        ) : null}
      </div>

      <div className="content-grid">
        <article>
          <h2>회의 보고서</h2>
          <pre className="report-view">{meeting.report_markdown || "생성된 보고서가 없습니다."}</pre>
        </article>

        <article>
          <h2>Transcript</h2>
          <pre className="transcript-view">{meeting.transcript || "변환된 transcript가 없습니다."}</pre>
        </article>
      </div>
    </section>
  );
}
