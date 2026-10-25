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
