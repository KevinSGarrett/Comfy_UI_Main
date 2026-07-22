# Wave64 InternVL3.5-241B Independent-Juror Admission

This instruction governs `W64-AQA-009` on the sole current production pod. It
does not grant runtime or juror authority.

## Current static decision

The candidate route is the pinned community `i1-IQ4_XS` three-part GGUF plus
the separate pinned Q8 vision projector. Header-only range audits identify the
model architecture as `qwen3moe` and the projector as `internvl`. Pinned
llama.cpp source contains both identifiers, but its current documentation names
InternVL 2.5 and InternVL 3, not InternVL 3.5, and describes multimodal support
as under heavy development. Treat this as a static identifier match only.

The exact candidate is 131,260,400,544 bytes (122.245774 GiB). Admission
requires enough exact live free quota for the candidate and a 50 GiB post-load
storage reserve: at least 172.245775 GiB before download. The latest
conservative project reserve is 53.335322 GiB and is not a live quota reading.
No download is admitted.

## Required order

1. Read the shared coordinator. Never clear or override a foreign recovery or
   lease state.
2. Prove exact tenant-visible free quota on network volume `o9qv2ld91c`.
   Shared-backend `df` output is not sufficient.
3. Require at least 172.245775 GiB free before admitting any candidate byte.
4. Build llama.cpp revision
   `e8e6c7af2456fd50bb62f7a2bbd642e6fb14ae77` in an immutable prefix and
   record compiler, flags, binary hashes, and self-tests.
5. Download only the four pinned files under an exact coordinator lease. Verify
   every part's size and SHA-256 before concatenation.
6. Concatenate the three model parts in provider order into staging; verify the
   resulting byte count and full-file digest before any open.
7. Run metadata-open and projector-open canaries without inference. Fail closed
   on architecture, tensor, tokenizer, projector, or dimension mismatch.
8. Under a separate lease, run one retained-rights single-image smoke with
   capacity telemetry, deterministic settings, unload, process exit, and
   cleanup evidence.
9. Run prospective calibration, quality, refusal, repeatability, latency, cost,
   and failure-injection campaigns. Independent-juror authority remains false
   until an exact-scope certificate passes every gate.

## Forbidden shortcuts

- Do not download based on the 1,000 GB control-plane volume size or shared MFS
  `df`; neither proves current tenant free quota.
- Do not infer InternVL3.5 support from family-name similarity.
- Do not load raw continuation parts or concatenate before part hash replay.
- Do not use the provisional 8B package as the independent juror.
- Do not claim runtime, visual quality, golden-mask, arbitration, promotion, or
  product approval from header or source-code evidence.

The canonical static receipt is
`Plan/Tracker/Evidence/W64_AQA_INTERNVL35_241B_GGUF_STATIC_ADMISSION_20260722T130625Z.json`.
