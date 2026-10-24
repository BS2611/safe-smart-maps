# Safe Smart Maps – Functional Specification

Version 0.1 · Cal Hacks 13.0 · Deadline: Sunday 9:00 AM PT

## 1. Purpose
Normal maps show the fastest walking route. Safe Smart Maps shows three walking routes for the time the user will actually be on the street, scored on lighting, open businesses, main roads, help points and transit, and on whether those are spread along the whole route (the continuity rule).

## 2. Target community and persona
**Community:** students leaving a campus late at night (campus name to be confirmed in docs/agent-context/OPEN_QUESTIONS.md).
**Persona – "Maya", 20, undergrad:** leaves the library at 10:40 PM, walks 15–25 minutes to transit or home, often alone. She will trade a few extra minutes for a route that stays lit and has open places along the whole way, and she wants to see *why* a route is recommended.

## 3. Wording and responsible-design rules (apply to all UI text)
- Never say a route is "safe". Use "better lit and more active". Always show reasons and data times.
- Missing or old data → show "not sure", never guess.
- Activity is an **estimate**, labeled as such; never presented as a real people count.
- Past-incident data has low weight and is disclosed as such.
- AI explanations carry the note "Explained by AI, may be wrong." Emergency notice: "For an emergency, call 911."
- Location is used only during the trip, deleted afterward, and sharing is opt-in.

## 4. User stories
| ID | As a… | I want… | So that… | Priority |
|---|---|---|---|---|
| F1 | student | to search a start and destination | I can plan a walk | Must |
| F2 | student | to pick a departure time | scores reflect when I will pass each place | Must |
| F3 | student | to see three routes (Safest, Balanced, Fastest) on a map | I can compare them | Must |
| F4 | student | route segments colored green/yellow/red | I see weak stretches at a glance | Must |
| F5 | student | a comparison card per route | I see extra minutes, coverage %, longest gap, open places, nearest help point | Must |
| F6 | student | a plain-language explanation | I understand the reasons | Must |
| F7 | student | to set max extra minutes, alone/with someone, factor priorities | the result fits me | Should |
| F8 | student | to see "data fetched at" time and "not sure" labels | I know how fresh the info is | Must |
| F9 | student | to compare the same trip at 8 PM vs 1 AM | I see how closing times change the result | Must (demo) |
| F10 | student | an opt-in heartbeat check with a trusted contact, using my watch | someone is alerted if I may need help | Stretch |
| F11 | student | the same app on my Android or iPhone | I can use whatever phone I have | Must |
| F12 | student | a watch prompt I can answer without taking out my phone | I can confirm I am OK quickly | Stretch |

## 5. Features

### 5.1 Trip input
Start and destination (geocoded search), departure time (default now), settings screen: maximum extra minutes, walking alone or with someone, and which factors matter most (adjusts weights within limits).

### 5.2 Three routes
- **Fastest:** shortest travel time.
- **Safest:** highest route score within the user's extra-time cap (labeled "most lit and active", not "safest" in UI copy where possible).
- **Balanced:** best trade-off of score and time.
- If two labels pick the same route, show it once and say so ("Safest and Balanced are the same route").
- 5–8 candidate routes are generated; the three are chosen from them.

### 5.3 Segment score (0–100 per ~50 m, evaluated at the user's arrival time at that point)
| Factor | Weight |
|---|---|
| Open places nearby (~50 m; 24-hour pharmacies, gas stations, restaurants count more) | 25% |
| Lighting (lit tag; recent outage reports reduce) | 20% |
| Main road share | 15% |
| Open help points (hospital, police, fire, 24-hour store within ~150 m) | 10% |
| Transit running (stop nearby, service in next ~15 min) | 10% |
| Activity estimate (open-venue density + time of day) | 10% |
| Past incidents | 5% |
| Turns and dead ends | 5% |
Total = 100%.

### 5.4 Continuity rule
- **Coverage:** share of route within ~75 m of an open place, help point or active transit stop. Target ≥ 80%.
- **Longest gap:** longest stretch with nothing nearby; penalize beyond ~150 m.
- **Worst window:** lowest average over any rolling 200 m.
- **Route score** = 0.5 × average segment score + 0.5 × worst-window score − gap penalty.
- Shown in words, e.g. "Longest empty stretch: 220 m near the park."

