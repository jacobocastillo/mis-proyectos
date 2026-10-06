You are implementing PHASE 5 ONLY for the StreakUP project.

Goal:
Make habit frequency operationally meaningful so daily, weekly, and custom schedules affect whether a habit is eligible to validate today.

Current grounded state:
- Frequency is stored, but not actually enforced in today/check-in/stats/streak logic.
- The backend currently returns active habits without real schedule filtering.
- Weekly is stored but behaves like daily in practice.
- Custom schedule support should already exist at the model/persistence level from earlier phases. :contentReference[oaicite:4]{index=4}

Scope for this phase:
1. Implement schedule-aware “can validate today?” logic.
2. Apply it to habit listing and validation eligibility.
3. Enforce:
   - daily
   - weekly
   - custom weekdays
4. Do NOT yet redesign final streak/stat formulas unless minimally required for correctness in the touched paths.
5. Keep validation behavior intact.

Required work:
Backend:
- Add eligibility logic for:
  - daily
  - weekly
  - custom
- Apply it to:
  - today habits retrieval
  - validation/check-in permission
- Prevent invalid validations on non-eligible days

Frontend:
- Reflect eligibility state in the dashboard/habit actions
- Avoid offering invalid actions when the habit should not be validated today

Suggested rule shape:
- daily: eligible every day
- weekly: eligible once per active week window
- custom: eligible only on enabled weekdays

Constraints:
- PHASE 5 ONLY
- No full streak/stat redesign yet unless necessary for safe behavior on changed endpoints/screens
- Avoid speculative scheduler/reminder work
- Keep changes grounded

Deliverables:
1. Eligibility logic
2. Schedule-aware today/validate behavior
3. Targeted tests
4. Report of changes and remaining gaps

Validation requirements:
- Daily habits are eligible every day
- Weekly habits can only count once per week
- Custom habits are only eligible on configured days
- Invalid-day validation attempts are rejected cleanly
- Existing completed validations remain intact

Output format:
- Executive summary
- Files changed
- Eligibility rules implemented
- Tests added/updated
- Validation results
- Remaining gaps for next phase