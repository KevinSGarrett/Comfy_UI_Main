#!/usr/bin/env python3
"""Build or check the additive Wave64 Rows149-220 planning sidecars.

The default mode is read-only check. Use --write explicitly to materialize files.
This script never edits Rows001-148 or any canonical package manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Iterable


STATUS = "Planned_Autonomous_Implementation_Required"
PACKAGE_ID = "wave64_ultimate_modular_character_to_multimodal_workflow_rows149_220"
AUTHORITY_REL = Path("Plan/00_PROJECT_CONTROL/WAVE64_ULTIMATE_MODULAR_CHARACTER_TO_MULTIMODAL_WORKFLOW_MASTER_PLAN.md")
CANONICAL_PROJECT_ROOT = PureWindowsPath("C:/Comfy_UI_Main")
CANONICAL_PLAN_ROOT = str(CANONICAL_PROJECT_ROOT / "Plan")

PRESERVATION_STATIC_PATHS = [
    "Plan/00_PROJECT_CONTROL/WAVE64_ULTIMATE_MODULAR_CHARACTER_TO_MULTIMODAL_WORKFLOW_MASTER_PLAN.md",
    "Plan/02_TARGET_ARCHITECTURE/WAVE64_ULTIMATE_CHARACTER_TO_MULTIMODAL_CONTROL_PLANE_ARCHITECTURE.md",
    "Plan/02_TARGET_ARCHITECTURE/WAVE64_PASS_LEVEL_ENGINE_MODEL_SPECIALIZATION_ARCHITECTURE.md",
    "Plan/03_IMAGE_SYSTEM/WAVE64_FIRST_PASS_AND_SPECIALIST_MULTIPASS_ENGINE_ROUTING_STRATEGY.md",
    "Plan/Instructions/ULTIMATE_MODULAR_MULTIMODAL_WORKFLOW_IMPLEMENTATION_AND_OPERATION_PROTOCOL.md",
    "Plan/Instructions/QA/ULTIMATE_MODULAR_MULTIMODAL_WORKFLOW_QA_AND_PROMOTION_PROTOCOL.md",
    "Plan/Instructions/QA/PASS_LEVEL_ENGINE_MODEL_ROUTING_QA_PROTOCOL.md",
    "Plan/Instructions/Hydration_Rehydration/ULTIMATE_MULTIMODAL_WORKFLOW_MAIN_SESSION_HANDOFF.md",
    "Plan/08_SCHEMAS/multimodal_contract_common.schema.json",
    "Plan/08_SCHEMAS/character_package_revision.schema.json",
    "Plan/08_SCHEMAS/scene_package.schema.json",
    "Plan/08_SCHEMAS/shot_pose_package.schema.json",
    "Plan/08_SCHEMAS/mask_factory_binding.schema.json",
    "Plan/08_SCHEMAS/engine_model_capability_card.schema.json",
    "Plan/08_SCHEMAS/engine_execution_stack_card.schema.json",
    "Plan/08_SCHEMAS/multimodal_pass_route_request.schema.json",
    "Plan/08_SCHEMAS/multimodal_pass_route_decision.schema.json",
    "Plan/08_SCHEMAS/cross_engine_bridge_contract.schema.json",
    "Plan/08_SCHEMAS/specialist_pass_contract.schema.json",
    "Plan/08_SCHEMAS/multimodal_pass_dag.schema.json",
    "Plan/08_SCHEMAS/multimodal_artifact_manifest.schema.json",
    "Plan/08_SCHEMAS/multimodal_orchestrator_event.schema.json",
    "Plan/08_SCHEMAS/autonomous_multimodal_job.schema.json",
    "Plan/08_SCHEMAS/examples/wave64_single_character_flux_to_sdxl_specialist.example.json",
    "Plan/08_SCHEMAS/examples/wave64_two_character_ownership_and_mask_binding.example.json",
    "Plan/08_SCHEMAS/examples/wave64_video_segment_route_and_span_repair.example.json",
    "Plan/08_SCHEMAS/examples/wave64_audio_stems_and_av_job.example.json",
    "Plan/10_REGISTRIES/wave64_multimodal_engine_model_capability_registry.json",
    "Plan/10_REGISTRIES/wave64_ultimate_multimodal_workflow_work_package_registry.json",
    "Plan/07_IMPLEMENTATION/scripts/build_wave64_ultimate_multimodal_workflow_control_package.py",
    "Plan/07_IMPLEMENTATION/scripts/validate_wave64_pass_level_engine_model_routing.py",
    "Plan/Instructions/QA/Scripts/test_wave64_ultimate_multimodal_workflow_control_package.py",
    "Plan/Instructions/QA/Scripts/test_wave64_pass_level_engine_model_routing.py",
    "Plan/Items/README.md",
    "Plan/Tracker/README.md",
    "Plan/Items/Waves/Wave64/README.md",
    "Plan/Tracker/Waves/Wave64/README.md",
    "Plan/Instructions/WAVE_NAMESPACE_AND_SEQUENCE_CONTROL.md",
]

BASELINE_PRESERVED_PATHS = [
    "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ITEM_ROWS.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_TRACKER_ROWS.csv",
    "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv",
    "Plan/02_TARGET_ARCHITECTURE/MODULAR_CHARACTER_TO_MULTIMODAL_MEDIA_ORCHESTRATION_ARCHITECTURE.md",
]

ITEM_HEADER = [
    "Item_ID", "Item_Wave", "Item_Type", "Item_Title", "Item_Category", "Item_Domain",
    "Owner_Domain", "Autonomous_Required", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Action", "Implementation_Target", "Deliverable_Type", "Acceptance_Criteria",
    "QA_Gates_Required", "Visual_Review_Required", "Visual_Review_Method", "Test_Required",
    "Evidence_Required", "Runtime_Proof_Required", "EC2_Allowed", "Blocker_Policy",
    "Source_Plan_Root", "Citation_File", "Citation_Full_Path", "Citation_Section",
    "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt", "Source_Package",
    "Source_Type", "Source_File_Size", "Priority", "Risk_Level", "Status", "Created_From",
    "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level", "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record"
]

TRACKER_HEADER = [
    "Tracker_ID", "Wave", "Phase", "Workstream", "Priority", "Risk_Level", "Owner_Role",
    "Environment", "Status", "Task_Name", "Detailed_Action", "Completion_Criteria",
    "Acceptance_Evidence", "Dependency_Prerequisite", "Validation_Method", "Output_Artifact",
    "Source_Path", "Related_Source_Paths", "Package_Top_Level_Directory",
    "Autonomous_Execution_Mode", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Desktop_Action", "QA_Strictness", "Visual_Review_Required", "Visual_Review_Method",
    "Test_Required", "Runtime_Proof_Required", "EC2_Allowed", "Preview_Required",
    "Final_Render_Gate", "Evidence_Path", "Citation_File", "Citation_Full_Path",
    "Citation_Section", "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt",
    "Source_Package", "Source_Type", "Source_Item_ID", "Blocker_Policy", "Rerun_Policy",
    "Status_Decision", "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level",
    "Coverage_Audit_Status", "Ultra_Source_Coverage_Record"
]


@dataclass(frozen=True)
class PlanRow:
    number: int
    workstream: str
    domain: str
    category: str
    section: str
    title: str
    action: str
    acceptance: str
    dependencies: tuple[int, ...]
    runtime_proof: bool = True
    review: str = "structured evidence review"
    priority: str = "P0"
    risk: str = "CRITICAL"


ROWS: list[PlanRow] = []


def add4(code: str, domain: str, category: str, section: str, entries: Iterable[tuple]) -> None:
    for entry in entries:
        number, title, action, acceptance, dependencies, runtime, review = entry
        ROWS.append(PlanRow(number, code, domain, category, section, title, action, acceptance, tuple(dependencies), runtime, review))


add4("W64-MCM-GOV", "governance_and_authority", "program_control", "Decision and authority", [
    (149, "Modular Media Program Charter", "Freeze the external control plane, modular ComfyUI execution boundary, App Mode role, registry authority, MaskFactory boundary, and monolithic-graph prohibition.", "Every component has one explicit responsibility and contract; the package extends rather than rewrites Rows001-148.", [2, 4, 35, 66, 112, 148], False, "architecture and traceability review"),
    (150, "Decision and Promotion Authority Matrix", "Assign proposal, validation, execution, QA, promotion, revocation, and rollback authority for packages, passes, attempts, and artifacts.", "Every state transition has one final authority and no LLM or VLM can self-promote.", [35, 49, 59, 63, 66, 149], True, "representative image, video, and audio decision-packet review"),
    (151, "Row Namespace and Non-Overlap Gate", "Reserve Rows149-220 and bind each row to one workstream, target, deliverable, and evidence class.", "Exactly 72 unique rows exist in eighteen four-row workstreams with no completion claim or collision.", [1, 50, 51, 57, 58, 149, 150], False, "structural review"),
    (152, "Revision, Exception, and Supersession Control", "Define immutable revisions, compatibility windows, exception records, deprecation, supersession, rollback, and revocation.", "No record is silently mutated; every exception is bounded, evidence-linked, reversible, and historically traceable.", [43, 47, 48, 49, 54, 59, 149, 150, 151], True, "lineage and rollback review"),
])

add4("W64-MCM-PKG", "canonical_ids_and_packages", "contracts", "Canonical products", [
    (153, "Canonical Entity ID and Relationship Model", "Define durable IDs for characters, revisions, scenes, shots, takes, instances, poses, masks, passes, attempts, routes, stacks, artifacts, events, runs, and QA decisions.", "IDs are immutable, collision-tested, reference-valid, and distinguish reusable characters from shot instances.", [4, 51, 54, 149, 150, 151, 152], True, "schema and relationship review"),
    (154, "Canonical Character Package Envelope", "Define identity, morphology, surface, wardrobe, accessory, voice, reference, adapter, benchmark, rights, and QA sections.", "The package contains no fixed node IDs or character paths; all production assets and revisions are hash-bound.", [10, 44, 51, 114, 115, 116, 117, 153], True, "reference contact sheet and voice-sample review"),
    (155, "Scene, Shot, Pose, and Pass Package Envelopes", "Define camera, framing, instance, skeleton, depth, contact, timing, audio-event, mask, protection, and pass-objective contracts.", "A pass compiles without hidden state and every target belongs to a scene, shot, take, and owner instance.", [8, 11, 19, 25, 51, 122, 153, 154], True, "pose, depth, ownership, and event-timeline review"),
    (156, "Artifact, Evidence, and Lineage Envelope", "Define parent hashes, transforms, stack/workflow hashes, attempts, runtime bindings, QA decisions, promotion, revocation, and replay data.", "Every output is reproducible or explainable from immutable parents and version-compatible decisions.", [43, 51, 54, 59, 62, 153, 154, 155], True, "image, video, and audio evidence-envelope review"),
])

add4("W64-MCM-CHAR", "character_factory", "character_system", "Character Package Revision", [
    (157, "Character Reference Intake and Identity Core", "Build reference intake, view coverage, quality grading, identity traits, proportions, marks, and voice-reference binding.", "Accepted/rejected references, coverage gaps, conflicts, hashes, and authority are explicit.", [10, 44, 114, 115, 116, 117, 154], True, "core_autonomous_runtime face/body validators plus qualified voice-reference similarity and intelligibility critics; human listening is optional independent_perceptual_calibration"),
    (158, "Modular Character State System", "Separate morphology, skin/surface, hair, makeup, wardrobe, accessory, material, and voice states from immutable identity.", "States are independently versioned, ownership-tagged, composable, and identity-preserving.", [10, 13, 14, 15, 114, 125, 157], True, "before/after state panels and relevant voice playback"),
    (159, "Engine-Specific Character Adapter Builder", "Publish FLUX-family, SDXL-family, edit, video, and audio adapter cards for one Character Package revision.", "Each adapter declares exact engine family, triggers, limits, hashes, calibration evidence, and prohibited pairings.", [9, 20, 26, 44, 117, 118, 157, 158], True, "cross-engine identity and voice-similarity review"),
    (160, "Character Revision Certification and Publication", "Certify and publish immutable Character Package revisions for solo and multi-character consumption.", "Identity, morphology, views, states, voice, adapters, and separation pass; failures remain staged and revocable.", [16, 17, 18, 35, 59, 131, 132, 157, 158, 159], True, "full character contact sheet, separation panel, and voice-continuity review"),
])

add4("W64-MCM-SHOT", "shot_pose_and_multi_character_ownership", "scene_and_pose", "Shot/Pose Package", [
    (161, "Scene-to-Shot and Pose Package Compiler", "Compile intent into camera, lens, framing, per-instance keypoints/keyframes, timing, safe margins, and expected audio events.", "One reusable package serves image, mask, video, audio, and AV without flattening ownership.", [11, 22, 86, 87, 88, 89, 90, 91, 92, 122, 155, 160], True, "skeleton, camera, framing, and timing-overlay review"),
    (162, "Per-Instance Ownership and Isolation Registry", "Assign every instance its character revision, skeleton, depth, silhouette, masks, protected regions, objects, wardrobe, and voice.", "No edit, mask, prop, dialogue line, control, or artifact is ambiguously owned.", [10, 85, 90, 134, 153, 160, 161], True, "color-coded ownership and active-speaker review"),
    (163, "Contact, Occlusion, and Depth Interaction Planner", "Encode person/person, person/object, body/support, wardrobe, visibility, occlusion, collision, and timed contact.", "Every contact declares participants, regions, timing, force class, visibility, ownership, and expected deformation.", [15, 28, 86, 87, 88, 89, 90, 91, 92, 161, 162], True, "contact, depth, pressure, and occlusion review"),
    (164, "Pose and Ownership Conformance Gate", "Validate outputs against pose, framing, ownership, contact, and protected-region contracts and issue scoped repairs.", "Wrong-person edits, swaps, pose drift, ownership leakage, and ambiguous occlusion block promotion.", [10, 11, 12, 13, 14, 15, 16, 17, 18, 21, 34, 161, 162, 163], True, "whole-frame and per-instance review"),
])

add4("W64-MCM-ROUTE", "per_pass_engine_model_routing", "engine_model_routing", "Per-pass engine/model specialization", [
    (165, "Unified Per-Pass Capability Registry", "Register exact engine/model/adapter capabilities by modality, intent, region, controls, references, edit mode, resolution, hardware, and evidence.", "A one-engine specialist is discoverable only for its certified pass scope and never becomes a universal default.", [9, 20, 26, 44, 54, 99, 118, 159], True, "capability calibration artifact review"),
    (166, "Hard Compatibility and Constraint Solver", "Reject engine, model, VAE, encoder, latent, adapter, control, node, workflow, license, hardware, authority, and package incompatibilities before ranking.", "No incompatible stack reaches execution; every rejection returns typed unmet constraints and missing evidence.", [36, 44, 46, 51, 54, 65, 66, 165], True, "referenced capability-evidence review"),
    (167, "Contextual Candidate Ranking and LLM Proposal", "Rank only eligible stacks by matching quality, preservation, stability, failure rate, runtime, memory, cost, and cache evidence.", "Ranking inputs are replayable and explainable; an LLM proposal cannot bypass compatibility or promotion gates.", [35, 63, 64, 81, 82, 83, 118, 123, 165, 166], True, "core_autonomous_runtime deterministic blinded candidate IDs plus qualified calibrated critic ranking; human side-by-side review is optional independent_perceptual_calibration"),
    (168, "Fallback, Abstention, and Route Decision Record", "Define explicit fallback, abstention, material-hypothesis retry, supersession, and immutable route-decision provenance.", "No eligible stack yields a typed blocker; every reroute explains the prior failure and no silent substitution or seed loop occurs.", [49, 59, 63, 66, 83, 165, 166, 167], True, "fallback media review only when certifying fallback quality"),
])

add4("W64-MCM-BRIDGE", "first_pass_and_cross_engine_bridging", "engine_bridges", "Cross-engine bridge", [
    (169, "First-Pass Intent Classifier and Engine Selector", "Classify composition, identity, pose, edit, character-count, motion, downstream specialist, quality, and resource needs before base routing.", "The first pass is objective-driven and declares downstream bridge needs; FLUX is a candidate rather than a hardcoded answer.", [8, 9, 10, 11, 19, 20, 155, 161, 165, 166, 167, 168], True, "base composition and identity comparison panels"),
    (170, "Canonical Decoded Artifact Bridge", "Standardize decoded image/frame/audio transfer, color/sample space, alpha, dimensions, coordinates, timebase, masks, crops, transforms, and hashes.", "Cross-engine round trips preserve coordinates, timing, color, ownership, and lineage; latent transfer blocks absent exact certification.", [9, 20, 36, 43, 51, 156, 169], True, "image difference maps and audio alignment/null checks"),
    (171, "Cross-Engine Conditioning Translator", "Translate prompts, references, pose, depth, masks, controls, denoise, scheduler, and adapter semantics into engine-native contracts.", "Raw settings are never copied blindly and every translation is versioned and testable.", [9, 20, 44, 54, 64, 165, 166, 167, 168, 169, 170], True, "engine-pair conditioning fidelity review"),
    (172, "First-Pass-to-Specialist Bridge Qualification", "Benchmark and certify base/specialist engine pairings inside exact capability and resource buckets.", "A pairing promotes only when identity, geometry, regional fidelity, seams, preservation, and whole-artifact regression pass.", [16, 17, 18, 21, 33, 34, 37, 38, 169, 170, 171], True, "core_autonomous_runtime deterministic cross-engine metrics plus qualified calibrated critics over blinded engine IDs; human comparison is optional independent_perceptual_calibration"),
])

add4("W64-MCM-REGION", "specialist_regional_passes", "specialist_passes", "Image multipass order", [
    (173, "Specialist Pass Catalog", "Define pass intents for face/eyes, hands/feet, anatomy, skin, hair, fabric, accessories, materials, contact, pressure, and deformation.", "Each entry binds capability tags, eligible exact stacks, inputs, outputs, preservation risks, and QA gates.", [13, 14, 15, 44, 64, 165, 166, 167, 168, 169, 170, 171, 172], True, "specialist calibration panels"),
    (174, "Regional Edit and Protected-Region Contract", "Bind target owner/mask, protected masks, crop/pad/feather, resolution, denoise bounds, transforms, recomposition, and parent artifact.", "No localized pass executes without trusted ownership and invertible preservation constraints.", [12, 17, 34, 85, 90, 162, 170, 173], True, "mask overlays, seams, and unaffected-region comparison"),
    (175, "Defect-to-Hypothesis Repair Planner", "Translate a classified defect into one bounded specialist hypothesis, exact route, changed variables, and retry budget.", "Retries materially differ, address the cause, preserve accepted parents, and stop on exhaustion or worsening evidence.", [23, 34, 63, 167, 168, 173, 174], True, "before/after target and whole-artifact review"),
    (176, "Regional Reintegration and Global Regression Gate", "Reintegrate accepted specialist output and evaluate color, grain, sharpness, geometry, identity, ownership, temporal, and audio continuity.", "Local improvement cannot promote when any protected owner, region, span, stem, or whole artifact regresses.", [16, 17, 18, 21, 32, 33, 34, 43, 174, 175], True, "mandatory localized and whole-artifact review"),
])

add4("W64-MCM-MASK", "maskfactory_integration", "mask_system", "MaskFactory integration", [
    (177, "MaskFactory Mode A Approved-Package Reader", "Read approved packages and validate image/parent hash, person index, ontology, coordinates, transforms, mask type, truth tier, provider, and certificate.", "Only certificate-authorized masks support promotion; visible truth and derived/non-truth remain distinguished and mismatches fail closed.", [12, 153, 154, 155, 156, 162, 174], True, "mask overlay and boundary review"),
    (178, "MaskFactory Mode B Live Draft Client", "Implement health, predict, refine, timeout, retry, champion-model, confidence, and provenance contracts for live MaskFactory access.", "Live results remain drafts at their certified authority and service absence never silently falls back to untrusted masks.", [12, 168, 177], True, "draft mask overlay review"),
    (179, "Normalized Mask Adapter and Arbitration Contract", "Normalize Mode A and Mode B outputs while preserving taxonomy, transforms, owner, source, truth tier, certificate, and disagreement.", "Mode B cannot overwrite stronger Mode A authority and every union/intersection/refinement is explicitly derived.", [43, 51, 62, 174, 177, 178], True, "comparative boundary and protected-region overlay review"),
    (180, "Mask Availability and Promotion Integration Gate", "Bind mask readiness to compilation, blocking, execution, repair, QA, and promotion without blocking unrelated DAG branches.", "Offline service, unknown taxonomy, ambiguous owner, stale certificate, or transform mismatch produces a typed dependent-pass blocker.", [35, 37, 38, 49, 59, 63, 177, 178, 179], True, "final mask and edited-artifact review"),
])

add4("W64-MCM-IMAGE", "modular_image_production", "image_pipeline", "Image multipass order", [
    (181, "Dynamic Image Pass-DAG Compiler", "Compile Character, Shot/Pose, route, bridge, specialist, and mask contracts into a minimal resumable image DAG.", "Only needed passes exist; accepted parents are immutable and dependencies, budgets, writes, protections, and gates are explicit.", [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 36, 51, 54, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180], True, "compiled DAG and expected-output review"),
    (182, "Versioned Image Workflow Module Library", "Parameterize composition, identity, pose/depth, realism, regional repair, material, upscale, and export workflows with stable patch points.", "Modules are API-compatible and contain no fixed character names, hidden paths, or orchestration decisions.", [8, 9, 36, 37, 64, 65, 66, 181], True, "one certified output panel per promoted module"),
    (183, "Single- and Multi-Character Image Vertical Slices", "Execute one complete single-character run then a two-character ownership/contact run with scoped repairs.", "Both runs resume, preserve identity/ownership, and rerun only failed regions using bounded causal hypotheses.", [10, 11, 12, 13, 14, 15, 16, 17, 18, 160, 161, 162, 163, 164, 181, 182], True, "whole-frame, per-character, pose, contact, and regional review"),
    (184, "Image Artifact Reproducibility and Promotion Gate", "Bind images to packages, prompts, seeds, models, workflows, masks, transforms, attempts, runtime, scorecards, and revocation.", "Only target/protected/whole-frame threshold-passing outputs become immutable accepted parents or promoted artifacts.", [16, 17, 18, 33, 34, 35, 43, 59, 156, 176, 181, 182, 183], True, "mandatory independent full-resolution image review"),
])

add4("W64-MCM-VIDEO", "modular_video_production", "video_pipeline", "Video, audio, and AV", [
    (185, "Approved Keyframe and Shot-to-Video Adapter", "Convert accepted images plus character, camera, pose, depth, contact, and timing contracts into video-engine requests.", "Requests retain shot/instance authority and reject unapproved or incompatible keyframes.", [19, 20, 21, 22, 155, 156, 160, 161, 162, 163, 164, 184], True, "keyframe, request, and first-frame comparison"),
    (186, "Segment-Level Video Engine and Model Routing", "Route generation, continuation, interpolation, motion control, and span repair independently by certified capability.", "Each segment has a route, overlaps/transitions, temporal constraints, resource envelope, and explicit fallback.", [19, 20, 21, 22, 23, 165, 166, 167, 168, 169, 170, 171, 172, 185], True, "motion, transition, camera, identity, and ownership review"),
    (187, "Temporal Identity and Failed-Span Repair", "Detect identity drift, ownership swap, structural/contact errors, flicker, and discontinuity and repair only the causal span.", "Accepted spans remain immutable and repaired boundaries reconnect without temporal, identity, or timing regression.", [21, 23, 164, 175, 176, 185, 186], True, "frame strip, playback, flow, contact, and boundary review"),
    (188, "Video/GIF Promotion and Export Package", "Package final video/GIF, frames, timebase, provenance, QA, repairs, encodes, and export variants.", "Frame count, duration, FPS, loop/export, lineage, playback, and temporal scorecards pass before promotion.", [19, 20, 21, 22, 23, 24, 33, 34, 35, 59, 156, 184, 185, 186, 187], True, "mandatory complete playback and loop review"),
])

add4("W64-MCM-AUDIO", "audio_workflow_integration", "audio_pipeline", "Video, audio, and AV", [
    (189, "Shot-to-Audio Intent and Event Binding", "Bind shot events, character voices, dialogue, contacts, environment, distance, room, and timing to existing sound and speech authorities.", "Rows067-148 are reused without duplicating their indexing, generation, voice, alignment, or certification scope.", [25, 26, 27, 28, 29, 30, 31, 32, 67, 112, 113, 148, 155, 161, 162, 163], True, "timeline and event/dialogue ownership review"),
    (190, "Modular Audio Workflow Adapter Library", "Compose speech, nonverbal vocalization, Foley, ambience, music, room, spatial, enhancement, and mix adapters under one contract.", "Every adapter declares exact package versions, stack requirements, stems, timebase, provenance, and QA gates.", [25, 26, 27, 28, 29, 30, 31, 32, 93, 108, 123, 146, 165, 166, 167, 168, 169, 170, 171, 172, 189], True, "core_autonomous_runtime isolated-stem and complete-mix signal validators plus qualified audio critics; human listening is optional independent_perceptual_calibration"),
    (191, "Audio Execution, Alignment, and Lineage Pipeline", "Execute bounded candidates, align events and speech, render space/room, mix buses, and preserve sample-level lineage.", "Every sample span is attributable to event/source/character/attempt/transform/mix decisions and failed stems are independently replaceable.", [97, 102, 103, 104, 105, 106, 135, 136, 137, 138, 139, 140, 156, 189, 190], True, "headphone/speaker playback and waveform review"),
    (192, "Audio Package Promotion and Revocation Gate", "Apply identity, prosody, timing, acoustics, defect, full-audio, continuity, provenance, promotion, and revocation gates.", "Only complete synchronized packages promote and local stem gains cannot hide global audio regression.", [27, 28, 29, 30, 31, 32, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 131, 148, 176, 189, 190, 191], True, "core_autonomous_runtime full-duration deterministic audio QA plus qualified calibrated critics and signed policy; human listening is optional independent_perceptual_calibration"),
])

add4("W64-MCM-AV", "audiovisual_assembly", "av_pipeline", "Video, audio, and AV", [
    (193, "Canonical AV Timeline and Clock Authority", "Define master timebase, frame/sample conversion, cuts, dialogue, events, offsets, handles, and ownership.", "All streams resolve to one monotonic clock without cumulative drift or ambiguous event ownership.", [30, 84, 91, 97, 122, 135, 155, 188, 189, 190, 191, 192], True, "timeline, waveform, and frame-marker review"),
    (194, "Provenance-Preserving AV Assembly and Mux", "Assemble only accepted video and audio while retaining stems, captions, metadata, codecs, hashes, and source lineage.", "Mux never substitutes unapproved media and all streams, durations, hashes, and manifests reconcile.", [30, 97, 105, 106, 156, 188, 192, 193], True, "full audiovisual playback review"),
    (195, "Localized AV Sync Diagnosis and Repair", "Classify lip, event, drift, offset, source-timing, and mux defects and repair the smallest authoritative span or stem.", "Repair avoids unnecessary regeneration and always triggers complete AV regression review.", [30, 32, 34, 135, 136, 137, 138, 139, 140, 175, 176, 193, 194], True, "normal-speed and diagnostic slow-motion before/after review"),
    (196, "Final AV Artifact Certification Package", "Package video, audio, stems, timeline, captions, hashes, QA, playback, decisions, and rollback/revocation instructions.", "Independent synchronization, identity, continuity, technical, provenance, and full-playback gates all pass.", [33, 34, 35, 59, 60, 106, 112, 148, 184, 188, 192, 193, 194, 195], True, "mandatory end-to-end visual and audio review"),
])

add4("W64-MCM-ORCH", "orchestrator_and_event_store", "control_plane", "Control plane", [
    (197, "Planner, Validator, Executor, and Promoter Separation", "Implement explicit services for proposal, deterministic validation, routing, scheduling, execution, QA observation, policy, and promotion.", "No service silently assumes another authority and every contract/state transition is versioned and replayable.", [2, 35, 48, 49, 50, 51, 54, 62, 63, 149, 150, 151, 152, 153, 154, 155, 156, 165, 166, 167, 168, 196], True, "representative decision-packet review"),
    (198, "Immutable Run and Event Store Schema", "Persist jobs, runs, DAGs, passes, edges, attempts, hypotheses, artifacts, routes, blockers, QA, promotion, and rollback events.", "Append-only events reconstruct exact projections with referential integrity, hashes, idempotency, and no lost terminal state.", [43, 51, 62, 153, 156, 197], True, "artifact previews and playback linked from reconstructed state"),
    (199, "Resumable DAG Scheduler and Hypothesis Retry Engine", "Schedule ready passes, enforce dependency/resource/retry budgets, classify failures, and choose material repair hypotheses.", "Crash or failure resumes without duplicate promotion, unexplained seed loops, accepted-parent mutation, or successful-branch reruns.", [23, 48, 63, 168, 175, 181, 197, 198], True, "repaired-media and retained-parent comparison"),
    (200, "Runtime Reconciliation and Recovery Controller", "Reconcile event store, ComfyUI queue/history, files/S3, caches, locks, artifacts, QA, and promotion after interruption.", "Orphans, partial writes, missing outputs, stale locks, duplicate delivery, and conflicts resolve fail-closed and idempotently.", [41, 42, 43, 47, 49, 62, 156, 198, 199], True, "recovered artifact preview/playback review"),
])

add4("W64-MCM-LLM", "self_hosted_llm_vlm_control", "autonomous_reasoning", "Self-hosted LLM/VLM topology", [
    (201, "Self-Hosted Model Role and Authority Decomposition", "Separate planner, prompt composer, router advisor, defect classifier, VLM critic, audio critic, retrieval, and summarizer roles.", "Every role has bounded contracts, context, model requirements, escalation, uncertainty, and no promotion authority.", [150, 165, 166, 167, 168, 175, 197], True, "critic output review against known media cases"),
    (202, "Registry-Grounded Retrieval and Tool Context", "Build retrieval over schemas, packages, capabilities, workflows, benchmarks, failures, evidence, and current event state.", "Responses cite immutable IDs and surface stale, conflicting, missing, or out-of-scope evidence rather than inventing it.", [44, 51, 54, 62, 153, 154, 155, 156, 165, 198, 201], True, "cited calibration-media review"),
    (203, "Structured Proposal, Uncertainty, and Validation Contract", "Require schema-valid plans, prompts, routes, diagnoses, hypotheses, confidence, evidence references, and alternatives.", "Unsupported IDs and authority bypasses reject deterministically; uncertainty may abstain or escalate without executing.", [166, 167, 168, 175, 197, 201, 202], True, "adjudicated image/video/audio proposal comparison"),
    (204, "Self-Hosted LLM/VLM Serving and Qualification", "Define exact model/runtime/template/parser/quantization/context stacks, health, versioning, batching, failover, shadow mode, and benchmarks.", "Only role- and bucket-qualified versions activate and model changes cannot silently alter accepted decisions.", [37, 44, 54, 63, 165, 201, 202, 203], True, "core_autonomous_runtime held-out deterministic benchmarks and qualified independent model critics over blinded identities; human adjudication is optional independent_perceptual_calibration"),
])

add4("W64-MCM-RUNTIME", "runtime_resources_and_cache", "runtime_control", "Control plane", [
    (205, "Unified Runtime Capability Profiles", "Record engine builds, nodes, models, codecs, services, precision, hardware, RAM/VRAM/disk, limits, and measurements.", "Routing and scheduling use validated runtime facts and scoped envelopes rather than assumed availability.", [5, 6, 7, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 165, 204], True, "runtime inventory review"),
    (206, "Resource-Aware Scheduler and Model Residency", "Control GPU/CPU leases, VRAM admission, concurrency, residency, load/evict, batching, audio isolation, priority, and cancellation.", "No pass starts without a certified envelope; starvation, OOM loops, and incompatible co-residency are prevented.", [42, 61, 62, 63, 108, 146, 199, 205], True, "media review after degraded or resumed execution"),
    (207, "Content-Addressed Artifact and Computation Cache", "Key cache entries by exact package/input/transform/stack/workflow/runtime/configuration hashes and replay policy.", "Hits are lineage-safe and stale, revoked, corrupt, stochastic-mismatched, or semantically incompatible artifacts cannot be reused.", [7, 43, 152, 156, 170, 198, 205, 206], True, "cached-versus-fresh artifact spot review"),
    (208, "Telemetry, Cost, Capacity, and Degraded-Mode Control", "Record latency, utilization, memory, cache, retries, cost, quality, queue depth, service health, and policy-driven degradation.", "Degraded routing creates explicit decisions while quality and authority gates remain unchanged.", [5, 42, 61, 62, 63, 168, 200, 205, 206, 207], True, "degraded-route output review before promotion"),
])

add4("W64-MCM-QA", "qa_benchmarks_and_release_readiness", "qa_and_benchmarks", "Implementation order and acceptance", [
    (209, "Modular Multimodal Scorecard", "Define separate identity, morphology, pose, framing, ownership, mask, anatomy, realism, temporal, speech, audio, sync, provenance, and runtime gates.", "Metrics have applicability, calibrated thresholds, method, authority, evidence, and severity without one subjective realism scalar.", [16, 17, 18, 21, 30, 31, 32, 33, 34, 35, 103, 106, 131, 141, 160, 196, 208], True, "core_autonomous_runtime deterministic visual/audio adjudication sets plus qualified calibrated critics; human calibration is optional independent_perceptual_calibration"),
    (210, "Character-to-AV Benchmark Corpus", "Build immutable positive, negative, adversarial, ownership, outage, recovery, cross-engine, specialist, video, audio, and AV fixtures.", "The held-out corpus spans solo/multi-character and failure buckets with exact expected outcomes and revisions.", [109, 147, 160, 172, 180, 183, 196, 204, 209], True, "independent labeling and full playback review"),
    (211, "Calibrated QA Ensemble and Promotion Gate", "Combine deterministic validators, scoped metrics, critics, and review packets without letting weak signals override hard failures.", "False accept/reject rates, abstention, disagreement, target/protected/whole-artifact gates, and promotion rules are explicit.", [150, 184, 188, 192, 196, 203, 209, 210], True, "core_autonomous_runtime blinded-ID deterministic evidence plus qualified calibrated multimodal critic adjudication and signed policy; human adjudication is optional independent_perceptual_calibration"),
    (212, "Cross-Wave Regression and Release Readiness Suite", "Verify Rows149-220 preserve Rows001-148 authority, evidence, security, runtime, audio, QA, and completion controls.", "Static and selected end-to-end suites pass with residual risk, scope, certificates, blockers, and no false completion recorded.", [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 66, 112, 148, 151, 209, 210, 211], True, "representative image, video, audio, and AV regression review"),
])

add4("W64-MCM-APP", "app_mode_and_operator_ux", "operator_experience", "App Mode/operator surface", [
    (213, "Operator Information Architecture", "Define Character Library, Scene/Shot, Pose, Passes, Queue, Assets, QA, Blockers, Results, Replay, and Release views.", "The UI exposes domain concepts while hiding node IDs, raw paths, credentials, and unsupported internals.", [4, 47, 51, 149, 153, 154, 155, 156, 197, 198, 199, 200], True, "operator UI visual review"),
    (214, "Character, Scene, and Generation Builder UX", "Build package-aware controls for revisions, instances, camera, pose, contact, media, quality, budget, route policy, and constraints.", "Requests validate before submission and preview ownership, dependencies, masks, routes, and expected DAG.", [154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 181, 185, 189, 213], True, "forms, overlays, timeline, and preview review"),
    (215, "Live Run, QA, Blocker, and Repair Console", "Display DAG, routes, attempts, resources, artifacts, metrics, blockers, hypotheses, decisions, revocations, and lineage.", "Operators can explain every run/stop/repair without editing a ComfyUI graph and reconnect restores exact state.", [168, 175, 184, 188, 192, 196, 198, 199, 200, 211, 213, 214], True, "inline image/video/audio review controls"),
    (216, "App Mode API Binding and UX Qualification", "Bind App Mode to controller APIs, permissions, feature flags, accessibility, performance, reconnect, cancellation, and error states.", "The UI cannot bypass schemas/authority and offline, stale, partial, unauthorized, and conflicting states are explicit.", [107, 145, 197, 204, 208, 213, 214, 215], True, "complete operator-journey visual and audio review"),
])

add4("W64-MCM-REL", "phased_implementation_and_release", "release_program", "Implementation order and acceptance", [
    (217, "Phase 0 - Contracts and Authority Freeze", "Implement preservation, governance, IDs, schemas, registries, package fixtures, non-overlap checks, and migration maps before workflow expansion.", "Rows149-156 pass static acceptance and downstream work binds canonical versioned contracts.", [51, 54, 58, 66, 149, 150, 151, 152, 153, 154, 155, 156], False, "package reference and voice fixture review"),
    (218, "Phase 1 - Character-to-Image Vertical Slice", "Implement Character Factory, shot/pose ownership, routing, bridging, specialist passes, Mode A MaskFactory, and one single-character image run.", "Rows157-184 pass for one published character, accepted work is reused, and an injected child failure preserves its parent.", [157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 217], True, "full character, pose, mask, specialist, and final-image review"),
    (219, "Phase 2 - Multi-Character and Multimodal Expansion", "Add two-character ownership/contact, video, integrated audio, AV, durable orchestration, runtime controls, and Mode B only when certified.", "Rows161-212 pass required multimodal benchmarks and unqualified Mode B remains draft-only without blocking Mode A paths.", [161, 162, 163, 164, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 218], True, "mandatory two-character image and complete short AV review"),
    (220, "Phase 3 - Autonomous Operator Release Certification", "Qualify self-hosted roles, recovery, resource policy, QA calibration, App Mode, security, release, rollback, and main-task integration.", "Rows149-219 are traceable; release/done gates pass; all new files are preserved and adopted by the main task with limitations recorded.", [59, 60, 66, 112, 148, 204, 208, 212, 213, 214, 215, 216, 217, 218, 219], True, "final independent image, video, audio, AV, and operator-journey review"),
])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def win_rel(path: Path) -> str:
    return str(path).replace("/", "\\")


def canonical_full_path(path: Path) -> str:
    return str(CANONICAL_PROJECT_ROOT / PureWindowsPath(path.as_posix()))


def citation_info(root: Path, section: str) -> tuple[int, int, str, int]:
    path = root / AUTHORITY_REL
    if not path.exists():
        return 1, 1, section, 0
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    wanted = "## " + section
    start = next((i + 1 for i, line in enumerate(lines) if line.strip() == wanted), 1)
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    excerpt = " ".join(line.strip() for line in lines[start - 1 : min(end, start + 6)])[:1200]
    return start, max(start, end), excerpt, path.stat().st_size


def dependency_ids(row: PlanRow) -> list[str]:
    return [f"ITEM-W64-{number:03d}" for number in row.dependencies]


def item_record(root: Path, row: PlanRow) -> dict[str, object]:
    line_start, line_end, excerpt, source_size = citation_info(root, row.section)
    visual_required = row.review not in {"structural review", "architecture and traceability review", "schema and relationship review", "runtime inventory review"}
    source_rel = win_rel(AUTHORITY_REL)
    source_full = canonical_full_path(AUTHORITY_REL)
    source_key = f"W64-MCM:{row.number}:{row.workstream}:{source_rel}#L{line_start}-L{line_end}"
    return {
        "Item_ID": f"ITEM-W64-{row.number:03d}", "Item_Wave": 64,
        "Item_Type": "ultimate_multimodal_workflow_requirement", "Item_Title": row.title,
        "Item_Category": row.category, "Item_Domain": row.domain, "Owner_Domain": row.workstream,
        "Autonomous_Required": "TRUE", "Human_Input_Allowed": "FALSE", "Human_Work_Allowed": "FALSE",
        "Codex_Action": row.action, "Implementation_Target": row.domain,
        "Deliverable_Type": "code_config_schema_registry_workflow_test_runtime_evidence_qa_decision",
        "Acceptance_Criteria": row.acceptance,
        "QA_Gates_Required": "schema|lineage|compatibility|target|protected_scope|whole_artifact|promotion|no_false_completion",
        "Visual_Review_Required": "TRUE" if visual_required else "FALSE", "Visual_Review_Method": row.review,
        "Test_Required": "TRUE", "Evidence_Required": "source_citation|implementation_hashes|tests|runtime_manifest_if_applicable|artifact_hashes_if_applicable|qa_record|pass_or_exact_blocker",
        "Runtime_Proof_Required": "TRUE" if row.runtime_proof else "FALSE", "EC2_Allowed": "TRUE",
        "Blocker_Policy": "Fail only the dependent scope with an exact typed blocker; preserve accepted parents and continue independent safe DAG branches.",
        "Source_Plan_Root": CANONICAL_PLAN_ROOT, "Citation_File": source_rel,
        "Citation_Full_Path": source_full, "Citation_Section": row.section,
        "Citation_Line_Start": line_start, "Citation_Line_End": line_end,
        "Citation_Excerpt": excerpt, "Source_Package": CANONICAL_PLAN_ROOT,
        "Source_Type": "md", "Source_File_Size": source_size, "Priority": row.priority,
        "Risk_Level": row.risk, "Status": STATUS,
        "Created_From": "Wave64 ultimate modular multimodal workflow control-package generator",
        "Notes": "Planning coverage only. No runtime, engine, workflow, mask, model, artifact, or promotion completion is implied. content_based_suppression=false.",
        "Source_Key": source_key, "Source_File_Relative": source_rel,
        "Coverage_Level": "wave64_additive_planning_control",
        "Coverage_Audit_Status": "planned_rows149_220_runtime_evidence_required",
        "Ultra_Source_Coverage_Record": source_key,
    }


def tracker_record(root: Path, row: PlanRow) -> dict[str, object]:
    item = item_record(root, row)
    dependencies = "|".join(dependency_ids(row))
    evidence = f"Plan/Tracker/Evidence/Wave64/TRK-W64-{row.number:03d}.json"
    return {
        "Tracker_ID": f"TRK-W64-{row.number:03d}", "Wave": 64, "Phase": "Wave 64 Rows149-220",
        "Workstream": row.workstream, "Priority": row.priority, "Risk_Level": row.risk,
        "Owner_Role": "Codex Desktop Autonomous Agent", "Environment": "local_repo_ci_ec2_s3_comfyui_runtime_as_required",
        "Status": STATUS, "Task_Name": row.title, "Detailed_Action": row.action,
        "Completion_Criteria": row.acceptance,
        "Acceptance_Evidence": "source_citation|implementation_hashes|tests|runtime_manifest_if_applicable|artifact_hashes_if_applicable|qa_record|pass_or_exact_blocker",
        "Dependency_Prerequisite": dependencies,
        "Validation_Method": "deterministic_contract_tests|failure_injection|scoped_runtime_proof|target_and_protected_and_whole_artifact_qa",
        "Output_Artifact": evidence, "Source_Path": item["Citation_Full_Path"],
        "Related_Source_Paths": "Plan/08_SCHEMAS|Plan/10_REGISTRIES|Plan/Instructions/QA",
        "Package_Top_Level_Directory": CANONICAL_PLAN_ROOT,
        "Autonomous_Execution_Mode": "Codex Desktop fully autonomous with deterministic authority gates",
        "Human_Input_Allowed": "FALSE", "Human_Work_Allowed": "FALSE", "Codex_Desktop_Action": row.action,
        "QA_Strictness": "STRICT", "Visual_Review_Required": item["Visual_Review_Required"],
        "Visual_Review_Method": row.review, "Test_Required": "TRUE",
        "Runtime_Proof_Required": item["Runtime_Proof_Required"], "EC2_Allowed": "TRUE",
        "Preview_Required": "TRUE" if item["Visual_Review_Required"] == "TRUE" else "FALSE",
        "Final_Render_Gate": "BLOCKED_UNTIL_ALL_DECLARED_CONTRACT_RUNTIME_QA_AND_PROMOTION_EVIDENCE_PASSES",
        "Evidence_Path": evidence, "Citation_File": item["Citation_File"],
        "Citation_Full_Path": item["Citation_Full_Path"], "Citation_Section": item["Citation_Section"],
        "Citation_Line_Start": item["Citation_Line_Start"], "Citation_Line_End": item["Citation_Line_End"],
        "Citation_Excerpt": item["Citation_Excerpt"], "Source_Package": item["Source_Package"],
        "Source_Type": "md", "Source_Item_ID": item["Item_ID"], "Blocker_Policy": item["Blocker_Policy"],
        "Rerun_Policy": "Targeted rerun only with a material failure hypothesis; preserve accepted parents; no unexplained seed loop or silent route substitution.",
        "Status_Decision": "planning_complete_implementation_and_runtime_not_claimed",
        "Notes": item["Notes"], "Source_Key": item["Source_Key"], "Source_File_Relative": item["Source_File_Relative"],
        "Coverage_Level": item["Coverage_Level"], "Coverage_Audit_Status": item["Coverage_Audit_Status"],
        "Ultra_Source_Coverage_Record": item["Ultra_Source_Coverage_Record"],
    }


def csv_bytes(header: list[str], records: list[dict[str, object]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8")


def requirements_bytes() -> bytes:
    workstreams: dict[str, list[int]] = {}
    requirements = []
    for row in ROWS:
        workstreams.setdefault(row.workstream, []).append(row.number)
        requirements.append({
            "row_number": row.number, "tracker_id": f"TRK-W64-{row.number:03d}",
            "item_id": f"ITEM-W64-{row.number:03d}", "workstream": row.workstream,
            "domain": row.domain, "title": row.title, "status": STATUS,
            "implementation_action": row.action, "acceptance": row.acceptance,
            "dependencies": dependency_ids(row), "runtime_proof_required": row.runtime_proof,
            "review_method": row.review,
            "mandatory_evidence": ["implementation_hashes", "tests", "runtime_manifest_if_applicable", "artifact_hashes_if_applicable", "qa_record", "pass_or_exact_blocker"],
        })
    payload = {
        "schema_version": "1.0.0", "package_id": PACKAGE_ID,
        "authority": win_rel(AUTHORITY_REL),
        "row_range": {"first": 149, "last": 220, "count": 72},
        "status": STATUS, "planning_complete": True, "runtime_complete": False,
        "content_based_suppression": False,
        "completion_rule": "Planning never counts as implementation, runtime, artifact, engine, model, workflow, mask, QA, promotion, or release completion.",
        "perceptual_review_profile_policy": {
            "core_autonomous_runtime": {
                "review_authority": "deterministic_validators_plus_qualified_calibrated_autonomous_critics_plus_signed_policy",
                "human_visual_listening_or_operator_approval_required": False,
                "human_absence_can_block_or_revoke_core": False,
                "runtime_proof_requirements_preserved": True,
            },
            "independent_perceptual_calibration": {
                "required_for_core_release": False,
                "human_blind_visual_listening_or_adjudication_allowed": True,
                "authority": "optional_calibration_evidence_only",
            },
            "explicit_user_override": {
                "default_or_implicit": False,
                "must_be_separately_recorded_and_policy_authorized": True,
                "can_waive_never_waivable_core_failure": False,
            },
        },
        "workstreams": [{"workstream": key, "first": min(nums), "last": max(nums), "count": len(nums)} for key, nums in workstreams.items()],
        "requirements": requirements,
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def validate_rows() -> None:
    numbers = [row.number for row in ROWS]
    if numbers != list(range(149, 221)):
        raise ValueError("Rows must be exactly contiguous 149-220")
    if len({row.title for row in ROWS}) != 72:
        raise ValueError("Row titles must be unique")
    perceptual_rows = {157, 167, 172, 190, 192, 204, 209, 211}
    for row in ROWS:
        if row.number in perceptual_rows and ("core_autonomous_runtime" not in row.review or "independent_perceptual_calibration" not in row.review):
            raise ValueError(f"Row{row.number} perceptual review is not autonomous-core and optional-human profile scoped")
    by_workstream: dict[str, int] = {}
    for row in ROWS:
        by_workstream[row.workstream] = by_workstream.get(row.workstream, 0) + 1
        for dep in row.dependencies:
            if dep == row.number or dep > 220 or (149 <= dep and dep >= row.number):
                raise ValueError(f"Invalid or cyclic dependency {dep} for row {row.number}")
    if len(by_workstream) != 18 or any(count != 4 for count in by_workstream.values()):
        raise ValueError("Expected eighteen workstreams with four rows each")


def build_outputs(root: Path) -> dict[Path, bytes]:
    validate_rows()
    items = [item_record(root, row) for row in ROWS]
    trackers = [tracker_record(root, row) for row in ROWS]
    item_csv = csv_bytes(ITEM_HEADER, items)
    tracker_csv = csv_bytes(TRACKER_HEADER, trackers)
    requirements = requirements_bytes()
    outputs = {
        Path("Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_ITEM_ROWS.csv"): item_csv,
        Path("Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_REQUIREMENTS.json"): requirements,
        Path("Plan/Tracker/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_TRACKER_ROWS.csv"): tracker_csv,
        Path("Plan/Tracker/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_REQUIREMENTS.json"): requirements,
    }
    coverage = {
        "schema_version": "1.0.0", "evidence_type": "planning_coverage_only",
        "package_id": PACKAGE_ID, "status": "PASS_PLANNING_COVERAGE_ONLY_RUNTIME_NOT_CLAIMED",
        "row_range": {"first": 149, "last": 220, "count": 72}, "workstream_count": 18,
        "content_based_suppression": False,
        "generated_artifacts": [{"path": win_rel(path), "sha256": sha256(data), "bytes": len(data)} for path, data in outputs.items()],
        "invariants": {
            "rows_are_contiguous": True, "rows_are_unique": True,
            "four_rows_per_workstream": True, "new_dependencies_are_acyclic": True,
            "items_and_tracker_requirement_json_are_byte_identical": True,
            "core_perceptual_review_is_autonomous_policy_and_qualified_critics": True,
            "human_perceptual_review_is_optional_profile_only": True,
            "rows001_148_modified": False, "runtime_completion_claimed": False,
        },
    }
    coverage_bytes = (json.dumps(coverage, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    outputs[Path("Plan/Instructions/QA/Evidence/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_PLANNING_COVERAGE.json")] = coverage_bytes
    outputs[Path("Plan/Tracker/Evidence/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_PLANNING_COVERAGE.json")] = coverage_bytes
    static_records = []
    for relative_text in PRESERVATION_STATIC_PATHS:
        relative = Path(relative_text)
        path = root / relative
        if path.exists():
            data = path.read_bytes()
            static_records.append({"path": win_rel(relative), "status": "present_intentional", "sha256": sha256(data), "bytes": len(data)})
        else:
            static_records.append({"path": win_rel(relative), "status": "missing_in_this_root", "sha256": None, "bytes": 0})
    baseline_records = []
    for relative_text in BASELINE_PRESERVED_PATHS:
        relative = Path(relative_text)
        path = root / relative
        if path.exists():
            data = path.read_bytes()
            baseline_records.append({"path": win_rel(relative), "status": "preserved_reference_do_not_rewrite", "sha256": sha256(data), "bytes": len(data)})
        else:
            baseline_records.append({"path": win_rel(relative), "status": "missing_in_this_root", "sha256": None, "bytes": 0})
    preservation = {
        "schema_version": "1.0.0", "manifest_id": "wave64_rows149_220_main_task_preservation_manifest",
        "package_id": PACKAGE_ID, "generated_at": "2026-07-16T22:15:00-05:00",
        "status": "intentional_planning_package_preserve_do_not_clean",
        "main_task_id": "019f422f-88b1-7382-872b-21de2089e983",
        "maskfactory_task_id": "019f4cfc-60c3-7500-8626-261dcf70db5d",
        "runtime_completion_claimed": False, "content_based_suppression": False,
        "self_hash_excluded": True,
        "static_package_files": static_records,
        "generated_sidecars": [{"path": win_rel(path), "status": "present_intentional", "sha256": sha256(data), "bytes": len(data)} for path, data in outputs.items()],
        "baseline_preserved_references": baseline_records,
        "preservation_rule": "Do not delete, clean, overwrite, renumber, or infer runtime completion from these dirty/untracked files. Main must review and record adoption before staging or implementation.",
    }
    preservation_bytes = (json.dumps(preservation, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    outputs[Path("Plan/Instructions/Hydration_Rehydration/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_PRESERVATION_MANIFEST.json")] = preservation_bytes
    return outputs


def check_outputs(root: Path, outputs: dict[Path, bytes]) -> list[str]:
    problems: list[str] = []
    for relative, expected in outputs.items():
        path = root / relative
        if not path.exists():
            problems.append(f"missing: {relative}")
        elif path.read_bytes() != expected:
            problems.append(f"mismatch: {relative}")
    return problems


def write_outputs(root: Path, outputs: dict[Path, bytes]) -> None:
    for relative, data in outputs.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = build_outputs(root)
    if args.write:
        write_outputs(root, outputs)
    problems = check_outputs(root, outputs)
    if problems:
        print("\n".join(problems))
        return 1
    print(json.dumps({"status": "pass", "mode": "write" if args.write else "check", "rows": len(ROWS), "outputs": len(outputs)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
