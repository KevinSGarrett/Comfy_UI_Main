# Wave64 Global Audio Review Gate (Row032)

## Purpose

Row032 is a fail-closed global audio hardening gate. It validates baseline/candidate lineage, enforces localized-change boundaries, and blocks any non-target regression.

## Request Contract

Required request payload fields:

- `request_version` is exact const `1`.
- `review_run_id`, `baseline_run_id`, and `candidate_run_id` are required and independent.
- Baseline/candidate bindings are required for:
  - mix WAV
  - row031 strict report
  - Wave30 event manifest
  - Wave30 mix manifest
  - Wave30 QA report
- `localized_change_declaration` requires:
  - `change_kind` in `audio_localized | visual_localized`
  - `audio_change_expected` boolean
  - target/non-target IDs
  - caller windows

`audio_localized` requires `audio_change_expected=true` and non-empty target/windows.
`visual_localized` supports:

- `audio_change_expected=false` with empty target/windows and byte-identical baseline/candidate WAV.
- `audio_change_expected=true` with non-empty target/windows, per-target RMS delta enforcement, and candidate row031 `row030_av_sync_report` binding present.

For the visual-with-audio path, the bound row030 report must validate against the canonical row030 schema, match the candidate run/synthetic lineage and source-audio binding, and have every technical sync gate PASS.

## Core Lineage/Metadata Rules

Row032 validates all lineage before computing gates and records failures in `review_lineage_blockers`:

- row031 baseline/candidate schema validity, required technical gates PASS, and binding exactness.
- Wave30 event->mix->QA binding chain exactness for baseline and candidate.
- Wave30 required technical hard gates (9) must be PASS and `proof_verification.artifact_bindings_verified=true`.
- Wave30 `mixdown_artifact` path/hash/bytes must exactly match bound WAV.
- Wave30 `mix_technical` sample rate/channels/sample width/frame count must match decoded WAV.
- Event manifest IDs must exactly equal mix `mix_event_metadata` IDs.
- Wave30 run/synthetic/scene consistency.
- Mixdown WAV identity and Wave30 metadata consistency.
- Recomputed Wave30 production eligibility (do not trust `production_eligible` alone).

Any lineage contradiction is a technical failure path.

## Localized Scope Hardening

- Canonical non-target IDs are recomputed from baseline/candidate event unions minus targets.
- Missing/extra caller non-target IDs are rejected.
- Non-target event records and non-target `mix_event_metadata` must be byte-equivalent between baseline and candidate.
- Derived target windows are recomputed from baseline/candidate target event timing union plus bounded padding.
- Caller windows must exactly equal derived windows.
- Same-layer foreground non-target overlap with any target-derived window/event is blocked.
- Exact-preserved overlapping non-target events are allowed when non-target `sync_class` is `ambient_free` or `music_scene_phase`, or when layer differs.

## Audio Defect Scans (Per Channel)

Row032 runs whole-file scans and reports independent maxima across channels:

- clipping ratio and clipping runs (max across channels)
- click/discontinuity peaks and click ratio (max across channels)
- loudness jump (max across channels)
- silence/dropout in active windows
- outside-target RMS/peak regression
- per-target RMS delta threshold checks

Single-channel clipping/dropout regression checks are required.

Frame-count mismatch is not an invalid-contract error.
Row032 compares over available frames and emits evaluated-duration FAIL/BLOCKED path when duration delta exceeds tolerance.

Incompatible technical format (sample rate/channels/sample width mismatch) remains invalid contract (`exit 1`).

## Promotion Authority Contract

The initial production baseline and bundle authority arrays are empty, so current production promotion remains BLOCKED. Promotion may PASS only when:

- non-synthetic technical-capture lineage
- all technical gates PASS
- both row031 baseline/candidate `promotion_decision` and `overall_pass` are PASS
- baseline and candidate recomputed Wave30 production eligibility are PASS
- production bundle exists and content matches baseline/candidate hashes
- production authority registry checks pass with exact full-record matching:
  - `approved_production_baselines`
  - `approved_production_bundles`
- baseline authority records include a non-empty authority ID, `baseline_run_id`, exact baseline hashes, `synthetic_only=false`, and a unique authority ID.
- bundle authority records include non-empty IDs, all run IDs (`baseline_run_id`, `candidate_run_id`, `review_run_id`), exact 64-char hashes, `synthetic_only=false`, and a unique bundle ID.
- production bundle payload includes schema/version/bundle_id/run IDs, `synthetic_only=false`, and exact hashes.
- `baseline_authority_id != bundle_authority_id`.

No hash-only authority records are allowed.

## Report Contract

- `report_version` is exact const `1`.
- Report includes production authority evidence booleans.
- Report includes `review_lineage_blockers`.
- `overall_pass` may not be PASS while blockers exist.
- Exit codes:
  - `0` only when no blockers and overall PASS
  - `2` when evaluation completed with FAIL/BLOCKED
  - `1` for invalid input/contract violations
