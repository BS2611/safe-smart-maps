from fastapi import APIRouter

from server.services.health import health_status

router = APIRouter()


@router.get("/v1/health")
def health() -> dict:
    return health_status()
