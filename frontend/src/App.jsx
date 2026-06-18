import { useEffect, useState } from "react";

import HistoryPage from "./pages/HistoryPage.jsx";
import MeetingResultPage from "./pages/MeetingResultPage.jsx";
import UploadPage from "./pages/UploadPage.jsx";

function getRoute() {
  return window.location.hash.replace(/^#/, "") || "/";
}

export default function App() {
  const [route, setRoute] = useState(getRoute());

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (path) => {
    window.location.hash = path;
    setRoute(path);
  };

  let page = <UploadPage navigate={navigate} />;
  const meetingMatch = route.match(/^\/meetings\/(\d+)$/);
  if (route === "/history") {
    page = <HistoryPage navigate={navigate} />;
  } else if (meetingMatch) {
    page = <MeetingResultPage meetingId={meetingMatch[1]} />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => navigate("/")} type="button">
          회의 보고서 자동화
        </button>
        <nav>
          <button onClick={() => navigate("/")} type="button">
            업로드
          </button>
          <button onClick={() => navigate("/history")} type="button">
            히스토리
          </button>
        </nav>
      </header>
      <main>{page}</main>
    </div>
  );
}
