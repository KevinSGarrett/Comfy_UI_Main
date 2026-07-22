# Autonomous Hyperreal Speech and Voice QA Protocol

## Purpose

This protocol governs Wave64 Rows113-148. It evaluates character voice authority, generated speech, nonverbal vocal events, alignment, acoustic rendering, dialogue mixes, and muxed video. It supplements existing Wave64 audio and human playback protocols.

## Required evidence layers

1. **Authority:** character version, identity policy, references, rights, transcript, hashes, and approved uses.
2. **Runtime:** exact engine/model/revision/packages, seed, controls, device, duration, output hash, and errors.
3. **Content:** normalized transcript, WER/CER, word-level errors, truncation, repetition, and hallucination.
4. **Identity:** speaker similarity against multiple references and continuity lines, with calibrated thresholds.
5. **Performance:** prosody, pitch, pace, pauses, emphasis, articulation, emotion, delivery style, and intensity.
6. **Technical:** decode, sample rate, channels, clipping, true peak, loudness, noise, bandwidth, phase, and defects.
7. **Timing:** speech bounds, target duration, alignment coverage, word/phoneme offsets, viseme/frame/sample mapping.
8. **Scene:** active speaker, position, distance, occlusion, room, microphone, dialogue edit, ducking, and mix.
9. **Review:** discriminated model or human authority, full-play coverage, scores, defects, and decision.
10. **Promotion:** immutable candidate lineage, thresholds, selected engine, rejected alternatives, rollback, and revocation.

## Provider and acquisition eligibility

Before runtime evidence is eligible, the asset must appear in `Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json` or an audited successor snapshot. Hugging Face assets require an immutable commit and exact runtime-critical LFS hashes. Civitai integrations require exact model/version/file IDs and SHA-256 and remain community integration candidates rather than model authority. Provider discovery, download, scan success, or workflow import cannot satisfy runtime, perceptual, or production gates.

Custom or unknown model terms, gated access, mismatched source commits, ambiguous multifile payloads, and unverified community conversions fail closed. Reuse a previously calibrated exact hash before reacquisition, and preserve completed-runtime no-rerun evidence.

## Hard rejection gates

- unknown or unauthorized voice authority;
- missing model/reference/output hashes;
- transcript leakage from evaluator labels into generation;
- missing, substituted, or hallucinated spoken content beyond threshold;
- spoken-content truncation used to meet duration;
- identity similarity below calibrated character threshold;
- unmeasured or excessive timing correction;
- non-monotonic or incomplete word/phoneme alignment;
- clipping, decode failure, terminal corruption, or severe bandwidth defect;
- active speaker or character ownership mismatch;
- model review represented as human review;
- promotion without complete evidence and rollback lineage.

## Timing acceptance

Record leading silence, speech onset, speech offset, trailing silence, total duration, target duration, native error, correction method, correction ratio, and corrected error. A corrected candidate must rerun content, identity, technical, and playback QA. Correction may not remove phonemes or change pitch/formant beyond calibrated bounds.

### Phoneme-alignment dependency and prospective matrix

The current-pod phoneme lane uses the hash-locked `phonemizer-fork==3.3.2` and `espeakng-loader==0.2.4` environment. Its Linux wheel requires one declared exact embedded-data symlink; activation must create or reuse only that symlink, verify its immutable target, and fail closed on a non-symlink or foreign target. Import and deterministic text phonemization grant dependency authority only.

The admitted Wav2Vec2 phoneme model passed the immutable clean-speech, tone-only, silence, and speech-plus-tone matrix under an exclusive shared-capacity lease. Both speech fixtures produced complete monotonic transcript-bound phoneme spans, both negative controls refused the speech gate, peak incremental GPU use was 1,842 MiB, and process exit returned to the exact pre-worker baseline. This grants authority only for that exact package, runtime, transcript, and four-fixture matrix.

General forced-alignment authority remains withheld until the same prospective process covers multiple speakers, accents, languages, noise levels, durations, overlaps, transcript mismatches, timing-boundary error, repeatability, and downstream viseme compilation. The retained matrix may seed those fixtures but may not be represented as speaker identity, general audio semantics, AV sync, operational activation, or product promotion.

### IPA-to-viseme compilation

Row136 consumes only an accepted speech fixture whose canary receipt, model package, transcript, fixture audio, and phoneme spans are hash bound. The mapping registry is versioned and must cover every observed IPA token without fallback substitution. The compiler inserts explicit silence for every unaligned sample gap, retains the model posterior only on aligned phoneme events, and requires a complete contiguous nonoverlapping sample timeline.

Frame controls use exactly one center-sample owner per frame. Coarticulation may blend only the immediately adjacent visemes under the frozen attack/release policy; every weight is bounded and sums to one. Both accepted speech fixtures must compile deterministically and preserve the same ordered phoneme-to-viseme sequence before the exact fixture compiler is accepted. Compilation alone never proves rendered lip sync, identity preservation, AV sync, general phoneme coverage, operational activation, or product promotion.

The frozen compiler passed both accepted speech fixtures: each output has 59 contiguous sample events, 77 single-owner frame controls, full silence/closure/plosive/fricative/vowel/rapid-transition coverage, and the same ordered 30-token IPA-to-viseme sequence. The tone-contaminated fixture shifted some accepted alignment boundaries by at most 20.125 ms and differed on six primary frame labels; those values are retained as diagnostics and are not promotion thresholds. Exact two-fixture compilation is accepted, while rendered lip-sync and all broader authority remain withheld.

