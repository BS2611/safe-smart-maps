"""Route planner: candidates -> data -> segment scores -> continuity -> three routes.

This only wires modules that already exist: Mapbox candidates (data/mapbox.py + candidates.py),
the places cache (data/cache.py), OSM context (data/osm.py), the segmenter and SegmentScorer
(segmenter.py, segment_scoring.py), then continuity, selector and the explainer. No new scoring
rules live here. Providers are injected so tests can swap them.

A data source that is missing or fails never fails the request: its factor stays "not sure"
(None) and a warning is returned (TECHNICAL_SPEC section 6).
"""
import math
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from server.data.mapbox import MapboxError, RouteCandidate
from server.data.models import AreaContext, BoundingBox, Place
from server.data.opening_hours import OpenStatus, evaluate_open_status
from server.data.osm import OsmError
from server.data.sf_open_data import SfDataError
from server.data.ttl_cache import TTLCache
from server.services.candidates import generate_candidates
from server.services.continuity import compute_continuity
from server.services.geo import haversine_m, point_to_polyline_m
from server.services.places_lookup import places_for_area
from server.services.schemas import (
    ContinuityOut,
    HelpPointOut,
    LineString,
    RouteOut,
    RoutesRequest,
    RoutesResponse,
    SegmentOut,
    StretchAuditOut,
)
from server.services.segment_scoring import SegmentScore, SegmentScorer
from server.services.segmenter import segment_route
from server.services.selector import Candidate, select_routes

PAD_DEG = 0.001            # about 100 m of padding around the candidates
LABEL_ORDER = ["safest", "balanced", "fastest"]
AUDIT_PER_ROUTE = int(os.environ.get("AUDIT_MAX_CALLS_PER_REQUEST", "3") or 3)   # photos Claude reads per request
AUDIT_MIN_SEPARATION_M = 100
# The UI uses friendlier names for the "what matters most" chips.
PRIORITY_ALIASES = {
    "lighting": "lighting", "open_places": "open_places", "main_road": "main_road",
    "main_roads": "main_road", "help_points": "help_points", "transit": "transit",
}


class PlannerError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Providers:
    routing: Any          # get_walking_routes(origin, dest, waypoints=()) -> list[RouteCandidate]
    places: Any           # CachedPlacesProvider (reads saved listings only; never fetches)
    context: Any          # ContextProvider: get_area_context(BoundingBox) -> AreaContext
    explainer: Any        # explain(facts) -> (text, source)
    incidents: Any = None # get_recent_incidents(area) -> list, or None if not configured
    outages: Any = None   # get_open_outages(area) -> list, or None if not configured
    transit: Any = None   # TransitSchedule, or None when no GTFS feed is configured
    auditor: Any = None   # StreetAuditor-like: audit(photo) -> StretchAudit | None; needs `photos` too
    photos: Any = None    # PhotoSource-like: photo_near(lat, lng) -> Photo | None


def apply_priorities(weights: dict[str, float], priorities: list[str], boost: float) -> dict[str, float]:
    """Boost up to two chosen factors, then renormalize so weights still sum to 1.0."""
    chosen = {PRIORITY_ALIASES[p] for p in priorities if p in PRIORITY_ALIASES}
    boosted = {k: v * (boost if k in chosen else 1.0) for k, v in weights.items()}
    total = sum(boosted.values())
    return {k: v / total for k, v in boosted.items()}


def bbox_of(candidates: list[RouteCandidate], pad: float = PAD_DEG) -> BoundingBox:
    lngs = [c[0] for cand in candidates for c in cand.coordinates]
    lats = [c[1] for cand in candidates for c in cand.coordinates]
    return BoundingBox(min(lats) - pad, min(lngs) - pad, max(lats) + pad, max(lngs) + pad)


def _round_area(area: BoundingBox) -> BoundingBox:
    f = 100  # 0.01 degree grid so nearby trips share the cached map data
    return BoundingBox(math.floor(area.south * f) / f, math.floor(area.west * f) / f,
                       math.ceil(area.north * f) / f, math.ceil(area.east * f) / f)


def confidence_for(known_weight_fraction: float, cfg: dict) -> str:
    c = cfg["confidence"]
    if known_weight_fraction >= c["high_min_known_weight"]:
        return "high"
    return "low" if known_weight_fraction >= c["low_min_known_weight"] else "unknown"


