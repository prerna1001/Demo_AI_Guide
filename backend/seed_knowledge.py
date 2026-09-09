"""
One-time script: embeds every page-doc / glossary chunk and upserts them
into Supabase's `knowledge_chunks` table, so RetrievalAgent has something
real to vector-search once SUPABASE_URL / SUPABASE_KEY are set.

Run once, after applying supabase.sql in the Supabase SQL editor:

    python seed_knowledge.py

Safe to re-run — it clears and reinserts every row each time, so editing
page_docs_fallback.py (PAGE_DOCS or GLOSSARY) and re-running keeps
Supabase's knowledge_chunks in sync with it.
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()

import context_store  # noqa: E402 (import after load_dotenv so SUPABASE_* is set)
from llama_client import LlamaClient  # noqa: E402


def main() -> None:
    if not context_store.is_using_supabase():
        print(
            "SUPABASE_URL / SUPABASE_KEY aren't set in backend/.env — nothing to seed.\n"
            "The app already runs fine on the local in-memory fallback; this script is "
            "only needed once you've created a Supabase project (via supabase.sql) and "
            "want retrieval + chat history to persist there instead."
        )
        sys.exit(1)

    llama = LlamaClient()
    client = context_store._get_client()  # internal, but this script is the one place
    # outside context_store.py that's meant to own the Supabase client directly, since
    # seeding is a one-off maintenance task, not part of the request path.

    chunks = context_store.list_knowledge_chunks()
    print(f"Embedding {len(chunks)} chunks with {llama.embed_model} ...")

    client.table("knowledge_chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    rows = []
    for i, chunk in enumerate(chunks, 1):
        vector = llama.embed(chunk["content"])
        rows.append({**chunk, "embedding": vector})
        print(f"  [{i}/{len(chunks)}] {chunk['label']} ({chunk['kind']})")

    client.table("knowledge_chunks").insert(rows).execute()
    print(f"Seeded {len(rows)} knowledge chunks into Supabase.")


if __name__ == "__main__":
    main()
