# Safe Smart Maps - Backlog by sprint

Method, Definition of Done and test strategy: docs/specs/AGILE_PLAN.md. Every story below includes its unit tests and a full regression run; "Done" means the DoD is met.
Owners: **A** = Bhavpreet (web/, design), **B** = Amey (server/, scoring/), **G** = guide. Est. in hours. Swap owners by strength.
Deadline: Sunday 9:00 AM PT.

## Status (updated 2026-10-24 evening, branch `ui`)
Verified by `bash scripts/verify.sh`: backend 169 tests, web 200 unit tests, 54 browser tests (3 phone sizes) incl. accessibility. All green.
- **Done:** S0 setup; S1 scoring, continuity, selector, providers, Welcome, Plan trip, Preferences; S2 `/v1/routes`, map, three route cards, checking states; S3 explanations, caching, Route detail, 8 PM vs 1 AM compare, How scores work; S4 accessibility automation, home-screen install (manifest, icons, tip), cache pre-warm; S5 README.
- **Not done / needs a person:** live runs with real Mapbox, Bright Data and Claude keys (`pytest -m live`); real iPhone and Android phone checks; confirm Bright Data `open_hours` shape; GitHub push, CI first run, branch protection; Amey's review of CONTRACTS and shared-file edits; Figma updates (missing screens, copy fixes); demo video, Devpost text, tracks.
- **Not built (stretch):** walk mode, heartbeat check, Wear OS app, voice, transit schedule feed.

## S0 - Foundations (Sat now to ~5 PM)
| # | Story | Owner | Est. | Tests / done when |
|---|---|---|---|---|
| 0.1 | Apply docs/design/FIGMA_FIXES_BRIEF.md in Figma (must-fix copy, missing screens) | A | 2 | Review checklist in FIGMA_REVIEW.md all ticked |
| 0.2 | Export tokens (colors, type, spacing) with Figma get_design_context into `web/` theme | A | 1 | Token file unit-tested for contrast pairs |
| 0.3 | Create GitHub repo, push, branch protection (green CI + 1 review) | A | 0.5 | PR from branch merges only when checks pass |
| 0.4 | CI skeleton (lint, type-check, pytest, Vitest, Playwright) with one trivial passing test per tool | A + B | 1.5 | CI green on a test PR |
| 0.5 | Review and merge Amey's scaffold (`amey/backend-scaffold`) | A | 0.5 | pytest for `/v1/health` and weights-sum check |
| 0.6 | Confirm CONTRACTS v1 and FastAPI; answer OPEN_QUESTIONS 5, 6, 13, 14 | B | 0.5 | CONTRACTS status set to CONFIRMED |
| 0.7 | Decide scope items D1-D6 from FIGMA_REVIEW.md | A + B | 0.3 | DECISIONS lines added |
| 0.8 | Find an Android phone and an iPhone for testing | G | 0.3 | Devices named in STATE |

## S1 - Data truth (to ~7 PM)
| # | Story | Owner | Est. | Tests |
|---|---|---|---|---|
| 1.1 | `scoring_v1.json` loader and validation | B | 0.5 | Weights sum, bounds, bad file rejected |
| 1.2 | Segmenter (50 m, arrival time per segment) | B | 1.5 | Lengths, time stepping, short routes |
| 1.3 | Segment scoring from config | B | 1.5 | Each factor, missing factor gives "unknown" |
| 1.4 | Continuity (coverage, longest gap, worst 200 m, penalty) and route score | B | 1.5 | Golden-file tests, empty-stretch cases, 100% coverage |
| 1.5 | Bright Data provider: listings and hours, open/closed at arrival | B | 3 | Fixture parsing; blocked/slow/empty; past midnight, 24 h; `@live` smoke |
| 1.6 | web: Welcome + Location Denied components | A | 1.5 | Vitest per state; Playwright at 390 and 360 |
| 1.7 | web: Plan trip screen (search, time chip, 8 PM/1 AM chips) | A | 2 | Form states, keyboard, time logic tests |
| 1.8 | web: Settings (extra minutes, alone/with someone, priorities max 2) | A | 1.5 | Limits, reset, weights adjust within bounds |

