"""Warms the caches for the demo trip so the first real request is fast.

Overpass (OpenStreetMap) takes 20-40 s on a cold start. Running the demo trip once fills the map
data cache for exactly the area a real request will use. Business listings are NOT fetched here:
they come from the places cache (server/data/cache.py, filled by the startup prefetch).
Enabled with PREWARM_DEMO=1. Costs a few Mapbox routing calls at startup, nothing else.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

from server.services.planner import PlannerError, RoutePlanner
from server.services.schemas import RoutesRequest

log = logging.getLogger("prewarm")

# Palace of Fine Arts -> Montgomery BART (configuration, not business data).
PALACE = {"lat": 37.8029, "lng": -122.4484}
MONTGOMERY = {"lat": 37.7894, "lng": -122.4013}
PACIFIC_OFFSET = timedelta(hours=-7)  # only used to pick a sensible evening time


def demo_request(now: datetime) -> RoutesRequest:
    """The demo trip at 8 PM Pacific tonight (yesterday's 8 PM if it is before 5 AM)."""
    local = now.astimezone(timezone(PACIFIC_OFFSET))
    base = local.replace(hour=20, minute=0, second=0, microsecond=0)
    if local.hour < 5:
        base -= timedelta(days=1)
    return RoutesRequest.model_validate({
        "from": PALACE, "to": MONTGOMERY, "depart_time": base.isoformat(),
        "settings": {"max_extra_minutes": 10},
    })


def prewarm(planner: RoutePlanner, now: datetime | None = None) -> dict:
    """Runs the demo trip. Never raises: returns what happened (also logged, without coordinates)."""
    try:
        planner.plan(demo_request(now or datetime.now(timezone.utc)))
        result = {"ok": 1, "failed": 0, "errors": []}
    except PlannerError as e:
        result = {"ok": 0, "failed": 1, "errors": [e.code]}
    except Exception as e:  # keep the server starting no matter what
        result = {"ok": 0, "failed": 1, "errors": [type(e).__name__]}
    log.info("prewarm finished: %s", result)
    return result


def start_prewarm_thread(planner: RoutePlanner) -> threading.Thread:
    thread = threading.Thread(target=prewarm, args=(planner,), name="prewarm", daemon=True)
    thread.start()
    return thread
