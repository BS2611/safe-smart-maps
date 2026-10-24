"""Continuity rule (docs/specs/FUNCTIONAL_SPEC.md section 5.4). Pure functions.

Route score = avg_weight * average segment score + worst_window_weight * worst-window score
              - gap penalty (per metre of the longest empty stretch beyond the gap limit).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentInfo:
    length_m: float
    score: float | None      # None = unknown
    covered: bool | None     # None = unknown


@dataclass(frozen=True)
class Continuity:
    coverage_pct: float | None
    longest_gap_m: float
    longest_gap_start_m: float | None
    worst_window_score: float | None
    average_score: float | None
    route_score: float | None
    gap_penalty: float


def average_score(segs: list[SegmentInfo]) -> float | None:
    """Length-weighted average over segments with a known score."""
    known = [s for s in segs if s.score is not None]
    total = sum(s.length_m for s in known)
    if total == 0:
        return None
    return sum(s.score * s.length_m for s in known) / total


def coverage_pct(segs: list[SegmentInfo]) -> float | None:
    """Share of known-coverage route length that is covered, 0..100."""
    known = [s for s in segs if s.covered is not None]
    total = sum(s.length_m for s in known)
    if total == 0:
        return None
    return 100.0 * sum(s.length_m for s in known if s.covered) / total


def longest_gap(segs: list[SegmentInfo]) -> tuple[float, float | None]:
    """(length in metres, distance from route start) of the longest run of uncovered segments.
    Unknown coverage breaks a run, so we never claim a gap we cannot see."""
    best, best_start = 0.0, None
    run, run_start, pos = 0.0, 0.0, 0.0
    for s in segs:
        if s.covered is False:
            if run == 0:
                run_start = pos
            run += s.length_m
            if run > best:
                best, best_start = run, run_start
        else:
            run = 0.0
        pos += s.length_m
    return best, best_start


def worst_window(segs: list[SegmentInfo], window_m: float) -> float | None:
    """Lowest average score over any rolling window of `window_m` metres.
    If the route is shorter than the window, the whole route is the window."""
    scored = [s for s in segs if s.score is not None]
    if not scored:
        return None
    seg_len = max(s.length_m for s in scored)
    n = max(1, round(window_m / seg_len)) if seg_len > 0 else 1
    scores = [s.score for s in segs]
    if len(segs) <= n:
        known = [x for x in scores if x is not None]
        return sum(known) / len(known)
    worst = None
    for i in range(len(segs) - n + 1):
        known = [x for x in scores[i:i + n] if x is not None]
        if len(known) < max(1, n // 2):  # too little known in this window to judge it
            continue
        avg = sum(known) / len(known)
        worst = avg if worst is None else min(worst, avg)
    if worst is None:
        known = [x for x in scores if x is not None]
        return sum(known) / len(known)
    return worst


def route_continuity(segs: list[SegmentInfo], cfg: dict) -> Continuity:
    c = cfg["continuity"]
    avg = average_score(segs)
    worst = worst_window(segs, c["window_m"])
    gap, gap_start = longest_gap(segs)
    penalty = max(0.0, gap - c["gap_limit_m"]) * c["gap_penalty_per_m"]
    if avg is None or worst is None:
        score = None
    else:
        raw = c["avg_weight"] * avg + c["worst_window_weight"] * worst - penalty
        score = round(max(0.0, min(100.0, raw)), 1)
    return Continuity(
        coverage_pct=None if coverage_pct(segs) is None else round(coverage_pct(segs), 1),
        longest_gap_m=round(gap),
        longest_gap_start_m=gap_start,
        worst_window_score=None if worst is None else round(worst, 1),
        average_score=None if avg is None else round(avg, 1),
        route_score=score,
        gap_penalty=round(penalty, 1),
    )
