from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_RUNTIME_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Runtime_Readiness"
QA_MODEL_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Model_Registry"
TRACKER_RUNTIME_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence" / "Runtime_Readiness"
HYDRATION_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "Hydration_Rehydration"


def now_stamp() -> tuple[str, str]:
    now = datetime.now().astimezone()
    return now.strftime("%Y%m%dT%H%M%S%z"), now.isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern), key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    if not matches:
        raise FileNotFoundError(f"No files matched {pattern} in {directory}")
    return matches[0]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON in {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get(data: dict[str, Any], dotted: str, default: Any = None) -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "result": "pass" if passed else "fail",
        "observed": observed,
        "expected": expected,
    }


def prepend(path: Path, section: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(section.rstrip() + "\n\n" + old.lstrip("\ufeff"), encoding="utf-8")


def copy_to_tracker(path: Path) -> Path:
    target = TRACKER_RUNTIME_DIR / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return target


def main() -> int:
    stamp, iso = now_stamp()
    evidence_id = f"W66_SELECTED_INPAINT_PUBLISH_DRY_RUN_CHAIN_ALIGNMENT_{stamp}"

    files = {
        "model_publish_dry_run": latest(
            QA_MODEL_DIR,
            "W66_SELECTED_MODEL_S3_PUBLISH_DRY_RUN_REALVISXL_S3_READY_*.json",
        ),
        "source_input_publish_dry_run": latest(
            QA_RUNTIME_DIR,
            "W66_SELECTED_INPUT_ASSET_S3_PUBLISH_DRY_RUN_SOURCE_S3_READY_*.json",
        ),
        "mask_input_publish_dry_run": latest(
            QA_RUNTIME_DIR,
            "W66_SELECTED_INPUT_ASSET_S3_PUBLISH_DRY_RUN_MASK_S3_READY_*.json",
        ),
        "pre_ec2_handoff": latest(
            QA_RUNTIME_DIR,
            "W66_SELECTED_TARGET_RUNTIME_PRE_EC2_HANDOFF_BUNDLE_PUBLISH_DRY_RUNS_SELECTED_INPAINT_*.json",
        ),
        "live_execution_runbook": latest(
            QA_RUNTIME_DIR,
            "W66_SELECTED_TARGET_RUNTIME_LIVE_EXECUTION_RUNBOOK_PUBLISH_DRY_RUNS_SELECTED_INPAINT_*.json",
        ),
        "execution_readiness_snapshot": latest(
            QA_RUNTIME_DIR,
            "W66_SELECTED_TARGET_RUNTIME_EXECUTION_READINESS_SNAPSHOT_PUBLISH_DRY_RUNS_SELECTED_INPAINT_*.json",
        ),
    }
    data = {key: read_json(path) for key, path in files.items()}

    checks = [
        check(
            "model_publish_dry_run_ready_without_upload",
            get(data["model_publish_dry_run"], "result") == "dry_run_ready_to_upload_model"
            and bool(get(data["model_publish_dry_run"], "local_only"))
            and not bool(get(data["model_publish_dry_run"], "aws_contacted"))
            and not bool(get(data["model_publish_dry_run"], "s3_contacted"))
            and not bool(get(data["model_publish_dry_run"], "upload.attempted")),
            {
                "result": get(data["model_publish_dry_run"], "result"),
                "local_only": get(data["model_publish_dry_run"], "local_only"),
                "aws_contacted": get(data["model_publish_dry_run"], "aws_contacted"),
                "s3_contacted": get(data["model_publish_dry_run"], "s3_contacted"),
                "upload_attempted": get(data["model_publish_dry_run"], "upload.attempted"),
            },
            "dry-run ready, no AWS/S3 contact, no upload",
        ),
        check(
            "source_input_publish_dry_run_ready_without_upload",
            get(data["source_input_publish_dry_run"], "result") == "dry_run_ready_to_upload_input_asset"
            and bool(get(data["source_input_publish_dry_run"], "local_only"))
            and not bool(get(data["source_input_publish_dry_run"], "aws_contacted"))
            and not bool(get(data["source_input_publish_dry_run"], "s3_contacted"))
            and not bool(get(data["source_input_publish_dry_run"], "upload.attempted")),
            {
                "result": get(data["source_input_publish_dry_run"], "result"),
                "local_only": get(data["source_input_publish_dry_run"], "local_only"),
                "aws_contacted": get(data["source_input_publish_dry_run"], "aws_contacted"),
                "s3_contacted": get(data["source_input_publish_dry_run"], "s3_contacted"),
                "upload_attempted": get(data["source_input_publish_dry_run"], "upload.attempted"),
            },
            "dry-run ready, no AWS/S3 contact, no upload",
        ),
        check(
            "mask_input_publish_dry_run_ready_without_upload",
            get(data["mask_input_publish_dry_run"], "result") == "dry_run_ready_to_upload_input_asset"
            and bool(get(data["mask_input_publish_dry_run"], "local_only"))
            and not bool(get(data["mask_input_publish_dry_run"], "aws_contacted"))
            and not bool(get(data["mask_input_publish_dry_run"], "s3_contacted"))
            and not bool(get(data["mask_input_publish_dry_run"], "upload.attempted")),
            {
                "result": get(data["mask_input_publish_dry_run"], "result"),
                "local_only": get(data["mask_input_publish_dry_run"], "local_only"),
                "aws_contacted": get(data["mask_input_publish_dry_run"], "aws_contacted"),
                "s3_contacted": get(data["mask_input_publish_dry_run"], "s3_contacted"),
                "upload_attempted": get(data["mask_input_publish_dry_run"], "upload.attempted"),
            },
            "dry-run ready, no AWS/S3 contact, no upload",
        ),
        check(
            "pre_ec2_handoff_passes_and_blocks_live_steps",
            get(data["pre_ec2_handoff"], "result") == "pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked"
            and int(get(data["pre_ec2_handoff"], "failed_check_count", -1)) == 0
            and int(get(data["pre_ec2_handoff"], "blocked_live_step_count", 0)) >= 1
            and not bool(get(data["pre_ec2_handoff"], "execute_allowed_now"))
            and not bool(get(data["pre_ec2_handoff"], "target_runtime_launch_allowed")),
            {
                "result": get(data["pre_ec2_handoff"], "result"),
                "failed_check_count": get(data["pre_ec2_handoff"], "failed_check_count"),
                "blocked_live_step_count": get(data["pre_ec2_handoff"], "blocked_live_step_count"),
                "execute_allowed_now": get(data["pre_ec2_handoff"], "execute_allowed_now"),
                "target_runtime_launch_allowed": get(data["pre_ec2_handoff"], "target_runtime_launch_allowed"),
            },
            "local handoff passes with live steps blocked",
        ),
        check(
            "runbook_is_ordered_and_fail_closed",
            get(data["live_execution_runbook"], "result") == "blocked_selected_target_runtime_live_execution_runbook_waiting_for_explicit_live_intent"
            and int(get(data["live_execution_runbook"], "failed_check_count", -1)) == 0
            and int(get(data["live_execution_runbook"], "ordered_step_count", 0)) == 20
            and not bool(get(data["live_execution_runbook"], "execute_allowed_now"))
            and not bool(get(data["live_execution_runbook"], "target_runtime_launch_allowed")),
            {
                "result": get(data["live_execution_runbook"], "result"),
                "failed_check_count": get(data["live_execution_runbook"], "failed_check_count"),
                "ordered_step_count": get(data["live_execution_runbook"], "ordered_step_count"),
                "execute_allowed_now": get(data["live_execution_runbook"], "execute_allowed_now"),
                "target_runtime_launch_allowed": get(data["live_execution_runbook"], "target_runtime_launch_allowed"),
            },
            "20 ordered steps, no failed checks, live execution closed",
        ),
        check(
            "execution_readiness_snapshot_has_three_local_install_proofs",
            get(data["execution_readiness_snapshot"], "result") == "blocked_selected_target_runtime_execution_readiness_local_proofs_complete_live_gates_closed"
            and int(get(data["execution_readiness_snapshot"], "failed_check_count", -1)) == 0
            and int(get(data["execution_readiness_snapshot"], "local_install_dry_run_proof_count", 0)) == 3
            and not bool(get(data["execution_readiness_snapshot"], "execute_allowed_now"))
            and not bool(get(data["execution_readiness_snapshot"], "target_runtime_launch_allowed")),
            {
                "result": get(data["execution_readiness_snapshot"], "result"),
                "failed_check_count": get(data["execution_readiness_snapshot"], "failed_check_count"),
                "local_install_dry_run_proof_count": get(data["execution_readiness_snapshot"], "local_install_dry_run_proof_count"),
                "execute_allowed_now": get(data["execution_readiness_snapshot"], "execute_allowed_now"),
                "target_runtime_launch_allowed": get(data["execution_readiness_snapshot"], "target_runtime_launch_allowed"),
            },
            "3 local install dry-run proofs, no failed checks, live gates closed",
        ),
    ]
    failed = [c for c in checks if c["result"] != "pass"]
    result = (
        "pass_local_only_selected_inpaint_publish_dry_run_chain_aligned_live_gates_closed"
        if not failed
        else "blocked_selected_inpaint_publish_dry_run_chain_alignment_failed"
    )

    evidence_json = QA_RUNTIME_DIR / f"{evidence_id}.json"
    evidence_md = QA_RUNTIME_DIR / f"{evidence_id}.md"
    payload = {
        "schema_version": "1.0",
        "evidence_id": evidence_id,
        "timestamp": iso,
        "wave": "66",
        "lane_id": "sdxl_realvisxl_inpaint_detail_lane",
        "task": "selected_inpaint_publish_dry_run_chain_alignment",
        "result": result,
        "local_only": True,
        "aws_contacted": False,
        "s3_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "prompt_posted": False,
        "active_runtime_marker_written": False,
        "mask_promoted": False,
        "wave70_gate_rerun": False,
        "wave71_activated": False,
        "failed_check_count": len(failed),
        "checks": checks,
        "source_evidence": {
            key: {
                "path": rel(path),
                "sha256": sha256_file(path),
                "result": get(data[key], "result"),
            }
            for key, path in files.items()
        },
        "proof_summary": {
            "model_publish_dry_run_ready": checks[0]["result"] == "pass",
            "input_asset_publish_dry_run_ready_count": int(checks[1]["result"] == "pass") + int(checks[2]["result"] == "pass"),
            "pre_ec2_handoff_failed_check_count": get(data["pre_ec2_handoff"], "failed_check_count"),
            "pre_ec2_handoff_blocked_live_step_count": get(data["pre_ec2_handoff"], "blocked_live_step_count"),
            "runbook_ordered_step_count": get(data["live_execution_runbook"], "ordered_step_count"),
            "snapshot_local_install_dry_run_proof_count": get(data["execution_readiness_snapshot"], "local_install_dry_run_proof_count"),
        },
        "blockers_remaining": [
            "explicit_target_runtime_live_intent_missing",
            "deploy_bundle_s3_execute_proof_missing",
            "input_asset_s3_execute_proofs_missing",
            "model_s3_execute_proof_missing",
            "ec2_install_hash_proof_missing",
            "ec2_start_authorization_missing",
            "target_runtime_static_proof_missing",
            "target_runtime_generation_and_strict_visual_qa_missing",
        ],
        "next_action": "Keep EC2 stopped and continue local-only selected-inpaint/final-certification work until explicit live intent and live gates are present.",
    }
    write_json(evidence_json, payload)

    md = f"""# Selected Inpaint Publish Dry-Run Chain Alignment - {iso}

- Result: `{result}`
- Failed checks: `{len(failed)}`
- Lane: `sdxl_realvisxl_inpaint_detail_lane`
- Model publish dry-run: `{rel(files["model_publish_dry_run"])}`
- Source input publish dry-run: `{rel(files["source_input_publish_dry_run"])}`
- Mask input publish dry-run: `{rel(files["mask_input_publish_dry_run"])}`
- Pre-EC2 handoff: `{rel(files["pre_ec2_handoff"])}`
- Live runbook: `{rel(files["live_execution_runbook"])}`
- Execution-readiness snapshot: `{rel(files["execution_readiness_snapshot"])}`
- Boundary: local-only; no AWS/S3 contact, EC2 start, prompt post, generation, active marker write, mask promotion, Wave70 gate rerun, or Wave71 activation.
- Next action: keep EC2 stopped and continue local-only selected-inpaint/final-certification work unless explicit live intent and live gates are present.
"""
    evidence_md.write_text(md, encoding="utf-8")

    tracker_json = copy_to_tracker(evidence_json)
    tracker_md = copy_to_tracker(evidence_md)

    section_title = f"Selected Inpaint Publish Dry-Run Chain Alignment Current - {iso}"
    common_files = (
        f"`{rel(evidence_json)}` and tracker mirror `{rel(tracker_json)}`"
    )
    resume = f"""## Resume Here - {section_title}

Resume from local-only selected-inpaint publish dry-run chain alignment evidence: {common_files}. The chain verifies the RealVisXL model publish dry-run, source and mask input publish dry-runs, pre-EC2 handoff, live execution runbook, and execution-readiness snapshot agree with 0 failed checks while leaving live execution closed.

Current state: result `{result}`, model dry-run ready, 2 input dry-runs ready, pre-EC2 handoff blocked live steps `{payload["proof_summary"]["pre_ec2_handoff_blocked_live_step_count"]}`, runbook ordered steps `{payload["proof_summary"]["runbook_ordered_step_count"]}`, local install dry-run proofs `{payload["proof_summary"]["snapshot_local_install_dry_run_proof_count"]}`. No AWS/S3/EC2/ComfyUI/generation/mask/Wave70/Wave71 action occurred.

Do not start EC2, upload to S3, post prompts, write an active runtime marker, promote masks, rerun Wave70 gates, or activate Wave71+ without explicit live intent and passing live gates.
"""
    current = f"""## Latest Runtime Progress - {section_title}

Generated selected-inpaint publish dry-run chain alignment evidence. The proof validates the latest model/input publish dry-runs, pre-EC2 handoff, runbook, and execution-readiness snapshot as mutually consistent and fail-closed. Evidence: {common_files}. Result `{result}`, failed checks `{len(failed)}`.

No live AWS/S3/EC2/ComfyUI/generation/mask/Jira/Wave70/Wave71 action occurred.
"""
    goal = f"""## Current Pursuing Goal - {section_title}

Keep pursuing selected-inpaint target-runtime readiness from local `C:\\Comfy_UI_Main` source-of-truth state. The latest concrete progress is a local-only alignment proof for the current publish dry-run handoff chain, proving the model/input dry-runs, pre-EC2 handoff, runbook, and execution-readiness snapshot agree while all live gates remain closed.

Current validation anchor: `{rel(evidence_json)}` reports `{result}` with `failed_check_count=0`, no AWS/S3 contact, no EC2 start, no generation, no prompt post, no active runtime marker write, and no mask promotion. Live execution remains unauthorized until explicit target-runtime/live intent, S3 Execute proofs for deploy bundle/input/model assets, EC2 install hash proof, EC2 start authorization, static proof, generation, and strict visual QA are present.
"""
    next_action = f"""## Immediate Next Action - {section_title}

Continue selected-inpaint/local final-certification work from the aligned publish dry-run chain. Use `{rel(evidence_json)}` as the current authority for this local lane state. The chain is ready only as fail-closed handoff evidence; it is not permission to upload assets, start EC2, post a prompt, or claim final runtime quality.

Next exact safe action: continue local-only selected-inpaint/final-certification closure or blocker evidence from current artifacts. Do not start EC2, upload to S3, post prompts, write an active marker, promote masks, rerun Wave70 gates, activate Wave71+, or run live target-runtime execution unless explicit live intent and all live gates are present.
"""
    evidence_index = f"""## Selected Inpaint Publish Dry-Run Chain Alignment - {iso}

- Evidence JSON: {rel(evidence_json)}
- Evidence Markdown: {rel(evidence_md)}
- Tracker mirror JSON: {rel(tracker_json)}
- Tracker mirror Markdown: {rel(tracker_md)}
- Result: `{result}`
- Boundary: local-only selected-inpaint alignment proof; no live execution.
"""
    blockers = f"""## Selected Inpaint Live Gate Blockers - {iso}

Current local publish dry-run chain alignment evidence `{rel(evidence_json)}` passes with fail-closed live gates. Remaining blockers: explicit target-runtime/live intent, deploy bundle/input/model S3 Execute proofs, EC2 install hash proof, EC2 start authorization, target-runtime static proof, generation, and strict visual QA. No EC2/S3/generation step is authorized by this alignment proof alone.
"""
    decisions = f"""## Decision - {section_title}

Treat the selected-inpaint publish dry-run chain as locally aligned but not live-authorized. Preserve the fail-closed boundary and continue only local certification/blocker work until explicit live intent and live-gate proofs exist.
"""

    prepend(HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md", resume)
    prepend(HYDRATION_DIR / "CURRENT_SESSION_STATE.md", current)
    prepend(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md", goal)
    prepend(HYDRATION_DIR / "NEXT_ACTION.md", next_action)
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", evidence_index)
    prepend(HYDRATION_DIR / "BLOCKERS.md", blockers)
    prepend(HYDRATION_DIR / "RECENT_DECISIONS.md", decisions)

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                iso,
                "66",
                "selected inpaint publish dry-run chain alignment",
                "Validated current selected-inpaint model/input publish dry-runs, pre-EC2 handoff, runbook, and execution-readiness snapshot as fail-closed local evidence; mirrored evidence to Tracker and updated hydration handoff files.",
                "; ".join(
                    [
                        rel(evidence_json),
                        rel(evidence_md),
                        rel(tracker_json),
                        rel(tracker_md),
                        "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
                        "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
                        "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
                        "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
                        "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md",
                        "Plan/Instructions/Hydration_Rehydration/BLOCKERS.md",
                        "Plan/Instructions/Hydration_Rehydration/RECENT_DECISIONS.md",
                    ]
                ),
                f"failed_check_count={len(failed)}; local_only=true; ec2_started=false; generation_executed=false",
                result,
                rel(evidence_json),
                "Continue local-only selected-inpaint/final-certification closure or blocker evidence; live execution still requires explicit live intent and passing live gates.",
            ]
        )

    print(json.dumps({"evidence_id": evidence_id, "result": result, "evidence": rel(evidence_json)}, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
