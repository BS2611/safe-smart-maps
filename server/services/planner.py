"""Route planner: candidates -> data -> scores -> three routes. The only place providers are wired.

Providers are injected so tests can swap them. A provider that fails never fails the request:
its factor becomes "not sure" and a warning is returned (TECHNICAL_SPEC section 6).
"""
import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from server.data.cache import TTLCache
from server.data.errors import DataSourceError, NotConfiguredError
from server.data.mapbox import RouteCandidate
from server.data.models import BoundingBox, Place
from server.services.continuity import SegmentInfo, route_continuity
from server.services.enrichment import DataBundle, build_route_facts
from server.services.geo import cumulative_m, haversine_m, point_at
from server.services.reasons import segment_reasons
from server.services.schemas import (
    ContinuityOut,
    HelpPointOut,
    LineString,
    RouteOut,
    RoutesRequest,
    RoutesResponse,
    SegmentOut,
)
from server.services.scoring import apply_priorities, compute_factors, is_covered, score_segment
from server.services.segmenter import Segment, segment_route
from server.services.selector import Candidate, select_routes

PAD_DEG = 0.001            # about 100 m of padding around the candidates
PLACES_CELL_DEG = 0.006    # about 650 m: one Bright Data lookup per cell
MAX_CELLS = 12
MAX_AREA_DIAGONAL_M = 7000.0
LABEL_ORDER = ["safest", "balanced", "fastest"]
ROUND_FACTORS = 1


class PlannerError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Providers:
    routing: Any          # get_walking_routes(origin, dest) -> list[RouteCandidate]
    places: Any           # get_places(BoundingBox, datetime) -> list[Place]
    osm: Any              # get_map_features(BoundingBox) -> MapFeatures
    sf: Any               # get_open_outages(area), get_recent_incidents(area)
    transit: Any          # get_active_stops(area, time)
    explainer: Any        # explain(facts) -> (text, source)


def bbox_of(candidates: list[RouteCandidate], pad: float = PAD_DEG) -> BoundingBox:
    lngs = [c[0] for cand in candidates for c in cand.coords]
    lats = [c[1] for cand in candidates for c in cand.coords]
    return BoundingBox(min(lats) - pad, min(lngs) - pad, max(lats) + pad, max(lngs) + pad)


def places_cells(coords_sets: list[list[tuple[float, float]]], size: float = PLACES_CELL_DEG,
                 limit: int = MAX_CELLS, pad: float = PAD_DEG) -> list[BoundingBox]:
    """Grid cells within `pad` degrees of any candidate route, in route order, at most `limit`.
    Routes are sampled about every 100 m so sparse polylines do not skip cells."""
    seen: dict[tuple[int, int], None] = {}
    for coords in coords_sets:
        cum = cumulative_m(coords)
        samples = [point_at(coords, cum, d) for d in range(0, int(cum[-1]) + 100, 100)]
        for lng, lat in samples:
            for dlat in (-pad, pad):
                for dlng in (-pad, pad):
                    seen.setdefault((math.floor((lat + dlat) / size), math.floor((lng + dlng) / size)), None)
    cells = list(seen)[:limit]
    return [BoundingBox(r * size, c * size, (r + 1) * size, (c + 1) * size) for r, c in cells]


def _round_area(area: BoundingBox) -> BoundingBox:
    f = 100  # 0.01 degree grid so nearby trips share cached map data
    return BoundingBox(math.floor(area.south * f) / f, math.floor(area.west * f) / f,
                       math.ceil(area.north * f) / f, math.ceil(area.east * f) / f)


