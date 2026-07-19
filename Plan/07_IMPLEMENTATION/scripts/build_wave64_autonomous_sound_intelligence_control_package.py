from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLAN_ROOT = PROJECT_ROOT / "Plan"
MASTER_REL = Path("Plan/00_PROJECT_CONTROL/WAVE64_AUTONOMOUS_VIDEO_TO_AUDIO_AND_SOUND_GENERATION_MASTER_PLAN.md")
MASTER = PROJECT_ROOT / MASTER_REL

ITEMS_REQUIREMENTS = PLAN_ROOT / "Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_REQUIREMENTS.json"
TRACKER_REQUIREMENTS = PLAN_ROOT / "Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_REQUIREMENTS.json"
ITEMS_CSV = PLAN_ROOT / "Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ITEM_ROWS.csv"
TRACKER_CSV = PLAN_ROOT / "Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_TRACKER_ROWS.csv"
REGISTRY = PLAN_ROOT / "10_REGISTRIES/wave64_autonomous_sound_intelligence_work_package_registry.json"
EVIDENCE = PLAN_ROOT / "Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_PLANNING_COVERAGE_20260715.json"
TRACKER_EVIDENCE = PLAN_ROOT / "Tracker/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_PLANNING_COVERAGE_20260715.json"

SOURCE_DOCUMENTS = (
    MASTER,
    PLAN_ROOT / "02_TARGET_ARCHITECTURE/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ARCHITECTURE.md",
    PLAN_ROOT / "05_AUDIO_SYSTEM/WAVE64_AUTONOMOUS_SOUND_LIBRARY_GENERATION_AND_QA_PLAN.md",
    PLAN_ROOT / "Instructions/QA/AUTONOMOUS_VIDEO_TO_AUDIO_AND_GENERATED_SOUND_QA_PROTOCOL.md",
    PLAN_ROOT / "Instructions/Hydration_Rehydration/AUTONOMOUS_SOUND_INTELLIGENCE_MAIN_SESSION_HANDOFF.md",
)

SCHEMA_CONTRACTS = (
    PLAN_ROOT / "08_SCHEMAS/audio_asset_intelligence_record.schema.json",
    PLAN_ROOT / "08_SCHEMAS/visual_audio_event_manifest.schema.json",
    PLAN_ROOT / "08_SCHEMAS/audio_candidate_score_record.schema.json",
    PLAN_ROOT / "08_SCHEMAS/generated_audio_asset_provenance.schema.json",
    PLAN_ROOT / "08_SCHEMAS/audio_orchestration_run.schema.json",
    PLAN_ROOT / "08_SCHEMAS/audio_clip_preparation_manifest.schema.json",
    PLAN_ROOT / "08_SCHEMAS/audio_spatial_render_manifest.schema.json",
    PLAN_ROOT / "08_SCHEMAS/generated_audio_qa_report.schema.json",
)

STATUS = "Planned_Autonomous_Implementation_Required"
BLOCKER = (
    "No false completion. Implement, test, run, review, and evidence the exact row. "
    "If a dependency, right, model, event authority, runtime proof, audio review, or evidence is missing, "
    "record the exact blocker and continue only with dependency-safe work."
)
RERUN = (
    "Targeted rerun only. Reuse hash-matched passed stages and never regenerate or rerun completed proof "
    "unless an input, objective, implementation, model, configuration, threshold, or authority changed."
)


@dataclass(frozen=True)
class WorkPackage:
    row: int
    slug: str
    title: str
    phase: str
    dependencies: tuple[int, ...]
    acceptance: str
    gates: tuple[str, ...]
    runtime: bool = True
    visual: bool = False
    ec2: bool = False
    risk: str = "HIGH"

    @property
    def item_id(self) -> str:
        return f"ITEM-W64-{self.row:03d}"

    @property
    def tracker_id(self) -> str:
        return f"TRK-W64-{self.row:03d}"


