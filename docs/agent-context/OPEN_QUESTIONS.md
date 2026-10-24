# OPEN QUESTIONS - unresolved items. When answered, move to DECISIONS.md (one line) and delete the row here.

| # | Question | Proposal | Owner to answer |
|---|---|---|---|
| 1 | Apify vs Bright Data split | Bright Data = core live feed (listings, hours). Apify = supporting sources/scheduled runs only. Never pull the same data from both. Check Apify pricing and Actor terms first. | both |
| 2 | Which campus / named community | One campus + 2-3 student interviews (Anthropic track) | Bhavpreet / guide |
| 3 | Demo corridor and hour | Palace of Fine Arts -> Montgomery BART; compare 8 PM vs 1 AM | both |
| 4 | Tracks to submit | Bright Data, Anthropic, Microsoft, People-First; confirm multi-track entry in #0-ask-directors | guide |
| 5 | Backend framework | FastAPI (Django possible) | Amey |
| 6 | Contract v1 in CONTRACTS.md | Amey confirms shapes and `/v1` prefix | Amey |
| 7 | Heartbeat alert in demo? | Stretch; simulated and labeled if shown | both |
| 8 | Microsoft "customer" | Only name a real one | guide |
| 9 | Repo hosting | Create GitHub repo, push this folder as root | Bhavpreet |
| 10 | Which Samsung watch model and Wear OS version does Bhavpreet have (tested = works with what)? | Galaxy Watch 4 or newer runs Wear OS; older Tizen watches cannot run our app | Bhavpreet |
| 11 | Test devices: which Android phone and which iPhone for testing? | Need one of each to prove platform independence | both / guide |
| 12 | Who builds the Wear OS app (Kotlin)? | Stretch; Bhavpreet unless Amey is faster | both |
| 13 | How does the contact get the alert (SMS provider, cost, consent flow)? | Opt-in SMS or show prompt flow only | Amey |
| 14 | Is a watch relay through our backend acceptable for the health-data rule? | In-memory, short TTL, deleted at trip end | both |
