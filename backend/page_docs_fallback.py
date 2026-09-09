"""
Local fallback content for the pages Waypoint knows how to guide someone
through, used when SUPABASE_URL / SUPABASE_KEY aren't set. In production
these rows live in Supabase's `page_docs` table (see supabase.sql) so a
product team can edit the copy without a redeploy.

Each entry is what a first-time user would actually need to know: what the
page is for, what has to be true before it does anything useful, and the
one thing to do next.
"""

PAGE_DOCS = {
    "dashboard": {
        "title": "Dashboard",
        "purpose": "System health at a glance: is the SDK connected, what happened today, and is anything blocking in production.",
        "prerequisites": "None — this is safe to open with zero data.",
        "next_step": "If Connection Health shows 'Not connected', send a test event before doing anything else.",
    },
    "traces": {
        "title": "Traces",
        "purpose": "Inspect one model interaction end to end: input, output, latency, model identity, and every guardrail finding tied to that run.",
        "prerequisites": "At least one event has to have arrived from the SDK. If none have, this page is empty by design, not broken.",
        "next_step": "Start here right after your integration sends its first event.",
    },
    "agent-intel": {
        "title": "Agent Intelligence",
        "purpose": "Per-dimension scoring for agent behavior (tool use quality, grounding, instruction adherence), compared run over run.",
        "prerequisites": "Needs evaluated traces — run at least one Evaluator task first, or these numbers are placeholders.",
        "next_step": "Compare a dimension before/after a prompt or context change to see if it actually moved.",
    },
    "agent-runs": {
        "title": "Agent Runs",
        "purpose": "A rule-by-rule breakdown of one run: which checks passed, which didn't apply and why, which failed.",
        "prerequisites": "At least one guardrail rule has to be configured for anything to show besides 'not applicable'.",
        "next_step": "Read the 'why' on any failed rule before you change production behavior based on the aggregate score.",
    },
    "evaluators": {
        "title": "Evaluators",
        "purpose": "Run a structured evaluation task against live traces — once, on a sample, or on a recurring schedule.",
        "prerequisites": "Needs traces to evaluate against.",
        "next_step": "Set a schedule once a one-off run looks right, so drift gets caught automatically.",
    },
    "guardrails": {
        "title": "Guardrails",
        "purpose": "Rules that flag or block behavior in production. The tester lets you validate a rule safely before it can block anything.",
        "prerequisites": "None to view; moving a rule from flagging to blocking should only happen after Test Guardrails confirms it behaves as expected.",
        "next_step": "If the tester's result ever disagrees with what a live trace actually showed, treat that as a bug to report, not a fluke.",
    },
}
