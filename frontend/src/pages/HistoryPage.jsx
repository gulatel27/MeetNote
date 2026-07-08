import { useEffect, useMemo, useState } from "react";

import { getMeetings } from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

const HISTORY_MODULES = [
  {
    key: "meeting",
    title: "미팅요약",
    description: "미팅 음성 기반 요약 및 보고서 생성 이력",
  },
  {
    key: "seminar",
    title: "세미나요약",
    description: "세미나 음성 기반 공유용 요약 이력",
  },
  {
    key: "internal",
    title: "내부회의요약",
    description: "내부회의 전용 요약 이력",
  },
];

function rowsForModule(meetings, moduleKey) {
  return meetings.filter((meeting) => (meeting.report_type || "meeting") === moduleKey);
}

function HistoryTable({ meetings, navigate }) {
  if (meetings.length === 0) {
    return <p className="empty-history">처리 이력이 없습니다.</p>;
  }

  return (
    <div className="table-wrap module-history-table">
      <table>
        <thead>
          <tr>
            <th>제목</th>
            <th>일자</th>
            <th>유형</th>
            <th>생성일</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {meetings.map((meeting) => (
            <tr key={meeting.id} onClick={() => navigate(`/meetings/${meeting.id}`)}>
              <td>{meeting.title}</td>
              <td>{meeting.meeting_date}</td>
              <td>{meeting.meeting_type}</td>
              <td>{new Date(meeting.created_at).toLocaleString()}</td>
              <td>
                <StatusBadge status={meeting.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function HistoryPage({ navigate }) {
  const [meetings, setMeetings] = useState([]);
  const [activeModule, setActiveModule] = useState("meeting");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError("");
      try {
        setMeetings(await getMeetings());
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const counts = useMemo(() => {
    return HISTORY_MODULES.reduce((acc, module) => {
      acc[module.key] = rowsForModule(meetings, module.key).length;
      return acc;
    }, {});
  }, [meetings]);

  const activeModuleMeta = HISTORY_MODULES.find((module) => module.key === activeModule) || HISTORY_MODULES[0];
  const activeRows = rowsForModule(meetings, activeModuleMeta.key);

  return (
    <section className="history-page">
      <div className="result-header">
        <div>
          <h1>처리 이력</h1>
          <p className="lead">상단 탭을 선택하면 해당 모듈의 처리 이력만 표시합니다.</p>
        </div>
      </div>

      {isLoading ? <p className="notice">목록을 불러오는 중...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      {!isLoading && !error ? (
        <section className="module-history-section">
          <div className="history-tabs" role="tablist" aria-label="히스토리 모듈">
            {HISTORY_MODULES.map((module) => (
              <button
                aria-selected={activeModule === module.key}
                className={activeModule === module.key ? "is-active" : ""}
                key={module.key}
                onClick={() => setActiveModule(module.key)}
                role="tab"
                type="button"
              >
                <span>{module.title}</span>
                <strong>{counts[module.key] || 0}</strong>
              </button>
            ))}
          </div>

          <header className="module-history-header">
            <div>
              <h2>{activeModuleMeta.title}</h2>
              <p>{activeModuleMeta.description}</p>
            </div>
            <span>{activeRows.length}건</span>
          </header>

          <HistoryTable meetings={activeRows} navigate={navigate} />
        </section>
      ) : null}
    </section>
  );
}
