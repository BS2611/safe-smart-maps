# mapbox-token-created

- When: 2026-10-24 18:13
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui / uncommitted
- Files touched: docs/agent-context/DECISIONS.md, docs/agent-context/STATE.md, this log
- What changed: Recorded that Bhavpreet created a free-tier Mapbox browser token (default public scopes, URL-restricted to localhost). No code changed.
- Why: Next agent must know the browser key exists and where it lives.
- Decisions made in chat (also added to DECISIONS.md? yes/no): browser token restricted to localhost, add deployed domain later (yes)
- Contracts affected: none (env names NEXT_PUBLIC_MAPBOX_TOKEN and MAPBOX_TOKEN already in CONTRACTS.md)
- How it was tested: not tested. The key was not seen by the agent and no live call was made.
- Unfinished / uncommitted: all of this is uncommitted. Server token MAPBOX_TOKEN not created yet.
- Open issues / risks: A URL-restricted token fails for server-side calls and curl, so the server needs a second unrestricted pk. token. Deployed domain must be added to the browser token before the demo.
- Next step for whoever continues: create a second public token for MAPBOX_TOKEN with no URL restriction, put both in git-ignored .env, run `pytest -m live`, then test the map in the browser at localhost.
- Needs from teammate: none (Amey may reuse the server token for routing)
