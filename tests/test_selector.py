"""Route selection (Fastest / Safest / Balanced). Pure functions. The continuity rule itself is
Amey's (tests/test_continuity.py)."""
from server.services.scoring_config import load_scoring_config
from server.services.selector import Candidate, select_routes

CFG = load_scoring_config()


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


def test_selector_needs_its_config_block():
    assert CFG["selection"]["balanced_points_per_extra_min"] > 0
