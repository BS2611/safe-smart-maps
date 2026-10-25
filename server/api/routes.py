"""POST /v1/routes. HTTP only: validation, error mapping. All logic is in services/planner.py."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from server.services.planner import PlannerError, RoutePlanner
from server.services.schemas import ErrorResponse, RoutesRequest, RoutesResponse

router = APIRouter()

STATUS = {
    "BAD_REQUEST": 400, "NO_ROUTE": 404, "UPSTREAM_ERROR": 502,
    "NOT_CONFIGURED": 503, "UPSTREAM_TIMEOUT": 504,
}


def get_planner(request: Request) -> RoutePlanner:
    return request.app.state.planner


def error_response(code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=STATUS[code], content={"error": {"code": code, "message": message}})


@router.post(
    "/v1/routes",
    response_model=RoutesResponse,
    responses={code: {"model": ErrorResponse} for code in (400, 404, 502, 503, 504)},
)
def plan_routes(body: RoutesRequest, planner: Annotated[RoutePlanner, Depends(get_planner)]):
    try:
        return planner.plan(body)
    except PlannerError as e:
        return error_response(e.code, e.message)
