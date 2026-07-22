# Wave64 Autonomous Video-to-Audio and Sound Generation Master Plan

## Authority and purpose

This document is the source authority for Wave64 Rows 067 through 112. It closes the planning gap between the existing Wave22 contact graph, Wave30 audio-event contracts, Wave31 force/spatial contracts, Wave64 Rows 025 through 033, and the complete external audio library.

The target is a production system that can:

1. inspect a silent or partially scored video;
2. identify audible scene events, actors, body parts, objects, materials, motion, contacts, timing, and uncertainty;
3. retrieve and rank suitable sounds from every indexed, license-eligible asset;
4. prepare, align, layer, spatialize, mix, and mux those sounds;
5. generate new sounds or controlled variations when retrieval is insufficient;
6. evaluate generated and retrieved audio autonomously;
7. preserve exact provenance, hashes, model identity, transforms, and decisions;
8. reuse only generated assets that pass the promotion contract; and
9. fail closed rather than inventing unsupported contact ownership, material, timing, license, or production authority.

This plan is additive. It does not reopen completed runtime proof and does not declare Rows 025 through 033 complete. The existing 39,771-audio-file intake remains authoritative for inventory. The full collection contains WAV, MP3, FLAC, and OGG assets; all technical assets remain visible, including adult-specific package paths. `content_based_suppression` must remain `false`.

## Completion meaning

`100_percent_complete` means every row in this package has implementation, tests, runtime evidence, QA evidence, and a pass decision against its acceptance gates. It does not mean every arbitrary video or generated sound is guaranteed correct. Low-confidence events and failed candidates must be rejected or escalated through a documented fallback. Final production listening remains a distinct authority gate where required by the human playback-review protocol.

Planning files, schemas, registries, and validators are not runtime completion proof.

## Existing authority reused

- Wave09 environment, material, and room state.
- Wave10 camera and framing state.
- Wave22 contact graph, source/target ownership, pressure, duration, and expected audio force.
- Waves26 through 29 keyframes, per-frame manifests, motion, repetition, and continuity.
- Wave30 audio event, dialogue, Foley, ambience, mix, and AV sync contracts.
- Wave31 force, distance, panning, room acoustics, reverb, and occlusion contracts.
- Wave64 Rows 025 through 033 for pipeline, routing, voice, Foley, spatial audio, sync, strict review, global review, and multimodal certification.
- The external audio intake registry and functional index infrastructure.

## End-to-end state machine

```text
source video and scene state
-> canonical media/timeline decode
-> actor/object/body-part tracking
-> pose, flow, depth, material, and contact evidence
-> confidence-scored visual audio events
-> deterministic library retrieval
-> generated-sound fallback when justified
-> clip preparation and transient alignment
-> layering and spatial rendering
-> mix and mux
-> technical, semantic, temporal, spatial, and global QA
-> human playback authority when required
-> production release
-> promoted generated-asset reuse only after provenance and QA pass
```

Every stage writes an immutable, hash-bound record. A downstream stage may not reconstruct missing upstream authority from filenames, prose, or a final mix.

## Operating invariants

1. Original library bytes are immutable.
2. Generated and transformed files use content-addressed paths outside Git.
3. Every source, derivative, and generated asset has SHA-256 provenance.
4. Duplicate audio is detected from canonical PCM hashes as well as container hashes.
5. License and attribution metadata travel with every candidate and derivative.
6. Filename/path classification is a seed signal, never the only semantic authority.
7. Visual contact ownership is required for certifying actor-specific contact Foley.
8. Event timestamps use canonical source time bases and record frame/sample conversions.
9. Transient sounds align their measured onset or peak to the visual contact anchor.
10. Dryness and existing reverberation are measured before room processing.
11. Generated candidates never enter the reusable production library directly.
12. Model identity includes engine, model, revision, weight hash, configuration, seed, and environment.
13. A failure or abstention cannot be relabeled as a pass.
14. Retrieval, generation, mixing, and QA are deterministic when the same manifest and seeds are replayed.
15. Adult-specific labels are technical taxonomy only and do not trigger suppression or reduced priority.

## Engine strategy

The system uses a hybrid engine policy:

- `library_retrieval`: preferred for exact one-shot footsteps, impacts, body Foley, fabric, props, doors, furniture, and reusable ambience.
- `deterministic_variation`: creates bounded variants through DSP while preserving event identity.
- `layered_synthesis`: combines approved stems into a new composite event.
- `text_to_audio`: creates missing sound classes from a structured event prompt.
- `audio_to_audio`: creates controlled variants from a license-eligible source or approved generated seed.
- `video_to_audio`: creates continuous or visually complex Foley candidates from video and structured text.
- `procedural_synthesis`: creates physically simple tones, noise, swishes, resonances, or impacts from deterministic parameters.

