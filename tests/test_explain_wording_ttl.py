"""Explanations (Claude + template fallback), wording rules and the in-memory TTL cache.
Anthropic answers are hand-written FIXTURES via httpx.MockTransport. No network."""
import json

import httpx
import pytest

from server.data.ttl_cache import TTLCache
from server.services.explain import ClaudeExplainer, template_explanation
from server.services.wording import find_banned_wording

FACTS = {"label": "safest", "duration_min": 13, "extra_min": 4, "coverage_pct": 88.0,
         "longest_gap_m": 110, "longest_gap_note": "on Lombard St", "open_places_count": 14,
         "nearest_help_point": {"name": "Fixture Station", "distance_m": 90}}


def mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def anthropic_reply(text):
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


# ---------- template ----------

def test_template_mentions_facts_and_never_says_safe():
    text = template_explanation(FACTS)
    assert "88%" in text and "110 m" in text and "Fixture Station" in text and "4 min" in text
    assert find_banned_wording(text) == []


def test_template_when_nothing_is_known():
    text = template_explanation({"coverage_pct": None, "longest_gap_m": 0, "open_places_count": None})
    assert "not sure" in text
    assert "no long stretch" in template_explanation({"coverage_pct": 95, "longest_gap_m": 0})
    assert "1 open place " in template_explanation({"coverage_pct": 95, "open_places_count": 1}) + " "


def test_template_plural_and_zero_extra_minutes():
    assert "2 open places" in template_explanation({"coverage_pct": 50, "open_places_count": 2})
    assert "adds about" not in template_explanation({"coverage_pct": 50, "extra_min": 0})


# ---------- Claude explainer ----------

def test_explainer_without_key_uses_template(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, source = ClaudeExplainer().explain(FACTS)
    assert source == "template" and text


def test_explainer_uses_ai_text_when_clean():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"], seen["body"] = request.headers, json.loads(request.content)
        return anthropic_reply("This route is better lit and more active, with a short quiet stretch.")

    text, source = ClaudeExplainer(api_key="fixture-key", client=mock_client(handler)).explain(FACTS)
    assert source == "ai" and "better lit" in text
    assert seen["headers"]["x-api-key"] == "fixture-key"
    assert "Never say a route is safe" in seen["body"]["system"]
    assert json.loads(seen["body"]["messages"][0]["content"])["coverage_pct"] == 88.0


@pytest.mark.parametrize("reply", [
    anthropic_reply("This is the safest route."),
    anthropic_reply("This route is safe to walk."),
    anthropic_reply(""),
    httpx.Response(429), httpx.Response(500), httpx.Response(200, text="not json"),
])
def test_explainer_falls_back_on_bad_or_banned_output(reply):
    text, source = ClaudeExplainer(api_key="k", client=mock_client(lambda r: reply)).explain(FACTS)
    assert source == "template" and "safest" not in text.lower()


@pytest.mark.parametrize("error", [httpx.ConnectError("down"), httpx.ReadTimeout("slow")])
def test_explainer_falls_back_on_network_error(error):
    def handler(request):
        raise error

    assert ClaudeExplainer(api_key="k", client=mock_client(handler)).explain(FACTS)[1] == "template"


def test_explainer_key_is_never_in_the_returned_text():
    text, _ = ClaudeExplainer(api_key="secret-fixture-key", client=mock_client(
        lambda r: httpx.Response(401))).explain(FACTS)
    assert "secret-fixture-key" not in text


# ---------- wording ----------

def test_wording_allowed_phrases():
    assert find_banned_wording("Welcome to Safe Smart Maps") == []
    assert find_banned_wording("We do not guarantee safety. In an emergency, call 911.") == []
    assert find_banned_wording("Better lit and more active; not sure about transit.") == []


def test_wording_flags_banned_phrases():
    for text in ["this route is safe", "the safest route", "Hazard report", "a dangerous alley",
                 "crime-free", "we guarantee this", "walk safely"]:
        assert find_banned_wording(text), text


# ---------- ttl cache ----------

def test_cache_ttl_and_failures_not_cached():
    now = [0.0]
    cache = TTLCache(ttl_seconds=10, clock=lambda: now[0], max_items=2)
    calls = []
    assert cache.get_or_load("k", lambda: calls.append(1) or "v") == "v"
    assert cache.get_or_load("k", lambda: calls.append(1) or "other") == "v"
    assert len(calls) == 1 and cache.hits == 1
    now[0] = 11
    assert cache.get_or_load("k", lambda: "fresh") == "fresh"

    def boom():
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError):
        cache.get_or_load("bad", boom)
    assert cache.get("bad") == (False, None)
    cache.set("a", 1)
    cache.set("b", 2)      # evicts the oldest (max_items=2)
    assert sum(cache.get(k)[0] for k in ["k", "a", "b", "bad"]) == 2
    cache.clear()
    assert cache.get("a") == (False, None)
