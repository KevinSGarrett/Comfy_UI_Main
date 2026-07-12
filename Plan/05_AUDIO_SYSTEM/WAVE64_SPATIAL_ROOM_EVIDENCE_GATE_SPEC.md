# Wave64 Spatial Room Evidence Gate Specification

## Scope

TRK-W64-029 defines a strict offline evaluator for spatial audio and room acoustics evidence.
The evaluator consumes a hash-bound evidence bundle and emits a fail-closed report.

## Canonical Execution

- Script: `Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_spatial_room_evidence.py`
- Input schema: `Plan/08_SCHEMAS/wave64_spatial_room_evidence_bundle.schema.json`
- Output schema: `Plan/08_SCHEMAS/wave64_spatial_room_evaluator_report.schema.json`
- Gate rules registry: `Plan/10_REGISTRIES/wave64_spatial_room_gate_rules.json`
- Canonical root is pinned from `__file__`; caller root overrides are rejected.

## Evidence Requirements

The evidence bundle must bind:

- `run_id`, `scene_id`, `shot_id`, `take_id`, and `is_synthetic`
- `evidence_origin` (`technical_capture`, `hand_authored_relabel`, `synthetic_fixture`)
- listener, camera, and source 3D coordinates plus camera orientation (`right_unit_vector` + `forward_unit_vector`)
- Wave31 spatial-mix and room-acoustics manifests by exact path and SHA-256
- real root-contained PCM WAV artifacts (`dry_dialogue`, `spatial_dialogue`, `ambience_bed`, `final_mix`)
- ambience continuity bindings for adjacent segments (distinct path + SHA) with optional allowlisted hard-cut contract
- optional playback proof, runtime proof, and production authority bundle

The evaluator rejects:

- unknown keys
- root escape paths
- non-finite numeric JSON values
- malformed/non-PCM WAV payloads
- hash/byte mismatches
- input/output path collisions

## Wave64 Gates

1. `spatial_position_check`
2. `room_reverb_check`
3. `ambience_continuity`
4. `mix_balance_review`
5. `spatial_audio_playback_review`
6. `production_runtime_proof`
7. `production_spatial_room_authority`
8. `overall_pass`

All gates are fail-closed (`PASS`/`FAIL`/`BLOCKED`).

## Measurements

The evaluator computes audio metrics from decoded PCM samples using the Python standard library:

- channel RMS/peak/clipping ratios
- duration/sample properties
- observed stereo pan
- dry-to-spatial attenuation ratio
- ambience continuity drift between adjacent segments
- dialogue-to-ambience balance in dB
- final-mix reconstruction residual against `spatial_dialogue + ambience_bed` when formats align
- final-mix energy ratio against registry-controlled bounds
- reverb tail and RT60 estimates from measured envelopes

No caller-provided score booleans are trusted as truth.

## Registry and Threshold Rules

- Registry floors/ceilings are mandatory.
- Bundle threshold overrides may only tighten registry constraints.
- Reverb-tail error override is clamped by the canonical room-rule ceiling.
- Final mix must be content-distinct from every stem and satisfy registry reconstruction/energy constraints.
- Reconstruction requires exact frame-count, sample-rate, channel-count, and sample-width parity with the dialogue and ambience stems; it may never be silently skipped inside a looser duration tolerance.
- Unknown room/material/reverb combinations fail closed.
- Existing Wave31 schemas and registries are loaded from canonical paths only.

## Proof and Production Authority

- Playback and runtime proofs are separate hash-bound JSON artifacts.
- Proofs must include engine/model/version/hash, run identity, measured artifact hashes, review results, and must not self-authorize.
- Playback/runtime proofs must match a canonical producer allowlist record (proof kind + engine + model + version + model SHA + authority ID + synthetic-only policy); unapproved producers block the gate.
- Hard-cut contracts are approved only via registry approver IDs/reasons/authorities; synthetic-only approvers cannot authorize non-synthetic bundles.
- Production authority requires all upstream gates to pass and a non-synthetic technical-capture bundle.
- `approved_bundle_allowlist` is fixed and currently empty.
- Synthetic and hand-authored relabel fixtures must never achieve `overall_pass`.

## Exit Codes

- `0`: overall pass
- `2`: evaluated successfully but did not pass all gates
- `1`: invalid input, schema, hash/path, or evaluator error
