You are implementing PHASE 1 ONLY for the StreakUP project.

Goal:
Prepare the data model and persistence layer for configurable habit validation and frequency without yet implementing the full validation flows.

Current grounded state:
- The project already persists validation_type, frequency, target_duration, target_quantity, and target_unit in both catalog habits and user habits.
- Current supported frequencies are only daily and weekly.
- There is no custom frequency support.
- There is no schedule-days table.
- There is no text-rule field like min_text_length.
- habitos_usuario is the best current extension point for user-specific configuration.
- The codebase is partially ready, moderate refactor needed. :contentReference[oaicite:0]{index=0}

Scope for this phase:
1. Extend persistence/modeling to support:
   - frequency = custom
   - optional min_text_length
   - user-specific weekday schedule storage
2. Keep existing functionality working.
3. Do NOT implement end-to-end validation flows yet.
4. Do NOT redesign stats/streaks yet.
5. Do NOT implement UI-heavy behavior beyond the minimal type alignment required by the backend/frontend contract.

Required work:
- Update database models and migrations to support:
  - custom frequency
  - min_text_length on user habits (and catalog habit only if architecture strongly benefits from it)
  - a new weekday schedule table for user habits
- Update ORM relations
- Update schemas/serializers/DTOs/types so these fields can move through the stack cleanly
- Update create/edit payload handling to accept schedule day data, but full UI behavior can remain minimal for now
- Preserve backward compatibility with existing daily/weekly habits

Constraints:
- PHASE 1 ONLY
- No full validation implementation
- No timer/check-in execution changes
- No streak/stats schedule-aware logic yet unless absolutely required for compile/runtime correctness
- Reuse current architecture patterns; do not introduce speculative catalog tables like validation_types unless the codebase already strongly uses that pattern
- Keep changes focused and production-credible

Deliverables:
1. Implementation
2. Migration(s)
3. Updated request/response/types as needed
4. Targeted tests for model and persistence behavior
5. A report with:
   - summary of changes
   - files changed
   - migrations added
   - tests added/updated
   - what remains for later phases

Validation requirements:
- Confirm create/update can persist:
  - validation_type
  - frequency including custom
  - target_duration
  - target_quantity
  - target_unit
  - min_text_length
  - schedule_days
- Confirm old daily/weekly habits still work
- Confirm no unrelated regressions

Output format:
- Executive summary
- Files changed
- Migrations
- Tests run
- Results
- Remaining gaps for next phase