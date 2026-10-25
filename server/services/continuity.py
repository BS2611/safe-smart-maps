"""Continuity rule and route-level contextual score (TECHNICAL_SPEC s5, FUNCTIONAL_SPEC 5.4).

Consumes only ordered SegmentScore results; no providers, no fetching. All constants come
from the `continuity` section of scoring/scoring_v1.json. Hackathon-v1 heuristics, NOT a
safety measurement: the result describes how evenly contextual signals are spread along a route.

  average      = length-weighted mean of known segment scores
  worst window = lowest length-weighted mean over any ~window_m stretch of the route
  coverage     = share of the route (by length) within radii_m.coverage of an open place, help point, or (when a GTFS feed is loaded) an active transit stop
  longest gap  = longest consecutive stretch (meters) that is confirmed NOT covered
  penalty      = max(0, gap - gap_limit_m) * gap_penalty_per_m
  route score  = clamp(avg_weight*average + worst_window_weight*worst - penalty, 0, 100)

Unknown is not zero: segments with score None are left out of average / worst window, segments
with covered None are left out of coverage and do not extend a gap. The unknown share is reported.
"""
import math
from dataclasses import dataclass, field

from server.services.scoring_config import ScoringConfigError
from server.services.segment_scoring import SegmentScore

_REQUIRED = ("coverage_target", "gap_limit_m", "window_m", "avg_weight", "worst_window_weight",
             "gap_penalty_per_m")
_EPS = 1e-9


@dataclass(frozen=True)
class ContinuityResult:
    route_length_m: float
    known_length_m: float               # length of segments that have a score
    unknown_length_m: float             # length of segments with score None ("not sure")
    average_score: float | None
    coverage_pct: float | None          # None when no segment's coverage is known
    coverage_known_pct: float           # share of route length whose coverage is known
    meets_coverage_target: bool | None
    longest_gap_m: float
    gap_start_m: float | None
    gap_end_m: float | None
    worst_window_score: float | None
    worst_window_start_m: float | None
    worst_window_end_m: float | None
    gap_penalty: float                  # formula value, before the cap
    gap_penalty_applied: float          # what was actually subtracted (never more than the base)
    base_score: float | None            # avg_weight*average + worst_window_weight*worst
    route_score: float | None           # None = not sure (nothing scored)
    notes: list[str] = field(default_factory=list)

    @property
    def insufficient_data(self) -> bool:
        return self.route_score is None

    def to_dict(self) -> dict:
        """Route result fields from CONTRACTS.md: `route_score` and `continuity`."""
        r = lambda v, n=1: None if v is None else round(v, n)
        if self.gap_start_m is None or self.longest_gap_m <= 0:
            note = None
        else:
            note = f"from {self.gap_start_m:.0f} m to {self.gap_end_m:.0f} m along the route"
        return {
            "route_score": r(self.route_score),
            "continuity": {
                "coverage_pct": r(self.coverage_pct),
                "longest_gap_m": r(self.longest_gap_m),
                "longest_gap_note": note,
                "worst_window_score": r(self.worst_window_score),
                "worst_window_start_m": r(self.worst_window_start_m),
                "worst_window_end_m": r(self.worst_window_end_m),
                "average_score": r(self.average_score),
                "gap_penalty": r(self.gap_penalty),
                "gap_penalty_applied": r(self.gap_penalty_applied),
                "meets_coverage_target": self.meets_coverage_target,
                "route_length_m": r(self.route_length_m),
                "unknown_length_m": r(self.unknown_length_m),
                "insufficient_data": self.insufficient_data,
                "notes": list(self.notes),
            },
        }


def check_continuity_params(config: dict) -> None:
    c = config.get("continuity")
    if not isinstance(c, dict):
        raise ScoringConfigError(f"{config.get('version')}: missing continuity section")
    missing = [k for k in _REQUIRED if k not in c]
    if missing:
        raise ScoringConfigError(f"{config.get('version')}: missing continuity keys {missing}")
    if not 0 <= c["coverage_target"] <= 1:
        raise ScoringConfigError("continuity.coverage_target must be between 0 and 1")
    if c["window_m"] <= 0:
        raise ScoringConfigError("continuity.window_m must be > 0")
    for key in ("gap_limit_m", "gap_penalty_per_m", "avg_weight", "worst_window_weight"):
        if c[key] < 0:
            raise ScoringConfigError(f"continuity.{key} must be >= 0")
    if not math.isclose(c["avg_weight"] + c["worst_window_weight"], 1.0, abs_tol=1e-9):
        raise ScoringConfigError("continuity.avg_weight + worst_window_weight must equal 1.0")


