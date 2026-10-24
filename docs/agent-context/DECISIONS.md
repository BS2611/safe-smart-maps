# DECISIONS - append one line per decision. Do not rewrite old ones.

Format: `YYYY-MM-DD HH:MM | who | decision | reason`

2026-10-24 | team | Bright Data is the core live feed; Apify only for supporting data | Bright Data prize needs it essential
2026-10-24 | team | Mapbox for map and routing; we generate candidates and re-rank ourselves | Directions API takes no custom segment costs
2026-10-24 | team | Never label a route "safe" | We describe conditions, we cannot guarantee safety
2026-10-24 10:56 | bhavpreet | Next.js frontend, Python backend (Django or FastAPI, FastAPI proposed), 3-layer architecture (presentation / service / data-access) | Swappable data sources; pending Amey's confirmation of framework
2026-10-24 11:05 | bhavpreet | Repo root = CalHack_13; layout web/ server/ scoring/ docs/specs/ docs/agent-context/; CONTRACTS.md overrides the tech spec; API is /v1/routes | One layout for kit and specs; Bhavpreet gave full authority to reconcile; Amey to confirm contract
2026-10-24 11:05 | bhavpreet | Agents must checkpoint logs every 30-45 min, record chat decisions in files immediately, and follow the handoff protocol (AGENTS.md sec 4) | Prevent context loss between agents/people
2026-10-24 10:56 | bhavpreet | Target community = students leaving a campus late | Fits Anthropic/People-First tracks; campus still to be named
2026-10-24 11:40 | bhavpreet | UI shows route labels "Most lit & active", "Balanced", "Fastest" (API value stays safest); dark theme default; mobile first | "Safest" reads as a promise
2026-10-24 12:05 | bhavpreet | Platform independent: one responsive PWA (Android Chrome + iOS Safari) plus optional Samsung Wear OS companion app; Apple Watch and native phone apps out of scope | Watch cannot be read from a phone browser; PWA keeps Next.js and one codebase
2026-10-24 12:05 | bhavpreet | Watch computes heart-rate trigger locally and reports via backend relay (memory only, deleted at trip end); fallbacks: BLE band (Android Chrome), labeled simulated | Locked phone suspends web pages; pending Amey review of relay endpoints
