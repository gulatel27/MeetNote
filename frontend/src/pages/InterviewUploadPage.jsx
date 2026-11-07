import { useState } from "react";

import { processMeeting, uploadMeeting } from "../api/client.js";

function today() {
  return new Date().toISOString().slice(0, 10);
}

export const DEFAULT_INTERVIEW_QUESTIONS = `총 4단계 평가항목들에 대해 의견을 상세히 기재해 주시기 바랍니다.

* Job & Competency (경력/직무역량)
[지원 동기/이직 사유]
과거 이직 횟수와 사유가 타당하고 지원 동기가 명확한가?
[과거행동기반]
과거의 경험을 토대로 창의적 문제해결능력을 갖췄는가?
[직무 적합성]
요구된 보유기술 및 전문 지식을 바탕으로 즉시 활용이 가능한가?

* Leadership & Communication (리더쉽/소통)
[리더쉽/책임감]
직위 및 직책에 부합하는 리더쉽과 책임감을 겸비하고 있는가?
[협동심]
공동의 목표를 달성하기 위해 필요한 협동심을 가지고 있는가?
[커뮤니케이션]
업무 소통시 원활한 커뮤니케이션이 가능한가?

* Career & Training (경력개발)
[경력관리]
꾸준한 자기 계발 및 경력 개발을 실천해왔는가?
[육성방안]
후보자의 향후 구체적 활용 방안 및 육성 방안이 무엇인가?

* Character & Personality (성향/인성)
[인성]
후보자의 개인적 성향과 특성이 어떠한가?
(ex. 외향적, 내성적, 성격의 장단점)
[가치관/태도]
정직함과 책임의식을 가지고 있는가?

* 면접자에 대한 종합의견을 작성해주세요.`;

export default function InterviewUploadPage({ navigate }) {
  const [form, setForm] = useState({
    audioFile: null,
    title: "",
    meetingDate: today(),
    candidate: "",
    interviewers: "",
    projectName: "",
    customPrompt: DEFAULT_INTERVIEW_QUESTIONS,
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
      setError("업로드할 면접 음성파일을 선택하세요.");
      return;
    }
    if (!form.customPrompt.trim()) {
      setError("평가 질문지를 입력하세요.");
      return;
    }

    const participants = [
      form.candidate.trim() ? `지원자: ${form.candidate.trim()}` : "",
      form.interviewers.trim() ? `면접관: ${form.interviewers.trim()}` : "",
    ]
      .filter(Boolean)
      .join(" / ");

    setIsSubmitting(true);
    try {
      setMessage("파일 업로드 중...");
      const uploadResult = await uploadMeeting({
        audioFile: form.audioFile,
        title: form.title,
        meetingDate: form.meetingDate,
        participants,
        projectName: form.projectName,
        meetingType: "면접",
        reportType: "interview",
        customPrompt: form.customPrompt,
      });
      uploadedMeetingId = uploadResult.meeting_id;
      setMessage("STT 변환 및 면접 평가서 작성 중...");
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
        <h1>면접 평가</h1>
        <p className="lead">
          면접 녹음을 업로드하면 평가 질문지의 항목별 의견과 종합의견을 작성한 면접 평가서 초안을 생성합니다.
        </p>
        <p className="field-help">
          녹음에서 근거를 찾지 못한 항목은 "면접 중 확인되지 않음"으로 표시됩니다. 결과는 초안이므로 면접관이 검토 후
          수정해서 사용하세요.
        </p>
      </div>

      <form className="form-panel" onSubmit={handleSubmit}>
        <label>
          면접 음성파일
          <input
            accept=".mp3,.wav,.m4a,.mp4,audio/*,video/mp4"
            disabled={isSubmitting}
            onChange={(event) => updateField("audioFile", event.target.files?.[0] || null)}
            required
            type="file"
          />
        </label>

        <label>
          면접 제목
          <input
            disabled={isSubmitting}
            onChange={(event) => updateField("title", event.target.value)}
            placeholder="예: 홍길동 1차 팀 면접"
            required
            type="text"
            value={form.title}
          />
        </label>

        <div className="two-column">
          <label>
            면접 일자
            <input
              disabled={isSubmitting}
              onChange={(event) => updateField("meetingDate", event.target.value)}
              required
              type="date"
              value={form.meetingDate}
            />
          </label>

          <label>
            지원 포지션
            <input
              disabled={isSubmitting}
              onChange={(event) => updateField("projectName", event.target.value)}
              placeholder="예: DB 엔지니어 (경력)"
              type="text"
              value={form.projectName}
            />
          </label>
        </div>

        <div className="two-column">
          <label>
            지원자
            <input
              disabled={isSubmitting}
              onChange={(event) => updateField("candidate", event.target.value)}
              placeholder="예: 홍길동"
              type="text"
              value={form.candidate}
            />
          </label>

          <label>
            면접관
            <input
              disabled={isSubmitting}
              onChange={(event) => updateField("interviewers", event.target.value)}
              placeholder="예: 김민수, 이지은"
              type="text"
              value={form.interviewers}
            />
          </label>
        </div>

        <label>
          평가 질문지
          <textarea
            disabled={isSubmitting}
            onChange={(event) => updateField("customPrompt", event.target.value)}
            rows="18"
            value={form.customPrompt}
          />
          <span className="field-help">
            기본 질문지가 채워져 있습니다. 항목을 수정하면 수정한 질문지 기준으로 평가서가 작성됩니다.{" "}
            <button
              className="secondary-button"
              disabled={isSubmitting}
              onClick={() => updateField("customPrompt", DEFAULT_INTERVIEW_QUESTIONS)}
              type="button"
            >
              기본 질문지로 되돌리기
            </button>
          </span>
        </label>

        <button disabled={isSubmitting} type="submit">
          <span aria-hidden="true">▶</span>
          {isSubmitting ? "분석 처리 중..." : "업로드 및 면접 평가 시작"}
        </button>

        {message ? <p className="notice">{message}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </form>
    </section>
  );
}
