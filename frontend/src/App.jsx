import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import PageView from "./components/PageView.jsx";
import GuidedTour from "./components/GuidedTour.jsx";
import AskPanel from "./components/AskPanel.jsx";
import { PAGE_ORDER, makeInitialState } from "./data/pages.js";

export default function App() {
  const [currentPage, setCurrentPage] = useState("traces"); // onboarding friction happens here first
  const [tourActive, setTourActive] = useState(true);
  const [data, setData] = useState(makeInitialState());

  function navigate(pageId) {
    if (!PAGE_ORDER.includes(pageId)) return;
    setCurrentPage(pageId);
  }

  function handleTourNext(nextId) {
    if (nextId) navigate(nextId);
    else setTourActive(false);
  }

  function sendTestEvent() {
    setData((d) => ({ ...d, sdkConnected: true, traceCount: 3, lastEventAt: new Date().toISOString() }));
  }

  return (
    <>
      <div className="top-strip">
        <span className="tag">Prototype</span>
        <span>
          <strong>Waypoint</strong> — a contextual AI layer that explains any page and can act on
          it, demoed here inside a sample AI-observability product. Click around, run the tour,
          and ask the panel on the right a real question.
        </span>
      </div>

      <div className="shell">
        <Sidebar currentPage={currentPage} onNavigate={navigate} tourActive={tourActive} />

        <main className="content">
          <PageView
            page={currentPage}
            state={{ data, onSendTestEvent: sendTestEvent }}
            onNavigate={navigate}
          />
        </main>

        <aside className="rail">
          <GuidedTour
            active={tourActive}
            currentPage={currentPage}
            onNext={handleTourNext}
            onSkip={() => setTourActive(false)}
            onRestart={() => { setTourActive(true); navigate("traces"); }}
          />
          <AskPanel currentPage={currentPage} projectState={data} onNavigate={navigate} />
        </aside>
      </div>

      <div className="footer-note">
        This is a click-through prototype of Waypoint, a contextual AI layer for complex
        products — built to make the idea concrete after watching real onboarding friction
        firsthand. Data and traces shown are fabricated for demonstration.
      </div>
    </>
  );
}
