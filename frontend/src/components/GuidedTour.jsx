import { PAGE_ORDER, PAGE_META, TOUR_COPY } from "../data/pages.js";

export default function GuidedTour({ active, currentPage, onNext, onSkip, onRestart }) {
  if (!active) {
    return (
      <div className="card rail-card">
        <h2>Guided tour</h2>
        <div className="sub">Walk through Traces → Guardrails the way a first-time user would.</div>
        <button className="btn ghost" style={{ marginTop: 12, width: "100%", justifyContent: "center" }} onClick={onRestart}>
          Restart tour
        </button>
      </div>
    );
  }

  const idx = PAGE_ORDER.indexOf(currentPage);
  const nextId = PAGE_ORDER[idx + 1];

  return (
    <div className="card rail-card">
      <div className="tour-badge">Guided tour · {idx + 1} of {PAGE_ORDER.length}</div>
      <h2>What this page does</h2>
      <div className="sub">{TOUR_COPY[currentPage]}</div>
      <div className="tour-dots">
        {PAGE_ORDER.map((_, i) => (
          <span key={i} className={i <= idx ? "done" : ""} />
        ))}
      </div>
      <div className="tour-actions">
        <button className="tour-skip" onClick={onSkip}>Skip tour</button>
        <button className="btn" onClick={() => onNext(nextId)}>
          {nextId ? `Next: ${PAGE_META[nextId].title}` : "Finish"}
        </button>
      </div>
    </div>
  );
}
