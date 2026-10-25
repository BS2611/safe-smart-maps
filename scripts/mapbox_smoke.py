"""ONE live Mapbox walking-route call, Palace of Fine Arts -> Montgomery BART. Prints safe output only.
Run: .venv/bin/python -m scripts.mapbox_smoke   (needs MAPBOX_TOKEN in .env)
Prints route count, distance, duration and coordinate count. Never the token, URL or raw response.
"""
from dotenv import load_dotenv

from server.data.mapbox import MapboxError, MapboxWalkingProvider

load_dotenv()
ORIGIN = (-122.4484, 37.8029)  # (lng, lat)
DEST = (-122.4013, 37.7894)    # (lng, lat)
try:
    routes = MapboxWalkingProvider().get_walking_routes(ORIGIN, DEST)
except MapboxError as e:
    raise SystemExit(f"FAILED ({e.kind}): {e}") from None
print(f"routes returned: {len(routes)}")
for r in routes:
    first_lng, first_lat = r.coordinates[0]
    in_sf = 37.0 < first_lat < 38.5 and -123.0 < first_lng < -122.0
    print(f"- {r.id} | {r.provider} | {r.distance_m:.0f} m | {r.duration_s:.0f} s "
          f"| {len(r.coordinates)} coordinates | first point is (lng, lat) in San Francisco: {in_sf}")
