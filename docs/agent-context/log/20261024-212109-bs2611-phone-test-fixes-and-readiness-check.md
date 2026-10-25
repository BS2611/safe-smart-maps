# Phone test fixes and readiness check of the ui branch

- When: 2026-10-24 21:40 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui / see git log
- Files touched: web/components/InstallTip.tsx(+test), web/app/globals.css
- What changed: Installed the APK on a Galaxy S22 Ultra with adb and ran it. Found and fixed two real device problems: (1) the "Install for best results" tip showed inside the Android app, now hidden there; (2) the bottom button (Show routes) sat under the Android navigation bar, so spacing now uses the injected --safe-area-inset-* values as well as env().
- Decisions made in chat: none. Bhavpreet asked only to check whether ui is ready, not to integrate.
- Contracts affected: none.
- How it was tested: verify --quick green (289 backend, 203 web unit); Playwright 54 passed; APK rebuilt and reinstalled. The nav-bar fix was built into the APK but not re-checked on the phone screen after the build. A phone screenshot accidentally captured a private chat (the phone switched to WhatsApp during testing); it was deleted and nothing was typed or sent in that app.
- Unfinished / uncommitted: none after commit.
- Open issues / risks: merging ui into main conflicts in server/ and tests/ (20 files, add/add) because main has its own backend built from the same contract; web/ and docs merge cleanly. The web app expects the CONTRACTS shape, and main's response models are a superset of it, so the web app should work against main's backend. Live trip never run end to end.
- Next step for whoever continues: decide the backend (keep main's, drop ui's server/ and tests/ except the tests/fixtures + make_fixture contract guard), then merge only web/ and docs from ui.
- Needs from teammate: Amey/Bhavpreet: choose the backend.
