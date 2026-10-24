"""Segment scoring (pure functions). Weights and thresholds come from scoring/scoring_v1.json.

Rule: missing data is "unknown", never a guessed value. Unknown factors are left out and the
weights of the known factors are renormalized; if too little is known the segment is
"unknown" (score None).
"""
from dataclasses import dataclass
from datetime import datetime

from server.data.opening_hours import PLACE_TZ

FACTOR_NAMES = (
    "open_places", "lighting", "main_road", "help_points",
    "transit", "activity", "incidents", "turns",
)
# The UI uses friendlier names for the "what matters most" chips.
PRIORITY_ALIASES = {
    "lighting": "lighting", "open_places": "open_places", "main_road": "main_road",
    "main_roads": "main_road", "help_points": "help_points", "transit": "transit",
}
PRIORITY_BOOST = 1.5


@dataclass(frozen=True)
class Evidence:
    """What we know near one segment. None means "no data", which is different from "none nearby"."""
    open_weight_50m: float | None = None   # sum of weights of OPEN places within 50 m
    open_count_100m: int | None = None     # OPEN places within 100 m
    covered_by_open_place: bool | None = None  # an open place within the coverage radius
    lit: bool | None = None
    outages_50m: int | None = None
    road_class: str | None = None
    help_known: bool = False
    help_distance_m: float | None = None   # nearest help point; None with help_known = none nearby
    transit_active: bool | None = None
    incidents_100m: int | None = None
    turn_angle_deg: float = 0.0
    tunnel: bool = False


@dataclass(frozen=True)
class SegmentScore:
    score: float | None
    band: str            # green | yellow | red | unknown
    confidence: str      # high | low | unknown
    factors: dict[str, float | None]
    known_weight: float


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def time_of_day_factor(arrival: datetime, table: dict[str, float]) -> float:
    hour = arrival.astimezone(PLACE_TZ).hour
    starts = sorted(int(k) for k in table)
    applicable = [s for s in starts if s <= hour]
    return table[str(applicable[-1] if applicable else starts[0])]


def compute_factors(ev: Evidence, arrival: datetime, cfg: dict) -> dict[str, float | None]:
    f: dict[str, float | None] = {}
    f["open_places"] = (
        None if ev.open_weight_50m is None
        else _clamp(ev.open_weight_50m * cfg["open_place_weights"]["points_per_weight"])
    )

    lc = cfg["lighting"]
    if ev.lit is None:
        f["lighting"] = None
    else:
        base = lc["lit_score"] if ev.lit else lc["unlit_score"]
        f["lighting"] = _clamp(base - lc["outage_penalty"] * (ev.outages_50m or 0))

    rc = cfg["roads"]
    if ev.road_class in rc["main"]:
        f["main_road"] = rc["main_score"]
    elif ev.road_class in rc["minor"]:
        f["main_road"] = rc["minor_score"]
    elif ev.road_class in rc["poor"]:
        f["main_road"] = rc["poor_score"]
    else:
        f["main_road"] = None

    if not ev.help_known:
        f["help_points"] = None
    elif ev.help_distance_m is None:
        f["help_points"] = 0.0
    else:
        near, far = 50.0, float(cfg["radii_m"]["help_point"])
        f["help_points"] = _clamp(100 * (1 - (ev.help_distance_m - near) / (far - near)))

    f["transit"] = None if ev.transit_active is None else (100.0 if ev.transit_active else 0.0)

    if ev.open_count_100m is None:
        f["activity"] = None
    else:
        base = min(100.0, ev.open_count_100m * cfg["activity"]["points_per_open_place"])
        f["activity"] = _clamp(base * time_of_day_factor(arrival, cfg["activity"]["time_of_day"]))

    f["incidents"] = (
        None if ev.incidents_100m is None
        else _clamp(100 - ev.incidents_100m * cfg["incidents"]["points_per_incident"])
    )

    tc = cfg["turns"]
    if ev.turn_angle_deg < tc["gentle_deg"]:
        turns = tc["gentle_score"]
    elif ev.turn_angle_deg < tc["moderate_deg"]:
        turns = tc["moderate_score"]
    else:
        turns = tc["sharp_score"]
    f["turns"] = _clamp(turns - (tc["tunnel_penalty"] if ev.tunnel else 0))
    return f


def band_for(score: float, cfg: dict) -> str:
    if score >= cfg["bands"]["green_min"]:
        return "green"
    if score >= cfg["bands"]["yellow_min"]:
        return "yellow"
    return "red"


def score_segment(factors: dict[str, float | None], weights: dict[str, float], cfg: dict) -> SegmentScore:
    known = {k: v for k, v in factors.items() if v is not None}
    known_weight = sum(weights[k] for k in known)
    total_weight = sum(weights.values())
    share = known_weight / total_weight if total_weight else 0.0
    if share < cfg["confidence"]["low_min_known_weight"]:
        return SegmentScore(None, "unknown", "unknown", factors, known_weight)
    score = sum(weights[k] * v for k, v in known.items()) / known_weight
    confidence = "high" if share >= cfg["confidence"]["high_min_known_weight"] else "low"
    return SegmentScore(round(score, 1), band_for(score, cfg), confidence, factors, known_weight)


def is_covered(ev: Evidence, cfg: dict) -> bool | None:
    """Within the coverage radius of an open place, a help point, or an active transit stop.

    True if any known source says so. False if at least places or help points are known and none
    applies (transit data may be missing; that is reported as a warning, not guessed). None if
    nothing about this segment is known."""
    radius = cfg["radii_m"]["coverage"]
    if ev.covered_by_open_place or ev.transit_active:
        return True
    if ev.help_known and ev.help_distance_m is not None and ev.help_distance_m <= radius:
        return True
    if ev.covered_by_open_place is not None or ev.help_known:
        return False
    return None


def apply_priorities(weights: dict[str, float], priorities: list[str]) -> dict[str, float]:
    """Boost up to two chosen factors by 1.5x, then renormalize so weights still sum to 1.0."""
    chosen = {PRIORITY_ALIASES[p] for p in priorities if p in PRIORITY_ALIASES}
    boosted = {k: v * (PRIORITY_BOOST if k in chosen else 1.0) for k, v in weights.items()}
    total = sum(boosted.values())
    return {k: v / total for k, v in boosted.items()}