class RoutePlanner:
    def __init__(self, providers: Providers, cfg: dict, context_cache: TTLCache | None = None):
        self.p = providers
        self.cfg = cfg
        # OpenStreetMap (Overpass) is slow (20-40 s) and changes rarely: keep it for a day.
        self.context_cache = context_cache or TTLCache(24 * 3600)

    # ---------- data gathering ----------
    def _context(self, area: BoundingBox, warnings: list[str]) -> AreaContext | None:
        rounded = _round_area(area)
        try:
            return self.context_cache.get_or_load(
                ("osm", rounded), lambda: self.p.context.get_area_context(rounded))
        except OsmError:
            warnings.append("Street and lighting map data (OpenStreetMap): not available right now, "
                            "so lighting, road type, help points and the activity estimate show as not sure.")
            return None

    def _cached_points(self, name: str, area: BoundingBox, loader, warning: str, warnings: list[str]):
        if loader is None:
            return None
        rounded = _round_area(area)
        try:
            return self.context_cache.get_or_load((name, rounded), lambda: loader(rounded))
        except SfDataError:
            warnings.append(warning)
            return None

    def _audit_stretches(self, scored: list[SegmentScore]) -> list[StretchAuditOut]:
        """Ask Claude to look at street photos of the weakest or not-sure stretches (a few, spread apart).
        Best effort: any problem just means fewer or no audits. Never changes scores."""
        if self.p.auditor is None or self.p.photos is None:
            return []
        limit = AUDIT_PER_ROUTE
        weak = sorted((s for s in scored if s.band != "green"),
                      key=lambda s: (s.score is not None, s.score if s.score is not None else 0))
        picked: list[SegmentScore] = []
        for s in weak:
            if all(haversine_m(s.segment.midpoint, q.segment.midpoint) >= AUDIT_MIN_SEPARATION_M for q in picked):
                picked.append(s)
            if len(picked) >= limit:
                break

        def one(s: SegmentScore):
            try:
                lat, lng = s.segment.midpoint
                photo = self.p.photos.photo_near(lat, lng)
                audit = self.p.auditor.audit(photo) if photo is not None else None
            except Exception:  # noqa: BLE001 - audits are optional; never break a route request
                return None
            return None if audit is None else StretchAuditOut(
                segment_id=s.segment.segment_id, photo_id=audit.photo_id,
                photo_url=f"https://www.mapillary.com/app/?pKey={audit.photo_id}", captured_at=audit.captured_at,
                attribution=audit.attribution, streetlights_visible=audit.streetlights_visible,
                open_storefronts=audit.open_storefronts, sidewalk_visibility=audit.sidewalk_visibility,
                construction=audit.construction, confidence=audit.confidence, evidence=audit.evidence,
                label=audit.label)

        if not picked:
            return []
        with ThreadPoolExecutor(max_workers=len(picked)) as pool:
            return [a for a in pool.map(one, picked) if a is not None]

    # ---------- per-route work ----------
    def _route_facts(self, cand: RouteCandidate, scored: list[SegmentScore],
                     places: list[Place] | None, context: AreaContext | None) -> dict:
        """Distinct open places and unreadable-hours places near the route, nearest help point."""
        radius = self.cfg["radii_m"]["open_place"]
        open_names: dict[str, str] = {}
        unknown_hours: set[str] = set()
        for s in scored:
            for p in places or []:
                if point_to_polyline_m((p.lat, p.lng), s.segment.coordinates) > radius:
                    continue
                key = p.place_id or f"{p.name}|{p.lat}|{p.lng}"
                status = evaluate_open_status(p, s.arrival_time)
                if status is OpenStatus.OPEN:
                    open_names[key] = p.name
                elif status is OpenStatus.UNKNOWN:
                    unknown_hours.add(key)
        nearest = None
        if context is not None:
            line = cand.as_lat_lng()
            limit = self.cfg["radii_m"]["help_point"]
            for h in context.help_points:
                d = point_to_polyline_m((h.lat, h.lng), line)
                if d <= limit and (nearest is None or d < nearest[1]):
                    nearest = (h.name or h.type.replace("_", " "), d)
        return {"open_count": len(open_names), "unknown_hours": len(unknown_hours - set(open_names)),
                "nearest_help": nearest}

    def _score_candidate(self, cand: RouteCandidate, req: RoutesRequest, scorer: SegmentScorer):
        segments = segment_route(cand.as_lat_lng(), self.cfg["segment_length_m"])
        if not segments:
            return None
        scored = scorer.score_route(segments, req.depart_time)
        return scored, compute_continuity(self.cfg, scored)

    def _segment_out(self, s: SegmentScore) -> SegmentOut:
        data = s.to_dict()
        data["confidence"] = confidence_for(s.known_weight_fraction, self.cfg)
        return SegmentOut.model_validate(data)

    # ---------- public ----------
    def plan(self, req: RoutesRequest) -> RoutesResponse:
        origin = (req.from_.lng, req.from_.lat)
        dest = (req.to.lng, req.to.lat)
        if haversine_m((origin[1], origin[0]), (dest[1], dest[0])) < 30:
            raise PlannerError("BAD_REQUEST", "Start and destination are almost the same place.")
        try:
            candidates = generate_candidates(self.p.routing, origin, dest, self.cfg)
        except MapboxError as e:
            raise self._routing_error(e) from None
        except ValueError:
            raise PlannerError("BAD_REQUEST", "Start or destination is not a valid place.") from None
        if not candidates:
            raise PlannerError("NO_ROUTE", "No walking route was found between these places.")

        area = bbox_of(candidates)
        diagonal = haversine_m((area.south, area.west), (area.north, area.east))
        if diagonal > self.cfg["candidates"]["max_route_diagonal_m"]:
            raise PlannerError("BAD_REQUEST", "This trip is longer than we can check. Try under about 5 km.")

        warnings: list[str] = []
        found = places_for_area(self.p.places, area)
        if found.warning:
            warnings.append(found.warning)
        context = self._context(area, warnings)
        incidents = self._cached_points(
            "incidents", area, None if self.p.incidents is None else self.p.incidents.get_recent_incidents,
            "Past incident reports are not available right now, so that part of the score shows as not sure.",
            warnings)
        outages = self._cached_points(
            "outages", area, None if self.p.outages is None else self.p.outages.get_open_outages,
            "Streetlight outage reports are not available right now, so lighting uses the map tag only.",
            warnings)
        transit = self.p.transit
        if transit is None:
            warnings.append("Transit schedules are not configured, so transit shows as not sure.")
        elif getattr(transit, "failed", False):
            warnings.append("Transit schedules could not be read, so transit shows as not sure.")
            transit = None
        elif getattr(transit, "partial_failure", False):
            warnings.append("One transit feed could not be read. Stops from the feed that loaded are still used.")
        weights = apply_priorities(self.cfg["weights"], req.settings.priorities,
                                   self.cfg["priorities"]["boost"])
        scorer = SegmentScorer(self.cfg, found.places, context, weights,
                               incidents=incidents, outages=outages, transit=transit)

        results = {}
        for cand in candidates:
            outcome = self._score_candidate(cand, req, scorer)
            if outcome is not None:
                results[cand.id] = (cand, *outcome)
        if not results:
            raise PlannerError("NO_ROUTE", "No walking route was found between these places.")

        fastest_min = min(v[0].duration_s for v in results.values()) / 60
        selection = select_routes(
            [Candidate(cid, v[0].duration_s / 60, v[2].route_score) for cid, v in results.items()],
            req.settings.max_extra_minutes, self.cfg)
        selection.sort(key=lambda s: LABEL_ORDER.index(s.labels[0]))

        routes: list[RouteOut] = []
        unknown_hours_seen = 0
        for sel in selection:
            cand, scored, result = results[sel.route_id]
            cont = ContinuityOut.model_validate(result.to_dict()["continuity"])
            route_score = result.to_dict()["route_score"]
            facts = self._route_facts(cand, scored, found.places, context)
            unknown_hours_seen = max(unknown_hours_seen, facts["unknown_hours"])
            nearest = (HelpPointOut(name=facts["nearest_help"][0], distance_m=round(facts["nearest_help"][1]))
                       if facts["nearest_help"] else None)
            open_count = facts["open_count"] if found.places is not None else None
            extra = round(cand.duration_s / 60 - fastest_min, 1)
            text, source = self.p.explainer.explain({
                "label": sel.labels[0], "duration_min": round(cand.duration_s / 60),
                "extra_min": extra, "coverage_pct": cont.coverage_pct,
                "longest_gap_m": cont.longest_gap_m, "longest_gap_note": cont.longest_gap_note,
                "worst_window_score": cont.worst_window_score, "route_score": route_score,
                "open_places_count": open_count,
                "nearest_help_point": nearest.model_dump() if nearest else None,
            })
            routes.append(RouteOut(
                label=sel.labels[0], also_labels=sel.labels[1:], route_id=cand.id, via=[],
                duration_min=round(cand.duration_s / 60, 1), extra_min=max(0.0, extra),
                distance_m=round(cand.distance_m), route_score=route_score, continuity=cont,
                open_places_count=open_count, nearest_help_point=nearest,
                geometry=LineString(coordinates=list(cand.coordinates)),
                segments=[self._segment_out(s) for s in scored],
                explanation=text, explanation_source=source,
                street_photo_audits=self._audit_stretches(scored) if not routes else [],
            ))
        if unknown_hours_seen:
            noun, verb = ("place", "it was") if unknown_hours_seen == 1 else ("places", "they were")
            warnings.append(f"{unknown_hours_seen} {noun} had opening hours we could not read; "
                            f"{verb} not counted as open.")
        stamps = [t for t in (found.fetched_at, context.fetched_at if context else None) if t]
        return RoutesResponse(scoring_version=self.cfg["version"],
                              data_fetched_at=min(stamps) if stamps else None,
                              routes=routes, warnings=warnings)

    @staticmethod
    def _routing_error(e: MapboxError) -> PlannerError:
        if e.kind == "not_configured":
            return PlannerError("NOT_CONFIGURED", "Routing is not set up on the server (MAPBOX_TOKEN is not set).")
        if e.kind == "timeout":
            return PlannerError("UPSTREAM_TIMEOUT", "The routing service did not answer in time. Try again.")
        if e.kind == "empty":
            return PlannerError("NO_ROUTE", "No walking route was found between these places.")
        return PlannerError("UPSTREAM_ERROR", "The routing service did not answer. Try again.")
