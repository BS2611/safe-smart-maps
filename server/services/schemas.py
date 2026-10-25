"""Request/response models for POST /v1/routes. Shapes follow docs/agent-context/CONTRACTS.md."""
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class LatLng(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class Settings(BaseModel):
    max_extra_minutes: float = Field(default=10, ge=0, le=20)
    with_companion: bool = False
    priorities: list[str] = Field(default_factory=list, max_length=2)


class RoutesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: LatLng = Field(alias="from")
    to: LatLng
    depart_time: AwareDatetime
    settings: Settings = Field(default_factory=Settings)


Band = Literal["green", "yellow", "red", "unknown"]
Confidence = Literal["high", "low", "unknown"]
Label = Literal["safest", "balanced", "fastest"]


class SegmentOut(BaseModel):
    segment_id: str
    start: tuple[float, float]       # [lng, lat]
    end: tuple[float, float]         # [lng, lat]
    length_m: float
    arrival_time: datetime
    score: float | None
    band: Band
    factors: dict[str, float | None]
    unknown_factors: list[str]
    known_weight_fraction: float
    reasons: list[str]
    data_fetched_at: datetime | None
    confidence: Confidence


class ContinuityOut(BaseModel):
    coverage_pct: float | None
    longest_gap_m: float
    longest_gap_note: str | None
    worst_window_score: float | None


class HelpPointOut(BaseModel):
    name: str
    distance_m: float


class LineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]]   # [lng, lat]


class RouteOut(BaseModel):
    label: Label
    also_labels: list[Label]
    route_id: str
    via: list[str]
    duration_min: float
    extra_min: float
    distance_m: float
    route_score: float | None
    continuity: ContinuityOut
    open_places_count: int | None
    nearest_help_point: HelpPointOut | None
    geometry: LineString
    segments: list[SegmentOut]
    explanation: str
    explanation_source: Literal["ai", "template"]


class RoutesResponse(BaseModel):
    api_version: str = "1"
    scoring_version: str
    data_fetched_at: datetime | None
    routes: list[RouteOut]
    warnings: list[str]


class ErrorBody(BaseModel):
    code: Literal["NO_ROUTE", "UPSTREAM_TIMEOUT", "UPSTREAM_ERROR", "BAD_REQUEST", "NOT_CONFIGURED"]
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
