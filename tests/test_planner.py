"""Planner end to end with labeled fake providers (tests/fakes.py). No network."""
from datetime import datetime, timezone

import pytest

from server.data.errors import DataSourceError
from server.data.mapbox import RouteCandidate, make_route_id
from server.services.planner import PlannerError, bbox_of, places_cells
from server.services.schemas import RoutesRequest
from tests import fakes

# 8 PM and 1 AM Pacific on the demo weekend (PDT = UTC-7).
EIGHT_PM = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)
ONE_AM = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)


def request(depart=EIGHT_PM, extra=10, priorities=None):
    return RoutesRequest.model_validate({
        "from": {"lat": fakes.ORIGIN[1], "lng": fakes.ORIGIN[0]},
        "to": {"lat": fakes.DEST[1], "lng": fakes.DEST[0]},
        "depart_time": depart.isoformat(),
        "settings": {"max_extra_minutes": extra, "priorities": priorities or []},
    })


def by_label(resp):
    out = {}
    for r in resp.routes:
        for label in [r.label, *r.also_labels]:
            out[label] = r
    return out


def test_returns_labeled_routes_with_contract_fields():
    resp = fakes.make_planner().plan(request())
    assert resp.api_version == "1" and resp.scoring_version == "scoring_v1"
    labels = by_label(resp)
    assert set(labels) == {"safest", "balanced", "fastest"}
    fast = labels["fastest"]
    assert fast.duration_min == 9.0 and fast.extra_min == 0
    assert fast.via == ["Marina Blvd", "Lyon St"] or set(fast.via) == {"Lyon St", "Marina Blvd"}
    seg = fast.segments[0]
    assert seg.segment_id == "s0" and seg.band in {"green", "yellow", "red", "unknown"}
    assert set(seg.factors) == {"open_places", "lighting", "main_road", "help_points",
                                "transit", "activity", "incidents", "turns"}
    assert fast.geometry.type == "LineString" and len(fast.geometry.coordinates) == 3


def test_time_awareness_coverage_drops_at_1am():
    """The demo moment: shops close, coverage falls."""
    planner = fakes.make_planner()
    night_early = by_label(planner.plan(request(EIGHT_PM)))["fastest"]
    night_late = by_label(planner.plan(request(ONE_AM)))["fastest"]
    assert night_early.continuity.coverage_pct > night_late.continuity.coverage_pct
    assert night_early.route_score > night_late.route_score
    assert night_late.continuity.longest_gap_m > night_early.continuity.longest_gap_m


def test_lit_main_road_with_late_shops_is_preferred_at_1am():
    resp = fakes.make_planner().plan(request(ONE_AM))
    labels = by_label(resp)
    assert labels["safest"].route_id != labels["fastest"].route_id
    assert labels["safest"].route_score > labels["fastest"].route_score
    assert labels["safest"].extra_min == 4.0
    assert labels["safest"].nearest_help_point.name  # a help point exists on route B


def test_extra_minutes_cap_collapses_to_the_fastest_route():
    resp = fakes.make_planner().plan(request(ONE_AM, extra=0))
    assert len(resp.routes) == 1
    r = resp.routes[0]
    assert r.label == "safest" and set(r.also_labels) == {"balanced", "fastest"}


def test_missing_places_become_not_sure_never_zero():
    planner = fakes.make_planner(places=fakes.FakePlaces(error=DataSourceError("brightdata", "HTTP 403")))
    resp = planner.plan(request())
    route = resp.routes[0]
    assert route.open_places_count is None
    assert all(s.factors["open_places"] is None for s in route.segments)
    assert any("Live business listings" in w for w in resp.warnings)
    assert resp.data_fetched_at is not None      # OpenStreetMap data still has a time


def test_partial_cell_failure_still_returns_data_with_warning():
    planner = fakes.make_planner(places=fakes.FakePlaces(partial_fail_cells=1))
    resp = planner.plan(request())
    assert any("only part of the area" in w for w in resp.warnings)
    assert resp.routes


