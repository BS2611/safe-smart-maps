"""Per-segment context matching and weighted score (scoring_v1, hackathon-v1 heuristics).

Consumes only normalized project models (Place, AreaContext). It never sees Bright Data,
Overpass or Mapbox JSON, and it never fetches: the caller passes what was read from the cache.
All constants come from scoring/scoring_v1.json. A factor value is 0-100, or None = "not sure".
The score is NOT a safety claim; it summarizes contextual signals.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from server.data.models import AreaContext, Place
from server.data.opening_hours import PLACE_TZ, OpenStatus, evaluate_open_status
from server.services.geo import bearing_deg, point_to_polyline_m, turn_angle_deg
from server.services.scoring_config import ScoringConfigError
from server.services.segmenter import Segment

_REQUIRED = ("walking_speed_mps", "bands", "factor_params", "radii_m")


@dataclass(frozen=True)
class FactorResult:
    name: str
    value: float | None                 # 0-100, or None = unknown ("not sure")
    reason: str
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SegmentScore:
    segment: Segment
    arrival_time: datetime
    score: float | None                 # None when no factor is known
    band: str                           # green | yellow | red | unknown
    factors: dict[str, FactorResult]
    unknown_factors: list[str]
    reasons: list[str]
    known_weight_fraction: float        # share of total weight backed by known factors
    data_fetched_at: datetime | None    # oldest source timestamp used
    covered: bool | None = None         # open place / help point within radii_m.coverage; None = not sure

    def to_dict(self) -> dict:
        """CONTRACTS.md "Segment score" shape. Coordinates are [lng, lat]."""
        s = self.segment
        return {
            "segment_id": s.segment_id,
            "start": [s.start[1], s.start[0]],
            "end": [s.end[1], s.end[0]],
            "length_m": round(s.length_m, 1),
            "arrival_time": self.arrival_time.isoformat(),
            "score": None if self.score is None else round(self.score, 1),
            "band": self.band,
            "factors": {k: v.value for k, v in self.factors.items()},
            "unknown_factors": list(self.unknown_factors),
            "reasons": list(self.reasons),
            "data_fetched_at": self.data_fetched_at.isoformat() if self.data_fetched_at else None,
            "known_weight_fraction": round(self.known_weight_fraction, 3),
        }


def check_scoring_params(config: dict) -> None:
    missing = [k for k in _REQUIRED if k not in config]
    if missing:
        raise ScoringConfigError(f"{config.get('version')}: missing config keys {missing}")
    for key in ("open_place", "help_point", "road_match", "coverage"):
        if config["radii_m"].get(key, 0) <= 0:
            raise ScoringConfigError(f"{config.get('version')}: radii_m.{key} must be > 0")
    if config["walking_speed_mps"] <= 0:
        raise ScoringConfigError(f"{config.get('version')}: walking_speed_mps must be > 0")
    bands = config["bands"]
    if not bands["green_min"] > bands["yellow_min"]:
        raise ScoringConfigError(f"{config.get('version')}: green_min must exceed yellow_min")


class SegmentScorer:
    """places=None / area_context=None mean "that dataset is unavailable" (-> unknown).
    An empty list / empty AreaContext means "available, nothing found"."""

    def __init__(self, config: dict, places: list[Place] | None,
                 area_context: AreaContext | None, weights: dict[str, float] | None = None,
                 incidents: list | None = None, outages: list | None = None, transit=None):
        check_scoring_params(config)
        self.config = config
        self.places = places
        self.area_context = area_context
        self.incidents = incidents      # Incident(lat, lng) list; None = source unavailable
        self.outages = outages          # Outage(lat, lng) list of OPEN streetlight reports; None = unavailable
        self.transit = transit          # TransitSnapshot (live arrivals); None = unavailable
        self.weights = dict(weights or config["weights"])
        if set(self.weights) != set(config["weights"]):
            raise ScoringConfigError("weights override must use the same factor names as the config")
        total = sum(self.weights.values())
        if total <= 0:
            raise ScoringConfigError("weights must sum to a positive number")
        self.weights = {k: v / total for k, v in self.weights.items()}

    # ---- factors -----------------------------------------------------------------
    def _open_places(self, seg: Segment, arrival: datetime) -> FactorResult:
        if self.places is None:
            return FactorResult("open_places", None, "open places: no place data (not sure)")
        radius = self.config["radii_m"]["open_place"]
        open_n = closed_n = unknown_n = 0
        for p in self.places:
            if point_to_polyline_m((p.lat, p.lng), seg.coordinates) <= radius:
                status = evaluate_open_status(p, arrival)
                if status is OpenStatus.OPEN:
                    open_n += 1
                elif status is OpenStatus.CLOSED:
                    closed_n += 1
                else:
                    unknown_n += 1
        table = self.config["factor_params"]["open_places_by_count"]
        value = float(table[min(open_n, len(table) - 1)])
        reason = f"{open_n} open place{'s' if open_n != 1 else ''} within {radius:g} m"
        if unknown_n:
            reason += f" ({unknown_n} nearby with hours not sure)"
        return FactorResult("open_places", value, reason,
                            {"open": open_n, "closed": closed_n, "unknown_hours": unknown_n})

    def _match_road(self, seg: Segment):
        if self.area_context is None:
            return None, None
        limit = self.config["radii_m"]["road_match"]
        best, best_d = None, math.inf
        for road in self.area_context.roads:
            d = point_to_polyline_m(seg.midpoint, road.coordinates)
            if d < best_d:
                best, best_d = road, d
        return (best, best_d) if best is not None and best_d <= limit else (None, None)

    def _road_factors(self, seg: Segment) -> tuple[FactorResult, FactorResult]:
        road, dist = self._match_road(seg)
        if road is None:
            why = "no road data" if self.area_context is None else "no mapped road within "\
                f"{self.config['radii_m']['road_match']:g} m"
            return (FactorResult("lighting", None, f"lighting not sure ({why})"),
                    FactorResult("main_road", None, f"road type not sure ({why})"))
        ev = {"osm_id": road.osm_id, "name": road.name, "road_class": road.road_class,
              "lit": road.lit, "match_distance_m": round(dist, 1)}
        params = self.config["factor_params"]
        lit_value = params["lighting_by_lit"].get(road.lit)
        if lit_value is None:
            lighting = FactorResult("lighting", None, "lighting not sure (not tagged)", ev)
        else:
            lighting = FactorResult("lighting", float(lit_value),
                                    "lit road" if road.lit == "yes" else "road tagged as not lit", ev)
        class_value = params["main_road_by_class"].get(road.road_class)
        if class_value is None:
            main = FactorResult("main_road", None, f"road type not sure ({road.road_class})", ev)
        else:
            main = FactorResult("main_road", float(class_value), f"{road.road_class} road", ev)
        return lighting, main

    def _help_points(self, seg: Segment) -> FactorResult:
        if self.area_context is None:
            return FactorResult("help_points", None, "help points: no area data (not sure)")
        radius = self.config["radii_m"]["help_point"]
        top = self.config["factor_params"]["help_point_max_value"]
        best, best_d = None, math.inf
        for h in self.area_context.help_points:
            d = point_to_polyline_m((h.lat, h.lng), seg.coordinates)
            if d < best_d:
                best, best_d = h, d
        if best is None:
            return FactorResult("help_points", 0.0, "no help point found in the queried area",
                                {"help_points_in_area": 0})
        value = max(0.0, top * (1 - best_d / radius))
        label = best.name or best.type.replace("_", " ")
        return FactorResult("help_points", value,
                            f"nearest help point: {best.type.replace('_', ' ')} ({label}), {best_d:.0f} m",
                            {"type": best.type, "name": best.name, "distance_m": round(best_d, 1)})

    def _turns(self, seg: Segment, prev: Segment | None) -> FactorResult:
        """Fewer sharp turns is easier to follow. Pure geometry, always known."""
        params = self.config["factor_params"]["turns_by_angle"]
        if prev is None:
            return FactorResult("turns", float(params["gentle"]), "start of the route (no turn)")
        angle = turn_angle_deg(bearing_deg(prev.start, prev.end), bearing_deg(seg.start, seg.end))
        if angle < params["gentle_max_deg"]:
            value, word = params["gentle"], "gentle"
        elif angle < params["moderate_max_deg"]:
            value, word = params["moderate"], "moderate"
        else:
            value, word = params["sharp"], "sharp"
        return FactorResult("turns", float(value), f"{word} turn ({angle:.0f} degrees)", {"angle_deg": round(angle, 1)})

    def _activity(self, seg: Segment, arrival: datetime) -> FactorResult:
        """ESTIMATE of how busy the street is: open places nearby x time of day. Not a count of people."""
        if self.places is None:
            return FactorResult("activity", None, "activity estimate: no place data (not sure)")
        radius = self.config["radii_m"]["activity"]
        open_n = sum(
            1 for p in self.places
            if point_to_polyline_m((p.lat, p.lng), seg.coordinates) <= radius
            and evaluate_open_status(p, arrival) is OpenStatus.OPEN)
        params = self.config["factor_params"]["activity"]
        hour = arrival.astimezone(PLACE_TZ).hour
        starts = sorted(int(k) for k in params["time_of_day"])
        key = str(max([s for s in starts if s <= hour], default=starts[0]))
        weight = params["time_of_day"][key]
        value = min(100.0, open_n * params["points_per_open_place"]) * weight
        return FactorResult(
            "activity", value,
            f"activity estimate: {open_n} open place{'s' if open_n != 1 else ''} within {radius:g} m at this hour "
            "(an estimate, not a count of people)", {"open": open_n, "time_weight": weight})

    def _incidents(self, seg: Segment) -> FactorResult:
        """Past police incident reports nearby. Low weight on purpose: it reflects policing as much as danger."""
        if self.incidents is None:
            return FactorResult("incidents", None, "past incidents: no data (not sure)")
        radius = self.config["radii_m"]["incident"]
        n = sum(1 for i in self.incidents if point_to_polyline_m((i.lat, i.lng), seg.coordinates) <= radius)
        value = max(0.0, 100.0 - n * self.config["factor_params"]["incident_points_each"])
        return FactorResult("incidents", value,
                            f"{n} past incident report{'s' if n != 1 else ''} within {radius:g} m (low weight)",
                            {"count": n})

    def _outage_penalty(self, lighting: FactorResult, seg: Segment) -> FactorResult:
        """Open streetlight-outage reports near the segment lower a KNOWN lighting value. They never
        turn "not sure" into a number: an outage report alone does not say the street is unlit."""
        if self.outages is None or lighting.value is None:
            return lighting
        radius = self.config["radii_m"]["outage"]
        n = sum(1 for o in self.outages if point_to_polyline_m((o.lat, o.lng), seg.coordinates) <= radius)
        if not n:
            return lighting
        value = max(0.0, lighting.value - n * self.config["factor_params"]["outage_penalty_each"])
        return FactorResult("lighting", value, f"{lighting.reason}; {n} open streetlight outage report"
                            f"{'s' if n != 1 else ''} nearby", {**lighting.evidence, "outages": n})

    def _transit(self, seg: Segment, arrival: datetime) -> FactorResult:
        """Vehicles predicted at nearby stops around the arrival time. Live feed only: later than the
        feed's horizon (or before it) is "not sure", never a guess."""
        snap = self.transit
        if snap is None:
            return FactorResult("transit", None, "transit: no live feed (not sure)")
        if arrival > snap.horizon or arrival < snap.fetched_at - timedelta(minutes=5):
            return FactorResult("transit", None, "transit: live arrivals only cover the next ~30 minutes (not sure)")
        radius = self.config["radii_m"]["transit"]
        win = self.config["factor_params"]["transit_window_min"]
        lo, hi = arrival - timedelta(minutes=win["before"]), arrival + timedelta(minutes=win["after"])
        n = sum(1 for a in snap.arrivals if lo <= a.time <= hi
                and point_to_polyline_m((a.lat, a.lng), seg.coordinates) <= radius)
        table = self.config["factor_params"]["transit_by_count"]
        return FactorResult("transit", float(table[min(n, len(table) - 1)]),
                            f"{n} bus or train arrival{'s' if n != 1 else ''} predicted within {radius:g} m "
                            f"in the next {win['after']} min (live feed)", {"arrivals": n})

    def _covered(self, seg: Segment, arrival: datetime) -> bool | None:
        """Continuity coverage (TECHNICAL_SPEC s5): an OPEN place or a help point within
        radii_m.coverage of the segment. True as soon as one is found. False only when both
        datasets are available and nothing could count (no place with unknown hours nearby either);
        otherwise None = not sure. Transit is not available yet."""
        radius = self.config["radii_m"]["coverage"]
        if self.area_context is not None and any(
                point_to_polyline_m((h.lat, h.lng), seg.coordinates) <= radius
                for h in self.area_context.help_points):
            return True
        maybe = False
        for p in self.places or []:
            if point_to_polyline_m((p.lat, p.lng), seg.coordinates) <= radius:
                status = evaluate_open_status(p, arrival)
                if status is OpenStatus.OPEN:
                    return True
                maybe = maybe or status is not OpenStatus.CLOSED
        if self.places is None or self.area_context is None or maybe:
            return None
        return False

    # ---- score -------------------------------------------------------------------
    def score_segment(self, seg: Segment, arrival: datetime, prev: Segment | None = None) -> SegmentScore:
        if arrival.tzinfo is None:
            raise ValueError("arrival must be timezone-aware")
        lighting, main_road = self._road_factors(seg)
        lighting = self._outage_penalty(lighting, seg)
        found = {f.name: f for f in (self._open_places(seg, arrival), lighting, main_road,
                                     self._help_points(seg), self._turns(seg, prev),
                                     self._activity(seg, arrival), self._incidents(seg),
                                     self._transit(seg, arrival))}
        for name in self.config["factor_params"]["not_yet_implemented"]:
            found[name] = FactorResult(name, None, f"{name.replace('_', ' ')}: not available yet (not sure)")
        factors = {name: found[name] for name in self.weights}   # config order
        known = {n: f for n, f in factors.items() if f.value is not None}
        known_w = sum(self.weights[n] for n in known)
        # "turns" is route geometry, not a condition of the street: with nothing else known there is
        # nothing to score, so the segment stays "not sure" instead of looking perfect.
        has_evidence = any(n != "turns" for n in known)
        score = (sum(self.weights[n] * f.value for n, f in known.items()) / known_w
                 if known and known_w > 0 and has_evidence else None)
        bands = self.config["bands"]
        band = ("unknown" if score is None else "green" if score >= bands["green_min"]
                else "yellow" if score >= bands["yellow_min"] else "red")
        stamps = [p.fetched_at for p in (self.places or [])]
        if self.area_context is not None:
            stamps.append(self.area_context.fetched_at)
        return SegmentScore(
            segment=seg, arrival_time=arrival, score=score, band=band, factors=factors,
            unknown_factors=[n for n, f in factors.items() if f.value is None],
            reasons=[f.reason for f in known.values()], known_weight_fraction=known_w,
            data_fetched_at=min(stamps) if stamps else None,
            covered=self._covered(seg, arrival))

    def score_route(self, segments: list[Segment], depart_at: datetime) -> list[SegmentScore]:
        """Arrival at each segment's start = depart_at + offset / walking speed."""
        speed = self.config["walking_speed_mps"]
        return [self.score_segment(s, depart_at + timedelta(seconds=s.offset_m / speed),
                                   segments[i - 1] if i else None)
                for i, s in enumerate(segments)]