### 5.5 Map and comparison cards
Colored segments on the map. Each route card: extra minutes, coverage %, longest gap, number of open places, nearest help point, data-fetched-at time, and the AI explanation with reasons.

### 5.6 Time-awareness demo
Same trip run at 8 PM and 1 AM: shops close, coverage drops, and the Safest route changes. The UI must make this visible (side-by-side or quick toggle).

### 5.7 Heartbeat alert (stretch, opt-in)
- Consent screen; user picks contact and threshold; contact must agree to receive alerts.
- Trigger: heart rate rises abnormally vs the user's own walking baseline **plus** another sign (sudden stop, large route deviation, very fast pace).
- Flow: "Are you OK?" prompt (on the wrist when a watch is paired, otherwise on the phone) -> no answer in ~30 s -> message to contact with live location and route.
- Wording: "unusual heart rate detected" (no medical claim). Does not replace calling 911.
- Inputs, best to worst: (1) **Samsung Galaxy Watch (Wear OS) companion app** reading the watch heart-rate sensor; (2) Bluetooth heart-rate band (Android Chrome only); (3) a **clearly labeled simulated** reading. Never present simulated data as real.
- Heart rate is health data: opt-in, minimal, kept in memory only, deleted when the trip ends, the user chooses the contact and threshold.

### 5.8 Platforms
Platform independent: one responsive web app (installable to the home screen) that works on **Android** (Chrome) and **iOS** (Safari), plus an optional **Wear OS watch companion** (tested watch: Samsung, model to be confirmed). Phone browsers cannot read a watch directly, so the watch app sends data through our backend (see TECHNICAL_SPEC section 8).
| Capability | Android Chrome | iOS Safari (installed to home screen) | Wear OS watch app |
|---|---|---|---|
| Plan trip, map, routes, details, time comparison | Yes | Yes | No (glance only) |
| Walk mode with screen on (wake lock) | Yes | Yes (iOS 16.4+) | Glance of next stretch |
| Tracking with screen locked | Limited | No | Yes, runs on the wrist |
| Vibration on prompts | Yes | No | Yes (haptics) |
| Bluetooth heart-rate band from the web | Yes | **No** | n/a |
| Watch heart rate | Via watch app | Via watch app | Native sensor |
| Push notifications | Yes | Only when installed to home screen (iOS 16.4+) | Yes |
Rules: every feature must degrade gracefully with a clear message, e.g. "Heart-rate input is not supported on this browser. Use a paired watch or the simulated reading." Core demo (routes and time comparison) must work on both Android and iOS.
Watch (stretch) screens: pairing code entry, "Walking" status with next-stretch hint, "Are you OK?" prompt with 30 s countdown and big "I'm OK" button, "Alert sent" with cancel. Small round screen, glanceable, one action per screen.
## 6. States and error handling (user-visible)
| Situation | Behavior |
|---|---|
| Live data slow | Loading state; show partial results with "still loading places" |
| Page blocked / source fails | Fall back to cached data with its age; else "not sure" for that factor |
| No results for an area | "We don't have enough data here yet"; do not invent a score |
| No route within extra-time cap | Say so and show Fastest only |
| Location denied | Manual start entry only |

## 7. Acceptance criteria
1. Entering the demo corridor trip returns three (or two, when merged) labeled routes with colored segments.
2. Changing departure time from 8 PM to 1 AM changes open-place counts, coverage, and can change the Safest route.
3. Every route card shows reasons and a data-fetched-at time; no UI text says "safe".
4. Live opening-hours data comes from real websites at demo time; no hardcoded or mocked data. Blocked, slow and empty responses are handled without crashing.
5. Route score follows the formula in 5.4 and weights in 5.3.
6. No API keys in the repo.

## 8. Out of scope (for the hackathon)
Multiple cities, accounts/login, guaranteed-safety claims, real foot-traffic counts, native phone apps (we ship one web app for Android and iOS), Apple Watch app, reading any watch directly from a phone browser.

## 9. Future improvements (one demo slide)
More cities; wearable and phone-sensor input; trusted-contact live sharing; feedback on how a route felt; voice guidance (Cartesia); community-reported lighting problems; verification against real street-lighting data.

