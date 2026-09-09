-- Waypoint context store
-- Run this once in the Supabase SQL editor for your project, then set
-- SUPABASE_URL / SUPABASE_KEY in backend/.env.

create table if not exists page_docs (
  id text primary key,
  title text not null,
  purpose text not null,
  prerequisites text not null,
  next_step text not null
);

create table if not exists chat_events (
  id uuid primary key default gen_random_uuid(),
  session_id text,
  page text not null,
  question text not null,
  answer text not null,
  action jsonb,
  created_at timestamptz not null default now()
);

create index if not exists chat_events_page_idx on chat_events (page);
create index if not exists chat_events_created_at_idx on chat_events (created_at desc);

-- Seed with the same copy backend/page_docs_fallback.py ships locally, so
-- moving to Supabase changes nothing about the demo's behavior — only where
-- the content lives and who can edit it.
insert into page_docs (id, title, purpose, prerequisites, next_step) values
  ('dashboard', 'Dashboard',
   'System health at a glance: is the SDK connected, what happened today, and is anything blocking in production.',
   'None — this is safe to open with zero data.',
   'If Connection Health shows ''Not connected'', send a test event before doing anything else.'),
  ('traces', 'Traces',
   'Inspect one model interaction end to end: input, output, latency, model identity, and every guardrail finding tied to that run.',
   'At least one event has to have arrived from the SDK. If none have, this page is empty by design, not broken.',
   'Start here right after your integration sends its first event.'),
  ('agent-intel', 'Agent Intelligence',
   'Per-dimension scoring for agent behavior (tool use quality, grounding, instruction adherence), compared run over run.',
   'Needs evaluated traces — run at least one Evaluator task first, or these numbers are placeholders.',
   'Compare a dimension before/after a prompt or context change to see if it actually moved.'),
  ('agent-runs', 'Agent Runs',
   'A rule-by-rule breakdown of one run: which checks passed, which did not apply and why, which failed.',
   'At least one guardrail rule has to be configured for anything to show besides ''not applicable''.',
   'Read the ''why'' on any failed rule before you change production behavior based on the aggregate score.'),
  ('evaluators', 'Evaluators',
   'Run a structured evaluation task against live traces — once, on a sample, or on a recurring schedule.',
   'Needs traces to evaluate against.',
   'Set a schedule once a one-off run looks right, so drift gets caught automatically.'),
  ('guardrails', 'Guardrails',
   'Rules that flag or block behavior in production. The tester lets you validate a rule safely before it can block anything.',
   'None to view; moving a rule from flagging to blocking should only happen after Test Guardrails confirms it behaves as expected.',
   'If the tester''s result ever disagrees with what a live trace actually showed, treat that as a bug to report, not a fluke.')
on conflict (id) do update set
  title = excluded.title,
  purpose = excluded.purpose,
  prerequisites = excluded.prerequisites,
  next_step = excluded.next_step;
