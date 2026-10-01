
import json
import re
from typing import Optional

from app.config import settings

_client = None


def _get_client():
    global _client
    if _client is None and settings.llm_enabled:
        import anthropic
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def is_live() -> bool:
    return settings.llm_enabled


def complete(system: str, prompt: str, max_tokens: int = 1024) -> str:
    """Return raw text completion. Falls back to a deterministic stub when
    no ANTHROPIC_API_KEY is set, so the whole pipeline still runs end to end."""
    client = _get_client()
    if client is None:
        return _stub_response(system, prompt)

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
    return "\n".join(parts).strip()


_JSON_MARKER = "Respond with ONLY a single valid JSON object."


def complete_json(system: str, prompt: str, max_tokens: int = 1024) -> dict:
    """Ask the model for strict JSON and parse it defensively, since LLMs
    occasionally wrap JSON in prose or code fences."""
    json_system = system + f"\n\n{_JSON_MARKER} No prose, no markdown code fences, no explanation."
    raw = complete(json_system, prompt, max_tokens=max_tokens)
    return _extract_json(raw)


def _extract_json(raw: str) -> dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"LLM did not return parseable JSON. Raw output:\n{raw}")


# ---------------------------------------------------------------------------
# Offline fallback so `uvicorn app.main:app` works with zero configuration.
# Each stub is intentionally simple and clearly labelled as a fallback.
# ---------------------------------------------------------------------------
def _stub_response(system: str, prompt: str) -> str:
    # complete_json() always appends _JSON_MARKER to the system prompt, so this
    # check is unambiguous regardless of what words appear elsewhere in the prompt.
    if _JSON_MARKER in system:
        return json.dumps({
            "root_cause": "LLM offline (no ANTHROPIC_API_KEY set) — showing rule-based summary of the retrieved data only.",
            "summary": "Set ANTHROPIC_API_KEY in .env to enable full reasoning by the Decision Agent.",
            "recommendations": [
                {
                    "action": "Configure ANTHROPIC_API_KEY",
                    "rationale": "The Decision Agent needs an LLM to synthesize root causes and recommendations.",
                    "priority": "medium",
                    "expected_impact": "Unlocks full autonomous reasoning.",
                    "action_type": "notify",
                }
            ],
            "confidence": 0.2,
        })
    if "SQL" in system:
        return "SELECT 1 AS note WHERE 0;  -- no ANTHROPIC_API_KEY configured, SQL Agent stubbed"
    return "LLM offline: set ANTHROPIC_API_KEY in your .env file for live reasoning."
