"""Bright Data places provider. Stub only: real fetching is not written yet."""
from datetime import datetime
from typing import Any

from server.data.places import PlacesProvider


class BrightDataPlacesProvider(PlacesProvider):
    def get_places(self, area: Any, time: datetime) -> list[dict]:
        raise NotImplementedError("Bright Data fetching is not implemented yet")
