"""
Waypoint backend — a small FastAPI service that answers "what does this
page do / why is it doing that" questions grounded in (a) durable page docs
and (b) the caller's live product state, and can act by calling a single
`navigate` tool. See README.md for the architecture note on why this is one
agent with one tool, not a multi-agent system.
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import context_store
from llama_client import LlamaClient, LlamaError
from schemas import AskRequest, AskResponse, NavigateAction, PageDoc, SessionMessage

load_dotenv()

app = FastAPI(title="Waypoint", version="0.1.0")

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
        "description": "Switch the product to a different page when that page would actually resolve the user's question.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {"type": "string", "enum": _known_pages},
            },
            "required": ["page"],
        },
    },
}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llama_base_url": llama.base_url,
        "llama_model": llama.model,
        "context_store": "supabase" if context_store.is_using_supabase() else "local_fallback",
    }


@app.get("/api/pages", response_model=list[PageDoc])
def list_pages():
    return context_store.list_page_docs()


@app.get("/api/sessions/{session_id}/messages", response_model=list[SessionMessage])
def get_session_messages(session_id: str):
    """Lets the frontend restore a past chat instead of always starting
    blank — reads the same chat_events rows /api/ask writes to."""
    return context_store.get_session_messages(session_id)


def _is_on_topic(question: str, doc: dict, history: list[dict]) -> bool:
    """Scope guard: a single classify-only call that runs before the main
    prompt. Keeps the model from improvising an answer to something that
    has nothing to do with the product — a cheap, high-value step for
    cutting down hallucination, and deliberately NOT a second 'agent': it
    has no tools, makes no decisions beyond yes/no, and never answers the
    user itself.

    Deliberately biased toward YES: this only sees the page's one-line
    description, not everything actually shown on it, so an oddly-phrased
    but legitimate question (e.g. referencing a specific rule name) can
    look unfamiliar to it. Wrongly declining a real question is a worse
    failure than letting a borderline one through — the main model still
    won't invent facts either way, that's its own job. So we only decline
    on a clear, explicit NO; anything else (including a garbled or
    hedging response) defaults to letting it through.
    """
    context_hint = ""
    if history:
        last = history[-1]
        context_hint = f'Most recent exchange — Q: "{last["question"]}" A: "{last["answer"]}"\n\n'

    guard_system = (
        "You are a scope guard for Waypoint, an AI guide embedded in a software product. "
        "You only decide whether a question is in scope — you never answer it. Give the "
        "user the benefit of the doubt: an odd phrasing, a typo, or a question that names "
        "a specific feature/rule/term you don't recognize is still IN SCOPE if it could "
        "plausibly be about using, understanding, or troubleshooting this product or the "
        "page they're on — including follow-ups to the recent exchange below. Only say NO "
        "when the question is clearly about something else entirely: general trivia, a "
        "different product, or a personal request. Reply with exactly one word: YES or NO."
    )
    guard_user = (
        f"PAGE: {doc['title']} — {doc['purpose']}\n"
        f"{context_hint}"
        f'QUESTION: "{question}"\n'
        "In scope? Reply YES or NO only."
    )
    try:
        verdict = llama.complete(guard_system, guard_user)
    except LlamaError:
        # If the guard call itself fails, fail open to the main answer path
        # rather than falsely declining a question over an infra hiccup.
        return True

    # Only decline on an explicit, standalone "NO" — anything else (a
    # clean YES, hedging, a garbled non-answer) defaults to letting the
    # question through, per the bias explained above.
    return re.search(r"\bno\b", verdict.strip(), re.IGNORECASE) is None


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    doc = context_store.get_page_doc(req.page)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Unknown page '{req.page}'")

    session_id = req.session_id or context_store.new_session_id()
    history = context_store.get_recent_history(session_id, limit=6)

    if not _is_on_topic(req.question, doc, history):
        decline = (
            f"That's outside what I can help with here — I'm scoped to {doc['title']} "
            "and this product, not general questions. Try asking something about this "
            "page instead."
        )
        context_store.log_chat_event(session_id, req.page, req.question, decline, None)
        return AskResponse(answer=decline, action=None, grounded_on=[], session_id=session_id)

    system_prompt = (
        "You are Waypoint, a contextual AI guide embedded inside a software product. "
        "You answer ONE focused question at a time using only the page doc and live "
        "project state given to you — never invent data that isn't there. Answer in "
        "2-4 sentences, be concrete and specific, and if you're not certain of a root "
        "cause say so plainly instead of guessing. Call the `navigate` tool only when "
        "moving the user to a different page would actually help resolve their question."
    )

    user_prompt = (
        f"CURRENT PAGE: {doc['title']} ({doc['id']})\n"
        f"WHAT THIS PAGE DOES: {doc['purpose']}\n"
        f"WHAT HAS TO BE TRUE FIRST: {doc['prerequisites']}\n"
        f"RECOMMENDED NEXT STEP: {doc['next_step']}\n\n"
        f"LIVE PROJECT STATE (JSON): {req.project_state}\n\n"
        f'USER QUESTION: "{req.question}"'
    )

    def execute_navigate(args: dict) -> dict:
        target = args.get("page")
        if target not in _known_pages:
            return {"ok": False, "error": "unknown page"}
        return {"ok": True, "opened": target}

    try:
        answer_text, executed = llama.chat_with_tool(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tool_schema=NAVIGATE_TOOL_SCHEMA,
            tool_executor=execute_navigate,
            history=history,
        )
    except LlamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    action = None
    if executed and executed["result"].get("ok"):
        action = NavigateAction(page=executed["result"]["opened"])

    context_store.log_chat_event(session_id, req.page, req.question, answer_text, action.model_dump() if action else None)

    return AskResponse(
        answer=answer_text, action=action, grounded_on=[doc["id"]], session_id=session_id
    )