class RoutePlanner:
    def __init__(self, providers: Providers, cfg: dict, cache: TTLCache | None = None,
                 static_cache: TTLCache | None = None):
        self.p = providers
        self.cfg = cfg
        self.cache = cache or TTLCache()
        # Street maps (OpenStreetMap) change rarely and the Overpass API is slow (20-30 s), so keep
        # them for a day. Listings, outages and incidents use the short cache above.
        self.static_cache = static_cache or TTLCache(24 * 3600)

    # ---------- data gathering ----------
    def _fetch_places(self, cells: list[BoundingBox], when: datetime) -> list[Place]:
        places: dict[str, Place] = {}
        errors: list[DataSourceError] = []

        def one(cell: BoundingBox) -> list[Place]:
            key = ("places", round(cell.south, 4), round(cell.west, 4))
            return self.cache.get_or_load(key, lambda: self.p.places.get_places(cell, when))

        with ThreadPoolExecutor(max_workers=min(6, max(1, len(cells)))) as pool:
            futures = [pool.submit(one, c) for c in cells]
            for f in futures:
                try:
                    for pl in f.result():
                        places[pl.place_id or f"{pl.name}|{pl.lat}|{pl.lng}"] = pl
                except DataSourceError as e:
                    errors.append(e)
        if errors and not places:
            raise errors[0]
        if errors:
            raise _Partial(list(places.values()), errors[0])
        return list(places.values())

    def _gather(self, area: BoundingBox, cells: list[BoundingBox], when: datetime
                ) -> tuple[DataBundle, list[str]]:
        warnings: list[str] = []
        bundle = DataBundle()
        rounded = _round_area(area)
        jobs: dict[str, Callable[[], Any]] = {
            "places": lambda: self._fetch_places(cells, when),
            "features": lambda: self.static_cache.get_or_load(
                ("osm", rounded), lambda: self.p.osm.get_map_features(rounded)),
            "outages": lambda: self.cache.get_or_load(
                ("sf311", rounded), lambda: self.p.sf.get_open_outages(rounded)),
            "incidents": lambda: self.cache.get_or_load(
                ("incidents", rounded), lambda: self.p.sf.get_recent_incidents(rounded)),
            "transit": lambda: self.p.transit.get_active_stops(area, when),
        }
        labels = {
            "places": "Live business listings", "features": "Street and lighting map data (OpenStreetMap)",
            "outages": "Streetlight outage reports", "incidents": "Past incident reports",
            "transit": "Transit schedules",
        }
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {name: pool.submit(fn) for name, fn in jobs.items()}
            for name, fut in futures.items():
                try:
                    results[name] = fut.result()
                except _Partial as part:
                    results[name] = part.partial
                    warnings.append(f"{labels[name]}: only part of the area loaded ({part.error.kind}).")
                except NotConfiguredError as e:
                    results[name] = None
                    warnings.append(f"{labels[name]}: not connected ({e}).")
                except DataSourceError as e:
                    results[name] = None
                    warnings.append(f"{labels[name]}: not available right now ({e.kind}).")
        bundle.places = results["places"]
        bundle.features = results["features"]
        bundle.outages = results["outages"]
        bundle.incidents = results["incidents"]
        bundle.transit = results["transit"]
        if bundle.transit is None and not any("Transit" in w for w in warnings):
            warnings.append("Transit schedules are not connected, so transit shows as not sure.")
        return bundle, warnings

    # ---------- scoring ----------
    def _score_candidate(self, cand: RouteCandidate, req: RoutesRequest, bundle: DataBundle,
                         weights: dict[str, float]):
        segments = segment_route(cand.coords, req.depart_time, cand.duration_s,
                                 self.cfg["segment_length_m"])
        facts = build_route_facts(segments, bundle, self.cfg)
        scored = []
        infos = []
        for seg, ev in zip(segments, facts.evidence, strict=True):
            factors = compute_factors(ev, seg.arrival_time, self.cfg)
            s = score_segment(factors, weights, self.cfg)
            scored.append((seg, ev, s))
            infos.append(SegmentInfo(seg.length_m, s.score, is_covered(ev, self.cfg)))
        return segments, facts, scored, route_continuity(infos, self.cfg)

    @staticmethod
    def _street_at(cand: RouteCandidate, distance_m: float) -> str | None:
        pos = 0.0
        for step in cand.steps:
            pos += step.distance_m
            if pos >= distance_m:
                return step.name or None
        return None

    def _fetched_at(self, bundle: DataBundle) -> datetime | None:
        times = [p.fetched_at for p in (bundle.places or [])]
        if bundle.features is not None:
            times.append(bundle.features.fetched_at)
        return min(times) if times else None

    # ---------- public ----------
    def plan(self, req: RoutesRequest) -> RoutesResponse:
        origin = (req.from_.lng, req.from_.lat)
        dest = (req.to.lng, req.to.lat)
        if haversine_m(origin, dest) < 30:
            raise PlannerError("BAD_REQUEST", "Start and destination are almost the same place.")
        try:
            candidates = self.p.routing.get_walking_routes(origin, dest)
        except NotConfiguredError as e:
            raise PlannerError("NOT_CONFIGURED", f"Routing is not set up on the server ({e}).") from None
        except DataSourceError as e:
            code = "UPSTREAM_TIMEOUT" if e.kind == "timeout" else "UPSTREAM_ERROR"
            raise PlannerError(code, "The routing service did not answer. Try again.") from None
        if not candidates:
            raise PlannerError("NO_ROUTE", "No walking route was found between these places.")

        area = bbox_of(candidates)
        diagonal = haversine_m((area.west, area.south), (area.east, area.north))
        if diagonal > MAX_AREA_DIAGONAL_M:
            raise PlannerError("BAD_REQUEST", "This trip is longer than we can check. Try under about 5 km.")
        cells = places_cells([c.coords for c in candidates])
        bundle, warnings = self._gather(area, cells, req.depart_time)

        weights = apply_priorities(self.cfg["weights"], req.settings.priorities)
        fastest_min = min(c.duration_s for c in candidates) / 60
        scored_by_id = {}
        for cand in candidates:
            scored_by_id[cand.route_id] = (cand, *self._score_candidate(cand, req, bundle, weights))

        selection = select_routes(
            [Candidate(cid, v[0].duration_s / 60, v[4].route_score) for cid, v in scored_by_id.items()],
            req.settings.max_extra_minutes, self.cfg)
        selection.sort(key=lambda s: LABEL_ORDER.index(s.labels[0]))

        fetched_at = self._fetched_at(bundle)
        routes: list[RouteOut] = []
        for sel in selection:
            cand, segments, facts, scored, cont = scored_by_id[sel.route_id]
            unknown_hours = facts.unknown_hours_places
            if unknown_hours and not any("opening hours" in w for w in warnings):
                noun, verb = ("place", "it was") if unknown_hours == 1 else ("places", "they were")
                warnings.append(f"{unknown_hours} {noun} had opening hours we could not read; "
                                f"{verb} not counted as open.")
            gap_note = None
            if cont.longest_gap_m and cont.longest_gap_start_m is not None:
                street = self._street_at(cand, cont.longest_gap_start_m + cont.longest_gap_m / 2)
                gap_note = f"on {street}" if street else None
            nearest = (HelpPointOut(name=facts.nearest_help[0], distance_m=round(facts.nearest_help[1]))
                       if facts.nearest_help else None)
            extra = round(cand.duration_s / 60 - fastest_min, 1)
            explain_facts = {
                "label": sel.labels[0], "duration_min": round(cand.duration_s / 60),
                "extra_min": extra, "coverage_pct": cont.coverage_pct,
                "longest_gap_m": cont.longest_gap_m, "longest_gap_note": gap_note,
                "worst_window_score": cont.worst_window_score, "route_score": cont.route_score,
                "open_places_count": facts.open_places_count if bundle.places is not None else None,
                "nearest_help_point": nearest.model_dump() if nearest else None,
            }
            text, source = self.p.explainer.explain(explain_facts)
            routes.append(RouteOut(
                label=sel.labels[0], also_labels=sel.labels[1:], route_id=cand.route_id,
                via=cand.via(), duration_min=round(cand.duration_s / 60, 1), extra_min=max(0.0, extra),
                distance_m=round(cand.distance_m), route_score=cont.route_score,
                continuity=ContinuityOut(coverage_pct=cont.coverage_pct, longest_gap_m=cont.longest_gap_m,
                                         longest_gap_note=gap_note,
                                         worst_window_score=cont.worst_window_score),
                open_places_count=facts.open_places_count if bundle.places is not None else None,
                nearest_help_point=nearest,
                geometry=LineString(coordinates=[tuple(c) for c in cand.coords]),
                segments=[self._segment_out(seg, ev, s, fetched_at) for seg, ev, s in scored],
                explanation=text, explanation_source=source,
            ))
        return RoutesResponse(scoring_version=self.cfg["version"], data_fetched_at=fetched_at,
                              routes=routes, warnings=warnings)

    @staticmethod
    def _segment_out(seg: Segment, ev, s, fetched_at: datetime | None) -> SegmentOut:
        return SegmentOut(
            segment_id=seg.segment_id, start=seg.start, end=seg.end, length_m=round(seg.length_m, 1),
            arrival_time=seg.arrival_time, score=s.score, band=s.band,
            factors={k: (None if v is None else round(v, ROUND_FACTORS)) for k, v in s.factors.items()},
            reasons=segment_reasons(ev, s.factors), data_fetched_at=fetched_at, confidence=s.confidence,
        )


class _Partial(Exception):
    """Some map cells failed but we have data from the others."""

    def __init__(self, partial: list[Place], error: DataSourceError):
        super().__init__("partial")
        self.partial = partial
        self.error = error

