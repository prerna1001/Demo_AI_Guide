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

# Named metrics/concepts that actually appear in the product's UI, kept
# separate from PAGE_DOCS because they cut across pages (e.g. "Tool Use
# Quality" is scored on Agent Intelligence but explained by a rule on Agent
# Runs). Without this, the model has no way to answer a question about a
# specific term unless that exact string happens to be in the one-line
# page purpose above — which is how a legitimate question like "what is
# tool call match" ended up unanswerable. Kept here (not Supabase) since
# it's product copy, not something a user's session ever changes.
GLOSSARY = {
    "Tool Use Quality": (
        "An Agent Intelligence dimension: did the agent call the right tool, with "
        "the right arguments, at the right point in the conversation. Shown as a "
        "before/after percentage. There's no separate metric called 'tool call "
        "match' — this is the closest one in the product; if a user asks about "
        "tool call matching, answer using this."
    ),
    "Grounding": (
        "An Agent Intelligence dimension: whether the agent's answer is actually "
        "supported by the retrieved context/tool output it had, versus invented."
    ),
    "Instruction Adherence": (
        "An Agent Intelligence dimension: whether the agent followed the "
        "system/developer instructions it was given for that run."
    ),
    "Rule status on Agent Runs": (
        "Each row is one guardrail rule evaluated against one run. Status is "
        "one of: passed, failed, or not applicable (the rule's trigger condition "
        "never matched this run, e.g. a voice-consent rule on a run with no audio)."
    ),
    "PII/PHI detection": (
        "A guardrail rule category (Traces/Guardrails) that flags personally "
        "identifiable or health information in a trace's input/output."
    ),
}
