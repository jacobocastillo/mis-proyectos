I need a focused recon/debug investigation for a regression in the validation flow.

Current issue:

* The UI shows: "No se pudo contactar el servicio de validación. Verifica tu conexión e inténtalo de nuevo."
* It still does not work.
* Important: this used to work before, so treat this as a regression, not as a brand-new feature problem.

Your task:
Do a deep recon to find why the validation service is no longer reachable from the app, and explain exactly where the failure is happening.

Scope:

* Do not implement fixes yet.
* First identify the real root cause(s), with evidence.
* Be precise about whether the failure is in frontend, backend, environment config, provider client, network/DNS, deployment config, or error mapping.

What I want you to investigate:

1. Frontend flow

* Find the exact page/component where the validation request starts.
* Trace the call chain from UI action → service layer → API client → backend request.
* Identify the exact request URL, method, payload, headers, timeout behavior, and error handling.
* Verify whether the frontend is calling the correct backend route.
* Check whether runtime config/base URL changed and is now wrong.
* Check whether the frontend is classifying all failures as "could not contact validation service" even when the backend is actually returning a real error.

2. Backend route and service flow

* Find the backend endpoint receiving this validation request.
* Trace the full backend path from route → service → provider client.
* Verify whether the route is being hit at all.
* Check for request validation issues, payload mismatch, auth issues, missing headers, or route mismatches.
* Confirm whether the backend returns structured errors or if something is crashing before that.

3. Environment and secrets

* Check whether required environment variables for the validation/OpenAI provider are present and correctly loaded.
* Verify if anything changed in env loading, config initialization, or secret validation.
* Check whether the API key, model name, base URL, or provider configuration is missing, invalid, or different from when it used to work.
* Identify whether local, dev, and production environments resolve config differently.

4. Provider connectivity

* Check whether the backend can actually reach the external validation provider.
* Investigate DNS issues, outbound network issues, TLS issues, timeouts, blocked egress, or bad base URLs.
* Determine whether the failure is:

  * provider init failure
  * env loading issue
  * wrong route
  * payload mismatch
  * frontend error mapping issue
  * model/API usage issue
  * backend egress/DNS/network issue
  * something else

5. Regression analysis

* Since this worked before, identify what changed.
* Search recent code/config changes related to:

  * validation page
  * validation service
  * API client
  * backend validation routes
  * provider/OpenAI service
  * config/env loading
* Compare current code against the last known working flow if possible.
* Highlight the most likely regression point.

6. Evidence I want
   For every finding, include:

* exact file(s)
* function(s)
* line references if possible
* whether it is confirmed or only suspected
* why it explains the current user-facing error

7. Output format
   Return the result in this exact structure:

A. Executive summary

* What is the most likely root cause?
* Is the frontend actually failing to contact the backend, or is the backend failing to contact the provider?
* Is this a regression? If yes, where is the likely regression point?

B. End-to-end request trace

* UI trigger
* frontend service
* API client
* backend route
* backend service/provider
* external call
* final failure point

C. Classification
Choose one primary classification and explain why:

* provider init failure
* env loading issue
* wrong route
* payload mismatch
* frontend error mapping issue
* model/API usage issue
* backend egress/DNS connectivity issue
* something else

D. Confirmed findings

* List only findings with evidence

E. Likely findings

* List strong suspects that still need confirmation

F. What changed

* Most likely regression-causing change(s)

G. Next fix plan

* Minimal fix
* Safer fix
* Recommended validation steps after the fix

Important instructions:

* Do not give a generic answer.
* Do not stop at the first plausible explanation.
* Trace the flow end to end.
* If the frontend message is masking a backend/provider error, call that out clearly.
* Prioritize root cause over cosmetic improvements.
* We need recon only for now, not implementation.
* Assume the issue still reproduces right now.
