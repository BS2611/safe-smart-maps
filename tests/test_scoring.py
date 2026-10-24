"""Pure scoring tests: factors, unknown handling, bands, coverage, priorities."""
from datetime import datetime, timedelta, timezone

import pytest

from server.services.scoring import (
    FACTOR_NAMES,
    Evidence,
    apply_priorities,
    band_for,
    compute_factors,
    is_covered,
    score_segment,
    time_of_day_factor,
)
from server.services.scoring_config import load_scoring_config

CFG = load_scoring_config()
W = CFG["weights"]
# 2026-10-24 22:40 Los Angeles = 05:40 UTC next day.
NIGHT = datetime(2026, 10, 25, 5, 40, tzinfo=timezone.utc)
NOON = datetime(2026, 10, 24, 19, 0, tzinfo=timezone.utc)  # 12:00 in Los Angeles
SMALL_HOURS = datetime(2026, 10, 25, 8, 30, tzinfo=timezone.utc)  # 01:30 in Los Angeles


def test_factor_names_match_config_weights():
    assert set(FACTOR_NAMES) == set(W)


def test_empty_evidence_leaves_only_geometry_factor_known():
    f = compute_factors(Evidence(), NIGHT, CFG)
    assert [k for k, v in f.items() if v is not None] == ["turns"]
    assert f["turns"] == 100


def test_open_places_scale_and_cap():
    assert compute_factors(Evidence(open_weight_50m=0.0), NIGHT, CFG)["open_places"] == 0
    assert compute_factors(Evidence(open_weight_50m=1.0), NIGHT, CFG)["open_places"] == 40
    assert compute_factors(Evidence(open_weight_50m=10.0), NIGHT, CFG)["open_places"] == 100


def test_lighting_lit_unlit_and_outages():
    assert compute_factors(Evidence(lit=True), NIGHT, CFG)["lighting"] == 100
    assert compute_factors(Evidence(lit=False), NIGHT, CFG)["lighting"] == 10
    assert compute_factors(Evidence(lit=True, outages_50m=1), NIGHT, CFG)["lighting"] == 70
    assert compute_factors(Evidence(lit=True, outages_50m=9), NIGHT, CFG)["lighting"] == 0
    assert compute_factors(Evidence(lit=None, outages_50m=2), NIGHT, CFG)["lighting"] is None


@pytest.mark.parametrize(
    ("road", "expected"),
    [("primary", 100), ("secondary", 100), ("residential", 55), ("service", 20),
     ("footway", 20), ("something_new", None), (None, None)],
)
def test_main_road_classes(road, expected):
    assert compute_factors(Evidence(road_class=road), NIGHT, CFG)["main_road"] == expected


def test_help_points_distance_curve():
    f = lambda **kw: compute_factors(Evidence(help_known=True, **kw), NIGHT, CFG)["help_points"]  # noqa: E731
    assert f(help_distance_m=20) == 100
    assert f(help_distance_m=50) == 100
    assert f(help_distance_m=100) == 50
    assert f(help_distance_m=150) == 0
    assert f(help_distance_m=400) == 0
    assert f(help_distance_m=None) == 0          # known: nothing nearby
    assert compute_factors(Evidence(), NIGHT, CFG)["help_points"] is None  # unknown


def test_transit_and_incidents():
    assert compute_factors(Evidence(transit_active=True), NIGHT, CFG)["transit"] == 100
    assert compute_factors(Evidence(transit_active=False), NIGHT, CFG)["transit"] == 0
    assert compute_factors(Evidence(), NIGHT, CFG)["transit"] is None
    assert compute_factors(Evidence(incidents_100m=0), NIGHT, CFG)["incidents"] == 100
    assert compute_factors(Evidence(incidents_100m=3), NIGHT, CFG)["incidents"] == 70
    assert compute_factors(Evidence(incidents_100m=50), NIGHT, CFG)["incidents"] == 0


def test_activity_depends_on_time_of_day():
    ev = Evidence(open_count_100m=3)
    noon = compute_factors(ev, NOON, CFG)["activity"]
    late = compute_factors(ev, NIGHT, CFG)["activity"]
    small = compute_factors(ev, SMALL_HOURS, CFG)["activity"]
    assert noon == 75
    assert late == pytest.approx(75 * 0.8)
    assert small == pytest.approx(75 * 0.35)
    assert compute_factors(Evidence(), NIGHT, CFG)["activity"] is None


