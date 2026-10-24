"""Provider parsing and HTTP behaviour with httpx.MockTransport. All payloads are LABELED FIXTURES
shaped like the real APIs (Overpass, Socrata, Mapbox Directions, Anthropic). No network."""
import json
from datetime import datetime, timezone

import httpx
import pytest

from server.data.cache import TTLCache
from server.data.errors import DataSourceError, NotConfiguredError
from server.data.mapbox import (
    MapboxRoutingProvider,
    RouteCandidate,
    Step,
    dedupe,
    detour_points,
    make_route_id,
    parse_directions,
    similar,
)
from server.data.models import BoundingBox
from server.data.osm import OverpassProvider, build_query, parse_overpass
from server.data.sf_open_data import SocrataClient, parse_incidents, parse_outages, points
from server.data.transit import NoTransitProvider
from server.services.explain import ClaudeExplainer, template_explanation
from server.services.geo import haversine_m

NOW = datetime(2026, 10, 24, 22, 0, tzinfo=timezone.utc)
AREA = BoundingBox(37.80, -122.45, 37.81, -122.44)


def mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------- OpenStreetMap ----------

OVERPASS = {"elements": [
    {"type": "way", "id": 1, "tags": {"highway": "primary", "lit": "yes", "name": "Lombard St"},
     "geometry": [{"lat": 37.80, "lon": -122.45}, {"lat": 37.80, "lon": -122.44}]},
    {"type": "way", "id": 2, "tags": {"highway": "footway", "lit": "no", "tunnel": "yes"},
     "geometry": [{"lat": 37.81, "lon": -122.45}]},
    {"type": "way", "id": 3, "tags": {"highway": "service", "layer": "-1"},
     "geometry": [{"lat": 37.81, "lon": -122.45}]},
    {"type": "way", "id": 4, "tags": {"highway": "residential", "lit": "maybe"}, "geometry": []},
    {"type": "node", "id": 9, "lat": 37.805, "lon": -122.446,
     "tags": {"amenity": "police", "name": "Fixture Station"}},
    {"type": "way", "id": 10, "center": {"lat": 37.806, "lon": -122.447}, "tags": {"amenity": "hospital"}},
    {"type": "node", "id": 11, "tags": {"amenity": "fire_station"}},  # no position: skipped
    {"type": "node", "id": 12, "lat": 1, "lon": 1, "tags": {"amenity": "cafe"}},  # not help
]}


def test_parse_overpass():
    f = parse_overpass(OVERPASS, NOW)
    assert [w.way_id for w in f.ways] == [1, 2, 3]
    assert f.ways[0].lit is True and f.ways[1].lit is False and f.ways[2].lit is None
    assert f.ways[1].tunnel and f.ways[2].tunnel and not f.ways[0].tunnel
    assert {h.name for h in f.help_points} == {"Fixture Station", "Hospital"}
    assert f.fetched_at == NOW


def test_overpass_query_mentions_the_box():
    assert "(37.8,-122.45,37.81,-122.44)" in build_query(AREA)


def test_overpass_provider_sends_user_agent_and_parses():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, json=OVERPASS)

    f = OverpassProvider(client=mock_client(handler)).get_map_features(AREA)
    assert "safe-smart-maps" in seen["ua"] and len(f.ways) == 3


@pytest.mark.parametrize(
    ("response", "kind"),
    [(httpx.Response(406), "failed"), (httpx.Response(200, text="<html>"), "failed"),
     (httpx.TimeoutException("slow"), "timeout"), (httpx.ConnectError("down"), "failed")],
)
def test_overpass_errors(response, kind):
    def handler(request):
        if isinstance(response, Exception):
            raise response
        return response

    with pytest.raises(DataSourceError) as exc:
        OverpassProvider(client=mock_client(handler)).get_map_features(AREA)
    assert exc.value.kind == kind and exc.value.source == "osm"


def test_overpass_falls_back_to_the_next_server():
    hosts = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        return httpx.Response(502) if len(hosts) == 1 else httpx.Response(200, json=OVERPASS)

    f = OverpassProvider(client=mock_client(handler)).get_map_features(AREA)
    assert len(hosts) == 2 and hosts[0] != hosts[1] and len(f.ways) == 3


def test_overpass_without_servers_fails_clearly():
    with pytest.raises(DataSourceError, match="no servers"):
        OverpassProvider(urls=()).get_map_features(AREA)


# ---------- SF open data ----------

