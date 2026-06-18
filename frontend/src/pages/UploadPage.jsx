import { useState } from "react";

import { processMeeting, uploadMeeting } from "../api/client.js";

const MEETING_TYPES = ["내부회의", "고객회의", "장애회의", "정기회의", "기타"];

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function UploadPage({ navigate }) {
  const [form, setForm] = useState({
    audioFile: null,
    title: "",
    meetingDate: today(),
    participants: "",
    projectName: "",
    meetingType: "내부회의",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    let uploadedMeetingId = null;

    if (!form.audioFile) {
      setError("업로드할 음성파일을 선택하세요.");
      return;
    }

    setIsSubmitting(true);
    try {
      setMessage("파일 업로드 중...");
      const uploadResult = await uploadMeeting(form);
      uploadedMeetingId = uploadResult.meeting_id;
      setMessage("STT 변환 및 요약 생성 중...");
      await processMeeting(uploadedMeetingId);
      navigate(`/meetings/${uploadedMeetingId}`);
    } catch (err) {
      if (uploadedMeetingId) {
        navigate(`/meetings/${uploadedMeetingId}`);
        return;
      }
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="page-grid">
      <div>
        <h1>회의 보고서 자동화</h1>
        <p className="lead">음성파일을 업로드하면 STT 변환, 요약, Markdown 회의 보고서 생성을 순차 실행합니다.</p>
      </div>

      <form className="form-panel" onSubmit={handleSubmit}>
        <label>
          회의 음성파일
          <input
            accept=".mp3,.wav,.m4a,.mp4,audio/*,video/mp4"
            disabled={isSubmitting}
            onChange={(event) => updateField("audioFile", event.target.files?.[0] || null)}
            required
            type="file"
          />
        </label>

        <label>
          회의 제목
          <input
            disabled={isSubmitting}
            onChange={(event) => updateField("title", event.target.value)}
            placeholder="예: 6월 정기 운영회의"
            required
            type="text"
            value={form.title}
          />
        </label>

        <div className="two-column">
          <label>
            회의 일자
            <input
              disabled={isSubmitting}
              onChange={(event) => updateField("meetingDate", event.target.value)}
              required
              type="date"
              value={form.meetingDate}
            />
          </label>

          <label>
            회의 유형
            <select
              disabled={isSubmitting}
              onChange={(event) => updateField("meetingType", event.target.value)}
              value={form.meetingType}
            >
              {MEETING_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label>
          참석자
          <input
            disabled={isSubmitting}
            onChange={(event) => updateField("participants", event.target.value)}
            placeholder="예: 김민수, 이지은, 고객사 박지훈"
            required
            type="text"
            value={form.participants}
          />
        </label>

        <label>
          고객사 또는 프로젝트명
          <input
            disabled={isSubmitting}
            onChange={(event) => updateField("projectName", event.target.value)}
            placeholder="예: ABC 구축 프로젝트"
            type="text"
            value={form.projectName}
          />
        </label>

        <button disabled={isSubmitting} type="submit">
          {isSubmitting ? "분석 처리 중..." : "업로드 및 분석 시작"}
        </button>

        {message ? <p className="notice">{message}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </form>
    </section>
  );
}
