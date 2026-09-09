const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function askWaypoint({ page, question, projectState, sessionId }) {
  const res = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      page,
      question,
      project_state: projectState,
      session_id: sessionId,
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `Waypoint backend returned ${res.status}`);
  }
  return res.json(); // { answer, action, grounded_on, session_id }
}

export async function fetchSessionMessages(sessionId) {
  const res = await fetch(`${API_URL}/api/sessions/${encodeURIComponent(sessionId)}/messages`);
  if (!res.ok) return []; // no history yet is not an error
  return res.json(); // [{ page, question, answer, action, created_at }]
}

export async function fetchHealth() {
  const res = await fetch(`${API_URL}/api/health`);
  if (!res.ok) throw new Error("backend unreachable");
  return res.json();
}
