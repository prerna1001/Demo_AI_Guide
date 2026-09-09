"""
Waypoint backend — orchestrates a small sequential multi-agent pipeline to
answer "what does this page do / why is it doing that" questions, and can
act by calling a single `navigate` tool. See agents.py for what each agent
does and why this is a sequential pipeline rather than autonomous peer
agents, and README.md for the fuller architecture write-up.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import context_store
from agents import AnsweringAgent, GroundingGuardAgent, RetrievalAgent, ScopeGuardAgent
from llama_client import LlamaClient, LlamaError
from schemas import AskRequest, AskResponse, NavigateAction, PageDoc, SessionMessage

load_dotenv()

app = FastAPI(title="Waypoint", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

llama = LlamaClient()

# Build the tool's page enum from whatever page ids actually exist right now
# (Supabase if configured, otherwise the local fallback) instead of
# hardcoding the list a second time.
_known_pages = [d["id"] for d in context_store.list_page_docs()]

NAVIGATE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "navigate",
        "description": "Switch the product to a different page that has the answer. Call this ALONGSIDE writing the real answer as text, never in place of it — the user should get the answer and the navigation together, not one or the other.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {"type": "string", "enum": _known_pages},
            },
            "required": ["page"],
        },
    },
}

# One instance of each agent, built once at import time and reused across
# requests — cheap since they're just (client, config) wrappers with no
# per-request state of their own.
scope_guard = ScopeGuardAgent(llama)
retrieval_agent = RetrievalAgent(llama, context_store)
answering_agent = AnsweringAgent(llama, NAVIGATE_TOOL_SCHEMA, _known_pages)
grounding_guard = GroundingGuardAgent(llama)


@app.get("/api/health")
def health():
    using_supabase = context_store.is_using_supabase()
    return {
        "status": "ok",
        "llama_base_url": llama.base_url,
        "llama_model": llama.model,
        "embed_model": llama.embed_model,
        "context_store": "supabase" if using_supabase else "local_fallback",
        "retrieval": "supabase_pgvector" if using_supabase else "local_cosine_fallback",
    }


@app.get("/api/pages", response_model=list[PageDoc])
def list_pages():
    return context_store.list_page_docs()


@app.get("/api/sessions/{session_id}/messages", response_model=list[SessionMessage])
def get_session_messages(session_id: str):
    """Lets the frontend restore a past chat instead of always starting
    blank — reads the same chat_events rows /api/ask writes to."""
    return context_store.get_session_messages(session_id)


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    doc = context_store.get_page_doc(req.page)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Unknown page '{req.page}'")

    session_id = req.session_id or context_store.new_session_id()
    history = context_store.get_recent_history(session_id, limit=6)

    # --- Agent 1: ScopeGuard ------------------------------------------------
    if not scope_guard.classify(req.question, doc, history):
        decline = (
            f"That's outside what I can help with here — I'm scoped to {doc['title']} "
            "and this product, not general questions. Try asking something about this "
            "page instead."
        )
        context_store.log_chat_event(session_id, req.page, req.question, decline, None)
        return AskResponse(answer=decline, action=None, grounded_on=[], session_id=session_id)

    # --- Agent 2: Retrieval (RAG) -------------------------------------------
    try:
        chunks = retrieval_agent.retrieve(req.question)
    except LlamaError:
        chunks = []

    # --- Agent 3: Answering --------------------------------------------------
    try:
        answer_text, executed = answering_agent.answer(
            question=req.question,
            current_page_id=doc["id"],
            current_page_prereq=doc["prerequisites"],
            chunks=chunks,
            project_state=req.project_state,
            history=history,
        )
    except LlamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # --- Agent 4: GroundingGuard ---------------------------------------------
    if not grounding_guard.verify(answer_text, chunks, req.project_state):
        answer_text = (
            "I want to avoid guessing here — I couldn't confirm that against what I "
            "actually have access to. Could you rephrase, or check this against the "
            "page directly?"
        )
        executed = None

    action = None
    if executed and executed["result"].get("ok"):
        action = NavigateAction(page=executed["result"]["opened"])

    grounded_on = sorted({c["page_id"] for c in chunks}) if chunks else [doc["id"]]

    context_store.log_chat_event(
        session_id, req.page, req.question, answer_text, action.model_dump() if action else None
    )

    return AskResponse(
        answer=answer_text, action=action, grounded_on=grounded_on, session_id=session_id
    )