No engine is universally authoritative. The router chooses by event type, confidence, available library coverage, duration, temporal precision, license, compute cost, and calibrated QA performance.

## Primary implementation candidates

- LAION-CLAP-compatible audio/text embeddings for semantic retrieval.
- Essentia-compatible onset detection plus independent sample-domain verification.
- MediaPipe-compatible pose/hand landmarks, SAM2-compatible video segmentation, RAFT-compatible optical flow, and Depth Anything-compatible depth adapters.
- Pyroomacoustics-compatible room impulse response simulation, plus measured impulse-response convolution where an approved IR exists.
- AudioGen-compatible text-to-sound and continuation candidates.
- Stable Audio-compatible text-to-audio, init-audio, inpainting, and continuation candidates where exact model/license authority permits.
- MMAudio-compatible and HunyuanVideo-Foley-compatible video-conditioned candidate generation.

These are adapter candidates, not preapproved production engines. Every payload and license must be registered and runtime-proven before selection.

## Reserved execution rows

### Row067 Planning authority and no-false-completion control

Implement this master plan, matching Items/Tracker coverage, dependency graph, completion semantics, and a validator that rejects missing rows, duplicate IDs, or claims that planning equals runtime completion.

Acceptance: Rows 067 through 112 exist exactly once in Items and Tracker, dependencies are acyclic, and all rows begin blocked or planned until their own evidence passes.

### Row068 Asset rights, provenance, and derivative-use authority

Implement per-asset and per-engine license records covering commercial/noncommercial constraints, attribution, derivative permission, redistribution, generated-output terms, dataset rights, and source-pack restrictions.

Acceptance: no asset can be selected, transformed, generated from, promoted, or exported without a machine-readable rights decision and attribution payload.

### Row069 Full-library resumable index completion

Finish one deterministic index across all supported audio files, preserving source bytes, resuming by path/size/mtime, hashing every asset, recording parse failures, and deduplicating container hashes.

Acceptance: indexed + exact blocker count equals discovered audio count; the index hash, record count, unique hash count, and failure manifest are reproducible.

### Row070 Canonical audio decode and technical metadata

Decode every supported asset to a canonical analysis representation while retaining original metadata. Record codec, duration, sample rate, channels, bit depth, channel layout, decode status, and canonical PCM hash.

Acceptance: decode results are deterministic; corrupt/unsupported files fail closed; no source file is rewritten.

### Row071 Waveform feature extraction

Compute loudness, true peak, RMS, crest factor, spectral centroid/bandwidth/rolloff, zero-crossing rate, dynamic range, noise floor, clipping, DC offset, and channel correlation.

Acceptance: features are versioned, unit-tested on fixtures, and calibrated across representative library strata.

### Row072 Onset, transient, and peak-anchor detection

Detect onset candidates, attack peak, maximum-energy peak, offset, confidence, and event density with at least two independently checkable methods for frame-exact candidates.

Acceptance: benchmark timing error meets the registered frame/sample threshold; ambiguous onsets remain multi-candidate or blocked.

### Row073 Silence, usable bounds, and natural decay analysis

Find leading/trailing silence, usable trim bounds, attack, sustain, release, noise-only tails, and natural decay boundaries without cutting audible tails.

Acceptance: trim suggestions preserve measured onset and decay; destructive trimming is never applied to source bytes.

### Row074 Multi-event segmentation

Detect and split recordings containing multiple footsteps, impacts, breaths, or repeated events into virtual segments with parent hash, sample ranges, overlap policy, and confidence.

Acceptance: segments are non-overlapping unless explicitly layered; each segment can be reproduced bit-exactly from the parent plus boundaries.

### Row075 Audio quality and defect classification

Classify clipping, hiss, hum, clicks, dropouts, codec damage, excessive noise, unintelligible speech contamination, severe pre-reverb, truncation, and unsuitable background layers.

Acceptance: defect labels include confidence and evidence; severe defects remove a candidate from production ranking without hiding it from the inventory.

### Row076 Dryness, reverberation, and room-tail estimation

Estimate direct-to-reverberant characteristics, decay time, early-reflection density, stereo room imprint, and whether additional convolution is safe.

Acceptance: already-wet assets cannot be double-reverberated without an explicit compatible-room rule.

### Row077 Semantic audio embeddings

