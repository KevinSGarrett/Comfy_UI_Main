from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_waves77_86_physics_deformation_expansion as expansion


CREATED_FROM = "generate_wave87_ec2_simulation_farm_runtime.py"
STATUS = expansion.STATUS
WAVE = 87
SLUG = "ec2_simulation_farm_worker_runtime_artifact_orchestration"
TITLE = "EC2 Simulation Farm Worker Runtime And Artifact Orchestration"
ACTIVATION_GATE = (
    "Deferred. Activate only after the current ComfyUI foundation, Wave70 Mask Factory, "
    "Waves71-86 physics/deformation planning layers, runtime lanes, cost controls, and strict QA gates "
    "are stable enough that this EC2/G7e worker-farm layer will not derail nearer project milestones. "
    "Activation requires an explicit source-cited project decision, valid AWS auth, clean Git gates, "
    "S3 permissions, worker AMI readiness, license availability, and cost-control approval."
)

EC2_FARM_QA_GATES = [
    "worker_ami_or_image_id_recorded",
    "worker_role_declared",
    "instance_type_policy_recorded",
    "aws_region_and_account_recorded_without_secrets",
    "ssm_managed_instance_online_before_dispatch",
    "ssm_command_id_recorded",
    "s3_input_bundle_uri_recorded",
    "s3_output_prefix_recorded",
    "s3_bundle_hash_manifest_validated",
    "tool_license_status_recorded",
    "os_gpu_driver_cuda_tool_versions_recorded",
    "runtime_ttl_watchdog_present",
    "artifact_upload_completed_before_shutdown",
    "final_stopped_state_verified",
    "no_secrets_or_env_values_in_logs",
    "dcv_disabled_for_normal_automation",
    "debug_access_requires_explicit_debug_window",
    "storage_tier_policy_validated",
    "scratch_storage_cleanup_verified",
    "cost_window_report_present",
]

EXTERNAL_REFERENCES = [
    {
        "name": "AWS G7e production GPU runtime",
        "url": "https://aws.amazon.com/ec2/instance-types/g7e/",
        "usage": "Production G7e worker and self-hosted LLM/VLM runtime target with explicit runtime windows and cost controls.",
    },
    {
        "name": "AWS Systems Manager Run Command",
        "url": "https://docs.aws.amazon.com/systems-manager/latest/userguide/run-command.html",
        "usage": "Primary non-SSH dispatch path for worker commands, status polling, logs, and bounded execution.",
    },
    {
        "name": "Amazon DCV",
        "url": "https://docs.aws.amazon.com/dcv/latest/adminguide/what-is-dcv.html",
        "usage": "Debug-only remote desktop access for graphics-heavy tools on EC2; normal production execution must remain scripted/headless.",
    },
    {
        "name": "EC2 AMIs",
        "url": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html",
        "usage": "Worker images should be prebuilt or baked with tool installs, drivers, licenses, smoke tests, and adapter manifests.",
    },
    {
        "name": "EC2 instance store and NVMe SSD",
        "url": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/InstanceStorage.html",
        "usage": "Temporary high-speed scratch/cache storage for simulation packages, render passes, and transient build products.",
    },
    {
        "name": "Amazon FSx for Lustre",
        "url": "https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html",
        "usage": "Optional high-performance shared asset/cache tier for larger future simulation farms; S3 remains the default artifact source of truth.",
    },
    {
        "name": "Blender command line",
        "url": "https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html",
        "usage": "Blender worker should run headless/background Python for production fitting, rigging, map baking, overlays, and exports.",
    },
    {
        "name": "SideFX Houdini batch workflow",
        "url": "https://www.sidefx.com/docs/houdini/render/batch.html",
        "usage": "Houdini worker should run hython/hbatch for procedural, SDF, Vellum, tissue, contact, and support-surface simulation packages.",
    },
    {
        "name": "Unreal Python automation",
        "url": "https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python",
        "usage": "Unreal worker should run Python-driven render-pass, Chaos, Control Rig, Sequencer, and realtime proof automation.",
    },
    {
        "name": "Marvelous Designer Python API",
        "url": "https://developer.marvelousdesigner.com/",
        "usage": "Marvelous/CLO worker should run clothing, blanket, sheet, fabric tension, and cloth/body collision automation where licensed.",
    },
]


