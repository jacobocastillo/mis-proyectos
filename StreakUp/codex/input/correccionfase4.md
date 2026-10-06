You are implementing PHASE 4 ONLY for the StreakUP project.

Goal:
Integrate a real countdown/timer UX into the habit validation flow for tiempo-based habits, using the configured target duration.

Current grounded state:
- target_duration already persists.
- There is an existing Pomodoro/timer-related screen and service stack in the project.
- Timer validation does not currently launch from the habit validation flow.
- The closest reusable asset is the standalone Pomodoro flow, but it is separate from habit progress. :contentReference[oaicite:3]{index=3}

Scope for this phase:
1. Build or adapt a countdown/timer experience triggered from validating a tiempo habit.
2. Use the habit’s configured target duration.
3. Complete timer validation only when the required duration is completed.
4. Connect the finished timer back into the validation/check-in flow.
5. Do NOT redesign frequency/streak/stats yet.

Required UX:
- User opens validate for a tiempo habit
- User can start the timer
- Timer uses configured duration
- User can see active timer progress
- Completion produces a valid timer-based check-in/validation
- If the timer is abandoned early, it should not count as completed

Required work:
- Reuse/adapt existing Pomodoro timer assets if practical
- Integrate timer completion with habit validation
- Persist completion timestamps and completed seconds
- Keep UX focused and reliable

Constraints:
- PHASE 4 ONLY
- No schedule-aware eligibility logic yet
- No stats/streak redesign yet
- Avoid building a second disconnected timer system if current Pomodoro code can be reasonably reused

Deliverables:
1. Functional timer-based habit validation flow
2. Integrated frontend UX
3. Backend persistence for completed timer validation
4. Targeted tests
5. Report of changes and remaining gaps

Validation requirements:
- A tiempo habit loads the configured duration correctly
- Completing the timer creates a successful validation/check-in
- Abandoning early does not count
- Existing Pomodoro functionality is not broken
- Photo/text validation flows still work

Output format:
- Executive summary
- Files changed
- UX implemented
- Tests added/updated
- Validation results
- Remaining gaps for next phase