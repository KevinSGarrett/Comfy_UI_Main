# Wave64 Autonomous Hyperreal Speech Architecture

## Pipeline

```text
character authority
  -> voice-reference cards
  -> dialogue normalization and pronunciation
  -> duration/prosody/nonverbal plan
  -> engine eligibility router
  -> bounded multi-engine candidate generation
  -> technical/content/identity/prosody evaluation
  -> word and phoneme alignment
  -> candidate tournament and promotion
  -> viseme and active-speaker binding
  -> acoustic scene rendering
  -> dialogue edit and mix
  -> sample-accurate mux
  -> automated and human playback QA
  -> production certification or exact blocker
```

## Service boundaries

### Voice authority service

Owns character-version identity policy, reference cards, rights, embeddings, continuity lines, pronunciation dictionaries, approved engines, and revocation. It never performs synthesis.

### Dialogue compiler

Converts script text into an immutable line contract containing normalized text, original text, language, pronunciation, tokens, expected phonemes, target duration, pace, pauses, emphasis, emotion class, delivery style, intensity, articulation, breath plan, overlap state, actor/source position, and QA thresholds.

### Provider asset resolver

Resolves each row's required asset IDs through `Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json`, checks exact-hash reuse, license/access state, official revision and file identity, adapter compatibility, placement, and runtime visibility, then emits an acquisition request or one exact blocker. Civitai workflows are sandboxed integration inputs and cannot replace official model authority or install undeclared dependencies.

### Engine adapter layer

Each engine adapter exposes the same request/result contract. Engine-native controls are translated explicitly and unsupported controls remain unsupported rather than being approximated silently. Adapter output records exact model/revision/hash, package identity, seed, sampling, reference hashes, inference time, memory, output format, and warnings.

### Candidate tournament

The tournament rejects candidates failing hard gates, normalizes soft scores, applies scope-specific weights, and emits an explainable ranking. Hard gates include decode integrity, exact content, no truncation, no hallucinated words, reference authority, speaker floor, timing policy, clipping/true peak, and prohibited promotion claims.

### Alignment service

Produces word, phoneme, pause, breath, and viseme intervals against both seconds and sample indexes. It records transform lineage and rejects incomplete coverage, non-monotonic intervals, transcript disagreement, or source-rate ambiguity.

### Acoustic renderer

Receives dry promoted dialogue and scene acoustics from Rows088, 095, and 096. It applies source position, distance, obstruction, room response, microphone character, EQ/dynamics, and automation while retaining a dry stem and nondestructive recipe.

### Speech QA service

Combines ASR, speaker verification, pitch/prosody analysis, emotion/intensity evidence, DNSMOS/full-band quality, forced-alignment metrics, repetition/hallucination checks, active-speaker timing, mux validation, and playback review. Model authority and human authority remain discriminated.

## Storage model

- `runtime_artifacts/audio_voice_references`: immutable reference-card payloads and derived features.
- `runtime_artifacts/audio_speech_candidates`: candidate WAVs, manifests, metrics, and rejection records.
- `runtime_artifacts/audio_speech_alignments`: word, phoneme, viseme, and frame/sample mappings.
- `runtime_artifacts/audio_speech_promoted`: promoted dry dialogue and promotion records.
- `runtime_artifacts/audio_speech_mix`: stems, acoustic recipes, mixes, and mux outputs.
- Git stores schemas, adapters, compact registries, tests, protocols, evidence summaries, exact hashes, and runtime pointers, not large generated media.

## Determinism and replay

Every decision unit binds request hash, character version, references, model files, package versions, seed, engine controls, preprocessing transforms, output hash, evaluator versions, thresholds, scores, ranking, and final disposition. Replaying with missing or hash-different dependencies fails closed.

## Engine isolation

TTS engines may require incompatible Python, Torch, CUDA, ONNX, or custom-node dependencies. Each engine runs in an isolated environment or container with a declared lockfile. ComfyUI calls adapters through a stable local API or subprocess contract; it does not merge incompatible packages into one interpreter.

## Failure taxonomy

- `BLOCKED_VOICE_AUTHORITY_MISSING`
- `BLOCKED_REFERENCE_RIGHTS_OR_PROVENANCE`
- `BLOCKED_ENGINE_MODEL_OR_RUNTIME_MISSING`
- `BLOCKED_ASSET_LICENSE_OR_GATED_ACCESS`
- `BLOCKED_ASSET_EXACT_SOURCE_OR_HASH_UNRESOLVED`
- `REJECTED_COMMUNITY_WORKFLOW_DEPENDENCY_OR_PROVENANCE`
- `REJECTED_SPEECH_CONTENT_MISMATCH`
- `REJECTED_SPEECH_TRUNCATION_OR_HALLUCINATION`
- `REJECTED_SPEAKER_IDENTITY_DRIFT`
- `REJECTED_DURATION_OR_ALIGNMENT`
- `REJECTED_PROSODY_STYLE_OR_INTENSITY`
- `REJECTED_TECHNICAL_AUDIO_DEFECT`
- `REJECTED_ACTIVE_SPEAKER_OR_LIP_SYNC`
- `REJECTED_ACOUSTIC_SCENE_MISMATCH`
- `BLOCKED_PLAYBACK_AUTHORITY_MISSING`
- `BLOCKED_PRODUCTION_CERTIFICATION_INCOMPLETE`

## Runtime policy

Local execution is preferred when model and compute fit. EC2 is permitted only after exact dependency, cost, watchdog, input, and pullback gates. Completed candidates are never regenerated solely to refresh evidence. One materially scoped candidate batch should evaluate several compatible engines or lines before a guarded checkpoint.