def farm_req(
    category: str,
    target: str,
    title: str,
    purpose: str,
    output: str,
    *,
    priority: str = "P1",
    risk: str = "High",
    visual: bool = True,
    video: bool = True,
    audio: bool = False,
    comfyui: bool = False,
    backend: bool = True,
    extra_qa: list[str] | None = None,
) -> dict[str, Any]:
    qa = list(EC2_FARM_QA_GATES)
    qa.extend(extra_qa or [])
    return expansion.req(
        category,
        title,
        target,
        (
            f"Autonomously define, execute when activated, validate, and evidence {target}. "
            f"It must support {purpose}. It must run only through bounded EC2/G7e worker-farm contracts "
            "after DAZ neutral prototype registration, require no human work during normal execution, "
            "write exact blockers when AWS/tool/license/storage prerequisites are unavailable, and avoid docs-only completion."
        ),
        (
            f"{target} is complete only when it has schema/config, worker or adapter implementation route, "
            f"{output}, S3/input/output manifests with hashes, command/status evidence, cost-control evidence, "
            "strict QA, and source-cited ledger evidence."
        ),
        [
            f"{target}_schema_or_contract_json",
            f"{target}_worker_or_adapter_manifest_json",
            f"{target}_s3_input_output_manifest_json",
            f"{target}_command_status_log",
            f"{target}_artifact_hash_manifest_json",
            f"{target}_cost_and_shutdown_evidence_json",
            f"{target}_strict_qa_report_json",
        ],
        qa,
        priority=priority,
        risk=risk,
        visual=visual,
        video=video,
        audio=audio,
        comfyui=comfyui,
        backend=backend,
        notes=f"Purpose: {purpose}. Required output: {output}.",
    )


def worker_req(
    target: str,
    title: str,
    worker_name: str,
    tool_stack: str,
    job_role: str,
    *,
    comfyui: bool = False,
    audio: bool = False,
) -> dict[str, Any]:
    return farm_req(
        "named_worker_amis",
        target,
        title,
        (
            f"prebuilt {worker_name} worker AMI/image with {tool_stack}; it must download a signed S3 job bundle, "
            f"perform {job_role}, upload artifacts, and stop without interactive desktop work"
        ),
        f"{worker_name} AMI manifest, smoke test, adapter command proof, output package, and stopped-state evidence",
        comfyui=comfyui,
        audio=audio,
        extra_qa=[
            f"{worker_name.replace('-', '_')}_smoke_test_pass",
            f"{worker_name.replace('-', '_')}_adapter_command_template_present",
            f"{worker_name.replace('-', '_')}_tool_versions_recorded",
        ],
    )


