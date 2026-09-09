// This is the demo "host" product Waypoint is layered onto — a generic
// AI-observability-style tool (called Aperture here, invented for the
// demo) with the same kind of page structure Waypoint is meant for:
// several dense, powerful tabs a first-time user has no obvious order to
// follow through.

export const HOST_NAME = "Aperture";

export const PAGE_ORDER = [
  "dashboard",
  "traces",
  "agent-intel",
  "agent-runs",
  "evaluators",
  "guardrails",
];

export const PAGE_META = {
  dashboard: {
    title: "Dashboard",
    desc: "System health at a glance: connection status, today's traces, and guardrail activity.",
  },
  traces: {
    title: "Traces",
    desc: "Inspect input, output, latency, model, guardrail findings, and the exact evidence for one run.",
  },
  "agent-intel": {
    title: "Agent Intelligence",
    desc: "Per-dimension scoring for agent behavior, compared run over run.",
  },
  "agent-runs": {
    title: "Agent Runs",
    desc: "A rule-by-rule breakdown: what passed, what didn't apply, and why.",
  },
  evaluators: {
    title: "Evaluators",
    desc: "Run structured evaluation tasks against live traces on a sample, filter, or schedule.",
  },
  guardrails: {
    title: "Guardrails",
    desc: "Rules that flag or block behavior in production, validated first in the tester.",
  },
};

export const TOUR_COPY = {
  dashboard: "Start here for a system-wide check: is the SDK connected, and what happened today.",
  traces: "Start here once your integration sends its first trace — every field you need to debug one run lives on this page.",
  "agent-intel": "See how agent behavior scores across dimensions, and whether a change actually moved the number.",
  "agent-runs": "See exactly which rules fired, which didn't apply, and why — before you trust the aggregate score.",
  evaluators: "Turn one-off checks into a recurring analysis over a sample of live traffic.",
  guardrails: "Test a rule safely here before you flip it from flagging to blocking in production.",
};

export const QUICK_QUESTIONS = {
  dashboard: "Is my SDK actually connected right now?",
  traces: "Why are no traces visible?",
  "agent-intel": "What does Tool Use Quality actually measure?",
  "agent-runs": "Why was the voice consent rule marked not applicable?",
  evaluators: "How do I make an evaluation run on a schedule instead of once?",
  guardrails: "Why did the tester say no PII was found?",
};

// Live mock state — this is exactly what a real integration would keep in
// memory / fetch from its own API, and it's what gets sent to the backend
// as "project_state" so Waypoint's answers are grounded in something real
// instead of generic.
export function makeInitialState() {
  return {
    sdkConnected: false,
    lastEventAt: null,
    traceCount: 0,
    toolUseQuality: { before: 40, after: 60, unit: "%" },
    piiExample: {
      livePath: "flagged as PII (phone number, spaced-digit pattern) on trace trc_9f21",
      testerPath: "returned 'no PII/PHI rule triggered' for the identical spaced-digit string",
      likelyCause:
        "different normalization before pattern matching on the two paths (unconfirmed — would need the tester's preprocessing step to say for sure)",
    },
  };
}
