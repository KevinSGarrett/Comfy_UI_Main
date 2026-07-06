# Wave 00–19 Master Schedule

This is the controlling schedule for the cumulative hyper-realism image, video/GIF, and audio generation blueprint. Wave 00 is this foundation pack. Every later wave must update this same cumulative project root rather than producing isolated one-off notes.

## Wave 00 — Foundation Blueprint, Source Audit, and AI Project-Manager Contract

**Goal:** Create the cumulative blueprint pack, analyze uploaded Plans/current flow/tracker/chat context, define non-negotiable architecture decisions, and establish strict AI-runner acceptance rules.

**Purpose:** Give the AI project manager a grounded starting point before modifying workflows or adding nodes.

**Requirements:**
- Preserve this pack as the cumulative root for all future waves.
- Record current system findings, main-flow runtime boundaries, tracker status, and prior plan coverage.
- Define the target architecture as modular workflows plus an external pass planner/orchestrator, not one giant untestable graph.
- Create machine-readable schemas for pass plans, QA manifests, model registry entries, and scene requests.
- Require every future wave to update manifests, validation reports, and cumulative docs.

## Wave 01 — Repository Structure, Runtime Inventory, and Validation Harness

**Goal:** Create the build repository layout, inventory all workflows/models/custom nodes/scripts, and implement validation that prevents broken paths, bad JSON, missing nodes, and stale manifests.

**Purpose:** Stop workflow growth from becoming untraceable and make every change testable before expensive GPU execution.

**Requirements:**
- Create canonical folders for workflows, subgraphs, configs, schemas, registries, examples, tests, QA evidence, and releases.
- Implement validators for JSON parse, ComfyUI workflow format, missing node classes, missing model filenames, and duplicate IDs.
- Create object_info snapshot requirements from the live ComfyUI instance.
- Require a pass/fail validation report before any workflow can be promoted.
- Keep original uploaded flow read-only as source evidence.

## Wave 02 — Main Flow Deconstruction, Modularization, and Subgraph Strategy

**Goal:** Break the current main flow into production modules: base generation, refine, inpaint/detail, identity, control maps, upscale, QA, and video/audio handoff.

**Purpose:** Replace the giant catalog-style canvas with clean reusable execution modules and subgraphs.

**Requirements:**
- Separate active runtime lanes from disabled library/catalog nodes.
- Convert reusable lane groups into ComfyUI subgraphs where stable.
- Create API-format workflow templates for each production module.
- Remove catalog-only nodes from active production graphs; keep catalog registries outside the graph.
- Produce before/after graph inventory and reachability reports.

## Wave 03 — Engine Compatibility Registry and Multi-Engine Router

**Goal:** Build a router for Flux, SDXL/RealVisXL, Pony, SD1.5, Z-Image, and future engines, including model/LoRA compatibility and pass-role constraints.

**Purpose:** Prevent wrong-engine LoRA usage and allow specialty passes only where they belong.

**Requirements:**
- Create model_family, checkpoint, VAE, CLIP/text-encoder, LoRA, ControlNet, IPAdapter, video model, and audio provider registries.
- Tag every model/LoRA by engine, role, verified status, risk, preferred pass, and allowed mask scope.
- Block disabled/rejected review assets from automatic selection.
- Require engine transitions through decoded images unless a latent bridge is proven.
- Create router decisions with reason, selected module, fallback, and QA expectations.

## Wave 04 — Scene Request Schema, Character Bible, and Identity Reference System

**Goal:** Define how users describe characters, references, target traits, outfits, body proportions, skin details, and scene requirements.

**Purpose:** Make character accuracy repeatable without relying on one long prompt or random LoRA stacking.

**Requirements:**
- Create per-character IDs and character bibles for face, hair, body, outfit, skin, expression, and voice.
- Separate identity references from body-shape references, detail references, and pose/camera references.
- Define FaceID/IPAdapter/IPAdapter-face reference weights by pass and engine.
- Create identity QA requirements: face match, hair match, body silhouette match, outfit match, no identity drift.
- Require reference assets to have hashes, version tags, and target usage scopes.

## Wave 05 — Pose, Camera, Depth, and Control Map System

**Goal:** Create a control-map factory for DWPose/OpenPose, hand pose, face landmarks, depth, normal, Canny, lineart, segmentation preview, and camera framing.

**Purpose:** Solve pose/camera failures as geometry/control problems instead of prompt-only problems.

**Requirements:**
- Add preprocess workflows for pose, hands, face, depth, normal, Canny/lineart, and camera composition.
- Save all control maps with run IDs and hashes.
- Create strength schedules for base pass vs refine pass.
- Require pose/camera QA before body/detail passes run.
- Rerun base generation if pose, character count, or camera angle fails.

## Wave 06 — Mask Factory and Body-Part/Instance Segmentation

**Goal:** Create automatic and operator-correctable masks for people, per-character instances, face, hair, hands, torso, stomach, waist, hips, thighs, clothing, background, and contact zones.