def test_all_sources_down_still_answers_with_geometry_only():
    err = DataSourceError("x", "timed out", kind="timeout")
    planner = fakes.make_planner(places=fakes.FakePlaces(error=err), osm=fakes.FakeOsm(error=err),
                                 sf=fakes.FakeSf(error=err))
    resp = planner.plan(request())
    assert len(resp.warnings) >= 4
    assert resp.data_fetched_at is None
    assert all(s.band == "unknown" and s.confidence == "unknown"
               for s in resp.routes[0].segments)
    assert resp.routes[0].route_score is None


def test_unknown_hours_places_are_reported_not_counted():
    resp = fakes.make_planner().plan(request())
    assert any("opening hours we could not read" in w for w in resp.warnings)
    assert any(w.startswith("1 place had") for w in resp.warnings)


def test_transit_not_connected_is_stated():
    resp = fakes.make_planner().plan(request())
    assert any("Transit schedules" in w for w in resp.warnings)
    assert all(s.factors["transit"] is None for s in resp.routes[0].segments)


def test_priorities_change_the_weighting():
    base = fakes.make_planner().plan(request(EIGHT_PM))
    boosted = fakes.make_planner().plan(request(EIGHT_PM, priorities=["open_places", "lighting"]))
    b = by_label(base)["fastest"].route_score
    p = by_label(boosted)["fastest"].route_score
    assert b != p


def test_explainer_receives_facts_without_coordinates_of_the_user():
    explainer = fakes.FakeExplainer()
    fakes.make_planner(explainer=explainer).plan(request())
    facts = explainer.seen[0]
    assert {"label", "duration_min", "coverage_pct", "longest_gap_m"} <= set(facts)
    assert "geometry" not in facts and "from" not in facts


def test_gap_note_names_the_street():
    resp = fakes.make_planner().plan(request(ONE_AM))
    note = by_label(resp)["fastest"].continuity.longest_gap_note
    assert note in {"on Lyon St", "on Marina Blvd"}


@pytest.mark.parametrize(
    ("error", "code"),
    [(fakes.not_configured(), "NOT_CONFIGURED"),
     (DataSourceError("mapbox", "slow", kind="timeout"), "UPSTREAM_TIMEOUT"),
     (DataSourceError("mapbox", "HTTP 500"), "UPSTREAM_ERROR")],
)
def test_routing_failures_map_to_error_codes(error, code):
    planner = fakes.make_planner(routing=fakes.FakeRouting(error=error))
    with pytest.raises(PlannerError) as exc:
        planner.plan(request())
    assert exc.value.code == code


def test_no_route_found():
    planner = fakes.make_planner(routing=fakes.FakeRouting(candidates=[]))
    with pytest.raises(PlannerError) as exc:
        planner.plan(request())
    assert exc.value.code == "NO_ROUTE"


def test_same_start_and_destination_rejected():
    req = RoutesRequest.model_validate({
        "from": {"lat": 37.8, "lng": -122.4}, "to": {"lat": 37.8, "lng": -122.4},
        "depart_time": EIGHT_PM.isoformat()})
    with pytest.raises(PlannerError) as exc:
        fakes.make_planner().plan(req)
    assert exc.value.code == "BAD_REQUEST"


def test_trip_too_long_rejected():
    far = [(-122.45, 37.80), (-122.30, 37.80)]
    cand = RouteCandidate(make_route_id(far), far, 13000.0, 9000.0, [])
    planner = fakes.make_planner(routing=fakes.FakeRouting(candidates=[cand]))
    with pytest.raises(PlannerError) as exc:
        planner.plan(request())
    assert exc.value.code == "BAD_REQUEST" and "5 km" in exc.value.message


def test_cache_prevents_a_second_provider_call():
    places = fakes.FakePlaces()
    osm = fakes.FakeOsm()
    planner = fakes.make_planner(places=places, osm=osm)
    planner.plan(request())
    first_places, first_osm = places.calls, osm.calls
    planner.plan(request(ONE_AM))
    assert places.calls == first_places and osm.calls == first_osm


def test_helpers_bbox_and_cells():
    box = bbox_of([fakes.route_a(), fakes.route_b()])
    assert box.south < 37.8029 < box.north and box.west < -122.4484 < box.east
    cells = places_cells([fakes.ROUTE_A_COORDS, fakes.ROUTE_B_COORDS])
    assert 1 <= len(cells) <= 12
    many = [[(-122.4 + i * 0.01, 37.8) for i in range(40)]]
    assert len(places_cells(many)) == 12
