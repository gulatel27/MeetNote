export default function InternalSummaryPage({ navigate }) {
  return (
    <section className="placeholder-page">
      <h1>내부회의 요약</h1>
      <p className="lead">내부회의 전용 요약은 다음 단계에서 구현 예정입니다. 현재는 미팅요약을 사용할 수 있습니다.</p>
      <button onClick={() => navigate("/meeting-report")} type="button">
        미팅요약으로 이동
      </button>
    </section>
  );
}
