# Wave64 Hyperreal Video, Audio/AV, and Operator Application QA Protocol

## Test pyramid

- Many schema, semantic, state-machine, policy, and ranking unit/property tests.
- Contract tests for controller, adapters, commands, queries, and projections.
- Integration tests with fake and local ComfyUI/audio workers.
- Fault-injection tests around every external side effect.
- Media benchmark and calibrated critic tests.
- Component, visual-regression, accessibility, and usability tests for the app.
- A small number of end-to-end release tests.

## Mandatory negative tests

- planned, suspended, revoked, expired, or hash-mismatched bundle selection;
- non-contiguous frames, duplicate tracks, identity owner swaps, contact
  asymmetry, clock disagreement, and unresolved continuity conflicts;
- repair outside the failed span, missing handles/protected masks, mutation of
  an accepted parent, and unchanged-hypothesis retry;
- audio event without ownership/clock/source evidence;
- dry voice promotion without identity/alignment evidence;
- spatial claim without position/acoustic evidence;
- frame/sample loss, non-monotonic PTS, excess time stretch, and hidden drift;
- UI dead controls, unauthorized commands, stale aggregate versions, duplicate
  idempotency keys, direct ComfyUI mutation, and projection-as-promotion;
- WebSocket loss, controller/worker restart, lease loss, unknown submission,
  disk full, artifact corruption, queue cancellation, and projection lag.

## Media qualification

Every metric records revision, threshold, direction, value, confidence bounds,
calibration, and evidence. Benchmarks include held-out slices and exact source
context. Report false-accept and false-reject rates. Candidate selection logs
assignment probability so learning does not treat biased history as a random
benchmark.

## Release rule

No aggregate average can hide a blocking failure. Promotion requires current
exact-bundle/runtime/workflow certificates, target/protected/whole-artifact QA,
continuity and clock consistency, qualified calibrated autonomous critics, and
the signed deterministic autonomous policy decision. Blind human/listening or
operator approval is optional `independent_perceptual_calibration` evidence or a
separately recorded explicit user override; its absence cannot block or revoke
`core_autonomous_runtime`. Static planning tests never satisfy runtime release.
