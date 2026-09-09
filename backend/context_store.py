"""
Waypoint's context layer.

"Context awareness" for a page-scoped assistant is really three things:
  1) durable knowledge about what each page is/needs (page_docs)
  2) what was actually said earlier in this conversation, so a follow-up
     question doesn't reset to zero (chat_events, read back as history)
  3) a way for a user to come back and see a past chat (chat_events, read
     back as a transcript)

Supabase is a reasonable place to put all three: it's a Postgres table away
from being queryable by the product team, needs no separate service to run,
and row-level security can scope it per workspace later. This module talks
to Supabase when it's configured (SUPABASE_URL / SUPABASE_KEY set — see
supabase.sql for the schema) and falls back to in-process memory otherwise,
so `uvicorn main:app` works with zero external services. The tradeoff of
the fallback: it only lives as long as this process does — restart the
server and history is gone. Filling in the two env vars removes that
limitation with no code change anywhere else.

If/when the retrieval need grows past "one doc per page" (e.g. searching
release notes, past incidents), this is the seam where a real vector search
over a Supabase `pgvector` column would slot in without touching main.py.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from page_docs_fallback import PAGE_DOCS

_supabase_client = None
_supabase_enabled = False

# In-process fallback chat log, keyed by session_id, each entry shaped like
# a chat_events row. Only used when Supabase isn't configured.
_local_chat_log: dict[str, list[dict[str, Any]]] = {}


def _get_client():
    global _supabase_client, _supabase_enabled
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        return None

    try:
        from supabase import Client, create_client
    except ImportError:
        # supabase-py isn't installed in this environment — fall back quietly.
        return None

    _supabase_client = create_client(url, key)
    _supabase_enabled = True
    return _supabase_client


def is_using_supabase() -> bool:
    return _get_client() is not None


def new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


def get_page_doc(page_id: str) -> Optional[dict[str, Any]]:
    client = _get_client()
    if client is not None:
        try:
            res = client.table("page_docs").select("*").eq("id", page_id).limit(1).execute()
            if res.data:
                return res.data[0]
        except Exception:
            # Table missing, network hiccup, RLS denial, etc — degrade to the
            # local copy instead of failing the request.
            pass

    doc = PAGE_DOCS.get(page_id)
    if doc is None:
        return None
    return {"id": page_id, **doc}


def list_page_docs() -> list[dict[str, Any]]:
    client = _get_client()
    if client is not None:
        try:
            res = client.table("page_docs").select("*").execute()
            if res.data:
                return res.data
        except Exception:
            pass
    return [{"id": pid, **doc} for pid, doc in PAGE_DOCS.items()]


def log_chat_event(session_id: str, page: str, question: str, answer: str, action: Optional[dict]) -> None:
    """Record one turn. Always kept in the in-process log (so history works
    even with zero external services); mirrored to Supabase when configured
    so it survives a restart and is queryable outside the process."""
    row = {
        "session_id": session_id,
        "page": page,
        "question": question,
        "answer": answer,
        "action": action,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _local_chat_log.setdefault(session_id, []).append(row)

    client = _get_client()
    if client is None:
        return
    try:
        client.table("chat_events").insert(row).execute()
    except Exception:
        pass


def get_recent_history(session_id: str, limit: int = 6) -> list[dict[str, Any]]:
    """Last `limit` turns for this session, oldest first — meant to be fed
    back to the model as conversation context, not shown to a user."""
    client = _get_client()
    if client is not None:
        try:
            res = (
                client.table("chat_events")
                .select("question,answer,created_at")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if res.data:
                return list(reversed(res.data))
        except Exception:
            pass

    rows = _local_chat_log.get(session_id, [])
    return rows[-limit:]


def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    """Full transcript for a session, oldest first — meant for a user to
    read back later, unlike get_recent_history which is model input."""
    client = _get_client()
    if client is not None:
        try:
            res = (
                client.table("chat_events")
                .select("page,question,answer,action,created_at")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .execute()
            )
            if res.data:
                return res.data
        except Exception:
            pass

    return _local_chat_log.get(session_id, [])
