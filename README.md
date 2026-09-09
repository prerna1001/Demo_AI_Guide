# Waypoint

A contextual AI layer for complex products: a per-page guided tour plus an
"Ask about this page" assistant that answers using the page you're on and
your product's live state, and can navigate you to the fix instead of just
describing it.

This repo demos it inside a small invented host app ("Aperture") with the
kind of dense, multi-tab IA that makes onboarding hard in the first place —
swap the six mock pages in `frontend/src/data/pages.js` for your product's
real ones and the rest of the wiring holds.

## Why this shape

**One agent, one tool — not multi-agent.** The job is: answer a question,
grounded in the current page + live state, and optionally take one
navigation action. That's a single LLM call with a single `navigate` tool,
executed once. A multi-agent setup (planner + sub-agents) would add
latency, cost, and failure surface without doing anything this doesn't
already do. If the scope grows into something like root-cause analysis over
many past failures, that's still one agent taking a short sequence of tool
calls — not multiple agents.

**Where the effort actually goes**, in order:
1. **Context assembly** — what state actually gets handed to the model per
   page (SDK status, config, recent errors). This is the entire difference
   between a real assistant and a chatbot glued onto your docs.
2. **The tool-call layer** — turning an answer into a real product action
   (open a page, open a specific rule) instead of a paragraph telling the
   user where to click.
3. **Honest uncertainty** — the system prompt tells the model to say
   "likely cause, unconfirmed" rather than inventing a confident answer.

Comparatively little time goes into exhaustive page coverage or any
multi-agent scaffolding.

## Architecture

```
frontend/  React (Vite) — the host app UI + the Waypoint tour and ask panel
backend/   FastAPI — /api/ask talks to Llama, grounded by context_store.py
```

- **LLM: Llama**, via any OpenAI-chat-completions-shaped endpoint —
  `backend/llama_client.py` has no vendor-specific code, so Ollama locally,
  or a hosted Llama endpoint (Groq, Together, Fireworks, your own vLLM),
  are a 3-line env change, not a code change.
- **Context: Supabase**, as a starting point — `backend/context_store.py`
  reads page docs and logs chat events to Supabase when configured
  (`backend/supabase.sql` has the schema + seed data), and falls back to a
  bundled local dict otherwise so the whole thing runs with zero external
  services. This is explicitly a "for now" choice: once retrieval needs to
  go beyond one doc per page (past incidents, release notes), the natural
  next step is a `pgvector` column in the same Supabase project — the
  seam for that is already `context_store.get_page_doc`.

## Running it

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in Supabase creds if/when you have them
uvicorn main:app --reload --port 8000
```

**Llama** — easiest local path is [Ollama](https://ollama.com):
```bash
ollama pull llama3.1
ollama serve
```
Without this running, `/api/ask` returns a clear 502 telling you so
(everything else — health check, page docs — works regardless).

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_URL, defaults to localhost:8000
npm run dev
```
Open the printed localhost URL. The demo starts on **Traces** with the SDK
disconnected — try the suggested question "Why are no traces visible?" and
watch it explain why, then open Connection Health for you.

**Supabase (optional)** — create a project, run `backend/supabase.sql` in
its SQL editor, then set `SUPABASE_URL` / `SUPABASE_KEY` in `backend/.env`.
Nothing else changes; `context_store.py` picks it up automatically and the
app behaves identically either way.

## What's fabricated vs. real

Everything under `frontend/src/data/pages.js` (traces, scores, the PII
example) is mock data for the demo. The `/api/ask` call, the Llama round
trip, the tool-calling navigation, and the Supabase read/write paths are
real and will do exactly what they do here against your actual product's
pages and state.
