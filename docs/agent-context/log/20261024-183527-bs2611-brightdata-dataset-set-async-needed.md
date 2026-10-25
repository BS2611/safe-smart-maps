# brightdata-dataset-set-async-needed

- When: 2026-10-24 18:35
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui / uncommitted
- Files touched: .env (git-ignored, local only), this log. No code changed.
- What changed: Set BRIGHTDATA_PLACES_DATASET_ID to the Google Maps "full information" dataset (the same id already used as the default in server/data/brightdata.py). Mapbox tokens verified (server unrestricted 200; browser token 200 only from localhost:3000). Anthropic key verified (claude-sonnet-5-5, 200). Web dev server restarted on port 3000.
- Why: Unblock the live Bright Data check.
- Decisions made in chat (also added to DECISIONS.md? yes/no): Ignore PREWARM_DEMO for now (no, temporary)
- Contracts affected: none
- How it was tested: ran scripts.brightdata_smoke and a 1-keyword probe: both fail with "202 (async job)". Raw API call returned a snapshot_id; polling /datasets/v3/progress/<id> showed "ready" after about 90 s, and /datasets/v3/snapshot/<id>?format=json returned 5 real places with open_hours.
- Unfinished / uncommitted: everything is uncommitted.
- Open issues / risks: The sync /scrape endpoint always returns 202 for this dataset (job takes about 60-100 s), so BrightDataPlacesProvider.get_places (server/data/brightdata.py, Amey's file) never succeeds live. It needs trigger + poll progress + download snapshot, with caching (and a longer-than-sync wait). A route request would otherwise wait 1-2 min.
- Next step for whoever continues: ask Amey (owner of server/) to add the async path (POST /datasets/v3/scrape returns snapshot_id on 202, poll /datasets/v3/progress/<id> until "ready", GET /datasets/v3/snapshot/<id>?format=json), then rerun `.venv/Scripts/python -m scripts.brightdata_smoke`.
- Needs from teammate: Amey: approve/implement the async polling in server/data/brightdata.py.
