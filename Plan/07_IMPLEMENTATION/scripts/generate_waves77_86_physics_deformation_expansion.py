from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generate_waves71_76_physics_deformation_system import (
    AUDIO_QA_GATES,
    COMMON_QA_GATES,
    COMFYUI_QA_GATES,
    ITEMS_HEADER,
    ITEMS_ROOT,
    PHYSICS_QA_GATES,
    PHYSICS_ROOT,
    PLAN,
    PLAN_MATRIX_HEADER,
    ROOT,
    TRACKER_HEADER,
    TRACKER_ROOT,
    counts_by,
    join_list,
    rel,
    write_csv,
    write_json,
    write_text,
)


CREATED_FROM = "generate_waves77_86_physics_deformation_expansion.py"
STATUS = "Deferred_Required_Not_Complete"
OWNER_DOMAIN = "physics_deformation_system"
ACTIVATION_GATE = (
    "Deferred. Activate only after the current ComfyUI foundation, Wave70 Mask Factory, "
    "Waves71-76 base physics/deformation layers, runtime lanes, cost controls, and strict QA gates "
    "are stable enough that this expansion will not derail nearer project milestones. Activation "
    "requires an explicit source-cited project decision."
)

EXPANSION_QA_GATES = [
    "deterministic_validator_result_present",
    "tool_adapter_manifest_present_when_tool_used",
    "numeric_metric_thresholds_declared",
    "llm_or_vlm_review_cannot_override_failed_metrics",
    "no_human_work_after_daz_prototype_registration",
    "daz_neutral_prototype_only_boundary_preserved",
    "cost_control_and_runtime_window_gate_pass",
]


EXTERNAL_REFERENCES = [
    {
        "name": "AWS G7e production GPU runtime",
        "url": "https://aws.amazon.com/ec2/instance-types/g7e/",
        "usage": "Production self-hosted LLM/VLM and heavy adapter execution target; use with explicit runtime windows and cost controls.",
    },
    {
        "name": "vLLM model serving",
        "url": "https://docs.vllm.ai/en/latest/models/supported_models/",
        "usage": "Candidate high-throughput self-hosted inference server for supervisor, code, and multimodal models.",
    },
    {
        "name": "Qwen VL family",
        "url": "https://github.com/QwenLM/Qwen2.5-VL",
        "usage": "Candidate self-hosted visual review model family for overlays, frame grids, maps, and generated artifacts.",
    },
    {
        "name": "Blender command line",
        "url": "https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html",
        "usage": "Primary autonomous production fitting, rigging, map baking, support-surface, and overlay backend.",
    },
    {
        "name": "SideFX Houdini batch workflow",
        "url": "https://www.sidefx.com/docs/houdini/render/batch.html",
        "usage": "Advanced procedural, Vellum, SDF, pressure, contact, and tissue simulation backend.",
    },
    {
        "name": "Unreal Python automation",
        "url": "https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python",
        "usage": "Realtime proof, Control Rig, Chaos, Deformer Graph, ML Deformer, and render-pass automation backend.",
    },
    {
        "name": "Marvelous Designer Python API",
        "url": "https://developer.marvelousdesigner.com/",
        "usage": "Garment, blanket, sheet, fabric tension, cloth stretch, and cloth/body collision backend.",
    },
    {
        "name": "Substance Automation Toolkit",
        "url": "https://adobedocs.github.io/substance-automation-toolkit/",
        "usage": "Batch material, normal, roughness, displacement, curvature, AO, pressure, wrinkle, fabric, and tension map baking.",
    },
    {
        "name": "Maya command line and Python",
        "url": "https://help.autodesk.com/view/MAYAUL/2026/ENU/",
        "usage": "Production rigging, skinning, blendshape, pose-space deformation, muscle, Bifrost, and validation backend.",
    },
    {
        "name": "MotionBuilder Python SDK",
        "url": "https://help.autodesk.com/view/MOBPRO/2026/ENU/",
        "usage": "Mocap, retargeting, HumanIK, characterization, takes, story, relation constraints, and batch FBX animation handling.",
    },
    {
        "name": "Cascadeur Python scripting",
        "url": "https://cascadeur.com/help",
        "usage": "Optional physics-aware animation cleanup, balance, AutoPosing, AutoPhysics, contact timing, and motion plausibility backend.",
    },
    {
        "name": "ZBrush ZScript",
        "url": "https://help.maxon.net/zbr/en-us/Content/html/user-guide/customizing-zbrush/zscripting/command-reference/command-reference.html",
        "usage": "Offline/source asset creation for universal base sculpt, alphas, pores, wrinkles, displacement, and corrective sculpt references.",
    },
]


def req(
    category: str,
    title: str,
    target: str,
    autonomous_behavior: str,
    acceptance: str,
    evidence: list[str],
    qa: list[str] | None = None,
    *,
    priority: str = "P2",
    risk: str = "High",
    visual: bool = True,
    video: bool = True,
    audio: bool = False,
    comfyui: bool = True,
    backend: bool = True,
    notes: str = "",
) -> dict[str, Any]:
    qa_gates = list(COMMON_QA_GATES)
    qa_gates.extend(PHYSICS_QA_GATES)
    qa_gates.extend(qa or [])
    qa_gates.extend(EXPANSION_QA_GATES)
    if comfyui:
        qa_gates.extend(COMFYUI_QA_GATES)
    if audio:
        qa_gates.extend(AUDIO_QA_GATES)
    qa_gates = list(dict.fromkeys(qa_gates))
    return {
        "category": category,
        "title": title,
        "implementation_target": target,
        "autonomous_behavior": autonomous_behavior,
        "acceptance_criteria": acceptance,
        "required_evidence": evidence,
        "qa_gates": qa_gates,
        "priority": priority,
        "risk": risk,
        "visual_review_required": visual,
        "video_review_required": video,
        "audio_review_required": audio,
        "comfyui_integration_required": comfyui,
        "simulation_backend_required": backend,
        "notes": notes,
    }


def system_req(category: str, target: str, title: str, purpose: str, output: str, *, audio: bool = False, priority: str = "P2", risk: str = "High") -> dict[str, Any]:
    return req(
        category,
        title,
        target,
        (
            f"Autonomously define, execute when activated, validate, and evidence {target}. "
            f"It must support {purpose}, operate after DAZ neutral prototype registration without human work, "
            "write exact blockers when prerequisites are unavailable, and avoid docs-only completion."
        ),
        (
            f"{target} is complete only when it has schema/config, adapter or deterministic implementation route, "
            f"{output}, manifest hashes, preview or overlay evidence, strict whole-artifact review, and source-cited QA."
        ),
        [
            f"{target}_schema_or_contract_json",
            f"{target}_execution_or_adapter_manifest_json",
            f"{target}_artifact_manifest_with_hashes",
            f"{target}_preview_overlay_or_metric_report",
            f"{target}_strict_qa_report_json",
        ],
        [
            "input_contract_validated",
            "output_manifest_hashes_validated",
            "visual_overlay_or_metric_threshold_pass",
            "rerun_policy_declared",
            "blocker_policy_declared",
        ],
        audio=audio,
        priority=priority,
        risk=risk,
        notes=f"Purpose: {purpose}. Required output: {output}.",
    )


def tool_req(category: str, target: str, title: str, tool_role: str, required_capabilities: str, *, priority: str = "P2", risk: str = "High") -> dict[str, Any]:
    return req(
        category,
        title,
        target,
        (
            f"Register {target} as a controlled backend adapter, not an interactive manual tool. "
            "The adapter must expose version/license checks, command templates, smoke tests, input JSON, timeout/watchdog, logs, "
            "output manifests, hash manifests, QA evidence, and fallback/blocker behavior."
        ),
        (
            f"{target} passes only when the autonomous adapter proves the tool can perform {tool_role}, "
            f"supports {required_capabilities}, and produces machine-readable evidence without human intervention after registration."
        ),
        [
            f"{target}_availability_license_version_check_json",
            f"{target}_batch_smoke_test_log",
            f"{target}_adapter_input_schema_json",
            f"{target}_adapter_output_manifest_json",
            f"{target}_qa_evidence_json",
        ],
        [
            "tool_version_recorded",
            "license_or_availability_status_recorded",
            "batch_smoke_test_pass_or_blocker_written",
            "adapter_timeout_watchdog_present",
            "fallback_route_declared",
        ],
        priority=priority,
        risk=risk,
        notes=f"Tool role: {tool_role}. Required capabilities: {required_capabilities}.",
    )


