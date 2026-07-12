# Wave64 AV Sync Certification Gate Spec

## Objective

`TRK-W64-030` defines a strict offline AV-sync certification evaluator. It validates real media content, lineage, and authority proofs before any production approval can be considered.

Evaluator requirements:

- operate from a canonical repository root pinned from `__file__`
- reject caller root override, root escape, unknown keys, and non-finite JSON tokens
- reject malformed artifacts, hash/byte mismatches, and output collisions
- decode actual media with PyAV (not metadata-only checks)
- fail closed for all gate decisions

## Evidence Inputs

The Wave64 measurement packet binds:

- run identity: `run_id`, `scene_id`, `shot_id`, `take_id`
- synthetic labeling: `is_synthetic`, `evidence_origin`
- source video container artifact (hash + byte-bound)
- source PCM WAV mix artifact (hash + byte-bound)
- final mux artifact (hash + byte-bound)
- canonical Wave30 event manifest binding
- canonical Wave30 mix manifest binding
- observed anchor measurement proof binding
- optional playback proof binding
- optional runtime proof binding
- optional production certification bundle binding

## Mandatory Decode/Lineage Validation

The evaluator decodes source video and mux video/audio streams with PyAV and records:

- stream map/count/type
- codec identity
- stream and frame timing bases
- dimensions and frame rate
- sample rate/channels/layout
- first and last decoded timestamps
- decoded durations
- packet/frame timestamp monotonicity

Lineage is bound through canonical decoded evidence:

- decoded source video frame sequence hash
- decoded mux video frame sequence hash
- decoded source WAV PCM hash
- decoded mux audio sample hash

Video sequence hashes use canonical full-color RGB24 rows, including chroma/color information and excluding decoder stride padding. Audio hashes use canonical valid PCM sample bytes and exclude plane padding.

The mux lineage gate must detect and fail on swapped/missing/extra/duplicated/truncated/unrelated stream content.

## Sync Metrics

The evaluator computes from decoded timestamps:

- AV start offset (`audio_start - video_start`)
- endpoint delta (`audio_end - video_end`)
- cumulative endpoint drift (`endpoint_delta - start_offset`)

Registry thresholds are mandatory ceilings and cannot be loosened by request input.

Video endpoints use the final decoded frame duration when available, then the last observed cadence, with average frame rate only as a final fallback. Any missing or non-monotonic decoded timestamps fail both the start-offset and drift decisions that consume them.

## Anchor/Event Cross-Checks

Observed anchor proof is validated against Wave30 event authority:

- event identity (`audio_event_id`, `source_event_id`)
- owner/subject binding parity
- sync class parity
- expected frame range parity
- observed frame-in-window
- observed frame/time coherence against frame rate
- duplicate/missing/extra anchor detection
- observed frame/time bounds against the decoded mux frame count and endpoint
- Wave30 `av_sync_evidence` parity against the decoded mux frame rate, measured start offset, and sync-scoped event envelope

Anchor producers must match exact registry allowlist identity:

- `engine`
- `model`
- `model_version`
- `model_sha256`
- `authority_id`

Only synthetic-only anchor producers exist initially. Non-synthetic relabel input cannot inherit synthetic-only producers.

## Independent Proof Gates

Playback and runtime proofs are independent inputs and must bind exact hashes for:

- source video artifact
- source audio mix artifact
- final mux artifact
- anchor proof artifact

Each proof must match registry-approved producer identity and synthetic-only policy.

When cross-role independence is enabled, one `authority_id` cannot appear in more than one measurement, playback, runtime, or production-certification allowlist. Caller-declared `self_authorized: false` is necessary but is not sufficient to establish independence.

## Gate Set (Fail-Closed)

Wave64 evaluator emits these gates:

1. `sync_offset_threshold`
2. `drift_check`
3. `mux_manifest`
4. `event_owner_alignment`
5. `av_review_record`
6. `production_runtime_proof`
7. `production_av_sync_authority`
8. `overall_pass`

Gate statuses are terminal-only: `PASS`, `FAIL`, `BLOCKED`.

## Production Authority Rules

Production authority:

- inherits every upstream `FAIL`/`BLOCKED` status
- requires non-synthetic technical capture evidence
- requires an exact production certification bundle hash match in fixed allowlist
- does not trust caller-declared pass booleans

The production allowlist remains empty by policy, so production authority must remain blocked.

## Safety/Determinism Requirements

- atomic write for report output
- transactional preservation when evaluation fails
- no output write when input is invalid
- parser version reported and enforced against registry allowlist

## Exit Codes

- `0`: overall pass (not expected under current empty production allowlist)
- `2`: evaluation completed with fail/blocked outcome
- `1`: invalid input, malformed artifacts, policy violations, or evaluator error
