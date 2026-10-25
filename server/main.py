import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from server.api import cache, health, routes, watch
from server.services.prefetch import build_places_provider, prefetch_enabled, start_prefetch
from server.services.prewarm import start_prewarm_thread
from server.services.scoring_config import load_scoring_config
from server.wiring import build_planner

load_dotenv()  # reads .env (git-ignored) if present; never committed; needed before WEB_ORIGINS below


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup check: refuses to start if the weights do not sum to 1.0.
    app.state.scoring_config = load_scoring_config()
    load_dotenv()
    app.state.places_provider = build_places_provider()
    if not hasattr(app.state, "planner"):  # tests set their own planner first
        app.state.planner = build_planner(app.state.scoring_config, app.state.places_provider)
        if os.environ.get("PREWARM_DEMO") == "1":
            start_prewarm_thread(app.state.planner)  # map data only; background
    if prefetch_enabled():
        start_prefetch(app.state.places_provider)  # background; never blocks startup
    yield


app = FastAPI(title="Safe Smart Maps API", lifespan=lifespan)

# The web app runs on another port in development. Origins come from env, never "*".
DEFAULT_ORIGIN = "http://localhost:3000"


def allowed_origins(raw: str | None) -> list[str]:
    """Comma-separated WEB_ORIGINS; an empty or missing value means the local web app only."""
    origins = [o.strip() for o in (raw or "").split(",") if o.strip()]
    return origins or [DEFAULT_ORIGIN]


_origins = allowed_origins(os.environ.get("WEB_ORIGINS"))
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"],
                   allow_headers=["content-type", "authorization"])


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # CONTRACTS.md error shape. Field names only: never echo the submitted values (locations).
    fields = sorted({".".join(str(p) for p in e["loc"][1:]) or "body" for e in exc.errors()})
    return routes.error_response("BAD_REQUEST", f"Check these fields: {', '.join(fields)}")


app.include_router(health.router)
app.include_router(cache.router)
app.include_router(routes.router)
app.include_router(watch.router)
