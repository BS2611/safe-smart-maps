import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from server.api import health, routes
from server.services.scoring_config import load_scoring_config
from server.wiring import build_planner

load_dotenv()  # reads .env (git-ignored) if present; never committed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup check: refuses to start if the weights do not sum to 1.0.
    app.state.scoring_config = load_scoring_config()
    if not hasattr(app.state, "planner"):  # tests set their own planner first
        app.state.planner = build_planner(app.state.scoring_config)
    yield


app = FastAPI(title="Safe Smart Maps API", lifespan=lifespan)

# The web app runs on another port in development. Origins come from env, never "*".
_origins = [o.strip() for o in os.environ.get("WEB_ORIGINS", "http://localhost:3100").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"],
                   allow_headers=["content-type"])


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # CONTRACTS.md error shape. Field names only: never echo the submitted values (locations).
    fields = sorted({".".join(str(p) for p in e["loc"][1:]) or "body" for e in exc.errors()})
    return routes.error_response("BAD_REQUEST", f"Check these fields: {', '.join(fields)}")


app.include_router(health.router)
app.include_router(routes.router)