def test_parse_outages_and_incidents_skip_bad_rows():
    outages = parse_outages([
        {"lat": "37.79", "long": "-122.47", "requested_datetime": "2026-10-23"},
        {"lat": "x", "long": "y"}, {}])
    assert len(outages) == 1 and outages[0].lat == 37.79
    incidents = parse_incidents([
        {"latitude": "37.8", "longitude": "-122.4", "incident_category": "Theft"}, {"latitude": None}])
    assert len(incidents) == 1 and incidents[0].category == "Theft"
    assert points(outages) == [(-122.47, 37.79)]


def test_socrata_queries_and_parses():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "vw6y-z8j6" in request.url.path:
            return httpx.Response(200, json=[{"lat": "37.8", "long": "-122.44"}])
        return httpx.Response(200, json=[{"latitude": "37.8", "longitude": "-122.44",
                                          "incident_category": "Other"}])

    sf = SocrataClient(client=mock_client(handler))
    assert len(sf.get_open_outages(AREA)) == 1
    assert len(sf.get_recent_incidents(AREA, now=NOW)) == 1
    where = seen[0].url.params["$where"]
    assert "Streetlights" in where and "Open" in where and "within_box" in where
    assert "2026-07-26" in seen[1].url.params["$where"]  # 90 days before NOW


@pytest.mark.parametrize(
    ("response", "kind"),
    [(httpx.Response(500), "failed"), (httpx.Response(200, text="nope"), "failed"),
     (httpx.Response(200, json={"error": "x"}), "failed"), (httpx.TimeoutException("t"), "timeout"),
     (httpx.ConnectError("c"), "failed")],
)
def test_socrata_errors(response, kind):
    def handler(request):
        if isinstance(response, Exception):
            raise response
        return response

    with pytest.raises(DataSourceError) as exc:
        SocrataClient(client=mock_client(handler)).get_open_outages(AREA)
    assert exc.value.kind == kind


def test_no_transit_provider_is_unknown():
    assert NoTransitProvider().get_active_stops(AREA, NOW) is None


# ---------- Mapbox ----------

DIRECTIONS = {"routes": [
    {"distance": 700.0, "duration": 500.0,
     "geometry": {"coordinates": [[-122.4484, 37.8029], [-122.4442, 37.8029], [-122.44, 37.8029]]},
     "legs": [{"steps": [{"name": "Lyon St", "distance": 300}, {"name": "", "distance": 20},
                         {"name": "Marina Blvd", "distance": 380}]}]},
    {"distance": 0, "duration": 0, "geometry": {"coordinates": []}},   # unusable: skipped
]}


def test_parse_directions_and_via():
    routes = parse_directions(DIRECTIONS)
    assert len(routes) == 1
    r = routes[0]
    assert r.distance_m == 700 and r.coords[0] == (-122.4484, 37.8029)
    assert r.via() == ["Lyon St", "Marina Blvd"]
    assert r.via(1) == ["Marina Blvd"]
    assert r.route_id == make_route_id(r.coords) and r.route_id.startswith("r")


def test_similar_and_dedupe():
    a = RouteCandidate("a", [(-122.45, 37.80), (-122.44, 37.80)], 900, 600, [])
    same = RouteCandidate("b", [(-122.45, 37.80003), (-122.44, 37.80003)], 905, 602, [])
    other = RouteCandidate("c", [(-122.45, 37.80), (-122.445, 37.806), (-122.44, 37.80)], 1300, 900, [])
    assert similar(a, same) and not similar(a, other)
    assert [c.route_id for c in dedupe([a, same, other])] == ["a", "c"]


def test_detour_points_are_on_both_sides():
    origin, dest = (-122.45, 37.80), (-122.44, 37.80)
    left, right = detour_points(origin, dest)
    assert left[1] > 37.80 > right[1] or right[1] > 37.80 > left[1]
    assert haversine_m(left, right) > 100


def mapbox_handler(calls):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.params.get("alternatives") == "true":
            return httpx.Response(200, json=DIRECTIONS)
        detour = {"routes": [{"distance": 1100, "duration": 800, "geometry": {"coordinates": [
            [-122.4484, 37.8029], [-122.447, 37.806], [-122.44, 37.8029]]}, "legs": []}]}
        return httpx.Response(200, json=detour)
    return handler


