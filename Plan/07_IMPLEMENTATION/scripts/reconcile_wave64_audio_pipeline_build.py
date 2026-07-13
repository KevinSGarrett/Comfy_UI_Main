#!/usr/bin/env python3
"""Record the bounded Row025 genuine-audio input inventory."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260713T051004-0500"
TIMESTAMP = "2026-07-13T05:10:04-05:00"
STATUS = "Blocked_Audio_Production_Runtime_Proof_Missing"
EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".aiff", ".aif"}
ROOTS = (
    ("authoritative_comfyui_input", ROOT / "ComfyUI/input"),
    ("pulled_back_runtime_artifacts", PLAN / "Instructions/Operations/Pulled_Back_Artifacts"),
)
NOTE = (
    "Wave64 Row025 bounded genuine-audio inventory 2026-07-13: the authoritative ComfyUI input "
    "and pulled-back artifact roots contain zero supported audio files. Existing 21-test pipeline "
    "and synthetic PCM proof remain valid, but no genuine engine runtime, playback review, or "
    "certification-loudness claim is made."
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def worker_timeout_detail(record: dict) -> str:
    issues = record.get("issues") or []
    if isinstance(issues, str):
        issues = [issues]
    timeout_issues = [str(issue) for issue in issues if "timed out after" in str(issue).lower()]
    if record.get("status") != "FAIL" or record.get("classification") != "CURSOR_HANDOFF_WRAPPER_FAILED" or len(timeout_issues) != 1:
        raise ValueError("Expected one explicit Cursor wrapper timeout issue")
    return timeout_issues[0]


def inventory(label: str, root: Path) -> dict:
    exists = root.is_dir()
    candidates = []
    if exists:
        for path in sorted(root.rglob("*"), key=lambda item: str(item).lower()):
            if path.is_file() and path.suffix.lower() in EXTENSIONS:
                candidates.append({"path": rel(path), "extension": path.suffix.lower(), "bytes": path.stat().st_size, "sha256": digest(path)})
    return {"label": label, "root": rel(root), "exists": exists, "candidate_count": len(candidates), "candidates": candidates}


def update_csv(path: Path, id_field: str, row_id: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    matched = [row for row in rows if row.get(id_field) == row_id]
    if len(matched) != 1:
        raise ValueError(f"Expected one {row_id} row in {path}, found {len(matched)}")
    row = matched[0]
    row["Status"] = STATUS
    if "Status_Decision" in row:
        row["Status_Decision"] = STATUS
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row025 Genuine Audio Input Inventory"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-025` / `ITEM-W64-025` remains `{STATUS}` after a bounded local inventory. The authoritative `ComfyUI/input` and pulled-back runtime-artifact roots both exist and contain zero WAV/MP3/FLAC/OGG/M4A/AAC/Opus/AIFF candidates. The existing strict Wave30 implementation, deterministic PCM mixer, 21-test suite, and synthetic technical probes remain preserved; they are not promoted into genuine audio-engine runtime proof. No audio generation, playback review, ComfyUI start, AWS, EC2, mask use/promotion, Jira mutation, or Wave71+ activation occurred.

Next action: preserve this exact external-runtime blocker and continue `TRK-W64-026` / `ITEM-W64-026` audio-engine routing reconciliation without fabricating engine availability or license proof.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + text, encoding="utf-8")


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/audio_pipeline_build.json"
    tracker_canonical_path = PLAN / "Tracker/Evidence/Wave64/audio_pipeline_build.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-025_audio_pipeline_build.json"
    test_log_path = PLAN / "Instructions/QA/Evidence/Wave64/audio_pipeline_build_test_log.json"
    broad_worker_path = ROOT / "runtime_artifacts/agent_handoffs/cursor/20260713T050045-0500_w64_row025_audio_candidate_inventory/handoff_record.json"
    narrow_worker_path = ROOT / "runtime_artifacts/agent_handoffs/cursor/20260713T050602-0500_w64_row025_audio_candidate_inventory_narrow/handoff_record.json"
    semantic_review_path = ROOT / "runtime_artifacts/agent_handoffs/claude_subscription/20260713T051823-0500_w64_row025_semantic_remediation_review/handoff_record.json"
    required = [canonical_path, report_path, test_log_path, broad_worker_path, narrow_worker_path, semantic_review_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row025 inputs: {missing}")

    canonical = load(canonical_path)
    report = load(report_path)
    test_log = load(test_log_path)
    broad_worker = load(broad_worker_path)
    narrow_worker = load(narrow_worker_path)
    semantic_review = load(semantic_review_path)
    broad_timeout_detail = worker_timeout_detail(broad_worker)
    narrow_timeout_detail = worker_timeout_detail(narrow_worker)
    semantic_review_excerpt = semantic_review.get("result_excerpt", "").lower()
    roots = [inventory(label, path) for label, path in ROOTS]
    candidates = [item for root_record in roots for item in root_record["candidates"]]
    checks = {
        "canonical_row_exact": canonical["tracker_id"] == "TRK-W64-025" and canonical["item_id"] == "ITEM-W64-025",
        "report_row_exact": report["tracker_id"] == "TRK-W64-025" and report["item_id"] == "ITEM-W64-025",
        "inventory_roots_present": all(item["exists"] for item in roots),
        "candidate_inventory_empty": not candidates,
        "existing_tests_passed": test_log["tests_run"] == 21 and test_log["failures"] == 0 and test_log["errors"] == 0,
        "synthetic_probe_not_production": canonical["synthetic_technical_probe"]["production_evidence"] is False,
        "synthetic_mix_not_production": canonical["synthetic_deterministic_mix_probe"]["production_evidence"] is False,
        "production_runtime_not_previously_claimed": canonical["strict_decision"]["production_runtime_claimed"] is False,
        "broad_worker_timeout_recorded": "timed out after 300 seconds" in broad_timeout_detail.lower(),
        "narrow_worker_timeout_recorded": "timed out after 180 seconds" in narrow_timeout_detail.lower(),
        "semantic_review_completed": semantic_review.get("status") == "PASS" and semantic_review.get("classification") == "CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED",
        "semantic_review_no_wrapper_issues": not semantic_review.get("issues"),
        "semantic_review_no_high_findings": "high findings: none" in semantic_review_excerpt,
        "semantic_review_no_medium_findings": "medium findings: none" in semantic_review_excerpt,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row025 reconciliation checks failed: {failed}")

    output_path = PLAN / f"Instructions/QA/Evidence/Wave64/AUDIO_PIPELINE_RUNTIME_INPUT_INVENTORY_{STAMP}.json"
    mirror_path = PLAN / f"Tracker/Evidence/AUDIO_PIPELINE_RUNTIME_INPUT_INVENTORY_{STAMP}.json"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-AUDIO-PIPELINE-RUNTIME-INPUT-INVENTORY-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-025",
        "item_id": "ITEM-W64-025",
        "status_decision": STATUS,
        "extensions": sorted(EXTENSIONS),
        "roots": roots,
        "summary": {"roots_checked": 2, "roots_present": 2, "candidate_count": 0, "genuine_runtime_candidate_count": 0},
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "validation": {"command": "python -m unittest Plan.Instructions.QA.Scripts.test_build_wave30_deterministic_audio_mix Plan.Instructions.QA.Scripts.test_wave30_audio_pipeline_strict", "tests_passed": 21, "tests_failed": 0, "elapsed_seconds": 52.021, "python_compile": "pass"},
        "worker_fallback": {
            "broad_attempt": rel(broad_worker_path),
            "broad_status": broad_worker["status"],
            "broad_classification": broad_worker["classification"],
            "broad_timeout_detail": broad_timeout_detail,
            "narrow_attempt": rel(narrow_worker_path),
            "narrow_status": narrow_worker["status"],
            "narrow_classification": narrow_worker["classification"],
            "narrow_timeout_detail": narrow_timeout_detail,
            "fallback_scope": "two exact roots and nine audio extensions",
        },
        "semantic_review": {
            "handoff_record": rel(semantic_review_path),
            "status": semantic_review["status"],
            "classification": semantic_review["classification"],
            "high_findings": "none",
            "medium_findings": "none",
        },
        "gate_results": {"pipeline_implementation_tested": True, "genuine_audio_candidate_present": False, "genuine_audio_engine_runtime_proof": False, "genuine_audio_playback_review": False, "certification_loudness_authority": False, "final_audio_certification": False},
        "boundaries": {"audio_generation_executed": False, "comfyui_started": False, "aws_contacted": False, "ec2_started": False, "candidate_masks_consumed_as_truth": False, "wave71_activation_claimed": False},
        "result": "blocked_no_genuine_audio_runtime_input_in_bounded_roots",
        "next_action": "Continue TRK-W64-026 / ITEM-W64-026 audio-engine routing reconciliation without fabricating engine availability or license proof."
    }
    dump(output_path, evidence)
    dump(mirror_path, evidence)

    canonical["timestamp"] = TIMESTAMP
    canonical["production_audio_inventory"] = {"evidence": rel(output_path), "roots_checked": 2, "candidate_count": 0, "genuine_runtime_candidate_present": False}
    canonical["review"].update({"cursor_audio_inventory_attempt": rel(broad_worker_path), "cursor_audio_inventory_retry": rel(narrow_worker_path), "audio_inventory_fallback": "compact_bounded_codex_inventory_after_two_timeouts", "semantic_review": rel(semantic_review_path), "semantic_review_status": "pass_no_high_or_medium_findings"})
    canonical["offline_validation"].update({"last_targeted_rerun": TIMESTAMP, "last_targeted_rerun_tests_passed": 21, "last_targeted_rerun_tests_failed": 0})
    canonical["blockers"][0]["reason"] = "Bounded inventory found zero genuine audio candidates in authoritative ComfyUI input and pulled-back runtime-artifact roots; retained PCM WAVs are synthetic fixtures only."
    canonical["result"] = evidence["result"]
    canonical["reconciliation_evidence"] = rel(output_path)
    dump(canonical_path, canonical)
    dump(tracker_canonical_path, canonical)

    report["timestamp"] = TIMESTAMP
    report["validation"].update({"bounded_genuine_audio_inventory": "pass", "inventory_roots_checked": 2, "inventory_candidate_count": 0, "targeted_test_rerun_passed": 21, "targeted_test_rerun_failed": 0, "semantic_review": "pass_no_high_or_medium_findings"})
    report["blockers"] = canonical["blockers"]
    report["evidence"] = [{"path": rel(canonical_path), "sha256": digest(canonical_path)}, {"path": rel(test_log_path), "sha256": digest(test_log_path)}, {"path": rel(output_path), "sha256": digest(output_path)}]
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
        update_csv(path, "Tracker_ID", "TRK-W64-025")
    for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
        update_csv(path, "Item_ID", "ITEM-W64-025")
    for name in ("NEXT_ACTION.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend(PLAN / "Instructions/Hydration_Rehydration" / name, rel(output_path))
    print(json.dumps({"status": STATUS, "checks": evidence["check_summary"], "summary": evidence["summary"], "next_action": evidence["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
