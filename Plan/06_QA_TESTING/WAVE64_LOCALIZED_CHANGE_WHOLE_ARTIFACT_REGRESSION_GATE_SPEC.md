# Wave64 Localized Change Whole-Artifact Regression Gate

## Scope

- Tracker: `TRK-W64-034`
- Item: `ITEM-W64-034`
- Gate id: `localized_change_whole_artifact_regression`
- Evaluator: `Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_localized_change_whole_artifact_regression.py`

This gate is an aggregation/compositor-only strict evaluator. It does not perform image/video/audio generation or re-analysis. It only consumes bound upstream evidence and recomputes pass/reject/block outcomes.

## Inputs

The request must bind exact baseline/candidate evidence for:

- Row033 baseline multimodal scorecard report
- Row033 candidate multimodal scorecard report
- Row032 global audio review report
- Wave33 preview QA report
- Baseline and candidate artifact manifests
- Failure record and retest record
- Whole-artifact delta report
- Whole-artifact final visual/audio review report
- Runtime proof record
- Baseline and candidate primary media
- Structured localized change manifest

Every bound file is verified by canonical-root containment, symlink-safe resolution, exact path/SHA256/bytes validation, strict duplicate-key/non-finite JSON rejection, and unknown-key rejection. A contained but missing or integrity-mismatched top-level binding produces a preserved blocker and exit `2`; an invalid or escaping request path remains exit `1`.

Wave33 evidence must contain every field in the canonical `wave33_preview_qa_report` contract plus supplemental candidate artifact/run/scene/shot/take identity. Its artifact object must exactly bind the candidate primary media and candidate artifact manifest used by this gate.

The gate is fail-closed for malformed nested custom records in bound evidence: these become `blocked` with exit `2` and preserved blockers.

## Failure and Retest Protocol

- Failure class must be one of:
  - `environment_infrastructure`
  - `workflow_logic`
  - `artifact_quality`
  - `observability_evidence`
  - `unknown_needs_diagnosis`
- Required before retest:
  - severity
  - suspected cause
  - exact change
  - expected result
  - original failure preservation
  - prior attempt history
- Material change requires both validated target-partition before/after differences and distinct verified baseline/candidate primary-media SHA-256 values.
- Attempt history is caller-supplied evidence but caller-computed retry fields are ignored for the decision.
- The evaluator derives `attempt_number` and `similar_failure_count` from attempt history and exact change-summary-hash comparison; a conflicting `similar_to_current` declaration is itself a blocker and cannot reduce the derived count.
- Third similar failed attempt requires deeper-diagnosis evidence and a distinct new-direction hash.
- Fourth similar failed attempt is blocked pending redesign.

## Whole-Artifact Coverage Requirements

- Canonical partitions use explicit visual and audio domains plus typed visual/audio partitions.
- Visual partitions must exactly cover frame domain `[0..total_frames-1]` with no overlaps or gaps.
- Audio partitions must exactly cover sample domain `[0..total_samples-1]` with no overlaps or gaps.
- Audio partition sample/time conversion must be exact within explicit tolerance using declared sample rate.
- Partition IDs must be unique, valid, disjoint, and complete.
- Target and non-target partition sets must be disjoint and their union must exactly equal the canonical full-domain set.
- Delta/review/manifests/change-manifest must all bind exactly the same canonical partition sets and target subsets.
- Any uncovered partition or set mismatch is blocked.
- Target-only review is blocked.
- Any newly introduced unrelated defect is rejected.
- Visual/no-audio changes must provide exact baseline/candidate mix WAV SHA256 and byte-count identity in Row032.
- Audio-expected changes must include target and non-target whole-audio proof.
- Candidate masks cannot be consumed as truth in this gate and mask authority cannot be promoted here.

## Recomputed Gate Set

The evaluator recomputes and ignores caller gate claims:

1. `before_after_delta`
2. `target_region_pass`
3. `global_region_pass`
4. `unrelated_defect_scan`
5. `audio_visual_regression_scan`
6. `reject_on_new_defect`

`unrelated_defect_scan` records whether delta and final review completed the same unrelated-region finding set. `reject_on_new_defect` separately records whether that completed scan found no new or persisting unrelated regression.

## Authority Rules

- Canonical registry arrays for production and fixture exact authority objects remain empty by default.
- Exact authority matching uses explicit objects (`authority_id` + `bundle_id`) and prevents duplicate-pair and cross-product acceptance.
- Production requires one exact production authority object binding every decision-affecting identity and exact binding, including change kind, audio expectation, attempt number, attempt-history digest, partition digest, producer/reviewer identities, and all input bindings.
- Fixture authority is allowed only for technical reachability as non-production.
- Reviewer role must be exactly `Codex Desktop autonomous QA`.
- Producer and reviewer identities must be independent and must differ.
- No synthetic upstream evidence may be accepted as production.

## Decision and Exit Codes

- `0`: pass, or fixture-only technical pass (`non-production`)
- `2`: evaluated `rejected` or `blocked`
- `1`: invalid request or operational failure

Blocking semantics:

- Missing/untrusted prerequisites -> `blocked`
- Protocol retry illegality -> `blocked`
- Attempt limit exceeded -> `blocked`
- Contained missing/hash-mismatched/size-mismatched bindings -> `blocked`
- Present target/global/new-defect regressions -> `rejected`
- Invalid request schema, escaping paths, or operational failure -> exit `1` and no output file
- Rejected reports must still preserve real blockers and must remain coupled to `exit_code=2`.

## Report Truth Surface

- Report schema includes explicit policy-state booleans:
  - `mask_authority_promoted=false`
  - `candidate_masks_used_as_truth=false`
  - `wave70_hard_gate_claimed=false`
  - `wave71_activated=false`
- Report lineage includes producer and reviewer identities with reviewer role exactly `Codex Desktop autonomous QA`.
- Decision and exit coupling is schema-enforced and blockers are preserved for blocked/rejected outcomes.
