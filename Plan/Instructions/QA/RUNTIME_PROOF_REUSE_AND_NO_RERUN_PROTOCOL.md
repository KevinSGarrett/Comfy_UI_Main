# Runtime Proof Reuse And No-Rerun Protocol

Updated: 2026-07-09T01:18:29-05:00

Purpose: prevent autonomous sessions from repeating completed ComfyUI local or AWS runtime work when valid proof already exists.

## Rule

Before running a local ComfyUI smoke, AWS/EC2 smoke, target-runtime proof, hard gate, package smoke, or lane certification step, inspect the active lane queue, active lane manifest, hydration top blocks, and existing QA evidence for the same lane/request/input/model route.

If equivalent evidence already exists and the workflow/request/control input/model route/artifact integrity has not changed, reuse the existing proof and move to the next unproven or changed project task.

## Completed Baseline: Canny Lane

`sdxl_realvisxl_controlnet_canny_lane` has completed baseline proof and must not be rerun as default work:

- W68 EC2 Canny v4 target-runtime smoke: static proof, input install, bounded generation, S3 sync, pullback/hash verification, technical QA, and visual QA passed with notes.
- W69/W72 local Canny robustness and follow-up evidence exist.
- 2026-07-09 local package smoke passed with two returned outputs: generated image plus diagnostic control map.

Remaining Canny work is not baseline proof. It is limited to final certification, explicitly selected changed-variant proof, or repair after a real workflow/request/input/model/artifact change.

## Allowed Rerun Reasons

A rerun is allowed only when one of these is true:

- The workflow JSON, smoke request, prompt profile, control/input image, model route, or runtime package changed.
- Existing evidence is missing, corrupt, hash-mismatched, or references the wrong lane.
- The user explicitly selects final certification or a changed target-runtime variant.
- A live runtime dependency changed and the new task requires fresh proof.

## Disallowed Rerun Reasons

Do not rerun because:

- Hydration text is stale or ambiguous.
- A row says “pending” while proof evidence already shows a pass-with-notes baseline.
- A bookkeeping/control row is next in sequence.
- AWS auth is available and idle.
- The session needs “something to do.”

## Required Session Behavior

When proof exists, record proof reuse or advance to a new concrete task. Do not use Git, Jira, Wave64/Wave65 coverage, generic registry checks, hydration churn, or repeated AWS/Canny smoke as substitute progress.

