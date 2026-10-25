# clearer leave time

- When: 2026-10-25 02:40 PT
- Who: owner request (agent: cursor)
- Branch / commit: cursor/ui-polish-01d5 / this commit
- Files touched: web/components/DepartureField.tsx, web/components/PlanTripScreen.tsx, web/components/Plan.test.tsx, web/e2e/helpers.ts, web/e2e/flow.spec.ts, docs/agent-context/DECISIONS.md
- What changed: The plan screen label is "When do you leave?" Chips read Leave now, 8 PM tonight, and 1 AM, after midnight. The note says 8 PM is this evening and 1 AM is after midnight, later the same night. Departure instants are unchanged.
- Why: "Leave" and "Tonight 1 AM" did not say that 1 AM is after midnight.
- Decisions made in chat (also added to DECISIONS.md? yes): chip wording above. STATE.md was not edited.
- Contracts affected: none
- How it was tested: `npx vitest run components/Plan.test.tsx` 16 passed. Chromium Playwright on Pixel 7 and 360px: 36 passed, including the 8 PM vs 1 AM flow.
- Unfinished / uncommitted: web/package-lock.json and docs/hackathon/ were left unstaged.
- Open issues / risks: docs/hackathon/DEMO.md still says "Tonight 8 PM". That folder belongs to the other agent.
- Next step for whoever continues: open http://localhost:3000/plan and read the leave chips.
- Needs from teammate: none
