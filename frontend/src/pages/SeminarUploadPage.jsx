import { useState } from "react";

import { processMeeting, uploadMeeting } from "../api/client.js";

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function SeminarUploadPage({ navigate }) {
  const [form, setForm] = useState({
    audioFile: null,
    imageFiles: [],
    title: "",
    meetingDate: today(),
    participants: "",
    projectName: "",
    meetingType: "세미나",
    reportType: "seminar",
    customPrompt: "",
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
      setError("업로드할 세미나 음성파일을 선택하세요.");
      return;
    }

    setIsSubmitting(true);
    try {
      setMessage("파일 업로드 중...");
      const uploadResult = await uploadMeeting(form);
      uploadedMeetingId = uploadResult.meeting_id;
      setMessage("STT 변환 및 세미나 요약 생성 중...");
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
    <section className="page-grid seminar-page">
      <div>
        <h1>세미나 요약</h1>
        <p className="lead">
          세미나 음성을 업로드하면 공유용 핵심요약, 내용 요약, 청중이 알아야 할 핵심 내용을 생성합니다.
        </p>
      </div>

      <form className="form-panel" onSubmit={handleSubmit}>
        <label>
          세미나 음성파일
          <input
            accept=".mp3,.wav,.m4a,.mp4,audio/*,video/mp4"
            disabled={isSubmitting}
            onChange={(event) => updateField("audioFile", event.target.files?.[0] || null)}
            required
            type="file"
          />
        </label>

        <label>
          참고 이미지 파일
          <input
            accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/*"
            disabled={isSubmitting}
            multiple
            onChange={(event) => updateField("imageFiles", Array.from(event.target.files || []))}
            type="file"
          />
          <span className="field-help">
            세미나 중 촬영한 발표자료, 화면, 화이트보드, 메모 이미지를 첨부하면 요약 작성 시 함께 참고합니다.
          </span>
          {form.imageFiles.length ? <span className="file-count">선택된 이미지 {form.imageFiles.length}개</span> : null}
        </label>

        <label>
          세미나 제목
          <input
            disabled={isSubmitting}
            onChange={(event) => updateField("title", event.target.value)}
            placeholder="예: AI 자동화 실무 세미나"
            required
            type="text"
            value={form.title}
          />
        </label>

        <div className="two-column">
          <label>
            세미나 일자
            <input
              disabled={isSubmitting}
              onChange={(event) => updateField("meetingDate", event.target.value)}
              required
              type="date"
              value={form.meetingDate}
            />
          </label>

          <label>
            발표자/진행자
            <input
              disabled={isSubmitting}
              onChange={(event) => updateField("participants", event.target.value)}
              placeholder="예: 홍길동, 김민수"
              type="text"
              value={form.participants}
            />
          </label>
        </div>

        <label>
          세미나 주제 또는 프로젝트명
          <input
            disabled={isSubmitting}
            onChange={(event) => updateField("projectName", event.target.value)}
            placeholder="예: 생성형 AI 업무 적용"
            type="text"
            value={form.projectName}
          />
        </label>

        <label>
          추가 프롬프트
          <textarea
            disabled={isSubmitting}
            onChange={(event) => updateField("customPrompt", event.target.value)}
            placeholder="예: 마케팅팀 공유용으로 작성. 실무 적용 아이디어를 더 강조. 전문 용어는 쉬운 설명을 덧붙일 것."
            rows="6"
            value={form.customPrompt}
          />
        </label>

        <button disabled={isSubmitting} type="submit">
          <span aria-hidden="true">▶</span>
          {isSubmitting ? "분석 처리 중..." : "업로드 및 세미나 요약 시작"}
        </button>

        {message ? <p className="notice">{message}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </form>
    </section>
  );
}