def test_time_of_day_factor_boundaries():
    table = CFG["activity"]["time_of_day"]
    la = lambda h: datetime(2026, 10, 24, 0, 0, tzinfo=timezone.utc) + timedelta(hours=h + 7)  # noqa: E731
    assert time_of_day_factor(la(12), table) == 1.0
    assert time_of_day_factor(la(23), table) == 0.6
    assert time_of_day_factor(la(3), table) == 0.35


def test_turn_angles_and_tunnel():
    t = lambda **kw: compute_factors(Evidence(**kw), NIGHT, CFG)["turns"]  # noqa: E731
    assert t(turn_angle_deg=10) == 100
    assert t(turn_angle_deg=50) == 70
    assert t(turn_angle_deg=120) == 40
    assert t(turn_angle_deg=10, tunnel=True) == 60
    assert t(turn_angle_deg=120, tunnel=True) == 0


def full_evidence(**over):
    base = dict(open_weight_50m=2.0, open_count_100m=4, covered_by_open_place=True, lit=True,
                outages_50m=0, road_class="primary", help_known=True, help_distance_m=40,
                transit_active=True, incidents_100m=0, turn_angle_deg=0)
    base.update(over)
    return Evidence(**base)


def test_score_all_known_is_weighted_average():
    f = compute_factors(full_evidence(), NOON, CFG)
    s = score_segment(f, W, CFG)
    expected = sum(W[k] * f[k] for k in W)
    assert s.score == pytest.approx(expected, abs=0.1)
    assert s.confidence == "high" and s.band == "green"
    assert s.known_weight == pytest.approx(1.0)


def test_score_renormalizes_over_known_factors():
    f = compute_factors(Evidence(lit=True, road_class="primary", turn_angle_deg=0), NIGHT, CFG)
    s = score_segment(f, W, CFG)
    # known weight = lighting .20 + main_road .15 + turns .05 = .40 (< .5) -> unknown
    assert s.score is None and s.band == "unknown" and s.confidence == "unknown"


def test_score_low_confidence_when_half_known():
    f = compute_factors(
        Evidence(lit=True, road_class="primary", help_known=True, help_distance_m=30,
                 turn_angle_deg=0), NIGHT, CFG)
    s = score_segment(f, W, CFG)
    # lighting .20 + main_road .15 + help .10 + turns .05 = .50 -> low, but scored
    assert s.confidence == "low" and s.score is not None


def test_bands():
    assert band_for(70, CFG) == "green"
    assert band_for(69.9, CFG) == "yellow"
    assert band_for(45, CFG) == "yellow"
    assert band_for(44.9, CFG) == "red"


def test_red_segment_for_empty_unlit_alley():
    ev = full_evidence(open_weight_50m=0, open_count_100m=0, covered_by_open_place=False, lit=False,
                       road_class="service", help_distance_m=None, transit_active=False,
                       incidents_100m=5, turn_angle_deg=100)
    s = score_segment(compute_factors(ev, NIGHT, CFG), W, CFG)
    assert s.band == "red" and s.score < 30


def test_is_covered_rules():
    assert is_covered(Evidence(covered_by_open_place=True), CFG) is True
    assert is_covered(Evidence(transit_active=True), CFG) is True
    assert is_covered(Evidence(help_known=True, help_distance_m=60), CFG) is True
    assert is_covered(Evidence(help_known=True, help_distance_m=120), CFG) is False
    assert is_covered(Evidence(covered_by_open_place=False), CFG) is False
    assert is_covered(Evidence(help_known=True, help_distance_m=None), CFG) is False
    assert is_covered(Evidence(), CFG) is None


def test_priorities_boost_and_renormalize():
    boosted = apply_priorities(W, ["lighting", "open_places"])
    assert sum(boosted.values()) == pytest.approx(1.0)
    assert boosted["lighting"] > W["lighting"] and boosted["open_places"] > W["open_places"]
    assert boosted["incidents"] < W["incidents"]


def test_priorities_ignore_unknown_names_and_accept_aliases():
    assert apply_priorities(W, ["nonsense"]) == pytest.approx(W)
    assert apply_priorities(W, ["main_roads"])["main_road"] > W["main_road"]
