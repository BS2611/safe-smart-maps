# Safe Smart Maps

Walking routes scored for the time you will be on the street. Built for students heading home after dark. Cal Hacks 13.0.

The app compares a few walks by lighting, open places, main roads, help points, and whether those hold up along the whole route. It describes conditions. It does not guarantee safety.

## Demo in one minute

1. Open the web app and choose Get started.
2. From Palace of Fine Arts to Montgomery BART. Leave at 8 PM.
3. Compare the scores on the map. Open a route and tap a stretch.
4. Compare the same walk at 1 AM. Places close, coverage drops.

## Repo

| Path | What |
|---|---|
| `web/` | Next.js app |
| `server/` | API, routing, scoring |
| `scoring/scoring_v1.json` | Weights and thresholds |
| `docs/specs/` | What the product does |

Do not commit API keys. Names live in `.env.example`.

## Street-level photos

On a route, tap the map or drag the peg to look at that spot from street level. Step forward and back along the walk. One button opens the darkest stretch. The photo is a picture of the street; the score and reasons are the same numbers as the rest of the app.

Photos come from [Mapillary](https://www.mapillary.com/) through `mapillary-js`. Put a Mapillary client token in `web/.env.local`:

`NEXT_PUBLIC_MAPILLARY_TOKEN`

Create it in the Mapillary dashboard (a client token, restricted by site URL). The browser can see it, so do not use a secret token, and do not commit it.

To use Google Street View instead, set `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` (a browser key, restricted by HTTP referrer, with the Maps JavaScript API enabled). If that name is set, the app uses Google and does not use the Mapillary token. If neither name is set, the screen says street view is unavailable and the rest of the walk still works.
