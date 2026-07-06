# QA and Rerun Decision Loop

run pass → collect evidence → score QA → if pass continue → if fail classify → if retryable and attempts remain generate rerun patch set → otherwise stop/fail manifest.

Reruns must be bounded and documented.
