"""
Thin client for an OpenAI-chat-completions-shaped Llama endpoint.

Ollama (https://ollama.com), vLLM, Together, Groq and Fireworks all speak
this same shape for Llama models, tool calls included — which is why this
file has no vendor-specific logic. Point LLAMA_BASE_URL at whichever one
you're running and nothing else in the backend has to change.

Deliberately not using an agent framework here: this is one call, with an
optional one-shot tool round-trip (the model asks to navigate, we execute
it, we ask once more for the final sentence). A single-agent, single-tool
loop is the whole job — see the README for why multi-agent isn't warranted.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

import requests


class LlamaError(RuntimeError):
    pass


class LlamaClient:
    def __init__(self):
        self.base_url = os.getenv("LLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.model = os.getenv("LLAMA_MODEL", "llama3.1")
        self.api_key = os.getenv("LLAMA_API_KEY", "ollama")

    def _post(self, messages: list[dict[str, Any]], tools: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise LlamaError(
                f"Couldn't reach a Llama endpoint at {self.base_url}. "
                "Is Ollama running ('ollama serve') with the model pulled "
                f"('ollama pull {self.model}')?"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            body = ""
            try:
                body = resp.text[:500]
            except Exception:
                pass
            raise LlamaError(f"Llama endpoint returned an error: {exc} — body: {body}") from exc

        return resp.json()

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """One plain call, no tools — for small, fast jobs like the scope
        guard (classify, don't answer). Deliberately separate from
        chat_with_tool so a classification call can never accidentally pick
        up tool-calling behavior."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        resp = self._post(messages)
        return resp["choices"][0]["message"].get("content", "").strip()

    def chat_with_tool(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_schema: dict[str, Any],
        tool_executor: Callable[[dict[str, Any]], dict[str, Any]],
        history: Optional[list[dict[str, str]]] = None,
    ) -> tuple[str, Optional[dict[str, Any]]]:
        """
        Runs one turn, letting the model call `tool_schema` at most once.
        `history` is prior (question, answer) turns from this same session —
        each becomes a user/assistant pair inserted before the current
        question, so a follow-up like "what about that" has something to
        refer to. Passing more than a handful of turns is a false economy:
        it doesn't make answers more grounded, just slower and pricier.
        Returns (final_answer_text, executed_tool_call_or_None).
        """
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history or []:
            messages.append({"role": "user", "content": turn["question"]})
            messages.append({"role": "assistant", "content": turn["answer"]})
        messages.append({"role": "user", "content": user_prompt})

        first = self._post(messages, tools=[tool_schema])
        choice = first["choices"][0]["message"]
        tool_calls = choice.get("tool_calls") or []

        if not tool_calls:
            return choice.get("content", "").strip(), None

        call = tool_calls[0]
        try:
            args = json.loads(call["function"]["arguments"])
        except (KeyError, json.JSONDecodeError):
            args = {}

        tool_result = tool_executor(args)

        # Rebuild a minimal assistant message instead of reusing the raw
        # response object verbatim — some OpenAI-compatible endpoints
        # (Cloudflare Workers AI included) reject content: null and the
        # extra vendor-specific fields (annotations, audio, reasoning, ...)
        # that come back on a tool-call response.
        messages.append(
            {
                "role": "assistant",
                "content": choice.get("content") or "",
                "tool_calls": tool_calls,
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", "call_0"),
                "content": json.dumps(tool_result),
            }
        )
        second = self._post(messages)
        final_text = second["choices"][0]["message"].get("content", "").strip()

        executed = {"name": call["function"]["name"], "arguments": args, "result": tool_result}
        return final_text or "Done.", executed
