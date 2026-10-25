"""LIVE checks against real services. Skipped by default (pyproject: -m 'not live').
Run by hand: python -m pytest -m live -q    Needs MAPBOX_TOKEN / ANTHROPIC_API_KEY in .env.
Each test makes a small number of real requests; do not run in CI."""
import os

import pytest
from dotenv import load_dotenv

from server.data.mapbox import MapboxWalkingProvider
from server.services.candidates import generate_candidates
from server.services.explain import ClaudeExplainer
from server.services.scoring_config import load_scoring_config
from server.services.wording import find_banned_wording

load_dotenv()
pytestmark = pytest.mark.live

PALACE = (-122.4484, 37.8029)      # (lng, lat)
MONTGOMERY = (-122.4013, 37.7894)


def need(var: str):
    if not os.environ.get(var):
        pytest.skip(f"{var} is not set")


def test_live_mapbox_walking_route_normalizes():
    need("MAPBOX_TOKEN")
    routes = MapboxWalkingProvider().get_walking_routes(PALACE, MONTGOMERY)
    assert routes and all(r.distance_m > 1000 and len(r.coordinates) > 10 for r in routes)
    lng, lat = routes[0].coordinates[0]
    assert -123 < lng < -122 and 37 < lat < 38          # (lng, lat) order, San Francisco


def test_live_candidates_with_detours():
    need("MAPBOX_TOKEN")
    found = generate_candidates(MapboxWalkingProvider(), PALACE, MONTGOMERY, load_scoring_config())
    assert found and len({c.id for c in found}) == len(found)


def test_live_claude_explanation_is_clean():
    need("ANTHROPIC_API_KEY")
    text, source = ClaudeExplainer().explain({
        "label": "safest", "duration_min": 46, "extra_min": 5, "coverage_pct": 88.0,
        "longest_gap_m": 110, "open_places_count": 14})
    assert find_banned_wording(text) == [] and source in {"ai", "template"}