def wave87_spec() -> dict[str, Any]:
    return {
        "wave": WAVE,
        "slug": SLUG,
        "title": TITLE,
        "purpose": (
            "Make the EC2/G7e-hosted execution model explicit for the future autonomous Soft-Body Physics "
            "And Deformation Map System: job-orchestrated worker AMIs, S3 bundles, SSM dispatch, DCV debug-only "
            "access, storage/cache tiers, bounded lifecycle, artifact pullback, license/driver validation, and "
            "final stopped-state/cost certification."
        ),
        "activation_gate": ACTIVATION_GATE,
        "sections": [
            {
                "title": "Worker Farm Architecture",
                "category": "worker_farm_architecture",
                "rows": [
                    farm_req("worker_farm_architecture", "ec2_worker_farm_manifest", "Define EC2 worker farm manifest", "single manifest for worker roles, AMIs/images, instance types, AWS region, S3 prefixes, IAM role names, dispatch method, TTL, and stop policy", "worker farm manifest"),
                    farm_req("worker_farm_architecture", "worker_role_registry", "Register worker roles", "canonical roles for blender-worker, houdini-worker, unreal-worker, marvelous-cloth-worker, maya-motionbuilder-worker, comfyui-worker, and llm-vlm-supervisor-worker", "worker role registry"),
                    farm_req("worker_farm_architecture", "worker_ami_bake_pipeline", "Define worker AMI bake pipeline", "prebuilt image creation or validation for drivers, tools, plugins, licenses, adapters, smoke tests, SSM agent, DCV debug support, and no-secret logs", "AMI bake report"),
                    farm_req("worker_farm_architecture", "worker_capability_matrix", "Build worker capability matrix", "mapping from physics work order stages to eligible worker types, fallback workers, required licenses, GPU/CPU/RAM/storage needs, and cost tier", "capability matrix"),
                    farm_req("worker_farm_architecture", "worker_instance_type_policy", "Define worker instance type policy", "selection among g5, g6e, g7e.2xlarge, g7e.4xlarge, g7e.12xlarge, or CPU workers by job type, cost, VRAM, and runtime risk", "instance type policy"),
                    farm_req("worker_farm_architecture", "worker_license_os_driver_validation", "Validate worker license OS driver state", "per-worker license availability, OS compatibility, NVIDIA driver, CUDA/runtime, tool version, plugin version, and adapter smoke test before accepting a job", "license OS driver validation report"),
                ],
            },
            {
                "title": "Named Worker AMIs",
                "category": "named_worker_amis",
                "rows": [
                    worker_req("blender_worker_ami", "Define blender-worker AMI", "blender-worker", "Blender, Python, required Blender addons, geometry/media validators, FFmpeg, OpenCV, NumPy, PyTorch, Open3D, and trimesh", "DAZ prototype intake, universal production mesh fitting, rig/mask/map generation, overlays, and export packages"),
                    worker_req("houdini_worker_ami", "Define houdini-worker AMI", "houdini-worker", "Houdini FX, hython/hbatch, PDG/TOPs, Vellum/SDF workflows, USD/Alembic exporters, and validators", "advanced soft tissue, SDF, collision, support-surface, and procedural simulation packages"),
                    worker_req("unreal_worker_ami", "Define unreal-worker AMI", "unreal-worker", "Unreal Engine, Python scripting, Control Rig, Chaos, Sequencer, Movie Render Queue, USD/Alembic, and validators", "realtime proof, render passes, animation playback, Chaos/physics evidence, and reference video packages"),
                    worker_req("marvelous_cloth_worker_ami", "Define marvelous-cloth-worker AMI", "marvelous-cloth-worker", "Marvelous Designer/CLO Python API, garment libraries, fabric presets, Alembic/OBJ/USD export, and validators", "garment, blanket, sheet, fabric tension, drape, and cloth/body collision simulation packages"),
                    worker_req("maya_motionbuilder_worker_ami", "Define maya-motionbuilder-worker AMI", "maya-motionbuilder-worker", "Maya, mayapy/mayabatch, MotionBuilder, pyfbsdk, HumanIK, FBX SDK, animation plugins, and validators", "mocap cleanup, retargeting, rig/skin/blendshape validation, and animation export packages"),
                    worker_req("comfyui_worker_ami", "Define comfyui-worker AMI", "comfyui-worker", "ComfyUI, model registry, nodes, ControlNet/IPAdapter/video/audio routes, queue API, and QA validators", "conditioning package execution, image/video/audio generation, pullback, and whole-artifact QA", comfyui=True, audio=True),
                    worker_req("llm_vlm_supervisor_worker_ami", "Define llm-vlm-supervisor-worker AMI", "llm-vlm-supervisor-worker", "vLLM/SGLang/TGI, reasoning model, VLM, RAG index, prompt packs, review tools, and deterministic validator bindings", "work-order planning, artifact review, correction planning, blocker writing, and final QA review", comfyui=False, audio=True),
                ],
            },
            {
                "title": "S3 Job Bundle And Artifact Package Contracts",
                "category": "s3_job_bundle_artifact_contracts",
                "rows": [
                    farm_req("s3_job_bundle_artifact_contracts", "physics_work_order_json_schema", "Define physics_work_order.json schema", "machine-readable request tying prototype, production base, worker type, tool adapter, map requirements, scene assets, generation requirements, QA gates, and tracker rows", "work order schema and sample"),
                    farm_req("s3_job_bundle_artifact_contracts", "s3_input_job_bundle_schema", "Define S3 input job bundle schema", "S3 package containing DAZ prototype exports, textures, scene refs, tool inputs, config, manifests, hashes, and required acceptance gates before EC2 starts", "S3 input bundle manifest"),
                    farm_req("s3_job_bundle_artifact_contracts", "s3_output_artifact_package_schema", "Define S3 output artifact package schema", "worker output package for rendered frames, maps, simulation caches, logs, previews, overlays, QA reports, command status, cost evidence, and hashes", "S3 output artifact package manifest"),
                    farm_req("s3_job_bundle_artifact_contracts", "s3_model_asset_cache_policy", "Define S3 model asset cache policy", "large model/tool/asset cache paths that avoid Git LFS and reduce EC2-on sync time while preserving exact hashes and provenance", "S3 cache policy"),
                    farm_req("s3_job_bundle_artifact_contracts", "bundle_hash_integrity_gate", "Gate bundle hash integrity", "verify every input, intermediate, and output artifact hash before worker execution, before upload, and before final tracker promotion", "bundle hash validation report"),
                ],
            },
            {
                "title": "SSM Dispatch And Bounded Worker Lifecycle",
                "category": "ssm_dispatch_bounded_lifecycle",
                "rows": [
                    farm_req("ssm_dispatch_bounded_lifecycle", "ssm_dispatch_contract", "Define SSM dispatch contract", "AWS Systems Manager Run Command as the normal command path with command id, timeout, stdout/stderr limits, artifact log path, status polling, and no SSH dependency", "SSM dispatch contract"),
                    farm_req("ssm_dispatch_bounded_lifecycle", "worker_start_health_probe", "Probe worker start and health", "start exact worker instance, wait for instance running, SSM online, GPU visible when needed, disk mounted, S3 accessible, and tool smoke checks before job execution", "start health probe report"),
                    farm_req("ssm_dispatch_bounded_lifecycle", "worker_bootstrap_download_run_contract", "Define worker bootstrap download run contract", "download S3 input bundle, verify manifest, create scratch workspace, run adapter command, write structured logs, and handle precise blockers", "bootstrap run contract"),
                    farm_req("ssm_dispatch_bounded_lifecycle", "adapter_execution_command_contract", "Define adapter execution command contract", "standard command templates for Blender background Python, Houdini hython/hbatch, Unreal Python, Marvelous/CLO automation, mayapy/mayabatch, MotionBuilder, ComfyUI, and LLM/VLM supervisor", "adapter command contract"),
                    farm_req("ssm_dispatch_bounded_lifecycle", "artifact_upload_pullback_contract", "Define artifact upload and pullback contract", "upload output package to S3, verify hashes, optionally pull summary artifacts locally, update tracker evidence paths, and avoid keeping EC2 on for inspection", "artifact upload pullback report"),
                    farm_req("ssm_dispatch_bounded_lifecycle", "worker_stop_verify_contract", "Define worker stop verify contract", "stop instance after artifact upload, wait for stopped, verify final state independently, and record stopped timestamp before marking runtime evidence trustworthy", "stop verification evidence"),
                    farm_req("ssm_dispatch_bounded_lifecycle", "ttl_watchdog_emergency_stop_contract", "Define TTL watchdog emergency stop contract", "instance-side watchdog, local stop attempt, AWS-native emergency stop/scheduled rule, timeout budget, and escalation blocker if stopped state cannot be verified", "TTL watchdog report"),
                ],
            },
            {
                "title": "Storage Cache Debug And Security Policy",
                "category": "storage_cache_debug_security_policy",
                "rows": [
                    farm_req("storage_cache_debug_security_policy", "storage_tier_policy_s3_ebs_nvme_fsx_efs", "Define storage tier policy", "S3 as source of truth, EBS for persistent tool/model cache, NVMe instance store for disposable scratch, and FSx/EFS only when shared high-speed farm storage is justified", "storage tier policy"),
                    farm_req("storage_cache_debug_security_policy", "nvme_scratch_cleanup_policy", "Define NVMe scratch cleanup policy", "temporary scratch mount, space checks, cleanup before stop, no reliance on instance store for source-of-truth artifacts, and failure blocker if upload did not complete", "scratch cleanup report"),
                    farm_req("storage_cache_debug_security_policy", "dcv_debug_only_policy", "Define DCV debug-only policy", "Amazon DCV may be enabled for explicit debug windows only; normal production jobs must remain scripted/headless and must not wait for a human desktop session", "DCV debug policy"),
                    farm_req("storage_cache_debug_security_policy", "iam_least_privilege_secret_redaction_policy", "Define IAM and secret redaction policy", "least-privilege S3/SSM/EC2/IAM permissions, no .env or token printing, redacted logs, scoped prefixes, and failure on secret leakage", "IAM redaction policy"),
                    farm_req("storage_cache_debug_security_policy", "cost_accounting_runtime_window_report", "Build cost accounting runtime window report", "record start time, stop time, instance id, instance type, worker role, queue wait, tool runtime, upload time, stopped verification, and estimated cost class", "cost runtime report"),
                    farm_req("storage_cache_debug_security_policy", "failure_retry_no_loop_policy", "Define failure retry no-loop policy", "bounded retries only on changed input or changed parameter; no repeated EC2 starts for the same failing bundle without new evidence or explicit activation decision", "retry no-loop policy"),
                ],
            },
            {
                "title": "Worker Farm Certification",
                "category": "worker_farm_certification",
                "rows": [
                    farm_req("worker_farm_certification", "ec2_worker_farm_dry_run", "Run EC2 worker farm dry-run certification", "non-render dry run proving S3 bundle download, SSM dispatch, tool smoke test, output package upload, stop verification, and ledger evidence for each worker role", "worker farm dry-run evidence"),
                    farm_req("worker_farm_certification", "ec2_worker_farm_end_to_end_certification", "Certify EC2 worker farm end to end", "full activated path from physics_work_order.json to selected worker, generated package, ComfyUI conditioning/generation where applicable, whole-artifact QA, artifact pullback, and final stopped-state evidence", "worker farm final certification", comfyui=True, audio=True),
                ],
            },
        ],
    }


