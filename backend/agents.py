"""
Waypoint's agent pipeline.

Four specialized agents run in a fixed sequence for every question — this
is a *sequential multi-agent pipeline* (each stage has one job, its own
model call, and passes a structured result to the next), not a group of
autonomous peers that negotiate or delegate to each other. That distinction
is worth stating plainly because it's a deliberate choice, not a
simplification: every question here follows the same fixed path (classify
-> retrieve -> answer -> verify) with no branching between independent
goals, so a sequential pipeline is the correct shape — it's simpler to
reason about and debug than peer-to-peer agents, with no loss of
capability for this problem.

  1. ScopeGuardAgent      - is this question in scope? (classify-only call)
  2. RetrievalAgent        - RAG: embeds the question, vector-searches
                            Supabase (pgvector) or the local fallback for
                            the most relevant page/glossary chunks
  3. AnsweringAgent         - drafts the answer from the retrieved chunks +
                            live project state + session history, and may
                            call the `navigate` tool
  4. GroundingGuardAgent    - does the drafted answer only state things the
                            retrieved chunks/state actually support? A
                            second, independent classify-only call — this
                            is what makes "grounded, not hallucinated" an
                            enforced property instead of just a prompt
                            instruction the main call might ignore.

Each agent takes the LlamaClient it needs and nothing else, so any one of
them could be swapped, tested, or run on a different model without
touching the others — that's the actual benefit "multi-agent" is supposed
to buy you, and it's true here even though the orchestration itself is a
plain sequential call chain in main.py, not an agent framework.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from llama_client import LlamaClient, LlamaError


class ScopeGuardAgent:
    """Decides in/out of scope. Never answers the user itself, and never
    generates the answer — that's a separation of duties, not a shortcut."""

    def __init__(self, llama: LlamaClient):
        self.llama = llama

    def classify(self, question: str, doc: dict, history: list[dict]) -> bool:
        context_hint = ""
        if history:
            last = history[-1]
            context_hint = f'Most recent exchange — Q: "{last["question"]}" A: "{last["answer"]}"\n\n'

        system = (
            "You are a scope guard for Waypoint, an AI guide embedded in a software product. "
            "You only decide whether a question is in scope — you never answer it. Give the "
            "user the benefit of the doubt: an odd phrasing, a typo, or a question that names "
            "a specific feature/rule/term you don't recognize is still IN SCOPE if it could "
            "plausibly be about using, understanding, or troubleshooting this product or the "
            "page they're on — including follow-ups to the recent exchange below. Only say NO "
            "when the question is clearly about something else entirely: general trivia, a "
            "different product, or a personal request. Reply with exactly one word: YES or NO."
        )
        user = (
            f"PAGE: {doc['title']} — {doc['purpose']}\n"
            f"{context_hint}"
            f'QUESTION: "{question}"\n'
            "In scope? Reply YES or NO only."
        )
        try:
            verdict = self.llama.complete(system, user)
        except LlamaError:
            return True  # fail open — an infra hiccup shouldn't look like a decline
        return re.search(r"\bno\b", verdict.strip(), re.IGNORECASE) is None


class RetrievalAgent:
    """RAG: turns a question into the handful of knowledge chunks that
    actually back an answer, via embedding + vector search — real
    retrieval, not a static dump of every doc into every prompt."""

    def __init__(self, llama: LlamaClient, context_store_module: Any):
        self.llama = llama
        self.store = context_store_module

    def retrieve(self, question: str, top_k: int = 5) -> list[dict]:
        try:
            query_embedding = self.llama.embed(question)
        except LlamaError:
            # Can't embed right now — fail open to "no retrieved chunks";
            # the Answering Agent still has project_state/history to work
            # with, and will say so rather than invent page content.
            return []
        return self.store.search_knowledge(query_embedding, self.llama.embed, top_k=top_k)


