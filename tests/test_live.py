"""LIVE checks: real network, real services. Not run by default or in CI.

    pytest -m live            (run by hand before a demo and at the end of every sprint)

Keys come from .env (git-ignored). A check is skipped, with the reason shown, if its key is missing.
These prove the live path works; unit tests prove the logic. Nothing here uses fixtures.
"""
import os
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv

from server.data.brightdata import BrightDataPlacesProvider
from server.data.mapbox import MapboxRoutingProvider
from server.data.models import BoundingBox
from server.data.opening_hours import OpenStatus, evaluate_open_status
from server.data.osm import OverpassProvider
from server.data.sf_open_data import SocrataClient
from server.services.explain import ClaudeExplainer
from server.services.wording import find_banned_wording

load_dotenv()
pytestmark = pytest.mark.live

# Palace of Fine Arts to Montgomery BART (the demo corridor), padded.
CORRIDOR = BoundingBox(37.789, -122.452, 37.806, -122.400)
PALACE = (-122.4484, 37.8029)
MONTGOMERY = (-122.4013, 37.7894)


def need(var: str):
    if not os.environ.get(var):
        pytest.skip(f"{var} is not set")


def test_live_openstreetmap_has_streets_and_help_points():
    small = BoundingBox(37.796, -122.452, 37.806, -122.438)
    features = OverpassProvider().get_map_features(small)
    assert len(features.ways) > 20
    assert any(w.highway for w in features.ways)


def test_live_sf_311_streetlight_reports_respond():
    outages = SocrataClient().get_open_outages(CORRIDOR)
    assert isinstance(outages, list)  # may be empty on a good night; the call must succeed


def test_live_sf_incidents_respond():
    incidents = SocrataClient().get_recent_incidents(CORRIDOR)
    assert isinstance(incidents, list)


def test_live_mapbox_walking_routes():
    need("MAPBOX_TOKEN")
    routes = MapboxRoutingProvider().get_walking_routes(PALACE, MONTGOMERY)
    assert routes and all(r.distance_m > 1000 for r in routes)


def test_live_brightdata_places_and_open_status():
    need("BRIGHTDATA_API_KEY")
    area = BoundingBox(37.7985, -122.4545, 37.8085, -122.4425)
    places = BrightDataPlacesProvider().get_places(area, datetime.now(timezone.utc))
    assert places, "expected some places near the Palace of Fine Arts"
    statuses = {evaluate_open_status(p, datetime.now(timezone.utc)) for p in places}
    assert statuses - {OpenStatus.UNKNOWN}, "every place came back with unreadable hours"


def test_live_claude_explanation_is_clean():
    need("ANTHROPIC_API_KEY")
    text, source = ClaudeExplainer().explain({
        "label": "safest", "duration_min": 46, "extra_min": 5, "coverage_pct": 88.0,
        "longest_gap_m": 110, "open_places_count": 14})
    assert find_banned_wording(text) == []
    print("explanation source:", source)
