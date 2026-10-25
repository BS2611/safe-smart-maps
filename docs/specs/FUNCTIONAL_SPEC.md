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
| F10 | student | an opt-in heartbeat check with a trusted contact | someone is alerted if I may need help | Stretch |

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

### 5.6 Walking navigation
Start, on the route detail, opens a full-screen walk for that route. It shows the next maneuver, the distance to it, the street name (or "not sure"), and the time and distance left. Position comes from the phone's GPS in the Android app and from the browser on the web. If location is denied or there is no fix, the screen says so and offers a walk labeled Simulated that replays the route. Steps advance as the walker passes each maneuver. Leaving the line by more than about 35 m asks before recalculating from the current point. A low-scoring stretch or a stretch with no open places ahead is called out in plain words. A compass button switches the map between heading-up and north-up; if there is no compass, the map uses the GPS direction of travel or stays north-up. Street view opens the panorama at the current point. Vibration on turns can be turned off, and it stays off when the device asks for reduced motion.

### 5.7 Street-level photos
On a route's detail map, tap a point or drag the peg to open a street-level photo at that spot. Drag to look around, step forward and back along the walk, and read that stretch's score and reasons on the photo. A mini map shows position and heading. One button opens the darkest stretch. With no photo token, the screen says street view is unavailable and the rest of the walk still works. Photos are Mapillary unless a Google browser key is set.

### 5.8 Time-awareness demo
Same trip run at 8 PM and 1 AM: shops close, coverage drops, and the Safest route changes. The UI must make this visible (side-by-side or quick toggle).

### 5.9 Heartbeat alert (stretch, opt-in)
- Consent screen; user picks contact and threshold; contact must agree to receive alerts.
- Trigger: heart rate rises abnormally vs the user's own walking baseline **plus** another sign (sudden stop, large route deviation, very fast pace).
- Flow: "Are you OK?" prompt → no answer in ~30 s → message to contact with live location and route.
- Wording: "unusual heart rate detected" (no medical claim). Does not replace 911.
- Demo input: Bluetooth heart-rate band or a **clearly labeled simulated** reading. Data stays on the phone and is deleted after the trip.

## 6. States and error handling (user-visible)
| Situation | Behavior |
|---|---|
| Live data slow | Loading state; show partial results with "still loading places" |
| Page blocked / source fails | Fall back to cached data with its age; else "not sure" for that factor |
| No results for an area | "We don't have enough data here yet"; do not invent a score |
| No route within extra-time cap | Say so and show Fastest only |
| Location denied | Manual start entry only. During navigation, say location is off and offer the simulated walk |
| No compass | Map stays north-up, or uses GPS direction of travel when that exists |

## 7. Acceptance criteria
1. Entering the demo corridor trip returns three (or two, when merged) labeled routes with colored segments.
2. Changing departure time from 8 PM to 1 AM changes open-place counts, coverage, and can change the Safest route.
3. Every route card shows reasons and a data-fetched-at time; no UI text says "safe".
4. Live opening-hours data comes from real websites at demo time; no hardcoded or mocked data. Blocked, slow and empty responses are handled without crashing.
5. Route score follows the formula in 5.4 and weights in 5.3.
6. No API keys in the repo.

## 8. Out of scope (for the hackathon)
Multiple cities, accounts/login, guaranteed-safety claims, real foot-traffic counts, native apps, reading Apple Watch data from the web.

## 9. Future improvements (one demo slide)
More cities; wearable and phone-sensor input; trusted-contact live sharing; feedback on how a route felt; voice guidance (Cartesia); community-reported lighting problems; verification against real street-lighting data.

