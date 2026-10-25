from fastapi import APIRouter, Request

from server.services.prefetch import cache_status

router = APIRouter()


@router.get("/v1/cache/status")
def status(request: Request) -> dict:
    return cache_status(request.app.state.places_provider)
