You are implementing PHASE 6 ONLY for the StreakUP project.

Goal:
Make streaks and stats frequency-aware so they reflect real scheduled behavior instead of assuming all habits are daily.

Current grounded state:
- Current streak logic is consecutive-calendar-day based.
- Current stats assume all active habits are eligible daily and often use total_habits * 7 style formulas.
- This misstates weekly and future custom-schedule habits. :contentReference[oaicite:5]{index=5}

Scope for this phase:
1. Redesign streak logic to respect frequency.
2. Redesign stats/summary logic to respect actual schedule opportunities.
3. Preserve correctness for existing daily habits.
4. Do NOT redesign unrelated dashboard features.

Required behavior:
- daily habits:
  - streak based on consecutive daily completion opportunities
- weekly habits:
  - streak based on consecutive successful weeks
- custom habits:
  - streak based on scheduled occurrences, not raw calendar days
- summary stats:
  - today totals based on habits actually eligible today
  - week possible/completion based on real schedule opportunities

Required work:
- Update streak service
- Update stats service
- Update any dependent serializers/endpoints/UI assumptions
- Add targeted tests covering daily, weekly, and custom cases

Constraints:
- PHASE 6 ONLY
- Do not rework validation execution flows unless required for correctness
- Keep formulas explainable and stable
- Avoid hidden magic assumptions

Deliverables:
1. Schedule-aware streak logic
2. Schedule-aware stats logic
3. Updated dependent tests
4. Report of changes and remaining gaps

Validation requirements:
- Daily streak behavior remains correct
- Weekly streaks do not use day-by-day logic
- Custom streaks respect scheduled weekdays
- Stats no longer treat every habit as daily
- Dashboard-facing summaries are coherent with actual eligibility

Output format:
- Executive summary
- Files changed
- Logic updated
- Tests added/updated
- Validation results
- Remaining gaps for next phase