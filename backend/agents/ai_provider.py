"""
AI provider abstraction (§44).

    AIProvider
     ├── MockAIProvider   — no API key required; deterministic, grounded
     └── LLMProvider      — calls a hosted model when LLM_API_KEY is set

Both receive the *same* thing: a system prompt, the consent-filtered context
block, and a deterministic `grounded_draft` composed by the role agent from
the retrieved records. The mock provider returns that draft; the LLM provider
asks the model to rewrite it in the role's register and falls back to the
draft on any error. Neither provider ever sees unauthorised records, and
neither is allowed to add clinical facts that are not in the context.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from config import AI_PROVIDER, LLM_API_KEY, LLM_API_URL, LLM_MODEL

SAFETY_RULES = (
    "You are part of a clinical health-memory system. Absolute rules:\n"
    "- Use ONLY the retrieved health memory provided below. Never invent a "
    "medication, dose, diagnosis, doctor, date or result.\n"
    "- If the answer is not in the context, say the information is not in the "
    "health memory.\n"
    "- Never prescribe, never change treatment, never give a diagnosis.\n"
    "- Keep patient-reported information clearly separate from "
    "doctor-recorded or reviewer-verified information.\n"
    "- Never present OCR-extracted information that is pending verification "
    "as confirmed fact.\n"
    "- Refer to the evidence by its provenance label where it matters."
)


class AIProvider:
    name = "AIProvider"
    available = False

    def generate(
        self,
        system_prompt: str,
        context_text: str,
        question: str,
        grounded_draft: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class MockAIProvider(AIProvider):
    """
    Deterministic provider used when no model API key is configured.

    It does not fabricate: the answer is composed by the role agent directly
    from the retrieved health-memory records, so the demo behaves correctly
    end-to-end with zero external dependencies.
    """

    name = "MockAIProvider"
    available = True

    def generate(self, system_prompt, context_text, question, grounded_draft,
                 history=None) -> Dict[str, Any]:
        answer = (grounded_draft or "").strip()
        if not answer:
            answer = (
                "I could not find anything in the authorized health memory that "
                "answers that. Nothing has been assumed or invented."
            )
        return {"answer": answer, "provider": self.name, "model": "deterministic"}


class LLMProvider(AIProvider):
    """Hosted-model provider. Used only when LLM_API_KEY is present."""

    name = "LLMProvider"

    def __init__(self):
        self.available = bool(LLM_API_KEY)

    def generate(self, system_prompt, context_text, question, grounded_draft,
                 history=None) -> Dict[str, Any]:
        if not self.available:
            return MockAIProvider().generate(
                system_prompt, context_text, question, grounded_draft, history
            )

        user_content = (
            f"QUESTION: {question}\n\n"
            f"{context_text}\n\n"
            f"A grounded draft answer assembled directly from the records above:\n"
            f"{grounded_draft}\n\n"
            "Rewrite the draft in the register described in your instructions. "
            "Do not add any clinical fact that is not in the records above."
        )
        payload = {
            "model": LLM_MODEL,
            "max_tokens": 1200,
            "system": f"{system_prompt}\n\n{SAFETY_RULES}",
            "messages": [
                *[
                    {"role": turn.get("role", "user"), "content": turn.get("content", "")}
                    for turn in (history or [])[-6:]
                ],
                {"role": "user", "content": user_content},
            ],
        }
        request = urllib.request.Request(
            LLM_API_URL,
            data=json.dumps(payload).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode())
            blocks = data.get("content") or []
            text = "".join(
                block.get("text", "") for block in blocks if isinstance(block, dict)
            ).strip()
            if not text:
                raise ValueError("Empty model response")
            return {"answer": text, "provider": self.name, "model": LLM_MODEL}
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError, OSError):
            fallback = MockAIProvider().generate(
                system_prompt, context_text, question, grounded_draft, history
            )
            fallback["provider"] = f"{self.name} (unavailable — grounded fallback)"
            return fallback


def get_provider() -> AIProvider:
    if AI_PROVIDER == "mock":
        return MockAIProvider()
    if AI_PROVIDER == "llm":
        return LLMProvider()
    provider = LLMProvider()
    return provider if provider.available else MockAIProvider()


def provider_status() -> Dict[str, Any]:
    provider = get_provider()
    return {
        "provider": provider.name,
        "configured": AI_PROVIDER,
        "llm_key_present": bool(LLM_API_KEY),
        "model": LLM_MODEL if isinstance(provider, LLMProvider) else "deterministic",
    }
