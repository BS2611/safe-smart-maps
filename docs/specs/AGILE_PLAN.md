# Agile plan - how we build, test and ship

Version 0.1 - 2026-10-24. Owner: Bhavpreet (product owner), Amey (backend lead), guide (reviewer/tester).

## 1. Method
Scrum-lite with short sprints.
- During Cal Hacks: 3-hour sprints (S0 to S5, see section 6) ending Sunday 9:00 AM PT.
- After the event: normal 1-week sprints from the same backlog.
- Each sprint: 10 min planning (pick stories from docs/specs/TASKS.md), build, 10 min review/demo of the working increment, 5 min retro. Write the result in a log entry and update STATE.md.
- Backlog = TASKS.md. A story is small (1-3 hours), has an owner, and names its tests.
- Work is done in vertical slices where possible (one screen plus its API plus tests), so every sprint ends with something that runs.

## 2. Definition of Done (every story, no exceptions)
1. Pull request from `<person>/<topic>` reviewed by the other person, merged to `main`.
2. **Unit tests written together with the code**, covering the happy path, edge cases and failures (blocked, slow, empty data).
3. **Full regression suite green** (every earlier test, not just the new ones), locally and in CI. Red means no merge.
4. Contract tests pass against docs/agent-context/CONTRACTS.md; lint and type-check pass; no secrets.
5. Wording check: never "safe"/"hazard"; "not sure" for missing data; "estimate" for activity.
6. Manual smoke on an Android viewport and an iPhone viewport for any UI story.
7. Log entry written; CONTRACTS, DECISIONS, STATE updated when affected.
A story that is not Done does not count toward the sprint goal.

## 3. Test strategy
| Layer | Tool | What it covers |
|---|---|---|
| Backend unit | pytest | Weights sum to 1.0; segment score; continuity (coverage, longest gap, worst 200 m window, gap penalty); route score formula; selector (Fastest/Safest within extra-minutes cap/Balanced, merged labels); open-at-arrival (past midnight, 24 h, timezone America/Los_Angeles); cache keys |
| Backend golden | pytest | Fixed segment fixture gives the exact expected route score (guards formula changes) |
| Backend provider | pytest + labeled fixtures in `tests/fixtures/` | Parsing, plus simulated blocked page, slow response (timeout), empty result |
| Backend API | FastAPI TestClient | `/v1/health`, `/v1/routes` request and response shape, errors and `warnings` |
| Contract | OpenAPI to generated TypeScript types; JSON-schema check | Fails when backend or frontend drift from CONTRACTS.md |
| Frontend unit | Vitest + React Testing Library | Each component: route card (3 variants + merged), segment legend, coverage bar, segment strip, settings, fetching checklist (each state), "not sure"/"estimate"/"simulated" tags, unsupported-browser notice |
| Frontend e2e / regression | Playwright (Chromium + WebKit) at 390 px and 360 px | Plan trip, results, detail, 8 PM vs 1 AM flow, location denied, error states |
| Visual regression | Playwright screenshots | Key screens at both widths |
| Live check | marked `@live`, run manually | One real Bright Data fetch for the demo corridor; run at the end of every sprint and before every demo. Not in CI (depends on network) |

Rules:
- **Every bug gets a failing test first, then the fix.** The test stays forever.
- Fixtures are labeled, live only in `tests/fixtures/`, and never feed the demo path.
- Coverage gates: scoring, continuity and selector modules 100% of lines; everything else at least 80%.
- Honest limit: tests prove what we test. The remaining risk is live web data (blocked pages, closed shops, odd hours). We cover it with the live check, cached fallback, "not sure" states, and a full 8 PM vs 1 AM rehearsal before the feature freeze.

## 4. CI and branch rules
- GitHub Actions on every PR: lint, type-check, backend pytest, frontend Vitest, Playwright. Branch protection on `main`: required green checks, one approving review, no force-push.
- Regression run (full suite) after each merged component, as well as on the PR.
- Feature freeze at the start of S4 (about 4 AM Sunday): after that only bug fixes with tests.

## 5. Roles
| Role | Who | Does |
|---|---|---|
| Product owner | Bhavpreet | Priorities, design (Figma), accepts stories, `web/` |
| Backend lead | Amey | `server/`, `scoring/`, data providers, contract confirmation |
| Guide | third person | Reviews, tests on real phones, Devpost, demo script, community quotes |
Agents follow AGENTS.md; they never merge their own PR without a human review.

## 6. Sprint map (Saturday 3:30 PM to Sunday 9:00 AM PT)
| Sprint | Ends | Goal (a demoable increment) | Main stories (each with tests) |
|---|---|---|---|
| S0 | ~5 PM | Foundations | Fix Figma ("must fix" list), export tokens; push repo, branch protection; CI skeleton plus pytest, Vitest, Playwright set up; Amey's scaffold PR; confirm CONTRACTS |
| S1 | ~7 PM | Data truth | scoring_v1 + segment score + continuity (pure, 100% covered); Bright Data provider with open-at-arrival; web: Welcome, Plan trip, Settings components |
| S2 | ~10 PM | Routes end to end | Candidates + selector + `/v1/routes`; web: map, colored segments, three route cards, fetching states wired to the API |
| S3 | ~1 AM | Explain and time | Claude explanations with template fallback; Route detail; time comparison; caching by area+hour |
| S4 | ~4 AM | Harden (freeze at start) | Blocked/slow/empty handling, Android + iPhone pass, accessibility pass, full regression, live check, bug fixes with tests |
| S5 | ~8 AM | Ship | README, demo video, Devpost, secrets scan, final live rehearsal; submit before 9:00 AM |
Stretch (heartbeat, Wear OS, Cartesia): only if S3 finishes early; likely cut. If a sprint slips, cut scope, never the tests.

## 7. Risks
| Risk | Response |
|---|---|
| Not enough hours for everything | Cut stretch first, then Route detail polish; keep core: plan trip, results, time comparison |
| Live data unreliable at demo time | Live check each sprint, cache, "not sure", rehearse; pre-warm cache for the corridor |
| Design changes mid-build | Figma fixes done in S0; later changes go through the backlog |
| Two people editing the same files | Folder ownership (web/ vs server/); contract changes only via CONTRACTS.md |
