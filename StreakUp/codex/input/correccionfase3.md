You are implementing PHASE 3 ONLY for the StreakUP project.

Goal:
Convert habit validation from the current photo-only implementation into a real type-driven validation system for foto, texto, and tiempo.

Current grounded state:
- Only photo validation works end-to-end today.
- validate_habit() currently hardcodes photo behavior.
- The validate screen detects text/time but only shows placeholders.
- validation_type already persists in habits and user habits. :contentReference[oaicite:2]{index=2}

Scope for this phase:
1. Refactor backend validation flow so it dispatches by validation type.
2. Add text validation flow.
3. Add timer-validation intake flow at the API/service level.
4. Update frontend validate screen so it no longer uses placeholders for text/time.
5. Do NOT yet implement the full countdown/timer UX; timer can use a controlled completion payload for now if necessary.
6. Do NOT redesign streaks/stats yet.
7. Keep photo flow working.

Required work:
Backend:
- Refactor validation route/service to branch by habit validation type
- Support:
  - photo validation payload
  - text validation payload
  - timer completion payload
- Persist meaningful validation logs/check-in data
- Stop hardcoding tipo_validacion="foto"

Frontend:
- Update validate page to render:
  - image upload for foto
  - textarea/input for texto
  - timer-validation entry point for tiempo
- Update validation service layer to support multiple payload shapes

Validation rules:
- Foto:
  - image required
- Texto:
  - text required
  - enforce min_text_length if configured
- Tiempo:
  - accept completed timer data
  - validate against configured target duration

Constraints:
- PHASE 3 ONLY
- No full Pomodoro/countdown UX yet beyond what is necessary to unblock the timer validation contract
- No schedule-aware streak/stats redesign yet
- Keep changes focused

Deliverables:
1. Multi-type validation backend
2. Multi-type validation frontend
3. Preserved photo compatibility
4. Targeted tests for foto/texto/tiempo validation
5. Report of changes and what remains

Validation requirements:
- Photo habit can still validate successfully
- Text habit can validate with valid text and reject too-short text
- Timer habit can validate through the new timer payload path
- Validation logs/check-ins reflect the correct type
- No type is accidentally routed through photo-only behavior

Output format:
- Executive summary
- Files changed
- API changes
- Tests added/updated
- Validation results
- Remaining gaps for next phase