def update_manifest(path: Path, row_count: int, report_paths: list[Path]) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    included = payload.get("included_waves", [])
    already_included = WAVE in included
    if not already_included:
        included.append(WAVE)
        if isinstance(payload.get("row_count"), int):
            payload["row_count"] += row_count
    payload["included_waves"] = sorted(included)

    expansion_waves = sorted(set(payload.get("deferred_physics_deformation_expansion_waves", [])) | {WAVE})
    if WAVE not in payload.get("deferred_physics_deformation_expansion_waves", []):
        payload["deferred_physics_deformation_expansion_row_count"] = (
            int(payload.get("deferred_physics_deformation_expansion_row_count", 0)) + row_count
        )
    payload["deferred_physics_deformation_expansion_waves"] = expansion_waves

    expansion_reports = list(payload.get("deferred_physics_deformation_expansion_reports", []))
    for report_path in report_paths:
        report_rel = expansion.rel(report_path)
        if report_rel not in expansion_reports:
            expansion_reports.append(report_rel)
    payload["deferred_physics_deformation_expansion_reports"] = expansion_reports

    system_waves = sorted(set(payload.get("deferred_physics_deformation_system_waves", [])) | {WAVE})
    if WAVE not in payload.get("deferred_physics_deformation_system_waves", []):
        payload["deferred_physics_deformation_system_row_count"] = (
            int(payload.get("deferred_physics_deformation_system_row_count", 0)) + row_count
        )
    payload["deferred_physics_deformation_system_waves"] = system_waves
    payload["deferred_physics_deformation_ec2_worker_farm_waves"] = [WAVE]
    payload["deferred_physics_deformation_ec2_worker_farm_row_count"] = row_count
    payload["deferred_physics_deformation_ec2_worker_farm_reports"] = [expansion.rel(path) for path in report_paths]
    payload["deferred_physics_deformation_system_rule"] = (
        "Waves 71-87 are deferred future autonomous body-physics/deformation planning rows. "
        "They are not next-action implementation work until activation gates pass; every row remains "
        "Deferred_Required_Not_Complete until strict implementation evidence passes. Wave87 explicitly "
        "covers EC2/G7e worker AMIs, S3 bundles, SSM dispatch, DCV debug-only access, storage tiers, "
        "bounded lifecycle, artifact pullback, and stopped-state/cost certification."
    )
    expansion.write_json(path, payload)


