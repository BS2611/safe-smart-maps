"""Road and help-point context interface (TECHNICAL_SPEC 2.3 RoadProvider). Implementations
live in their own modules."""
from abc import ABC, abstractmethod

from server.data.models import AreaContext, BoundingBox


class ContextProvider(ABC):
    @abstractmethod
    def get_area_context(self, area: BoundingBox) -> AreaContext:
        """Road segments (class, lit) and help points inside `area`, already normalized."""
