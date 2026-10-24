# Figma fixes brief (paste to the designer / Stitch / Figma AI)

Apply to the current Safe Smart Maps file. Full reasoning: docs/design/FIGMA_REVIEW.md.

## 1. Add these screens (same dark style, 390 x 844, plus a 360 x 800 check of the results screen)
1. **Plan trip**: map behind a bottom sheet; From (default "My location") and To fields with suggestions and a swap button; departure chip ("Leave now" or time picker) with the line "Scores use the time you reach each street, not when you leave"; quick chips "Tonight 8 PM" and "Tonight 1 AM"; primary "Show routes"; settings icon.
2. **Results**: full-bleed map showing the selected route as colored segments (each with an icon or pattern, not color alone), the other two faded; bottom sheet (peek/half/full) with three route cards: **Most lit & active**, **Balanced**, **Fastest**. Each card: minutes and "+6 min vs fastest", score word, coverage %, longest empty stretch with place, open places count, nearest help point and distance. Merged case: one card with two badges. "Data fetched at 10:31 PM" badge. Buttons: Details, "Compare 8 PM vs 1 AM".
3. **Route detail**: header; continuity block (coverage bar with 80% marker, longest empty stretch, lowest 200 m score); segment strip; tapped-segment popover with reasons; 8 factor bars with weights; AI explanation card with "Explained by AI, may be wrong"; open-places list; sources and fetched-at.
4. **States**: no route within extra-time cap, no data for this area ("We don't have enough data here yet"), source failed (warning banner), data stale (older than 2 h).
5. **Install tip card** (iPhone: Share > Add to Home Screen; Android banner) and a "not supported on this browser" notice.

## 2. Fix the copy (exact replacements)
| Find | Replace with |
|---|---|
| Safe Prioritized | Most lit & active preferred |
| Cached offline safety profile | Saved results from your last check |
| Quarterly Safety Report | Quarterly incident report |
| Mandatory Safety Notice | Important notice |
| Hazard Report / Hazard | How scores work |
| Fresh Telemetry Recalculation | Recalculating with fresh data |
| Pipeline test rig, Edition 24.4, Night model, Radar active, Field survey specimen | delete |
| Corridor Comparison | Route comparison |
| SAMPLE DATA, "Sample data . Live simulation" | delete (dev flag only) |
| Scenarios & Fallbacks card, Normal/Slow/Unavailable tabs | remove from the user view |
| Verified venue closing hours | Closing hours from public listings |
| Google Places / OSM | Public business listings (live) |
| Verified municipal fixture survey, lux estimates | OpenStreetMap "lit" tag and 311 streetlight outage reports |
| GTFS Realtime live stream (30s cadence) | Transit schedules (511 / GTFS) |
| Aggregated historical foot-traffic models | Estimate from open venues nearby and time of day |
| End-to-end encrypted with temporary passcodes | Kept in memory only and deleted when the trip ends |
| 74 (B), 41 (Grade D) | 74 Better lit and active / 41 Fewer supports |
| Within 60m of venue | Within 75 m of an open place |
| Route A (via Polk) / Route B | Most lit & active (via Polk) / Balanced / Fastest |
| Safe Smart Map | Safe Smart Maps |
| GRID 40.7128 N | San Francisco, or delete |
Also add "Bright Data" to the sources list as the live business-hours source.

## 3. Decide, then cut or define (reply to Bhavpreet)
Bottom nav tabs Conditions / Explore / Layers; "Lock corridor" option; "companionship routing advice" claim; red asterisk header button (label "Call 911" if emergency); preset chips on Route Preferences; keep either "Done" or "Apply preferences".

## 4. Layout and accessibility
Fix clipped text (origin/destination labels, "14 active venues along..."); stop legend dots overlapping; min text 12 px and 4.5:1 contrast; show the slider handle; add safe-area padding top and bottom; check 360 px width; tap targets at least 48 px.