def _mean_in_window(spans: list[tuple[float, float, float]], t0: float, t1: float) -> float | None:
    """Length-weighted mean of known scores over [t0, t1]; None if no known score overlaps."""
    num = den = 0.0
    for a, b, score in spans:
        overlap = min(b, t1) - max(a, t0)
        if overlap > 0:
            num += overlap * score
            den += overlap
    return num / den if den > _EPS else None


def _worst_window(spans: list[tuple[float, float, float]], total: float, window: float):
    """Exact minimum of the windowed mean. The mean is piecewise linear in the window start, with
    breakpoints where either window edge crosses a segment boundary, so only those starts are tried.
    Routes not longer than the window use the whole route. Returns (score, start, end) or Nones."""
    if not spans:
        return None, None, None
    if total <= window + _EPS:
        return _mean_in_window(spans, 0.0, total), 0.0, total
    last = total - window
    starts = {0.0, last}
    for a, b, _ in spans:
        for edge in (a, b):
            for s in (edge, edge - window):
                if 0.0 <= s <= last:
                    starts.add(s)
    best = (math.inf, None)
    for s in sorted(starts):
        m = _mean_in_window(spans, s, s + window)
        if m is not None and m < best[0] - _EPS:
            best = (m, s)
    return best[0], best[1], best[1] + window


def compute_continuity(config: dict, scored: list[SegmentScore]) -> ContinuityResult:
    """`scored` = ordered SegmentScore list for ONE route (as returned by SegmentScorer.score_route)."""
    check_continuity_params(config)
    c = config["continuity"]
    prev_end = 0.0
    for s in scored:
        if s.segment.offset_m < prev_end - 1e-6:
            raise ValueError("segments must be ordered along the route and must not overlap")
        prev_end = s.segment.offset_m + s.segment.length_m
    total = sum(s.segment.length_m for s in scored)

    spans = [(s.segment.offset_m, s.segment.offset_m + s.segment.length_m, s.score)
             for s in scored if s.score is not None]
    known = sum(b - a for a, b, _ in spans)
    unknown = total - known
    notes: list[str] = []

    average = sum((b - a) * v for a, b, v in spans) / known if known > _EPS else None
    worst, w0, w1 = _worst_window(spans, total, c["window_m"])

    # coverage: share of length whose coverage is known to be True
    cov_known = cov_true = 0.0
    run_start = None
    best_gap, best_start, best_end = 0.0, None, None
    for s in scored:
        a, b = s.segment.offset_m, s.segment.offset_m + s.segment.length_m
        if s.covered is not None:
            cov_known += b - a
            cov_true += (b - a) if s.covered else 0.0
        if s.covered is False:
            run_start = a if run_start is None else run_start
            if b - run_start > best_gap + _EPS:
                best_gap, best_start, best_end = b - run_start, run_start, b
        else:
            run_start = None
    coverage_pct = 100 * cov_true / cov_known if cov_known > _EPS else None
    meets = None if coverage_pct is None else coverage_pct >= 100 * c["coverage_target"] - _EPS

    penalty = max(0.0, best_gap - c["gap_limit_m"]) * c["gap_penalty_per_m"]
    if average is None:
        base = score = None
        applied = 0.0
        notes.append("no segment has a score, so the route score is not sure")
    else:
        base = c["avg_weight"] * average + c["worst_window_weight"] * worst
        applied = min(penalty, base)
        score = min(100.0, max(0.0, base - applied))
        if penalty > _EPS:
            notes.append(f"gap of {best_gap:.0f} m exceeds the {c['gap_limit_m']:g} m limit "
                         f"(penalty {applied:.1f})")
    if unknown > _EPS and total > 0:
        notes.append(f"{100 * unknown / total:.0f}% of the route has no score (not sure); "
                     "average and worst window use only the scored part")
    if cov_known < total - _EPS and total > 0:
        notes.append(f"coverage not sure for {100 * (total - cov_known) / total:.0f}% of the route")
    if meets is False:
        notes.append(f"coverage {coverage_pct:.0f}% is below the {100 * c['coverage_target']:.0f}% target")

    return ContinuityResult(
        route_length_m=total, known_length_m=known, unknown_length_m=unknown, average_score=average,
        coverage_pct=coverage_pct, coverage_known_pct=100 * cov_known / total if total > 0 else 0.0,
        meets_coverage_target=meets, longest_gap_m=best_gap, gap_start_m=best_start, gap_end_m=best_end,
        worst_window_score=worst, worst_window_start_m=w0, worst_window_end_m=w1,
        gap_penalty=penalty, gap_penalty_applied=applied, base_score=base, route_score=score,
        notes=notes)