def all_specs() -> list[dict[str, Any]]:
    return [
        {
            "wave": 77,
            "slug": "autonomous_physics_ai_supervisor_multimodal_review_agent",
            "title": "Autonomous Physics AI Supervisor And Multimodal Review Agent",
            "purpose": "Add the G7e-backed self-hosted LLM/VLM supervisor stack that plans, reviews, corrects, blocks, and records evidence for the full autonomous DAZ-to-physics-to-ComfyUI pipeline.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Self Hosted Supervisor Runtime",
                    "category": "self_hosted_supervisor_runtime",
                    "rows": [
                        system_req("self_hosted_supervisor_runtime", "g7e_llm_runtime_profile", "Define G7e LLM runtime profile", "G7e.2xlarge, G7e.4xlarge, and G7e.12xlarge selection for supervisor, VLM, code, RAG, and adapter workloads", "runtime profile with cost and concurrency limits", priority="P1"),
                        system_req("self_hosted_supervisor_runtime", "vllm_sglang_tgi_serving_adapter", "Define self-hosted model serving adapter", "vLLM, SGLang, or TGI style inference serving with health checks and model registry binding", "model server adapter manifest", priority="P1"),
                        system_req("self_hosted_supervisor_runtime", "supervisor_reasoning_model_registry", "Register supervisor reasoning model", "high-end reasoning/planning model for work orders, rerun decisions, tracker updates, and blocker writing", "model registry record and prompt contract", priority="P1"),
                        system_req("self_hosted_supervisor_runtime", "visual_review_vlm_registry", "Register visual review VLM", "multimodal review of DAZ references, fitted mesh overlays, masks, maps, frame grids, and generated outputs", "VLM registry record and review prompt pack", priority="P1"),
                        system_req("self_hosted_supervisor_runtime", "code_adapter_model_registry", "Register code and adapter model", "Blender Python, Maya Python, Houdini scripts, validators, schema fixes, and adapter repair", "code model registry record", priority="P2"),
                        system_req("self_hosted_supervisor_runtime", "small_fast_local_model_registry", "Register cheap routine helper model", "low-cost JSON checks, summaries, routing, and simple review so expensive G7e calls are minimized", "small model registry record"),
                    ],
                },
                {
                    "title": "Supervisor RAG And Evidence Memory",
                    "category": "supervisor_rag_evidence_memory",
                    "rows": [
                        system_req("supervisor_rag_evidence_memory", "plan_items_tracker_rag_index", "Build Plan Items Tracker RAG index", "retrieval over Plan, Items, Tracker, schemas, evidence, adapter docs, tool docs, and past QA reports", "versioned RAG index manifest", priority="P1"),
                        system_req("supervisor_rag_evidence_memory", "physics_tool_manual_index", "Build physics tool manual index", "tool-specific retrieval for Blender, Houdini, Unreal, Maya, MotionBuilder, Cascadeur, Marvelous, Substance, ZBrush, and ComfyUI nodes", "tool manual citation index"),
                        system_req("supervisor_rag_evidence_memory", "evidence_first_decision_policy", "Define evidence-first decision policy", "hard rule that LLM/VLM review cannot override failed deterministic geometry, map, contact, or QA metrics", "decision policy JSON", priority="P1"),
                        system_req("supervisor_rag_evidence_memory", "hallucination_guardrail_contract", "Define hallucination guardrail contract", "source citations, exact evidence paths, no guessed pass/fail, confidence scores, and blocker on missing evidence", "guardrail contract JSON", priority="P1"),
                        system_req("supervisor_rag_evidence_memory", "supervisor_audit_trail", "Build supervisor audit trail", "every model decision, prompt, input artifact hash, output decision, correction, rerun, or blocker", "supervisor audit JSONL manifest", priority="P1"),
                    ],
                },
                {
                    "title": "Supervisor Work Orders And Corrections",
                    "category": "supervisor_work_orders_corrections",
                    "rows": [
                        system_req("supervisor_work_orders_corrections", "daz_prototype_to_work_order_planner", "Plan DAZ prototype work order", "convert registered neutral DAZ prototype into a complete autonomous fitting, inference, map, simulation, ComfyUI, and QA work order", "work order JSON", priority="P1"),
                        system_req("supervisor_work_orders_corrections", "adapter_selection_policy", "Select backend adapters", "choose Blender, Maya, Houdini, Unreal, Marvelous, Substance, MotionBuilder, Cascadeur, or fallback routes by capability and cost", "adapter selection report", priority="P1"),
                        system_req("supervisor_work_orders_corrections", "rerun_adjustment_policy", "Define rerun and adjustment policy", "parameter correction for fit weights, stiffness, damping, collision proxy, support surface compression, grip force, and ComfyUI conditioning", "rerun decision JSON"),
                        system_req("supervisor_work_orders_corrections", "tracker_items_hydration_update_policy", "Update tracker items and hydration", "write only source-cited ledger and hydration updates when actual evidence changes; avoid housekeeping loops", "ledger update evidence"),
                        system_req("supervisor_work_orders_corrections", "g7e_cost_runtime_window_policy", "Define G7e runtime cost window", "start/stop, TTL, watchdog, artifacts, and final stopped-state verification for model supervisor runs", "G7e runtime window evidence", priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 78,
            "slug": "ultimate_toolchain_adapter_registry",
            "title": "Ultimate Toolchain Adapter Registry",
            "purpose": "Register every tool and plugin discussed for the future physics/deformation system as an autonomous adapter, offline asset source, optional backend, or blocked dependency.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Core Runtime Tool Adapters",
                    "category": "core_runtime_tool_adapters",
                    "rows": [
                        tool_req("core_runtime_tool_adapters", "daz_neutral_prototype_export_adapter", "DAZ neutral prototype export adapter", "neutral A/T-pose prototype export only", "source scene, FBX/OBJ, textures, reference renders, hashes, and no runtime DAZ deformation", priority="P1"),
                        tool_req("core_runtime_tool_adapters", "diffeomorphic_daz_import_adapter", "Diffeomorphic DAZ import adapter", "optional DAZ-to-Blender import route", "Genesis geometry import, materials, metadata, and reference conversion without production rig authority"),
                        tool_req("core_runtime_tool_adapters", "blender_core_background_adapter", "Blender core background adapter", "primary production fitting, rigging, maps, support surfaces, overlays, and exports", "Python background mode, geometry nodes, simulation nodes, cloth, soft body, shape keys, drivers, armature, mesh deform, surface deform, lattice, data transfer, Alembic, USD, and FBX", priority="P1"),
                        tool_req("core_runtime_tool_adapters", "houdini_fx_batch_adapter", "Houdini FX batch adapter", "advanced procedural/SDF/Vellum/tissue simulation", "hython/hbatch, Vellum, SDF fields, KineFX, PDG/TOPs, HQueue, Solaris, and USD", priority="P1"),
                        tool_req("core_runtime_tool_adapters", "unreal_engine_python_adapter", "Unreal Engine Python adapter", "realtime proof and rendered pass backend", "Control Rig, IK Rig/Retargeter, Sequencer, Chaos Cloth, Panel Cloth, Chaos Flesh, Deformer Graph, ML Deformer, geometry cache, Alembic, USD, and Movie Render Queue", priority="P1"),
                        tool_req("core_runtime_tool_adapters", "marvelous_clo_python_adapter", "Marvelous Designer CLO adapter", "garment, blanket, sheet, fabric pressure, cloth/body collision, and drape simulation", "Python/plugin automation, garment physical properties, Alembic, FBX, OBJ, and USD export", priority="P1"),
                        tool_req("core_runtime_tool_adapters", "comfyui_physics_conditioning_adapter", "ComfyUI physics conditioning adapter", "final image/video/audio conditioning and generation", "ControlNet, IPAdapter, inpaint/detailer, video nodes, masks, depth, normal, segmentation, optical flow, and QA manifests", priority="P1"),
                    ],
                },
                {
                    "title": "Blender Addon Tool Adapters",
                    "category": "blender_addon_tool_adapters",
                    "rows": [
                        tool_req("blender_addon_tool_adapters", "auto_rig_pro_adapter", "Auto-Rig Pro adapter", "production rigging, retargeting, and export", "autonomous rig generation checks, bone naming, retarget, FBX, and GLTF"),
                        tool_req("blender_addon_tool_adapters", "voxel_heat_diffuse_skinning_adapter", "Voxel Heat Diffuse Skinning adapter", "automatic skin weighting for complex or overlapping meshes", "skin-weight pass/fail overlays and deformation smoke evidence"),
                        tool_req("blender_addon_tool_adapters", "faceform_r3ds_wrap_adapter", "Faceform R3DS Wrap adapter", "high-quality non-rigid fitting of universal topology to DAZ/reference shape", "landmark wrap, topology preservation, distance heatmaps, and fit overlays", priority="P1"),
                        tool_req("blender_addon_tool_adapters", "retopoflow_fallback_adapter", "RetopoFlow fallback adapter", "manual/semi-auto retopology fallback only when stable topology cannot be fit", "blocked-by-human policy unless automated path exists"),
                        tool_req("blender_addon_tool_adapters", "quad_remesher_fallback_adapter", "Quad Remesher fallback adapter", "fast quad retopo fallback for non-production proxy assets", "proxy-only topology report and no replacement of universal production mesh"),
                        tool_req("blender_addon_tool_adapters", "faceit_adapter", "Faceit adapter", "facial shape keys, expression controls, facial mocap or validation", "identity-safe face region controls and expression QA"),
                        tool_req("blender_addon_tool_adapters", "keentools_facebuilder_facetracker_adapter", "KeenTools FaceBuilder FaceTracker adapter", "head/face reconstruction or tracking reference", "face landmark, identity, and fit evidence"),
                        tool_req("blender_addon_tool_adapters", "cloth_weaver_simply_cloth_adapter", "Cloth Weaver Simply Cloth adapter", "fast cloth prototype and cloth setup inside Blender", "cloth setup manifest and collision proof"),
                        tool_req("blender_addon_tool_adapters", "wiggle_bones_adapter", "Wiggle Bones adapter", "spring/jiggle bone prototyping", "secondary motion approximation manifest and QA"),
                        tool_req("blender_addon_tool_adapters", "ragdoll_dynamics_blender_adapter", "Ragdoll Dynamics Blender adapter", "ragdoll and physics transform testing", "contact, balance, and motion plausibility evidence"),
                    ],
                },
                {
                    "title": "Studio Grade Specialist Tool Adapters",
                    "category": "studio_grade_specialist_tool_adapters",
                    "rows": [
                        tool_req("studio_grade_specialist_tool_adapters", "maya_mayapy_production_adapter", "Maya mayapy production adapter", "studio rigging, skinning, blendshape, pose-space deformation, muscle, Bifrost, and validation", "mayabatch/mayapy, OpenMaya, HumanIK, Time Editor, Animation Layers, skinCluster, blendShape, Delta Mush, Pose Editor, nCloth, nHair, Maya Muscle, and Bifrost", priority="P1"),
                        tool_req("studio_grade_specialist_tool_adapters", "maya_plugin_suite_adapter", "Maya plugin suite adapter", "production rig and deformation plugins", "mGear, Advanced Skeleton, ngSkinTools2, SHAPES, weightDriver, RBF Solver, Ragdoll Dynamics, Zoo Tools Pro, Maya Bonus Tools, and optional Faceware"),
                        tool_req("studio_grade_specialist_tool_adapters", "motionbuilder_retargeting_adapter", "MotionBuilder retargeting adapter", "mocap retargeting, characterization, cleanup, and batch FBX processing", "pyfbsdk, Open Reality SDK, FBX SDK, HumanIK, Actor, Control Rig, Story, Takes, and Relation Constraints"),
                        tool_req("studio_grade_specialist_tool_adapters", "cascadeur_physics_animation_adapter", "Cascadeur physics animation adapter", "physics-aware animation cleanup and motion plausibility", "AutoPosing, AutoPhysics, secondary motion, Python API, FBX/DAE export, and custom rig templates"),
                        tool_req("studio_grade_specialist_tool_adapters", "substance_3d_automation_adapter", "Substance 3D automation adapter", "batch material and texture map generation", "Painter, Designer, Sampler, Automation Toolkit, sbsbaker, sbscooker, sbsrender, sbsmutator, export presets, UDIM, OCIO, smart materials, and smart masks", priority="P1"),
                        tool_req("studio_grade_specialist_tool_adapters", "zbrush_offline_asset_source_registry", "ZBrush offline asset source registry", "offline sculpt/detail source, not required unattended runtime", "ZScript, GoZ, ZWrap, ZRemesher, Decimation Master, Multi Map Exporter, UV Master, Morph Targets, Layers, Polygroups, Project All, Surface Noise, alphas, brushes, pores, wrinkles, and corrective sculpt references"),
                        tool_req("studio_grade_specialist_tool_adapters", "mocap_source_adapter_registry", "Mocap source adapter registry", "optional mocap ingestion and retarget source handling", "Rokoko, Xsens, Move.ai, OptiTrack, Vicon, Reallusion Character Creator, AccuRIG, and iClone as optional adapters or source packages"),
                    ],
                },
                {
                    "title": "Pipeline Format And QA Tool Adapters",
                    "category": "pipeline_format_qa_tool_adapters",
                    "rows": [
                        tool_req("pipeline_format_qa_tool_adapters", "usd_openusd_scene_package_adapter", "USD OpenUSD scene package adapter", "long-term scene and asset interchange", "scene graph, variants, references, asset manifests, and unit/axis conventions"),
                        tool_req("pipeline_format_qa_tool_adapters", "alembic_simulation_cache_adapter", "Alembic simulation cache adapter", "baked cloth, body, mattress, contact, deformation, and render-pass caches", "frame count, FPS, units, hashes, and importer proof"),
                        tool_req("pipeline_format_qa_tool_adapters", "ffmpeg_video_audio_package_adapter", "FFmpeg video audio package adapter", "video/audio assembly and probe validation", "codec, duration, frame count, audio stream, AV sync, and hash evidence"),
                        tool_req("pipeline_format_qa_tool_adapters", "opencv_numpy_pytorch_open3d_trimesh_validator_stack", "Geometry and media validator stack", "automated geometry, image, video, map, and metric validation", "OpenCV, NumPy, PyTorch, Open3D, trimesh, mesh metrics, map ranges, overlays, and plots", priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 79,
            "slug": "body_composition_tissue_material_inference_solver",
            "title": "Body Composition Tissue Material Inference Solver",
            "purpose": "Convert a registered neutral DAZ prototype and fitted production mesh into per-region tissue classes, mass, stiffness, damping, elasticity, sag, jiggle, compression, collision, and confidence evidence.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Inference Inputs",
                    "category": "body_composition_inference_inputs",
                    "rows": [
                        system_req("body_composition_inference_inputs", "daz_prototype_metadata_intake", "Read DAZ prototype metadata as provenance only", "neutral A/T-pose DAZ export metadata, source files, textures, measurements, and optional prototype creation recipe as provenance only, never as runtime deformation authority", "metadata intake report", priority="P1"),
                        system_req("body_composition_inference_inputs", "regional_volume_delta_solver", "Compute regional volume deltas", "per-region volume/circumference deltas against neutral universal production base and registered body archetypes", "volume delta report", priority="P1"),
                        system_req("body_composition_inference_inputs", "surface_shape_feature_extractor", "Extract surface shape features", "fat rolls, folds, overhangs, cellulite-like surface variation, compression dents, sag contours, muscle definition, sharp cuts, and soft tissue transitions", "surface feature maps", priority="P1"),
                        system_req("body_composition_inference_inputs", "texture_normal_displacement_feature_extractor", "Extract texture normal displacement features", "normal, displacement, roughness, curvature, skin mark, pore, wrinkle, fold, and fabric tension cues", "texture feature report"),
                        system_req("body_composition_inference_inputs", "character_registry_tag_verifier", "Verify character registry tags", "user/asset tags such as skinny, athletic, very overweight, large abdomen, thick thighs, muscular, soft tissue, firm, or loose skin against geometry", "tag verification report"),
                    ],
                },
                {
                    "title": "Tissue Class Outputs",
                    "category": "body_composition_tissue_outputs",
                    "rows": [
                        system_req("body_composition_tissue_outputs", "regional_tissue_classification_map", "Classify regional tissue", "lean, muscular, dense soft tissue, soft fat, loose skin, fabric-covered, support-compressed, hard-protected, and mixed layered tissue classes", "per-region tissue class map", priority="P1"),
                        system_req("body_composition_tissue_outputs", "mass_density_parameter_map", "Infer mass density parameters", "per-region mass/density for gravity, inertia, center of mass, support load, and contact behavior", "mass density map", priority="P1"),
                        system_req("body_composition_tissue_outputs", "stiffness_damping_parameter_map", "Infer stiffness damping parameters", "per-region stiffness and damping for firm muscle, soft tissue, loose skin, fabric-covered areas, and support compression", "stiffness damping map", priority="P1"),
                        system_req("body_composition_tissue_outputs", "elasticity_rebound_parameter_map", "Infer elasticity rebound parameters", "bounce, rebound, settling, and return-to-rest behavior for soft and firm regions", "elasticity rebound map"),
                        system_req("body_composition_tissue_outputs", "sag_jiggle_ripple_parameter_map", "Infer sag jiggle ripple parameters", "gravity sag, jiggle amount, ripple amount, temporal decay, and protected anchors", "sag jiggle ripple map", priority="P1"),
                        system_req("body_composition_tissue_outputs", "compression_collision_parameter_map", "Infer compression collision parameters", "compression limits, contact deformation, collision backstops, penetration prevention, friction, and stiction", "compression collision map", priority="P1"),
                    ],
                },
                {
                    "title": "Body Archetype Rules",
                    "category": "body_composition_archetype_rules",
                    "rows": [
                        system_req("body_composition_archetype_rules", "skinny_body_profile_solver", "Define skinny body profile solver", "low soft-tissue mass, low jiggle, sharper anchors, low compression, and careful bone/joint/face/hand protection", "skinny profile evidence"),
                        system_req("body_composition_archetype_rules", "athletic_muscular_profile_solver", "Define athletic muscular profile solver", "high firmness, low sag, low loose jiggle, strong muscle tension, sharper corrective shapes, and motion-linked flexion", "athletic profile evidence"),
                        system_req("body_composition_archetype_rules", "fit_large_soft_region_profile_solver", "Define fit body with large soft-region solver", "firm torso/limbs with localized high-mass soft-body regions and protected muscular anchors", "fit large soft-region profile evidence", priority="P1"),
                        system_req("body_composition_archetype_rules", "mixed_layered_tissue_profile_solver", "Define mixed layered tissue solver", "regions where firmness and softness coexist, such as firm muscle under soft tissue or fabric-covered compression", "mixed tissue report"),
                    ],
                },
                {
                    "title": "Inference Confidence And Blockers",
                    "category": "body_composition_confidence_blockers",
                    "rows": [
                        system_req("body_composition_confidence_blockers", "inference_confidence_score", "Score tissue inference confidence", "combine morph provenance, measurements, volume deltas, shape features, texture features, and registry tags into confidence", "confidence report", priority="P1"),
                        system_req("body_composition_confidence_blockers", "low_confidence_conservative_fallback", "Define low confidence fallback", "use conservative safe profiles and write blocker instead of guessing high-risk tissue behavior", "fallback blocker evidence", priority="P1"),
                        system_req("body_composition_confidence_blockers", "tissue_inference_visual_overlay_review", "Review tissue inference overlays", "whole-body and per-region overlays for tissue class, mass, stiffness, softness, sag, contact, and protected anchors", "overlay QA report", priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 80,
            "slug": "muscle_activation_grip_force_contact_strength_system",
            "title": "Muscle Activation Grip Force And Contact Strength System",
            "purpose": "Add muscle flexion, grip strength, finger pressure, tendon tension, exertion, contact force, and audio-force alignment as first-class physics/deformation controls.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Muscle Activation Maps",
                    "category": "muscle_activation_maps",
                    "rows": [
                        system_req("muscle_activation_maps", "muscle_activation_maps", "Define muscle activation maps", "which muscles/regions are active from pose, weight bearing, grip, exertion, motion, or contact", "muscle activation maps", priority="P1"),
                        system_req("muscle_activation_maps", "muscle_flexion_maps", "Define muscle flexion maps", "localized biceps, forearms, shoulders, abdomen, thighs, calves, neck, jaw, and face tension/flexion", "muscle flexion maps", priority="P1"),
                        system_req("muscle_activation_maps", "muscle_relaxation_maps", "Define muscle relaxation maps", "return-to-rest and release behavior after flexion, load removal, grip release, or exertion decay", "muscle relaxation maps"),
                        system_req("muscle_activation_maps", "tendon_tension_maps", "Define tendon tension maps", "hand, wrist, forearm, neck, ankle, knee, and foot tendon prominence under force", "tendon tension maps"),
                        system_req("muscle_activation_maps", "skin_stretch_tension_maps", "Define skin stretch tension maps", "skin pull, stretch, fold flattening, pressure marks, and tension lines near active muscles and contacts", "skin stretch tension maps"),
                        system_req("muscle_activation_maps", "vein_prominence_maps", "Define vein prominence maps", "optional exertion-linked vascular prominence with safety and realism limits", "vein prominence maps"),
                        system_req("muscle_activation_maps", "joint_load_maps", "Define joint load maps", "load and bend pressure around shoulders, elbows, wrists, hips, knees, ankles, hands, and feet", "joint load maps"),
                    ],
                },
                {
                    "title": "Grip Force And Hand Contact",
                    "category": "grip_force_hand_contact",
                    "rows": [
                        system_req("grip_force_hand_contact", "grip_force_maps", "Define grip force maps", "light touch, hold, firm grip, squeeze, pull, brace, press, impact, and release", "grip force maps", priority="P1", audio=True),
                        system_req("grip_force_hand_contact", "finger_pad_compression_maps", "Define finger pad compression maps", "finger and palm soft contact compression with target object/body/fabric/support surface", "finger pad compression maps", priority="P1"),
                        system_req("grip_force_hand_contact", "knuckle_tendon_prominence_maps", "Define knuckle tendon prominence maps", "visible hand force response when gripping or bracing", "knuckle tendon maps"),
                        system_req("grip_force_hand_contact", "hand_contact_pressure_maps", "Define hand contact pressure maps", "contact patches, pressure intensity, contact normals, and protected neighboring regions", "hand contact pressure maps", priority="P1", audio=True),
                        system_req("grip_force_hand_contact", "object_grip_deformation_maps", "Define object grip deformation maps", "fabric, cushion, prop, clothing, soft-body, and support-surface deformation from grip or hand pressure", "object grip deformation maps", priority="P1", audio=True),
                        system_req("grip_force_hand_contact", "friction_slip_risk_maps", "Define friction slip risk maps", "slide, stick, drag, hand reposition, grip loss, and contact stability", "friction slip maps"),
                    ],
                },
                {
                    "title": "Exertion And Audio Force",
                    "category": "exertion_audio_force",
                    "rows": [
                        system_req("exertion_audio_force", "exertion_state_maps", "Define exertion state maps", "whole-body and per-region exertion from action, pose, load, repetition, contact force, and fatigue", "exertion maps", audio=True, priority="P1"),
                        system_req("exertion_audio_force", "breath_chest_expansion_maps", "Define breath chest expansion maps", "breathing, ribcage, abdomen, chest, shoulder, neck, and timing state for image/video/audio consistency", "breath expansion maps", audio=True),
                        system_req("exertion_audio_force", "pose_to_audio_force_maps", "Define pose to audio force maps", "visual force converted to foley, breath, cloth rustle, impact, support compression, and contact audio events", "audio force maps", audio=True, priority="P1"),
                        system_req("exertion_audio_force", "force_timeline_curve", "Define force timeline curve", "per-frame force, grip, muscle activation, support compression, rebound, and audio event timing", "force timeline JSON", audio=True, priority="P1"),
                        system_req("exertion_audio_force", "muscle_grip_whole_artifact_qa", "Certify muscle grip whole artifact QA", "full-frame/full-duration review for anatomy, contact, hands, fingers, force, temporal stability, and audio alignment", "muscle grip QA report", audio=True, priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 81,
            "slug": "support_surface_physics_contact_compression_deformation",
            "title": "Support Surface Physics Contact Compression And Deformation",
            "purpose": "Treat beds, mattresses, pillows, blankets, couches, chairs, floors, walls, tables, rugs, and other support objects as first-class physics surfaces with soft or hard response.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Support Surface Taxonomy",
                    "category": "support_surface_taxonomy",
                    "rows": [
                        system_req("support_surface_taxonomy", "mattress_soft_surface_profile", "Define mattress soft-surface profile", "thickness, grid density, stiffness, damping, rebound, wrinkles, fabric normals, and body load response", "mattress profile"),
                        system_req("support_surface_taxonomy", "bed_frame_hard_support_profile", "Define bed frame hard-support profile", "non-deforming rigid support, occlusion, collision, contact shadow, and mattress coupling", "bed frame profile"),
                        system_req("support_surface_taxonomy", "pillow_soft_surface_profile", "Define pillow soft-surface profile", "head/neck/hand/body compression, wrinkles, rebound, and cloth/filling behavior", "pillow profile"),
                        system_req("support_surface_taxonomy", "blanket_sheet_fabric_support_profile", "Define blanket sheet fabric support profile", "drape, stretch, wrinkle, fold, body contact, hand pull, and fabric pressure", "blanket sheet profile"),
                        system_req("support_surface_taxonomy", "couch_cushion_profile", "Define couch cushion profile", "soft seating support, multi-contact compression, rebound, fabric stretch, and crease behavior", "couch cushion profile"),
                        system_req("support_surface_taxonomy", "hard_chair_profile", "Define hard chair profile", "rigid chair contact, no deformation except contact shadow/friction/audio", "hard chair profile"),
                        system_req("support_surface_taxonomy", "hard_floor_wall_table_profile", "Define hard floor wall table profile", "rigid support surfaces with friction, contact shadow, collision, reflection, and audio force but no geometry deformation", "hard surface profile"),
                        system_req("support_surface_taxonomy", "rug_carpet_soft_floor_profile", "Define rug carpet soft-floor profile", "shallow compression, fiber direction, foot/body contact, drag, shadow, and foley", "rug carpet profile", audio=True),
                    ],
                },
                {
                    "title": "Support Surface Maps",
                    "category": "support_surface_maps",
                    "rows": [
                        system_req("support_surface_maps", "support_contact_patch_maps", "Define support contact patch maps", "where body, hands, feet, clothing, hair, props, or other characters touch support surfaces", "contact patch maps", priority="P1", audio=True),
                        system_req("support_surface_maps", "support_pressure_load_maps", "Define support pressure load maps", "pressure distribution from body mass, pose, center of mass, clothing, and multi-character contact", "pressure load maps", priority="P1"),
                        system_req("support_surface_maps", "support_compression_depth_maps", "Define support compression depth maps", "how far mattress, pillow, cushion, carpet, or soft support deforms", "compression depth maps", priority="P1"),
                        system_req("support_surface_maps", "support_displacement_normal_maps", "Define support displacement normal maps", "visible surface deformation for soft surfaces and render/control maps", "displacement normal maps"),
                        system_req("support_surface_maps", "support_wrinkle_fold_maps", "Define support wrinkle fold maps", "fabric wrinkles, cushion folds, mattress fabric tension, and blanket/sheet creases", "wrinkle fold maps"),
                        system_req("support_surface_maps", "support_contact_shadow_occlusion_maps", "Define support contact shadow occlusion maps", "shadow, occlusion, grounding, and no-floating-contact evidence for all support types", "contact shadow maps", priority="P1"),
                        system_req("support_surface_maps", "support_rebound_settling_maps", "Define support rebound settling maps", "temporal return-to-rest behavior for mattress, pillow, cushion, blanket, carpet, and soft props", "rebound settling maps"),
                        system_req("support_surface_maps", "support_surface_audio_force_maps", "Define support surface audio force maps", "bed, chair, couch, floor, fabric, creak, thump, footstep, cloth rustle, and support compression event binding", "support audio force maps", audio=True, priority="P1"),
                    ],
                },
                {
                    "title": "Support Surface QA",
                    "category": "support_surface_qa",
                    "rows": [
                        system_req("support_surface_qa", "no_floating_support_contact_gate", "Gate no floating support contact", "body parts and props must visually contact support surfaces when physics says contact exists", "no floating QA evidence", priority="P1"),
                        system_req("support_surface_qa", "no_support_penetration_gate", "Gate no support penetration", "body, clothing, props, mattress, chair, floor, or other supports cannot clip through each other", "penetration QA evidence", priority="P1"),
                        system_req("support_surface_qa", "soft_vs_hard_surface_response_gate", "Gate soft vs hard response", "soft surfaces must deform plausibly and hard surfaces must not deform except shadows/friction/audio", "surface response QA evidence", priority="P1"),
                        system_req("support_surface_qa", "support_surface_whole_artifact_review", "Review support surfaces in whole artifact", "support object correctness cannot pass if hands, face, body, background, or unrelated full-frame defects fail", "whole artifact support QA", audio=True, priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 82,
            "slug": "daz_neutral_prototype_to_production_mesh_detail_transfer",
            "title": "DAZ Neutral Prototype To Production Mesh Detail Transfer",
            "purpose": "Strengthen the DAZ boundary and the autonomous process for fitting a Blender-owned universal production mesh to a DAZ Genesis 9/8.1 neutral prototype without inheriting DAZ topology or rig quirks.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "DAZ Boundary And Intake",
                    "category": "daz_boundary_intake",
                    "rows": [
                        system_req("daz_boundary_intake", "daz_neutral_pose_only_gate", "Enforce DAZ neutral pose only gate", "DAZ provides only the neutral A/T-pose character shape, optional hair/clothing reference, textures, and reference renders", "DAZ boundary validation", priority="P1"),
                        system_req("daz_boundary_intake", "no_daz_runtime_morphing_gate", "Enforce no DAZ runtime morphing gate", "no DAZ hand pose libraries, dForce, runtime morphing, deformation, rigging, or simulation after prototype registration", "no DAZ runtime gate evidence", priority="P1"),
                        system_req("daz_boundary_intake", "daz_surface_shell_cleanup", "Clean DAZ surface shell target", "remove or isolate eyes, lashes, teeth, tongue, nails, hair, clothes, accessories, geografts, hidden surfaces, and non-body islands for wrap target creation", "DAZ shell cleanup report", priority="P1"),
                        system_req("daz_boundary_intake", "hollow_mesh_non_blocker_policy", "Define hollow mesh non-blocker policy", "treat DAZ surface shell as reference target only and generate production collision volumes/SDFs from fitted production mesh", "hollow mesh policy evidence"),
                    ],
                },
                {
                    "title": "Production Mesh Fitting",
                    "category": "production_mesh_fitting",
                    "rows": [
                        system_req("production_mesh_fitting", "universal_production_base_mesh_loader", "Load universal production base mesh", "stable topology, UVs, vertex order, rig landmarks, Wave70 mask IDs, Wave71 map IDs, anchors, and soft-body zones", "base mesh load report", priority="P1"),
                        system_req("production_mesh_fitting", "rigid_alignment_solver", "Run rigid alignment solver", "match height, scale, pelvis, head, shoulders, hips, hands, feet, and scene axes", "rigid alignment report", priority="P1"),
                        system_req("production_mesh_fitting", "landmark_alignment_solver", "Run landmark alignment solver", "match face, eyes, mouth, jaw, shoulders, elbows, wrists, hands, chest, waist, hips, knees, ankles, feet, fingers, and toes", "landmark alignment report", priority="P1"),
                        system_req("production_mesh_fitting", "lattice_cage_shape_solver", "Run lattice cage shape solver", "reshape global and regional proportions while protecting identity, hands, feet, mouth, eyes, joints, and anchors", "lattice fit report"),
                        system_req("production_mesh_fitting", "non_rigid_wrap_solver", "Run non-rigid wrap solver", "fit production mesh to DAZ/reference surface using Faceform/R3DS Wrap or Blender fallback while preserving topology", "wrap fit report", priority="P1"),
                        system_req("production_mesh_fitting", "regional_refinement_solver", "Run regional refinement solver", "refine face, hands, feet, torso, abdomen, chest, hips, thighs, arms, calves, and neck separately", "regional refinement report"),
                        system_req("production_mesh_fitting", "fit_shape_key_baker", "Bake fit as production shape key", "store fitted character shape as versioned production shape key/delta while preserving topology and maps", "shape key bake manifest"),
                    ],
                },
                {
                    "title": "Detail Transfer And Fit QA",
                    "category": "detail_transfer_fit_qa",
                    "rows": [
                        system_req("detail_transfer_fit_qa", "texture_projection_to_production_uvs", "Project textures to production UVs", "project DAZ/reference skin/material/skinmark information to production UVs without inheriting DAZ topology", "texture projection report"),
                        system_req("detail_transfer_fit_qa", "high_poly_detail_bake", "Bake high poly detail", "normal, displacement, vector displacement, pores, wrinkles, folds, skin marks, muscle cuts, and cellulite-like detail to production maps", "detail bake manifest"),
                        system_req("detail_transfer_fit_qa", "fit_distance_heatmap", "Generate fit distance heatmap", "nearest-surface distance, silhouette error, volume error, and protected-region error across reference views", "fit heatmap evidence", priority="P1"),
                        system_req("detail_transfer_fit_qa", "topology_uv_invariant_proof", "Prove topology UV invariance", "vertex count, vertex order, face order, UV layout, named groups, mask IDs, physics IDs, and anchors unchanged", "invariant proof JSON", priority="P1"),
                        system_req("detail_transfer_fit_qa", "fit_visual_overlay_certification", "Certify fit visual overlays", "front, side, back, three-quarter, close face, hands, feet, and full-body overlays reviewed by deterministic metrics and VLM", "fit overlay QA report", priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 83,
            "slug": "sculpt_material_surface_detail_map_pipeline",
            "title": "Sculpt Material And Surface Detail Map Pipeline",
            "purpose": "Add offline ZBrush source assets and autonomous Substance/Blender/Houdini material-map baking for skin, fabric, pressure, stretch, wrinkle, normal, displacement, and tension/compression detail.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "ZBrush Source Asset Boundary",
                    "category": "zbrush_source_asset_boundary",
                    "rows": [
                        system_req("zbrush_source_asset_boundary", "zbrush_universal_base_sculpt_source", "Register ZBrush universal base sculpt source", "offline high-end production sculpt reference for the universal base, not per-request manual work", "ZBrush base source registry"),
                        system_req("zbrush_source_asset_boundary", "zbrush_alpha_brush_library", "Register ZBrush alpha brush library", "pores, wrinkles, stretch marks, fabric creases, skin folds, pressure marks, and sculpt detail sources", "alpha brush manifest"),
                        system_req("zbrush_source_asset_boundary", "zbrush_corrective_sculpt_reference_library", "Register corrective sculpt reference library", "pose-space, joint, muscle, grip, support compression, face, hand, foot, and soft-body corrective references", "corrective sculpt registry"),
                        system_req("zbrush_source_asset_boundary", "zbrush_not_required_runtime_policy", "Define ZBrush not-required runtime policy", "ZBrush can provide source assets but Blender/Houdini/Maya/Substance must replace per-character unattended runtime tasks", "ZBrush boundary policy", priority="P1"),
                    ],
                },
                {
                    "title": "Substance Material Automation",
                    "category": "substance_material_automation",
                    "rows": [
                        system_req("substance_material_automation", "substance_skin_material_baker", "Bake skin material maps", "color, normal, bump, displacement, roughness, curvature, AO, pores, wrinkles, moles, scars, freckles, pressure marks, and tension maps", "skin material package", priority="P1"),
                        system_req("substance_material_automation", "substance_fabric_material_baker", "Bake fabric material maps", "stretch, folds, seams, cuffs, hems, compression, wetness, transparency/sheerness risk, and cloth tension", "fabric material package"),
                        system_req("substance_material_automation", "substance_support_surface_material_baker", "Bake support surface material maps", "mattress, cushion, pillow, blanket, rug, carpet, hard surface, friction, pressure, contact shadow, and fabric normal maps", "support material package"),
                        system_req("substance_material_automation", "substance_pressure_tension_mask_baker", "Bake pressure tension masks", "contact redness/material response, indentation detail, fabric stretch, grip pressure, and support compression", "pressure tension mask package", priority="P1"),
                        system_req("substance_material_automation", "substance_udim_ocio_export_gate", "Validate UDIM OCIO exports", "UDIM tiles, color management, texture naming, map ranges, image dimensions, hashes, and ComfyUI import route", "texture export QA report"),
                    ],
                },
                {
                    "title": "Surface Detail QA",
                    "category": "surface_detail_qa",
                    "rows": [
                        system_req("surface_detail_qa", "surface_detail_map_value_gate", "Gate surface detail map values", "normal, displacement, roughness, color, tension, compression, and wrinkle maps have valid ranges and no corrupt tiles", "map value QA report", priority="P1"),
                        system_req("surface_detail_qa", "surface_detail_identity_continuity_gate", "Gate identity and skin continuity", "detail transfer cannot alter face identity, skin tone continuity, tattoos, scars, freckles, moles, makeup, or hairline unintentionally", "identity continuity QA"),
                        system_req("surface_detail_qa", "material_visual_consistency_review", "Review material visual consistency", "whole artifact review for skin/fabric/support material realism and no unrelated full-frame defects", "material visual QA", priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 84,
            "slug": "animation_mocap_temporal_physics_pipeline",
            "title": "Animation Mocap And Temporal Physics Pipeline",
            "purpose": "Add autonomous animation, mocap, retargeting, force timelines, balance, contact timing, secondary motion, temporal maps, and video/audio synchronization for the physics system.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Motion Source And Retargeting",
                    "category": "motion_source_retargeting",
                    "rows": [
                        system_req("motion_source_retargeting", "motion_source_registry", "Register motion sources", "procedural animation, mocap clips, hand-authored source clips, Cascadeur outputs, MotionBuilder takes, Unreal sequences, and Blender actions", "motion source registry"),
                        system_req("motion_source_retargeting", "skeleton_characterization_solver", "Solve skeleton characterization", "map source skeletons to production rig landmarks, HumanIK, Control Rig, KineFX, or Blender rig equivalents", "characterization report", priority="P1"),
                        system_req("motion_source_retargeting", "retarget_scale_stride_solver", "Solve retarget scale and stride", "match body height, limb length, center of mass, stride, hand reach, foot contact, and support contact", "retarget QA report", priority="P1"),
                        system_req("motion_source_retargeting", "motionbuilder_batch_retarget_route", "Define MotionBuilder batch retarget route", "pyfbsdk batch characterization, retarget, take cleanup, constraints, and FBX export", "MotionBuilder route evidence"),
                        system_req("motion_source_retargeting", "cascadeur_physics_cleanup_route", "Define Cascadeur physics cleanup route", "AutoPosing, AutoPhysics, balance, arcs, contact timing, and secondary motion plausibility", "Cascadeur route evidence"),
                    ],
                },
                {
                    "title": "Temporal Physics Maps",
                    "category": "temporal_physics_maps",
                    "rows": [
                        system_req("temporal_physics_maps", "per_frame_pose_force_timeline", "Generate per-frame pose force timeline", "pose, grip, contact, muscle activation, support load, gravity, velocity, acceleration, and audio event force", "pose force timeline", audio=True, priority="P1"),
                        system_req("temporal_physics_maps", "optical_flow_motion_vector_maps", "Generate optical flow motion vector maps", "frame-to-frame motion, deformation, repair spans, temporal conditioning, and ComfyUI video routes", "optical flow maps"),
                        system_req("temporal_physics_maps", "secondary_motion_decay_maps", "Generate secondary motion decay maps", "jiggle, rebound, ripple, support settling, fabric sway, hair sway, and muscle release decay", "secondary motion maps", priority="P1"),
                        system_req("temporal_physics_maps", "contact_persistence_maps", "Generate contact persistence maps", "hand, foot, body, clothing, support surface, and multi-character contacts across frames", "contact persistence maps", priority="P1", audio=True),
                        system_req("temporal_physics_maps", "temporal_repair_span_isolation", "Isolate temporal repair spans", "only bad frames/regions are repaired while identity, clothing, body shape, and support contact remain stable", "repair span manifest"),
                    ],
                },
                {
                    "title": "Temporal QA",
                    "category": "temporal_physics_qa",
                    "rows": [
                        system_req("temporal_physics_qa", "balance_gravity_plausibility_gate", "Gate balance gravity plausibility", "center of mass, support polygon, gravity vector, contact points, and no impossible floating/leaning", "balance QA report", priority="P1"),
                        system_req("temporal_physics_qa", "temporal_anatomy_drift_gate", "Gate temporal anatomy drift", "face, identity, hands, fingers, feet, body shape, muscle/fat behavior, clothing, support surfaces, and props remain coherent", "temporal anatomy QA", priority="P1"),
                        system_req("temporal_physics_qa", "audio_visual_force_sync_gate", "Gate audio visual force sync", "force intensity and timing in visual contact matches foley, breath, impact, rustle, support compression, and AV sync", "AV force QA", audio=True, priority="P1"),
                    ],
                },
            ],
        },
        {
            "wave": 85,
            "slug": "end_to_end_autonomous_physics_work_order_orchestration",
            "title": "End To End Autonomous Physics Work Order Orchestration",
            "purpose": "Define the full no-human-work state machine from registered DAZ neutral prototype through production fitting, tissue inference, maps, tools, ComfyUI package, generation, QA, blockers, and release evidence.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Work Order State Machine",
                    "category": "work_order_state_machine",
                    "rows": [
                        system_req("work_order_state_machine", "registered_daz_to_work_order_state", "Start registered DAZ work order state", "validate source hashes, neutral pose, metadata, reference renders, and allowed use before any automated processing", "state manifest", priority="P1"),
                        system_req("work_order_state_machine", "production_fit_state", "Run production fit state", "invoke W82 fitting, invariant gates, detail transfer, heatmaps, and fit QA", "fit state evidence", priority="P1"),
                        system_req("work_order_state_machine", "tissue_inference_state", "Run tissue inference state", "invoke W79 tissue class, mass, stiffness, damping, sag, jiggle, compression, and confidence scoring", "tissue state evidence", priority="P1"),
                        system_req("work_order_state_machine", "rig_collision_map_state", "Run rig collision map state", "invoke W73 plus W80/W81 maps for rig, collision, gravity, support, muscle, grip, and contact", "rig collision state evidence", priority="P1"),
                        system_req("work_order_state_machine", "simulation_adapter_state", "Run simulation adapter state", "select and execute Blender, Houdini, Unreal, Maya, Marvelous, Substance, MotionBuilder, Cascadeur, or fallback routes", "adapter state evidence", priority="P1"),
                        system_req("work_order_state_machine", "comfyui_conditioning_state", "Run ComfyUI conditioning state", "package pose, depth, normal, mask, segmentation, contact, deformation, support, muscle, force, and temporal maps", "ComfyUI package evidence", priority="P1"),
                        system_req("work_order_state_machine", "generation_and_qa_state", "Run generation and QA state", "generate proof artifacts and perform full visual, video, audio, geometry, physics, and ledger QA", "generation QA evidence", priority="P1", audio=True),
                    ],
                },
                {
                    "title": "Autonomous Failure And Fallback",
                    "category": "autonomous_failure_fallback",
                    "rows": [
                        system_req("autonomous_failure_fallback", "missing_tool_fallback_policy", "Define missing tool fallback policy", "fallback from specialist tool to Blender/Houdini/Maya/ComfyUI approximation or blocker without looping", "fallback policy evidence", priority="P1"),
                        system_req("autonomous_failure_fallback", "license_unavailable_blocker_policy", "Define license unavailable blocker policy", "write exact blocker and continue eligible local-first work when paid tool/license is unavailable", "license blocker evidence"),
                        system_req("autonomous_failure_fallback", "low_confidence_blocker_policy", "Define low confidence blocker policy", "block when geometry/tissue/contact/visual review is uncertain rather than guessing physics parameters", "low confidence blocker evidence", priority="P1"),
                        system_req("autonomous_failure_fallback", "retry_budget_policy", "Define retry budget policy", "bounded reruns only when changed input, changed parameter, or new evidence exists", "retry budget report", priority="P1"),
                        system_req("autonomous_failure_fallback", "no_housekeeping_loop_policy", "Define no housekeeping loop policy", "avoid repeated docs, indexes, validators, hydration, and evidence churn without new implementation/runtime/QA inputs", "no-loop evidence", priority="P1"),
                    ],
                },
                {
                    "title": "Manifests And Provenance",
                    "category": "manifests_provenance",
                    "rows": [
                        system_req("manifests_provenance", "physics_work_order_manifest", "Build physics work order manifest", "single manifest tying prototype, production base, tools, adapters, maps, generated media, QA, and tracker rows", "work order manifest", priority="P1"),
                        system_req("manifests_provenance", "artifact_hash_chain", "Build artifact hash chain", "hash every input, intermediate map, simulation cache, texture, render pass, ComfyUI package, output media, and QA report", "hash chain manifest", priority="P1"),
                        system_req("manifests_provenance", "source_citation_to_tracker_linker", "Link source citations to tracker rows", "every work order stage cites Plan, Items, Tracker, evidence, and generated artifacts", "citation linker report"),
                        system_req("manifests_provenance", "release_candidate_packet", "Build release candidate packet", "final proof package for the physics/deformation system with pass/fail and known boundaries", "release candidate packet", priority="P1", audio=True),
                    ],
                },
            ],
        },
        {
            "wave": 86,
            "slug": "expanded_physics_deformation_final_certification_gates",
            "title": "Expanded Physics Deformation Final Certification Gates",
            "purpose": "Add final strict certification for the expanded waves: tool adapters, AI supervisor, tissue inference, muscle/grip, support surfaces, animation, materials, work orders, visual/video/audio, and cost-safe runtime behavior.",
            "activation_gate": ACTIVATION_GATE,
            "sections": [
                {
                    "title": "Deterministic Certification",
                    "category": "deterministic_certification",
                    "rows": [
                        system_req("deterministic_certification", "topology_invariant_certification", "Certify topology invariants", "production mesh topology, UVs, vertex order, groups, anchors, masks, maps, and rig compatibility remain valid", "topology certification", priority="P1"),
                        system_req("deterministic_certification", "geometry_metric_certification", "Certify geometry metrics", "landmarks, silhouette, distance heatmaps, volume deltas, region maps, body proportions, and fit thresholds", "geometry metric certification", priority="P1"),
                        system_req("deterministic_certification", "physics_map_certification", "Certify physics maps", "mass, stiffness, damping, elasticity, sag, jiggle, ripple, collision, contact, support, force, and temporal maps", "physics map certification", priority="P1"),
                        system_req("deterministic_certification", "tool_adapter_certification", "Certify tool adapters", "availability, version, license, batch smoke, output manifest, timeout, fallback, and QA for every registered tool", "tool adapter certification", priority="P1"),
                        system_req("deterministic_certification", "g7e_supervisor_certification", "Certify G7e supervisor", "LLM/VLM runtime, RAG, evidence-first policy, cost windows, audit trails, and no-vibe-only decisions", "supervisor certification", priority="P1"),
                    ],
                },
                {
                    "title": "Visual Video Audio Certification",
                    "category": "visual_video_audio_certification",
                    "rows": [
                        system_req("visual_video_audio_certification", "whole_image_visual_certification", "Certify whole image visual QA", "prompt alignment, identity, face, eyes, teeth, hands, fingers, feet, anatomy, clothing, props, background, support, contact, and artifacts", "whole image QA", priority="P1"),
                        system_req("visual_video_audio_certification", "full_duration_video_certification", "Certify full duration video QA", "frame grids plus playback for drift, flicker, temporal popping, contact persistence, deformation, support surfaces, and loop/cut boundaries", "video QA", priority="P1", audio=True),
                        system_req("visual_video_audio_certification", "full_duration_audio_certification", "Certify full duration audio QA", "clipping, noise, voice, intelligibility, foley, mix, ambience, spatial match, force timing, AV sync, and drift", "audio QA", priority="P1", audio=True),
                        system_req("visual_video_audio_certification", "localized_review_insufficient_gate", "Gate localized review insufficiency", "target-region edits cannot pass if unrelated full-frame/full-duration defects exist", "localized review gate", priority="P1", audio=True),
                        system_req("visual_video_audio_certification", "support_muscle_tissue_contact_certification", "Certify support muscle tissue contact", "body tissue, muscles, grip, support surfaces, hard/soft contact, collision, compression, rebound, and audio force align", "support muscle tissue contact certification", priority="P1", audio=True),
                    ],
                },
                {
                    "title": "Final Autonomous Release Gates",
                    "category": "final_autonomous_release_gates",
                    "rows": [
                        system_req("final_autonomous_release_gates", "no_human_work_certification", "Certify no human work after registration", "after DAZ neutral prototype registration, every tool, adapter, review, correction, QA, and blocker is autonomous", "no human work certification", priority="P1"),
                        system_req("final_autonomous_release_gates", "cost_control_certification", "Certify cost control", "local-first, CI/package-first, bounded G7e/EC2 runtime windows, TTLs, watchdogs, stop verification, and artifact pullback", "cost certification", priority="P1"),
                        system_req("final_autonomous_release_gates", "blocked_state_certification", "Certify blocked state handling", "unavailable tools, missing licenses, uncertain inference, failed QA, or impossible physics are blocked precisely and do not loop", "blocked state certification", priority="P1"),
                        system_req("final_autonomous_release_gates", "end_to_end_release_readiness_gate", "Gate end to end release readiness", "all waves 71-86 have evidence, generated artifacts where applicable, strict QA, target-runtime proof before final, and source-cited tracker closure", "release readiness packet", priority="P1", audio=True),
                    ],
                },
            ],
        },
    ]


def build_plan_markdown(spec: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    wave = spec["wave"]
    lines: list[str] = [
        f"# Wave{wave} {spec['title']}",
        "",
        f"Purpose: {spec['purpose']}",
        "",
        f"Activation gate: {spec['activation_gate']}",
        "",
        "This wave is intentionally deferred. It is included so the autonomous project has exact end-to-end planning, Items, Tracker rows, QA gates, and future implementation instructions. It must not displace nearer active ComfyUI runtime, workflow, cost-control, Mask Factory, or current-lane work.",
        "",
        "DAZ boundary: DAZ is only a neutral A-pose or T-pose prototype source. After prototype registration, DAZ must not be used for runtime morphing, grip posing, hand posing, dForce simulation, production rigging, or production deformation. Blender, Maya, Houdini, Unreal, Marvelous, Substance, ComfyUI, and validated adapters own the autonomous downstream pipeline.",
        "",
        "Autonomy rule: after any user-supplied DAZ prototype/reference asset is registered, all setup, conversion, adapter execution, map generation, routing, testing, QA, visual review, video review, audio review, correction, rerun, tracker update, and blocker recording must be autonomous.",
        "",
        "Strict QA rule: no row can be promoted from documentation, taxonomy presence, a single smoke artifact, a model review without deterministic evidence, or target-region-only review. Generated outputs require whole-artifact visual review and, for video/audio work, full-duration temporal/audio review.",
        "",
        "Evidence-first supervisor rule: LLM/VLM review can recommend, route, and interpret, but it cannot override failed deterministic metrics for topology, geometry, maps, collision, support contact, audio sync, or whole-artifact QA.",
        "",
        "External references:",
        "",
    ]
    for ref in EXTERNAL_REFERENCES:
        lines.append(f"- {ref['name']}: {ref['url']} -- {ref['usage']}")
    lines.append("")

    line_map: dict[str, dict[str, Any]] = {}
    for section in spec["sections"]:
        section_title = section["title"]
        category = section["category"]
        start = len(lines) + 1
        lines.extend(
            [
                f"## {section_title}",
                "",
                f"Source key prefix: W{wave}:{category}",
                "",
                "Completion rule: every row in this section remains Deferred_Required_Not_Complete until activation gate, implementation artifacts, adapter evidence, preview/overlay evidence, strict QA, and promotion evidence all pass.",
                "",
                "| requirement | implementation_target | autonomous_behavior | acceptance_summary |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in section["rows"]:
            lines.append(
                f"| {row['title']} | {row['implementation_target']} | {row['autonomous_behavior']} | {row['acceptance_criteria']} |"
            )
        end = len(lines)
        line_map[category] = {"section": section_title, "line_start": start, "line_end": end}
        lines.append("")
    return lines, line_map


def enrich_rows(spec: dict[str, Any], line_map: dict[str, dict[str, Any]], plan_md: Path) -> list[dict[str, Any]]:
    wave = spec["wave"]
    rows: list[dict[str, Any]] = []
    file_size = plan_md.stat().st_size
    index = 1
    for section in spec["sections"]:
        source = line_map[section["category"]]
        for item in section["rows"]:
            source_key = f"W{wave}:{item['category']}:{item['implementation_target']}"
            enriched = dict(item)
            enriched.update(
                {
                    "requirement_id": f"W{wave}-{index:04d}",
                    "item_id": f"ITEM-W{wave}-{index:04d}",
                    "tracker_id": f"TRK-W{wave}-{index:04d}",
                    "source_key": source_key,
                    "source_file_relative": rel(plan_md),
                    "citation_section": source["section"],
                    "citation_line_start": source["line_start"],
                    "citation_line_end": source["line_end"],
                    "source_file_size": file_size,
                }
            )
            rows.append(enriched)
            index += 1
    return rows


def build_plan_matrix_rows(spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "requirement_id": item["requirement_id"],
            "wave": spec["wave"],
            "category": item["category"],
            "title": item["title"],
            "implementation_target": item["implementation_target"],
            "autonomous_behavior": item["autonomous_behavior"],
            "acceptance_criteria": item["acceptance_criteria"],
            "required_evidence": join_list(item["required_evidence"]),
            "qa_gates": join_list(item["qa_gates"]),
            "visual_review_required": str(item["visual_review_required"]).lower(),
            "video_review_required": str(item["video_review_required"]).lower(),
            "audio_review_required": str(item["audio_review_required"]).lower(),
            "comfyui_integration_required": str(item["comfyui_integration_required"]).lower(),
            "simulation_backend_required": str(item["simulation_backend_required"]).lower(),
            "deferred_status": STATUS,
            "activation_gate": spec["activation_gate"],
            "source_key": item["source_key"],
            "source_file_relative": item["source_file_relative"],
            "citation_section": item["citation_section"],
            "citation_line_start": item["citation_line_start"],
            "citation_line_end": item["citation_line_end"],
        }
        for item in rows
    ]


def build_item_rows(spec: dict[str, Any], rows: list[dict[str, Any]], plan_md: Path) -> list[dict[str, Any]]:
    item_rows = []
    for item in rows:
        item_rows.append(
            {
                "Item_ID": item["item_id"],
                "Item_Wave": spec["wave"],
                "Item_Type": "deferred_physics_deformation_expansion_requirement",
                "Item_Title": item["title"],
                "Item_Category": spec["title"],
                "Item_Domain": item["category"],
                "Owner_Domain": OWNER_DOMAIN,
                "Autonomous_Required": "TRUE",
                "Human_Input_Allowed": "FALSE",
                "Human_Work_Allowed": "FALSE",
                "Codex_Action": "Do not implement before activation gate. When activated, implement or block this requirement with source-cited autonomous evidence and strict QA.",
                "Implementation_Target": item["implementation_target"],
                "Deliverable_Type": "plan_contract_adapter_or_artifact_validation_strict_qa_evidence",
                "Acceptance_Criteria": item["acceptance_criteria"],
                "QA_Gates_Required": join_list(item["qa_gates"]),
                "Visual_Review_Required": "TRUE" if item["visual_review_required"] else "FALSE",
                "Visual_Review_Method": "strict_whole_artifact_plus_map_overlay_plus_target_region_review",
                "Test_Required": "TRUE",
                "Evidence_Required": join_list(item["required_evidence"]),
                "Runtime_Proof_Required": "TRUE",
                "EC2_Allowed": "FALSE",
                "Blocker_Policy": "If unavailable or blocked, record exact blocker and continue nearer active project work; do not start housekeeping loops.",
                "Source_Plan_Root": str(PLAN),
                "Citation_File": plan_md.name,
                "Citation_Full_Path": str(plan_md),
                "Citation_Section": item["citation_section"],
                "Citation_Line_Start": item["citation_line_start"],
                "Citation_Line_End": item["citation_line_end"],
                "Citation_Excerpt": f"Wave{spec['wave']} defines {item['implementation_target']} as a deferred autonomous physics/deformation expansion requirement.",
                "Source_Package": f"Wave{spec['wave']} {spec['title']}",
                "Source_Type": "Plan Source",
                "Source_File_Size": item["source_file_size"],
                "Priority": item["priority"],
                "Risk_Level": item["risk"],
                "Status": STATUS,
                "Created_From": CREATED_FROM,
                "Notes": item["notes"],
                "Source_Key": item["source_key"],
                "Source_File_Relative": item["source_file_relative"],
                "Coverage_Level": "deferred_direct_physics_deformation_expansion_requirement",
                "Coverage_Audit_Status": "source_cited_deferred_required_not_complete",
                "Ultra_Source_Coverage_Record": f"{item['source_key']}#L{item['citation_line_start']}-L{item['citation_line_end']}",
            }
        )
    return item_rows


def build_tracker_rows(spec: dict[str, Any], rows: list[dict[str, Any]], plan_md: Path, matrix_csv: Path) -> list[dict[str, Any]]:
    tracker_rows = []
    for item in rows:
        evidence_path = f"Plan\\Instructions\\QA\\Evidence\\Physics_Deformation\\Wave{spec['wave']}\\{item['implementation_target']}.json"
        tracker_rows.append(
            {
                "Tracker_ID": item["tracker_id"],
                "Wave": spec["wave"],
                "Phase": f"Wave{spec['wave']} {spec['title']}",
                "Workstream": item["category"],
                "Priority": item["priority"],
                "Risk_Level": item["risk"],
                "Owner_Role": "autonomous_codex_physics_deformation_builder",
                "Environment": "deferred_local_first_g7e_or_target_runtime_only_after_activation",
                "Status": STATUS,
                "Task_Name": item["title"],
                "Detailed_Action": item["autonomous_behavior"],
                "Completion_Criteria": item["acceptance_criteria"],
                "Acceptance_Evidence": evidence_path,
                "Dependency_Prerequisite": spec["activation_gate"],
                "Validation_Method": join_list(item["qa_gates"]),
                "Output_Artifact": evidence_path,
                "Source_Path": item["source_file_relative"],
                "Related_Source_Paths": rel(matrix_csv),
                "Package_Top_Level_Directory": "Plan",
                "Autonomous_Execution_Mode": "deferred_source_cited_local_first_strict_qa",
                "Human_Input_Allowed": "FALSE",
                "Human_Work_Allowed": "FALSE",
                "Codex_Desktop_Action": "Do not start until activation gate passes. When active, implement/prove/block with exact evidence and avoid docs-only loops.",
                "QA_Strictness": "strict_physics_visual_video_audio_when_applicable",
                "Visual_Review_Required": "TRUE" if item["visual_review_required"] else "FALSE",
                "Visual_Review_Method": "whole_artifact_plus_map_overlay_review; localized target review is insufficient",
                "Test_Required": "TRUE",
                "Runtime_Proof_Required": "TRUE",
                "EC2_Allowed": "FALSE",
                "Preview_Required": "TRUE",
                "Final_Render_Gate": "Blocked until strict evidence proves map/package/physics route and whole-artifact QA.",
                "Evidence_Path": evidence_path,
                "Citation_File": plan_md.name,
                "Citation_Full_Path": str(plan_md),
                "Citation_Section": item["citation_section"],
                "Citation_Line_Start": item["citation_line_start"],
                "Citation_Line_End": item["citation_line_end"],
                "Citation_Excerpt": f"Wave{spec['wave']} defines {item['implementation_target']} as a deferred autonomous physics/deformation expansion requirement.",
                "Source_Package": f"Wave{spec['wave']} {spec['title']}",
                "Source_Type": "Plan Source",
                "Source_Item_ID": item["item_id"],
                "Blocker_Policy": "Write exact blocker and continue nearer active project work if prerequisite backend/assets are unavailable.",
                "Rerun_Policy": "Rerun only when prototype, production base, backend, tool adapter, map package, ComfyUI route, generated media, or QA artifact changed.",
                "Status_Decision": "deferred_required_not_complete_until_activation_and_evidence_pass",
                "Notes": item["notes"],
                "Source_Key": item["source_key"],
                "Source_File_Relative": item["source_file_relative"],
                "Coverage_Level": "deferred_direct_physics_deformation_expansion_tracker_requirement",
                "Coverage_Audit_Status": "source_cited_deferred_required_not_complete",
                "Ultra_Source_Coverage_Record": f"{item['source_key']}#L{item['citation_line_start']}-L{item['citation_line_end']}",
            }
        )
    return tracker_rows


def build_scope_md(spec: dict[str, Any], plan_md: Path, matrix_csv: Path, items_csv: Path, tracker_csv: Path) -> list[str]:
    wave = spec["wave"]
    return [
        f"# Wave{wave} {spec['title']} Scope",
        "",
        f"Status: {STATUS}.",
        "",
        f"Purpose: {spec['purpose']}",
        "",
        f"Activation gate: {spec['activation_gate']}",
        "",
        "This wave is part of the future autonomous body-physics/deformation expansion system. It must not become the next implementation target unless the active project direction explicitly activates it.",
        "",
        "Authoritative files:",
        "",
        f"1. `{plan_md}`",
        f"2. `{matrix_csv}`",
        f"3. `{items_csv}`",
        f"4. `{tracker_csv}`",
        "",
        "Strict execution rules:",
        "",
        "- Do not mark rows complete from planning coverage alone.",
        "- Do not start backend/tool installation, G7e, or EC2 work just because this wave exists.",
        "- DAZ is neutral prototype source only; no DAZ runtime morphing, posing, dForce, simulation, production rigging, or production deformation.",
        "- Prefer local validation, schemas, adapter stubs, and future-proof planning until activation.",
        "- When activated, every row needs contract, artifact or adapter route, validation evidence, preview/overlay evidence, generated-output evidence when applicable, and strict whole-artifact QA.",
        "- LLM/VLM reviews cannot override failed deterministic geometry, topology, collision, support contact, map, video, audio, or cost-control gates.",
        "- For video, review the full duration plus frame grids.",
        "- For audio, review full-duration playback, event timing, foley/contact alignment, clipping/noise, mix, and AV sync.",
        "- If blocked, write a precise blocker and return to the nearest active source-cited project task.",
    ]


def update_manifest(path: Path, waves: list[int], row_count: int, report_paths: list[Path]) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    included = payload.get("included_waves", [])
    added_count = 0
    for wave in waves:
        if wave not in included:
            included.append(wave)
            added_count += 1
    payload["included_waves"] = sorted(included)
    if added_count and isinstance(payload.get("row_count"), int):
        payload["row_count"] += row_count
    if "deferred_physics_deformation_base_row_count" not in payload:
        payload["deferred_physics_deformation_base_row_count"] = payload.get("deferred_physics_deformation_system_row_count", 0)
    base_count = payload["deferred_physics_deformation_base_row_count"]
    payload["deferred_physics_deformation_expansion_waves"] = waves
    payload["deferred_physics_deformation_expansion_row_count"] = row_count
    payload["deferred_physics_deformation_expansion_reports"] = [rel(path) for path in report_paths]
    payload["deferred_physics_deformation_system_waves"] = sorted(set(payload.get("deferred_physics_deformation_system_waves", [])) | set(waves))
    payload["deferred_physics_deformation_system_row_count"] = base_count + row_count
    payload["deferred_physics_deformation_system_rule"] = (
        "Waves 71-86 are deferred future autonomous body-physics/deformation planning rows. "
        "They are not next-action implementation work until activation gates pass; every row remains "
        "Deferred_Required_Not_Complete until strict implementation evidence passes."
    )
    write_json(path, payload)


def update_readme(path: Path, label: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8-sig")
    if "Wave 86 - Expanded physics deformation final certification gates" in text:
        return
    text = text.replace(
        "plus Deferred Waves 71-76 Physics Coverage",
        "plus Deferred Waves 71-86 Physics Coverage",
    )
    text = text.replace(
        "Waves 71-76 are deferred source-cited",
        "Waves 71-86 are deferred source-cited",
    )
    insert_after = "- Wave 76 - Deferred physics, deformation, video, audio, and visual QA certification"
    additions = [
        "- Wave 77 - Deferred autonomous physics AI supervisor and multimodal review agent",
        "- Wave 78 - Deferred ultimate toolchain adapter registry",
        "- Wave 79 - Deferred body composition tissue material inference solver",
        "- Wave 80 - Deferred muscle activation, grip force, and contact strength system",
        "- Wave 81 - Deferred support surface physics, contact, compression, and deformation",
        "- Wave 82 - Deferred DAZ neutral prototype to production mesh detail transfer",
        "- Wave 83 - Deferred sculpt, material, and surface detail map pipeline",
        "- Wave 84 - Deferred animation, mocap, and temporal physics pipeline",
        "- Wave 85 - Deferred end-to-end autonomous physics work order orchestration",
        "- Wave 86 - Expanded physics deformation final certification gates",
    ]
    text = text.replace(insert_after, insert_after + "\n" + "\n".join(additions))
    block_marker = "wave76_physics_deformation_qa_certification_"
    if block_marker in text:
        block = "\n".join(
            [
                "wave77_autonomous_physics_ai_supervisor_multimodal_review_agent_" + label + ".csv",
                "wave78_ultimate_toolchain_adapter_registry_" + label + ".csv",
                "wave79_body_composition_tissue_material_inference_solver_" + label + ".csv",
                "wave80_muscle_activation_grip_force_contact_strength_system_" + label + ".csv",
                "wave81_support_surface_physics_contact_compression_deformation_" + label + ".csv",
                "wave82_daz_neutral_prototype_to_production_mesh_detail_transfer_" + label + ".csv",
                "wave83_sculpt_material_surface_detail_map_pipeline_" + label + ".csv",
                "wave84_animation_mocap_temporal_physics_pipeline_" + label + ".csv",
                "wave85_end_to_end_autonomous_physics_work_order_orchestration_" + label + ".csv",
                "wave86_expanded_physics_deformation_final_certification_gates_" + label + ".csv",
            ]
        )
        text = text.replace(
            "wave76_physics_deformation_qa_certification_" + label + ".csv",
            "wave76_physics_deformation_qa_certification_" + label + ".csv\n" + block,
        )
    text = text.replace(
        "For Waves 71-76,",
        "For Waves 71-86,",
    )
    text = text.replace(
        "DAZ prototype -> universal production base -> physics maps -> simulation adapters -> ComfyUI conditioning -> strict QA system",
        "DAZ neutral prototype -> universal production base -> tissue inference -> tool adapters -> AI supervisor -> support surfaces -> muscle/grip/force -> physics maps -> simulation adapters -> ComfyUI conditioning -> strict QA system",
    )
    write_text(path, text.splitlines())


def write_master_blueprint(summary: dict[str, Any]) -> None:
    lines = [
        "# Waves71-86 Master Autonomous Physics And Deformation Blueprint",
        "",
        f"Status: {STATUS}.",
        "",
        "This blueprint extends Waves71-76 with Waves77-86 so the future autonomous Soft-Body Physics And Deformation Map System has a complete machine-actionable map for every discussed tool, body/tissue inference layer, support-surface layer, muscle/grip/force layer, self-hosted AI supervisor, and strict certification gate.",
        "",
        "Deferred priority rule: do not activate this system until a source-cited project decision says the current ComfyUI foundation, Wave70 Mask Factory, runtime lanes, cost controls, and QA gates are stable enough. These files are planning and ledger coverage, not completion evidence.",
        "",
        "DAZ boundary: DAZ is only the neutral A-pose or T-pose prototype source. After registration, every conversion, fit, rig, simulation, map bake, material bake, animation, grip, support-surface, ComfyUI, QA, correction, tracker update, and blocker must be autonomous outside DAZ.",
        "",
        "End-to-end chain:",
        "",
        "1. Register DAZ neutral prototype.",
        "2. Load Blender-owned universal production base.",
        "3. Fit production mesh without changing topology or UVs.",
        "4. Transfer high-poly/reference detail into production maps.",
        "5. Infer body composition and tissue material parameters.",
        "6. Generate rig, collision, gravity, support-surface, muscle, grip, and force maps.",
        "7. Select tool adapters and run bounded simulations/material bakes.",
        "8. Package ComfyUI conditioning assets.",
        "9. Generate proof media.",
        "10. Run deterministic validators, VLM review, full visual/video/audio QA, and source-cited tracker closure.",
        "",
        "Generated expansion waves:",
        "",
    ]
    for wave, data in sorted(summary["waves"].items(), key=lambda kv: int(kv[0])):
        lines.append(f"- Wave {wave}: {data['title']} ({data['row_count']} rows)")
    lines.extend(
        [
            "",
            "Hard completion boundary:",
            "",
            "- Planning rows do not prove implementation.",
            "- LLM/VLM review cannot override failed deterministic validation.",
            "- Localized target-region review is insufficient.",
            "- G7e/EC2 runtime is allowed only after activation, cost-control, runtime-window, artifact pullback, and stop-verification gates.",
            "- If any required tool, license, model, asset, backend, or confidence threshold is missing, write an exact blocker and continue nearer active project work.",
        ]
    )
    write_text(PHYSICS_ROOT / "WAVES71_86_MASTER_AUTONOMOUS_PHYSICS_DEFORMATION_BLUEPRINT.md", lines)


def main() -> None:
    specs = all_specs()
    generated_at = datetime.now(timezone.utc).isoformat()
    total_rows = 0
    report_paths: list[Path] = []
    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at_utc": generated_at,
        "status": STATUS,
        "waves": {},
        "external_references": EXTERNAL_REFERENCES,
        "deferred_rule": "Do not implement Waves 77-86 until active project priorities and activation gates allow it.",
    }

    for spec in specs:
        wave = spec["wave"]
        slug = spec["slug"]
        wave_dir_items = ITEMS_ROOT / "Waves" / f"Wave{wave}"
        wave_dir_tracker = TRACKER_ROOT / "Waves" / f"Wave{wave}"
        scope_md = PLAN / "Instructions" / "Waves" / f"Wave{wave}" / f"WAVE{wave}_SCOPE.md"
        plan_md = PHYSICS_ROOT / f"WAVE{wave}_{slug.upper()}.md"
        plan_json = PHYSICS_ROOT / f"WAVE{wave}_{slug.upper()}.json"
        matrix_csv = PHYSICS_ROOT / f"WAVE{wave}_{slug.upper()}_MATRIX.csv"
        items_csv = ITEMS_ROOT / f"wave{wave}_{slug}_itemized_list.csv"
        items_wave_csv = wave_dir_items / f"WAVE{wave}_{slug.upper()}_ITEM_ROWS.csv"
        items_req_json = wave_dir_items / f"WAVE{wave}_{slug.upper()}_REQUIREMENTS.json"
        items_report_json = ITEMS_ROOT / "Reports" / f"wave{wave}_{slug}_coverage_report.json"
        tracker_csv = TRACKER_ROOT / f"wave{wave}_{slug}_tracker.csv"
        tracker_wave_csv = wave_dir_tracker / f"WAVE{wave}_{slug.upper()}_TRACKER_ROWS.csv"
        tracker_req_json = wave_dir_tracker / f"WAVE{wave}_{slug.upper()}_REQUIREMENTS.json"
        tracker_report_json = TRACKER_ROOT / "Reports" / f"wave{wave}_{slug}_coverage_report.json"

        md_lines, line_map = build_plan_markdown(spec)
        write_text(plan_md, md_lines)
        enriched = enrich_rows(spec, line_map, plan_md)
        matrix_rows = build_plan_matrix_rows(spec, enriched)
        item_rows = build_item_rows(spec, enriched, plan_md)
        tracker_rows = build_tracker_rows(spec, enriched, plan_md, matrix_csv)

        write_csv(matrix_csv, PLAN_MATRIX_HEADER, matrix_rows)
        write_csv(items_csv, ITEMS_HEADER, item_rows)
        write_csv(items_wave_csv, ITEMS_HEADER, item_rows)
        write_csv(tracker_csv, TRACKER_HEADER, tracker_rows)
        write_csv(tracker_wave_csv, TRACKER_HEADER, tracker_rows)
        write_text(scope_md, build_scope_md(spec, plan_md, matrix_csv, items_csv, tracker_csv))

        requirements_payload = {
            "schema_version": "1.0",
            "wave": wave,
            "title": spec["title"],
            "slug": slug,
            "generated_at_utc": generated_at,
            "status": STATUS,
            "activation_gate": spec["activation_gate"],
            "row_count": len(enriched),
            "source_files": [rel(plan_md), rel(matrix_csv), rel(scope_md)],
            "items_csv": rel(items_csv),
            "tracker_csv": rel(tracker_csv),
            "common_qa_gates": COMMON_QA_GATES,
            "physics_qa_gates": PHYSICS_QA_GATES,
            "comfyui_qa_gates": COMFYUI_QA_GATES,
            "audio_qa_gates": AUDIO_QA_GATES,
            "expansion_qa_gates": EXPANSION_QA_GATES,
            "external_references": EXTERNAL_REFERENCES,
        }
        write_json(items_req_json, requirements_payload)
        write_json(tracker_req_json, requirements_payload)

        report_payload = {
            "schema_version": "1.0",
            "wave": wave,
            "title": spec["title"],
            "slug": slug,
            "generated_at_utc": generated_at,
            "result": "pass_generated_deferred_required_not_complete_rows",
            "row_count": len(enriched),
            "items_rows": len(item_rows),
            "tracker_rows": len(tracker_rows),
            "matrix_rows": len(matrix_rows),
            "categories": counts_by(enriched, "category"),
            "status": STATUS,
            "activation_gate": spec["activation_gate"],
            "required_files": {
                "plan_md": rel(plan_md),
                "plan_json": rel(plan_json),
                "matrix_csv": rel(matrix_csv),
                "scope_md": rel(scope_md),
                "items_csv": rel(items_csv),
                "items_wave_csv": rel(items_wave_csv),
                "tracker_csv": rel(tracker_csv),
                "tracker_wave_csv": rel(tracker_wave_csv),
            },
            "known_boundary": "Generated planning/ledger rows do not prove implementation completion.",
        }
        write_json(items_report_json, report_payload)
        write_json(tracker_report_json, report_payload)
        write_json(
            plan_json,
            {
                "schema_version": "1.0",
                "wave": wave,
                "title": spec["title"],
                "slug": slug,
                "generated_at_utc": generated_at,
                "purpose": spec["purpose"],
                "activation_gate": spec["activation_gate"],
                "status": STATUS,
                "row_count": len(enriched),
                "categories": counts_by(enriched, "category"),
                "requirements": enriched,
                "external_references": EXTERNAL_REFERENCES,
            },
        )

        total_rows += len(enriched)
        report_paths.extend([items_report_json, tracker_report_json])
        summary["waves"][str(wave)] = {
            "title": spec["title"],
            "slug": slug,
            "row_count": len(enriched),
            "plan_md": rel(plan_md),
            "matrix_csv": rel(matrix_csv),
            "scope_md": rel(scope_md),
            "items_csv": rel(items_csv),
            "tracker_csv": rel(tracker_csv),
            "status": STATUS,
        }

    summary["total_row_count"] = total_rows
    summary["wave_count"] = len(specs)
    write_json(PHYSICS_ROOT / "WAVES77_86_PHYSICS_DEFORMATION_EXPANSION_SUMMARY.json", summary)
    write_text(
        PHYSICS_ROOT / "WAVES77_86_DEFERRED_IMPLEMENTATION_PRIORITY.md",
        [
            "# Waves77-86 Deferred Implementation Priority",
            "",
            "Waves 77-86 expand the future autonomous body-physics/deformation system with AI supervision, tool adapters, tissue inference, muscle/grip force, support surfaces, detail/material maps, temporal animation, work-order orchestration, and final certification.",
            "",
            "They are not next-action implementation work. The active project should continue the current ComfyUI foundation, runtime lanes, cost controls, workflow generation, Mask Factory proofing, and current QA milestones before activating these waves.",
            "",
            "Activation requires an explicit source-cited decision that the current ComfyUI foundation and Waves 71-76 base physics system are stable enough to absorb this expansion without loop/drift or G7e/EC2 cost risk.",
            "",
            "Every row remains Deferred_Required_Not_Complete until implementation artifacts and strict evidence pass.",
        ],
    )
    write_master_blueprint(summary)
    update_manifest(ITEMS_ROOT / "Manifests" / "items_package_manifest.json", list(range(77, 87)), total_rows, report_paths)
    update_manifest(TRACKER_ROOT / "Manifests" / "tracker_package_manifest.json", list(range(77, 87)), total_rows, report_paths)
    update_readme(ITEMS_ROOT / "README.md", "itemized_list")
    update_readme(TRACKER_ROOT / "README.md", "tracker")

    print(json.dumps({"generated_waves": list(range(77, 87)), "total_rows": total_rows}, sort_keys=True))


if __name__ == "__main__":
    main()
