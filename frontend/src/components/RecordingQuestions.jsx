import { useState } from "react";
import { askMeetingQuestion } from "../api/client.js";

export default function RecordingQuestions({ meetingId, hasTranscript, isProcessing }) {
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState("");
  const [copyMessage, setCopyMessage] = useState("");

  const submitQuestion = async (event) => {
    event.preventDefault();
    if (!question.trim() || isAsking || !hasTranscript || isProcessing) return;
    const submittedQuestion = question.trim();
    setIsAsking(true);
    setError("");
    setCopyMessage("");
    try {
      const result = await askMeetingQuestion(meetingId, submittedQuestion);
      setAnswers((previous) => [...previous, { question: submittedQuestion, ...result }]);
      setQuestion("");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAsking(false);
    }
  };

  const copyAnswer = async (item) => {
    try {
      await navigator.clipboard.writeText([
        `질문: ${item.question}`, item.answer,
        ...item.evidence.map((quote) => `근거: ${quote}`),
      ].join("\n\n"));
      setCopyMessage("답변을 복사했습니다.");
    } catch {
      setCopyMessage("복사하지 못했습니다. 답변을 직접 선택해 복사하세요.");
    }
  };

  return (
    <article className="recording-questions report-card">
      <h2>녹음 내용에 질문하기</h2>
      <p>전사문을 바탕으로 AI가 답변하고 근거를 표시합니다. 각 질문은 독립적으로 분석합니다.</p>
      {!hasTranscript ? <p className="notice">먼저 음성 분석을 실행해 전사문을 생성하세요.</p> : null}
      <form onSubmit={submitQuestion}>
        <label htmlFor="recording-question">질문</label>
        <textarea
          id="recording-question" rows={3} maxLength={2000} required
          placeholder="예: 회의에서 결정된 작업 담당자와 마감일을 정리해줘."
          value={question} onChange={(event) => setQuestion(event.target.value)}
          disabled={!hasTranscript || isAsking || isProcessing}
        />
        <div className="actions">
          <button type="submit" disabled={!hasTranscript || !question.trim() || isAsking || isProcessing}>
            {isAsking ? "답변 생성 중..." : "AI 답변 생성"}
          </button>
          <span>{question.length}/2000</span>
        </div>
      </form>
      {isAsking ? <p role="status">녹음 내용을 분석하고 있습니다...</p> : null}
      {error ? <p className="error" role="alert">{error}</p> : null}
      {copyMessage ? <p role="status">{copyMessage}</p> : null}
      <div aria-live="polite" aria-busy={isAsking}>
        {answers.map((item, index) => (
          <section className="recording-answer" key={index}>
            <h3>{item.question}</h3>
            {item.insufficient_evidence ? <p className="notice">녹음에서 확인되지 않는 내용이 있습니다.</p> : null}
            <div className="recording-answer-text">{item.answer}</div>
            {item.evidence.length ? (
              <details open>
                <summary>전사문 근거</summary>
                {item.evidence.map((quote, quoteIndex) => <blockquote key={quoteIndex}>{quote}</blockquote>)}
              </details>
            ) : null}
            <button type="button" className="secondary-button" onClick={() => copyAnswer(item)}>답변 복사</button>
          </section>
        ))}
      </div>
      <p className="meta">전사 오류가 답변에 영향을 줄 수 있으니 근거를 확인하세요. 질문·답변은 이 화면을 벗어나거나 새로고침하면 사라집니다.</p>
    </article>
  );
}
