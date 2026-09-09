import { PAGE_META } from "../data/pages.js";

function PageHead({ id }) {
  return (
    <div className="page-head">
      <h1>{PAGE_META[id].title}</h1>
      <p>{PAGE_META[id].desc}</p>
    </div>
  );
}

function Dashboard({ state, onSendTestEvent }) {
  return (
    <>
      <PageHead id="dashboard" />
      <div className="tile-row">
        <div className="card tile">
          <div className="label">Connection health</div>
          <div className="value">
            {state.sdkConnected ? (
              <span className="pill ok"><span className="dot" />Connected</span>
            ) : (
              <span className="pill bad"><span className="dot" />Not connected</span>
            )}
          </div>
        </div>
        <div className="card tile">
          <div className="label">Traces today</div>
          <div className="value">{state.traceCount}</div>
        </div>
        <div className="card tile">
          <div className="label">Tool Use Quality</div>
          <div className="value">
            {state.toolUseQuality.after}
            <span className="unit">% · was {state.toolUseQuality.before}%</span>
          </div>
        </div>
        <div className="card tile">
          <div className="label">Guardrail blocks (7d)</div>
          <div className="value">0</div>
        </div>
      </div>
      <div className="card card-pad">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Connection Health</h3>
        <p style={{ margin: "0 0 10px", fontSize: 13, color: "var(--text-muted)" }}>
          {state.sdkConnected
            ? "SDK connected. Last event: just now."
            : "No events received from the SDK yet."}
        </p>
        {!state.sdkConnected && (
          <button className="btn" onClick={onSendTestEvent}>Send a test event</button>
        )}
      </div>
    </>
  );
}

function Traces({ state, onOpenDashboard }) {
  if (!state.sdkConnected || state.traceCount === 0) {
    return (
      <>
        <PageHead id="traces" />
        <div className="card empty-state">
          <div className="icon">◇</div>
          <h3>No traces yet</h3>
          <p>
            Traces will appear here as soon as your SDK sends its first event. If you
            expected to see data already, check Connection Health on the Dashboard.
          </p>
          <button className="btn" onClick={onOpenDashboard}>Open Connection Health</button>
        </div>
      </>
    );
  }

  const rows = [
    { id: "trc_9f21", model: "gpt-4o-mini", latency: "612ms", finding: "PII detected", status: "flagged" },
    { id: "trc_9f1e", model: "claude-3.7-sonnet", latency: "884ms", finding: "—", status: "clean" },
    { id: "trc_9f0a", model: "gpt-4o-mini", latency: "401ms", finding: "—", status: "clean" },
  ];

  return (
    <>
      <PageHead id="traces" />
      <div className="card table-wrap">
        <table>
          <thead>
            <tr><th>Trace</th><th>Model</th><th>Latency</th><th>Guardrail finding</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="mono">{r.id}</td>
                <td>{r.model}</td>
                <td className="mono">{r.latency}</td>
                <td>{r.finding}</td>
                <td>
                  {r.status === "flagged" ? (
                    <span className="pill warn"><span className="dot" />Flagged</span>
                  ) : (
                    <span className="pill ok"><span className="dot" />Clean</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function AgentIntel({ state }) {
  const dims = [
    { name: "Tool Use Quality", before: state.toolUseQuality.before, after: state.toolUseQuality.after },
    { name: "Grounding", before: 55, after: 71 },
    { name: "Instruction Adherence", before: 78, after: 82 },
  ];
  return (
    <>
      <PageHead id="agent-intel" />
      <div className="card card-pad">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {dims.map((d) => (
            <div key={d.name}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                <span>{d.name}</span><span className="mono">{d.after}%</span>
              </div>
              <div style={{ height: 8, borderRadius: 5, background: "var(--surface-2)", overflow: "hidden", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, width: `${d.before}%`, background: "var(--border)" }} />
                <div style={{ position: "absolute", inset: 0, width: `${d.after}%`, background: "var(--host-accent)" }} />
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 4 }}>
                was {d.before}% before adding grounded workflow context
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function AgentRuns() {
  const rules = [
    { name: "Tool call matches declared schema", state: "pass", why: "All 4 tool calls in this run validated against their JSON schema." },
    { name: "Response grounded in retrieved context", state: "pass", why: "Claims traced back to 2 of 2 retrieved passages." },
    { name: "PII/PHI exposure", state: "fail", why: "Output contained a spaced-digit phone number pattern." },
    { name: "Voice consent metadata present", state: "na", why: "Not applicable — this run has no voice channel." },
  ];
  return (
    <>
      <PageHead id="agent-runs" />
      <div className="card card-pad">
        {rules.map((r) => (
          <div className="rule-row" key={r.name}>
            <div className={`rule-status ${r.state}`}>{r.state === "pass" ? "✓" : r.state === "fail" ? "!" : "–"}</div>
            <div>
              <div className="rule-name">{r.name}</div>
              <div className="rule-why">{r.why}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function Evaluators() {
  return (
    <>
      <PageHead id="evaluators" />
      <div className="card card-pad">
        <table>
          <thead><tr><th>Task</th><th>Sample</th><th>Schedule</th><th>Last run</th></tr></thead>
          <tbody>
            <tr><td>Tool Use Quality — checkout agent</td><td>10% of traffic</td><td>Every 6h</td><td className="mono">14:20</td></tr>
            <tr><td>Grounding — support agent</td><td>All flagged traces</td><td>On flag</td><td className="mono">13:58</td></tr>
          </tbody>
        </table>
      </div>
    </>
  );
}

function Guardrails() {
  return (
    <>
      <PageHead id="guardrails" />
      <div className="split">
        <div className="card card-pad">
          <div className="head">Live trace — trc_9f21</div>
          <p style={{ fontSize: 13, margin: "0 0 8px" }}>Input contained: <span className="mono">555 0192</span></p>
          <span className="pill warn"><span className="dot" />PII detected</span>
        </div>
        <div className="card card-pad">
          <div className="head">Guardrail tester</div>
          <p style={{ fontSize: 13, margin: "0 0 8px" }}>Same input: <span className="mono">555 0192</span></p>
          <span className="pill bad"><span className="dot" />No rule triggered</span>
        </div>
      </div>
      <div className="card card-pad section-gap">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>Why the mismatch matters</h3>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>
          Teams use the tester to sign off on production rules. If it disagrees with what
          the live path actually does, that sign-off is unreliable. Ask the panel on the
          right about this.
        </p>
      </div>
    </>
  );
}

export default function PageView({ page, state, onNavigate }) {
  switch (page) {
    case "dashboard":
      return <Dashboard state={state.data} onSendTestEvent={state.onSendTestEvent} />;
    case "traces":
      return <Traces state={state.data} onOpenDashboard={() => onNavigate("dashboard")} />;
    case "agent-intel":
      return <AgentIntel state={state.data} />;
    case "agent-runs":
      return <AgentRuns />;
    case "evaluators":
      return <Evaluators />;
    case "guardrails":
      return <Guardrails />;
    default:
      return null;
  }
}
