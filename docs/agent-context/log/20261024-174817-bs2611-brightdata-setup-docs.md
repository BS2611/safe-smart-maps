# brightdata-setup-docs

- When: 2026-10-24 17:48
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: bhav/brightdata-setup (based on amey/brightdata-places 4c2dcc0), pushed to amey/brightdata-places
- Files touched: docs/agent-context/BRIGHTDATA.md (new), DECISIONS.md (1 line), .env.example (added BRIGHTDATA_ZONE name), this log
- What changed: Added a Bright Data setup guide from the Cal Hacks public-data-hackpack (signup, key, .env, smoke test, 202 polling, error rules, Web Unlocker zone).
- Why: Team needs one place for key setup; Amey's live smoke test is waiting on a key.
- Decisions made in chat (also added to DECISIONS.md? yes/no): doc location + env names, yes
- Contracts affected: none (new optional env name BRIGHTDATA_ZONE only in .env.example)
- How it was tested: docs only. Read hackpack SETUP.md and AGENTS.md from a clone. No key exists yet; no live call run.
- Unfinished / uncommitted: key not created (needs a human with the Bright Data account). No code changed in server/.
- Open issues / risks: brightdata.py raises on HTTP 202 (long jobs); hackpack says to poll progress/snapshot. Dataset id gd_m8ebnr0q2qlklc02fz not yet verified against a live account.
- Next step for whoever continues: create key, put in .env as BRIGHTDATA_API_KEY, run `.venv/bin/python -m scripts.brightdata_smoke`; if 202, add polling in server/data/brightdata.py (Amey owns it).
- Needs from teammate: Amey: run the smoke test once a key exists and add 202 polling if needed.
