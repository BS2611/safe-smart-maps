# DECISIONS - append one line per decision. Do not rewrite old ones.

Format: `YYYY-MM-DD HH:MM | who | decision | reason`

2026-10-24 | team | Bright Data is the core live feed; Apify only for supporting data | Bright Data prize needs it essential
2026-10-24 | team | Mapbox for map and routing; we generate candidates and re-rank ourselves | Directions API takes no custom segment costs
2026-10-24 | team | Never label a route "safe" | We describe conditions, we cannot guarantee safety
2026-10-24 10:56 | bhavpreet | Next.js frontend, Python backend (Django or FastAPI, FastAPI proposed), 3-layer architecture (presentation / service / data-access) | Swappable data sources; pending Amey's confirmation of framework
2026-10-24 11:05 | bhavpreet | Repo root = CalHack_13; layout web/ server/ scoring/ docs/specs/ docs/agent-context/; CONTRACTS.md overrides the tech spec; API is /v1/routes | One layout for kit and specs; Bhavpreet gave full authority to reconcile; Amey to confirm contract
2026-10-24 11:05 | bhavpreet | Agents must checkpoint logs every 30-45 min, record chat decisions in files immediately, and follow the handoff protocol (AGENTS.md sec 4) | Prevent context loss between agents/people
2026-10-24 10:56 | bhavpreet | Target community = students leaving a campus late | Fits Anthropic/People-First tracks; campus still to be named
2026-10-24 18:00 | bhavpreet | Bright Data setup and API facts live in docs/agent-context/BRIGHTDATA.md (from the Cal Hacks public-data-hackpack); we use env BRIGHTDATA_API_KEY, optional BRIGHTDATA_ZONE for Web Unlocker | Single place for key setup, 202 polling and error rules
2026-10-24 19:00 | amey | Places cache key is (provider, area) with no hour_bucket; file cache in .cache/; stale served while a background refresh runs; routes never fetch; startup prefetch of the Palace of Fine Arts area; TTL default 24h | A Bright Data fetch takes ~3 min and costs credit; weekly hours are the same every hour
2026-10-24 20:40 | amey | OSM via public Overpass API (no key, no new paid service). Only explicit lit values count: yes/24/7/sunset-sunrise = yes, no = no, missing or anything else (automatic, limited, ...) = unknown. Help points = police, hospital, fire_station only (24-hour stores come from the places feed). One Overpass request returns roads + help points as an AreaContext | Missing lit must never read as unlit; keep raw OSM tags inside server/data/osm.py
