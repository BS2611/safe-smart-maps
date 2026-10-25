"""Measure how much of a walking line has a recent Mapillary photo nearby. Run: python scripts/mapillary_coverage.py
Usage: python scripts/mapillary_coverage.py LAT1 LNG1 LAT2 LNG2 [samples]   (needs MAPILLARY_TOKEN in .env)"""
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from server.data.mapillary import MapillaryPhotoSource

load_dotenv(".env")
a = [float(x) for x in sys.argv[1:5]] if len(sys.argv) >= 5 else [37.8029, -122.4484, 37.8080, -122.4177]
n = int(sys.argv[5]) if len(sys.argv) > 5 else 25
src = MapillaryPhotoSource()
now = datetime.now(timezone.utc)
ages, hits = [], 0
for i in range(n):
    t = i / (n - 1)
    img = src.find(a[0] + (a[2] - a[0]) * t, a[1] + (a[3] - a[1]) * t, now)
    if img:
        hits += 1
        ages.append((now - datetime.fromtimestamp(img["captured_at"] / 1000, tz=timezone.utc)).days / 365)
print(f"{hits}/{n} sample points have a flat photo within {src.radius_m:g} m and {src.max_age_years:g} years")
if ages:
    print(f"photo age years: min {min(ages):.1f}, median {sorted(ages)[len(ages)//2]:.1f}, max {max(ages):.1f}")
