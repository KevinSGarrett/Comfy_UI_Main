# Wave64 Autonomous Hyperreal Speech and Voice Master Plan

## Authority and scope

This additive package governs Wave64 Rows113-148. It extends, but does not replace, Rows025-033 and the autonomous sound-intelligence Rows067-112. Rows067-112 own general audio-library understanding, Foley, generated sound, spatial rendering, mixing, and video-to-audio orchestration. Rows113-148 own human speech, character voice identity, pronunciation, prosody, nonverbal vocalization, dialogue timing, phoneme/viseme alignment, speech mixing, and speech certification.

Planning, schemas, or model acquisition never imply runtime readiness. Every row begins as `Planned_Autonomous_Implementation_Required`. A row can advance only from hash-bound implementation, deterministic tests, genuine runtime output where required, direct QA, and an explicit pass or exact blocker.

## Current truth boundary

- The 39,771-file external audio index is technically complete and hash-bound, but the semantic audio-card enrichment in Rows067-112 remains planned.
- Parler-TTS, CosyVoice2, and Chatterbox have genuine runtime candidates, but none is production eligible.
- The preserved Chatterbox candidate has exact text, WER 0.0, passing speaker similarity and DNSMOS, and 3.92-second duration against a 3.0-second contract.
- The corrected CosyVoice2 candidate has exact text and passing speaker similarity, but 4.84-second duration against the same contract.
- C01 remains `identity_policy=pending_selection` and `production_authorized=false`.
- Human playback and production-review authority remain required for final perceptual certification. Automation prepares, ranks, and validates every packet; it must not invent a human decision.

## Completion meaning

The speech system is complete only when it can autonomously:

1. create or select a licensed character voice authority;
2. normalize dialogue and resolve pronunciation before synthesis;
3. plan duration, pauses, emphasis, emotion, intensity, articulation, breaths, and vocal effort;
4. route each line through a benchmarked engine ensemble;
5. generate bounded candidates with immutable seeds, model hashes, revisions, and settings;
6. reject hallucination, truncation, repetition, wrong text, identity drift, timing drift, acoustic defects, and inappropriate style;
7. align accepted speech to words, phonemes, visemes, frames, and samples;
8. integrate dialogue with room acoustics, Foley, ambience, spatial position, ducking, buses, and final mux;
9. preserve continuity across lines, shots, scenes, languages, and production revisions;
10. promote, revoke, and replay every production decision from immutable evidence.

## Non-negotiable invariants

- Gold/reference audio and evaluator inputs remain separate from generated candidates.
- Voice identity is never inferred from a filename alone.
- Adult or NSFW source naming is metadata only and never causes hiding, suppression, quarantine, deprioritization, or a separate content gate.
- `content_based_suppression=false` remains explicit in every applicable asset and candidate record.
- Paid, private, gated, or license-restricted access is not bypassed.
- Exact local, legacy, S3, or model-cache hashes are reused before network acquisition.
- Downloaded is not ready; model load, runtime output, technical QA, perceptual QA, and promotion are separate gates.
- Emotion class, delivery style, intensity, pace, emphasis, articulation, and duration remain independent controls.
- `focused` and `controlled` are never force-mapped into an emotion classifier taxonomy.
- Post-generation truncation cannot be used to conceal missing words.
- Time stretching is permitted only as a bounded, measured postprocess after content and identity pass, with pitch/formant, transient, intelligibility, and perceptual QA.
- A rejected candidate is immutable and is never silently replaced under the same candidate ID.
- One engine is not assumed best for every voice, language, line length, or delivery style.

## Engine ensemble strategy

The router must benchmark exact immutable revisions rather than vendor or family names. Initial candidate families are:

- Qwen3-TTS VoiceDesign, CustomVoice, and Base for designed voices, cloning, expressive instruction, and streaming;
- Fun-CosyVoice3 as the successor benchmark to the installed CosyVoice2 payload;
- Chatterbox Multilingual V3 and Turbo for multilingual identity continuity and efficient English delivery;
- Fish Speech S2 for multilingual and short-reference cloning comparison;
- existing Parler-TTS as a prompt-controlled English baseline;
- approved RVC or other speech-to-speech conversion only when source/reference rights and identity authority are explicit.

