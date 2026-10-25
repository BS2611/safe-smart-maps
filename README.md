# Safe Smart Maps

Walking routes for the time you will actually be on the street. For one trip it shows three routes,
**Most lit & active**, **Balanced** and **Fastest**, each scored on open places, lighting, main roads,
help points, transit and a low-weight incident check, **at the time you reach each part of the route**,
and on whether those things are spread along the **whole** walk (the continuity rule). Built for Cal Hacks 13.0.

> We describe conditions. We do not guarantee safety. Missing data shows as "not sure", never a guess.
> In an emergency, call 911.

## How it works
1. **Mapbox Directions** gives several walking routes (alternatives plus detours through side points).
2. Each route is cut into ~50 m segments, with an arrival time for each segment.
3. For every segment we check, at its arrival time: live **business listings and opening hours** (Bright Data),
   street class, lit tag and underpasses (OpenStreetMap), open streetlight reports (SF 311), past incidents
   (SF open data, low weight), and the shape of the route.
4. Segment scores (0-100) become a route score: 50% average + 50% weakest 200 m, minus a penalty for any
   empty stretch over 150 m. Coverage must reach 80% to hit the target.
5. A Claude explanation puts it in plain words (a fixed template is used if Claude is unavailable).

Specs: [functional](docs/specs/FUNCTIONAL_SPEC.md), [technical](docs/specs/TECHNICAL_SPEC.md),
[agile plan](docs/specs/AGILE_PLAN.md). Data contract: [CONTRACTS.md](docs/agent-context/CONTRACTS.md).

## Where each sponsor tool is used
| Tool | Used for | Where |
|---|---|---|
| Bright Data | Live public business listings and opening hours: the core data feed | `server/data/brightdata.py`, `server/data/opening_hours.py` |
| Mapbox | Walking routes, address search, the map | `server/data/mapbox.py`, `web/lib/geocode.ts`, `web/components/RouteMap.tsx` |
| Claude API | Plain-language route explanations (checked against our wording rules) | `server/services/explain.py` |
| Apify | Not used. Bright Data covers the live feed (see DECISIONS) | n/a |

## Run it
Needs Python 3.12 and Node 24.

```bash
cp .env.example .env            # then fill in the keys you have (never commit .env)
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # Windows; use .venv/bin/pip on Mac/Linux
.venv/Scripts/python -m uvicorn server.main:app --port 8000
```
```bash
cd web && npm install && npm run dev        # http://localhost:3100
```
Set `NEXT_PUBLIC_MAPBOX_TOKEN` (a URL-restricted public token) in `web/.env.local` for the map and address search.
Set `PREWARM_DEMO=1` on the server to warm the caches for the demo corridor at startup.

No keys yet? Put `NEXT_PUBLIC_DEV_FIXTURES=1` in `web/.env.local` to review the screens with saved sample data.
It shows a visible "Sample data" banner and is off by default.

### Keys
| Variable | What it enables | Without it |
|---|---|---|
| `MAPBOX_TOKEN` (server) | Walking routes | `/v1/routes` answers `NOT_CONFIGURED` |
| `BRIGHTDATA_API_KEY` | Live open places and hours | Place factors show "not sure" |
| `ANTHROPIC_API_KEY` | AI explanations | Template explanations |
| `NEXT_PUBLIC_MAPBOX_TOKEN` (browser) | Map tiles, address search | A simple route drawing, demo places only |

## Test it (the Definition of Done)
```bash
bash scripts/verify.sh            # secrets scan, lint, backend tests, web types/lint/unit tests, browser tests
bash scripts/verify.sh --quick    # same without the browser tests
.venv/Scripts/python -m pytest -m live    # real services, by hand: OpenStreetMap, SF data, Mapbox, Bright Data, Claude
```
Browser tests run on an iPhone-class WebKit browser, an Android-class Chromium browser and a 360 px phone, and
include an automated accessibility check (WCAG A/AA). CI (`.github/workflows/ci.yml`) runs the same on every pull request.

## Known limits
- **Live path not verified end to end in the repo's test setup.** Mapbox, Bright Data and Claude need keys; they are
  covered by unit tests with labeled fixtures, and by `pytest -m live` once keys are set. Run it before any demo.
- The shape of Bright Data's `open_hours` field is an assumption (see the Bright Data log in `docs/agent-context/log/`).
  If every place comes back "unknown", the parser needs adjusting.
- Transit schedules are not connected, so the transit factor always says "not sure".
- Lighting depends on OpenStreetMap `lit` tags, which many streets lack: those segments say "not sure".
- OpenStreetMap's public Overpass servers are slow (20-30 s) and sometimes busy. Results are cached for 24 h and three
  servers are tried; pre-warm before a demo.
- Demo area only: trips up to about 5 km, San Francisco time zone for opening hours.
- Past-incident data has a 5% weight because it can reflect policing as much as danger.
- Activity is an estimate from open places and time of day. It is not a count of people.
- Not built (stretch): walk mode, heartbeat check, Samsung Wear OS app, voice. Designed in the docs only.
- Real-device checks on an iPhone and an Android phone are still to do; browser tests use emulation.

## Privacy and responsible design
Trip locations stay in the browser tab (session storage) and are sent only to our API to compute routes; the server logs
no coordinates. Nothing is stored after the request except short-lived map-data caches keyed by area, not by person.
Wording never says a route is "safe"; this is enforced by automated tests on both the web and server code.

## Working with AI agents and teammates
Read [AGENTS.md](AGENTS.md) and [README_FIRST.md](README_FIRST.md). Shared memory is in `docs/agent-context/`
(state, contracts, decisions, a log entry per change).
