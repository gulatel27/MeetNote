import { useEffect, useState } from "react";

import { getMeetings } from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function HistoryPage({ navigate }) {
  const [meetings, setMeetings] = useState([]);
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

  return (
    <section>
      <div className="result-header">
        <div>
          <h1>처리 이력</h1>
          <p className="lead">SQLite에 저장된 회의 처리 기록입니다.</p>
        </div>
      </div>

      {isLoading ? <p className="notice">목록을 불러오는 중...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>회의 제목</th>
              <th>회의 일자</th>
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
            {!isLoading && meetings.length === 0 ? (
              <tr>
                <td colSpan="5">아직 처리한 회의가 없습니다.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
