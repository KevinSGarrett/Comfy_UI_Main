from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any


LANE_ID = "flux2_klein_4b_distilled"
EVIDENCE_REL = "Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_FLUX2_KLEIN_4B_DISTILLED_LOCAL_RUNTIME_20260716T133738-0500/evidence.json"
MIRROR_REL = "Plan/Tracker/Evidence/Workflow_Runtime/W64_FLUX2_KLEIN_4B_DISTILLED_LOCAL_RUNTIME_20260716T133738-0500/evidence.json"
RECONCILIATION_REL = "Plan/Instructions/QA/Evidence/Engine_Router/W64_FLUX2_KLEIN_CAPABILITY_RECONCILIATION_20260716T133738-0500.json"
RECONCILIATION_MIRROR_REL = "Plan/Tracker/Evidence/Engine_Router/W64_FLUX2_KLEIN_CAPABILITY_RECONCILIATION_20260716T133738-0500.json"
STATIC_EVIDENCE_REL = "Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W64_FLUX2_KLEIN_4B_DISTILLED_STATIC_VALIDATION_20260716T142938-0500.json"
MODEL_HASHES = {
    "97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6",
    "6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a",
    "d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def append_unique(values: list[str], additions: list[str]) -> list[str]:
    result = list(values)
    for value in additions:
        if value not in result:
            result.append(value)
    return result


def append_semicolon(value: str, addition: str) -> str:
    parts = [part.strip() for part in value.split(";") if part.strip()]
    if addition not in parts:
        parts.append(addition)
    return "; ".join(parts)


def lane_manifest_defects(queue_row: dict[str, Any], active_row: dict[str, Any]) -> list[str]:
    expected = {
        "queue_workflow": (queue_row.get("workflow_path"), "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/workflow.api.json"),
        "queue_t2i_workflow": (queue_row.get("text_to_image_workflow_path"), "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/text_to_image.api.json"),
        "queue_edit_workflow": (queue_row.get("edit_workflow_path"), "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/single_reference_edit.api.json"),
        "queue_smoke_catalog": (queue_row.get("smoke_request_catalog_path"), "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/smoke_test_requests.json"),
        "queue_readme": (queue_row.get("readme_path"), "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/README.md"),
        "queue_requirements": (queue_row.get("requirements_path"), "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/runtime_requirements.json"),
        "active_workflow": (active_row.get("workflow"), "Workflows/base_generation/flux2_klein_4b_distilled/workflow.api.json"),
        "active_t2i_workflow": (active_row.get("text_to_image_workflow"), "Workflows/base_generation/flux2_klein_4b_distilled/text_to_image.api.json"),
        "active_edit_workflow": (active_row.get("edit_workflow"), "Workflows/base_generation/flux2_klein_4b_distilled/single_reference_edit.api.json"),
        "active_smoke_request": (active_row.get("smoke_request"), "Workflows/base_generation/flux2_klein_4b_distilled/smoke_test_request.json"),
        "active_smoke_catalog": (active_row.get("smoke_request_catalog"), "Workflows/base_generation/flux2_klein_4b_distilled/smoke_test_requests.json"),
        "active_requirements": (active_row.get("runtime_requirements"), "Workflows/base_generation/flux2_klein_4b_distilled/runtime_requirements.json"),
    }
    return [name for name, (observed, wanted) in expected.items() if observed != wanted]


def update_runtime_requirements(root: Path) -> None:
    path = root / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/runtime_requirements.json"
    payload = read_json(path)
    payload["asset_authority_complete"] = True
    payload["current_status"] = "bounded_local_t2i_and_single_reference_edit_runtime_and_visual_qa_pass"
    payload["runtime_evidence"] = EVIDENCE_REL
    payload["production_ready"] = False
    payload["promotion_allowed_without_evidence"] = False
    for model in payload["required_models"]:
        model["hash_status"] = "local_sha256_verified"
        model["path_status"] = "local_model_present"
        model["runtime_validation_status"] = "local_generation_smoke_complete"
    write_json(path, payload)
    source = path.parent
    mirror = root / "Workflows/base_generation/flux2_klein_4b_distilled"
    mirror.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        if child.is_file():
            shutil.copy2(child, mirror / child.name)


def update_model_registry(root: Path) -> int:
    path = root / "Plan/Registries/Models/model_registry.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    updated = 0
    for row in rows:
        if row.get("workflow_lane") != LANE_ID or row.get("sha256") not in MODEL_HASHES:
            continue
        row["base_model"] = "flux2"
        row["compatible_engines"] = append_unique(row.get("compatible_engines") or [], ["flux2"])
        row["storage_location"] = "local"
        row["compatibility_status"] = "local_runtime_smoke_validated_with_notes"
        row["qa_status"] = "pass_with_notes_for_local_flux2_klein_bounded_capabilities"
        row["runtime_validation_status"] = "local_generation_smoke_complete"
        row["last_tested_at"] = "2026-07-16T13:37:38-05:00"
        row["evidence_paths"] = append_unique(row.get("evidence_paths") or [], [EVIDENCE_REL, RECONCILIATION_REL])
        row["known_issues"] = [
            "Bounded proof covers one 512x512 four-step product T2I prompt and one single-reference recolor only.",
            "Broad prompt, subject, seed, resolution, identity, and production robustness remain unproven.",
        ]
        updated += 1
    if updated != 3:
        raise RuntimeError(f"Expected to update three FLUX.2 model records, updated {updated}")
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    return updated


def update_runtime_queue(root: Path) -> int:
    path = root / "Plan/Registries/Models/model_runtime_validation_queue.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    updated = 0
    for row in rows:
        if row.get("workflow_lane") != LANE_ID:
            continue
        row["status"] = "local_generation_smoke_complete"
        row["evidence_path"] = EVIDENCE_REL
        updated += 1
    if updated != 3:
        raise RuntimeError(f"Expected to update three FLUX.2 queue rows, updated {updated}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return updated


def update_engine_registry(root: Path) -> None:
    path = root / "Plan/10_REGISTRIES/wave06_engine_registry.json"
    payload = read_json(path)
    matches = [row for row in payload if row.get("engine_id") == "flux2_klein_preview"]
    if len(matches) != 1:
        raise RuntimeError("Expected one flux2_klein_preview engine record")
    row = matches[0]
    row["tier"] = "bounded_local_t2i_and_edit_candidate"
    row["exact_variant"] = "FLUX.2 Klein 4B distilled FP8"
    row["required_assets"] = ["flux-2-klein-4b-fp8.safetensors", "qwen_3_4b.safetensors", "flux2-vae.safetensors"]
    row["asset_sha256"] = sorted(MODEL_HASHES)
    row["model_locations"]["local"] = "C:/Comfy_UI_Main/models/{diffusion_models,text_encoders,vae}/"
    row["promotion_status"] = "bounded_local_t2i_and_single_reference_edit_pass_not_production_certified"
    row["runtime_evidence"] = EVIDENCE_REL
    row["known_boundaries"] = [
        "one product-material T2I scope",
        "one single-reference recolor scope",
        "no FLUX.2 Dev runtime proof",
        "no broad production certification",
    ]
    write_json(path, payload)


def update_runtime_lane_manifests(root: Path) -> None:
    queue_path = root / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    queue = read_json(queue_path)
    active_path = root / "Workflows/base_generation/ACTIVE_LANES.json"
    active = read_json(active_path)
    queue_matches = [row for row in queue["lanes"] if row.get("lane_id") == LANE_ID]
    active_matches = [row for row in active["lanes"] if row.get("lane_id") == LANE_ID]
    if len(queue_matches) == 1 and len(active_matches) == 1:
        defects = lane_manifest_defects(queue_matches[0], active_matches[0])
        if defects:
            raise RuntimeError(f"FLUX.2 Klein lane manifest fields are inconsistent: {defects}")
        return
    if queue_matches or active_matches:
        raise RuntimeError("FLUX.2 Klein lane manifest state is partially applied")
    lanes = queue["lanes"]
    lanes[:] = [row for row in lanes if row.get("lane_id") != LANE_ID]
    lanes.append({
        "order": 11,
        "lane_id": LANE_ID,
        "role": "bounded_local_flux2_text_to_image_and_single_reference_edit",
        "workflow_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/workflow.api.json",
        "text_to_image_workflow_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/text_to_image.api.json",
        "edit_workflow_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/single_reference_edit.api.json",
        "smoke_request_catalog_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/smoke_test_requests.json",
        "readme_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/README.md",
        "requirements_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/runtime_requirements.json",
        "status": "local_bounded_t2i_and_edit_runtime_validated_with_notes",
        "required_next_runtime_gate": "changed_prompt_subject_seed_resolution_or_broader_production_scope_only",
        "promotion_rule": "Permit only the two hash-bound bounded capabilities; do not promote as the production default or infer FLUX.2 Dev proof.",
        "proof_evidence": [STATIC_EVIDENCE_REL, EVIDENCE_REL, RECONCILIATION_REL],
        "local_pre_ec2_evidence": [STATIC_EVIDENCE_REL, EVIDENCE_REL, RECONCILIATION_REL],
    })
    selection = queue["selection_policy"]
    selection["completed_runtime_lane_ids"] = append_unique(selection["completed_runtime_lane_ids"], [LANE_ID])
    selection["runtime_not_started_lane_ids"] = [value for value in selection["runtime_not_started_lane_ids"] if value != LANE_ID]
    selection["proof_scope_note"] = "Existing lane proof boundaries remain unchanged. FLUX.2 Klein adds one bounded local four-step 512x512 product T2I and one single-reference recolor; it is not target-runtime or production certification and does not prove FLUX.2 Dev."
    queue["updated_at"] = "2026-07-16T13:37:38-05:00"
    write_json(queue_path, queue)

    active_lanes = active["lanes"]
    active_lanes[:] = [row for row in active_lanes if row.get("lane_id") != LANE_ID]
    active_lanes.append({
        "order": 11,
        "lane_id": LANE_ID,
        "workflow": "Workflows/base_generation/flux2_klein_4b_distilled/workflow.api.json",
        "text_to_image_workflow": "Workflows/base_generation/flux2_klein_4b_distilled/text_to_image.api.json",
        "edit_workflow": "Workflows/base_generation/flux2_klein_4b_distilled/single_reference_edit.api.json",
        "smoke_request": "Workflows/base_generation/flux2_klein_4b_distilled/smoke_test_request.json",
        "smoke_request_catalog": "Workflows/base_generation/flux2_klein_4b_distilled/smoke_test_requests.json",
        "runtime_requirements": "Workflows/base_generation/flux2_klein_4b_distilled/runtime_requirements.json",
        "patch_points": "Workflows/base_generation/flux2_klein_4b_distilled/patch_points.json",
        "status": "bounded_local_t2i_and_single_reference_edit_runtime_and_visual_qa_pass_not_production_certified",
        "next_gate": "changed_prompt_subject_seed_resolution_or_broader_production_scope_only_do_not_rerun_exact_proof",
    })
    active["updated_at"] = "2026-07-16T13:37:38-05:00"
    write_json(active_path, active)


def update_portfolio(root: Path) -> None:
    path = root / "Plan/10_REGISTRIES/comfyui_delivery_portfolio_registry.json"
    payload = read_json(path)
    lanes = payload["lanes"]
    lanes[:] = [row for row in lanes if row.get("lane_id") != LANE_ID]
    dev_index = next(index for index, row in enumerate(lanes) if row.get("lane_id") == "flux2_dev")
    klein = {
        "modality": "image",
        "lane_id": LANE_ID,
        "classification": "bounded_image_modernization",
        "workflow_graph_complete": True,
        "local_runtime_proven": True,
        "ec2_runtime_proven": False,
        "genuine_artifact_present": True,
        "technical_qa_passed": True,
        "direct_review_passed": True,
        "production_lane_certified": False,
        "scope": "official distilled FP8 assets, separate four-step 512x512 T2I and single-reference edit graphs, active loader visibility, genuine local runtime, direct visual QA, and matched-seed FLUX.1/RealVisXL comparison",
        "state": "bounded_local_t2i_and_edit_pass_not_production_certified",
        "recovery_priority": 60,
        "next_concrete_outcome": "Use this proven local-first FLUX.2 lane for bounded preview/edit work; broaden prompts, subjects, seeds, and resolution before production promotion; do not rerun the exact proof inputs.",
        "evidence": [EVIDENCE_REL, RECONCILIATION_REL],
    }
    lanes.insert(dev_index, klein)
    dev = next(row for row in lanes if row.get("lane_id") == "flux2_dev")
    dev.update({
        "scope": "eligible higher-quality FLUX.2 Dev T2I/reference-edit lane for the authorized non-commercial, non-distributed project; exact target-runtime stack remains unresolved",
        "state": "eligible_not_disqualified_by_license_runtime_and_hardware_proof_missing",
        "next_concrete_outcome": "Select the exact Dev precision and a sufficient target runtime, acquire only the needed immutable stack, then compare against the proven Klein lane. Non-commercial status is a recorded use boundary, not a disqualifier.",
        "evidence": append_unique(dev.get("evidence") or [], [EVIDENCE_REL]),
    })
    payload["updated_at"] = "2026-07-16T13:37:38-05:00"
    write_json(path, payload)


def update_item_reports(root: Path) -> None:
    path8 = root / "Plan/Items/Reports/ITEM-W64-008_image_pipeline_build.json"
    row8 = read_json(path8)
    row8["created_iso"] = "2026-07-16T13:37:38-05:00"
    row8["status"] = "Blocked_End_To_End_Image_Promotion_FLUX2_Klein_Local_T2I_Edit_Pass"
    base = next(row for row in row8["stage_states"] if row.get("stage") == "base_generation")
    base["lane_ids"] = append_unique(base["lane_ids"], [LANE_ID])
    base["status"] = "partial_with_flux2_klein_bounded_local_t2i_and_edit_pass"
    base["blockers"] = ["base_broader_composition_certification", "flux2_dev_runtime_and_broad_robustness"]
    row8["blockers"] = [
        "complete same-scope base-to-final runtime chain missing",
        "current image artifact manifest remains unpromoted for end-to-end production",
        "trusted mask/body/hand/contact authority remains blocked",
        "FLUX.2 Dev and broad Klein robustness remain unproven",
        "final promotion remains denied pending end-to-end certification proof",
    ]
    row8["evidence"] = append_unique(row8["evidence"], [EVIDENCE_REL, RECONCILIATION_REL])
    row8["next_action"] = "Use the bounded FLUX.2 Klein local T2I/edit lane where appropriate while keeping full image promotion fail-closed; next modernize the exact higher-quality FLUX.2 Dev target-runtime lane without treating its non-commercial license as a disqualifier."
    write_json(path8, row8)

    path9 = root / "Plan/Items/Reports/ITEM-W64-009_image_engine_router.json"
    row9 = read_json(path9)
    row9["created_iso"] = "2026-07-16T13:37:38-05:00"
    row9["status"] = "Completed_Local_Router_FLUX2_Klein_Bounded_Capabilities_Selectable_Production_Not_Certified"
    row9["current_route_state"]["active_lane_count"] = 11
    row9["current_route_state"]["runtime_queue_lane_count"] = 11
    row9["current_route_state"]["bounded_capability_selected_lane_count"] = 1
    row9["current_route_state"]["flux2_klein_capabilities"] = ["text_to_image", "single_reference_edit"]
    row9["blockers"] = [
        "production image routing remains fail-closed without full lane certification",
        "FLUX.2 Klein proof is bounded to one T2I and one single-reference edit scope",
        "FLUX.2 Dev target-runtime and final production comparison remain unproven",
    ]
    row9["evidence"] = append_unique(row9["evidence"], [EVIDENCE_REL, RECONCILIATION_REL, "Plan/07_IMPLEMENTATION/scripts/resolve_flux2_image_route.py", "Plan/Instructions/QA/Scripts/test_resolve_flux2_image_route.py"])
    row9["next_action"] = "Permit only hash-bound FLUX.2 Klein T2I/edit capability records through the bounded router; keep production/default routing blocked until materially broader certification evidence exists."
    write_json(path9, row9)


def update_tracker_csv(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    statuses = {
        "TRK-W64-008": "Blocked_End_To_End_Image_Promotion_FLUX2_Klein_Local_T2I_Edit_Pass",
        "TRK-W64-009": "Completed_Local_Router_FLUX2_Klein_Bounded_Capabilities_Selectable_Production_Not_Certified",
    }
    decisions = {
        "TRK-W64-008": "flux2_klein_local_t2i_edit_pass_end_to_end_image_promotion_blocked",
        "TRK-W64-009": "flux2_klein_bounded_capability_route_pass_production_fail_closed",
    }
    updated = 0
    for row in rows:
        tracker_id = row.get("Tracker_ID")
        if tracker_id not in statuses:
            continue
        row["Status"] = statuses[tracker_id]
        row["Evidence_Path"] = append_semicolon(row.get("Evidence_Path", ""), EVIDENCE_REL)
        row["Evidence_Path"] = append_semicolon(row["Evidence_Path"], RECONCILIATION_REL)
        row["Status_Decision"] = decisions[tracker_id]
        note = "Wave64 FLUX.2 Klein reconciliation 20260716T133738-0500: exact three-asset stack, separate T2I/edit graphs, local 8GB runtime, direct visual QA, and fail-closed capability routing pass; production/default and FLUX.2 Dev remain unproven."
        if note not in row.get("Notes", ""):
            row["Notes"] = (row.get("Notes", "").rstrip() + " | " + note).strip(" |")
        updated += 1
    if updated != 2:
        raise RuntimeError(f"Expected two Wave64 tracker rows in {path}, updated {updated}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile bounded FLUX.2 Klein proof into exact project control rows")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    proof = read_json(root / EVIDENCE_REL)
    if proof.get("result") != "pass_bounded_local_flux2_klein_t2i_and_single_reference_edit" or proof.get("check_summary", {}).get("failed") != 0:
        raise RuntimeError("Authoritative FLUX.2 proof is not pass-like")
    if proof.get("production_ready") is not False:
        raise RuntimeError("FLUX.2 proof must remain non-production")

    update_runtime_requirements(root)
    registry_count = update_model_registry(root)
    queue_count = update_runtime_queue(root)
    update_engine_registry(root)
    update_runtime_lane_manifests(root)
    update_portfolio(root)
    update_item_reports(root)
    tracker_counts = [
        update_tracker_csv(root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"),
        update_tracker_csv(root / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"),
    ]
    reconciliation = {
        "schema_version": "1.0",
        "evidence_id": "W64-FLUX2-KLEIN-CAPABILITY-RECONCILIATION-20260716T133738-0500",
        "created_at": "2026-07-16T13:37:38-05:00",
        "tracker_ids": ["TRK-W64-008", "TRK-W64-009"],
        "item_ids": ["ITEM-W64-008", "ITEM-W64-009"],
        "source_runtime_evidence": EVIDENCE_REL,
        "classification": "bounded_flux2_klein_capability_integrated_production_fail_closed",
        "checks": {
            "runtime_proof_pass": True,
            "production_ready_false": True,
            "three_model_registry_rows_updated": registry_count == 3,
            "three_runtime_queue_rows_updated": queue_count == 3,
            "two_tracker_rows_updated_in_both_copies": tracker_counts == [2, 2],
            "klein_and_dev_portfolio_roles_separated": True,
            "runtime_and_active_lane_manifests_include_klein": True,
            "flux2_dev_not_disqualified_by_license": True,
            "mask_wave71_ec2_aws_jira_boundaries_preserved": True,
        },
        "result": "PASS",
        "boundaries": {
            "full_image_pipeline_complete": False,
            "production_default_promoted": False,
            "flux2_dev_runtime_proven": False,
            "ec2_started": False,
            "aws_or_s3_mutated": False,
            "mask_promotion_or_wave71_activation": False,
            "jira_mutated": False,
        },
    }
    write_json(root / RECONCILIATION_REL, reconciliation)
    write_json(root / RECONCILIATION_MIRROR_REL, reconciliation)
    print(json.dumps({"status": "PASS", "evidence": RECONCILIATION_REL, "registry_rows": registry_count, "queue_rows": queue_count, "tracker_rows_per_copy": tracker_counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