def update_readme(path: Path, label: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("Deferred Waves 71-86 Physics Coverage", "Deferred Waves 71-87 Physics Coverage")
    text = text.replace("Waves 71-86 are deferred", "Waves 71-87 are deferred")
    text = text.replace("For Waves 71-86,", "For Waves 71-87,")
    if "Wave 87 - Deferred EC2 simulation farm worker runtime and artifact orchestration" not in text:
        text = text.replace(
            "- Wave 86 - Expanded physics deformation final certification gates",
            "- Wave 86 - Expanded physics deformation final certification gates\n"
            "- Wave 87 - Deferred EC2 simulation farm worker runtime and artifact orchestration",
        )
    filename = f"wave87_{SLUG}_{label}.csv"
    if filename not in text:
        anchor = f"wave86_expanded_physics_deformation_final_certification_gates_{label}.csv"
        text = text.replace(anchor, anchor + "\n" + filename)
    text = text.replace(
        "tissue inference -> tool adapters -> AI supervisor -> support surfaces -> muscle/grip/force -> physics maps -> simulation adapters -> ComfyUI conditioning -> strict QA system",
        "tissue inference -> tool adapters -> AI supervisor -> support surfaces -> muscle/grip/force -> physics maps -> EC2 worker farm -> simulation adapters -> ComfyUI conditioning -> strict QA system",
    )
    expansion.write_text(path, text.splitlines())


def write_master_blueprints(summary: dict[str, Any]) -> None:
    previous_summary = json.loads(
        (expansion.PHYSICS_ROOT / "WAVES77_86_PHYSICS_DEFORMATION_EXPANSION_SUMMARY.json").read_text(encoding="utf-8")
    )
    wave_rows = dict(previous_summary.get("waves", {}))
    wave_rows[str(WAVE)] = summary["waves"][str(WAVE)]
    lines = [
        "# Waves71-87 Master Autonomous Physics And Deformation Blueprint",
        "",
        f"Status: {STATUS}.",
        "",
        "This blueprint extends Waves71-86 with Wave87 so the future autonomous Soft-Body Physics And Deformation Map System has explicit EC2/G7e worker-farm runtime coverage.",
        "",
        "Deferred priority rule: do not activate this system until a source-cited project decision says the current ComfyUI foundation, Wave70 Mask Factory, runtime lanes, cost controls, and QA gates are stable enough. These files are planning and ledger coverage, not completion evidence.",
        "",
        "DAZ boundary: DAZ is only the neutral A-pose or T-pose prototype source. After registration, every conversion, fit, rig, simulation, map bake, material bake, animation, grip, support-surface, ComfyUI, QA, correction, tracker update, blocker, EC2 dispatch, artifact upload, and shutdown verification must be autonomous outside DAZ.",
        "",
        "EC2 worker-farm boundary:",
        "",
        "- Normal execution is job-orchestrated, not an always-on manual desktop.",
        "- GitHub Actions/local validation prepares the bundle while EC2 is off.",
        "- S3 stores input bundles, output packages, model/tool caches, manifests, and QA evidence.",
        "- SSM Run Command dispatches bounded worker jobs; SSH is not the normal path.",
        "- DCV is debug-only and requires an explicit debug window; normal jobs remain scripted/headless.",
        "- Each worker starts, downloads bundle, verifies hashes, runs adapter, uploads artifacts, stops, and verifies stopped state.",
        "- S3 is source of truth; EBS may cache persistent tools/models; NVMe instance store is disposable scratch; FSx/EFS are optional future shared-cache tiers only when justified.",
        "",
        "End-to-end chain:",
        "",
        "1. Register DAZ neutral prototype.",
        "2. Load Blender-owned universal production base.",
        "3. Fit production mesh without changing topology or UVs.",
        "4. Transfer high-poly/reference detail into production maps.",
        "5. Infer body composition and tissue material parameters.",
        "6. Generate rig, collision, gravity, support-surface, muscle, grip, and force maps.",
        "7. Create physics_work_order.json and S3 input bundle.",
        "8. Select exact EC2 worker AMI/image and dispatch through SSM.",
        "9. Run bounded tool adapter and upload S3 output package.",
        "10. Package ComfyUI conditioning assets.",
        "11. Generate proof media.",
        "12. Run deterministic validators, VLM review, full visual/video/audio QA, artifact pullback, stopped-state verification, cost report, and source-cited tracker closure.",
        "",
        "Generated expansion waves:",
        "",
    ]
    for wave, data in sorted(wave_rows.items(), key=lambda kv: int(kv[0])):
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
            "- If any required tool, license, model, asset, backend, AWS auth, S3 permission, worker AMI, or confidence threshold is missing, write an exact blocker and continue nearer active project work.",
        ]
    )
    expansion.write_text(expansion.PHYSICS_ROOT / "WAVES71_87_MASTER_AUTONOMOUS_PHYSICS_DEFORMATION_BLUEPRINT.md", lines)
    expansion.write_text(
        expansion.PHYSICS_ROOT / "WAVES71_86_MASTER_AUTONOMOUS_PHYSICS_DEFORMATION_BLUEPRINT.md",
        [
            "# Waves71-86 Master Autonomous Physics And Deformation Blueprint",
            "",
            "Superseded for current planning by `WAVES71_87_MASTER_AUTONOMOUS_PHYSICS_DEFORMATION_BLUEPRINT.md`.",
            "",
            "Wave87 adds the EC2/G7e worker-farm runtime, S3 bundle, SSM dispatch, DCV debug-only, storage/cache, lifecycle, artifact pullback, and stopped-state/cost certification coverage that was not explicit enough in Waves71-86.",
        ],
    )
    expansion.write_text(
        expansion.PHYSICS_ROOT / "WAVES77_87_DEFERRED_IMPLEMENTATION_PRIORITY.md",
        [
            "# Waves77-87 Deferred Implementation Priority",
            "",
            "Waves 77-87 expand the future autonomous body-physics/deformation system with AI supervision, tool adapters, tissue inference, muscle/grip force, support surfaces, detail/material maps, temporal animation, work-order orchestration, EC2 worker-farm runtime, and final certification.",
            "",
            "They are not next-action implementation work. The active project should continue the current ComfyUI foundation, runtime lanes, cost controls, workflow generation, Mask Factory proofing, and current QA milestones before activating these waves.",
            "",
            "Activation requires an explicit source-cited decision that the current ComfyUI foundation and Waves 71-76 base physics system are stable enough to absorb this expansion without loop/drift or G7e/EC2 cost risk.",
            "",
            "Every row remains Deferred_Required_Not_Complete until implementation artifacts and strict evidence pass.",
        ],
    )


