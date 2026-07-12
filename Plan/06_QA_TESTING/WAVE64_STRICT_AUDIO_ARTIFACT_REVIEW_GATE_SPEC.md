# Wave64 Strict Audio Artifact Review Gate (Row031)

## Purpose

Define a fail-closed, hash-bound strict evaluator that reviews Wave64 audio artifacts and upstream Wave30 lineage before any promotion decision.

## Required Inputs

The evaluator request must bind each artifact with absolute path, SHA-256, and byte length:

- `mix_wav_binding` (required, PCM WAV mix artifact under canonical root)
- `wave30_event_manifest_binding` (required)
- `wave30_mix_manifest_binding` (required)
- `wave30_qa_report_binding` (required)
- `prompt_reference_binding` (required)
- `prompt_alignment_proof_binding` (required)
- `playback_proof_binding` (optional, but playback gate cannot PASS without it)
- `row030_av_sync_report_binding` (conditionally required when prompt reference requires video pairing)
- `production_review_bundle_binding` (optional, required for promotion PASS)

## Core Safety and Parsing Rules

- Canonical project root is pinned from evaluator `__file__`.
- All bound paths must resolve under canonical project root; root escape is invalid input.
- JSON parsing is strict: reject duplicate keys, unknown keys, and non-finite values (`NaN`, `Infinity`, `-Infinity`).
- Hash and byte mismatch on any binding is invalid input.
- Output collision is invalid input (reject existing output path).
- Output writes are transactional and atomic.

## Upstream Lineage Validation

Evaluator must schema-validate:

- Wave30 event manifest against `wave30_audio_event_manifest.schema.json`
- Wave30 mix manifest against `wave30_audio_mix_manifest.schema.json`
- Wave30 QA report against `wave30_audio_qa_report.schema.json`

Evaluator must enforce exact lineage:

- request `run_id` and `is_synthetic` exactly match upstream report/manifest lineage
- mix manifest must bind exactly the same event manifest path and hash as request
- Wave30 QA report must bind exactly the same event/mix artifacts as request
- required upstream technical gates (registry controlled, currently nine metadata gates) must all be PASS
- upstream production eligibility must be independently recomputed from the upstream report contract (do not trust a single caller-supplied boolean flag)

## Prompt Reference and Prompt Alignment

Prompt reference contract:

- kind enum: `speech`, `music`, `ambience`, `mixed`
- expected text required for `speech` and `mixed`
- expected attribute name/value pairs required for all kinds
- `video_pairing_required` boolean required

Prompt alignment proof contract:

- proof must carry full immutable producer identity:
  - `producer_id`
  - `engine`
  - `model`
  - `model_version`
  - `model_sha256`
  - `authority_id`
  - `synthetic_only`
- evaluator must never trust bare `producer_id`; full identity must exactly match an allowlist identity record with `proof_kind=prompt_alignment`
- `self_authorized` must be false
- proof must bind exact audio hash and prompt reference hash
- evaluator computes normalized WER for `speech` and `mixed`
- expected attributes require exact coverage and exact value matches
- request/proof synthetic parity and identity policy must be enforced:
  - synthetic-only producer (`synthetic_only=true`) may pass technical gate only when `request.is_synthetic=true`, `proof.is_synthetic=true`, and `production_evidence=false`
  - synthetic-only producer must BLOCK for non-synthetic technical capture and for `hand_authored_relabel`
  - future production-capable producer (`synthetic_only=false`) must require `request.is_synthetic=false`, `proof.is_synthetic=false`, and `production_evidence=true`
- caller-supplied pass booleans are ignored

## Playback Review Gate

Playback proof requirements:

- independent allowlisted playback authority with exact immutable identity record (`proof_kind=playback_review`)
- never trust bare `producer_id`; require exact identity match across all producer fields
- enforce synthetic parity and `synthetic_only` policy exactly as prompt alignment
- hash-bound audio reference
- `self_authorized` must be false
- section coverage: `beginning`, `middle`, `end`, `loud`, `quiet`, `transitions`
- 0-5 scores for required protocol categories
- defect list with code and severity

Gate behavior:

- missing/unapproved/identity-policy-violating proof: BLOCKED
- malformed or contradictory proof: FAIL
- blocking defect present: BLOCKED

## Sync Evidence Gate

- If prompt reference says no video pairing: PASS with evaluator-derived not-applicable reason.
- If pairing required: require row030 AV-sync report binding and schema-validate against `wave64_av_sync_certification_report.schema.json`.
- Require row030 parity with request for `run_id`, `is_synthetic`, and `evidence_origin`.
- Require row030 `artifact_bindings.source_audio_mix_artifact` path/SHA-256/bytes to exactly match request `mix_wav_binding`.
- If pairing required: require PASS for all row030 technical sync gates:
  - `sync_offset_threshold`
  - `drift_check`
  - `mux_manifest`
  - `event_owner_alignment`
  - `av_review_record`
- Row030 production-only gates (`production_runtime_proof`, `production_av_sync_authority`, `overall_pass`) may remain BLOCKED without failing this technical sync gate.

## Promotion Decision Gate

Promotion gate PASS only when all are true:

- capture mode is `technical_capture`
- non-synthetic request and non-synthetic independent producers
- all prior gates PASS
- no blocking playback defects
- upstream Wave30 production eligibility is independently recomputed as true only when all 11 schema-required hard gates are `pass`, proof verification booleans are all true, computed flags (`all_hard_gates_passed`, `production_eligible`) are true, promotion decision is `promote`, and lineage/run identity remains exact
- production review bundle binding exists and exact hash appears in immutable allowlist

Mandatory blocks:

- synthetic requests always BLOCKED for promotion
- `hand_authored_relabel` capture mode always BLOCKED for promotion
- initial production review bundle allowlist is intentionally empty

## Authority Registry Requirements

- Registry must use exact-record allowlists for prompt and playback producer identities.
- Each identity record keys must be exactly:
  - `proof_kind`, `producer_id`, `engine`, `model`, `model_version`, `model_sha256`, `authority_id`, `synthetic_only`
- Registry must reject duplicate producer identities and reject cross-role collisions.
- `authority_id` values must be disjoint across prompt, playback, and production roles.
- `production_review_authorities` may be an empty exact-record array initially.

## Report Contract

Report gates must be exactly:

- `audio_metadata_check`
- `playback_review`
- `prompt_alignment`
- `sync_evidence`
- `promotion_decision`
- `overall_pass`

Each gate is one of `PASS`, `FAIL`, or `BLOCKED`.

Report must include:

- blockers
- artifact bindings
- computed metrics (including WER when applicable)
- producer identities
- final decision summary

## Exit Codes

- `0`: evaluation completed with overall PASS
- `2`: evaluation completed with overall FAIL or BLOCKED
- `1`: invalid input or strict contract violation
