from __future__ import annotations

import hashlib
import json
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
IMAGE_QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Image_Artifact_QA"
WORKFLOW_QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Workflow_Runtime"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "Hydration_Rehydration"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
HUMAN_TS = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%dT%H:%M:%S-05:00")
EVIDENCE_ID = f"W70_NOSE_CANDIDATE_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "combined_gold_gate_decision": (QA_DIR, "W70_FACIAL_COMBINED_GOLD_GATE_DECISION_*.json"),
    "combined_gold_postprocess_route_eval": (QA_DIR, "W70_COMBINED_GOLD_POSTPROCESS_ROUTE_EVAL_*.json"),
    "nose_parser_derived_v5": (QA_DIR, "W70_MF70_NOSE_PARSER_DERIVED_V5_*.json"),
    "nose_v5_local_visual_qa": (
        IMAGE_QA_DIR,
        "W70_LOCAL_MF70_NOSE_V5_PARSER_DERIVED_SEED210825_VISUAL_QA_*.json",
    ),
    "nose_v5_local_runtime": (
        WORKFLOW_QA_DIR,
        "W70_LOCAL_MF70_NOSE_V5_PARSER_DERIVED_SEED210825_EXECUTE_*.json",
    ),
    "post_nose_v5_geometry_gate": (QA_DIR, "W70_MASK_GEOMETRY_HARD_GATE_POST_NOSE_V5_LOCAL_PROOF_*.json"),
    "post_nose_v5_promotion_gate": (QA_DIR, "W70_MASK_PROMOTION_HARD_GATE_POST_NOSE_V5_LOCAL_PROOF_*.json"),
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No evidence found for {directory / pattern}")
    return matches[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_record(name: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "path": rel(path),
        "sha256": sha256(path),
        "result": payload.get("result"),
    }


def combined_region_record(payload: dict[str, Any], region: str) -> dict[str, Any]:
    for record in payload.get("region_decisions", []):
        if record.get("region") == region:
            return record
    raise RuntimeError(f"Combined gold gate has no {region} record")


def postprocess_region_record(payload: dict[str, Any], region: str) -> dict[str, Any]:
    for record in payload.get("region_route_records", []):
        if record.get("region") == region:
            return record
    raise RuntimeError(f"Postprocess route eval has no {region} record")


def hard_gate_counts(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": payload.get("evidence_id"),
        "result": payload.get("result"),
        "checked_count": payload.get("checked_count") or payload.get("total_checked"),
        "pass_like_count": payload.get("pass_like_count") or payload.get("pass_like"),
        "failure_count": payload.get("failure_count") or payload.get("failures"),
    }


def prepend_once(path: Path, section: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(section.rstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def append_once(path: Path, section: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n" + section.rstrip() + "\n", encoding="utf-8")


def csv_row(fields: list[str]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="")
    writer.writerow(fields)
    return output.getvalue()


def update_hydration(evidence_rel: str, tracker_rel: str, selected_policy: str) -> None:
    marker = f"W70-NOSE-CANDIDATE-POLICY-{RUN_STAMP}"
    section = f"""## Immediate Next Action - Nose Candidate Policy Recorded - {HUMAN_TS}

The current `mf70_nose` route is now explicitly recorded as a gold-supported candidate only, not a promotion or certification-ready mask. Evidence `{evidence_rel}` selects `{selected_policy}`: combined CelebAMask-HQ+LaPa gate passes, combined postprocess route `open_r4` passes, and the local v5 generated-output visual QA passes with notes, while `mask_promoted=false`, `active_input_mask_overwritten=false`, `target_runtime_proof_present=false`, and `reference_image_matrix_pass=false`.

Next exact action: continue concrete non-mask ComfyUI runtime/orchestration work or another gold-backed row that does not consume candidate masks as truth. Do not promote `mf70_nose`, overwrite active inputs, claim Wave70 certification, start EC2, activate Wave71+, switch to Jira bookkeeping, or use `C:\\Comfy_UI`.
"""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_PURSUING_GOAL.md",
        "CURRENT_SESSION_STATE.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend_once(HYDRATION_DIR / name, section, marker)

    proof_row = csv_row(
        [
            HUMAN_TS,
            "70",
            f"mf70_nose candidate policy {marker}",
            "Recorded mf70_nose as gold-supported local candidate only; promotion and certification remain blocked",
            f"{evidence_rel}; {tracker_rel}",
            "existing combined gold gate; postprocess route eval; local v5 visual QA; runtime evidence readback",
            "CANDIDATE_SUPPORTED_POLICY_NO_PROMOTION",
            evidence_rel,
            "Continue concrete non-mask runtime/orchestration or another gold-backed row without consuming candidate masks as truth",
        ]
    )
    append_once(HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv", proof_row, marker)


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(directory, pattern) for name, (directory, pattern) in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    combined = combined_region_record(sources["combined_gold_gate_decision"], "mf70_nose")
    postprocess = postprocess_region_record(sources["combined_gold_postprocess_route_eval"], "mf70_nose")
    visual_qa = sources["nose_v5_local_visual_qa"]
    runtime = sources["nose_v5_local_runtime"]

    combined_all_gold_pass = not combined.get("blocked_by") and set(combined.get("passed_by", [])) >= {
        "CelebAMask-HQ",
        "LaPa",
    }
    postprocess_pass = bool(postprocess.get("best_pass_gate"))
    local_visual_pass = visual_qa.get("result") == "pass_with_notes_local_wave70_nose_v5_parser_derived_generated_output"
    local_runtime_pass = runtime.get("result") == "pass_local_run_package_generation_smoke"
    promoted = any(bool(sources[name].get("mask_promoted")) for name in sources)
    overwritten = any(bool(sources[name].get("active_input_mask_overwritten")) for name in sources)
    target_runtime_proof_present = bool(visual_qa.get("target_runtime_proof_present"))
    reference_image_matrix_pass = bool(visual_qa.get("reference_image_matrix_pass"))
    candidate_supported = combined_all_gold_pass and postprocess_pass and local_visual_pass and local_runtime_pass
    promotion_ready = (
        candidate_supported
        and not promoted
        and not overwritten
        and target_runtime_proof_present
        and reference_image_matrix_pass
    )

    policy_options = [
        {
            "policy": "promote_mf70_nose_from_current_gold_and_local_v5_candidate",
            "decision": "rejected",
            "reason": (
                "Current evidence is candidate support only: the combined gold gate and postprocess route explicitly say not promotion, "
                "and the local visual QA lacks target-runtime and reference-matrix completion."
            ),
        },
        {
            "policy": "treat_local_generated_output_as_final_certification",
            "decision": "rejected",
            "reason": (
                "The local v5 proof is a generated-output stability check with notes. It does not prove generalization, target-runtime behavior, "
                "or final reference-image matrix coverage."
            ),
        },
        {
            "policy": "candidate_supported_no_promotion_until_target_runtime_and_reference_matrix_proof",
            "decision": "selected",
            "reason": (
                "Nose is supported by current gold gates and local proof, but project promotion/certification requires separate target-runtime, "
                "reference-matrix, and explicit promotion authority evidence."
            ),
        },
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_nose candidate policy decision from existing gold-gate, postprocess, and local v5 proof evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_nose",
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "combined_gold_nose_record": combined,
        "combined_gold_postprocess_record": postprocess,
        "local_v5_visual_qa_summary": {
            "result": visual_qa.get("result"),
            "status_after_qa": visual_qa.get("status_after_qa"),
            "semantic_mask_alignment_candidate_pass": visual_qa.get("semantic_mask_alignment_candidate_pass"),
            "generated_output_safe_pass": visual_qa.get("generated_output_safe_pass"),
            "target_runtime_proof_present": visual_qa.get("target_runtime_proof_present"),
            "reference_image_matrix_pass": visual_qa.get("reference_image_matrix_pass"),
            "final_completion_allowed": visual_qa.get("final_completion_allowed"),
            "promotion_allowed": visual_qa.get("promotion_allowed"),
            "boundary": visual_qa.get("boundary"),
        },
        "local_v5_runtime_summary": {
            "result": runtime.get("result"),
            "generation_executed": runtime.get("generation_executed"),
            "ec2_started": runtime.get("ec2_started"),
        },
        "post_nose_v5_geometry_gate": hard_gate_counts(sources["post_nose_v5_geometry_gate"]),
        "post_nose_v5_promotion_gate": hard_gate_counts(sources["post_nose_v5_promotion_gate"]),
        "combined_all_gold_policy_pass": combined_all_gold_pass,
        "combined_gold_postprocess_policy_pass": postprocess_pass,
        "local_v5_visual_qa_pass_with_notes": local_visual_pass,
        "local_v5_runtime_pass": local_runtime_pass,
        "target_runtime_proof_present": target_runtime_proof_present,
        "reference_image_matrix_pass": reference_image_matrix_pass,
        "candidate_supported_by_current_evidence": candidate_supported,
        "current_nose_promotion_ready": promotion_ready,
        "policy_options": policy_options,
        "selected_policy": "candidate_supported_no_promotion_until_target_runtime_and_reference_matrix_proof",
        "result": "mf70_nose_candidate_supported_policy_no_promotion",
        "decision": (
            "Keep mf70_nose as the current gold-supported local candidate. Do not promote it, overwrite active inputs, or claim final Wave70 certification "
            "until target-runtime proof, reference-matrix proof, and explicit promotion authority are present."
        ),
        "next_required_action": (
            "Continue concrete non-mask ComfyUI runtime/orchestration work or another gold-backed row that does not consume candidate masks as truth."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    update_hydration(rel(evidence_path), rel(tracker_path), evidence["selected_policy"])

    print(
        json.dumps(
            {
                "evidence": rel(evidence_path),
                "tracker": rel(tracker_path),
                "result": evidence["result"],
                "selected_policy": evidence["selected_policy"],
                "combined_all_gold_policy_pass": combined_all_gold_pass,
                "combined_gold_postprocess_policy_pass": postprocess_pass,
                "local_v5_visual_qa_pass_with_notes": local_visual_pass,
                "local_v5_runtime_pass": local_runtime_pass,
                "target_runtime_proof_present": target_runtime_proof_present,
                "reference_image_matrix_pass": reference_image_matrix_pass,
                "current_nose_promotion_ready": promotion_ready,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
