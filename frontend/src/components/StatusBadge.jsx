const STATUS_LABELS = {
  uploaded: "업로드 완료",
  stt_processing: "STT 변환 중",
  summarizing: "요약 생성 중",
  completed: "보고서 생성 완료",
  failed: "실패",
};

export default function StatusBadge({ status }) {
  return <span className={`status status-${status}`}>{STATUS_LABELS[status] || status}</span>;
}

export function StatusSteps({ status }) {
  const steps = [
    ["uploaded", "업로드"],
    ["stt_processing", "STT"],
    ["summarizing", "요약"],
    ["completed", "완료"],
  ];
  const order = steps.map(([key]) => key);
  const activeIndex = order.indexOf(status);

  return (
    <div className="status-steps">
      {steps.map(([key, label], index) => (
        <div
          className={`status-step ${index <= activeIndex || status === "completed" ? "is-done" : ""}`}
          key={key}
        >
          <span>{index + 1}</span>
          {label}
        </div>
      ))}
    </div>
  );
}