Produce versioned audio embeddings and text-taxonomy embeddings for event, action, body part, material, footwear, object, environment, intensity, and acoustic descriptors.

Acceptance: embedding model/revision/hash and preprocessing are fixed; nearest-neighbor retrieval passes held-out semantic tests and cannot alone certify a sound.

### Row078 Audio tagging and caption ensemble

Generate structured tags and concise technical captions using an ensemble of path metadata, embeddings, tagging models, and deterministic acoustic features.

Acceptance: disagreements and unknown taxonomy remain explicit; no caption may overwrite source metadata.

### Row079 Fine-grained Foley taxonomy enrichment

Add body region, contact pair, footwear, gait phase, surface material, object material, force, attack, motion, room, and source perspective tags needed for examples such as heel-on-hardwood and hand-to-body contact.

Acceptance: every promoted Foley asset has required known fields or a documented `unknown` that prevents incompatible exact-match use.

### Row080 Vector and structured retrieval index

Build a content-addressed retrieval service combining metadata filters, lexical search, embedding similarity, and canonical-hash deduplication.

Acceptance: the same query/index revision returns the same ordered candidate set; stale index generations cannot mix.

### Row081 Weighted candidate scoring and explanation

Score candidates by event, source/target, material, body part, footwear, force, timing, duration, onset, acoustics, quality, rights, continuity, and cost.

Acceptance: every score component, normalization, weight, exclusion, and tie-break is recorded; missing mandatory fields fail closed.

### Row082 Repetition, diversity, and recent-use control

Implement deterministic cooldowns, near-duplicate penalties, actor/scene continuity, alternating-foot patterns, and bounded variation so repeated actions do not reuse an identical sample unnaturally.

Acceptance: repeated-event benchmarks prove diversity without semantic drift or continuity breaks.

### Row083 Retrieval confidence and fallback calibration

Calibrate thresholds for exact retrieval, approximate retrieval, layered synthesis, generated fallback, abstention, and review escalation.

Acceptance: held-out precision/recall and false-match rates are recorded per event family; low confidence cannot silently choose a sound.

### Row084 Canonical video decode and timeline normalization

Decode source frames, time bases, variable frame rate, cuts, missing frames, camera motion, and target audio sample clock into one canonical timeline.

Acceptance: frame-to-seconds-to-samples conversion round-trips within registered tolerances and survives mux replay.

### Row085 Actor, object, and body-region segmentation/tracking

Track actors, limbs, hands, feet, clothing regions, props, furniture, and surfaces across frames with persistent ownership IDs and occlusion/reappearance handling.

Acceptance: identity switches, lost tracks, and occlusion gaps are measured; unsupported ownership blocks certifying contact Foley.

### Row086 Pose, hand, foot, and gait-state extraction

Extract body/hand/foot landmarks, joint trajectories, gait phase, heel strike, sole contact, toe-off, hand approach, contact, release, and body recoil candidates.

Acceptance: frame-level events are confidence-scored and benchmarked against annotated clips; partial-body views do not fabricate hidden joints.

### Row087 Optical flow, velocity, acceleration, and force cues

Compute local and actor-relative motion, approach velocity, deceleration, impact acceleration proxies, sliding, scuffing, fabric movement, and camera-motion compensation.

Acceptance: force cues are calibrated as estimates, not physical ground truth; camera motion cannot become false actor motion.

### Row088 Depth, camera, and acoustic source position

Estimate relative/metric depth where supported, source-camera distance, screen azimuth/elevation, listener position, occlusion, and uncertainty.

Acceptance: spatial coordinates bind to the exact camera/take; uncalibrated monocular depth remains relative.

### Row089 Surface, object, clothing, and material recognition

Fuse scene registry, prompts, segmentation, image classification, texture evidence, and contact context to infer hardwood, carpet, tile, skin, fabric, leather, metal, glass, and other registered materials.

Acceptance: material decisions include provenance and confidence; visually ambiguous surfaces use broader classes or abstain.

### Row090 Contact inference and ownership authority

Infer source, target, body region, object/surface, onset, peak, release, duration, force band, visibility, and ownership from tracked masks, landmarks, depth, and motion.

Acceptance: actor-specific contact requires trusted ownership; candidate-only output is allowed when mask/contact authority is blocked, but certification is not.

### Row091 Timed visual audio-event manifest

Compile detected contacts, motion, ambience, dialogue, props, and scene transitions into a canonical event manifest with frame/sample anchors, confidence, expected layers, and silence decisions.