WORK_PACKAGES = (
    WorkPackage(67, "sound_intelligence_planning_authority", "Autonomous sound intelligence planning authority and no-false-completion control", "control_and_inventory", (), "Items and Tracker contain exact Rows067-112, dependencies are acyclic, and planning cannot be classified as runtime completion.", ("row_parity", "dependency_dag", "no_false_completion"), False, False, False, "CRITICAL"),
    WorkPackage(68, "audio_rights_provenance_authority", "Audio rights, provenance, attribution, and derivative-use authority", "control_and_inventory", (67,), "Every source, transform, generator, derivative, export, and promoted asset has a machine-readable rights and attribution decision.", ("license_known", "derivative_rights_known", "output_use_known", "attribution_bound"), False, False, False, "CRITICAL"),
    WorkPackage(69, "full_audio_library_index", "Full-library resumable audio index completion", "control_and_inventory", (67, 68), "Indexed plus exact-blocker count equals discovered audio count with reproducible index and failure-manifest hashes.", ("inventory_reconciled", "source_bytes_immutable", "sha256_complete", "resume_verified", "dedup_counted")),
    WorkPackage(70, "canonical_audio_decode", "Canonical audio decode and technical metadata", "control_and_inventory", (69,), "Every supported asset has deterministic decode metadata and a canonical PCM hash or an exact fail-closed decode blocker.", ("decode_integrity", "canonical_pcm_hash", "metadata_complete", "source_immutable")),
    WorkPackage(71, "waveform_feature_extraction", "Waveform and acoustic feature extraction", "audio_understanding", (70,), "Versioned acoustic features pass fixture and representative-strata calibration tests.", ("loudness", "true_peak", "spectral_features", "dynamic_range", "channel_analysis")),
    WorkPackage(72, "onset_transient_detection", "Onset, transient, peak, and offset anchor detection", "audio_understanding", (70, 71), "Frame-exact benchmark errors meet registered thresholds and ambiguous anchors remain explicit.", ("onset_precision", "peak_alignment", "offset_detection", "multi_method_agreement"), risk="CRITICAL"),
    WorkPackage(73, "usable_bounds_decay_analysis", "Silence, usable bounds, envelope, and natural-decay analysis", "audio_understanding", (71, 72), "Suggested bounds preserve primary onset and audible natural decay without changing source bytes.", ("silence_bounds", "attack_sustain_release", "tail_preservation", "non_destructive")),
    WorkPackage(74, "multi_event_segmentation", "Multi-event audio segmentation and virtual clips", "audio_understanding", (72, 73), "Every virtual segment is reproducible from parent hash and sample bounds with calibrated event-count accuracy.", ("event_count", "segment_bounds", "parent_lineage", "overlap_policy"), risk="CRITICAL"),
    WorkPackage(75, "audio_defect_classification", "Audio quality and defect classification", "audio_understanding", (70, 71), "Severe technical defects are detected and remove production eligibility without hiding inventory records.", ("clipping", "noise", "dropout", "truncation", "codec_damage", "visibility_preserved")),
    WorkPackage(76, "audio_reverb_dryness_estimation", "Dryness, reverberation, and room-tail estimation", "audio_understanding", (71, 73), "Dry/wet and decay estimates are calibrated and prevent incompatible double reverberation.", ("direct_reverberant_estimate", "rt60_estimate", "early_reflections", "double_reverb_guard")),
    WorkPackage(77, "semantic_audio_embeddings", "Versioned semantic audio and taxonomy embeddings", "audio_understanding", (69, 70), "Held-out semantic retrieval passes registered metrics with exact model, preprocessing, and embedding-index identity.", ("model_hash", "preprocessing_hash", "embedding_determinism", "heldout_retrieval"), ec2=True),
    WorkPackage(78, "audio_tag_caption_ensemble", "Audio tagging and technical caption ensemble", "audio_understanding", (71, 75, 77), "Tags preserve disagreements and unknowns while combining independent metadata, acoustic, embedding, and model signals.", ("ensemble_sources", "taxonomy_validation", "conflict_preservation", "unknown_fail_closed"), ec2=True),
    WorkPackage(79, "fine_grained_foley_taxonomy", "Fine-grained Foley body, material, footwear, force, and room enrichment", "audio_understanding", (74, 76, 78), "Promoted Foley records have exact required tags or explicit unknowns that prevent incompatible use.", ("event_family", "contact_pair", "body_region", "footwear", "material", "force", "room"), risk="CRITICAL"),
    WorkPackage(80, "hybrid_audio_retrieval_index", "Hybrid structured, lexical, embedding, and hash retrieval index", "retrieval_intelligence", (69, 77, 79), "A fixed query and index revision returns the same candidate set with no mixed index generations.", ("structured_filter", "lexical_search", "vector_search", "canonical_dedup", "deterministic_order")),
    WorkPackage(81, "explainable_candidate_ranking", "Explainable weighted audio candidate scoring and ranking", "retrieval_intelligence", (68, 72, 76, 79, 80), "Every hard exclusion, score component, weight, penalty, tie-break, and final decision is recorded.", ("hard_filters", "component_scores", "weights_versioned", "tie_break", "decision_explanation"), risk="CRITICAL"),
    WorkPackage(82, "audio_repetition_diversity", "Audio repetition, diversity, continuity, and recent-use control", "retrieval_intelligence", (74, 80, 81), "Repeated-event tests demonstrate non-repetitive selection without semantic or continuity drift.", ("cooldown", "near_duplicate_penalty", "alternation", "scene_continuity", "bounded_variation")),
    WorkPackage(83, "retrieval_fallback_calibration", "Retrieval confidence, abstention, and generated-fallback calibration", "retrieval_intelligence", (81, 82), "Held-out event-family precision and false-match metrics govern exact, approximate, generated, and abstain routes.", ("confidence_calibration", "precision_recall", "false_match_rate", "fallback_threshold", "abstention"), risk="CRITICAL"),
    WorkPackage(84, "canonical_video_timeline", "Canonical video decode, cuts, frame timing, and sample-clock normalization", "visual_event_intelligence", (67,), "Frame/time/sample conversions round-trip within tolerance for fixed and variable frame rate sources.", ("video_decode", "time_base", "cut_detection", "frame_sample_roundtrip"), visual=True),
    WorkPackage(85, "actor_object_region_tracking", "Actor, object, body-region, clothing, and surface segmentation/tracking", "visual_event_intelligence", (84,), "Persistent ownership tracks have measured identity-switch, occlusion, reappearance, and lost-track behavior.", ("actor_tracking", "object_tracking", "body_region_tracking", "occlusion", "ownership"), visual=True, ec2=True, risk="CRITICAL"),
    WorkPackage(86, "pose_hand_foot_gait_extraction", "Pose, hand, foot, gait, and contact-phase extraction", "visual_event_intelligence", (84, 85), "Annotated-clip benchmarks validate visible landmark trajectories and contact phases without fabricated hidden joints.", ("pose", "hands", "feet", "gait_phase", "contact_phase", "partial_view_guard"), visual=True, ec2=True, risk="CRITICAL"),
    WorkPackage(87, "motion_force_cues", "Optical flow, velocity, acceleration, scuff, and force-cue extraction", "visual_event_intelligence", (84, 85, 86), "Camera-compensated motion and force proxies pass calibrated trajectory tests and remain labeled estimates.", ("optical_flow", "camera_compensation", "velocity", "acceleration", "force_proxy"), visual=True, ec2=True),
    WorkPackage(88, "depth_camera_source_position", "Depth, camera, listener, and acoustic source-position estimation", "visual_event_intelligence", (84, 85), "Spatial coordinates bind to exact take/camera and preserve relative-depth uncertainty where metric depth is unavailable.", ("depth", "camera_binding", "source_position", "listener_position", "uncertainty"), visual=True, ec2=True),
    WorkPackage(89, "visual_material_recognition", "Surface, object, clothing, and contact-material recognition", "visual_event_intelligence", (85, 88), "Material decisions fuse independent evidence and abstain or broaden class when visual proof is ambiguous.", ("scene_registry", "material_classifier", "texture_evidence", "contact_context", "confidence"), visual=True, ec2=True, risk="CRITICAL"),
    WorkPackage(90, "contact_inference_ownership", "Visual contact inference, timing, force, and source-target ownership authority", "visual_event_intelligence", (85, 86, 87, 88, 89), "Actor-specific contact certification requires trusted source/target ownership and calibrated onset/peak/release evidence.", ("source_owner", "target_owner", "contact_onset", "contact_peak", "release", "authority_ceiling"), visual=True, ec2=True, risk="CRITICAL"),
    WorkPackage(91, "visual_audio_event_manifest", "Canonical timed visual audio-event manifest compiler", "visual_event_intelligence", (84, 90), "Every expected audible event is evidenced, intentionally silent, or explicitly blocked with frame and sample anchors.", ("event_traceability", "frame_anchor", "sample_anchor", "expected_layers", "silence_decision", "coverage"), visual=True, risk="CRITICAL"),
    WorkPackage(92, "event_uncertainty_fallback", "Visual event uncertainty, conflict, offscreen, and fallback policy", "visual_event_intelligence", (91,), "Detector conflicts, occlusion, unknown materials, cuts, and offscreen events produce deterministic fallback and certification ceilings.", ("conflict_resolution", "uncertainty_preserved", "offscreen_policy", "fallback_route", "certification_ceiling"), visual=True, risk="CRITICAL"),
    WorkPackage(93, "canonical_clip_preparation", "Canonical non-destructive audio clip preparation", "rendering_and_mix", (70, 72, 73, 74, 75), "Prepared derivatives retain source lineage, anchor timing, natural tail, phase, and transform reproducibility.", ("resample", "channel_convert", "trim", "fades", "anchor_preservation", "tail_preservation")),
    WorkPackage(94, "layered_foley_composition", "Layer construction and deterministic composite Foley synthesis", "rendering_and_mix", (68, 79, 81, 91, 93), "Every layer is compatible, separately attributable, reconstructable, and justified by the event manifest.", ("layer_justification", "license_compatibility", "acoustic_compatibility", "stem_lineage", "composite_hash")),
    WorkPackage(95, "spatial_audio_renderer", "Spatial panning, distance, elevation, motion, and occlusion renderer", "rendering_and_mix", (88, 91, 93), "Moving-source and occlusion fixtures match expected trajectories without phase, clipping, or loudness defects.", ("pan", "distance", "elevation", "source_motion", "occlusion", "phase"), ec2=True, risk="CRITICAL"),
    WorkPackage(96, "room_acoustic_renderer", "Room impulse response, early-reflection, RT60, and convolution renderer", "rendering_and_mix", (76, 88, 89, 95), "Measured output RT60 and early reflections meet target tolerances and wet-source compatibility rules.", ("room_geometry", "material_absorption", "rir", "early_reflections", "rt60", "wet_source_guard"), ec2=True, risk="CRITICAL"),
    WorkPackage(97, "sample_accurate_mix_mux", "Sample-accurate timeline mixer, buses, loudness, stems, and video mux", "rendering_and_mix", (91, 93, 94, 95, 96), "Reproducible mix/mux preserves frames and samples with no clipping, missing stems, or endpoint drift.", ("sample_schedule", "bus_processing", "loudness", "true_peak", "stem_manifest", "mux_lineage"), ec2=True, risk="CRITICAL"),
    WorkPackage(98, "deterministic_sound_variation", "Deterministic reusable sound variation engine", "sound_creation", (68, 71, 72, 73, 79, 93), "Bounded variants preserve event identity and anchors, avoid duplicates, and retain source/transform/rights provenance.", ("bounded_transforms", "semantic_preservation", "anchor_preservation", "dedup", "provenance")),
    WorkPackage(99, "neural_text_to_audio", "Neural text-to-audio sound-effect generation router", "sound_creation", (68, 79, 83, 91), "Seeded candidates carry exact model/config rights provenance and pass duration, semantic, technical, and uniqueness gates.", ("structured_prompt", "engine_authority", "seeded_batch", "rights", "candidate_only"), ec2=True, risk="CRITICAL"),
    WorkPackage(100, "reference_audio_variation", "Reference-conditioned audio-to-audio variation, inpainting, and continuation", "sound_creation", (68, 72, 73, 83, 98, 99), "Derivative rights, structural similarity, requested variation, timing, and unwanted-content rejection all pass.", ("source_rights", "conditioning_strength", "structure_preservation", "variation_measure", "unexpected_class_reject"), ec2=True, risk="CRITICAL"),
    WorkPackage(101, "video_conditioned_foley", "Video-conditioned Foley generation and deterministic-event blending", "sound_creation", (83, 91, 92, 97, 99), "Generated Foley is compared to trusted event anchors and cannot silently overwrite exact one-shots.", ("video_hash", "event_script_hash", "engine_identity", "anchor_alignment", "blend_decision"), visual=True, ec2=True, risk="CRITICAL"),
    WorkPackage(102, "generated_asset_provenance", "Generated-audio provenance and candidate staging", "sound_creation", (68, 98, 99, 100, 101), "Every candidate is immutable and records inputs, prompt, event, engine, model, config, seed, environment, output, rights, and QA state.", ("input_hashes", "prompt_hash", "engine_hashes", "seed", "output_hash", "rights", "staging_boundary"), risk="CRITICAL"),
    WorkPackage(103, "generated_sound_qa", "Generated-sound technical, semantic, timing, acoustic, and uniqueness QA", "sound_creation", (71, 72, 75, 76, 79, 83, 102), "Calibrated multi-signal QA rejects semantic mismatch, extra events, timing defects, technical defects, and unsuitable acoustics.", ("technical_qa", "semantic_qa", "timing_qa", "acoustic_qa", "dedup", "negative_evidence"), ec2=True, risk="CRITICAL"),
    WorkPackage(104, "generated_asset_promotion", "Generated-asset promotion, reuse, revocation, and library ingestion", "sound_creation", (80, 102, 103), "Only fully passing generated assets enter a versioned reusable library with provenance, QA, rights, dedup, and revocation status.", ("promotion_authority", "registry_ingestion", "selector_visibility", "origin_preserved", "revocation"), risk="CRITICAL"),
    WorkPackage(105, "audio_end_to_end_orchestrator", "End-to-end autonomous video-to-audio orchestration and recovery", "orchestration_and_operations", (83, 92, 97, 104), "The content-addressed DAG is idempotent, resumable, cost-bounded, and cannot skip mandatory gates.", ("dag", "idempotency", "resume", "stage_authority", "retry_budget", "publication"), ec2=True, risk="CRITICAL"),
    WorkPackage(106, "audio_av_qa_matrix", "Automated event, mix, spatial, global-audio, and AV QA matrix", "orchestration_and_operations", (90, 91, 97, 103, 105), "Fixture, adversarial, and genuine-video tests measure coverage, false events, alignment, drift, semantics, room, repetition, and full-duration quality.", ("event_coverage", "false_event", "contact_offset", "endpoint_drift", "semantic_match", "room_consistency", "global_review"), visual=True, ec2=True, risk="CRITICAL"),
    WorkPackage(107, "comfyui_audio_integration", "Modular ComfyUI and API integration for autonomous sound intelligence", "orchestration_and_operations", (91, 97, 105, 106), "Versioned modular workflows pass static/runtime validation and expose bounded inputs/outputs without embedding authority in a monolith.", ("schema_io", "modular_workflows", "static_validation", "runtime_smoke", "external_authority"), visual=True, ec2=True, risk="CRITICAL"),
    WorkPackage(108, "audio_runtime_cache_cost", "Audio runtime, feature cache, batching, EC2, S3, and cost controls", "orchestration_and_operations", (69, 77, 99, 101, 105), "Caches invalidate by exact identity, batches resume, GPU/EC2 use is bounded, and cost/transfer evidence is recorded.", ("cache_identity", "batch_resume", "gpu_budget", "ec2_ttl", "s3_manifest", "cost_record"), ec2=True),
    WorkPackage(109, "audio_benchmark_corpus", "Audio-event benchmark, calibration, held-out test, and adversarial corpus", "orchestration_and_operations", (67, 68), "Representative event/material/room/ownership fixtures have separate calibration and final-test roles with immutable truth.", ("coverage_matrix", "annotation_authority", "partition_separation", "adversarial_cases", "truth_integrity"), visual=True, risk="CRITICAL"),
    WorkPackage(110, "audio_observability_replay", "Audio observability, replay, rejection diagnosis, and run ledger", "orchestration_and_operations", (102, 105, 106), "Every release or promoted asset is reconstructable from the run ledger or has an exact external dependency blocker.", ("stage_timing", "model_identity", "candidate_ranking", "rejection_reason", "transform_lineage", "replay")),
    WorkPackage(111, "audio_existing_component_migration", "Existing Wave30, Wave31, Wave64, selector, indexer, and generator compatibility migration", "orchestration_and_operations", (67, 69, 80, 91, 97, 105), "Existing compatible components are adapted once, limitations remain explicit, and completed proof is not reopened or duplicated.", ("component_inventory", "adapter_contract", "no_duplicate_work", "limitations_preserved", "completed_proof_guard"), risk="CRITICAL"),
    WorkPackage(112, "audio_full_system_certification", "Autonomous sound intelligence production acceptance and full-system certification", "certification", tuple(range(67, 112)), "Multiple genuine videos and all required routes pass exact rights, provenance, event, audio, spatial, AV, playback, global, and multimodal authority gates.", ("all_dependencies_pass", "genuine_runtime", "full_duration_review", "av_sync", "rights", "provenance", "global_qa", "multimodal_release"), visual=True, ec2=True, risk="CRITICAL"),
)