**Purpose:** Make all local edits spatially controlled and prevent chopped-body artifacts.

**Requirements:**
- Implement person instance masks for character A/B/C/D/E.
- Implement body-part masks and mask overlays for QA.
- Add mask grow, erode, blur, feather, and falloff presets.
- Classify requested edits into small, medium, large, and contact masks.
- Require mask QA before inpaint/detail passes can modify the image.

## Wave 07 — Autonomous Pass Planner and ComfyUI API Orchestrator

**Goal:** Build the controller that converts a scene request into ordered passes, runs ComfyUI workflows through the API, collects outputs, runs QA, and selects reruns/repairs.

**Purpose:** Make the system know when to run first pass, second pass, third pass, etc.

**Requirements:**
- Implement pass_plan.schema.json and pass_plan_builder.
- Use ComfyUI API /prompt, /history, /object_info, /upload/image, and WebSocket progress tracking.
- Store every pass input, model selection, workflow hash, output hash, mask hash, and QA result.
- Implement rerun rules for pose, identity, body shape, hands, contact, mask bleed, and upscale artifacts.
- Never promote outputs directly from notes, catalog nodes, or unverified lanes.

## Wave 08 — Image Base Generation Lanes

**Goal:** Build reliable base-image generation modules for Flux-first, SDXL/RealVisXL, Z-Image, and fallback routes.

**Purpose:** Produce the correct character count, body silhouette, pose, camera, lighting, and composition before detail work starts.

**Requirements:**
- Implement Flux1-dev base as the preferred high-control base lane unless a router decision says otherwise.
- Add SDXL/RealVisXL base fallback and Z-Image exploratory lane.
- Restrict base LoRAs to zero to two neutral global LoRAs unless verified.
- Require base QA: character count, pose, camera, silhouette, identity, composition, and no major anatomy failures.
- Save approved base images and control maps for all downstream passes.

## Wave 09 — Image Refine and Specialty Engine Passes

**Goal:** Build low-denoise SDXL/RealVisXL/Pony/Flux specialty passes for improving realism without changing identity, pose, or body layout.

**Purpose:** Allow unique engine/model strengths without contaminating the full base image.

**Requirements:**
- Bridge engines through decoded images unless proven latent conversion exists.
- Implement full-image realism refine at low denoise and masked specialty refiners for engine-specific LoRAs.
- Add Pony only as a specialty pass unless proven as a base engine for the selected style.
- Require no identity swap, no pose change, no body merge, no style drift.
- Store before/after comparisons and reject overprocessed or waxy results.

## Wave 10 — Body Shape, Proportion, and Morphing Correction

**Goal:** Implement large-mask body correction passes for stomach, waist, hips, shoulders, thighs, body silhouette, and proportional targets.

**Purpose:** Fix body-shape accuracy with masks and control maps instead of prompt-only requests.

**Requirements:**
- Use large masks for silhouette/proportion corrections and small masks only for texture.
- Include surrounding anatomy and clothing seams in large masks to prevent chopped composites.
- Use depth/edge guidance for large body-shape edits.
- QA measurements must compare waist/hip/shoulder/stomach silhouette to target thresholds.
- Rerun base instead of inpainting when pose/camera/character count is fundamentally wrong.

## Wave 11 — Skin, Fabric, Cellulite, Blemish, and Surface Microdetail Lanes

**Goal:** Create masked detail passes for cellulite, pores, freckles, blemishes, fabric folds, compression marks, wetness/sweat/oil, makeup, hair strands, and clothing texture.

**Purpose:** Localize realism details to exact body parts/materials and stop detail LoRAs from bleeding globally.

**Requirements:**
- Use small/medium masks for texture and surface details.
- Map each requested surface detail to an allowed engine/model pass and target body/clothing region.
- Use low denoise for microdetail and require mask feathering.
- QA must prove details appear only inside the intended target region.
- Reject over-sharpened pores, smeared texture, fake plastic skin, hard mask edges, and detail bleed.

## Wave 12 — Face, Hands, Feet, and Hard-Anatomy Detailers

**Goal:** Build strict crop/detail/inpaint lanes for face, eyes, teeth, hairline, hands, fingers, nails, feet, toes, and other high-failure anatomy.

**Purpose:** Solve rough hands/faces through dedicated detailers, not global prompts.

**Requirements:**
- Use detector/crop/detailer workflows with mask overlays.
- Use hand pose/keypoint guidance where available.
- Restrict hand/body-part LoRAs to masked hand/detail passes.
- QA finger count, readable fingers, attachment, scale, symmetry, natural texture, and no fused/extra digits.
- Block promotion if contact hands fail strict visual QA.

## Wave 13 — Soft-Body Contact, Collision, Deformation, and Indentation Lanes

**Goal:** Build contact-zone workflows for hand/body/object interaction, skin compression, indentation, pull/push deformation, contact shadows, occlusion, and soft-body visual believability.

