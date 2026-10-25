"""Continuity rule and route selection (pure functions)."""
import pytest

from server.services.continuity import (
    SegmentInfo,
    average_score,
    coverage_pct,
    longest_gap,
    route_continuity,
    worst_window,
)
from server.services.scoring_config import load_scoring_config
from server.services.selector import Candidate, select_routes

CFG = load_scoring_config()


def segs(scores, covered=None, length=50.0):
    covered = covered if covered is not None else [True] * len(scores)
    return [SegmentInfo(length, s, c) for s, c in zip(scores, covered, strict=True)]


def test_average_is_length_weighted_and_skips_unknown():
    s = [SegmentInfo(50, 80, True), SegmentInfo(100, 20, True), SegmentInfo(50, None, None)]
    assert average_score(s) == pytest.approx((80 * 50 + 20 * 100) / 150)
    assert average_score([SegmentInfo(50, None, None)]) is None


def test_coverage_pct():
    s = segs([50] * 4, [True, True, True, False])
    assert coverage_pct(s) == 75
    assert coverage_pct([SegmentInfo(50, 50, None)]) is None
    assert coverage_pct(segs([50] * 2, [True, None])) == 100  # unknown is left out, not counted


def test_longest_gap_and_position():
    s = segs([50] * 8, [True, False, False, True, False, False, False, True])
    gap, start = longest_gap(s)
    assert gap == 150 and start == 200
    assert longest_gap(segs([50] * 3, [True, True, True])) == (0.0, None)


def test_unknown_coverage_breaks_a_gap():
    s = segs([50] * 5, [False, False, None, False, False])
    assert longest_gap(s)[0] == 100


def test_worst_window_finds_the_empty_stretch():
    # 4 segments = 200 m window. Good start, terrible middle.
    s = segs([90, 90, 90, 90, 10, 10, 10, 10, 90, 90])
    assert worst_window(s, 200) == 10


def test_worst_window_short_route_uses_whole_route():
    assert worst_window(segs([40, 60]), 200) == 50


def test_worst_window_skips_unknown_heavy_windows():
    s = segs([None, None, None, None, 80, 80, 80, 80, 80])
    assert worst_window(s, 200) == 80
    assert worst_window(segs([None, None]), 200) is None


def test_worst_window_falls_back_when_every_window_is_mostly_unknown():
    s = [SegmentInfo(50, x, True) for x in [None, None, None, 60, None, None, None, None]]
    assert worst_window(s, 200) == 60


def test_busy_start_empty_end_does_not_look_safe():
    """The key idea: a good average hides an empty stretch; the rule must punish it."""
    even = segs([60] * 20)
    lopsided = segs([95] * 4 + [45] * 16, [True] * 4 + [False] * 16)
    even_c = route_continuity(even, CFG)
    lop_c = route_continuity(lopsided, CFG)
    assert lop_c.route_score < even_c.route_score
    assert lop_c.longest_gap_m == 800 and lop_c.gap_penalty == 65.0
    assert lop_c.worst_window_score == 45


def test_route_score_formula_no_gap():
    c = route_continuity(segs([80] * 8), CFG)
    assert c.route_score == 80
    assert c.gap_penalty == 0 and c.coverage_pct == 100


def test_route_score_formula_with_gap_penalty():
    s = segs([60] * 8, [True, True] + [False] * 6)       # gap 300 m
    c = route_continuity(s, CFG)
    assert c.longest_gap_m == 300
    assert c.gap_penalty == pytest.approx(15.0)           # (300-150) * 0.1
    assert c.route_score == pytest.approx(60 - 15)


def test_score_is_clamped_and_unknown_when_nothing_scored():
    heavy = route_continuity(segs([10] * 40, [False] * 40), CFG)
    assert heavy.route_score == 0
    none = route_continuity(segs([None] * 4, [None] * 4), CFG)
    assert none.route_score is None and none.coverage_pct is None
    assert none.worst_window_score is None and none.average_score is None


def test_gap_at_the_limit_has_no_penalty():
    s = segs([60] * 6, [True, True, True] + [False] * 3)  # exactly 150 m
    assert route_continuity(s, CFG).gap_penalty == 0


# ---------- selector ----------

def cand(rid, minutes, score):
    return Candidate(rid, minutes, score)


def test_three_distinct_routes():
    cs = [cand("a", 40, 50), cand("b", 46, 80), cand("c", 42, 76)]
    sel = {s.labels[0]: s.route_id for s in select_routes(cs, 10, CFG)}
    assert sel["fastest"] == "a"
    assert sel["safest"] == "b"
    assert sel["balanced"] == "c"


def test_extra_minutes_cap_limits_safest():
    cs = [cand("a", 40, 50), cand("b", 52, 95), cand("c", 43, 60)]
    out = {s.labels[0]: s.route_id for s in select_routes(cs, 5, CFG)}
    assert out["safest"] == "c"          # b is 12 min slower, over the 5 min cap


def test_zero_extra_minutes_collapses_everything_to_fastest():
    cs = [cand("a", 40, 50), cand("b", 41, 90)]
    out = select_routes(cs, 0, CFG)
    assert len(out) == 1 and out[0].route_id == "a"
    assert out[0].labels == ["safest", "balanced", "fastest"]


def test_merged_labels_when_same_route_wins_two_labels():
    cs = [cand("a", 40, 50), cand("b", 43, 90)]
    out = {s.route_id: s.labels for s in select_routes(cs, 10, CFG)}
    assert out["b"] == ["safest", "balanced"]
    assert out["a"] == ["fastest"]


def test_scoreless_candidates_can_only_be_fastest():
    cs = [cand("a", 40, None), cand("b", 45, None)]
    out = select_routes(cs, 10, CFG)
    assert [(s.route_id, s.labels) for s in out] == [("a", ["fastest"])]


def test_ties_are_deterministic():
    cs = [cand("b", 40, 70), cand("a", 40, 70)]
    assert select_routes(cs, 10, CFG) == select_routes(list(reversed(cs)), 10, CFG)


def test_no_candidates():
    assert select_routes([], 10, CFG) == []


# ---------- coverage per segment (uses Amey's Segment, Place and opening-hours code) ----------

def test_is_covered_follows_open_status_and_distance():
    from datetime import datetime, timezone

    from server.services.continuity import is_covered
    from server.services.segmenter import segment_route
    from tests import fakes

    seg = segment_route([(37.8029, -122.4484), (37.8029, -122.4442)], 50.0)[0]
    eight_pm = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)
    one_am = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)
    near_evening = fakes.place("Near Evening", -122.4470, 37.80295, "restaurant", fakes.EVENING)
    near_owl = fakes.place("Near Owl", -122.4470, 37.80295, "restaurant", fakes.NIGHT_OWL)
    far = fakes.place("Far", -122.4470, 37.8100, "restaurant", fakes.NIGHT_OWL)
    mystery = fakes.place("Mystery", -122.4470, 37.80295, "other", None)

    assert is_covered(seg, eight_pm, [near_evening], CFG) is True
    assert is_covered(seg, one_am, [near_evening], CFG) is False       # closed by 1 AM
    assert is_covered(seg, one_am, [near_owl], CFG) is True
    assert is_covered(seg, eight_pm, [far], CFG) is False              # open but too far
    assert is_covered(seg, eight_pm, [mystery], CFG) is False          # unknown hours never count
    assert is_covered(seg, eight_pm, [], CFG) is False                 # data available, nothing found
    assert is_covered(seg, eight_pm, None, CFG) is None                # no data: not sure


def test_selector_needs_its_config_block():
    assert CFG["selection"]["balanced_points_per_extra_min"] > 0