def main() -> None:
    expansion.EXTERNAL_REFERENCES = EXTERNAL_REFERENCES
    spec = wave87_spec()
    generated_at = datetime.now(timezone.utc).isoformat()
    wave = spec["wave"]
    slug = spec["slug"]
    wave_dir_items = expansion.ITEMS_ROOT / "Waves" / f"Wave{wave}"
    wave_dir_tracker = expansion.TRACKER_ROOT / "Waves" / f"Wave{wave}"
    scope_md = expansion.PLAN / "Instructions" / "Waves" / f"Wave{wave}" / f"WAVE{wave}_SCOPE.md"
    plan_md = expansion.PHYSICS_ROOT / f"WAVE{wave}_{slug.upper()}.md"
    plan_json = expansion.PHYSICS_ROOT / f"WAVE{wave}_{slug.upper()}.json"
    matrix_csv = expansion.PHYSICS_ROOT / f"WAVE{wave}_{slug.upper()}_MATRIX.csv"
    items_csv = expansion.ITEMS_ROOT / f"wave{wave}_{slug}_itemized_list.csv"
    items_wave_csv = wave_dir_items / f"WAVE{wave}_{slug.upper()}_ITEM_ROWS.csv"
    items_req_json = wave_dir_items / f"WAVE{wave}_{slug.upper()}_REQUIREMENTS.json"
    items_report_json = expansion.ITEMS_ROOT / "Reports" / f"wave{wave}_{slug}_coverage_report.json"
    tracker_csv = expansion.TRACKER_ROOT / f"wave{wave}_{slug}_tracker.csv"
    tracker_wave_csv = wave_dir_tracker / f"WAVE{wave}_{slug.upper()}_TRACKER_ROWS.csv"
    tracker_req_json = wave_dir_tracker / f"WAVE{wave}_{slug.upper()}_REQUIREMENTS.json"
    tracker_report_json = expansion.TRACKER_ROOT / "Reports" / f"wave{wave}_{slug}_coverage_report.json"

    md_lines, line_map = expansion.build_plan_markdown(spec)
    expansion.write_text(plan_md, md_lines)
    enriched = expansion.enrich_rows(spec, line_map, plan_md)
    matrix_rows = expansion.build_plan_matrix_rows(spec, enriched)
    item_rows = expansion.build_item_rows(spec, enriched, plan_md)
    tracker_rows = expansion.build_tracker_rows(spec, enriched, plan_md, matrix_csv)

    for row in item_rows:
        row["Item_Type"] = "deferred_physics_deformation_ec2_worker_farm_requirement"
        row["Created_From"] = CREATED_FROM
        row["Notes"] = row["Notes"] + " EC2 worker-farm runtime coverage; EC2 remains disallowed until activation gates pass."
    for row in tracker_rows:
        row["Notes"] = row["Notes"] + " EC2 worker-farm runtime coverage; EC2 remains disallowed until activation gates pass."

    expansion.write_csv(matrix_csv, expansion.PLAN_MATRIX_HEADER, matrix_rows)
    expansion.write_csv(items_csv, expansion.ITEMS_HEADER, item_rows)
    expansion.write_csv(items_wave_csv, expansion.ITEMS_HEADER, item_rows)
    expansion.write_csv(tracker_csv, expansion.TRACKER_HEADER, tracker_rows)
    expansion.write_csv(tracker_wave_csv, expansion.TRACKER_HEADER, tracker_rows)
    expansion.write_text(scope_md, expansion.build_scope_md(spec, plan_md, matrix_csv, items_csv, tracker_csv))

    requirements_payload = {
        "schema_version": "1.0",
        "wave": wave,
        "title": spec["title"],
        "slug": slug,
        "generated_at_utc": generated_at,
        "status": STATUS,
        "activation_gate": spec["activation_gate"],
        "row_count": len(enriched),
        "source_files": [expansion.rel(plan_md), expansion.rel(matrix_csv), expansion.rel(scope_md)],
        "items_csv": expansion.rel(items_csv),
        "tracker_csv": expansion.rel(tracker_csv),
        "common_qa_gates": expansion.COMMON_QA_GATES,
        "physics_qa_gates": expansion.PHYSICS_QA_GATES,
        "comfyui_qa_gates": expansion.COMFYUI_QA_GATES,
        "audio_qa_gates": expansion.AUDIO_QA_GATES,
        "expansion_qa_gates": expansion.EXPANSION_QA_GATES,
        "ec2_farm_qa_gates": EC2_FARM_QA_GATES,
        "external_references": EXTERNAL_REFERENCES,
    }
    expansion.write_json(items_req_json, requirements_payload)
    expansion.write_json(tracker_req_json, requirements_payload)

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
        "categories": expansion.counts_by(enriched, "category"),
        "status": STATUS,
        "activation_gate": spec["activation_gate"],
        "required_files": {
            "plan_md": expansion.rel(plan_md),
            "plan_json": expansion.rel(plan_json),
            "matrix_csv": expansion.rel(matrix_csv),
            "scope_md": expansion.rel(scope_md),
            "items_csv": expansion.rel(items_csv),
            "items_wave_csv": expansion.rel(items_wave_csv),
            "tracker_csv": expansion.rel(tracker_csv),
            "tracker_wave_csv": expansion.rel(tracker_wave_csv),
        },
        "known_boundary": "Generated planning/ledger rows do not prove EC2 worker-farm implementation completion.",
    }
    expansion.write_json(items_report_json, report_payload)
    expansion.write_json(tracker_report_json, report_payload)
    expansion.write_json(
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
            "categories": expansion.counts_by(enriched, "category"),
            "requirements": enriched,
            "ec2_farm_qa_gates": EC2_FARM_QA_GATES,
            "external_references": EXTERNAL_REFERENCES,
        },
    )

    summary = {
        "schema_version": "1.0",
        "generated_at_utc": generated_at,
        "status": STATUS,
        "wave_count": 1,
        "total_row_count": len(enriched),
        "deferred_rule": "Do not implement Wave87 until active project priorities and activation gates allow it.",
        "external_references": EXTERNAL_REFERENCES,
        "waves": {
            str(wave): {
                "title": spec["title"],
                "slug": slug,
                "row_count": len(enriched),
                "plan_md": expansion.rel(plan_md),
                "matrix_csv": expansion.rel(matrix_csv),
                "scope_md": expansion.rel(scope_md),
                "items_csv": expansion.rel(items_csv),
                "tracker_csv": expansion.rel(tracker_csv),
                "status": STATUS,
            }
        },
    }
    expansion.write_json(expansion.PHYSICS_ROOT / "WAVE87_EC2_SIMULATION_FARM_RUNTIME_SUMMARY.json", summary)
    write_master_blueprints(summary)
    report_paths = [items_report_json, tracker_report_json]
    update_manifest(expansion.ITEMS_ROOT / "Manifests" / "items_package_manifest.json", len(enriched), report_paths)
    update_manifest(expansion.TRACKER_ROOT / "Manifests" / "tracker_package_manifest.json", len(enriched), report_paths)
    update_readme(expansion.ITEMS_ROOT / "README.md", "itemized_list")
    update_readme(expansion.TRACKER_ROOT / "README.md", "tracker")

    print(json.dumps({"generated_waves": [wave], "total_rows": len(enriched)}, sort_keys=True))


if __name__ == "__main__":
    main()
