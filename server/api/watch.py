"""Watch relay endpoints. Contract: CONTRACTS.md "Watch relay endpoints". All state is in memory."""
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from server.services.watch_relay import RelayError, WatchRelay

router = APIRouter()

_STATUS = {"BAD_REQUEST": 400, "BAD_CODE": 400, "UNAUTHORIZED": 401, "NOT_FOUND": 404,
           "TOO_MANY_ATTEMPTS": 429}


def relay_of(request: Request) -> WatchRelay:
    if not hasattr(request.app.state, "watch_relay"):
        request.app.state.watch_relay = WatchRelay()
    return request.app.state.watch_relay


def _error(e: RelayError) -> JSONResponse:
    # Same shape as the rest of the API. Messages never echo codes, tokens or readings.
    return JSONResponse(status_code=_STATUS.get(e.code, 400),
                        content={"error": {"code": e.code, "message": e.message}})


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


class PairBody(BaseModel):
    pair_code: str = Field(pattern=r"^\d{6}$")
    device: Literal["wearos"] = "wearos"


class HeartbeatBody(BaseModel):
    bpm: int
    ts: str
    source: Literal["wearos", "band", "simulated"]


class LatLng(BaseModel):
    lat: float
    lng: float


class AlertBody(BaseModel):
    trip_id: str
    location: LatLng | None = None  # accepted but never stored or logged
    route_id: str | None = None


class AckBody(BaseModel):
    trip_id: str
    ok: bool


@router.post("/v1/trips/pair")
def trips_pair(request: Request):
    return relay_of(request).create_trip()


@router.get("/v1/trips/{trip_id}/events")
def trip_events(trip_id: str, request: Request, after: int = 0):
    try:
        return relay_of(request).events(trip_id, after)
    except RelayError as e:
        return _error(e)


@router.post("/v1/trips/{trip_id}/end", status_code=204)
def trip_end(trip_id: str, request: Request):
    try:
        relay_of(request).end(trip_id)
    except RelayError as e:
        return _error(e)
    return Response(status_code=204)


@router.post("/v1/watch/pair")
def watch_pair(body: PairBody, request: Request):
    try:
        return relay_of(request).pair(body.pair_code)
    except RelayError as e:
        return _error(e)


@router.post("/v1/watch/heartbeat", status_code=204)
def watch_heartbeat(body: HeartbeatBody, request: Request,
                    authorization: Annotated[str | None, Header()] = None):
    try:
        relay_of(request).heartbeat(_bearer(authorization), body.bpm, body.ts, body.source)
    except RelayError as e:
        return _error(e)
    return Response(status_code=204)


@router.post("/v1/watch/prompt", status_code=204)
def watch_prompt(request: Request, authorization: Annotated[str | None, Header()] = None):
    try:
        relay_of(request).prompt(_bearer(authorization))
    except RelayError as e:
        return _error(e)
    return Response(status_code=204)


@router.post("/v1/alerts")
def alerts(body: AlertBody, request: Request, authorization: Annotated[str | None, Header()] = None):
    try:
        return {"status": relay_of(request).alert(_bearer(authorization), body.trip_id)}
    except RelayError as e:
        return _error(e)


@router.post("/v1/alerts/ack", status_code=204)
def alerts_ack(body: AckBody, request: Request):
    try:
        relay_of(request).ack(body.trip_id, body.ok)
    except RelayError as e:
        return _error(e)
    return Response(status_code=204)
