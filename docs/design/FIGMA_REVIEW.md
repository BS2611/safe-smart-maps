# Figma design review

Reviewed: 2026-10-24 by Claude Code for Bhavpreet.
File: https://www.figma.com/design/vRgsr90ax1IwDkiisf89lh (Page 1, six 390 px mobile frames).
Checked against: docs/design/STITCH_UI_BRIEF.pdf, docs/specs/FUNCTIONAL_SPEC.md, docs/agent-context/CONTRACTS.md, AGENTS.md section 6.

## Verdict
Strong visual base. Needs one copy/rules pass and five missing screens before build. Do not start the matching code until the "Must fix" items for that screen are closed.

What works: dark night-friendly theme, calm tone, honest wording ("We describe conditions. We do not guarantee safety", "Not sure", fetched-at times), the 8 weights (25/20/15/10/10/10/5/5), the formula (50% average + 50% lowest 200 m minus gap penalty), the 150 m gap limit and 80% coverage target all match our spec. The loading screen's "we do not interpolate or estimate percentages" is exactly our honesty rule.

## Frames reviewed
| Node | Frame | Maps to brief screen |
|---|---|---|
| 1:374 | First-Run Welcome | 1 Welcome |
| 1:506 | First-Run - Location Denied | 1 Welcome (state) |
| 1:634 | Trip Planner - Honest Loading State | 4 Fetching live data |
| 1:862 | Route Preferences | 3 Settings |
| 1:2 | The same walk, later | 7 Time comparison |
| 1:1013 | How Scores Work | 10 About this data |

## Missing screens (blocking)
1. **Plan trip** input (from/to, departure time chip, "Tonight 8 PM / 1 AM" chips) - brief screen 2.
2. **Results: map + three route cards** - brief screen 5. This is the core screen.
3. **Route detail** (continuity block, segment strip, factor bars, AI explanation, open places) - brief screen 6.
4. Empty / error / no-route-within-cap states.
5. Install tip (iPhone: Share > Add to Home Screen) and "not supported on this browser" notices.
Stretch: Walk mode, heartbeat flow, Wear OS watch.

## Must fix (rule or truth violations)
| # | Where | Problem | Fix |
|---|---|---|---|
| M1 | Loading (1:634) "+10m extra . Safe Prioritized" | Says "safe" (AGENTS rule 6) | "Most lit & active preferred" |
| M2 | Comparison "Cached offline safety profile"; About "Quarterly Safety Report", "Mandatory safety notice" | "safety" wording | "saved offline results", "Quarterly incident report", "Important notice" |
| M3 | About title "Hazard Report", "Hazard" | Alarming | "How scores work" |
| M4 | Jargon: Telemetry, Pipeline test rig, Radar active, Field survey specimen, Edition 24.4, Night model, Corridor comparison | Our rule: plain words, calm | Plain replacements ("fresh data", "Checking your walk") |
| M5 | About sources: "Google Places / OSM" | Our core live feed is Bright Data (public listings) | "Public business listings (live)" and name Bright Data in the sources list |
| M6 | About lighting: "verified municipal fixture survey, lux estimates" | We use OSM lit tag + 311 outage reports | Say exactly that |
| M7 | About transit: "GTFS Realtime live stream (30 s)" | We plan 511/GTFS schedules | "Transit schedules (511/GTFS)" |
| M8 | About activity: "aggregated historical footfall density models" | Ours = open-venue density + time of day | Say that; keep "estimate" tag |
| M9 | About privacy: "end-to-end encrypted with temporary passcodes" | Not planned or built | Remove, or state what we do: in-memory, deleted after trip |
| M10 | Comparison "Verified venue closing hours" | Overclaim | "Closing hours from public listings, fetched 4 min ago" |
| M11 | "SAMPLE DATA", "Sample data . Live simulation", "Pipeline test rig" tabs, "Scenarios & Fallbacks" card | Developer harness shown as UI; demo must be live, no mocks | Remove from user UI; keep only behind a hidden dev flag (they map to QA states) |
| M12 | Welcome (1:506) "GRID 40.7128 N" | That is New York; demo is San Francisco (about 37.80 N) | Fix or remove |
| M13 | Comparison "74 (B)", "41 (Grade D)" | Letter grades not in CONTRACTS; judgmental | Score + band word ("Mixed", "Fewer supports") |
| M14 | Comparison "Within 60m of venue" | Spec coverage radius is 75 m | 75 m |
| M15 | Route names "Route A via Polk / Route B" | Our labels are Most lit & active / Balanced / Fastest | Use our labels, put the street in a subtitle |

## Decisions needed (scope)
| # | Item | Question |
|---|---|---|
| D1 | Bottom nav: Compare / Conditions / Explore / Layers | 3 of 4 tabs have no screens. Cut to what exists (Plan, Compare, About)? |
| D2 | "Lock Polk corridor despite gaps" | New feature (route locking) not in spec. Cut? |
| D3 | "Walking with someone ... companionship routing advice" | We do not change routing for this. Say so honestly or cut the claim |
| D4 | Red square with asterisk in the header | Unclear. If it is emergency, label it "Call 911" and keep it consistent |
| D5 | Presets "Default / Changed (+15m) / 0 min (Fastest)" | Dev states or real feature? |
| D6 | Product name contains "Safe" | The rule bans calling a route safe, not the name. Team to confirm the name is acceptable |

## Polish
- "Safe Smart Map" (header) vs "Safe Smart Maps": pick one.
- "Done" in the header and "Apply preferences" at the bottom do the same thing: keep one.
- Detour slider shows no handle at 10m.
- Clipped text: "Montg", "Destinat", "14 active venues along Po"; legend dots overlap ("Mixed" and "Fewer supports").
- 10-11 px monospace caps with low contrast: raise size and contrast for accessibility (target 12 px minimum, 4.5:1).
- Colors alone distinguish segments in places: confirm icons/patterns on the real map (brief section 3).
- No safe-area insets shown; nothing designed at 360 px (Android) or 390 px landscape.
- Warning/gap states are good; add the same "not sure" dashed style to the map legend everywhere.

## Next
See docs/design/FIGMA_FIXES_BRIEF.md for the paste-ready fix list. Once fixed, pull design tokens and components with Figma get_design_context (Sprint 0).
