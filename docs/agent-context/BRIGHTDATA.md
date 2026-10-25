# Bright Data setup (team reference)

Source: https://github.com/ScrapeAlchemist/public-data-hackpack (SETUP.md, AGENTS.md), read 2026-10-24.
Track: "Best Agent/App Using Public Web Data". Public, logged-out data only.

## One-time setup (each person who runs live calls)
1. Sign up with the Cal Hacks link: https://brightdata.com/?promo=calhack2026&hs_signup=1
   (at the venue, use phone mobile data for signup).
2. Account settings > API keys (https://brightdata.com/cp/setting/users) > Add API key.
   Only an account admin can create keys. Copy it once; pick an expiry past Sunday 9 AM PT.
3. Put it in `.env` (git-ignored) on the line `BRIGHTDATA_API_KEY=`. Edit the existing line, no duplicates.
   Windows: create `.env` with an editor or `copy .env.example .env`; do NOT use PowerShell `echo >` (wrong encoding).
4. Never paste the key into a chat, a log, front-end code or a URL. All calls run server-side.
5. Check: `.venv/bin/python -m scripts.brightdata_smoke` (Windows: `.venv\Scripts\python -m scripts.brightdata_smoke`).
   Expect a list of places near the Palace of Fine Arts with open/closed/unknown. Record the real
   `open_hours` shape in a log entry (still unverified, see Amey's log).

## What our code uses
- Web Scraper API, Google Maps places, `POST https://api.brightdata.com/datasets/v3/scrape`
  with `type=discover_new&discover_by=location` (server/data/brightdata.py).
- Dataset id default `gd_m8ebnr0q2qlklc02fz`, overridable by `BRIGHTDATA_PLACES_DATASET_ID`.
- Header `Authorization: Bearer <key>`. No zone needed for the Web Scraper API.

## Hackpack facts that matter to us
- Sync scrape returns 202 + `snapshot_id` if it runs over ~1 min. Then poll
  `GET /datasets/v3/progress/<id>` until `ready`, download `GET /datasets/v3/snapshot/<id>?format=json`.
  Our provider currently raises on 202: add the polling path if the smoke test hits it.
- A 200 can still contain records with `error` / `error_code`; skip those (provider already does).
- Latency 4 s to several minutes. Never fetch on a user click: cache (CACHE_TTL_SECONDS) and
  prefetch; show the data time ("not sure" if old).
- Web Unlocker (`POST /request`, zone type `unblocker`) is optional, for any public page.
  Zone name goes in `BRIGHTDATA_ZONE` (empty = auto-pick via `GET /zone/get_active_zones`).
  Do not create zones from code. 200 with empty body = failure; check `x-brd-error-code`; retry up to 3.
- Skip anything using Bright Data's Discover API (`/discover`): it returns 404.
- Optional agent tools (not needed by the app): MCP `https://mcp.brightdata.com/mcp` and
  `npx skills add brightdata/skills` (Windows PowerShell: `npx.cmd`). Key goes in the header, keep it private.
- Troubleshooting: 401 = missing/expired key; shell env var beats `.env`; restart server after editing `.env`.
- The hackpack names the variable `BRIGHTDATA_API_TOKEN`; it also accepts `BRIGHTDATA_API_KEY`. We use `BRIGHTDATA_API_KEY`.
