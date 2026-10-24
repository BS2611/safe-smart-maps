API_VERSION = "1"


def health_status() -> dict:
    return {"status": "ok", "api_version": API_VERSION}
