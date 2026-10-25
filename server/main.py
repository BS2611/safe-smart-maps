from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from server.api import cache, health
from server.services.prefetch import build_places_provider, prefetch_enabled, start_prefetch
from server.services.scoring_config import load_scoring_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup check: refuses to start if the weights do not sum to 1.0.
    app.state.scoring_config = load_scoring_config()
    load_dotenv()
    app.state.places_provider = build_places_provider()
    if prefetch_enabled():
        start_prefetch(app.state.places_provider)  # background; never blocks startup
    yield


app = FastAPI(title="Safe Smart Maps API", lifespan=lifespan)
app.include_router(health.router)
app.include_router(cache.router)
