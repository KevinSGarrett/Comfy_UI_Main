from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_ROOT = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence"
QA_RUNTIME_DIR = QA_ROOT / "Runtime_Readiness"
QA_DONE_DIR = QA_ROOT / "Done_Certifications"
TRACKER_DONE_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence" / "Done_Certifications"
HYDRATION_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "Hydration_Rehydration"


def now_stamp() -> tuple[str, str]:
    now = datetime.now().astimezone()
    return now.strftime("%Y%m%dT%H%M%S%z"), now.isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def latest(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    return matches[0] if matches else None


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


def get(data: dict[str, Any] | None, dotted: str, default: Any = None) -> Any:
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


def git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "status", "--short"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return [f"git_status_failed:{proc.stderr.strip() or proc.stdout.strip()}"]
    return [line for line in proc.stdout.splitlines() if line.strip()]


def copy_to_tracker(path: Path) -> Path:
    target = TRACKER_DONE_DIR / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return target


def prepend(path: Path, section: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(section.rstrip() + "\n\n" + old.lstrip("\ufeff"), encoding="utf-8")


def main() -> int:
    stamp, iso = now_stamp()
    evidence_id = f"W66_SELECTED_INPAINT_FINAL_CERTIFICATION_BLOCKER_AFTER_CHAIN_ALIGNMENT_{stamp}"

    alignment_path = latest(QA_RUNTIME_DIR, "W66_SELECTED_INPAINT_PUBLISH_DRY_RUN_CHAIN_ALIGNMENT_*.json")
    if alignment_path is None:
        raise FileNotFoundError("Missing selected-inpaint publish dry-run chain alignment evidence.")
    alignment = read_json(alignment_path)

    work_order_path = latest(QA_DONE_DIR, "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json")
    if work_order_path is None:
        work_order_path = latest(QA_RUNTIME_DIR, "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json")
    closure_path = latest(QA_RUNTIME_DIR, "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_*.json")
    coverage_path = latest(QA_RUNTIME_DIR, "W66_ACTIVE_RUNTIME_QUEUE_FINAL_REVIEW_EVIDENCE_COVERAGE_*.json")
    inpaint_blocker_path = latest(QA_DONE_DIR, "W66_INPAINT_LANE_FINAL_REVIEW_BLOCKER_PACKET_*.json")

    work_order = read_json(work_order_path) if work_order_path else None
    closure = read_json(closure_path) if closure_path else None
    coverage = read_json(coverage_path) if coverage_path else None
    inpaint_blocker = read_json(inpaint_blocker_path) if inpaint_blocker_path else None

    status_lines = git_status()
    dirty_paths = [line[3:] if len(line) > 3 else line for line in status_lines]
    alignment_mtime = alignment_path.stat().st_mtime

    final_review_sources = {
        "work_order": rel(work_order_path) if work_order_path else None,
        "closure_rollup": rel(closure_path) if closure_path else None,
        "evidence_coverage": rel(coverage_path) if coverage_path else None,
        "inpaint_blocker_packet": rel(inpaint_blocker_path) if inpaint_blocker_path else None,
    }
    stale_sources = []
    for label, path in {
        "work_order": work_order_path,
        "closure_rollup": closure_path,
        "evidence_coverage": coverage_path,
        "inpaint_blocker_packet": inpaint_blocker_path,
    }.items():
        if path is None:
            stale_sources.append(f"{label}:missing")
        elif path.stat().st_mtime < alignment_mtime:
            stale_sources.append(f"{label}:older_than_chain_alignment")

    checks = [
        check(
            "chain_alignment_is_current_local_pass",
            get(alignment, "result") == "pass_local_only_selected_inpaint_publish_dry_run_chain_aligned_live_gates_closed"
            and int(get(alignment, "failed_check_count", -1)) == 0
            and bool(get(alignment, "local_only"))
            and not bool(get(alignment, "ec2_started"))
            and not bool(get(alignment, "generation_executed")),
            {
                "result": get(alignment, "result"),
                "failed_check_count": get(alignment, "failed_check_count"),
                "local_only": get(alignment, "local_only"),
                "ec2_started": get(alignment, "ec2_started"),
                "generation_executed": get(alignment, "generation_executed"),
            },
            "aligned local pass, no EC2/generation",
        ),
        check(
            "current_worktree_is_not_clean_for_final_or_live_gate",
            len(status_lines) > 0,
            {"changed_path_count": len(status_lines), "sample": status_lines[:12]},
            "dirty worktree must block live/final certification",
        ),
        check(
            "existing_final_review_sources_need_post_alignment_refresh",
            len(stale_sources) > 0,
            stale_sources,
            "at least one final-review source is missing or older than the chain alignment, so final closure must be refreshed before any claim",
        ),
        check(
            "no_target_runtime_generation_or_strict_visual_qa_present",
            "target_runtime_generation_and_strict_visual_qa_missing" in list(get(alignment, "blockers_remaining", [])),
            get(alignment, "blockers_remaining", []),
            "target-runtime generation and strict visual QA remain missing",
        ),
    ]
    failed = [row for row in checks if row["result"] != "pass"]

    result = (
        "blocked_selected_inpaint_final_certification_after_chain_alignment"
        if not failed
        else "invalid_selected_inpaint_final_certification_blocker_inputs"
    )
    evidence_json = QA_DONE_DIR / f"{evidence_id}.json"
    evidence_md = QA_DONE_DIR / f"{evidence_id}.md"

    payload = {
        "schema_version": "1.0",
        "artifact_type": "selected_inpaint_final_certification_blocker_packet",
        "evidence_id": evidence_id,
        "timestamp": iso,
        "wave": "66",
        "lane_id": "sdxl_realvisxl_inpaint_detail_lane",
        "result": result,
        "final_decision": "blocked",
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
        "full_project_certification_allowed": False,
        "closes_work_order": False,
        "failed_check_count": len(failed),
        "tests_performed": checks,
        "source_evidence": {
            "chain_alignment": rel(alignment_path),
            **final_review_sources,
        },
        "current_git_state": {
            "clean_worktree": len(status_lines) == 0,
            "changed_path_count": len(status_lines),
            "changed_paths": dirty_paths,
        },
        "final_review_state": {
            "work_order_count": get(work_order, "work_order_count"),
            "open_work_order_count": get(closure, "open_work_order_count"),
            "closed_work_order_count": get(closure, "closed_work_order_count"),
            "final_review_work_order_count": get(coverage, "final_review_work_order_count"),
            "missing_review_evidence_count": get(coverage, "missing_review_evidence_count"),
            "inpaint_blocker_result": get(inpaint_blocker, "result"),
            "stale_or_missing_sources_after_alignment": stale_sources,
        },
        "exact_blockers": [
            "current_worktree_dirty_with_uncheckpointed_local_evidence",
            "post_alignment_final_certification_work_order_refresh_missing",
            "post_alignment_closure_rollup_refresh_missing",
            "target_runtime_generation_and_strict_visual_qa_missing",
            "explicit_target_runtime_live_intent_missing",
            "s3_execute_and_ec2_runtime_proofs_missing",
        ],
        "next_action": "Continue local-only final-certification closure refresh from the chain-aligned state, or explicitly satisfy live gates before any EC2/S3/generation step.",
    }
    write_json(evidence_json, payload)

    evidence_md.write_text(
        f"""# Selected Inpaint Final Certification Blocker After Chain Alignment - {iso}

- Result: `{result}`
- Failed checks: `{len(failed)}`
- Lane: `sdxl_realvisxl_inpaint_detail_lane`
- Chain alignment: `{rel(alignment_path)}`
- Changed path count: `{len(status_lines)}`
- Work order count: `{payload["final_review_state"]["work_order_count"]}`
- Open work orders: `{payload["final_review_state"]["open_work_order_count"]}`
- Stale or missing post-alignment sources: `{len(stale_sources)}`
- Boundary: local-only blocker packet; no AWS/S3 contact, EC2 start, prompt post, generation, active marker write, mask promotion, Wave70 rerun, or Wave71 activation.
- Next action: refresh local final-certification closure/work-order evidence from the aligned state, or satisfy explicit live gates before target-runtime execution.
""",
        encoding="utf-8",
    )

    tracker_json = copy_to_tracker(evidence_json)
    tracker_md = copy_to_tracker(evidence_md)

    title = f"Selected Inpaint Final Certification Blocker After Chain Alignment - {iso}"
    resume = f"""## Resume Here - {title}

Resume from local-only final-certification blocker evidence `{rel(evidence_json)}`. It consumes the current selected-inpaint publish dry-run chain alignment and the actual current Git status, then blocks final/live certification because the worktree has uncheckpointed local evidence, final-certification work-order/closure sources predate the chain alignment, and target-runtime generation plus strict visual QA are still missing.

Do not start EC2, upload to S3, post prompts, write an active runtime marker, promote masks, rerun Wave70 gates, or activate Wave71+ without explicit live intent and passing live gates.
"""
    current = f"""## Latest Runtime Progress - {title}

Generated local-only selected-inpaint final-certification blocker evidence after the chain-alignment proof. Evidence `{rel(evidence_json)}` reports `{result}`, current changed path count `{len(status_lines)}`, and exact blockers for post-alignment final-certification refresh plus missing target-runtime generation/strict visual QA. Tracker mirror: `{rel(tracker_json)}`.

No live AWS/S3/EC2/ComfyUI/generation/mask/Jira/Wave70/Wave71 action occurred.
"""
    goal = f"""## Current Pursuing Goal - {title}

Keep pursuing selected-inpaint target-runtime/final-certification readiness locally. The latest concrete progress is a blocker packet that prevents stale clean-gate or pre-alignment final-review evidence from being treated as final certification proof.

Current validation anchor: `{rel(evidence_json)}` reports `{result}` with `failed_check_count=0`, `full_project_certification_allowed=false`, `closes_work_order=false`, current dirty worktree count `{len(status_lines)}`, and live/runtime QA blockers still present.
"""
    next_action = f"""## Immediate Next Action - {title}

Continue local-only selected-inpaint/final-certification closure refresh from `{rel(evidence_json)}`. The safe next work is to refresh current final-certification work-order, closure rollup, and evidence coverage from the aligned chain while keeping live gates closed.

Do not start EC2, upload to S3, post prompts, write an active marker, promote masks, rerun Wave70 gates, activate Wave71+, or run live target-runtime execution unless explicit live intent and all live gates are present.
"""
    evidence_index = f"""## Selected Inpaint Final Certification Blocker After Chain Alignment - {iso}

- Evidence JSON: {rel(evidence_json)}
- Evidence Markdown: {rel(evidence_md)}
- Tracker mirror JSON: {rel(tracker_json)}
- Tracker mirror Markdown: {rel(tracker_md)}
- Result: `{result}`
- Boundary: local-only final-certification blocker; no live execution.
"""
    blockers = f"""## Selected Inpaint Final Certification Blocker After Chain Alignment - {iso}

Evidence `{rel(evidence_json)}` blocks final certification from the current aligned dry-run state. Exact blockers: dirty current worktree with uncheckpointed local evidence, post-alignment final-certification work-order/closure refresh missing, target-runtime generation and strict visual QA missing, explicit live intent missing, and S3/EC2 runtime proofs missing.
"""
    decisions = f"""## Decision - {title}

Do not use pre-alignment final-review closure or stale clean-gate evidence as proof of final readiness. Treat selected-inpaint final certification as blocked until the local final-certification closure is refreshed from the aligned chain and live/runtime QA evidence exists.
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
                "selected inpaint final certification blocker after chain alignment",
                "Recorded local-only final-certification blocker from the current chain alignment and actual dirty worktree; mirrored evidence to Tracker and updated hydration handoff files.",
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
                f"failed_check_count={len(failed)}; current_changed_path_count={len(status_lines)}; ec2_started=false; generation_executed=false",
                result,
                rel(evidence_json),
                "Refresh local final-certification work-order/closure evidence from the aligned chain; live execution remains gated.",
            ]
        )

    print(json.dumps({"evidence_id": evidence_id, "result": result, "evidence": rel(evidence_json)}, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