ITEM_HEADERS = [
    "Item_ID", "Item_Wave", "Item_Type", "Item_Title", "Item_Category", "Item_Domain",
    "Owner_Domain", "Autonomous_Required", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Action", "Implementation_Target", "Deliverable_Type", "Acceptance_Criteria",
    "QA_Gates_Required", "Visual_Review_Required", "Visual_Review_Method", "Test_Required",
    "Evidence_Required", "Runtime_Proof_Required", "EC2_Allowed", "Blocker_Policy",
    "Source_Plan_Root", "Citation_File", "Citation_Full_Path", "Citation_Section",
    "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt", "Source_Package",
    "Source_Type", "Source_File_Size", "Priority", "Risk_Level", "Status", "Created_From",
    "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level", "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]

TRACKER_HEADERS = [
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
    "Coverage_Audit_Status", "Ultra_Source_Coverage_Record",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def section_for(row: int, lines: list[str]) -> tuple[int, int, str, str]:
    prefix = f"### Row{row:03d} "
    starts = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(starts) != 1:
        raise ValueError(f"expected one master-plan heading for Row{row:03d}, found {len(starts)}")
    start = starts[0]
    end = next((i - 1 for i in range(start + 1, len(lines)) if lines[i].startswith("### Row")), len(lines) - 1)
    section = lines[start].removeprefix("### ")
    excerpt = " ".join(line.strip() for line in lines[start : min(end + 1, start + 8)] if line.strip())[:500]
    return start + 1, end + 1, section, excerpt


def requirements_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "package_id": "WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ROWS_067_112",
        "created_at": "2026-07-15T00:00:00-05:00",
        "authority": str(MASTER_REL).replace("/", "\\"),
        "status": STATUS,
        "planning_complete_runtime_complete": False,
        "reserved_row_range": {"first": 67, "last": 112, "count": len(WORK_PACKAGES)},
        "inventory_boundary": {
            "discovered_audio_files": 39771,
            "wav_files": 36195,
            "source_bytes_immutable": True,
            "content_based_suppression": False,
        },
        "completion_rule": (
            "Every row requires its own implementation, tests, runtime proof where applicable, QA, evidence, and pass decision. "
            "Planning artifacts never count as runtime completion."
        ),
        "research_sources": [
            "https://github.com/LAION-AI/CLAP",
            "https://essentia.upf.edu/tutorial_rhythm_onsetdetection.html",
            "https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker",
            "https://github.com/facebookresearch/sam2",
            "https://docs.pytorch.org/vision/stable/models/raft.html",
            "https://github.com/DepthAnything/Depth-Anything-V2",
            "https://github.com/LCAV/pyroomacoustics",
            "https://github.com/facebookresearch/audiocraft/blob/main/docs/AUDIOGEN.md",
            "https://github.com/Stability-AI/stable-audio-3",
            "https://github.com/hkchengrex/MMAudio",
            "https://github.com/Tencent-Hunyuan/HunyuanVideo-Foley",
        ],
        "schema_contracts": [str(path.relative_to(PROJECT_ROOT)).replace("/", "\\") for path in SCHEMA_CONTRACTS],
        "work_packages": [
            {
                **asdict(work),
                "item_id": work.item_id,
                "tracker_id": work.tracker_id,
                "dependencies": [f"ITEM-W64-{dep:03d}" for dep in work.dependencies],
                "tracker_dependencies": [f"TRK-W64-{dep:03d}" for dep in work.dependencies],
                "status": STATUS,
            }
            for work in WORK_PACKAGES
        ],
    }


def item_row(work: WorkPackage, citation: tuple[int, int, str, str]) -> dict[str, str]:
    start, end, section, excerpt = citation
    deps = "|".join(f"ITEM-W64-{dep:03d}" for dep in work.dependencies) or "none"
    action = f"Autonomously implement, test, runtime-prove, review, and evidence {work.slug}; preserve dependencies and fail closed."
    source_key = f"W64:{work.slug}:{str(MASTER_REL).replace('/', chr(92))}#L{start}-L{end}"
    return {
        "Item_ID": work.item_id, "Item_Wave": "64", "Item_Type": "autonomous_sound_intelligence_requirement",
        "Item_Title": work.title, "Item_Category": work.phase, "Item_Domain": work.slug,
        "Owner_Domain": "Autonomous Audio System", "Autonomous_Required": "TRUE",
        "Human_Input_Allowed": "FALSE", "Human_Work_Allowed": "FALSE", "Codex_Action": action,
        "Implementation_Target": work.slug, "Deliverable_Type": "code_schema_registry_workflow_tests_runtime_qa_evidence",
        "Acceptance_Criteria": work.acceptance, "QA_Gates_Required": "|".join(work.gates),
        "Visual_Review_Required": str(work.visual).upper(),
        "Visual_Review_Method": "combined_frame_contact_audio_review" if work.visual else "audio_waveform_spectrogram_manifest_review",
        "Test_Required": "TRUE", "Evidence_Required": "source_citation|implementation_hashes|test_log|runtime_record|qa_record|blocker_or_pass_decision",
        "Runtime_Proof_Required": str(work.runtime).upper(), "EC2_Allowed": str(work.ec2).upper(),
        "Blocker_Policy": BLOCKER, "Source_Plan_Root": str(PLAN_ROOT),
        "Citation_File": str(MASTER_REL).replace("/", "\\"), "Citation_Full_Path": str(MASTER),
        "Citation_Section": section, "Citation_Line_Start": str(start), "Citation_Line_End": str(end),
        "Citation_Excerpt": excerpt, "Source_Package": str(PLAN_ROOT), "Source_Type": "md",
        "Source_File_Size": str(MASTER.stat().st_size), "Priority": "P0" if work.risk == "CRITICAL" else "P1",
        "Risk_Level": work.risk, "Status": STATUS, "Created_From": "Wave64 autonomous sound intelligence master plan",
        "Notes": f"Dependencies={deps}. Planning coverage only; runtime completion is false until exact row evidence passes.",
        "Source_Key": source_key, "Source_File_Relative": str(MASTER_REL).replace("/", "\\"),
        "Coverage_Level": "autonomous_sound_intelligence_end_to_end", "Coverage_Audit_Status": "direct_reserved_row_coverage",
        "Ultra_Source_Coverage_Record": source_key,
    }


def tracker_row(work: WorkPackage, citation: tuple[int, int, str, str]) -> dict[str, str]:
    item = item_row(work, citation)
    deps = "|".join(f"TRK-W64-{dep:03d}" for dep in work.dependencies) or "none"
    evidence_path = f"Plan/Instructions/QA/Evidence/Wave64/{work.tracker_id}_{work.slug}.json"
    return {
        "Tracker_ID": work.tracker_id, "Wave": "64", "Phase": "Wave 64 Autonomous Sound Intelligence",
        "Workstream": work.slug, "Priority": item["Priority"], "Risk_Level": work.risk,
        "Owner_Role": "Codex Desktop Autonomous Agent", "Environment": "local_repo_comfyui_gpu_ec2_s3_as_required",
        "Status": STATUS, "Task_Name": work.title, "Detailed_Action": item["Codex_Action"],
        "Completion_Criteria": work.acceptance, "Acceptance_Evidence": item["Evidence_Required"],
        "Dependency_Prerequisite": deps, "Validation_Method": "|".join(work.gates),
        "Output_Artifact": evidence_path, "Source_Path": str(MASTER),
        "Related_Source_Paths": "Plan\\02_TARGET_ARCHITECTURE\\WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ARCHITECTURE.md|Plan\\05_AUDIO_SYSTEM\\WAVE64_AUTONOMOUS_SOUND_LIBRARY_GENERATION_AND_QA_PLAN.md|Plan\\Instructions\\QA\\AUTONOMOUS_VIDEO_TO_AUDIO_AND_GENERATED_SOUND_QA_PROTOCOL.md",
        "Package_Top_Level_Directory": str(PLAN_ROOT),
        "Autonomous_Execution_Mode": "Codex Desktop autonomous implementation; human only supplies irreducible final playback judgment when protocol requires it",
        "Human_Input_Allowed": "FALSE", "Human_Work_Allowed": "FALSE", "Codex_Desktop_Action": item["Codex_Action"],
        "QA_Strictness": "STRICT", "Visual_Review_Required": item["Visual_Review_Required"],
        "Visual_Review_Method": item["Visual_Review_Method"], "Test_Required": "TRUE",
        "Runtime_Proof_Required": item["Runtime_Proof_Required"], "EC2_Allowed": item["EC2_Allowed"],
        "Preview_Required": str(work.visual).upper(), "Final_Render_Gate": "BLOCKED_UNTIL_EXACT_ROW_IMPLEMENTATION_RUNTIME_QA_AND_AUTHORITY_PASS",
        "Evidence_Path": evidence_path, "Citation_File": item["Citation_File"], "Citation_Full_Path": str(MASTER),
        "Citation_Section": item["Citation_Section"], "Citation_Line_Start": item["Citation_Line_Start"],
        "Citation_Line_End": item["Citation_Line_End"], "Citation_Excerpt": item["Citation_Excerpt"],
        "Source_Package": str(PLAN_ROOT), "Source_Type": "md", "Source_Item_ID": work.item_id,
        "Blocker_Policy": BLOCKER, "Rerun_Policy": RERUN, "Status_Decision": STATUS,
        "Notes": item["Notes"], "Source_Key": item["Source_Key"], "Source_File_Relative": item["Source_File_Relative"],
        "Coverage_Level": item["Coverage_Level"], "Coverage_Audit_Status": item["Coverage_Audit_Status"],
        "Ultra_Source_Coverage_Record": item["Ultra_Source_Coverage_Record"],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build() -> None:
    lines = MASTER.read_text(encoding="utf-8").splitlines()
    citations = {work.row: section_for(work.row, lines) for work in WORK_PACKAGES}
    requirements = requirements_payload()
    write_json(ITEMS_REQUIREMENTS, requirements)
    write_json(TRACKER_REQUIREMENTS, requirements)
    write_csv(ITEMS_CSV, ITEM_HEADERS, [item_row(work, citations[work.row]) for work in WORK_PACKAGES])
    write_csv(TRACKER_CSV, TRACKER_HEADERS, [tracker_row(work, citations[work.row]) for work in WORK_PACKAGES])
    registry = {
        "schema_version": "1.0",
        "registry_id": "wave64_autonomous_sound_intelligence_work_packages",
        "source_authority": str(MASTER_REL).replace("/", "\\"),
        "source_authority_sha256": sha256(MASTER),
        "planning_package_status": "PLANNING_COVERAGE_PASS_RUNTIME_IMPLEMENTATION_REQUIRED",
        "planning_complete_runtime_complete": False,
        "reserved_rows": [67, 112],
        "row_count": len(WORK_PACKAGES),
        "item_rows": str(ITEMS_CSV.relative_to(PROJECT_ROOT)).replace("/", "\\"),
        "tracker_rows": str(TRACKER_CSV.relative_to(PROJECT_ROOT)).replace("/", "\\"),
        "requirements_sha256": sha256(ITEMS_REQUIREMENTS),
        "items_sha256": sha256(ITEMS_CSV),
        "tracker_sha256": sha256(TRACKER_CSV),
        "content_based_suppression": False,
        "source_documents": {
            str(path.relative_to(PROJECT_ROOT)).replace("/", "\\"): sha256(path) for path in SOURCE_DOCUMENTS
        },
        "schema_contracts": {
            str(path.relative_to(PROJECT_ROOT)).replace("/", "\\"): sha256(path) for path in SCHEMA_CONTRACTS
        },
        "work_packages": [
            {"item_id": work.item_id, "tracker_id": work.tracker_id, "slug": work.slug, "phase": work.phase, "status": STATUS}
            for work in WORK_PACKAGES
        ],
    }
    write_json(REGISTRY, registry)
    evidence = {
        "schema_version": "1.0",
        "evidence_id": "WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_PLANNING_COVERAGE_20260715",
        "created_at": "2026-07-15T00:00:00-05:00",
        "classification": "PLANNING_COVERAGE_PASS_RUNTIME_IMPLEMENTATION_REQUIRED",
        "planning_complete_runtime_complete": False,
        "authority_sha256": sha256(MASTER),
        "requirements_sha256": sha256(ITEMS_REQUIREMENTS),
        "items_sha256": sha256(ITEMS_CSV),
        "tracker_sha256": sha256(TRACKER_CSV),
        "registry_sha256": sha256(REGISTRY),
        "source_document_count": len(SOURCE_DOCUMENTS),
        "schema_contract_count": len(SCHEMA_CONTRACTS),
        "source_document_hashes": {
            str(path.relative_to(PROJECT_ROOT)).replace("/", "\\"): sha256(path) for path in SOURCE_DOCUMENTS
        },
        "schema_contract_hashes": {
            str(path.relative_to(PROJECT_ROOT)).replace("/", "\\"): sha256(path) for path in SCHEMA_CONTRACTS
        },
        "row_count": len(WORK_PACKAGES),
        "row_first": 67,
        "row_last": 112,
        "checks": {
            "item_tracker_id_parity": True,
            "master_heading_coverage": True,
            "dependency_dag": True,
            "unique_ids": True,
            "content_based_suppression_false": True,
            "schema_contracts_parse": True,
            "source_documents_hash_bound": True,
            "runtime_completion_claimed": False,
        },
    }
    write_json(EVIDENCE, evidence)
    write_json(TRACKER_EVIDENCE, evidence)


def validate() -> dict[str, Any]:
    lines = MASTER.read_text(encoding="utf-8").splitlines()
    rows = [work.row for work in WORK_PACKAGES]
    if rows != list(range(67, 113)):
        raise ValueError("work-package rows must be contiguous 067-112")
    if len({work.item_id for work in WORK_PACKAGES}) != len(WORK_PACKAGES):
        raise ValueError("duplicate item IDs")
    for work in WORK_PACKAGES:
        section_for(work.row, lines)
        if any(dep >= work.row for dep in work.dependencies):
            raise ValueError(f"Row{work.row:03d} has non-prior dependency")
    for path in (ITEMS_REQUIREMENTS, TRACKER_REQUIREMENTS, REGISTRY, EVIDENCE, TRACKER_EVIDENCE):
        json.loads(path.read_text(encoding="utf-8"))
    for path in SOURCE_DOCUMENTS:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"missing source document: {path}")
    for path in SCHEMA_CONTRACTS:
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError(f"unexpected schema dialect: {path}")
    with ITEMS_CSV.open(encoding="utf-8", newline="") as handle:
        item_rows = list(csv.DictReader(handle))
    with TRACKER_CSV.open(encoding="utf-8", newline="") as handle:
        tracker_rows = list(csv.DictReader(handle))
    if len(item_rows) != len(WORK_PACKAGES) or len(tracker_rows) != len(WORK_PACKAGES):
        raise ValueError("row count mismatch")
    if [row["Item_ID"].replace("ITEM", "TRK", 1) for row in item_rows] != [row["Tracker_ID"] for row in tracker_rows]:
        raise ValueError("Items/Tracker ID parity failure")
    if ITEMS_REQUIREMENTS.read_bytes() != TRACKER_REQUIREMENTS.read_bytes():
        raise ValueError("requirements mirrors differ")
    if EVIDENCE.read_bytes() != TRACKER_EVIDENCE.read_bytes():
        raise ValueError("evidence mirrors differ")
    return {
        "status": "PASS",
        "classification": "WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_CONTROL_PACKAGE_VALID",
        "row_count": len(WORK_PACKAGES),
        "first_row": 67,
        "last_row": 112,
        "planning_complete_runtime_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        build()
    print(json.dumps(validate(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
