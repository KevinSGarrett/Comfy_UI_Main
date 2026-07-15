#!/usr/bin/env python3
"""Record the one-attempt AnimateDiff result without changing Row019 status."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TRACKER_ID = "TRK-W64-019"
ITEM_ID = "ITEM-W64-019"
STATUS = "Blocked_Keyframe_And_Repair_Visual_Acceptance_Missing_Bounded_Wan_Pass"
STAMP = "20260715T140007-0500"
ARTIFACT_DIR = Path(
    f"Plan/Instructions/Operations/Pulled_Back_Artifacts/wave64_animatediff_meaningful_{STAMP}"
)
VISUAL_EVIDENCE = Path(
    f"Plan/Instructions/QA/Evidence/Image_Artifact_QA/"
    f"W64_LOCAL_ANIMATEDIFF_MEANINGFUL_SEQUENCE_VISUAL_QA_{STAMP}.json"
)
TRACKER_MIRROR = Path(
    f"Plan/Tracker/Evidence/Image_Artifact_QA/"
    f"W64_LOCAL_ANIMATEDIFF_MEANINGFUL_SEQUENCE_VISUAL_QA_{STAMP}.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_entries(current: str, additions: list[str]) -> str:
    values = [value.strip() for value in (current or "").split(";") if value.strip()]
    for addition in additions:
        if addition not in values:
            values.append(addition)
    return "; ".join(values)


def update_csv(
    path: Path, key: str, expected_id: str, evidence: list[str], tags: list[str], note: str
) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matches = 0
    for row in rows:
        if row.get(key) != expected_id:
            continue
        matches += 1
        if row.get("Status") != STATUS:
            raise ValueError(f"Refusing to replace current Row019 status in {path}: {row.get('Status')}")
        evidence_field = "Evidence_Path" if "Evidence_Path" in fields else "Evidence_Required"
        row[evidence_field] = add_entries(row.get(evidence_field, ""), evidence)
        row["Coverage_Audit_Status"] = add_entries(row.get("Coverage_Audit_Status", ""), tags)
        row["Notes"] = add_entries(row.get("Notes", ""), [note])
    if matches != 1:
        raise ValueError(f"Expected one {expected_id} row in {path}, found {matches}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return matches


def validate_evidence() -> dict[str, Any]:
    visual = ROOT / VISUAL_EVIDENCE
    mirror = ROOT / TRACKER_MIRROR
    runtime = ROOT / ARTIFACT_DIR / "runtime_technical_evidence.json"
    artifact = ROOT / ARTIFACT_DIR / "wave64_animatediff_meaningful_seed7151601_00001_.webp"
    contact = ROOT / ARTIFACT_DIR / "contact_sheet.png"
    payload = json.loads(visual.read_text(encoding="utf-8"))
    if visual.read_bytes() != mirror.read_bytes():
        raise ValueError("Visual QA and Tracker mirror differ")
    if payload["result"] != "fail_visual_black_single_frame_output":
        raise ValueError("Unexpected visual result")
    if payload["row_status_preserved"] != STATUS:
        raise ValueError("Visual evidence does not preserve current Row019 status")
    bindings = payload["source_bindings"]
    checks = {
        "visual_tracker_mirror_exact": sha256(visual) == sha256(mirror),
        "runtime_evidence_hash_bound": sha256(runtime)
        == bindings["runtime_technical_evidence"]["sha256"],
        "artifact_hash_bound": sha256(artifact) == bindings["artifact"]["sha256"],
        "contact_sheet_hash_bound": sha256(contact) == bindings["contact_sheet"]["sha256"],
        "decoded_one_frame": payload["runtime_observations"]["decoded_frame_count"] == 1,
        "decoded_frame_all_black": payload["runtime_observations"]["decoded_frame_black_clip_ratio"]
        == 1.0,
        "direct_visual_failed": payload["direct_visual_checks"]["visual_temporal_pass"] is False,
        "single_attempt_preserved": payload["boundaries"]["single_generation_attempt_preserved"]
        is True,
        "no_rerun": payload["boundaries"]["rerun_performed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Evidence validation failed: " + ", ".join(failed))
    return {"checks": checks, "failed_checks": failed, "visual_evidence_sha256": sha256(visual)}


def main() -> int:
    validation = validate_evidence()
    evidence_paths = [
        VISUAL_EVIDENCE.as_posix(),
        TRACKER_MIRROR.as_posix(),
        (ARTIFACT_DIR / "runtime_technical_evidence.json").as_posix(),
        (ARTIFACT_DIR / "wave64_animatediff_meaningful_seed7151601_00001_.webp").as_posix(),
        (ARTIFACT_DIR / "contact_sheet.png").as_posix(),
        "Workflows/video_generation/animatediff_fallback_meaningful_sequence/workflow.api.json",
        "Workflows/video_generation/animatediff_fallback_meaningful_sequence/runtime_requirements.json",
        "Plan/07_IMPLEMENTATION/scripts/run_wave64_animatediff_meaningful_sequence.py",
    ]
    tags = [
        "animatediff_changed_scope_quality_attempt_executed",
        "animatediff_meaningful_sequence_black_single_frame_output",
        "animatediff_fallback_promotion_remains_blocked",
        "single_attempt_no_seed_loop_preserved",
    ]
    note = (
        "Wave64 Row019 20260715T140007-0500: executed the one authorized materially changed "
        "16-frame AnimateDiff quality sequence. ComfyUI reported success, but the hash-bound WebP "
        "decoded as one uniformly black 384x512 frame, so automated and direct visual QA failed. "
        "The attempt is preserved, no retry or seed loop ran, and the broader Row019 blocker remains unchanged."
    )
    paths = [
        (ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv", "Tracker_ID", TRACKER_ID),
        (
            ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
            "Tracker_ID",
            TRACKER_ID,
        ),
        (ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv", "Item_ID", ITEM_ID),
        (
            ROOT / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
            "Item_ID",
            ITEM_ID,
        ),
    ]
    counts = [update_csv(path, key, row_id, evidence_paths, tags, note) for path, key, row_id in paths]
    report = {
        "schema_name": "wave64_animatediff_meaningful_sequence_reconciliation",
        "schema_version": "1.0",
        "timestamp": "2026-07-15T14:00:07-05:00",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": STATUS,
        "status_changed": False,
        "result": "blocked_animatediff_meaningful_sequence_black_single_frame_output",
        "validation": validation,
        "updated_rows": counts,
        "evidence_paths": evidence_paths,
        "boundaries": {
            "rerun_performed": False,
            "seed_loop_performed": False,
            "selected_wan_primary_invalidated": False,
            "promotion_claimed": False,
        },
        "next_action": "Continue the next concrete non-mask project task; do not rerun this candidate.",
    }
    report_path = ROOT / f"Plan/Items/Reports/ITEM-W64-019_animatediff_meaningful_sequence_{STAMP}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