Each adapter must record repository, immutable revision, model filenames, SHA-256, bytes, license, architecture, sample rate, language support, reference requirements, VRAM, runtime packages, deterministic settings, and ComfyUI/API wiring. Community wrappers are integration candidates, not model authority.

## Provider-resolved asset authority

The exact provider snapshot is `Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json`. It binds official Hugging Face repository commits and runtime-critical LFS hashes, official source-code commits, exact Civitai model/version/file IDs and hashes for optional ComfyUI integrations, license/access states, priorities, dispositions, and Row117-148 dependencies.

Row117 must execute that catalog through the unified model-asset acquisition controller. It must reuse exact local/Main/legacy/S3/cache hashes before any network transfer. Civitai workflow archives are inspected offline and may contribute wiring patterns, but they never replace official model authority and may not install dependencies implicitly. Unknown/custom model terms, gated acceptance, unavailable exact hashes, or incompatible nodes remain exact blockers.

The initial provider-resolved P0 set includes Qwen3-TTS 1.7B CustomVoice/Base/VoiceDesign and tokenizer, Fun-CosyVoice3 0.5B, Chatterbox multilingual V3 and Turbo, Fish Audio S2 Pro subject to exact terms, MMAudio reuse-first, HunyuanVideo-Foley XL subject to terms, Stable Audio 3 Small SFX subject to gated terms, LatentSync 1.6, LAION CLAP, Whisper large-v3-turbo, pyannote diarization subject to gated acceptance, and the existing calibrated emotion2vec/DNSMOS/ERes2Net routes. Lower-VRAM Qwen variants and Stable Audio 3 Medium remain benchmarked fallbacks rather than automatic downloads.

The tournament challenger pool additionally includes IndexTTS2, F5-TTS, Spark-TTS, VibeVoice 1.5B, VoxCPM2, Step-Audio-2 Mini, Dia2 2B, Sesame CSM 1B, MegaTTS3, MaskGCT, and OpenVoiceV2. Challengers exist to cover emotion/timbre transfer, long-form and multi-speaker dialogue, conversational context, zero-shot cloning, duration modeling, speech-to-speech tone conversion, and lower-cost alternatives. P1/P2 status does not authorize installation: the router activates a challenger only when its capability is relevant, its terms permit the intended scope, and the P0 tournament leaves a measured gap.

## Candidate tournament

For each character and dialogue class, route at least three materially distinct eligible engines when available. A tournament record must include:

- exact normalized text and pronunciation plan;
- target duration and tolerance;
- character/reference authority hashes;
- engine/model/revision/configuration;
- seed and sampling controls;
- WER/CER and hallucination/repetition checks;
- speaker similarity and continuity-line similarity;
- pitch, energy, speaking-rate, pause, and prosody deltas;
- emotion, delivery-style, and intensity evidence without taxonomy conflation;
- DNSMOS or successor quality metrics and full-band technical checks;
- word/phoneme alignment coverage and timing error;
- model-review eligibility and human-playback eligibility;
- rejection reasons and no-rerun policy.

The router chooses the highest-scoring eligible candidate, not the candidate with the best single metric.

## Duration strategy

Dialogue timing is planned before synthesis:

1. normalize text and count expected syllables/phonemes;
2. estimate duration from the character's calibrated pace distribution;
3. adjust script punctuation, pause plan, and engine controls without changing semantic content;
4. generate bounded candidates;
5. measure actual speech bounds separately from leading/trailing silence;
6. accept native timing when within tolerance;
7. optionally apply a bounded high-quality stretch only within a calibrated ratio and only after content/identity pass;
8. otherwise reject and route to a materially different engine/configuration or revise the shot timing contract through explicit authority.

The system must never trim spoken content to satisfy a duration target.

## Voice-reference cards

Every production character requires one or more immutable voice-reference cards containing:

