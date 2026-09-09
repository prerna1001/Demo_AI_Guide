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

**A sequential multi-agent pipeline, not autonomous peer agents.** Every
question follows the same fixed path — classify, retrieve, answer, verify —
with no branching between independent goals, so the right shape is four
specialized agents run in order, each owning one model call it can be
tested and swapped on its own (see `backend/agents.py`):

1. **ScopeGuardAgent** — is this question in scope for this product? A
   classify-only call, biased toward YES (an unfamiliar phrasing shouldn't
   get falsely declined).
2. **RetrievalAgent** — RAG: embeds the question and vector-searches for
   the page/glossary chunks that actually back an answer, instead of
   statically dumping every doc into every prompt.
3. **AnsweringAgent** — drafts the answer from what RetrievalAgent found,
   plus live project state and session history, and may call the
   `navigate` tool — always alongside a real answer, never instead of one.
4. **GroundingGuardAgent** — a second, independent check that the drafted
   answer only states what the retrieved context/state actually support.
   This is what makes "grounded, not hallucinated" an enforced property of
   the pipeline rather than just an instruction the answering call could
   ignore.

`backend/main.py` is a thin orchestrator: it calls these four in sequence
and returns. What it deliberately is **not**: autonomous agents that
negotiate, delegate to each other, or set their own sub-goals — nothing
here needs that, because there's exactly one path every question takes.
That distinction is the actual engineering call being made, and it's worth
being able to state precisely rather than reaching for "multi-agent" as a
label — a sequential pipeline of specialized agents is simpler to reason
about and debug than peer-to-peer agents, with no loss of capability for
this problem shape.

**Where the effort actually goes**, in order:
1. **Retrieval** — turning "what does this term/page mean" into the right
   chunk of grounding content, via real vector search, not keyword luck.
2. **The tool-call layer** — turning an answer into a real product action
   (open a page, open a specific rule) instead of a paragraph telling the
   user where to click.
3. **Enforced groundedness** — a second model call whose only job is to
   catch the first one inventing something, not just a prompt asking it to
   be careful.

## Architecture

```
frontend/  React (Vite) — the host app UI + the Waypoint tour and ask panel
backend/   FastAPI — /api/ask orchestrates agents.py, grounded via context_store.py
```

```
User question
     │
     ▼
ScopeGuardAgent ──(out of scope)──► decline, log, return
     │ in scope
     ▼
RetrievalAgent ──► embed question (Cloudflare Workers AI) ──► vector search
     │                                                        (Supabase pgvector,
     │                                                         or local cosine fallback)
     ▼
AnsweringAgent ──► LLM + `navigate` tool ──► draft answer (+ optional navigation)
     │
     ▼
GroundingGuardAgent ──(not grounded)──► replace with honest "can't confirm that"
     │ grounded
     ▼
log to chat_events (Supabase or in-memory) ──► response to the user
```

- **LLM: Llama**, via any OpenAI-chat-completions-shaped endpoint —
  `backend/llama_client.py` has no vendor-specific code for the chat path,
  so Ollama locally, or a hosted Llama endpoint (Groq, Together, Fireworks,
  your own vLLM), are a 3-line env change, not a code change. Embeddings
  (`LlamaClient.embed`) currently target Cloudflare Workers AI's native
  route specifically, since that's the provider in use here.
- **Retrieval: Supabase pgvector**, via a `knowledge_chunks` table and a
  `match_knowledge` SQL function (`backend/supabase.sql`) called through
  `context_store.search_knowledge`. Falls back to embedding the same fixed
  chunk set into an in-process cache and doing the identical cosine search
  in plain Python when Supabase isn't configured — same retrieval
  semantics either way, no external vector database required to run this
  locally with zero services set up. Populate the table once with
  `python backend/seed_knowledge.py` after applying `supabase.sql`.
- **Context/session storage: Supabase**, as a starting point —
  `backend/context_store.py` reads page docs and logs chat events to
  Supabase when configured, and falls back to a bundled local dict/list
  otherwise.

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

**Supabase (optional, needed for RAG/history to persist)** — create a
project, run `backend/supabase.sql` in its SQL editor (this also enables
the `vector` extension and creates `knowledge_chunks` + `match_knowledge`),
set `SUPABASE_URL` / `SUPABASE_KEY` in `backend/.env`, then run:
```bash
cd backend
python seed_knowledge.py   # embeds page docs + glossary into knowledge_chunks
```
Nothing else changes; `context_store.py` and `agents.py` pick it up
automatically and the app behaves the same either way — just backed by
real vector search + durable chat history instead of the in-memory
fallback. Check `GET /api/health` to confirm: `context_store` and
`retrieval` both flip from `local_fallback`/`local_cosine_fallback` to
`supabase`/`supabase_pgvector`.

## What's fabricated vs. real

Everything under `frontend/src/data/pages.js` (traces, scores, the PII
example) is mock data for the demo. The `/api/ask` call, the Llama round
trip, the tool-calling navigation, and the Supabase read/write paths are
real and will do exactly what they do here against your actual product's
pages and state.
