"""Places provider interface. Implementations live in their own modules."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class PlacesProvider(ABC):
    @abstractmethod
    def get_places(self, area: Any, time: datetime) -> list[dict]:
        """Places in `area` with opening hours checked at `time`.

        Each place: opening hours, is_24h, category, source, fetched_at
        (see docs/agent-context/CONTRACTS.md, "Data source interface").
        """
