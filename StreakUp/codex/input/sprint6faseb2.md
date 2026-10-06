You are continuing Phase B in the StreakUP repository.

Goal:
Make progress logic strict and validation-driven so streak and XP are only affected by approved validations.

Scope for this phase:
- approved validation grants progress
- pending validation does not grant progress yet
- rejected validation does not grant progress
- rejected validation should reset or break streak according to the intended product behavior
- eliminate premature streak/XP increments

Tasks:
1. Inspect the current backend logic for:
   - check-ins
   - validation result handling
   - streak calculation
   - XP/stat updates
2. Refactor the flow so the order becomes:
   - user submits evidence
   - validation attempt is recorded
   - validation result is determined
   - only then are streak/XP/progress effects applied
3. Implement the rejected-validation streak reset behavior in a clean and deterministic way.
4. Prevent double counting, duplicate rewards, and premature stat updates.
5. Update or add backend tests for:
   - approved grants progress
   - pending grants nothing
   - rejected grants nothing
   - rejected breaks/reset streak
   - no double increment bugs

Important:
- Do NOT implement achievements yet
- Avoid unrelated rewrites
- Stay grounded in existing repository patterns
- If legacy compatibility logic is needed, keep it explicit and temporary

Expected outcome:
- streak and XP are validation-driven
- failed validations have real consequences
- stat updates are consistent and testable

At the end provide:
A. Files changed
B. Business rules implemented
C. Edge cases handled
D. What remains for Phase C