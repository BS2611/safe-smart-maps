# osm-context-provider

- When: 2026-10-24 20:40 PT
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend / see git log (one commit with this log)
- Files touched: server/data/osm.py (new), server/data/context.py (new), server/data/models.py (RoadContext, HelpPoint, AreaContext), tests/test_osm.py (new), .env.example (OVERPASS_URL), CONTRACTS.md, DECISIONS.md, STATE.md (Amey section), this log
- What changed: (1) Verified the real cache: ran `scripts.prefetch_places` once (one paid job) -> 18 places stored in .cache/places/ (ignored). Server with one worker: GET /v1/cache/status -> palace_of_fine_arts fresh, places 18, data_fetched_at set, last_error null; two status reads left data_fetched_at unchanged and the uvicorn log showed no new job (reads never fetch). (2) M2.4: OverpassContextProvider (public OSM Overpass, no key) makes one request for roads (way[highway]) and help points (amenity police|hospital|fire_station) and returns AreaContext(roads, help_points, fetched_at). Raw OSM tags are read only in osm.py. Road class: motorway, trunk, primary, secondary, tertiary, residential (also living_street, unclassified), service, pedestrian (footway, pedestrian, path, steps, cycleway), "_link" maps to parent, other tags -> "other", missing -> "unknown". Lighting: lit yes/24/7/sunset-sunrise -> yes, no -> no, missing or anything else -> unknown (never "no"). Help points: police, hospital, fire_station; ways use their center point; no coordinates -> dropped; node+building duplicates of the same type and name within 100 m merged. Ways with no highway tag or fewer than 2 valid points are dropped. Failures raise OsmError (HTTP error, timeout, bad JSON, no elements list, Overpass "runtime error" remark).
- Why: segment scoring needs road class, lighting and help points without knowing OSM tags.
- Decisions made in chat (also added to DECISIONS.md? yes): lit semantics, help-point categories, Overpass as source. Interface is ContextProvider.get_area_context (one call returns roads + help points) instead of the spec's RoadProvider.get_road_attributes, to avoid two Overpass requests; CONTRACTS.md updated.
- Contracts affected: CONTRACTS.md "Data source interface" (AreaContext, RoadContext, HelpPoint), env OVERPASS_URL.
- How it was tested: `.venv/bin/python -m unittest discover -s tests -t .` -> Ran 181 tests, OK (162 old + 19 new in tests/test_osm.py, all with labeled hand-written fixtures and a mocked httpx.post). REAL OSM REQUEST NOT VERIFIED: both overpass-api.de and overpass.kumi.systems refused connections from this machine (curl exit 7; provider raised OsmError ConnectError), while api.brightdata.com was reachable. So the real Overpass response shape (out tags geom center) is untested live.
- Unfinished / uncommitted: nothing after commit. Not pushed.
- Open issues / risks:
  - Live Overpass unverified (network). Retry from another network: run the OverpassContextProvider on DEMO_AREAS["palace_of_fine_arts"] and check counts of roads, lit values and help points.
  - Help points use the same box as roads, so one just outside the box is missed; a wider box for help points may be needed for "nearest help point".
  - No cache for OSM data yet; each call hits Overpass.
  - .env has CACHE_TTL_SECONDS=900, so the cache goes stale after 15 min (still served, refresh in background on read of a stale entry). Set 86400 or remove the line.
  - The prefetch returned 18 places; the earlier smoke test returned 19 (listings vary run to run).
- Next step for whoever continues: retry the live Overpass check from a working network; then M3 segment scoring (match RoadContext/HelpPoint/Place to route segments using scoring/scoring_v1.json), then continuity.
- Needs from teammate: none (the Mapbox provider belongs to the other developer).
