"""Per-segment context matching and weighted score (scoring_v1, hackathon-v1 heuristics).

Consumes only normalized project models (Place, AreaContext). It never sees Bright Data,
Overpass or Mapbox JSON, and it never fetches: the caller passes what was read from the cache.
All constants come from scoring/scoring_v1.json. A factor value is 0-100, or None = "not sure".
The score is NOT a safety claim; it summarizes contextual signals.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from server.data.models import AreaContext, Place
from server.data.opening_hours import OpenStatus, evaluate_open_status
from server.data.sf_open_data import Incident, Outage
from server.services.geo import haversine_m, point_to_polyline_m
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
                 incidents: list[Incident] | None = None, outages: list[Outage] | None = None,
                 transit=None):
        check_scoring_params(config)
        self.config = config
        self.places = places
        self.area_context = area_context
        self.incidents = incidents          # None = dataset unavailable; [] = none reported
        self.outages = outages              # None = 311 unavailable; [] = no open outage
        self.transit = transit              # None = no schedule; else .active_stops(when, window)
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
        lit_value, lit_reason = self._lighting_value(seg, road.lit)
        if lit_value is None:
            lighting = FactorResult("lighting", None, lit_reason, ev)
        else:
            lighting = FactorResult("lighting", lit_value, lit_reason, ev)
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

    def _count_near(self, seg: Segment, points, radius: float) -> int:
        return sum(1 for p in points if point_to_polyline_m((p.lat, p.lng), seg.coordinates) <= radius)

    def _lighting_value(self, seg: Segment, lit: str) -> tuple[float | None, str]:
        """Unknown lit tags stay unknown. Lamps or an open outage can still be evidence."""
        params = self.config["factor_params"]
        lamps = 0
        if self.area_context is not None:
            lamps = self._count_near(seg, self.area_context.street_lamps, params["streetlight_radius_m"])
        outages = None if self.outages is None else self._count_near(seg, self.outages, params["outage_radius_m"])
        tagged = params["lighting_by_lit"].get(lit)
        if tagged is None:
            if lamps > 0:
                table = params["lighting_from_lamps"]
                value = float(table[min(lamps, len(table) - 1)])
                reason = f"{lamps} street lamp{'s' if lamps != 1 else ''} nearby (street lighting tag is not sure)"
            elif outages:
                value = float(params["lighting_outage_only"])
                reason = "open streetlight outage nearby (street lighting tag is not sure)"
            else:
                return None, "lighting not sure (not tagged)"
            if value <= 0:
                return None, "lighting not sure (not tagged)"
            if outages and lamps:
                value = max(float(params["lighting_outage_only"]), value - float(params["lighting_outage_penalty"]))
                if value <= 0:
                    return None, "lighting not sure (not tagged)"
                reason += f"; {outages} open streetlight outage{'s' if outages != 1 else ''} nearby"
            return value, reason
        value = float(tagged)
        reason = "lit road" if lit == "yes" else "road tagged as not lit"
        if lit == "no" and lamps:
            value = max(value, float(params.get("lighting_unlit_with_lamps", 40)))
            reason = "road tagged as not lit, street lamp nearby"
        elif lit == "yes" and lamps:
            reason = f"lit road, {lamps} street lamp{'s' if lamps != 1 else ''} nearby"
        if outages and lit == "yes":
            value = max(float(params["lighting_outage_only"]), value - float(params["lighting_outage_penalty"]))
            reason += f"; {outages} open streetlight outage{'s' if outages != 1 else ''} nearby"
        return value, reason

    def _turns(self, seg: Segment, prev_bearing: float | None) -> FactorResult:
        params = self.config["factor_params"]
        change = _max_turn_deg(seg.coordinates, prev_bearing)
        if change < params["turn_min_deg"]:
            value = float(params["turn_score_straight"])
            reason = "straight stretch"
        elif change < params["turn_moderate_deg"]:
            value = float(params["turn_score_moderate"])
            reason = f"moderate turn ({change:.0f}°)"
        elif change < params["turn_sharp_deg"]:
            value = float(params["turn_score_sharp"])
            reason = f"sharp turn ({change:.0f}°)"
        else:
            value = float(params["turn_score_reversal"])
            reason = f"very sharp turn ({change:.0f}°)"
        road, _dist = self._match_road(seg)
        dark = road is not None and road.lit == "no" and change >= params["turn_min_deg"]
        if dark:
            value = max(0.0, value - params["dark_turn_penalty"])
            reason += " on a street tagged as not lit"
        if road is not None and road.tunnel:
            value = max(0.0, value - params["tunnel_penalty"])
            reason += "; underpass"
        return FactorResult("turns", value, reason, {"turn_deg": round(change, 1), "dark": dark,
                                                      "tunnel": bool(road and road.tunnel)})

    def _activity(self, seg: Segment, arrival: datetime) -> FactorResult:
        if self.area_context is None or not self.area_context.activity_known:
            return FactorResult("activity", None, "activity not sure (no place-density data)")
        params = self.config["factor_params"]
        count = self._count_near(seg, self.area_context.activity_points, params["activity_radius_m"])
        table = params["activity_by_count"]
        base = float(table[min(count, len(table) - 1)])
        local_hour = arrival.astimezone(ZoneInfo("America/Los_Angeles")).hour
        # arrival is already timezone-aware; use its clock hour in that zone
        factors = params["activity_time_factor"]
        if local_hour < params["activity_late_end_hour"]:
            label, mult = "late night", factors["late"]
        elif local_hour >= params["activity_evening_start_hour"]:
            label, mult = "evening", factors["evening"]
        else:
            label, mult = "daytime", factors["day"]
        value = max(0.0, min(100.0, base * mult))
        return FactorResult(
            "activity", value,
            f"activity estimate: {count} busy place{'s' if count != 1 else ''} nearby, {label}",
            {"places": count, "time": label})

    def _incidents(self, seg: Segment) -> FactorResult:
        if self.incidents is None:
            return FactorResult("incidents", None, "past incidents not sure (no incident data)")
        params = self.config["factor_params"]
        count = self._count_near(seg, self.incidents, params["incident_radius_m"])
        table = params["incidents_by_count"]
        value = float(table[min(count, len(table) - 1)])
        if count == 0:
            reason = f"no incident reports within {params['incident_radius_m']:g} m"
        else:
            reason = (f"{count} incident report{'s' if count != 1 else ''} within "
                      f"{params['incident_radius_m']:g} m (low weight; reports can reflect policing patterns)")
        return FactorResult("incidents", value, reason, {"reports": count})

    def _transit(self, seg: Segment, arrival: datetime) -> FactorResult:
        if self.transit is None:
            return FactorResult("transit", None, "transit not sure (no schedule)")
        params = self.config["factor_params"]
        window = int(params["transit_window_min"])
        stops = self.transit.active_stops(arrival, window)
        if not stops:
            return FactorResult("transit", 0.0, f"no stop with service in the next {window} minutes",
                                {"active_stops": 0})
        best, best_d = None, math.inf
        for stop in stops:
            dist = point_to_polyline_m((stop.lat, stop.lng), seg.coordinates)
            if dist < best_d:
                best, best_d = stop, dist
        radius = params["transit_radius_m"]
        if best_d > radius:
            return FactorResult("transit", 0.0, f"nearest running stop is {best_d:.0f} m away",
                                {"distance_m": round(best_d, 1)})
        value = max(0.0, 100.0 * (1 - best_d / radius))
        return FactorResult("transit", value,
                            f"{best.name}, {best_d:.0f} m, departure within {window} minutes",
                            {"name": best.name, "distance_m": round(best_d, 1)})

    def _covered(self, seg: Segment, arrival: datetime) -> bool | None:
        """Continuity coverage (TECHNICAL_SPEC s5): an OPEN place or a help point within
        radii_m.coverage of the segment. True as soon as one is found. False only when both
        datasets are available and nothing could count (no place with unknown hours nearby either);
        otherwise None = not sure. An active transit stop counts only when a schedule is loaded."""
        radius = self.config["radii_m"]["coverage"]
        if self.transit is not None:
            window = int(self.config["factor_params"]["transit_window_min"])
            for stop in self.transit.active_stops(arrival, window):
                if point_to_polyline_m((stop.lat, stop.lng), seg.coordinates) <= radius:
                    return True
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
    def score_segment(self, seg: Segment, arrival: datetime,
                      prev_bearing: float | None = None) -> SegmentScore:
        if arrival.tzinfo is None:
            raise ValueError("arrival must be timezone-aware")
        lighting, main_road = self._road_factors(seg)
        found = {f.name: f for f in (
            self._open_places(seg, arrival), lighting, main_road, self._help_points(seg),
            self._transit(seg, arrival), self._activity(seg, arrival), self._incidents(seg),
            self._turns(seg, prev_bearing))}
        factors = {name: found[name] for name in self.weights}   # config order
        known = {n: f for n, f in factors.items() if f.value is not None}
        known_w = sum(self.weights[n] for n in known)
        score = sum(self.weights[n] * f.value for n, f in known.items()) / known_w if known else None
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
        scored = []
        prev = None
        for s in segments:
            scored.append(self.score_segment(
                s, depart_at + timedelta(seconds=s.offset_m / speed), prev))
            prev = _final_bearing(s.coordinates)
        return scored


def _bearing(a, b) -> float | None:
    if haversine_m(a, b) < 1:
        return None
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _delta(a: float, b: float) -> float:
    return abs((b - a + 180) % 360 - 180)


def _initial_bearing(coords) -> float | None:
    for a, b in zip(coords, coords[1:], strict=False):
        bearing = _bearing(a, b)
        if bearing is not None:
            return bearing
    return None


def _final_bearing(coords) -> float | None:
    for a, b in reversed(list(zip(coords, coords[1:], strict=False))):
        bearing = _bearing(a, b)
        if bearing is not None:
            return bearing
    return None


def _max_turn_deg(coords, prev_bearing: float | None) -> float:
    bearings = []
    for a, b in zip(coords, coords[1:], strict=False):
        bearing = _bearing(a, b)
        if bearing is not None:
            bearings.append(bearing)
    deltas = []
    if prev_bearing is not None and bearings:
        deltas.append(_delta(prev_bearing, bearings[0]))
    deltas.extend(_delta(a, b) for a, b in zip(bearings, bearings[1:], strict=False))
    return max(deltas) if deltas else 0.0
