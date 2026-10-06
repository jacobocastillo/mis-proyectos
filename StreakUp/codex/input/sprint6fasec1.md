You are implementing Phase C in the StreakUP repository.

Goal:
Improve the product layer so users can personalize habits more deeply and see richer habit details in the UI.

Scope for this phase:
- allow user-level habit renaming
- allow user-level quantity and duration targets
- ensure those targets are actually used by the system
- enrich the habit display with clearer metadata and guidance

Tasks:
1. Inspect the current frontend and backend support for:
   - custom habit name
   - quantity targets
   - duration targets
   - description/detail rendering
2. Complete any missing backend/frontend work so the user can:
   - rename a habit
   - set or update target quantity
   - set or update target unit
   - set or update target duration
3. Ensure those personalized values are reflected consistently in:
   - API responses
   - frontend display
   - validation expectations where relevant
4. Improve the habit UI so it clearly communicates:
   - what the habit is
   - how it is validated
   - what the target is
   - what evidence is expected

Important:
- Do NOT implement achievements yet
- Do NOT do visual redesign beyond what is needed to support the feature clearly
- Keep the UX simple and incremental

Expected outcome:
- habits are truly personalized per user
- metadata is visible and meaningful
- the system behavior matches the configured targets

At the end provide:
A. Files changed
B. Personalization features completed
C. UI/UX improvements made
D. Remaining work for achievements