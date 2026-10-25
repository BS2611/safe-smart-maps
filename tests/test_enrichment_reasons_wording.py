"""Enrichment (providers -> per-segment evidence), reasons and wording rules. Pure, no network."""
from datetime import datetime, timedelta, timezone

from server.data.osm import MapFeatures, Way
from server.data.sf_open_data import Incident, Outage
from server.data.transit import ActiveStop
from server.services.enrichment import DataBundle, build_route_facts, help_points_from
from server.services.reasons import segment_reasons
from server.services.scoring import Evidence
from server.services.scoring_config import load_scoring_config
from server.services.segmenter import segment_route
from server.services.wording import find_banned_wording
from tests import fakes

CFG = load_scoring_config()
EIGHT_PM = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)
ONE_AM = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)


def segments(when=EIGHT_PM):
    r = fakes.route_a()
    return segment_route(r.coords, when, r.duration_s, 50)


def test_no_data_at_all_gives_all_unknown_evidence():
    facts = build_route_facts(segments(), DataBundle(), CFG)
    ev = facts.evidence[0]
    assert ev.open_weight_50m is None and ev.lit is None and ev.road_class is None
    assert ev.help_known is False and ev.transit_active is None
    assert facts.open_places_count == 0 and facts.nearest_help is None


def test_places_open_and_closed_by_arrival_time():
    bundle = DataBundle(places=fakes.places())
    evening = build_route_facts(segments(EIGHT_PM), bundle, CFG)
    late = build_route_facts(segments(ONE_AM), bundle, CFG)
    assert evening.open_places_count >= 1 and "Day Cafe" in evening.open_place_names
    assert "Day Cafe" not in late.open_place_names   # the cafe is closed at 1 AM
    assert "Night Owl 0" in late.open_place_names    # the night-owl places are still open
    assert evening.unknown_hours_places == 1     # the shop with unreadable hours


def test_pharmacy_24h_counts_as_help_point():
    bundle = DataBundle(places=fakes.places())
    kinds = {h.kind for h in help_points_from(bundle)}
    assert kinds == {"store_24h"}
    with_osm = DataBundle(places=fakes.places(), features=fakes.features())
    assert {h.kind for h in help_points_from(with_osm)} == {"store_24h", "police"}


def test_road_lit_and_tunnel_from_nearest_ways():
    ways = [
        Way(1, "footway", False, False, None, fakes.ROUTE_A_COORDS),
        Way(2, "primary", True, True, "Main", fakes.ROUTE_A_COORDS),
        Way(3, "residential", None, False, None, [(-122.0, 37.0), (-122.0, 37.1)]),  # far away
    ]
    bundle = DataBundle(features=MapFeatures(ways, [], EIGHT_PM))
    ev = build_route_facts(segments(), bundle, CFG).evidence[0]
    assert ev.road_class == "primary"        # best class wins over the sidewalk beside it
    assert ev.lit is True                     # any lit tag beats an unlit sidewalk
    assert ev.tunnel is True


def test_unlit_only_and_no_ways_nearby():
    only_no = MapFeatures([Way(1, "residential", False, False, None, fakes.ROUTE_A_COORDS)], [], EIGHT_PM)
    ev = build_route_facts(segments(), DataBundle(features=only_no), CFG).evidence[0]
    assert ev.lit is False
    far = MapFeatures([Way(1, "residential", True, False, None, [(0.0, 0.0), (0.0, 0.1)])], [], EIGHT_PM)
    ev = build_route_facts(segments(), DataBundle(features=far), CFG).evidence[0]
    assert ev.road_class is None and ev.lit is None and ev.help_known is True


def test_outages_incidents_counts():
    mid = segments()[0].mid
    bundle = DataBundle(
        outages=[Outage(mid[0], mid[1], "2026-10-24"), Outage(0.0, 0.0, "x")],
        incidents=[Incident(mid[0], mid[1], "Theft")] * 3)
    ev = build_route_facts(segments(), bundle, CFG).evidence[0]
    assert ev.outages_50m == 1 and ev.incidents_100m == 3


def test_transit_needs_a_departure_within_15_minutes():
    seg0 = segments()[0]
    soon = ActiveStop("Stop", seg0.mid[0], seg0.mid[1], seg0.arrival_time + timedelta(minutes=5))
    later = ActiveStop("Stop", seg0.mid[0], seg0.mid[1], seg0.arrival_time + timedelta(minutes=40))
    assert build_route_facts(segments(), DataBundle(transit=[soon]), CFG).evidence[0].transit_active is True
    assert build_route_facts(segments(), DataBundle(transit=[later]), CFG).evidence[0].transit_active is False
    assert build_route_facts(segments(), DataBundle(transit=[]), CFG).evidence[0].transit_active is False


def test_nearest_help_is_reported_with_distance():
    bundle = DataBundle(features=fakes.features(), places=[])
    facts = build_route_facts(segments(), bundle, CFG)
    name, dist = facts.nearest_help
    assert name == "Fixture Police Station" and dist > 0


# ---------- reasons ----------

def test_reasons_for_a_rich_segment():
    ev = Evidence(open_weight_50m=3.0, lit=True, outages_50m=1, road_class="primary", help_known=True,
                  help_distance_m=62.0, transit_active=True, tunnel=True, turn_angle_deg=90)
    reasons = segment_reasons(ev, {"main_road": 100.0})
    assert "3 open places within 50 m" in reasons and "lit street" in reasons
    assert "streetlight outage reported nearby" in reasons and "main road" in reasons
    assert "help point 62 m away" in reasons and "transit running nearby" in reasons
    assert "underpass or tunnel" in reasons and "sharp turn" in reasons


def test_reasons_for_missing_and_empty_data():
    reasons = segment_reasons(Evidence(), {"main_road": None})
    assert "not sure: open places data missing" in reasons
    assert "not sure: lighting data missing" in reasons
    assert "not sure: transit schedule not connected" in reasons
    quiet = segment_reasons(Evidence(open_weight_50m=0.0, lit=False, transit_active=False),
                            {"main_road": 20.0})
    assert "no open places nearby" in quiet and "street not marked as lit" in quiet
    assert "alley or path" in quiet
    assert "side street" in segment_reasons(Evidence(open_weight_50m=1.0), {"main_road": 55.0})
    assert "1 open place within 50 m" in segment_reasons(Evidence(open_weight_50m=1.0), {})


def test_no_reason_ever_says_safe():
    for ev in (Evidence(), Evidence(open_weight_50m=2, lit=True, help_known=True, help_distance_m=10)):
        assert find_banned_wording(" ".join(segment_reasons(ev, {"main_road": 100.0}))) == []


# ---------- wording ----------

def test_wording_allowed_phrases():
    assert find_banned_wording("Welcome to Safe Smart Maps") == []
    assert find_banned_wording("We do not guarantee safety. In an emergency, call 911.") == []
    assert find_banned_wording("Better lit and more active; not sure about transit.") == []


def test_wording_flags_banned_phrases():
    for text in ["this route is safe", "the safest route", "Hazard report", "a dangerous alley",
                 "crime-free", "we guarantee this", "walk safely"]:
        assert find_banned_wording(text), text
