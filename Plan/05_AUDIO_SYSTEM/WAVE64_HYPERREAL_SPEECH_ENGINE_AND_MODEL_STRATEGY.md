# Wave64 Hyperreal Speech Engine and Model Strategy

## Selection principle

There is no universal best TTS model. The production router selects an exact engine revision per character, language, line type, duration, and style using calibrated evidence. Model popularity, example demos, or workflow availability are not production proof.

## Initial benchmark families

### Qwen3-TTS

Evaluate exact VoiceDesign, CustomVoice, and Base variants for designed synthetic identity, reference cloning, instruction control, streaming, multilingual output, and short/long dialogue. Acquire immutable Hugging Face files through the unified acquisition controller. Record model-card license and all tokenizer/codec dependencies.

### Fun-CosyVoice3

Benchmark Fun-CosyVoice3 against the already tested CosyVoice2 path. Preserve CosyVoice2 rejected candidates; do not rerun them. Evaluate content consistency, zero-shot speaker similarity, instruction following, prosody, multilingual behavior, duration, and runtime cost.

### Chatterbox Multilingual V3 and Turbo

Benchmark V3 for multilingual identity continuity and Turbo for efficient English delivery. Preserve the existing Chatterbox rejection as immutable evidence. Verify watermark behavior, package identity, exact model revisions, hallucination rate, duration control, and identity consistency.

### Fish Speech S2

Evaluate short-reference cloning, multilingual delivery, multi-speaker behavior where supported, stability, and license. Isolate its environment and record codec/tokenizer revisions.

### Existing baselines

Parler-TTS remains a prompt-controlled English baseline. Existing CosyVoice2 and Chatterbox outputs are regression fixtures. RVC/voice conversion is a separate speech-to-speech route and requires source-performance authority plus target-character voice authority.

### Provider-resolved challengers

- IndexTTS2: emotion and timbre-conditioned cloning; blocked until exact model terms are recorded.
- VoxCPM2: Apache-licensed context-aware cloning and voice design.
- VibeVoice 1.5B: long-form and multi-speaker dialogue continuity.
- Dia2 2B: expressive dialogue, turn-taking, and nonverbal vocal events.
- MegaTTS3: zero-shot cloning with explicit G2P, duration, alignment, and diffusion components.
- OpenVoiceV2: tone-color conversion and cross-language speech-to-speech testing.
- F5-TTS, Spark-TTS, and MaskGCT: noncommercial benchmark challengers only under their recorded model terms.
- Step-Audio-2 Mini: large any-to-any audio-language challenger, deferred until P0 engines leave an understanding/generation gap.
- Sesame CSM 1B: gated conversational-context challenger, blocked until access is accepted and recorded.

These candidates expand coverage; they do not create an unbounded tournament. The benchmark scheduler selects at least three materially distinct eligible engines per decision class, adds a challenger only for a declared capability gap, and stops when confidence, quality, runtime, and failure-rate criteria are met.

## Acquisition gates

Exact model revisions, key-file hashes, access states, Civitai integration candidates, and row bindings are authoritative in `Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json`. Family names in this document are not sufficient acquisition instructions.

For every selected model:

1. reuse an exact local, legacy, S3, or cache hash;
2. otherwise resolve an immutable provider revision and exact file list;
3. record license, access, attribution, and use restrictions;
4. acquire through API or authenticated invisible-browser fallback;
5. stage, hash, size-check, and place each file;
6. verify loader visibility and node/API surface;
7. execute a model-load smoke;
8. generate one bounded calibration candidate;
9. run technical and perceptual QA;
10. register the adapter only after evidence passes.

Downloaded assets remain unavailable to production routing until step 10.

## Benchmark matrix

Each eligible engine is tested across:

- male and female character authorities;
- low, medium, and high pitch ranges;
- neutral, focused, happy, sad, angry, fearful, surprised, whisper, shout, and restrained delivery where supported;
- low, controlled, medium, and high intensity;
- short, medium, long, punctuation-heavy, number-heavy, acronym, proper-name, and difficult-pronunciation lines;
- 1.5-second, 3-second, 6-second, and unconstrained timing targets;
- clean and noisy references, while only authority-approved references may promote;
- monolingual and cross-lingual cases;
- close, medium, distant, occluded, and reverberant scene rendering;
- continuity across at least ten lines and three scenes.

## Required metrics

- WER/CER and exact normalized transcript;
- insertion, deletion, substitution, repetition, and unwanted continuation counts;
- speaker embedding similarity against multiple reference and continuity clips;
- F0 distribution, voiced/unvoiced errors, energy, pace, pause, syllable, and phoneme duration;
- emotion-class evidence where taxonomy applies;
- separate delivery-style and intensity evidence;
- DNSMOS or successor speech quality, full-band spectral checks, clipping, true peak, noise, and reverb;
- forced-alignment coverage and word/phoneme timing error;
- native duration error and postprocess ratio where applicable;
- generation speed, peak VRAM/RAM, startup latency, and cache behavior;
- direct playback scores and defects for eligible finalists.

## Promotion policy

An engine may be approved globally, per language, per character, or per dialogue class. Character-level approval must lock model, revision, references, preprocessing, pronunciation dictionary, default controls, and QA thresholds. Promotion of one engine does not demote alternatives; the router retains approved fallbacks and diversity controls.

## Current acquisition priorities

1. Qwen3-TTS exact VoiceDesign and cloning payloads referenced by the existing workflow.
2. Fun-CosyVoice3 exact upstream payload and isolated runtime.
3. Chatterbox Multilingual V3 and Turbo exact revisions.
4. Fish Speech S2 exact runtime and weights.
5. HunyuanVideo-Foley XL/XXL for human vocal reactions only as a separate video-conditioned candidate, never as dialogue authority.
6. Stable Audio 3 for bounded vocal texture or repair experiments only after speech-leakage and identity rules are implemented.

Provider resolution found that the primary official assets are available from pinned Hugging Face repositories, while Civitai primarily contributes small community workflow archives. Therefore the default strategy is official weights plus audited local adapters; an exact Civitai workflow is used only when its wiring is useful and its scripts, nodes, embedded links, and settings pass offline inspection. The catalog records integration candidates for Qwen3-TTS, CosyVoice3, Chatterbox, Fish Audio S2, MMAudio, HunyuanVideo-Foley, Stable Audio 3, LatentSync, IndexTTS2, VibeVoice, VoxCPM2, CSM, and MegaTTS3.

Fish Audio S2, HunyuanVideo-Foley, Stable Audio 3, and pyannote retain explicit license or gated-access blockers until their exact terms are accepted and recorded. BEATs remains source-resolved but checkpoint-hash blocked; unverified community mirrors are prohibited. MFA language models are selected per certified dialogue language, not downloaded as an undifferentiated bundle.

## Prohibited shortcuts

- no latest-floating model downloads;
- no filename-only model identity;
- no unlicensed reference cloning;
- no hidden resampling, truncation, or stretching;
- no single-engine final selection without comparative evidence when alternatives are eligible;
- no model-generated reviewer metadata presented as human playback;
- no promotion from WER, speaker similarity, or DNSMOS alone.
