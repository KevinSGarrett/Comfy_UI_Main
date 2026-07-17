# Wave30 Model OS Autonomous Selection Readiness Audit

Audit date: 2026-07-16 America/Chicago

## Verdict

Wave30 is a high-value catalog, taxonomy, review-queue, and migration-planning
package. It is not an empirically qualified model library and its selector
cannot be used directly as production routing authority.

The intended model binaries have not yet been completely downloaded. The
7,282-row staging import, pilot, bundle-solver runtime, benchmark runner, and
downstream autonomous selector integration are therefore deferred until a
complete-download declaration, exact scope manifest, deterministic inventory
verification, and main-task activation acknowledgement are recorded. The
metadata archive's `model_binary_count` of zero cannot satisfy that gate.

## Archive integrity

The five cumulative parts are a raw split of one ordinary single-disk ZIP, not
five independent volumes. Parts one through four are 78,643,200 bytes and part
five is 53,320,477 bytes. The logical stream is 367,893,277 bytes with SHA-256
ab87f86c120085834d86b004e886e733a383ac9246f5f0f34087b6627d373351.
The ZIP contains 675 members, has no unsafe or traversal paths, and passed full
decompression and CRC inspection.

The patch archive is 13,243,618 bytes with SHA-256
19add2d6e5bd298ad9cb985876e8c4b684a4d2e048624dcb19d75b4dfe958d26.
Its 39 members are exact members of the cumulative archive. It is a convenient
subset, not an incremental binary delta.

## What the source contains

- 334 CSV, 220 Markdown, 61 JSON, 42 JSONL, and 18 YAML members.
- 2,577,809,722 uncompressed bytes of text and metadata.
- No checkpoint, LoRA, ControlNet, VAE, video model, audio model, or other
  model-weight binary.
- 7,282 artifact records and artifact-card indexes.
- 3,770 model-family card records.
- A detailed Wave26 metadata selector with engine, function, tags, confidence,
  status, and conflict weights.
- Wave12L visual-test assignments and planning statistics.
- Wave29 classification-consistency scoring and QA queues.

## What the source does not prove

- That the model file exists at a local, S3, or target-runtime location.
- That its recorded hash matches a downloaded file.
- That its architecture matches the normalized engine label.
- That it loads in the intended ComfyUI runtime.
- That a LoRA works with an exact checkpoint, VAE, encoder, workflow, prompt,
  weight, target region, or neighboring LoRA.
- That it improves the desired output rather than merely changing it.
- That it preserves identity, anatomy, pose, ownership, protected regions,
  temporal continuity, audio quality, or synchronization.
- That it fits a VRAM, RAM, latency, cache, or cost envelope.
- That an LLM or critic can evaluate it reliably.

## Measured readiness

The final production statistics describe 5,056 caution-first-pass candidates,
2,039 manual-review-required artifacts, and 187 copy-ready records. Wave30 moved
zero files. All 7,282 artifact QA states remain open and all artifacts are
caution-required.

The apparent strong and acceptable classification-accuracy bands are computed
from internal consistency signals such as known engine, known parent function,
tags, folder agreement, review state, operational confidence, and selector
score. Wave29 explicitly states that this is not measured human-labeled
accuracy. It is also not measured generative behavior.

The manual-review registry contains 29,593 rows with no accumulated reviewer
or QA notes. The quarantine registry remains open. Therefore, the archive does
not yet provide the longitudinal observations requested for future intelligent
selection.

## Visual-test gap

Wave12L contains the correct idea: fixed checkpoint, prompt, negative prompt,
seed set, resolution, sampler, baseline, weight sweep, and visual metrics.
Statistics claim 4,978 jobs and 71,800 render rows, but the documentation states
that it generated no images. The referenced full job plan, weight-sweep table,
score sheet, prompt-template assets, and rubric are absent from the archive.
Wave12L must be rebuilt as executable qualification work rather than accepted as
completed QA.

## Source inconsistencies to preserve and reconcile

- The cumulative root MANIFEST identifies the patch pack and reports 39 files
  although the cumulative archive has 675 members.
- The root README retains a Wave 08 title while describing later waves.
- The root manifest self-size differs from the actual member.
- Selector eligibility and production-status summaries contain a 45-row
  disagreement.
- The archive contains intentional duplicated aliases and cumulative/final
  copies that must not become duplicate model identities.

These are ingestion exceptions, not reasons to discard the source.

## Existing project fit

Wave06 through Wave09 already establish engine-family compatibility, Civitai
metadata use, character-aware model constraints, and environment selection.
Wave64 Rows165-172 establish exact per-pass stacks, hard filters, contextual
ranking, first-pass selection, decoded bridges, translation, and pairing
certification. Rows201-204 establish role separation, registry-grounded
retrieval, structured uncertainty, and exact LLM/VLM stack qualification.

The missing layer is the strict source-to-observation-to-certificate-to-report
system defined by Rows221-260.

## Admission decision

Admit Wave30 as discovery_metadata with runtime_selection_allowed=false and
promotion_allowed=false. Preserve every source row and citation. Normalize it
into strict cards and use it to:

- retrieve candidates;
- estimate test relevance;
- discover conflicts and taxonomy gaps;
- prioritize hash acquisition and qualification;
- seed trigger and weight hypotheses;
- compare source claims with measured behavior.

Do not merge Wave30 scores directly into production model utility. Independent
hash, inspection, install, load, A/B, benchmark, report, and scoped certificate
evidence is required first.
