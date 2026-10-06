You are implementing PHASE 2 ONLY for the StreakUP project.

Goal:
Make the habit create/edit flow fully support configurable validation and frequency setup from the UI and persist it correctly.

Current grounded state:
- validation_type and frequency already exist and are persisted.
- Current UI supports foto/texto/tiempo and daily/weekly.
- Duration and quantity/unit inputs exist but are not properly dynamic.
- There is no custom weekday picker.
- There is no text-rule field in forms/types.
- Backend/model support for custom schedule and min_text_length should already exist from Phase 1. :contentReference[oaicite:1]{index=1}

Scope for this phase:
1. Update create/edit screens and related form/state/types.
2. Make fields dynamic based on validation type and frequency.
3. Persist the full configuration end-to-end.
4. Do NOT implement validate/check-in execution flows yet.
5. Do NOT implement timer validation behavior yet.
6. Do NOT redesign streaks/stats yet.

Required UI behavior:
- validation type options:
  - foto
  - texto
  - tiempo
- frequency options:
  - daily
  - weekly
  - custom

Conditional behavior:
- If validation_type = foto:
  - hide text-specific rule inputs
  - hide timer-only inputs unless explicitly needed by current UX
- If validation_type = texto:
  - show min_text_length
- If validation_type = tiempo:
  - show target_duration
- If frequency = custom:
  - show weekday picker with Sunday through Saturday
  - require at least one selected day

Required work:
- Update frontend create/edit screens
- Update frontend types and form state
- Update service payloads
- Ensure backend requests include the new fields
- Ensure edit loads and re-renders existing values correctly
- Make the UI production-credible, not placeholder

Constraints:
- PHASE 2 ONLY
- Do not implement real validation execution yet
- Do not implement stats/streak schedule logic yet
- Do not over-refactor unrelated screens
- Prefer focused changes

Deliverables:
1. Working create/edit flow
2. Dynamic form rendering
3. Correct payload persistence
4. Targeted tests for create/edit behavior
5. Report of changes and remaining gaps

Validation requirements:
- Create a habit with each validation type
- Create a custom-frequency habit with selected weekdays
- Edit an existing habit and verify values reload correctly
- Confirm hidden fields do not cause bad payloads
- Confirm persistence round-trips correctly

Output format:
- Executive summary
- Files changed
- Behavior implemented
- Tests added/updated
- Validation results
- Remaining gaps for next phase