import { useEffect, useRef, useState } from "react";
import { PAGE_META, QUICK_QUESTIONS } from "../data/pages.js";
import { askWaypoint, fetchSessionMessages } from "../lib/api.js";

let idCounter = 0;
const nextId = () => `m${++idCounter}`;

const SESSION_STORAGE_KEY = "waypoint_session_id";

function loadOrCreateSessionId() {
  try {
    const existing = localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
  } catch {
    // localStorage can throw in some contexts (private mode, blocked
    // storage) — fall through to a fresh in-memory id for this tab.
  }
  const fresh = `sess_${Math.random().toString(36).slice(2)}`;
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, fresh);
  } catch {
    /* ignore */
  }
  return fresh;
}

export default function AskPanel({ currentPage, projectState, onNavigate }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const sessionId = useRef(loadOrCreateSessionId());
  const logRef = useRef(null);

  // On mount, try to restore this session's past chat instead of always
  // starting blank — this is what makes "come back and see this chat
  // later" actually work, as long as the backend has somewhere durable
  // to read it from (Supabase) or the backend process never restarted
  // (in-memory fallback).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const past = await fetchSessionMessages(sessionId.current).catch(() => []);
      if (cancelled) return;
      if (past.length > 0) {
        const restored = past.flatMap((turn) => [
          { id: nextId(), role: "user", text: turn.question },
          { id: nextId(), role: "assistant", text: turn.answer },
        ]);
        setMessages(restored);
      } else {
        setMessages([
          {
            id: nextId(),
            role: "assistant",
            text: `Hi — I can see you're on ${PAGE_META[currentPage].title}. Ask me anything about this page, or try the suggested question below.`,
          },
        ]);
      }
      setHistoryLoaded(true);
    })();
    return () => {
      cancelled = true;
    };
    // Deliberately only on mount — currentPage changing later shouldn't
    // wipe a restored conversation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages]);

  function addMessage(role, text) {
    setMessages((m) => [...m, { id: nextId(), role, text }]);
  }

  async function send(question) {
    const q = (question ?? input).trim();
    if (!q || busy) return;
    setInput("");
    addMessage("user", q);
    setBusy(true);

    try {
      const result = await askWaypoint({
        page: currentPage,
        question: q,
        projectState,
        sessionId: sessionId.current,
      });
      addMessage("assistant", result.answer);
      if (result.action && result.action.type === "navigate") {
        onNavigate(result.action.page);
        addMessage("system", `Opened ${PAGE_META[result.action.page]?.title ?? result.action.page} for you.`);
      }
    } catch (err) {
      addMessage("error", err.message || "Couldn't reach the Waypoint backend. Is it running on the expected port?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card rail-card">
      <div className="wp-brand" style={{ marginBottom: 10 }}>
        <div className="mark">◈</div>
        <div>
          <div className="name">Waypoint</div>
          <div className="tagline">the contextual layer</div>
        </div>
      </div>
      <h2>Ask about this page</h2>
      <div className="sub">Answers using the current tab and this project's live state, remembers this conversation, and can jump you straight to the fix.</div>

      <div className="chips">
        <button className="chip" onClick={() => send(QUICK_QUESTIONS[currentPage])} disabled={busy || !historyLoaded}>
          {QUICK_QUESTIONS[currentPage]}
        </button>
      </div>

      <div className="chat-log" ref={logRef}>
        {!historyLoaded && <div className="msg system">Loading this chat…</div>}
        {messages.map((m) => (
          <div key={m.id} className={`msg ${m.role}`}>{m.text}</div>
        ))}
        {busy && <div className="msg assistant">Thinking…</div>}
      </div>

      <div className="ask-input-row">
        <input
          type="text"
          placeholder="Ask a focused question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") send(); }}
          disabled={busy || !historyLoaded}
        />
        <button className="ask-send" onClick={() => send()} disabled={busy || !historyLoaded} aria-label="Send">→</button>
      </div>
      <div className="ask-note">
        Calls the Waypoint backend (FastAPI → Llama), grounded in the mock project state and remembered across reloads for this session — nothing here is scripted.
      </div>
    </div>
  );
}
