You are continuing Phase C in the StreakUP repository.

Goal:
Add the foundation for achievements/badges/milestones and harden the full habit-validation-progress flow.

Scope for this phase:
- create an extensible achievements foundation
- connect achievements to validated progress where appropriate
- strengthen tests and seed/demo data for the new product direction

Tasks:
1. Inspect the current XP/streak/stats model and determine the cleanest way to introduce:
   - achievements
   - badges
   - milestones
   - optional XP rewards
2. Implement the minimal clean data model and backend logic needed for achievement support.
3. Add a few representative example achievements, such as:
   - first approved validation
   - 7-day streak
   - 30 approved habit completions
4. Update seed/demo data and tests so the repository reflects the new product direction.
5. Harden the overall system with tests covering:
   - configurable habits
   - multi-type validation
   - strict streak logic
   - XP updates
   - achievement awarding

Important:
- Do NOT overengineer the achievement engine
- Keep it extensible but practical
- Avoid unrelated cleanup
- Preserve repository conventions

Expected outcome:
- achievements have a real foundation in the codebase
- core flows are better tested and more stable
- the repository is in a good state for the next product iteration

At the end provide:
A. Files changed
B. Achievement model/logic added
C. Tests and seed updates
D. Remaining known limitations