class AnsweringAgent:
    """Drafts the answer from retrieved chunks (not the full page-doc set),
    and may call `navigate` — always alongside a real answer, never instead
    of one."""

    def __init__(self, llama: LlamaClient, tool_schema: dict, known_pages: list[str]):
        self.llama = llama
        self.tool_schema = tool_schema
        self.known_pages = known_pages

    def answer(
        self,
        question: str,
        current_page_id: str,
        current_page_prereq: str,
        chunks: list[dict],
        project_state: dict,
        history: list[dict],
    ) -> tuple[str, Optional[dict]]:
        if chunks:
            retrieved_text = "\n".join(
                f"- ({c['page_id']}/{c['kind']}) {c['content']}" for c in chunks
            )
        else:
            retrieved_text = (
                "(retrieval returned nothing relevant — answer only from live project "
                "state below, and say plainly if that isn't enough to answer)"
            )

        system = (
            "You are Waypoint, a contextual AI guide embedded inside a software product. "
            "You answer ONE focused question at a time using only the RETRIEVED CONTEXT and "
            "LIVE PROJECT STATE given to you — never invent data that isn't there. Answer in "
            "2-4 sentences, be concrete and specific, and if you're not certain of a root "
            "cause say so plainly instead of guessing.\n\n"
            "The retrieved context may point at a different page than the one the user is "
            "currently on. Answer using whichever page's content actually answers the "
            "question. NEVER respond with only 'I moved you to X, look there' and no "
            "substantive answer — that is not an answer. If moving the user to the page "
            "that actually has the answer would help, call the `navigate` tool AND give the "
            "real answer in the same response; the tool result does not replace answering."
        )
        user = (
            f"CURRENT PAGE: {current_page_id}\n"
            f"WHAT HAS TO BE TRUE FIRST ON THIS PAGE: {current_page_prereq}\n\n"
            f"RETRIEVED CONTEXT (top matches for this question, via vector search):\n{retrieved_text}\n\n"
            f"LIVE PROJECT STATE (JSON): {project_state}\n\n"
            f'USER QUESTION: "{question}"'
        )

        def execute_navigate(args: dict) -> dict:
            target = args.get("page")
            if target not in self.known_pages:
                return {"ok": False, "error": "unknown page"}
            return {"ok": True, "opened": target}

        answer_text, executed = self.llama.chat_with_tool(
            system_prompt=system,
            user_prompt=user,
            tool_schema=self.tool_schema,
            tool_executor=execute_navigate,
            history=history,
        )
        return answer_text, executed


class GroundingGuardAgent:
    """Second guardrail: a post-hoc, independent check that the drafted
    answer stayed inside what the retrieved chunks/project state actually
    said. This is what turns 'grounded, not hallucinated' into something
    enforced rather than a system-prompt instruction the answering call
    might quietly ignore. Biased toward YES for the same reason
    ScopeGuardAgent is: this is a coarse check, not a fact-checker, so it
    only catches an answer that plainly invented something with no basis
    anywhere in the context it was given."""

    def __init__(self, llama: LlamaClient):
        self.llama = llama

    def verify(self, answer: str, chunks: list[dict], project_state: dict) -> bool:
        context_text = "\n".join(c["content"] for c in chunks) or "(none retrieved)"
        system = (
            "You check whether a drafted answer stayed grounded in the context it was given, "
            "or invented something with no basis in it. Give the benefit of the doubt: a "
            "reasonable inference, a paraphrase, or a plain 'I don't know' all count as "
            "GROUNDED. Only flag NOT if the answer states a specific fact, number, or claim "
            "that contradicts or has no basis anywhere in the context or project state. "
            "Reply with exactly one word: GROUNDED or NOT."
        )
        user = (
            f"CONTEXT GIVEN TO THE ANSWERER:\n{context_text}\n\n"
            f"PROJECT STATE (JSON): {project_state}\n\n"
            f'DRAFTED ANSWER: "{answer}"\n'
            "Grounded? Reply GROUNDED or NOT only."
        )
        try:
            verdict = self.llama.complete(system, user)
        except LlamaError:
            return True  # fail open — same bias as ScopeGuardAgent, and for the same reason
        return re.search(r"\bnot\b", verdict.strip(), re.IGNORECASE) is None
