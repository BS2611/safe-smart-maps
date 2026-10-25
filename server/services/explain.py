"""Plain-language route explanation. Claude when configured, a fixed template otherwise.

The model only rewords facts we computed; it is told not to add facts or promise safety, and its
output is checked with the wording rules before use. Raw API errors never reach the user.
"""
import json
import os

import httpx

from server.services.wording import find_banned_wording

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-haiku-5-5"
SYSTEM_PROMPT = (
    "You explain walking routes for people walking at night. Use ONLY the facts in the JSON. "
    "Write 2 or 3 short plain sentences. Never say a route is safe or dangerous; say "
    "'better lit and more active' or 'quieter' and describe conditions. If a value is null, say "
    "we are not sure about it. Mention the longest quiet stretch if there is one. No markdown."
)


def template_explanation(facts: dict) -> str:
    parts = []
    coverage = facts.get("coverage_pct")
    if coverage is None:
        parts.append("We are not sure how active this route is, because some data was not available.")
    else:
        parts.append(f"{round(coverage)}% of this walk stays near an open place.")
    gap = facts.get("longest_gap_m")
    if gap:
        note = f" {facts['longest_gap_note']}" if facts.get("longest_gap_note") else ""
        parts.append(f"The longest quiet stretch is about {round(gap)} m{note}.")
    elif coverage is not None:
        parts.append("There is no long stretch without something nearby.")
    count = facts.get("open_places_count")
    if count is not None:
        parts.append(f"{count} open place{'s' if count != 1 else ''} along the way.")
    help_point = facts.get("nearest_help_point")
    if help_point:
        parts.append(f"Nearest help point: {help_point['name']}, {round(help_point['distance_m'])} m away.")
    extra = facts.get("extra_min")
    if extra:
        parts.append(f"It adds about {round(extra)} min compared with the fastest route.")
    return " ".join(parts)


class ClaudeExplainer:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout_s: float = 8.0,
                 client: httpx.Client | None = None):
        self._api_key = api_key
        # `or`, not a default argument: .env.example ships ANTHROPIC_MODEL= (empty), which would
        # otherwise send model "" and get a 400 on every request.
        self.model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.timeout_s = timeout_s
        self._client = client

    def explain(self, facts: dict) -> tuple[str, str]:
        """(text, source) where source is "ai" or "template". Never raises."""
        fallback = (template_explanation(facts), "template")
        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return fallback
        body = {
            # Haiku 5.5 thinks by default; with a 220-token cap the reply was only a thinking block.
            "model": self.model, "max_tokens": 220, "thinking": {"type": "disabled"},
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": json.dumps(facts, default=str)}],
        }
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        try:
            resp = (self._client or httpx).post(ANTHROPIC_URL, json=body, headers=headers,
                                                timeout=self.timeout_s)
            if resp.status_code != 200:
                return fallback
            text = "".join(b.get("text", "") for b in resp.json().get("content", [])
                           if b.get("type") == "text").strip()
        except (httpx.HTTPError, ValueError):
            return fallback
        if not text or find_banned_wording(text):
            return fallback
        return text, "ai"


class OpenAICompatExplainer:
    """Optional alternative model (Qwen via an OpenAI-style endpoint, a local Ollama, ...).

    Same job and same guardrails as ClaudeExplainer: facts in, 2-3 sentences out, wording filter,
    template fallback, never raises. Needs EXPLAINER_BASE_URL (ending before /chat/completions).
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None,
                 timeout_s: float = 15.0, client: httpx.Client | None = None):
        self.base_url = (base_url or os.environ.get("EXPLAINER_BASE_URL") or "").rstrip("/")
        self._api_key = api_key or os.environ.get("EXPLAINER_API_KEY")
        self.model = model or os.environ.get("EXPLAINER_MODEL") or ""
        self.timeout_s = timeout_s
        self._client = client

    def explain(self, facts: dict) -> tuple[str, str]:
        fallback = (template_explanation(facts), "template")
        if not self.base_url or not self.model:
            return fallback
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        body = {"model": self.model, "max_tokens": 220, "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(facts, default=str)}]}
        try:
            resp = (self._client or httpx).post(f"{self.base_url}/chat/completions", json=body,
                                                headers=headers, timeout=self.timeout_s)
            if resp.status_code != 200:
                return fallback
            text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            return fallback
        if not text or find_banned_wording(text):
            return fallback
        return text, "ai"


def build_explainer():
    """EXPLAINER_PROVIDER=claude (default) or openai_compat. Unknown values use Claude."""
    if (os.environ.get("EXPLAINER_PROVIDER") or "claude").strip().lower() == "openai_compat":
        return OpenAICompatExplainer()
    return ClaudeExplainer()
