# Platform independent: Android, iOS, Samsung Wear OS

- When: 2026-10-24 12:10 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: bhav/initial-kit-and-specs / see git log
- Files touched: docs/specs/FUNCTIONAL_SPEC.md (5.7, new 5.8, F11/F12, out of scope), docs/specs/TECHNICAL_SPEC.md (stack table, new section 8 platforms/watch, layout adds watch/), docs/specs/TASKS.md (platform + watch tasks), docs/agent-context/CONTRACTS.md (watch/ folder, watch relay endpoints, platform matrix), OPEN_QUESTIONS.md (10-14), DECISIONS.md, STATE.md, docs/design/STITCH_UI_BRIEF.pdf (v0.2, 8 pages: section 6b, screen 11 watch, iOS fallbacks)
- What changed: Product is now platform independent: one responsive PWA for Android Chrome + iOS Safari, plus optional Samsung Wear OS (Kotlin) companion. Watch reads heart rate, computes trigger locally, reports through a backend relay (memory only) paired by a 6-digit code. Fallbacks: BLE band (Android Chrome), labeled simulated. Apple Watch and native phone apps out of scope.
- Why: Bhavpreet wants it to work on Android, iOS and has a Samsung watch.
- Decisions made in chat (also added to DECISIONS.md? yes): PWA + Wear OS companion; watch-local trigger; relay in memory.
- Contracts affected: CONTRACTS.md: new "Watch relay endpoints" (/v1/trips/pair, /v1/watch/pair, /v1/watch/heartbeat, /v1/trips/{id}/stream, /v1/alerts, /v1/alerts/ack), watch/ folder, platform matrix.
- How it was tested: PDF regenerated, 8 pages, text check found Wear OS and iPhone sections. No code exists. Platform limits (iOS no Web Bluetooth/vibration, wake lock 16.4+, Wear OS Health Services) are from general knowledge and must be verified on real devices.
- Unfinished / uncommitted: watch model unknown; no iPhone identified for testing.
- Open issues / risks: Samsung "tested" model unknown (must be Wear OS i.e. Galaxy Watch 4+; older Tizen cannot run our app). Relay passes health data through our server (memory only) - Amey/both must accept. SMS provider for contact alert undecided. Wear OS app is substantial work for a hackathon: keep stretch.
- Next step for whoever continues: Bhavpreet answers OPEN_QUESTIONS 10-11; Amey reviews CONTRACTS watch endpoints; give STITCH_UI_BRIEF.pdf to Stitch; then start M1 in docs/specs/TASKS.md plus P.1.
- Needs from teammate: Amey: review watch relay endpoints and answer #13/#14.
