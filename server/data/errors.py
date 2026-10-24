"""Shared errors for the data layer. Messages never contain credentials or coordinates of users."""


class DataSourceError(RuntimeError):
    """A provider could not deliver data (blocked, slow, bad response, not configured)."""

    def __init__(self, source: str, message: str, kind: str = "failed"):
        super().__init__(f"{source}: {message}")
        self.source = source
        self.kind = kind  # failed | timeout | not_configured | empty


class NotConfiguredError(DataSourceError):
    def __init__(self, source: str, what: str):
        super().__init__(source, f"{what} is not set", kind="not_configured")
