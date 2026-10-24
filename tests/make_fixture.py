"""Builds tests/fixtures/routes_response.json from the labeled fake scenario in tests/fakes.py.

LABELED TEST FIXTURE, not real data. The web app (Vitest, Playwright) loads this file so its
tests follow the real response shape. Regenerate after any intended API change:

    python -m tests.make_fixture
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from server.services.schemas import RoutesRequest
from tests import fakes

FIXTURES = Path(__file__).parent / "fixtures"
WHEN = {
    "routes_response.json": datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc),       # 8 PM Pacific
    "routes_response_1am.json": datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc),   # 1 AM Pacific
}


def build_fixture(name: str = "routes_response.json") -> dict:
    req = RoutesRequest.model_validate({
        "from": {"lat": fakes.ORIGIN[1], "lng": fakes.ORIGIN[0]},
        "to": {"lat": fakes.DEST[1], "lng": fakes.DEST[0]},
        "depart_time": WHEN[name].isoformat(),
        "settings": {"max_extra_minutes": 10},
    })
    resp = fakes.make_planner().plan(req)
    return json.loads(resp.model_dump_json())


if __name__ == "__main__":
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name in WHEN:
        (FIXTURES / name).write_text(json.dumps(build_fixture(name), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {FIXTURES / name}")