### LatentSync admission boundary

Row137 uses official LatentSync code pinned at commit `a229c3948406bc2cf6eaf4873e662e70c6a04746` and the exact 13-file `ByteDance/LatentSync-1.6` model package at revision `c42c7e6c8e9c213626389fa7d9a3c444b8536353`. Storage installation is a separate no-load transaction. Code checkout, dependency environment, source video, audio/control binding, identity baseline, capacity lease, inference, temporal QA, whole-video visual review, cleanup, rollback, and promotion each require later evidence.

The first video fixture must be immutable, rights/provenance qualified, face-detectable, and suitable for identity comparison. Absence of such a fixture blocks inference but does not block exact model storage or isolated dependency work. Official demo media may be used only for a non-product capability diagnostic unless its subject and media rights are separately accepted.

The 13-file model package now passes atomic storage installation and an independent full-file installer replay. The retained package contains 9,635,785,477 payload bytes including small repository files, and its installation receipt SHA-256 is `35510125ed8716193501f8ee5175abb2bc5c34f1610e29bd782865f1e3099b7d`. This is storage authority only; the next stage remains exact code, isolated dependencies, and an eligible video/identity fixture.

The code checkout admission pins commit `a229c3948406bc2cf6eaf4873e662e70c6a04746` and tree `51f62bc8aea02da92b1a349077cfb78d0456f742`. GitHub does not report a verified signature for this commit, so exact commit/tree identity, official repository ownership, clean detached checkout, recorded license, and later code review are the acceptance basis; signature verification must not be claimed. Checkout admission permits no import, execution, dependency install, node activation, model load, or inference.

The detached checkout now passes exact HEAD/tree identity, a clean 124-file inventory totaling 10,801,107 bytes, no submodules, and no symlinks. No project code was imported or executed. This grants checkout identity only; semantic review, dependency lock/build, import, runtime, and product gates remain pending.

The Python 3.11/cu121 dependency graph now has an accepted 149-package `uv` pylock (`ac29c11...b9605`) whose 281 wheel/source artifact entries all carry SHA-256 values and use only `files.pythonhosted.org` or `download-r2.pytorch.org`. A prior resolver output (`c237e2bb...5a59a`) is rejected because its selected Jinja2 and MarkupSafe wheels carried no SHA-256 values. The accepted lock still grants no install authority: `antlr4-python3-runtime==4.9.3`, `insightface==0.7.3`, and `python-speech-features==0.6` are source-only and require a separately hash-bound build environment and retained wheel receipts before runtime-environment admission.

Those three source-only packages now have accepted local wheels built by the six-package hash-locked Python 3.11 builder. All three source archives passed hash, traversal, link, and setup-script process/network scans; the resulting three wheels pass metadata, RECORD, path, symlink, ZIP-integrity, hash, tree, and replay verification. Two pre-build failures are retained as evidence and published no wheelhouse. This grants exact source-wheel identity only; isolated runtime installation, imports, model load, inference, visual/temporal review, activation, and product authority remain pending.

The isolated Python 3.11/cu121 environment now passes from repaired-wheel lock `fcda6408...b599e`: 149 distributions exactly match the lock, `uv pip check` passes, the active/global metadata signature is unchanged, and full tree replay passes. The upstream decord wheel required a separately admitted two-entry `WHEEL`/`RECORD` repair; `libdecord.so` remains byte-identical. A subsequent CUDA-hidden, offline canary passes 18 exact package/project imports from the admitted environment and clean checkout. These results grant dependency installation and import authority only. Model configuration, weights, construction, tensor/GPU work, inference, source-video rights, identity/AV-sync review, activation, and product authority remain false. The retained environment's conservative apparent size is 10.691 GiB and the current provider-quota reserve estimate is 53.335 GiB, so every further large admission requires a new budget check.

The Row137 functional fixture is separately admitted and atomically present. Its video is project-generated from an unnamed fictional adult prompt; its speech voice is a Public Domain Mark 1.0 LibriVox excerpt, and its foley attribution remains bound. All 49 frames are reviewed and contain a usable face, but known identity and side-light drift make the fixture deliberately non-golden. Fixture storage and rights scope do not grant model-load, inference, identity-preservation, AV-sync, visual-quality, activation, or product authority. If the shared coordinator is in a foreign-project recovery state, never clear or override that lease; continue non-GPU preparation and wait for the owning project to restore admission.

## Multi-engine comparison

Hard-gate survivors are ranked by a versioned scorecard. The record must expose raw metrics, normalized metrics, weights, missing-metric handling, and final explanation. A missing mandatory metric blocks; it is never assigned a neutral score.

## Human playback

Automation creates the packet and validates it. A real reviewer records reviewer ID/role, independence attestation, device/environment, full-play coverage, artifact hash, naturalness, intelligibility, identity, emotion/style, timing, defects, and final decision. Human playback and final production authority remain separate roles unless the protocol explicitly authorizes one person for both and records that exception.

## Certification corpus

Final certification includes multiple approved male and female character voices, varied pitch/timbre/accent, neutral and expressive lines, whispers/shouts, breaths and vocal efforts, short and long timing targets, proper names/numbers, multilingual cases, overlapping speakers, off-screen and occluded dialogue, moving sources, multiple room types, and final mux playback.

## No-false-completion rule

Planning, schema validation, model download, model-load smoke, one candidate, automated metrics, or one listening review cannot complete the system. Row148 requires a hash-bound multi-character, multi-engine, multi-scene production matrix with zero unresolved blocking defects and explicit authority.
