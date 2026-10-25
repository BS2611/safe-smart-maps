"""Warms the caches for the demo corridor so the first real request is fast.

Overpass (map data) takes 20-30 s on a cold start. Running the demo trip once at 8 PM and once at
1 AM fills the map, listing, outage and incident caches. Enabled with PREWARM_DEMO=1 on startup.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

from server.services.planner import PlannerError, RoutePlanner
from server.services.schemas import RoutesRequest

log = logging.getLogger("prewarm")

PALACE = {"lat": 37.8029, "lng": -122.4484}
MONTGOMERY = {"lat": 37.7894, "lng": -122.4013}
PACIFIC_OFFSET = timedelta(hours=-7)  # only used to pick two sensible evening/night times


def demo_requests(now: datetime) -> list[RoutesRequest]:
    local = now.astimezone(timezone(PACIFIC_OFFSET))
    base = local.replace(hour=20, minute=0, second=0, microsecond=0)
    if local.hour < 5:
        base -= timedelta(days=1)
    times = [base, base + timedelta(hours=5)]  # 8 PM and 1 AM
    return [
        RoutesRequest.model_validate({
            "from": PALACE, "to": MONTGOMERY, "depart_time": t.isoformat(),
            "settings": {"max_extra_minutes": 10},
        })
        for t in times
    ]


def prewarm(planner: RoutePlanner, now: datetime | None = None) -> dict:
    """Runs the demo trips. Never raises: returns what happened (also logged, without coordinates)."""
    result = {"ok": 0, "failed": 0, "errors": []}
    for req in demo_requests(now or datetime.now(timezone.utc)):
        try:
            planner.plan(req)
            result["ok"] += 1
        except PlannerError as e:
            result["failed"] += 1
            result["errors"].append(e.code)
        except Exception as e:  # keep the server starting no matter what
            result["failed"] += 1
            result["errors"].append(type(e).__name__)
    log.info("prewarm finished: %s", result)
    return result


def start_prewarm_thread(planner: RoutePlanner) -> threading.Thread:
    thread = threading.Thread(target=prewarm, args=(planner,), name="prewarm", daemon=True)
    thread.start()
    return thread
