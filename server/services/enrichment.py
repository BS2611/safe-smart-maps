"""Turns raw provider data into per-segment Evidence (pure: no network).

Honesty rule: a source that failed or is not configured gives None ("not sure"), never zero.
"""
from dataclasses import dataclass, field
from datetime import timedelta

from server.data.models import Place
from server.data.opening_hours import OpenStatus, evaluate_open_status
from server.data.osm import HelpPoint, MapFeatures, Way
from server.data.sf_open_data import Incident, Outage
from server.data.transit import ActiveStop
from server.services.geo import haversine_m, point_to_polyline_m
from server.services.scoring import Evidence
from server.services.segmenter import Segment

ROAD_RANK = {
    "trunk": 6, "primary": 5, "secondary": 4, "tertiary": 3,
    "residential": 2, "unclassified": 2, "living_street": 2,
}
WAY_DISTANCE_M = 20.0
STORE_24H_CATEGORIES = {"convenience_store", "pharmacy", "gas_station"}


@dataclass
class DataBundle:
    """None for a source means "not available" (failed or not configured)."""
    places: list[Place] | None = None
    features: MapFeatures | None = None
    outages: list[Outage] | None = None
    incidents: list[Incident] | None = None
    transit: list[ActiveStop] | None = None


@dataclass(frozen=True)
class RouteFacts:
    evidence: list[Evidence]
    open_places_count: int
    nearest_help: tuple[str, float] | None  # (name, distance in metres)
    unknown_hours_places: int = 0
    open_place_names: list[str] = field(default_factory=list)


def _way_attributes(mid: tuple[float, float], ways: list[Way]) -> tuple[str | None, bool | None, bool]:
    near = [w for w in ways if point_to_polyline_m(mid, w.geometry) <= WAY_DISTANCE_M]
    if not near:
        return None, None, False
    best = max(near, key=lambda w: ROAD_RANK.get(w.highway or "", 1))
    lit_values = [w.lit for w in near if w.lit is not None]
    lit = True if any(lit_values) else (False if lit_values else None)
    return best.highway, lit, any(w.tunnel for w in near)


def _place_weight(place: Place, cfg: dict) -> float:
    w = cfg["open_place_weights"]
    boosted = place.is_24h or place.category in w["boosted_categories"]
    return w["boosted"] if boosted else w["default"]


def help_points_from(bundle: DataBundle) -> list[HelpPoint]:
    points: list[HelpPoint] = list(bundle.features.help_points) if bundle.features else []
    for p in bundle.places or []:
        if p.is_24h and p.category in STORE_24H_CATEGORIES:
            points.append(HelpPoint(p.name, "store_24h", p.lng, p.lat, p.source))
    return points


def build_route_facts(segments: list[Segment], bundle: DataBundle, cfg: dict) -> RouteFacts:
    radii = cfg["radii_m"]
    help_points = help_points_from(bundle)
    help_known = bundle.features is not None or bundle.places is not None
    unknown_hours = (
        sum(1 for p in bundle.places if evaluate_open_status(p, segments[0].arrival_time)
            is OpenStatus.UNKNOWN) if bundle.places else 0
    )
    evidence: list[Evidence] = []
    open_names: dict[str, str] = {}
    nearest_help: tuple[str, float] | None = None

    for seg in segments:
        open_weight = open_count = None
        covered = None
        if bundle.places is not None:
            open_weight, open_count, covered = 0.0, 0, False
            for p in bundle.places:
                d = haversine_m(seg.mid, (p.lng, p.lat))
                if d > radii["activity"]:
                    continue
                if evaluate_open_status(p, seg.arrival_time) is not OpenStatus.OPEN:
                    continue
                open_count += 1
                if d <= radii["coverage"]:
                    covered = True
                if d <= radii["open_place"]:
                    open_weight += _place_weight(p, cfg)
                    open_names[p.place_id or f"{p.name}|{p.lat}|{p.lng}"] = p.name

        road, lit, tunnel = (None, None, False)
        if bundle.features is not None:
            road, lit, tunnel = _way_attributes(seg.mid, bundle.features.ways)

        help_distance = None
        if help_known and help_points:
            nearest = min(help_points, key=lambda h: haversine_m(seg.mid, (h.lng, h.lat)))
            d = haversine_m(seg.mid, (nearest.lng, nearest.lat))
            if d <= radii["help_point"]:
                help_distance = d
            if nearest_help is None or d < nearest_help[1]:
                nearest_help = (nearest.name, d)

        outages = (
            sum(1 for o in bundle.outages if haversine_m(seg.mid, (o.lng, o.lat)) <= radii["outage"])
            if bundle.outages is not None else None
        )
        incidents = (
            sum(1 for i in bundle.incidents if haversine_m(seg.mid, (i.lng, i.lat)) <= radii["incident"])
            if bundle.incidents is not None else None
        )
        transit = None
        if bundle.transit is not None:
            transit = any(
                haversine_m(seg.mid, (s.lng, s.lat)) <= radii["help_point"]
                and timedelta(0) <= s.next_departure - seg.arrival_time <= timedelta(minutes=15)
                for s in bundle.transit
            )

        evidence.append(Evidence(
            open_weight_50m=open_weight, open_count_100m=open_count, covered_by_open_place=covered,
            lit=lit, outages_50m=outages, road_class=road, help_known=help_known,
            help_distance_m=help_distance, transit_active=transit, incidents_100m=incidents,
            turn_angle_deg=seg.turn_angle_deg, tunnel=tunnel,
        ))

    return RouteFacts(evidence, len(open_names), nearest_help, unknown_hours, sorted(open_names.values()))