**Purpose:** Create visual soft-body realism as masked contact deformation passes with proof, not as global physics prompts.

**Requirements:**
- Build combined masks: hand/object mask + target body area + contact zone + falloff region.
- Use pose/depth/normal guidance to lock contact geometry and prevent body penetration.
- Add contact-shadow and compression detail prompts only inside bounded masks.
- QA must inspect contact crops for readable hands, plausible pressure, no merged anatomy, no impossible collision.
- If contact geometry fails, rerun pose/base or contact pass; do not upscale failed contact.

## Wave 14 — Multi-Character Scene Graph, Layout, and Reference Isolation

**Goal:** Create robust 1–5 character scene control with per-character IDs, references, masks, regions, depth order, pose, gaze, expression, outfit, and identity locks.

**Purpose:** Prevent multiple characters from merging into one body and make each person controllable.

**Requirements:**
- Never treat multi-character scenes as one giant prompt.
- Create per-character prompt blocks and per-character reference/mask bindings.
- Use instance masks and layout bounding regions for every character.
- QA character count, region occupancy, identity isolation, depth order, and no body-part merge.
- Require rerun of layout/base pass when character count or separation fails.

## Wave 15 — Multi-Character Interaction, Occlusion, and Object/Prop Handling

**Goal:** Add character-to-character and character-to-object interaction control, object continuity, handoffs, occlusion, grip, contact points, and scene-graph timeline events.

**Purpose:** Make interactions believable without body/limb merging.

**Requirements:**
- Bind every interaction to source entity, target entity/object, body part, contact zone, and timing.
- Use interaction masks and depth/occlusion maps before detail passes.
- Track object identity, position, scale, and hand contact across image/video frames.
- QA interaction crops for each contact pair and object/hand relationship.
- Reject merged people, duplicated objects, impossible handoffs, and incorrect occlusion.

## Wave 16 — Video/GIF Keyframe Motion Planner and Temporal Control Maps

**Goal:** Build still-to-motion workflows using approved keyframes, pose/depth/mask timelines, interpolation, GIF/MP4/WebM export, and motion-state planning.

**Purpose:** Approximate motion and soft-body changes without requiring a reference video or 3D simulation, while being honest that it is not true simulation.

**Requirements:**
- Create keyframes for neutral, contact, compression peak, release, and settle states.
- Generate/interpolate pose, depth, normal, and masks per keyframe.
- Support GIF as a frame-sequence export target and MP4/WebM for quality playback.
- QA every frame for identity, pose, hand/contact, deformation, flicker, and temporal consistency.
- Use frame repair passes for failed frames instead of regenerating the full clip when possible.

## Wave 17 — Video Engine Routing, Frame Repair, and Temporal QA

**Goal:** Integrate Wan, HunyuanVideo, LTXV, AnimateDiff/fallback lanes, frame repair, optical-flow/landmark checks, and video QA scorecards.

**Purpose:** Turn still-image control into production video/GIF routing with measurable quality gates.

**Requirements:**
- Route video jobs based on duration, motion complexity, available models, VRAM, identity risk, and target format.
- Maintain per-frame control maps and per-frame metadata.
- Add temporal QA for flicker, identity drift, body drift, hand drift, contact drift, and background instability.
- Repair or reject frames that fail crop-level QA.
- Require final video/GIF manifest with frame hashes, model decisions, and QA results.

## Wave 18 — Audio Generation: Dialogue, Voice, SFX, Foley, Ambience, Music

**Goal:** Build audio planning and generation lanes for dialogue/speech, voice profile consistency, foley, SFX, ambience, room tone, and music cues.

**Purpose:** Make audio generation part of the same scene graph rather than an afterthought.

**Requirements:**
- Bind each speech line to character ID, emotion, pacing, timing, and mouth region.
- Bind foley/SFX cues to motion/contact/object events.
- Create audio router decisions for speech, SFX/foley, ambience, music, and room tone.
- Create manifests for generated or selected audio assets without storing credentials or private/licensed content.
- QA voice consistency, timing, clipping risk, cue purpose, and dialogue intelligibility.

## Wave 19 — AV Sync, App Mode Front-End, End-to-End Release, and Production Promotion

**Goal:** Assemble the full App Mode/operator interface, orchestrator integration, AV sync/mix timeline, release gates, documentation, tests, and cumulative production package.

**Purpose:** Deliver the complete AI-operated hyper-realism system with strict end-to-end proof.

**Requirements:**
- Expose only high-level controls in ComfyUI App Mode and keep orchestration logic outside the graph.
- Create master AV sync timeline for video, speech, lip-sync, gestures, SFX/foley, ambience, and mix.
- Run end-to-end still, GIF/video, and audio test scenes.
- Generate final QA sheets, manifests, evidence reports, checksums, and promotion decision.
- Block release unless all critical gates pass and all known limitations are recorded.
