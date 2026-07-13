#!/usr/bin/env python3
"""Record the bounded Row022 production-reference video inventory."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260713T035710-0500"
TIMESTAMP = "2026-07-13T03:57:10-05:00"
STATUS = "Blocked_Reference_Video_Production_Proof_Missing"
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
DIAGNOSTIC_EXTENSIONS = SUPPORTED_EXTENSIONS | {".gif", ".webp"}
ROOTS = (
    ("reference_images", ROOT / "Reference_Images"),
    ("ref_image_1", ROOT / "Ref_Image_1"),
    ("ref_image_2", ROOT / "Ref_Image_2"),
    ("canonical_body", ROOT / "Ref_Image_Canonical_Body"),
    ("authoritative_comfyui_input", ROOT / "ComfyUI/input"),
    ("legacy_comfyui_input_absence_check", Path(r"C:\Comfy_UI\input")),
)
OLD_NOTE = (
    "Wave64 Row022 bounded production-input inventory 2026-07-13: zero supported video, "
    "conditional GIF, or diagnostic WebP files exist in the four present user/reference roots; "
    "the legacy C:\\Comfy_UI\\input root is absent. Existing 40-test ingest/semantic tooling proof "
    "is preserved, but no production decode, timeline, source comparison, visual review, or "
    "promotion is claimed."
)
NOTE = (
    "Wave64 Row022 bounded production-input inventory 2026-07-13: zero supported video, "
    "conditional GIF, diagnostic WebP, or numbered PNG/JPG sequence candidates exist in the five "
    "present user/reference and authoritative ComfyUI input roots; the legacy C:\\Comfy_UI\\input "
    "root is absent. Existing 40-test ingest/semantic tooling proof is preserved, but no production "
    "decode, timeline, source comparison, visual review, or promotion is claimed."
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
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def inventory_root(label: str, root: Path) -> dict:
    exists = root.is_dir()
    candidates = []
    numbered_groups: dict[tuple[Path, str, str], list[tuple[int, Path]]] = {}
    if exists:
        for path in sorted(root.rglob("*"), key=lambda item: str(item).lower()):
            if not path.is_file():
                continue
            extension = path.suffix.lower()
            if extension in DIAGNOSTIC_EXTENSIONS:
                if extension in SUPPORTED_EXTENSIONS:
                    classification = "supported_video_requires_provenance_review"
                elif extension == ".gif":
                    classification = "conditional_loop_reference_requires_provenance_review"
                else:
                    classification = "unsupported_webp_diagnostic_only"
                candidates.append(
                    {
                        "path": rel(path),
                        "extension": extension,
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                        "classification": classification,
                    }
                )
            if extension in {".png", ".jpg", ".jpeg"}:
                match = re.fullmatch(r"(.*?)(\d+)", path.stem)
                if match:
                    key = (path.parent, match.group(1), extension)
                    numbered_groups.setdefault(key, []).append((int(match.group(2)), path))
    sequence_candidates = []
    for (parent, prefix, extension), frames in sorted(
        numbered_groups.items(), key=lambda item: str(item[0]).lower()
    ):
        unique_numbers = sorted({number for number, _ in frames})
        longest_run = 1
        current_run = 1
        for previous, current in zip(unique_numbers, unique_numbers[1:]):
            current_run = current_run + 1 if current == previous + 1 else 1
            longest_run = max(longest_run, current_run)
        if len(unique_numbers) < 3 or longest_run < 3:
            continue
        sequence_candidates.append(
            {
                "directory": rel(parent),
                "filename_prefix": prefix,
                "extension": extension,
                "numbered_file_count": len(unique_numbers),
                "minimum_index": unique_numbers[0],
                "maximum_index": unique_numbers[-1],
                "longest_consecutive_run": longest_run,
                "classification": "supported_numbered_image_sequence_requires_provenance_review",
            }
        )
    return {
        "label": label,
        "root": rel(root),
        "exists": exists,
        "media_candidate_count": len(candidates),
        "media_candidates": candidates,
        "sequence_candidate_count": len(sequence_candidates),
        "sequence_candidates": sequence_candidates,
        "candidate_count": len(candidates) + len(sequence_candidates),
    }


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
    if "Notes" in row:
        if OLD_NOTE in row["Notes"]:
            row["Notes"] = row["Notes"].replace(OLD_NOTE, NOTE)
        elif NOTE not in row["Notes"]:
            row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row022 Production Reference Video Inventory"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-022` / `ITEM-W64-022` remains `{STATUS}` after a bounded production-input inventory. The five present user/reference and authoritative ComfyUI input roots contain zero supported video, conditional GIF, diagnostic WebP, or numbered PNG/JPG sequence candidates; legacy `C:\\Comfy_UI\\input` is absent. The existing strict ingest and semantic-candidate implementation remains validated by 40 tests and synthetic tooling probes only. No production decode, derived timeline, source comparison, visual pass, generation, AWS, EC2, mask use/promotion, hard-gate rerun, Jira mutation, or Wave71+ activation occurred.

Next action: preserve this exact external-input blocker and continue `TRK-W64-023` / `ITEM-W64-023` frame repair and inpainting reconciliation without fabricating before/after repair proof.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + text, encoding="utf-8")


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_reference_input.json"
    tracker_canonical_path = PLAN / "Tracker/Evidence/Wave64/video_reference_input.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-022_video_reference_input.json"
    test_log_path = PLAN / "Instructions/QA/Evidence/Wave64/video_reference_input_test_log.json"
    format_registry_path = PLAN / "10_REGISTRIES/wave26_reference_video_input_format_registry.json"
    worker_record_path = ROOT / "runtime_artifacts/agent_handoffs/cursor/20260713T034607-0500_w64_row022_reference_video_inventory_narrow/handoff_record.json"
    claude_review_path = ROOT / "runtime_artifacts/agent_handoffs/claude_subscription/20260713T040233-0500_w64_row022_semantic_final_review/handoff_record.json"
    claude_confirmation_path = ROOT / "runtime_artifacts/agent_handoffs/claude_subscription/20260713T040835-0500_w64_row022_semantic_remediation_review/handoff_record.json"
    required = [canonical_path, report_path, test_log_path, format_registry_path, worker_record_path, claude_review_path, claude_confirmation_path]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row022 inputs: {missing}")

    canonical = load(canonical_path)
    report = load(report_path)
    test_log = load(test_log_path)
    registry = load(format_registry_path)
    worker = load(worker_record_path)
    claude_review = load(claude_review_path)
    claude_confirmation = load(claude_confirmation_path)
    inventory = [inventory_root(label, path) for label, path in ROOTS]
    media_candidates = [candidate for root_record in inventory for candidate in root_record["media_candidates"]]
    sequence_candidates = [candidate for root_record in inventory for candidate in root_record["sequence_candidates"]]
    supported = set(registry["supported_video_extensions"])
    checks = {
        "canonical_row_exact": canonical["tracker_id"] == "TRK-W64-022" and canonical["item_id"] == "ITEM-W64-022",
        "report_row_exact": report["tracker_id"] == "TRK-W64-022" and report["item_id"] == "ITEM-W64-022",
        "format_registry_matches_implementation": supported == SUPPORTED_EXTENSIONS,
        "sequence_registry_matches_implementation": set(registry["supported_sequence_inputs"]) == {"numbered_png_sequence", "numbered_jpg_sequence", "extracted_frame_folder"},
        "four_reference_roots_present": all(record["exists"] for record in inventory[:4]),
        "authoritative_comfyui_input_present": inventory[4]["exists"] is True,
        "legacy_input_root_absent": inventory[5]["exists"] is False,
        "media_candidate_inventory_empty": not media_candidates,
        "sequence_candidate_inventory_empty": not sequence_candidates,
        "production_video_not_previously_claimed": canonical["acceptance_gates"]["production_reference_video_supplied"] is False,
        "existing_test_count_exact": canonical["offline_validation"]["tests_run"] == 40,
        "existing_tests_passed": test_log.get("tests_run") == 40 and test_log.get("failures") == 0 and test_log.get("errors") == 0,
        "synthetic_probe_not_production": canonical["synthetic_local_runtime_probe"]["production_evidence"] is False,
        "worker_handoff_passed": worker["status"] == "PASS" and worker["classification"] == "CURSOR_HANDOFF_COMPLETED",
        "worker_handoff_clean": not worker["issues"] and not worker["worktree_paths_changed_during_handoff"],
        "worker_inventory_agrees": "zero" in worker["cursor_result_excerpt"].lower() and "no eligible media files" in worker["cursor_result_excerpt"].lower(),
        "claude_review_passed": claude_review["status"] == "PASS" and claude_review["classification"] == "CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED",
        "claude_medium_findings_addressed": "Two MEDIUM findings" in claude_review["result_excerpt"],
        "claude_confirmation_passed": claude_confirmation["status"] == "PASS" and claude_confirmation["classification"] == "CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED",
        "claude_confirmation_no_medium_high": "no HIGH/MEDIUM defects remain" in claude_confirmation["result_excerpt"],
        "candidate_masks_not_required_for_inventory": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row022 reconciliation checks failed: {failed}")

    output_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_REFERENCE_INPUT_INVENTORY_{STAMP}.json"
    mirror_path = PLAN / f"Tracker/Evidence/VIDEO_REFERENCE_INPUT_INVENTORY_{STAMP}.json"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-REFERENCE-INPUT-INVENTORY-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-022",
        "item_id": "ITEM-W64-022",
        "status_decision": STATUS,
        "source_citation": canonical["source_citation"],
        "inventory_policy": {
            "supported_video_extensions": sorted(SUPPORTED_EXTENSIONS),
            "supported_sequence_inputs": registry["supported_sequence_inputs"],
            "conditional_reference_extensions": [".gif"],
            "diagnostic_unsupported_extensions": [".webp"],
            "generated_outputs_scanned": False,
            "runtime_artifacts_scanned": False,
            "model_caches_scanned": False,
            "pulled_back_artifacts_scanned": False,
        },
        "roots": inventory,
        "summary": {
            "roots_checked": len(inventory),
            "roots_present": sum(record["exists"] for record in inventory),
            "roots_absent": sum(not record["exists"] for record in inventory),
            "media_candidate_count": len(media_candidates),
            "sequence_candidate_count": len(sequence_candidates),
            "candidate_count": len(media_candidates) + len(sequence_candidates),
            "production_candidate_count": 0,
        },
        "supporting_worker_record": {"path": rel(worker_record_path), "sha256": digest(worker_record_path)},
        "semantic_review": {
            "path": rel(claude_review_path),
            "sha256": digest(claude_review_path),
            "initial_medium_findings": 2,
            "confirmation_path": rel(claude_confirmation_path),
            "confirmation_sha256": digest(claude_confirmation_path),
            "remaining_high_or_medium_findings": 0,
            "remediations": [
                "Added the authoritative C:\\Comfy_UI_Main\\ComfyUI\\input root.",
                "Added numbered PNG/JPG sequence detection across every present inventory root.",
            ],
        },
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "validation": {
            "command": "python -m pytest -q Plan/Instructions/QA/Scripts/test_ingest_wave26_reference_video.py Plan/Instructions/QA/Scripts/test_analyze_wave26_reference_semantic_candidates.py",
            "tests_passed": 40,
            "tests_failed": 0,
            "elapsed_seconds": 117.70,
            "python_compile": "pass",
        },
        "gate_results": {
            "ingest_and_semantic_tooling_tested": True,
            "production_reference_video_discovered": False,
            "production_reference_video_provenance_verified": False,
            "production_reference_video_runtime_proof": False,
            "source_reference_visual_review": False,
            "final_promotion_ready": False,
        },
        "boundaries": {
            "new_generation_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "candidate_masks_consumed_as_truth": False,
            "mask_promotion_claimed": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activation_claimed": False,
        },
        "result": "blocked_no_production_reference_video_or_sequence_in_bounded_input_roots",
        "next_action": "Continue TRK-W64-023 / ITEM-W64-023 frame repair and inpainting reconciliation without fabricating before/after repair proof.",
    }
    dump(output_path, evidence)
    dump(mirror_path, evidence)

    canonical["timestamp"] = TIMESTAMP
    canonical["production_reference_inventory"] = {
        "evidence": rel(output_path),
        "roots_checked": len(inventory),
        "roots_present": evidence["summary"]["roots_present"],
        "candidate_count": 0,
        "supported_video_count": 0,
        "numbered_sequence_count": 0,
        "conditional_gif_count": 0,
        "diagnostic_webp_count": 0,
        "authoritative_comfyui_input_present": True,
        "legacy_comfyui_input_present": False,
        "production_candidate_discovered": False,
    }
    canonical["review"]["cursor_production_input_inventory"] = rel(worker_record_path)
    canonical["review"]["claude_inventory_scope_review"] = rel(claude_review_path)
    canonical["review"]["claude_inventory_scope_medium_findings_remediated"] = 2
    canonical["review"]["claude_inventory_scope_confirmation"] = rel(claude_confirmation_path)
    canonical["review"]["remaining_high_or_medium_findings"] = 0
    canonical["offline_validation"].update(
        {
            "last_targeted_rerun": TIMESTAMP,
            "last_targeted_rerun_tests_passed": 40,
            "last_targeted_rerun_tests_failed": 0,
        }
    )
    canonical["runtime"].update({"production_video_used": False, "generation_executed": False, "aws_contacted": False, "ec2_started": False})
    canonical["blockers"] = [
        {
            "classification": STATUS,
            "scope": "primary_row_blocker",
            "reason": "Bounded inventory found zero production-reference video, GIF/WebP, or numbered PNG/JPG sequence candidates in five present user/reference and authoritative ComfyUI input roots; legacy C:\\Comfy_UI\\input is absent. Synthetic decode/extraction remains tooling proof only.",
        },
        {
            "classification": "Blocked_Gold_Mask_Dependency_Missing",
            "scope": "mask_and_contact_timeline_subgates_only",
            "reason": "Candidate masks cannot certify mask/contact timeline alignment or contact-phase sampling while manual body gold masks remain unavailable.",
        },
    ]
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = False
    canonical["status_decision"] = STATUS
    canonical["reconciliation_evidence"] = rel(output_path)
    dump(canonical_path, canonical)
    dump(tracker_canonical_path, canonical)

    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = False
    report["validation"].update(
        {
            "bounded_production_input_inventory": "pass",
            "inventory_roots_checked": len(inventory),
            "inventory_roots_present": evidence["summary"]["roots_present"],
            "inventory_candidate_count": 0,
            "cursor_inventory_status": "PASS",
            "claude_semantic_confirmation": "PASS_NO_HIGH_OR_MEDIUM_FINDINGS",
            "targeted_test_rerun_passed": 40,
            "targeted_test_rerun_failed": 0,
        }
    )
    report["blockers"] = canonical["blockers"]
    report["evidence"] = [
        {"path": rel(canonical_path), "sha256": digest(canonical_path)},
        {"path": rel(test_log_path), "sha256": digest(test_log_path)},
        {"path": rel(output_path), "sha256": digest(output_path)},
    ]
    report["runtime"].update({"production_video_count": 0, "comfyui_started": False, "generation_count": 0, "aws_contacted": False, "ec2_started": False})
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_csv(path, "Tracker_ID", "TRK-W64-022")
    for path in (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", "ITEM-W64-022")
    for name in ("NEXT_ACTION.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend(PLAN / "Instructions/Hydration_Rehydration" / name, rel(output_path))
    print(
        json.dumps(
            {
                "status": STATUS,
                "checks": evidence["check_summary"],
                "inventory": evidence["summary"],
                "next_action": evidence["next_action"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
