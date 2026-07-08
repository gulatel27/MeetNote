const OPTIONS = [
  {
    title: "미팅요약",
    description: "미팅 음성을 STT로 변환하고 안건, 결정사항, 액션아이템 중심의 보고서를 생성합니다.",
    path: "/meeting-report",
    icon: "📝",
  },
  {
    title: "세미나 요약",
    description: "강연/교육 음성을 공유용 핵심요약, 내용 요약, 청중 핵심 포인트로 정리합니다.",
    path: "/seminar-summary",
    icon: "🎤",
  },
  {
    title: "내부회의 요약",
    description: "내부 논의, 업무 공유, 후속 조치 중심의 요약 화면입니다.",
    path: "/internal-summary",
    icon: "🏢",
  },
];

export default function HomePage({ navigate }) {
  return (
    <section className="home-page">
      <div className="home-header">
        <h1>MeetNote</h1>
        <p className="lead">음성파일을 업로드하고 목적에 맞는 요약 보고서를 생성합니다.</p>
      </div>

      <div className="summary-options">
        {OPTIONS.map((option) => (
          <button className="summary-option" key={option.path} onClick={() => navigate(option.path)} type="button">
            <span className="summary-option-icon" aria-hidden="true">
              {option.icon}
            </span>
            <span>
              <strong>{option.title}</strong>
              <small>{option.description}</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
