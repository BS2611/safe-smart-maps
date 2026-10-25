"""Street auditor and the explainer provider switch. Model answers are labeled hand-written FIXTURES."""
import json

import httpx
import pytest

from server.services.audit import Photo, StreetAuditor, parse_audit
from server.services.explain import ClaudeExplainer, OpenAICompatExplainer, build_explainer

PHOTO = Photo(id="img-1", jpeg=b"\xff\xd8fixture", captured_at="2024-05-01", attribution="CC BY-SA fixture")
GOOD = {"streetlights_visible": "yes", "open_storefronts": "no", "sidewalk_visibility": "good",
        "construction": "no", "confidence": "medium", "evidence": "Two lamp posts and a clear sidewalk."}
FACTS = {"coverage_pct": 80, "longest_gap_m": 120, "open_places_count": 3, "extra_min": 2}


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def reply(obj_or_text):
    text = obj_or_text if isinstance(obj_or_text, str) else json.dumps(obj_or_text)
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


def test_parse_accepts_good_json_even_with_extra_text():
    audit = parse_audit("Here you go: " + json.dumps(GOOD), PHOTO)
    assert audit.streetlights_visible == "yes" and audit.photo_id == "img-1"
    assert "daytime" in audit.label and audit.attribution == "CC BY-SA fixture"


@pytest.mark.parametrize("bad", [
    "not json", "[]", {**GOOD, "confidence": "certain"}, {**GOOD, "streetlights_visible": True},
    {**GOOD, "evidence": ""}, {**GOOD, "evidence": "This is a safe street."}, {k: v for k, v in GOOD.items() if k != "construction"},
])
def test_parse_rejects_odd_answers(bad):
    text = bad if isinstance(bad, str) else json.dumps(bad)
    assert parse_audit(text, PHOTO) is None


def test_auditor_sends_image_and_returns_audit():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return reply(GOOD)

    audit = StreetAuditor(api_key="fixture-key", client=client(handler)).audit(PHOTO)
    assert audit is not None
    content = seen["body"]["messages"][0]["content"]
    assert content[0]["type"] == "image" and content[0]["source"]["media_type"] == "image/jpeg"
    assert seen["body"]["thinking"] == {"type": "disabled"}


def test_auditor_caches_by_photo_id_and_respects_cap():
    calls = []

    def handler(request):
        calls.append(1)
        return reply(GOOD)

    auditor = StreetAuditor(api_key="k", max_calls=1, client=client(handler))
    assert auditor.audit(PHOTO) is not None and auditor.audit(PHOTO) is not None
    assert len(calls) == 1
    assert auditor.audit(Photo(id="img-2", jpeg=b"x")) is None      # cap reached
    assert len(calls) == 1


def test_auditor_without_key_or_on_errors_returns_none(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert StreetAuditor(client=client(lambda r: reply(GOOD))).audit(PHOTO) is None
    for bad in (httpx.Response(500), httpx.Response(200, text="oops")):
        assert StreetAuditor(api_key="k", client=client(lambda r, b=bad: b)).audit(PHOTO) is None

    def boom(request):
        raise httpx.ConnectError("down")

    assert StreetAuditor(api_key="k", client=client(boom)).audit(PHOTO) is None


def test_audit_near_without_photo_source_is_none():
    assert StreetAuditor(api_key="k").audit_near(None, 37.8, -122.4) is None


def test_openai_compat_explainer_ok_and_fallbacks():
    def ok(request):
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(200, json={"choices": [{"message": {"content": "Better lit and more active."}}]})

    ex = OpenAICompatExplainer(base_url="http://local:11434/v1", model="qwen", client=client(ok))
    assert ex.explain(FACTS) == ("Better lit and more active.", "ai")
    banned = httpx.Response(200, json={"choices": [{"message": {"content": "This route is safe."}}]})
    for bad in (banned, httpx.Response(500), httpx.Response(200, json={"oops": 1})):
        got = OpenAICompatExplainer(base_url="http://x/v1", model="m", client=client(lambda r, b=bad: b)).explain(FACTS)
        assert got[1] == "template"
    assert OpenAICompatExplainer(base_url="", model="").explain(FACTS)[1] == "template"   # not configured


def test_build_explainer_switch(monkeypatch):
    monkeypatch.delenv("EXPLAINER_PROVIDER", raising=False)
    assert isinstance(build_explainer(), ClaudeExplainer)
    monkeypatch.setenv("EXPLAINER_PROVIDER", "openai_compat")
    assert isinstance(build_explainer(), OpenAICompatExplainer)
    monkeypatch.setenv("EXPLAINER_PROVIDER", "something-else")
    assert isinstance(build_explainer(), ClaudeExplainer)
