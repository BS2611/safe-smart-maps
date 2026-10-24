# Safe Smart Maps – Task Breakdown

Team: **Dev A** (frontend/presentation), **Dev B** (backend/service + data), **Guide** (third person: advice, story, submission content; not heavy build work). Swap owners based on strengths.
Deadline: Sunday 9:00 AM PT. Plan in blocks; "Est." in hours.

## M0 – Kickoff together (Now – ~1h)
| # | Task | Owner | Est. | Done when |
|---|---|---|---|---|
| 0.1 | Create GitHub repo, add docs, branch rules (main + feature branches) | Dev A | 0.25 | Both can push |
| 0.2 | Answer docs/agent-context/OPEN_QUESTIONS.md items: corridor, campus, backend framework, Apify split | All | 0.5 | Decisions filled in |
| 0.3 | Freeze API contract + sample JSON (TECHNICAL_SPEC §4) | A + B | 0.5 | `sample_routes.json` agreed |
| 0.4 | Get Mapbox and Bright Data keys working locally (not committed) | B (A for Mapbox browser token) | 0.5 | Test call succeeds |

## M1 – Scaffolds (until ~10 AM)
| # | Task | Owner | Est. |
|---|---|---|---|
| 1.1 | Next.js app, Mapbox map loads, geocoding search for start/destination | A | 2 |
| 1.2 | Settings layout (extra minutes, alone/with someone, priorities, time picker) | A | 1 |
| 1.3 | FastAPI scaffold, `/v1/health`, config loader + weight validation | B | 1 |
| 1.4 | Provider interfaces + cache skeleton (3-layer folders) | B | 1 |

## M2 – Live data and map rendering (10 AM – 1 PM)
| # | Task | Owner | Est. |
|---|---|---|---|
| 2.1 | Render colored segments + route line from the sample JSON | A | 2 |
| 2.2 | Bright Data pull: listings + hours for the corridor | B | 2.5 |
| 2.3 | Opening-hours → open/closed at arrival time | B | 1 |
| 2.4 | OSM road/lit tags; help points | B | 1.5 |

## M3 – Scoring and cards (1 – 4 PM)
| # | Task | Owner | Est. |
|---|---|---|---|
| 3.1 | Three-route comparison cards, label merge display | A | 2 |
| 3.2 | Time picker wired to request; data-fetched-at badge | A | 1 |
| 3.3 | Segmenter + segment scoring from `scoring_v1.json` | B | 2 |
| 3.4 | Continuity rule (coverage, longest gap, worst window, penalty) | B | 1.5 |
| 3.5 | Candidate generation (Mapbox alternatives + waypoint detours) and selector | B | 1.5 |

## M4 – Integration (4 – 7 PM)
| # | Task | Owner | Est. |
|---|---|---|---|
| 4.1 | Connect UI to live `/v1/routes`; loading/empty/error states | A | 2.5 |
| 4.2 | Claude explanations with template fallback | B | 1.5 |
| 4.3 | Settings change weights; 311, 511 and incidents (low weight) providers | B | 1.5 |

## M5 – Hardening (7 – 10 PM)
| # | Task | Owner | Est. |
|---|---|---|---|
| 5.1 | End-to-end tests; empty and slow data handling in UI | A | 2 |
| 5.2 | Caching, retries/backoff, blocked-page handling | B | 2 |
| 5.3 | "Not sure" labels and wording audit (no "safe") | A + Guide | 0.5 |

## M6 – Polish and demo (10 PM – 1 AM)
| # | Task | Owner | Est. |
|---|---|---|---|
| 6.1 | 8 PM vs 1 AM demo flow polished | A | 2 |
| 6.2 | Bug fixes; verify data-fetched-at everywhere | B | 2 |
| 6.3 | Demo script (2-minute story, real results) | Guide | 1 |

## M7 – Submission (1 – 9 AM, sleep in shifts)
| # | Task | Owner |
|---|---|---|
| 7.1 | README (setup, sponsor tools and where used, known limits); secrets scan | B |
| 7.2 | Record demo video; set table number; project image | A |
| 7.3 | Devpost text, tracks selected, GitHub link; **submit before 9:00 AM** | B + Guide |

## Platform tasks (core: both phones)
| # | Task | Owner | Est. |
|---|---|---|---|
| P.1 | PWA setup (manifest, icons, service worker), safe-area insets, keyboard-aware inputs | A | 1.5 |
| P.2 | Test every must-have screen on a real Android phone (Chrome) and a real iPhone (Safari, installed to home screen); fix layout and map issues | A | 2 |
| P.3 | Feature detection + fallback messages (Bluetooth, vibration, wake lock, push) | A | 1 |
| P.4 | Find an iPhone for testing (borrow from the guide or a friend) | Guide | 0.2 |

## Stretch (only if core is done)
Heartbeat alert, Cartesia voice, Convex saved trips.
| # | Task | Owner | Est. |
|---|---|---|---|
| W.1 | Confirm the Samsung watch model and Wear OS version; enable developer mode and ADB over Wi-Fi | A | 0.5 |
| W.2 | Watch app skeleton (Kotlin, Compose for Wear OS), read heart rate with Health Services on the real watch | A (or Guide pairs) | 3 |
| W.3 | Relay endpoints in CONTRACTS (pair, heartbeat, stream, alerts) in memory only | B | 2 |
| W.4 | Pairing screen in web app + live bpm display, Simulated badge | A | 1.5 |
| W.5 | Watch prompt: baseline, trigger, 30 s countdown, haptics, alert call | A | 2 |
| W.6 | Contact message provider (SMS) with opt-in check; or show prompt flow only and say so | B | 1.5 |
| W.7 | Fallback: simulated source, Bluetooth band on Android Chrome | A | 1 |

## Guide responsibilities
Quotes from 2–3 real students (Anthropic track), customer story and measurable results (Microsoft track), confirm with organizers (#0-ask-directors) that one project can enter several tracks, review demo for the "never say safe" rule.

## Risks
| Risk | Mitigation |
|---|---|
| Bright Data pages blocked or slow | Cache + "not sure" fallback; test early (2.2) |
| Scope creep | Core = M0–M5; stretch only after |
| Sleep/time | Shifts in M7; one person always on bug fixes |
| Keys committed | `.gitignore`, `.env.example`, final scan (7.1) |