- character and character-version IDs;
- identity policy and production authorization state;
- source path, SHA-256, bytes, duration, sample rate, channels, transcript, and language;
- license, attribution, provenance, permitted derivative uses, and restrictions;
- speaker demographics only when explicitly supplied and technically relevant;
- timbre, pitch range, accent, pace, articulation, delivery styles, emotion/intensity coverage, and microphone/room observations;
- clean speech segments and excluded regions;
- continuity lines and pronunciation dictionary;
- embedding model/revision and reference embeddings;
- reference-quality, clipping, noise, reverb, and contamination scores;
- approved engines and locked configurations;
- revocation and replacement lineage.

Reference-card approval is separate from engine approval and generated-candidate promotion.

## Human vocal sound scope

The speech system includes spoken dialogue plus breaths, gasps, sighs, laughs, cries, exertion, effort, strain, whispers, shouts, coughs, and other nonverbal vocal events. These events use the same identity, rights, intensity, timing, room, and promotion controls as speech. They may come from licensed recordings, approved voice conversion, deterministic composition, or a validated generative engine. The system must distinguish vocal events from generic Foley and from spoken words.

## Alignment and video integration

- Whisper/WhisperX-style ASR supplies content and word-timing evidence.
- Montreal Forced Aligner or an equivalent validated route supplies phoneme timing and pronunciation diagnostics.
- Speaker diarization and active-speaker tracking bind speech to the correct visible character.
- Viseme compilation maps phonemes to the project's face/mouth control representation with coarticulation and confidence.
- Lip-sync correction is a downstream candidate stage, not permission to accept incorrect speech.
- Sample-accurate dialogue timing binds to canonical video timebase, frame PTS, audio samples, and mux lineage.
- Off-screen, occluded, distant, whispered, and overlapping dialogue retain explicit acoustic-source state.

## Acoustic realism

Clean synthesis is treated as a dry production source. The mix pipeline may apply, through measured nondestructive stages:

- breath and mouth-noise management;
- de-click, de-plosive, de-ess, and noise reduction;
- microphone and proximity modeling;
- EQ, compression, saturation, and limiting;
- distance, obstruction, occlusion, early reflections, and room response;
- actor position and movement automation;
- dialogue editing, crossfades, room tone, Foley/ambience ducking, and bus processing.

Enhancement must not erase character identity, consonants, breaths needed for realism, or intentional vocal texture.

## Reserved execution rows

- Rows113-116: authority, cards, reference intake, and character casting.
- Rows117-118: engine acquisition and benchmark tournament.
- Rows119-122: text, pronunciation, dialogue, and duration planning.
- Rows123-127: candidate generation, cloning/design, prosody, and emotion/intensity.
- Rows128-130: nonverbal voice, acoustic chain, and enhancement.
- Rows131-134: identity, continuity, multilingual, and multi-speaker control.
- Rows135-140: forced alignment, visemes, lip sync, spatialization, mixing, and overlaps.
- Rows141-144: evaluator ensemble, adversarial QA, playback packets, and promotion/revocation.
- Rows145-148: ComfyUI integration, runtime/cache, benchmark corpus, and final certification.

## Dependency and execution order

Phase A: Rows113-122 establish authority and deterministic planning.

Phase B: Rows123-134 produce and evaluate dry character speech and vocal events.

Phase C: Rows135-140 align and mix speech into video.

Phase D: Rows141-148 certify evaluation, orchestration, and production behavior.

Rows may run in parallel only when their declared input authorities are immutable and their output paths do not overlap. Existing Rows025-033 remain the portfolio-level production gates and are updated only after real evidence from this expansion exists.

## Required evidence

Each row requires source citations, implementation hashes, tests, exact dependency versions, runtime manifests where applicable, artifact hashes, QA records, blocker/pass decisions, and explicit prohibited claims. Final certification requires multiple characters, male and female voice profiles, short and long lines, emotional and neutral delivery, multilingual cases where supported, close and distant acoustics, overlapping dialogue, nonverbal vocal events, multiple scenes, and muxed-video playback review.

## No-conflict main-session boundary

This package is additive. It does not edit the existing Rows025-033, Rows067-112, hydration top blocks, package manifests, runtime queue, Git state, AWS state, masks, Wave71, or Jira. The main session may ingest this package at a stable checkpoint and must preserve concurrent model-acquisition and runtime work.
