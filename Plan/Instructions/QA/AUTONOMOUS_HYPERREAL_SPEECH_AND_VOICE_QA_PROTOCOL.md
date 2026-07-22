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

## Multi-engine comparison

Hard-gate survivors are ranked by a versioned scorecard. The record must expose raw metrics, normalized metrics, weights, missing-metric handling, and final explanation. A missing mandatory metric blocks; it is never assigned a neutral score.

## Human playback

Automation creates the packet and validates it. A real reviewer records reviewer ID/role, independence attestation, device/environment, full-play coverage, artifact hash, naturalness, intelligibility, identity, emotion/style, timing, defects, and final decision. Human playback and final production authority remain separate roles unless the protocol explicitly authorizes one person for both and records that exception.

## Certification corpus

Final certification includes multiple approved male and female character voices, varied pitch/timbre/accent, neutral and expressive lines, whispers/shouts, breaths and vocal efforts, short and long timing targets, proper names/numbers, multilingual cases, overlapping speakers, off-screen and occluded dialogue, moving sources, multiple room types, and final mux playback.

## No-false-completion rule

Planning, schema validation, model download, model-load smoke, one candidate, automated metrics, or one listening review cannot complete the system. Row148 requires a hash-bound multi-character, multi-engine, multi-scene production matrix with zero unresolved blocking defects and explicit authority.
