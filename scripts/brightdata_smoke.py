"""One live Bright Data call around the Palace of Fine Arts. Prints safe output only.
Run: .venv/bin/python -m scripts.brightdata_smoke   (needs BRIGHTDATA_API_KEY in .env)
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from server.data.brightdata import BrightDataError, BrightDataPlacesProvider
from server.data.models import BoundingBox
from server.data.opening_hours import evaluate_open_status

load_dotenv()
AREA = BoundingBox(south=37.797, west=-122.455, north=37.809, east=-122.440)
when = datetime.now(ZoneInfo("America/Los_Angeles")).replace(hour=20, minute=0, second=0, microsecond=0)
try:
    places = BrightDataPlacesProvider().get_places(AREA, when)
except BrightDataError as e:
    raise SystemExit(f"FAILED: {e}")
print(f"places returned: {len(places)}  (status evaluated for {when.isoformat()})")
for p in places[:8]:
    print(f"- {p.name} | {p.category} (raw: {p.raw_category}) | {evaluate_open_status(p, when).value} | fetched_at {p.fetched_at.isoformat()}")
