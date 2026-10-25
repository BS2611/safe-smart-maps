"""Fill the places cache for the demo areas (blocking; one paid fetch of ~3 min per area).
Run: .venv/bin/python -m scripts.prefetch_places [--force]   (needs BRIGHTDATA_API_KEY in .env)
Skips areas whose cache is still fresh unless --force.
"""
import sys

from dotenv import load_dotenv

from server.data.brightdata import BrightDataError
from server.services.prefetch import DEMO_AREAS, build_places_provider

load_dotenv()
force = "--force" in sys.argv
provider = build_places_provider()
for name, area in DEMO_AREAS.items():
    look = provider.lookup(area)
    if look.status == "fresh" and not force:
        print(f"{name}: cache fresh ({len(look.places)} places, fetched {look.fetched_at.isoformat()}), skipped")
        continue
    print(f"{name}: fetching live (takes about 3 minutes)...", flush=True)
    try:
        n = provider.refresh(area)
    except BrightDataError as e:
        print(f"{name}: FAILED: {e}")
        continue
    print(f"{name}: stored {n} places")
