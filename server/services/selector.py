"""Picks Fastest, Most lit & active ("safest" in the API) and Balanced from scored candidates.

The API label values stay "safest | balanced | fastest" (CONTRACTS.md); the UI shows friendlier text.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    route_id: str
    duration_min: float
    route_score: float | None


@dataclass(frozen=True)
class Selection:
    route_id: str
    labels: list[str]   # first = primary label; the rest become also_labels


def select_routes(
    candidates: list[Candidate], max_extra_minutes: float, cfg: dict
) -> list[Selection]:
    """Returns one Selection per distinct route (1 to 3). Scoreless candidates can still be
    Fastest but never win Safest or Balanced."""
    if not candidates:
        return []
    fastest = min(candidates, key=lambda c: (c.duration_min, c.route_id))
    allowed = [
        c for c in candidates
        if c.route_score is not None and c.duration_min - fastest.duration_min <= max_extra_minutes
    ]
    picks: dict[str, str] = {"fastest": fastest.route_id}
    if allowed:
        safest = max(allowed, key=lambda c: (c.route_score, -c.duration_min, c.route_id))
        penalty = cfg["selection"]["balanced_points_per_extra_min"]
        balanced = max(
            allowed,
            key=lambda c: (c.route_score - penalty * (c.duration_min - fastest.duration_min),
                           -c.duration_min, c.route_id),
        )
        picks["safest"] = safest.route_id
        picks["balanced"] = balanced.route_id

    order = ["safest", "balanced", "fastest"]
    grouped: dict[str, list[str]] = {}
    for label in order:
        if label in picks:
            grouped.setdefault(picks[label], []).append(label)
    return [Selection(route_id=rid, labels=labels) for rid, labels in grouped.items()]