Acceptance: every event traces to visual/scene evidence; every visible required event is covered, intentionally silent, or explicitly blocked.

### Row092 Event uncertainty, conflict, and fallback policy

Resolve conflicting detectors, unknown materials, occluded contacts, crowded scenes, cuts, offscreen events, and confidence decay through deterministic policy.

Acceptance: uncertainty is never discarded; fallback route and certification ceiling are machine-readable.

### Row093 Canonical clip preparation

Create non-destructive derivatives with resampling, channel conversion, trim, event isolation, fades, gain staging, phase checks, and preserved natural decay.

Acceptance: derivatives record source hash and exact transforms; onset shift and tail loss remain within threshold.

### Row094 Layer construction and composite Foley synthesis

Combine compatible transient, body, clothing, object, settle, debris, and room components with deterministic gain/envelope rules.

Acceptance: each layer remains separately attributable and reconstructable; incompatible licenses or acoustic perspectives cannot combine.

### Row095 Spatial panning, distance, elevation, and occlusion rendering

Render source position, stereo/binaural pan, distance attenuation, air absorption, elevation cue, screen movement, occlusion filtering, and offscreen continuity.

Acceptance: moving-source tests match expected trajectories; phase, clipping, and loudness remain valid.

### Row096 Room acoustics and reflection rendering

Create or select room impulse responses from room geometry/materials, early reflections, RT60 targets, and listener/source positions; convolve dry sources and preserve room continuity.

Acceptance: measured output RT60 and early-reflection timing match target tolerance; wet sources follow compatibility rules.

### Row097 Timeline mixer, bus processing, and mux

Schedule sample-accurate events, ambience loops, dialogue ducking, buses, loudness, limiting, stems, final mix, and hash-bound video mux.

Acceptance: no clipping, missing stems, endpoint drift, frame loss, sample loss, or lineage ambiguity; mix is reproducible.

### Row098 Deterministic sound variation engine

Generate reusable variations through bounded pitch, duration, envelope, EQ, transient shaping, convolution, layering, microtiming, stereo perspective, and physically justified synthesis.

Acceptance: variants retain event identity, pass semantic similarity bounds, avoid canonical-PCM duplicates, preserve license provenance, and never modify originals.

### Row099 Neural text-to-audio generation router

Route structured event descriptions to registered text-to-audio engines when library retrieval is insufficient, generating multiple seeded candidates with exact engine/model/config provenance.

Acceptance: engine license and output-use rights pass; candidates meet duration, semantic, technical, and uniqueness gates before further use.

### Row100 Reference-conditioned audio-to-audio variation

Use an eligible source or approved generated seed for controlled audio-to-audio variation, inpainting, continuation, or style transfer with bounded strength.

Acceptance: source derivative rights pass; structural similarity and requested variation are measured; identity drift, unwanted speech/music, or timing loss rejects the candidate.

### Row101 Video-conditioned Foley generation

Generate complex continuous Foley candidates from video plus the canonical event script using registered MMAudio-compatible, HunyuanVideo-Foley-compatible, or future validated engines.

Acceptance: candidates are compared against deterministic event anchors and may supplement, not overwrite, trusted exact one-shots without an explicit blend decision.

### Row102 Generated-asset provenance and candidate staging

Store generated candidates outside the approved library with prompt/event manifest hashes, source hashes, engine identity, seed, environment, output hashes, rights, and QA state.

Acceptance: no generated file is reusable from the production selector until promoted; staging is an evidence boundary, not content suppression.

### Row103 Generated-sound autonomous QA

Evaluate decode integrity, duration, onset, event count, silence, clipping, loudness, spectral defects, semantic alignment, material/action fit, timing, diversity, source leakage, and acoustic suitability.

Acceptance: thresholds are calibrated on real reference sounds; no single model metric can grant production authority; failed candidates remain immutable negative evidence.

### Row104 Generated-asset promotion and reusable-library ingestion

Promote only passing generated sounds into a versioned generated-asset library with canonical tags, provenance, QA bundle, license, attribution, deduplication, and revocation status.

Acceptance: promoted assets are discoverable by the same selector as source assets while retaining generated origin; revocation removes eligibility without deleting evidence.

Current bounded implementation: the strict Row104 schema, frozen policy,
evaluator, and synthetic calibration suite now enforce accepted Row080/102/103
dependencies, exact rights/provenance/QA bindings, canonical tags, generated
origin, exact/near dedup decisions, content-addressed no-clobber publication,
selector visibility, and evidence-preserving revocation. Five deterministic
fixtures prove promotable-fixture isolation, rights/QA/exact-duplicate
rejection, justified near-duplicate handling, and revocation removal. No
generated PCM or live selector was mutated. Rows080, 102, and 103 remain held,
so Row104 library and runtime authority remain false pending one genuine
publication/discovery/revocation replay.

