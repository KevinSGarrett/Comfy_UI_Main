# Wave64 Autonomous Sound Intelligence Architecture

## Boundary

ComfyUI is the execution surface. The external controller owns scene reasoning, dependency selection, evidence validation, retry policy, and promotion. Large media, embeddings, feature stores, generated candidates, and mixes remain outside Git; Git stores schemas, code, compact registries, hashes, and evidence pointers.

## Services

### Media normalizer

Produces canonical video timing and canonical audio analysis representations. It preserves original bytes and records all time-base, sample-rate, channel, and transform decisions.

### Audio intelligence service

Produces acoustic features, onset/offset/peak anchors, usable bounds, segments, embeddings, tags, quality defects, room characteristics, and canonical PCM hashes. Feature records are keyed by:

```text
source_sha256 + decoder_revision + feature_pipeline_revision + model_hashes
```

### Visual event intelligence service

Fuses scene registry state, actor/object tracks, masks, landmarks, flow, depth, material evidence, and contact-graph rules. It outputs confidence-scored events and silence decisions. It must distinguish observed, inferred, inherited-from-scene-state, and unknown evidence.

### Retrieval and decision service

Applies hard filters first, then weighted ranking. Hard filters include rights, decode integrity, event family compatibility, mandatory ownership/material fields, and certification ceiling. Soft ranking includes semantic similarity, force, duration, onset quality, room compatibility, quality, continuity, variation, and cost.

### Sound creation service

Supports deterministic DSP variants, layered composites, procedural synthesis, text-to-audio, audio-to-audio, and video-to-audio. It returns candidates only. It has no promotion authority.

### Renderer

Prepares clips, aligns measured anchors, layers stems, applies source motion, distance, occlusion, early reflections, room tails, bus processing, and sample-accurate scheduling.

### QA and authority service

Runs technical, semantic, timing, spatial, global, and multimodal checks. It separates automated QA, playback review, final production authority, and reusable-library promotion.

### Run coordinator

Executes a content-addressed DAG. Each node is idempotent and resumable. A node may consume only immutable predecessor records in a pass-like state allowed by policy.

## Core records

- `audio_asset_intelligence_record`
- `audio_segment_record`
- `visual_audio_event_manifest`
- `audio_candidate_score_record`
- `audio_clip_preparation_manifest`
- `audio_spatial_render_manifest`
- `generated_audio_asset_provenance`
- `generated_audio_qa_report`
- `audio_orchestration_run`
- existing Wave30/Wave31/Wave64 QA records through versioned adapters

## Heel-on-hardwood execution

1. Track actor, right foot, floor region, camera, and room.
2. Infer heel strike from downward foot trajectory, velocity change, landmark/mask proximity, depth consistency, and contact persistence.
3. Resolve footwear and surface material with confidence.
4. Emit a `footstep.heel_strike` event with frame, seconds, sample anchor, force, source position, and uncertainty.
5. Hard-filter the index for rights, decode, footstep/impact family, compatible material/footwear, and frame-exact onset suitability.
6. Rank candidates and apply recent-use penalties.
7. If confidence is insufficient, route to layered synthesis or generated fallback; do not pretend an approximate sound is exact.
8. Prepare the selected clip and subtract its measured transient offset from the event sample anchor.
9. Render room reflections from the environment profile without double-reverberating a wet source.
10. Mix, mux, and verify contact-to-transient offset, endpoint drift, room consistency, clipping, repetition, and full-scene quality.

## Hand-to-body contact execution

1. Track source hand and target actor/body region with ownership.
2. Infer approach, contact, compression/recoil, release, velocity, clothing coverage, and visibility.
3. Emit one parent contact event and optional child layers: body transient, clothing movement, settle, breath reaction, and room response.
4. Retrieve or generate each justified layer separately.
5. Align the transient to contact onset; align rustle/settle envelopes to motion windows.
6. Block certification when source/target ownership or body/contact geometry is untrusted.

## Ranking model

The canonical score is an explainable weighted composition, not an opaque single embedding score:

```text
eligible = rights AND decode AND event_family AND mandatory_fields AND quality_floor
score = semantic + taxonomy + material + source_target + force + duration
      + onset + acoustic + spatial + continuity + quality
      - recent_use - near_duplicate - transform_cost - uncertainty
```

Weights are versioned by event family and calibrated on held-out fixtures. Hard exclusions are recorded separately from scores.

## Variation model

Variations use a three-tier policy:

1. `micro_variation`: bounded gain, timing, pitch, EQ, transient, stereo, and room changes.
2. `structural_variation`: approved layer substitution, alternate parent segment, or audio-to-audio generation.
3. `new_event_generation`: text/video-conditioned generation when no library candidate reaches threshold.

The engine must preserve action/material identity, maintain natural timing, avoid exact or near duplicates, and record every source and transform.

## Fail-closed boundaries

- Unknown rights: no use or generation from the asset.
- Unknown source/target ownership: candidate mix allowed only below certification ceiling.
- Unknown material: broader retrieval class or generation prompt; never exact-material certification.
- Ambiguous onset: multi-anchor candidate or windowed sync; never frame-exact claim.
- Missing model hash/revision: engine unavailable.
- Generated semantic mismatch or unexpected speech/music: reject.
- Existing strong reverb with incompatible target room: reject or use dry alternative.
- Missing final playback authority: technical pass only where protocol requires listening.

## Research basis

- LAION CLAP: https://github.com/LAION-AI/CLAP
- Essentia onset detection: https://essentia.upf.edu/tutorial_rhythm_onsetdetection.html
- MediaPipe Pose: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker
- SAM2 video segmentation: https://github.com/facebookresearch/sam2
- RAFT optical flow: https://docs.pytorch.org/vision/stable/models/raft.html
- Depth Anything V2: https://github.com/DepthAnything/Depth-Anything-V2
- Pyroomacoustics: https://github.com/LCAV/pyroomacoustics
- AudioCraft AudioGen: https://github.com/facebookresearch/audiocraft/blob/main/docs/AUDIOGEN.md
- Stable Audio tools and init-audio: https://github.com/Stability-AI/stable-audio-3
- MMAudio: https://github.com/hkchengrex/MMAudio
- HunyuanVideo-Foley: https://github.com/Tencent-Hunyuan/HunyuanVideo-Foley

All external engines remain subject to local payload, license, security, capability, and runtime validation.
