You are implementing Phase B in the StreakUP repository.

Goal:
Add real support for multiple validation flows so a habit can be completed through photo, text, or timer evidence.

Scope for this phase:
- complete the check-in/validation contract
- support evidence submission by validation type
- store validation attempts consistently
- wire frontend and backend together for photo/text/timer inputs

Tasks:
1. Inspect the current check-in and validation flow in backend and frontend.
2. Extend or refactor the submission flow so a validation attempt can carry:
   - validation_type
   - text evidence
   - photo/media evidence or reference
   - duration/time evidence
3. Implement the backend handling needed to accept and store those attempts consistently.
4. Implement the frontend input flow so the user sees the correct input mode based on validation_type.
5. Reuse the current photo flow where possible, and add clean support for text and timer.

Important:
- Do NOT implement achievements yet
- Do NOT do broad cleanup
- Keep changes incremental and compatible with repository patterns
- If there is already partial support for photo validation, preserve and adapt it instead of rewriting unnecessarily

Expected outcome:
- habits can submit photo, text, or timer evidence
- validation attempts have a consistent structure
- frontend routes users into the correct validation UI

At the end provide:
A. Files changed
B. Validation payload shape
C. What works for photo/text/timer
D. Remaining work for strict streak/XP logic