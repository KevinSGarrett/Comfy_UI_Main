# Autonomous Video-to-Audio and Generated Sound QA Protocol

## Scope

This protocol governs Wave64 Rows067-112 and complements existing Rows025-033 protocols. It applies to retrieved sounds, transformed derivatives, layered composites, procedural sounds, neural generations, mixes, and muxes.

## Required authority layers

1. `source_and_rights_authority`
2. `visual_event_authority`
3. `audio_semantic_authority`
4. `timing_and_onset_authority`
5. `render_and_spatial_authority`
6. `technical_qa_authority`
7. `playback_review_authority` when required
8. `production_release_authority`
9. `generated_asset_promotion_authority` for reusable generated sounds

No authority layer may manufacture evidence belonging to another layer.

## Mandatory automated gates

- exact input/output hashes and canonical PCM hashes;
- model, revision, weight hash, configuration, environment, and seed;
- rights and attribution decision;
- source/target/event/material confidence;
- event coverage and false-event rejection;
- onset/contact offset and endpoint drift;
- duration, sample rate, channels, loudness, true peak, clipping, silence, and defects;
- semantic event/material/action fit;
- generated-output unexpected-class rejection;
- room, pan, distance, occlusion, and continuity consistency;
- duplicate and near-duplicate detection;
- full-duration mix/global review;
- immutable evidence and no-clobber publication.

## Timing thresholds

Thresholds must be registered per event family and frame rate. A frame-exact contact event should target an error no greater than half a source frame, with stricter sample-domain thresholds where calibrated. Windowed rustle, ambience, and movement events use explicit onset/end windows. The evaluator records both frame and sample errors.

## Semantic ensemble rule

Filename/path tags, audio embeddings, acoustic features, audio tags/captions, event-script expectations, and applicable reference comparisons are independent signals. No single signal may grant final semantic PASS. Disagreement produces lower confidence, fallback, or abstention.

## Generated candidate decision

A generated candidate must be rejected for any of the following:

- unknown output-use rights;
- missing engine/model/config provenance;
- decode failure or corrupted samples;
- wrong or extra event family;
- unexpected speech or music when excluded;
- missing/late/early primary transient;
- truncated attack or natural decay;
- material/action mismatch beyond threshold;
- severe noise, clipping, hum, dropout, or pre-reverb conflict;
- canonical or near duplicate without a justified role;
- source leakage or memorization concern identified by the configured checks;
- failed full-scene mix or AV-sync review.

## Benchmark requirements

Benchmarks must include:

- heel and toe phases on wood, tile, carpet, concrete, and ambiguous surfaces;
- bare foot, soft shoe, sneaker, boot, and hard heel;
- hand/body contacts with visible, clothed, occluded, and multi-actor ownership cases;
- fabric, prop, furniture, door, water, and ambience events;
- single and repeated events;
- dry and reverberant sources;
- fixed and moving cameras;
- cuts, slow motion, variable frame rate, and offscreen events;
- intentionally silent visual motion;
- adversarial filename and semantic mismatches;
- generated candidates containing extra events, wrong materials, or timing drift.

Train, calibration, and final test partitions remain separate. Generated outputs cannot become reference truth merely by passing their own model-based evaluator.

## Completion rule

Rows067-112 remain planned or blocked until their exact implementation, tests, runtime evidence, and QA pass. Row112 cannot pass while any prerequisite row is incomplete or while required playback/production authority is absent.
