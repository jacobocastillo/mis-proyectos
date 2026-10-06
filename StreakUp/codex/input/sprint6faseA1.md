You are implementing Phase A of the StreakUP repository.

Goal:
Build the structural foundation for configurable habits and multiple validation types, while keeping the current app flow stable.

Scope for this phase:
- normalize the data model for habits
- distinguish base habit definition vs user-specific habit configuration
- prepare support for validation types: photo, text, timer
- support configurable fields such as:
  - custom_name
  - validation_type
  - target_quantity
  - target_unit
  - target_duration
  - description
  - frequency
- align backend routes/services/schemas with this model

Tasks:
1. Inspect the current schema, migrations, models, seed data, backend routes, serializers/schemas, and services related to:
   - habits
   - user habits
   - check-ins / validation
2. Implement the smallest clean schema/model evolution needed so the system can support:
   - base habits
   - user-configured habits
   - future multi-type validation
3. Update backend endpoints and services so the API becomes the source of truth for habit configuration.
4. Ensure the API can read, create, and update configured user habits.
5. Keep backward compatibility where practical and avoid breaking the current flow.

Important:
- Do NOT implement strict streak reset logic yet
- Do NOT implement full text validation yet
- Do NOT implement full timer/pomodoro flow yet
- Do NOT implement achievements yet
- Do NOT do unrelated cleanup or broad rewrites

Expected outcome:
- schema/model/backend foundation ready
- API supports configurable habit metadata
- seed and models stay coherent

At the end provide:
A. Files changed
B. Schema/model decisions
C. Endpoints changed
D. Example request/response payloads
E. What remains for frontend work in the next prompt