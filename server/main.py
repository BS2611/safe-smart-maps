from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.api import health
from server.services.scoring_config import load_scoring_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup check: refuses to start if the weights do not sum to 1.0.
    app.state.scoring_config = load_scoring_config()
    yield


app = FastAPI(title="Safe Smart Maps API", lifespan=lifespan)
app.include_router(health.router)