## S2 - Routes end to end (to ~10 PM)
| # | Story | Owner | Est. | Tests |
|---|---|---|---|---|
| 2.1 | Candidate routes (Mapbox alternatives plus detours via waypoints) | B | 2.5 | Provider interface with fixtures; 5-8 candidates |
| 2.2 | Selector (Fastest, Safest within cap, Balanced; merged labels) | B | 1 | Edge cases, ties, cap too small |
| 2.3 | `POST /v1/routes` per CONTRACTS | B | 2 | TestClient, errors, `warnings`, contract test |
| 2.4 | OSM road/lit tags; 311 outages; help points | B | 2 | Provider fixtures; stale/missing data |
| 2.5 | web: Map with colored segments + legend (icons, not color alone) | A | 2.5 | Component tests; WebKit screenshot |
| 2.6 | web: Three route cards + merged card + fetched-at badge | A | 2 | All variants, "not sure" case |
| 2.7 | web: Fetching checklist wired to real stages | A | 1.5 | Normal, slow, unavailable states |

## S3 - Explain and time (to ~1 AM)
| # | Story | Owner | Est. | Tests |
|---|---|---|---|---|
| 3.1 | Claude explanations with template fallback | B | 1.5 | Fallback on failure; no "safe" in output (test) |
| 3.2 | Cache scored data by area+hour | B | 1.5 | Hit/miss/TTL tests |
| 3.3 | Transit (511/GTFS) and incidents (low weight) providers | B | 2 | Fixtures; weights respected |
| 3.4 | web: Route detail (continuity, strip, factors, explanation) | A | 3 | Component and e2e tests |
| 3.5 | web: Time comparison 8 PM vs 1 AM | A | 2.5 | Same trip, route changes, e2e |
| 3.6 | web: About / How scores work | A | 1 | Copy test: weights match scoring_v1 |

## S4 - Harden (to ~4 AM; freeze at start)
| # | Story | Owner | Est. | Tests |
|---|---|---|---|---|
| 4.1 | Blocked page, timeout, retry/backoff everywhere | B | 2 | Simulated failures through the API |
| 4.2 | Feature detection and fallbacks; install tip; safe areas; keyboard | A | 2 | Playwright WebKit + Chromium, 390 and 360 |
| 4.3 | Accessibility pass (contrast, 48 px targets, labels) | A | 1 | Automated a11y checks in Playwright |
| 4.4 | Full regression, `@live` run, rehearse 8 PM vs 1 AM | A + B + G | 1.5 | All green, live check noted in log |
| 4.5 | Pre-warm cache for the demo corridor | B | 0.5 | Cache hit test |

## S5 - Ship (to ~8 AM, submit before 9:00 AM)
| # | Story | Owner |
|---|---|---|
| 5.1 | README (setup, sponsor tools and where used, known limits); secrets scan | B |
| 5.2 | Demo video, table number, project image | A |
| 5.3 | Devpost text, tracks, GitHub link, community quotes, customer story | G + B |
| 5.4 | Final live rehearsal; submit | all |

## Stretch (only if S3 finishes early)
| # | Story | Owner | Est. |
|---|---|---|---|
| X.1 | Walk mode (wake lock, next-stretch hint) | A | 2.5 |
| X.2 | Heartbeat flow with simulated source, labeled | A | 3 |
| W.1-W.7 | Wear OS companion (pair, heartbeat, prompt, alert); needs watch model (OPEN_QUESTIONS 10) | A / B | 12+ |
| X.3 | Cartesia voice readout | A | 2 |

## Guide responsibilities
Quotes from 2-3 real students (Anthropic track), customer story and results (Microsoft track), confirm multi-track entry with organizers (#0-ask-directors), test on real Android and iPhone, review demo for the "never say safe" rule.

## Risks
See docs/specs/AGILE_PLAN.md section 7.
