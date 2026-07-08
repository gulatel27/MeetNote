import { useEffect, useState } from "react";

import HistoryPage from "./pages/HistoryPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import InternalSummaryPage from "./pages/InternalSummaryPage.jsx";
import MeetingResultPage from "./pages/MeetingResultPage.jsx";
import SeminarUploadPage from "./pages/SeminarUploadPage.jsx";
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

  let page = <HomePage navigate={navigate} />;
  const meetingMatch = route.match(/^\/meetings\/(\d+)$/);
  if (route === "/meeting-report") {
    page = <UploadPage navigate={navigate} />;
  } else if (route === "/seminar-summary") {
    page = <SeminarUploadPage navigate={navigate} />;
  } else if (route === "/internal-summary") {
    page = <InternalSummaryPage navigate={navigate} />;
  } else if (route === "/history") {
    page = <HistoryPage navigate={navigate} />;
  } else if (meetingMatch) {
    page = <MeetingResultPage meetingId={meetingMatch[1]} />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => navigate("/")} type="button">
          MeetNote
        </button>
        <nav>
          <button onClick={() => navigate("/")} type="button">
            홈
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