def test_mapbox_provider_builds_candidates_and_keeps_token_in_query_only():
    calls: list[httpx.Request] = []
    p = MapboxRoutingProvider(token="fixture-token", client=mock_client(mapbox_handler(calls)))
    routes = p.get_walking_routes((-122.4484, 37.8029), (-122.44, 37.8029))
    assert len(calls) == 3                       # main + two detours
    assert len(routes) == 2                      # the two detours are the same street: deduped
    assert all("walking" in str(c.url) for c in calls)
    assert calls[0].url.params["access_token"] == "fixture-token"


def test_mapbox_requires_token(monkeypatch):
    monkeypatch.delenv("MAPBOX_TOKEN", raising=False)
    with pytest.raises(NotConfiguredError):
        MapboxRoutingProvider().get_walking_routes((0, 0), (1, 1))


def test_mapbox_main_failure_raises_and_detour_failure_is_ignored():
    def fail_main(request):
        return httpx.Response(401, json={"message": "Not Authorized - token=fixture-token"})

    p = MapboxRoutingProvider(token="fixture-token", client=mock_client(fail_main))
    with pytest.raises(DataSourceError) as exc:
        p.get_walking_routes((-122.4484, 37.8029), (-122.44, 37.8029))
    assert "fixture-token" not in str(exc.value)          # never leak the token

    def detour_fails(request):
        if request.url.params.get("alternatives") == "true":
            return httpx.Response(200, json=DIRECTIONS)
        return httpx.Response(500)

    p = MapboxRoutingProvider(token="t", client=mock_client(detour_fails))
    assert len(p.get_walking_routes((-122.4484, 37.8029), (-122.44, 37.8029))) == 1


@pytest.mark.parametrize(("exc", "kind"), [(httpx.TimeoutException("t"), "timeout"),
                                           (httpx.ConnectError("c"), "failed")])
def test_mapbox_network_errors(exc, kind):
    def handler(request):
        raise exc

    p = MapboxRoutingProvider(token="t", client=mock_client(handler))
    with pytest.raises(DataSourceError) as e:
        p.get_walking_routes((0, 0), (1, 1))
    assert e.value.kind == kind


def test_mapbox_invalid_json():
    p = MapboxRoutingProvider(token="t", client=mock_client(lambda r: httpx.Response(200, text="x")))
    with pytest.raises(DataSourceError):
        p.get_walking_routes((0, 0), (1, 1))


def test_route_candidate_without_named_steps_has_no_via():
    r = RouteCandidate("x", [(0, 0), (1, 1)], 1, 1, [Step("", 10)])
    assert r.via() == []


# ---------- Claude explainer ----------

FACTS = {"label": "safest", "duration_min": 13, "extra_min": 4, "coverage_pct": 88.0,
         "longest_gap_m": 110, "longest_gap_note": "on Lombard St", "open_places_count": 14,
         "nearest_help_point": {"name": "Fixture Station", "distance_m": 90}}


def anthropic_reply(text):
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


def test_template_mentions_facts_and_never_says_safe():
    text = template_explanation(FACTS)
    assert "88%" in text and "110 m" in text and "Fixture Station" in text and "4 min" in text
    from server.services.wording import find_banned_wording
    assert find_banned_wording(text) == []


def test_template_when_nothing_is_known():
    text = template_explanation({"coverage_pct": None, "longest_gap_m": 0, "open_places_count": None})
    assert "not sure" in text
    assert "no long stretch" in template_explanation({"coverage_pct": 95, "longest_gap_m": 0})
    assert "1 open place " in template_explanation({"coverage_pct": 95, "open_places_count": 1}) + " "


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
    httpx.Response(429), httpx.Response(200, text="not json"),
])
def test_explainer_falls_back_on_bad_or_banned_output(reply):
    text, source = ClaudeExplainer(api_key="k", client=mock_client(lambda r: reply)).explain(FACTS)
    assert source == "template" and "safest" not in text.lower()


def test_explainer_falls_back_on_network_error():
    def handler(request):
        raise httpx.ConnectError("down")

    assert ClaudeExplainer(api_key="k", client=mock_client(handler)).explain(FACTS)[1] == "template"


# ---------- cache ----------

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
        raise DataSourceError("x", "failed")

    with pytest.raises(DataSourceError):
        cache.get_or_load("bad", boom)
    assert cache.get("bad") == (False, None)
    cache.set("a", 1)
    cache.set("b", 2)      # evicts the oldest (max_items=2)
    assert sum(cache.get(k)[0] for k in ["k", "a", "b", "bad"]) == 2
    cache.clear()
    assert cache.get("a") == (False, None)
