You are continuing Phase A in the StreakUP repository.

Goal:
Align the frontend with the new backend-backed habit configuration model so the UI uses real metadata instead of hardcoded assumptions or partial local-only logic.

Scope for this phase:
- update frontend types/services/hooks/components to match the backend payloads
- render configurable habit metadata from API
- enable online editing of habit configuration
- visually distinguish validation types and targets

Tasks:
1. Inspect the current frontend code for:
   - habit list
   - habit cards
   - habit creation/editing
   - services/hooks/types related to habits
2. Update frontend types/models to support fields such as:
   - custom_name
   - validation_type
   - target_quantity
   - target_unit
   - target_duration
   - description
   - frequency
3. Connect the habit editing flow to the real backend instead of local-only assumptions.
4. Render validation type and targets dynamically in the UI.
5. Keep the UI incremental and repository-consistent.

Important:
- Do NOT implement full text evidence submission yet
- Do NOT implement full timer/pomodoro flow yet
- Do NOT implement strict streak reset logic yet
- Do NOT implement achievements UI yet
- Avoid unrelated refactors

Expected outcome:
- frontend now consumes real backend metadata
- configurable habits can be edited online
- UI is ready for multi-validation support in the next phase

At the end provide:
A. Files changed
B. UI flows updated
C. What is now working
D. What remains for Phase B