### Row105 End-to-end autonomous audio orchestrator

Implement the transaction coordinator from video/scene inputs through perception, event compilation, retrieval/generation, rendering, QA, retry, publication, and resumable failure recovery.

Acceptance: runs are idempotent, content-addressed, restartable, cost-bounded, and cannot skip a required gate.

### Row106 Automated event, mix, and AV QA matrix

Measure event coverage, false events, contact/transient offset, endpoint drift, semantic/material match, repetition, room consistency, clipping, loudness, dialogue masking, and full-duration defects.

Acceptance: fixture, synthetic, adversarial, and genuine-video tests pass; metrics link to exact media hashes.

### Row107 ComfyUI workflow and node integration

Expose bounded ComfyUI/API modules for analysis requests, event manifests, selector results, generated candidates, mix rendering, and QA while the external controller retains reasoning and authority.

Acceptance: workflows validate statically and at runtime; no giant monolithic graph; inputs/outputs use versioned schemas.

### Row108 Runtime, cache, batch, and cost controls

Implement local-first analysis, content-addressed feature/embedding caches, bounded GPU batches, EC2 selection only when justified, S3 transfer manifests, TTL/watchdog controls, and no-repeat proofs.

Acceptance: cache invalidation follows model/config hashes; interrupted batches resume; cost estimates and actuals are recorded.

### Row109 Benchmark, calibration, and adversarial corpus

Create representative annotated clips and audio fixtures for footsteps, heel strikes, body contacts, clothing, props, rooms, occlusions, multiple actors, cuts, ambiguous materials, and intentionally silent events.

Acceptance: train/calibration/test roles are separated; generated test artifacts cannot contaminate reference truth.

### Row110 Observability, replay, and defect diagnosis

Record stage timings, model versions, cache hits, candidate rankings, rejection reasons, transforms, mix decisions, QA scores, retries, and final authority in one replayable run ledger.

Acceptance: any released mix and promoted generated asset can be reconstructed or its exact external dependency blocker identified.

### Row111 Existing-component migration and compatibility

Integrate the current functional indexer, selector, Wave30 compiler/mixer, Wave31 force/spatial compilers, MMAudio proof, and Rows025-033 evaluators behind the new contracts without reopening completed proof.

Acceptance: legacy structural capabilities have explicit adapter status; known limitations remain visible; no duplicate implementation is created where a compatible component exists.

### Row112 Production acceptance and full-system certification

Run the complete acceptance matrix over multiple genuine videos, event families, rooms, actors, materials, library retrievals, deterministic variants, and neural generations.

Acceptance: all prerequisite rows pass; exact production artifacts, full-duration listening records, visual/contact review, AV sync, provenance, rights, global QA, and multimodal certification are present. Otherwise the row remains blocked with exact failing dependencies.

## Dependency phases

1. `control_and_inventory`: Rows067-070.
2. `audio_understanding`: Rows071-079.
3. `retrieval_intelligence`: Rows080-083.
4. `visual_event_intelligence`: Rows084-092.
5. `rendering_and_mix`: Rows093-097.
6. `sound_creation`: Rows098-104.
7. `orchestration_and_operations`: Rows105-111.
8. `certification`: Row112.

Rows may execute in parallel only when dependencies and shared runtime resources permit. Certification cannot move ahead of producer implementation.

## Generated-sound promotion states

```text
generated_candidate
-> technical_pass
-> semantic_pass
-> timing_pass
-> rights_pass
-> autonomous_qa_pass
-> playback_review_pass_when_required
-> promoted_reusable_asset
```

Rejected candidates remain hash-bound negative evidence. They are not deleted, renamed into success, or repeatedly regenerated under the same decision unit.

## Required evidence per row

- source citation and exact objective;
- implementation files and hashes;
- deterministic/unit/integration test results;
- runtime command/environment/model identity where applicable;
- input and output hashes;
- QA results and thresholds;
- license/provenance decision;
- pass, blocked, failed, or abstained classification;
- remaining blocker and exact next action.

## Main-session continuation rule

The main session should treat Rows067-112 as the complete reserved backlog for autonomous sound intelligence. It should batch three to five compatible implementation rows per protected PR, preserve current Row025-033 work, and update Items/Tracker only after implementation and evidence. It must not mark this package complete from the presence of these planning files.
