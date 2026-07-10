from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
PHYSICS_ROOT = PLAN / "07_IMPLEMENTATION" / "physics_deformation_system"
ITEMS_ROOT = PLAN / "Items"
TRACKER_ROOT = PLAN / "Tracker"


ITEMS_HEADER = [
    "Item_ID",
    "Item_Wave",
    "Item_Type",
    "Item_Title",
    "Item_Category",
    "Item_Domain",
    "Owner_Domain",
    "Autonomous_Required",
    "Human_Input_Allowed",
    "Human_Work_Allowed",
    "Codex_Action",
    "Implementation_Target",
    "Deliverable_Type",
    "Acceptance_Criteria",
    "QA_Gates_Required",
    "Visual_Review_Required",
    "Visual_Review_Method",
    "Test_Required",
    "Evidence_Required",
    "Runtime_Proof_Required",
    "EC2_Allowed",
    "Blocker_Policy",
    "Source_Plan_Root",
    "Citation_File",
    "Citation_Full_Path",
    "Citation_Section",
    "Citation_Line_Start",
    "Citation_Line_End",
    "Citation_Excerpt",
    "Source_Package",
    "Source_Type",
    "Source_File_Size",
    "Priority",
    "Risk_Level",
    "Status",
    "Created_From",
    "Notes",
    "Source_Key",
    "Source_File_Relative",
    "Coverage_Level",
    "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]


TRACKER_HEADER = [
    "Tracker_ID",
    "Wave",
    "Phase",
    "Workstream",
    "Priority",
    "Risk_Level",
    "Owner_Role",
    "Environment",
    "Status",
    "Task_Name",
    "Detailed_Action",
    "Completion_Criteria",
    "Acceptance_Evidence",
    "Dependency_Prerequisite",
    "Validation_Method",
    "Output_Artifact",
    "Source_Path",
    "Related_Source_Paths",
    "Package_Top_Level_Directory",
    "Autonomous_Execution_Mode",
    "Human_Input_Allowed",
    "Human_Work_Allowed",
    "Codex_Desktop_Action",
    "QA_Strictness",
    "Visual_Review_Required",
    "Visual_Review_Method",
    "Test_Required",
    "Runtime_Proof_Required",
    "EC2_Allowed",
    "Preview_Required",
    "Final_Render_Gate",
    "Evidence_Path",
    "Citation_File",
    "Citation_Full_Path",
    "Citation_Section",
    "Citation_Line_Start",
    "Citation_Line_End",
    "Citation_Excerpt",
    "Source_Package",
    "Source_Type",
    "Source_Item_ID",
    "Blocker_Policy",
    "Rerun_Policy",
    "Status_Decision",
    "Notes",
    "Source_Key",
    "Source_File_Relative",
    "Coverage_Level",
    "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]


PLAN_MATRIX_HEADER = [
    "requirement_id",
    "wave",
    "category",
    "title",
    "implementation_target",
    "autonomous_behavior",
    "acceptance_criteria",
    "required_evidence",
    "qa_gates",
    "visual_runtime_ready",
    "video_runtime_ready",
    "audio_runtime_ready",
    "comfyui_integration_required",
    "simulation_backend_required",
    "deferred_status",
    "activation_gate",
    "source_key",
    "source_file_relative",
    "citation_section",
    "citation_line_start",
    "citation_line_end",
]


COMMON_QA_GATES = [
    "schema_validation_pass",
    "source_citation_present",
    "artifact_manifest_with_hashes_present",
    "preview_or_overlay_generated",
    "strict_visual_review_pass",
    "whole_artifact_review_pass_when_media_exists",
    "no_human_work_dependency_after_registered_inputs",
    "autonomous_failure_blocker_written_if_blocked",
]

PHYSICS_QA_GATES = [
    "body_region_mapping_pass",
    "protected_anchor_preservation_pass",
    "gravity_direction_plausibility_pass",
    "collision_contact_plausibility_pass",
    "no_mesh_or_visual_penetration_pass",
    "no_floating_contact_pass",
    "body_shape_continuity_pass",
    "temporal_stability_pass_for_video",
]

COMFYUI_QA_GATES = [
    "control_map_dimensions_match_generation",
    "map_value_range_normalized",
    "comfyui_route_manifest_pass",
    "generated_output_proof_present",
    "target_runtime_proof_before_final_certification",
]

AUDIO_QA_GATES = [
    "full_duration_audio_review_pass",
    "audio_event_visual_contact_alignment_pass",
    "av_sync_drift_check_pass",
    "clipping_noise_mix_balance_pass",
]


EXTERNAL_REFERENCES = [
    {
        "name": "Blender command line and background automation",
        "url": "https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html",
        "usage": "Blender-first adapter can run scripted scene import, fitting, simulation prep, render-pass export, and validation from command line.",
    },
    {
        "name": "SideFX Houdini hython/hbatch batch workflow",
        "url": "https://www.sidefx.com/docs/houdini/render/batch.html",
        "usage": "Optional Houdini adapter can run procedural/SDF/Vellum-style simulation and render/export tasks through command-line tools.",
    },
    {
        "name": "Unreal Python command-line scripting",
        "url": "https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python?lang=en-US",
        "usage": "Optional Unreal adapter can automate editor/script tasks for physics assets, animation, rendered passes, and real-time simulation evidence.",
    },
    {
        "name": "DAZ Studio scripting",
        "url": "https://docs.daz3d.com/public/software/dazstudio/4/referenceguide/scripting/start",
        "usage": "DAZ is treated as prototype sculpt/source intake and scriptable export surface, not the production physics authority.",
    },
    {
        "name": "DAZ silent FBX export sample",
        "url": "https://docs.daz3d.com/public/software/dazstudio/4/referenceguide/scripting/api_reference/samples/file_io/export_fbx_silent/start",
        "usage": "DAZ prototype packages can be exported without interactive export dialogs when DAZ is available.",
    },
    {
        "name": "DAZ dForce simulation settings",
        "url": "https://docs.daz3d.com/public/software/dazstudio/4/userguide/animating/videos/simulation_settings/start",
        "usage": "DAZ dForce is optional prototype/cloth-source context; final production physics maps should be validated in the adapter layer.",
    },
    {
        "name": "Marvelous Designer Python API",
        "url": "https://developer.marvelousdesigner.com/",
        "usage": "Optional clothing adapter can automate garment import, simulation, and export where licensed/available.",
    },
    {
        "name": "Marvelous Designer export API list",
        "url": "https://developer.marvelousdesigner.com/list.html",
        "usage": "Optional clothing adapter can export OBJ/Alembic and related artifacts for downstream fitting, collision, and map baking.",
    },
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("/", "\\")


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
    )


def join_list(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


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
    comfyui: bool = False,
    backend: bool = True,
    notes: str = "",
) -> dict[str, Any]:
    qa_gates = list(COMMON_QA_GATES)
    qa_gates.extend(qa or [])
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
        "visual_runtime_ready": visual,
        "video_runtime_ready": video,
        "audio_runtime_ready": audio,
        "comfyui_integration_required": comfyui,
        "simulation_backend_required": backend,
        "notes": notes,
    }


def map_req(category: str, map_id: str, controls: str, used_for: str, comfyui_equivalent: str, body_regions: str) -> dict[str, Any]:
    return req(
        category,
        f"Define and prove {map_id}",
        map_id,
        f"Autonomously create or import {map_id}, normalize it into the standard physics-map schema, declare ComfyUI equivalents, and block completion until evidence proves it can drive or document {used_for}.",
        f"{map_id} has a schema record, generation/import route, preview overlay, value range validation, body-region mapping, ComfyUI translation, and QA evidence for {used_for}.",
        [
            "physics_map_schema_record",
            "source_or_generation_manifest",
            "preview_overlay_or_render_pass",
            "value_range_validation_json",
            "body_region_mapping_json",
            "comfyui_translation_record",
            "qa_report_json",
        ],
        PHYSICS_QA_GATES + COMFYUI_QA_GATES,
        comfyui=True,
        notes=f"Controls: {controls}. Used for: {used_for}. ComfyUI equivalent: {comfyui_equivalent}. Body regions: {body_regions}.",
    )


def build_wave71() -> dict[str, Any]:
    map_types = [
        ("vertex_weight_maps", "0-1 per-vertex influence", "pinning, stiffness, softness, jiggle amount, deformation zones", "grayscale mask or Advanced-ControlNet strength mask", "all soft-body regions"),
        ("skin_weight_maps", "bone-to-mesh influence", "normal rig deformation and joint motion", "pose map/keypoints plus rig metadata", "full body, face, hands, feet"),
        ("pin_anchor_maps", "areas locked or nearly locked to skeleton", "stable ribs, pelvis, skull, hands, joints", "protected negative mask", "skeleton anchors and identity anchors"),
        ("damping_maps", "how fast motion settles", "heavy vs bouncy movement", "temporal decay metadata; no direct ComfyUI equivalent", "soft tissue regions and cloth"),
        ("bend_stretch_shear_maps", "cloth or soft mesh bending/stretching/shearing", "clothing, skin folds, soft tissue surfaces", "lineart/depth/normal plus cloth mask", "cloth, abdomen, thighs, arms"),
        ("collision_backstop_maps", "where mesh collides or avoids penetration", "body contact, cloth-body collision, compression limits", "contact mask, occlusion mask, depth map", "hands, clothing, support surfaces, multi-character contact"),
        ("morph_target_blendshape_maps", "stored vertex-position changes", "body morphing, expressions, corrective poses", "reference render or shape-target metadata", "body, face, hands"),
        ("corrective_shape_pose_space_maps", "pose-specific deformation fixes", "elbows, knees, hips, shoulders, belly compression, thigh contact", "corrected depth/normal/reference frame", "joints and contact regions"),
        ("delta_vertex_maps", "offset from base mesh to morphed mesh", "shape fitting and production rebuild evidence", "not native; rendered/depth/normal delta package", "production base mesh"),
        ("displacement_maps", "surface height/detail displacement", "wrinkles, cellulite, folds, compression dents", "detail inpaint map or displacement-looking texture", "skin, fabric, support contact"),
        ("vector_displacement_maps", "3D displacement directions", "complex folds and sculpted deformations", "not native; rendered visual reference", "skin folds, cloth, pressure areas"),
        ("normal_bump_detail_maps", "surface shading detail", "pores, fine wrinkles, cellulite texture", "normal map, bump/detail image", "skin and fabric"),
        ("tension_compression_maps", "stretch/squeeze driver values", "dynamic wrinkles, skin pull, fabric stress, contact lines", "wrinkle/contact mask", "skin, cloth, hands, support contact"),
        ("sdf_volume_collision_fields", "signed distance to surface or volume", "advanced collision and penetration prevention", "depth/geometry proxy evidence; not native", "whole body and support objects"),
        ("elasticity_restitution_maps", "how strongly a region rebounds", "bounce, rebound, settling", "temporal response metadata plus reference sequence", "soft tissue and cloth"),
        ("friction_stiction_maps", "slide vs stick at contact points", "hand contact, cloth drag, body-on-surface realism", "contact mask plus audio/visual event metadata", "hands, thighs, support surfaces, clothing"),
        ("contact_normal_maps", "direction of pressure/contact", "physically plausible compression direction", "normal/depth/contact map combination", "body-object and body-body contact"),
        ("penetration_depth_maps", "how much surfaces overlap or nearly overlap", "clipping prevention and collision QA", "depth delta/occlusion evidence", "all collision pairs"),
        ("rest_shape_maps", "shape body returns to after deformation", "body-shape continuity after motion", "before/after reference and delta maps", "soft tissue and face"),
        ("temporal_decay_settling_maps", "how motion damps over time", "jiggle, ripple, rebound decay", "frame sequence metrics", "video soft-body regions"),
        ("global_gravity_vector_maps", "scene gravity vector and scale", "consistent sag, cloth drape, falling/settling direction", "scene metadata plus overlay arrows", "entire scene"),
        ("contact_load_transfer_maps", "how weight transfers through contact", "body-on-bed/chair/floor and multi-character pressure", "contact pressure mask plus depth/normal", "support surfaces and shared contact"),
        ("inertia_momentum_maps", "lag and follow-through behavior", "secondary body motion and heavy movement", "motion vector/optical flow metadata", "video body motion"),
        ("gravity_collision_response_maps", "combined gravity and collision response", "sag plus compression plus rebound", "multi-map physics package", "soft tissue, cloth, support surfaces"),
    ]
    rows = [
        map_req("physics_map_taxonomy", map_id, controls, used_for, comfyui_equivalent, body_regions)
        for map_id, controls, used_for, comfyui_equivalent, body_regions in map_types
    ]
    body_regions = [
        ("abdomen_stomach_region", "belly softness, compression, breathing, gravity sag, hands/clothing contact"),
        ("thigh_hip_waist_region", "thigh compression, hip/waist shape, walking/sitting contact and cloth friction"),
        ("upper_arm_calf_loose_skin_region", "secondary motion on arms/calves and loose skin without joint drift"),
        ("face_cheek_neck_region", "face morphing, cheek softness, neck fold deformation, identity preservation"),
        ("hands_fingers_feet_toes_anchor_region", "protected anchors for contact, no broken hands/feet, no toe/finger drift"),
        ("clothing_fabric_region", "cloth bend/stretch/shear, drape, stiction, compression, and fabric wrinkles"),
        ("hair_region", "hair motion/contact proxy, collision exclusion, face/neck protection"),
        ("support_surface_region", "bed, couch, chair, floor, table, pillow, blanket contact and load transfer"),
        ("multi_character_contact_region", "shared contact, separation, occlusion, collision ownership, and identity separation"),
        ("audio_event_contact_region", "footstep, hand contact, clothing rustle, support compression, impact timing"),
    ]
    for region_id, purpose in body_regions:
        rows.append(
            req(
                "body_region_physics_presets",
                f"Define physics preset coverage for {region_id}",
                region_id,
                f"Autonomously select and validate required maps for {region_id} whenever a scene, prompt, reference, or DAZ prototype includes that region.",
                f"{region_id} declares required map types, protected anchors, gravity/collision behavior, ComfyUI outputs, and strict QA gates.",
                [
                    "region_preset_json",
                    "required_map_list",
                    "protected_anchor_list",
                    "gravity_collision_rules",
                    "qa_gate_matrix",
                    "comfyui_output_mapping",
                ],
                PHYSICS_QA_GATES + COMFYUI_QA_GATES + AUDIO_QA_GATES,
                comfyui=True,
                audio="audio" in region_id,
                notes=purpose,
            )
        )
    return {
        "wave": 71,
        "slug": "soft_body_physics_deformation_map_system",
        "title": "Soft-Body Physics And Deformation Map System",
        "purpose": "Define every physics, deformation, gravity, collision, morph, surface-detail, and ComfyUI-equivalent map required for autonomous hyperrealistic image, video, and audio generation.",
        "activation_gate": "Deferred. Activate only after current ComfyUI foundation, runtime lanes, cost controls, and Wave70 Mask Factory coverage are stable enough that physics-map work will not derail nearer project milestones.",
        "rows": rows,
    }


def build_wave72() -> dict[str, Any]:
    targets = [
        ("daz_prototype_asset_contract", "DAZ prototype package schema for source sculpt, reference renders, optional hair/clothes, textures, body-region metadata, and export paths"),
        ("universal_a_t_pose_requirement", "A/T-pose normalization and rejection of prototypes that cannot be aligned without severe distortion"),
        ("daz_silent_export_adapter", "scriptable DAZ export route for FBX/OBJ/textures/reference renders when DAZ is available"),
        ("prototype_registry", "character_prototype_id registry with version, source files, hashes, body type, and allowed use"),
        ("prototype_measurement_extractor", "height, limb lengths, torso volume, shoulder/hip/waist/chest/thigh/arm proportions"),
        ("prototype_reference_render_set", "orthographic front/side/back/three-quarter reference renders plus silhouette/depth captures"),
        ("prototype_landmark_detector", "face, joints, hands, feet, pelvis, chest, abdomen, body contour, garment and hair landmarks"),
        ("universal_production_base_mesh_spec", "high-end Blender-owned base figure with stable topology, UVs, landmarks, vertex groups, Wave70 masks, and Wave71 physics IDs"),
        ("production_base_version_registry", "immutable base mesh versions and compatibility with rig, maps, and ComfyUI exporters"),
        ("topology_uv_invariant_gate", "fit operation cannot change topology, UV layout, vertex order, or required named groups"),
        ("wave70_region_label_transfer", "Wave70 mask region labels transferred to fitted production body"),
        ("wave71_physics_anchor_transfer", "Wave71 physics anchors and map IDs transferred to fitted production body"),
        ("shape_transfer_wrap_solver", "Blender wrap/lattice/shrinkwrap/landmark fit to match DAZ prototype silhouette and proportions"),
        ("fit_error_metrics", "landmark, silhouette, volume, body-proportion, and camera/reference-view fit thresholds"),
        ("hair_clothing_prototype_extraction", "optional DAZ hair/clothing prototype imported as reference, then rebuilt or proxied for production"),
        ("material_texture_reference_capture", "texture/material/color/skinmark reference capture for later ComfyUI and rendering consistency"),
        ("body_region_metadata_contract", "body, garment, region-label, and fit-context metadata preserved as ordinary technical validation data"),
        ("prototype_to_production_qa_report", "single audit artifact proving the DAZ prototype was converted into a production-ready fitting target"),
        ("manual_asset_boundary", "DAZ sculpt can be a supplied input, but no human implementation work is allowed after registration"),
        ("not_next_priority_gate", "explicit deferred rule preventing the main session from implementing this before nearer ComfyUI project milestones"),
    ]
    rows = [
        req(
            "daz_prototype_intake_and_universal_base",
            f"Build {target_id}",
            target_id,
            f"Autonomously validate, register, or generate evidence for {description}.",
            f"{target_id} is complete only with schema, scripts or adapter stubs, sample manifest, validation evidence, fit/visual QA where applicable, and blocker behavior if unavailable.",
            [
                "schema_or_contract_json",
                "adapter_or_process_spec",
                "example_manifest",
                "validation_report_json",
                "visual_reference_or_overlay",
                "qa_report_json",
            ],
            PHYSICS_QA_GATES,
            notes=description,
        )
        for target_id, description in targets
    ]
    return {
        "wave": 72,
        "slug": "daz_prototype_universal_production_base_fitting",
        "title": "DAZ Prototype Intake And Universal Production Base Fitting",
        "purpose": "Treat DAZ as a prototype sculpt/reference source, then fit a stable Blender-owned production base figure to that prototype for autonomous rigging, physics, map baking, and ComfyUI conditioning.",
        "activation_gate": "Deferred. Do not implement until the current ComfyUI generation system, Wave70 mask coverage, and Wave71 map taxonomy are stable enough to consume production-body physics work.",
        "rows": rows,
    }


def build_wave73() -> dict[str, Any]:
    targets = [
        ("production_armature_builder", "create a production-grade skeleton/armature independent of DAZ rig quirks"),
        ("skin_weight_generation", "generate and validate clean skin weights for body, face, hands, and feet"),
        ("ik_fk_control_rig", "IK/FK controls, pole targets, constraints, and animation handles for autonomous pose/application"),
        ("face_rig_expression_system", "face controls, expression regions, jaw/eyes/mouth anchors, and identity-preserving face morphing"),
        ("corrective_shapes_shoulders", "pose-space shoulder/armpit corrective deformation"),
        ("corrective_shapes_elbows_wrists", "elbow and wrist bend/skin fold corrective deformation"),
        ("corrective_shapes_hips_thighs", "hip/thigh/belly contact corrective deformation"),
        ("corrective_shapes_knees_ankles", "knee/ankle/foot bend and pressure corrective deformation"),
        ("collision_capsule_proxy_set", "capsule proxies for torso, arms, legs, fingers, and support-safe collision"),
        ("collision_sphere_proxy_set", "sphere proxies for joints and soft zones"),
        ("collision_convex_proxy_set", "convex hull proxies for more accurate body/prop collision"),
        ("sdf_collision_proxy_set", "optional SDF/volume collision fields for advanced adapters"),
        ("center_of_mass_model", "body-wide and per-region center-of-mass model"),
        ("body_part_gravity_model", "per-body-part gravity vector, mass, sag, and support behavior"),
        ("abdomen_soft_body_preset", "abdomen/stomach compression, breath, sag, damping, contact and clothing behavior"),
        ("thigh_hip_soft_body_preset", "thigh/hip/waist collision, friction, compression, cloth, and support behavior"),
        ("upper_arm_calf_soft_body_preset", "upper-arm/calf loose-skin secondary motion and protected joint anchors"),
        ("face_cheek_neck_softness_preset", "face/cheek/neck deformation without identity drift"),
        ("hands_feet_protected_anchor_preset", "hands/fingers/feet/toes protected anchors and contact correctness"),
        ("clothing_collision_proxy_builder", "cloth/body collision proxies and fabric-region map anchors"),
        ("hair_collision_proxy_builder", "hair/head/neck/shoulder collision proxies and protected-face constraints"),
        ("support_surface_proxy_builder", "bed/chair/couch/floor/table/pillow/blanket collision and load-transfer proxies"),
        ("multi_character_collision_ownership", "character A/B collision ownership, separation, shared contact, occlusion, and identity protection"),
        ("gravity_contact_load_transfer_solver", "support-surface and body-body load transfer with gravity and compression maps"),
        ("physics_map_baker", "bake vertex, weight, stiffness, damping, pressure, collision, gravity, tension, compression, and decay maps"),
        ("simulation_cache_baker", "bake final simulation caches for video and repeatable map export"),
        ("render_pass_exporter", "export reference frames, depth, normal, segmentation, masks, contact, deformation, and motion passes"),
        ("production_rig_smoke_test", "automated rig deformation smoke test across body poses and soft-body regions"),
    ]
    rows = [
        req(
            "production_rig_collision_gravity_maps",
            f"Implement {target_id}",
            target_id,
            f"Autonomously build, validate, and evidence {description}.",
            f"{target_id} passes production-rig, physics-map, collision, gravity, visual overlay, and no-regression QA before any downstream ComfyUI conditioning can trust it.",
            [
                "production_body_manifest",
                "rig_or_proxy_artifact",
                "map_or_cache_artifact",
                "preview_overlay",
                "physics_validation_report",
                "visual_qa_report",
            ],
            PHYSICS_QA_GATES,
            risk="Critical" if "collision" in target_id or "gravity" in target_id or "soft_body" in target_id else "High",
            notes=description,
        )
        for target_id, description in targets
    ]
    return {
        "wave": 73,
        "slug": "production_rig_collision_gravity_soft_body_map_generation",
        "title": "Production Rig, Collision, Gravity, And Soft-Body Map Generation",
        "purpose": "Build the production figure from the fitted universal base, then generate rigging, corrective deformation, collision, gravity, mass, soft-body, support-surface, and render-pass outputs.",
        "activation_gate": "Deferred. Activate only after Wave72 can produce a fitted production base and the active ComfyUI foundation has capacity for simulation-map integration.",
        "rows": rows,
    }


def build_wave74() -> dict[str, Any]:
    targets = [
        ("simulation_request_schema", "machine-readable request for region, owner, motion, gravity, contact objects, softness, damping, frames, and ComfyUI map outputs"),
        ("backend_capability_matrix", "capability table for Blender, Houdini, Unreal, DAZ, Marvelous, and fallback ComfyUI-only approximation"),
        ("backend_availability_license_check", "detect installed backend, license availability, command path, version, and allowed execution mode without blocking current project work"),
        ("backend_selector_policy", "choose cheapest valid backend; Blender first; optional Houdini/Unreal/Marvelous/DAZ only when available and required"),
        ("blender_background_adapter", "Blender command-line/background adapter for import, fitting, map baking, render-pass export, and validation"),
        ("houdini_hython_hbatch_adapter", "optional Houdini adapter for procedural/SDF/Vellum-style simulations and advanced collision fields"),
        ("unreal_python_commandlet_adapter", "optional Unreal adapter for physics assets, animation, real-time simulation, and rendered pass export"),
        ("daz_prototype_export_adapter", "optional DAZ script adapter for prototype export; not production physics authority"),
        ("marvelous_clo_cloth_adapter", "optional Marvelous/CLO adapter for garment simulation/export where licensed"),
        ("comfyui_only_approximation_adapter", "fallback adapter using pose/depth/normal/SAM/optical-flow maps when true 3D simulation is unavailable"),
        ("adapter_timeout_watchdog", "bounded runtime, logs, termination, and no endless backend process loops"),
        ("adapter_security_policy", "no secrets printed, no untrusted scripts, quarantined external assets, deterministic output directories"),
        ("simulation_package_manifest_schema", "standard manifest for frames, maps, hashes, backend, versions, settings, and QA evidence"),
        ("render_pass_hash_manifest", "hash all frames, depth, normal, masks, contact maps, deformation maps, motion vectors, and audio-event maps"),
        ("backend_output_validator", "validate files exist, dimensions match, value ranges pass, frame counts align, and route metadata is complete"),
        ("adapter_fallback_blocker_policy", "if backend unavailable, write blocker and switch to local ComfyUI approximation or deferred row, not docs churn"),
        ("s3_cache_artifact_policy", "optional S3/cache path for large simulation packages without Git LFS"),
        ("cost_control_policy", "no EC2 for backend setup; local or CI validation first; bounded runtime for target proof"),
        ("deterministic_seed_and_versioning", "record seeds, backend versions, base mesh version, request hash, and output hashes"),
        ("adapter_smoke_matrix", "minimal smoke tests for each backend without forcing unavailable proprietary tools"),
    ]
    rows = [
        req(
            "autonomous_simulation_backend_adapters",
            f"Define adapter requirement {target_id}",
            target_id,
            f"Autonomously implement or block {description}; never require interactive/manual backend work during normal execution.",
            f"{target_id} has schema, command contract, availability behavior, bounded execution, output manifest, validation evidence, and fallback/blocker handling.",
            [
                "adapter_contract_json",
                "command_template_or_script",
                "availability_check_report",
                "sample_request",
                "sample_output_manifest",
                "validation_report",
                "blocker_or_fallback_evidence",
            ],
            PHYSICS_QA_GATES,
            priority="P1" if "blender" in target_id or "schema" in target_id or "selector" in target_id else "P2",
            notes=description,
        )
        for target_id, description in targets
    ]
    return {
        "wave": 74,
        "slug": "autonomous_simulation_backend_adapters",
        "title": "Autonomous Simulation Backend Adapters",
        "purpose": "Define the adapter layer that can call Blender first, then optional Houdini, Unreal, DAZ, Marvelous/CLO, or ComfyUI-only approximation routes without manual work or drift.",
        "activation_gate": "Deferred. Adapter implementation starts only after the schema and production-base requirements are stable and the current ComfyUI work is not blocked by this future layer.",
        "rows": rows,
    }


def build_wave75() -> dict[str, Any]:
    targets = [
        ("conditioning_package_manifest", "standard ComfyUI conditioning package manifest for simulation-derived outputs"),
        ("pose_map_ingestion", "OpenPose/DWPose/SDPose-compatible pose map ingestion from rig/sim/reference frames"),
        ("depth_map_ingestion", "Depth Anything/MoGe/Zoe/MiDaS-compatible depth map normalization and route proof"),
        ("normal_map_ingestion", "normal_bae/MoGe/DSINE normal map normalization including OpenGL/DirectX convention metadata"),
        ("segmentation_body_part_mask_ingestion", "SAM/segmentation/body-part mask ingestion aligned with Wave70 masks"),
        ("contact_mask_ingestion", "contact, pressure, collision, occlusion, and support-surface masks for regional passes"),
        ("deformation_map_ingestion", "soft-body, gravity, compression, jiggle, ripple, rebound, morph, and corrective deformation maps"),
        ("optical_flow_motion_vector_ingestion", "flow/motion-vector ingestion for temporal consistency and motion QA"),
        ("audio_event_map_ingestion", "footstep, hand contact, cloth rustle, support compression, mouth/breath event maps"),
        ("controlnet_route_builder", "ControlNet route plan for pose/depth/normal/lineart/canny/segmentation maps"),
        ("masked_inpaint_route_builder", "regional inpaint/detail routes for compression, wrinkles, skin texture, cloth, hands, feet, face"),
        ("video_to_video_conditioning_route", "frame sequence, temporal masks, optical flow, and reference frames routed into video workflows"),
        ("regional_prompt_conditioning", "region-specific prompts/negative prompts tied to body-part masks and protected anchors"),
        ("map_strength_schedule", "per-map strength/start/end/temporal schedule to avoid over-constrained or plastic outputs"),
        ("whole_artifact_preview_builder", "contact/physics overlays plus generated-output previews for strict review"),
        ("local_comfyui_validation_lane", "local ComfyUI lane validates package without EC2 where possible"),
        ("target_runtime_certification_gate", "EC2/target runtime proof only after local package passes and cost-control gates are satisfied"),
        ("translation_table_to_comfyui_names", "map every physics/deformation map to ComfyUI IMAGE/MASK/ControlNet/conditioning equivalent or declare no native equivalent"),
        ("no_fake_physics_rule", "ComfyUI outputs cannot claim true physics unless backed by simulation or explicit approximation label"),
        ("conditioning_package_regression_suite", "regression tests for package structure, map dimensions, routing, output artifacts, and QA evidence"),
    ]
    rows = [
        req(
            "comfyui_physics_conditioning_package",
            f"Build ComfyUI conditioning requirement {target_id}",
            target_id,
            f"Autonomously package, route, validate, and QA {description}.",
            f"{target_id} passes map normalization, route manifest, generated-output proof, whole-artifact QA, and target-runtime gate before certification.",
            [
                "conditioning_package_manifest",
                "map_files_or_sequences",
                "route_manifest_json",
                "generated_output_artifact",
                "technical_validation_report",
                "whole_artifact_visual_qa",
                "target_runtime_evidence_before_final",
            ],
            PHYSICS_QA_GATES + COMFYUI_QA_GATES + AUDIO_QA_GATES,
            priority="P1" if "manifest" in target_id or "route" in target_id or "translation" in target_id else "P2",
            comfyui=True,
            audio="audio" in target_id,
            backend=False,
            notes=description,
        )
        for target_id, description in targets
    ]
    return {
        "wave": 75,
        "slug": "comfyui_physics_conditioning_package",
        "title": "ComfyUI Physics Conditioning Package",
        "purpose": "Convert production physics/simulation outputs into ComfyUI-ready pose, depth, normal, segmentation, contact, deformation, optical-flow, temporal, and audio-linked conditioning packages.",
        "activation_gate": "Deferred. Activate after at least one production simulation package can be generated or approximated and the current ComfyUI runtime lanes are stable.",
        "rows": rows,
    }


def build_wave76() -> dict[str, Any]:
    targets = [
        ("physics_certification_manifest", "one certification manifest tying request, prototype, production base, simulation package, ComfyUI outputs, and QA evidence"),
        ("full_frame_visual_qa", "whole-image/full-frame review for anatomy, identity, hands, feet, face, clothing, props, background, contact, and artifacts"),
        ("full_duration_video_qa", "full clip plus representative frame-grid review for drift, flicker, temporal popping, motion, contact, and loop/cut boundaries"),
        ("full_duration_audio_qa", "audio playback review for clipping, noise, event timing, foley, breath, cloth, support contact, and AV sync"),
        ("mesh_collision_qa", "no clipping, no penetration, collision ownership, backstop behavior, and proxy alignment"),
        ("visual_collision_qa", "generated image/video shows plausible contact, no floating limbs, no impossible overlaps, no contact shadow errors"),
        ("gravity_plausibility_qa", "body gravity, body-part gravity, contact load, sag, drape, rebound, and settling are plausible for scene orientation"),
        ("soft_body_motion_qa", "jiggle, bounce, shake, ripple, rebound, damping, and decay are plausible and not cartoonish unless requested"),
        ("shape_identity_continuity_qa", "body shape, face identity, proportions, hands, feet, and clothing ownership do not drift across frames or rerenders"),
        ("material_surface_detail_qa", "skin pores, wrinkles, cellulite, folds, dents, fabric stress, and surface detail are localized and not over-sharpened"),
        ("multi_character_physics_qa", "multi-character contact, occlusion, ownership, separation, and identity protection pass"),
        ("support_surface_physics_qa", "bed/chair/couch/floor/table/pillow/blanket contact, compression, shadows, and load transfer pass"),
        ("body_region_route_qa", "body regions or sensitive regions only route with explicit geometry evidence and never accidentally"),
        ("proxy_to_final_match_qa", "DAZ prototype, production base, simulation proxy, and final ComfyUI output match enough for physics guidance to be valid"),
        ("map_value_range_qa", "all maps have expected dimensions, frame counts, alpha/value ranges, and coordinate conventions"),
        ("temporal_map_consistency_qa", "temporal masks, flow, motion vectors, deformation maps, and generated frames stay aligned"),
        ("audio_visual_event_alignment_qa", "audio events match visual contact, mouth/breath/chest motion, footsteps, impacts, and cloth movement"),
        ("regression_suite", "rerun proof for schemas, adapter outputs, package routes, visual/audio QA, and target-runtime evidence"),
        ("failure_classification_policy", "classify failures as map, proxy, adapter, ComfyUI route, generation, visual QA, audio QA, or technical blocker"),
        ("final_promotion_gate", "no physics/deformation system row can be marked complete from docs, taxonomies, or one smoke artifact alone"),
    ]
    rows = [
        req(
            "physics_deformation_qa_certification",
            f"Certify QA requirement {target_id}",
            target_id,
            f"Autonomously run or require strict evidence for {description}.",
            f"{target_id} is complete only when strict evidence proves full-artifact visual/video/audio and physics-specific QA passed, or a precise blocker is recorded.",
            [
                "qa_manifest_json",
                "technical_validation_report",
                "visual_review_report",
                "video_review_report_when_applicable",
                "audio_review_report_when_applicable",
                "failure_classification_or_pass_record",
                "promotion_decision_json",
            ],
            PHYSICS_QA_GATES + COMFYUI_QA_GATES + AUDIO_QA_GATES,
            priority="P1",
            risk="Critical",
            comfyui=True,
            backend=False,
            audio="audio" in target_id,
            notes=description,
        )
        for target_id, description in targets
    ]
    return {
        "wave": 76,
        "slug": "physics_deformation_qa_certification",
        "title": "Physics, Deformation, Video, Audio, And Visual QA Certification",
        "purpose": "Define strict technical, visual, video, audio, and promotion gates for the entire autonomous body-physics/deformation system.",
        "activation_gate": "Deferred. Activate after Waves 71-75 have implementation artifacts or approximation packages requiring certification.",
        "rows": rows,
    }


def all_specs() -> list[dict[str, Any]]:
    return [build_wave71(), build_wave72(), build_wave73(), build_wave74(), build_wave75(), build_wave76()]


def build_plan_markdown(spec: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    wave = spec["wave"]
    title = spec["title"]
    rows = spec["rows"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        grouped.setdefault(item["category"], []).append(item)

    lines: list[str] = []
    line_map: dict[str, dict[str, Any]] = {}

    def add(text: str = "") -> None:
        lines.append(text)

    add(f"# Wave{wave} {title}")
    add("")
    add(f"Purpose: {spec['purpose']}")
    add("")
    add(f"Activation gate: {spec['activation_gate']}")
    add("")
    add("This wave is intentionally deferred. It is included so the autonomous project has exact end-to-end planning, Items, Tracker rows, QA gates, and future implementation instructions. It must not displace nearer active ComfyUI runtime, workflow, cost-control, or current-lane work.")
    add("")
    add("Autonomy rule: after any user-supplied prototype/reference asset is registered, all setup, conversion, adapter execution, map generation, routing, testing, QA, visual review, video review, audio review, and blocker recording must be autonomous.")
    add("")
    add("Strict QA rule: no row can be promoted from documentation, taxonomy presence, a single smoke artifact, or target-region-only review. Generated outputs require whole-artifact visual review and, for video/audio work, full-duration temporal/audio review.")
    add("")
    add("External automation references:")
    for ref in EXTERNAL_REFERENCES:
        add(f"- {ref['name']}: {ref['url']} -- {ref['usage']}")
    add("")

    for category, category_rows in grouped.items():
        start = len(lines) + 1
        title_text = category.replace("_", " ").title()
        add(f"## {title_text}")
        add("")
        add(f"Source key prefix: W{wave}:{category}")
        add("")
        add("Completion rule: every row in this section remains Deferred_Required_Not_Complete until the activation gate is met and the row has contract, implementation artifact or adapter route, validation evidence, preview/overlay evidence, strict QA, and promotion evidence.")
        add("")
        add("| requirement | implementation_target | autonomous_behavior | acceptance_summary |")
        add("| --- | --- | --- | --- |")
        for item in category_rows:
            add(
                "| {title} | {target} | {behavior} | {acceptance} |".format(
                    title=item["title"],
                    target=item["implementation_target"],
                    behavior=item["autonomous_behavior"],
                    acceptance=item["acceptance_criteria"],
                )
            )
        add("")
        end = len(lines)
        line_map[category] = {
            "section": title_text,
            "line_start": start,
            "line_end": end,
        }
    return lines, line_map


def enrich_rows(spec: dict[str, Any], line_map: dict[str, dict[str, Any]], plan_md: Path) -> list[dict[str, Any]]:
    wave = spec["wave"]
    enriched = []
    file_size = plan_md.stat().st_size
    for index, item in enumerate(spec["rows"], start=1):
        item = dict(item)
        source = line_map[item["category"]]
        req_id = f"W{wave}-{index:04d}"
        item_id = f"ITEM-W{wave}-{index:04d}"
        tracker_id = f"TRK-W{wave}-{index:04d}"
        source_key = f"W{wave}:{item['category']}:{item['implementation_target']}"
        item.update(
            {
                "requirement_id": req_id,
                "item_id": item_id,
                "tracker_id": tracker_id,
                "source_key": source_key,
                "source_file_relative": rel(plan_md),
                "citation_section": source["section"],
                "citation_line_start": source["line_start"],
                "citation_line_end": source["line_end"],
                "source_file_size": file_size,
            }
        )
        enriched.append(item)
    return enriched


def build_plan_matrix_rows(spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix_rows = []
    for item in rows:
        matrix_rows.append(
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
                "visual_runtime_ready": str(item["visual_runtime_ready"]).lower(),
                "video_runtime_ready": str(item["video_runtime_ready"]).lower(),
                "audio_runtime_ready": str(item["audio_runtime_ready"]).lower(),
                "comfyui_integration_required": str(item["comfyui_integration_required"]).lower(),
                "simulation_backend_required": str(item["simulation_backend_required"]).lower(),
                "deferred_status": "Deferred_Required_Not_Complete",
                "activation_gate": spec["activation_gate"],
                "source_key": item["source_key"],
                "source_file_relative": item["source_file_relative"],
                "citation_section": item["citation_section"],
                "citation_line_start": item["citation_line_start"],
                "citation_line_end": item["citation_line_end"],
            }
        )
    return matrix_rows


def build_item_rows(spec: dict[str, Any], rows: list[dict[str, Any]], plan_md: Path) -> list[dict[str, Any]]:
    item_rows = []
    for item in rows:
        item_rows.append(
            {
                "Item_ID": item["item_id"],
                "Item_Wave": spec["wave"],
                "Item_Type": "deferred_physics_deformation_system_requirement",
                "Item_Title": item["title"],
                "Item_Category": spec["title"],
                "Item_Domain": item["category"],
                "Owner_Domain": "physics_deformation_system",
                "Autonomous_Required": "TRUE",
                "Human_Input_Allowed": "FALSE",
                "Human_Work_Allowed": "FALSE",
                "Codex_Action": "Do not implement before activation gate. When activated, implement or block this requirement with source-cited autonomous evidence and strict QA.",
                "Implementation_Target": item["implementation_target"],
                "Deliverable_Type": "plan_contract_adapter_or_artifact_validation_strict_qa_evidence",
                "Acceptance_Criteria": item["acceptance_criteria"],
                "QA_Gates_Required": join_list(item["qa_gates"]),
                "Visual_Review_Required": "TRUE" if item["visual_runtime_ready"] else "FALSE",
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
                "Citation_Excerpt": f"Wave{spec['wave']} defines {item['implementation_target']} as a deferred autonomous physics/deformation requirement.",
                "Source_Package": f"Wave{spec['wave']} {spec['title']}",
                "Source_Type": "Plan Source",
                "Source_File_Size": item["source_file_size"],
                "Priority": item["priority"],
                "Risk_Level": item["risk"],
                "Status": "Deferred_Required_Not_Complete",
                "Created_From": "generate_waves71_76_physics_deformation_system.py",
                "Notes": item["notes"],
                "Source_Key": item["source_key"],
                "Source_File_Relative": item["source_file_relative"],
                "Coverage_Level": "deferred_direct_physics_deformation_requirement",
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
                "Environment": "deferred_local_first_target_runtime_before_final",
                "Status": "Deferred_Required_Not_Complete",
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
                "Visual_Review_Required": "TRUE" if item["visual_runtime_ready"] else "FALSE",
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
                "Citation_Excerpt": f"Wave{spec['wave']} defines {item['implementation_target']} as a deferred autonomous physics/deformation requirement.",
                "Source_Package": f"Wave{spec['wave']} {spec['title']}",
                "Source_Type": "Plan Source",
                "Source_Item_ID": item["item_id"],
                "Blocker_Policy": "Write exact blocker and continue nearer active project work if prerequisite backend/assets are unavailable.",
                "Rerun_Policy": "Rerun only when prototype, production base, backend, map package, ComfyUI route, generated media, or QA artifact changed.",
                "Status_Decision": "deferred_required_not_complete_until_activation_and_evidence_pass",
                "Notes": item["notes"],
                "Source_Key": item["source_key"],
                "Source_File_Relative": item["source_file_relative"],
                "Coverage_Level": "deferred_direct_physics_deformation_tracker_requirement",
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
        f"Status: Deferred_Required_Not_Complete.",
        "",
        f"Purpose: {spec['purpose']}",
        "",
        f"Activation gate: {spec['activation_gate']}",
        "",
        "This wave is part of the future autonomous body-physics/deformation system. It must not become the next implementation target unless the active project direction explicitly activates it.",
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
        "- Do not start backend/tool installation or EC2 work just because this wave exists.",
        "- Prefer local validation, schemas, adapter stubs, and future-proof planning until activation.",
        "- When activated, every row needs contract, artifact or adapter route, validation evidence, preview/overlay evidence, generated-output evidence when applicable, and strict whole-artifact QA.",
        "- For video, review the full duration plus frame grids.",
        "- For audio, review full-duration playback, event timing, foley/contact alignment, clipping/noise, mix, and AV sync.",
        "- If blocked, write a precise blocker and return to the nearest active source-cited project task.",
    ]


def counts_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        result[str(row[key])] = result.get(str(row[key]), 0) + 1
    return dict(sorted(result.items()))


def update_manifest(path: Path, waves: list[int], row_count: int, report_paths: list[Path]) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    included = payload.get("included_waves", [])
    added = False
    for wave in waves:
        if wave not in included:
            included.append(wave)
            added = True
    payload["included_waves"] = sorted(included)
    if added and isinstance(payload.get("row_count"), int):
        payload["row_count"] = payload["row_count"] + row_count
    payload["deferred_physics_deformation_system_waves"] = waves
    payload["deferred_physics_deformation_system_row_count"] = row_count
    payload["deferred_physics_deformation_system_reports"] = [rel(path) for path in report_paths]
    payload["deferred_physics_deformation_system_rule"] = (
        "Waves 71-76 are future autonomous body-physics/deformation planning rows. They are not next-action implementation work "
        "until activation gates pass; every row remains Deferred_Required_Not_Complete until strict evidence passes."
    )
    write_json(path, payload)


def main() -> None:
    specs = all_specs()
    generated_at = datetime.now(timezone.utc).isoformat()
    total_rows = 0
    report_paths: list[Path] = []
    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at_utc": generated_at,
        "waves": {},
        "external_references": EXTERNAL_REFERENCES,
        "deferred_rule": "Do not implement Waves 71-76 until active project priorities and activation gates allow it.",
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
            "status": "Deferred_Required_Not_Complete",
            "activation_gate": spec["activation_gate"],
            "row_count": len(enriched),
            "source_files": [rel(plan_md), rel(matrix_csv), rel(scope_md)],
            "items_csv": rel(items_csv),
            "tracker_csv": rel(tracker_csv),
            "common_qa_gates": COMMON_QA_GATES,
            "physics_qa_gates": PHYSICS_QA_GATES,
            "comfyui_qa_gates": COMFYUI_QA_GATES,
            "audio_qa_gates": AUDIO_QA_GATES,
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
            "status": "Deferred_Required_Not_Complete",
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
                "status": "Deferred_Required_Not_Complete",
                "row_count": len(enriched),
                "categories": counts_by(enriched, "category"),
                "requirements": enriched,
                "external_references": EXTERNAL_REFERENCES,
            },
        )

        total_rows += len(enriched)
        report_paths.append(items_report_json)
        report_paths.append(tracker_report_json)
        summary["waves"][str(wave)] = {
            "title": spec["title"],
            "slug": slug,
            "row_count": len(enriched),
            "plan_md": rel(plan_md),
            "matrix_csv": rel(matrix_csv),
            "scope_md": rel(scope_md),
            "items_csv": rel(items_csv),
            "tracker_csv": rel(tracker_csv),
            "status": "Deferred_Required_Not_Complete",
        }

    summary["total_row_count"] = total_rows
    summary["wave_count"] = len(specs)
    write_json(PHYSICS_ROOT / "WAVES71_76_PHYSICS_DEFORMATION_SYSTEM_SUMMARY.json", summary)
    write_text(
        PHYSICS_ROOT / "WAVES71_76_DEFERRED_IMPLEMENTATION_PRIORITY.md",
        [
            "# Waves71-76 Deferred Implementation Priority",
            "",
            "Waves 71-76 fully capture the future autonomous body-physics, DAZ prototype, universal production base, simulation adapter, ComfyUI conditioning, and strict QA system.",
            "",
            "They are not next-action implementation work. The active project should continue the current ComfyUI foundation, runtime lanes, cost controls, workflow generation, Mask Factory proofing, and current QA milestones before activating these waves.",
            "",
            "Activation requires an explicit source-cited decision that the current ComfyUI foundation is stable enough to absorb production-body physics work without creating loop/drift or EC2-cost risk.",
            "",
            "Every row remains Deferred_Required_Not_Complete until implementation artifacts and strict evidence pass.",
        ],
    )

    update_manifest(ITEMS_ROOT / "Manifests" / "items_package_manifest.json", [71, 72, 73, 74, 75, 76], total_rows, report_paths)
    update_manifest(TRACKER_ROOT / "Manifests" / "tracker_package_manifest.json", [71, 72, 73, 74, 75, 76], total_rows, report_paths)

    print(json.dumps({"generated_waves": [71, 72, 73, 74, 75, 76], "total_rows": total_rows}, sort_keys=True))


if __name__ == "__main__":
    main()
