from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_candidate_mask_working_guard" / STAMP

CANDIDATE_BATCH = PROJECT_ROOT / "Ref_Image_Canonical_Body/candidate_mask_batch_20260708T192941"
V2_BATCH = PROJECT_ROOT / "Ref_Image_Canonical_Body/V2_filled_masks_20260708T194915"
MANIFEST = CANDIDATE_BATCH / "mask_manifest.csv"
STRICT_SUMMARY = CANDIDATE_BATCH / "STRICT_REVIEW_SUMMARY.json"

EVIDENCE = QA_DIR / f"W70_CANDIDATE_MASK_BATCH_WORKING_GUARD_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "candidate_mask_batch_working_guard.json"
PANEL = RUNTIME_DIR / "candidate_mask_batch_working_guard_panel.png"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_manifest_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def file_counts(root: Path) -> dict[str, object]:
    if not root.exists():
        return {
            "exists": False,
            "file_count": 0,
            "image_count": 0,
            "json_count": 0,
            "csv_count": 0,
            "binary_mask_count": 0,
            "overlay_count": 0,
            "contact_sheet_count": 0,
            "metadata_count": 0,
            "top_level_dirs": [],
        }
    files = [path for path in root.rglob("*") if path.is_file()]
    return {
        "exists": True,
        "file_count": len(files),
        "image_count": sum(1 for path in files if path.suffix.lower() in IMAGE_EXTS),
        "json_count": sum(1 for path in files if path.suffix.lower() == ".json"),
        "csv_count": sum(1 for path in files if path.suffix.lower() == ".csv"),
        "binary_mask_count": sum(1 for path in files if path.name.lower().startswith("binary_mask")),
        "overlay_count": sum(1 for path in files if path.name.lower().startswith("overlay")),
        "contact_sheet_count": sum(1 for path in files if "contact_sheet" in path.name.lower()),
        "metadata_count": sum(1 for path in files if path.name.lower().startswith("metadata")),
        "top_level_dirs": [path.name for path in sorted(root.iterdir()) if path.is_dir()],
    }


def manifest_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    def count(field: str) -> dict[str, int]:
        return dict(sorted(Counter(row.get(field, "") or "blank" for row in rows).items()))

    return {
        "row_count": len(rows),
        "headers": list(rows[0].keys()) if rows else [],
        "image_index_counts": count("image_index"),
        "category_counts": count("category"),
        "status_counts": count("status"),
        "method_counts": count("method"),
        "runtime_ready_counts": count("runtime_ready"),
        "certified_99_9_correct_counts": count("certified_99_9_correct"),
        "estimated_confidence_truthful_counts": count("estimated_confidence_truthful"),
    }


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, key_value: str, updates: dict[str, list[str] | str]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    count = 0
    for row in rows:
        if row.get(key) != key_value:
            continue
        count += 1
        for field, value in updates.items():
            if field not in fieldnames:
                continue
            if isinstance(value, list):
                row[field] = append_unique(row.get(field, ""), value)
            else:
                row[field] = value
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return count


def prepend(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_panel(payload: dict[str, object]) -> None:
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 940), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(34)
    head_font = load_font(24)
    body_font = load_font(20)
    small_font = load_font(16)
    draw.rectangle([0, 0, 1600, 88], fill=(42, 55, 72))
    draw.text((34, 24), "Wave70 Candidate Mask Working Guard", fill=(255, 255, 255), font=title_font)
    draw.text((36, 120), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 158), "User stated this batch is still being perfected. Do not consume as gold or authority.", fill=(125, 38, 28), font=body_font)

    batch = payload["candidate_batch_summary"]
    manifest = payload["manifest_summary"]
    v2 = payload["v2_batch_summary"]
    lines = [
        f"Candidate batch files: {batch['file_count']}",
        f"Candidate batch images: {batch['image_count']}",
        f"Binary masks: {batch['binary_mask_count']}",
        f"Overlays: {batch['overlay_count']}",
        f"Metadata JSON files: {batch['metadata_count']}",
        f"Manifest rows: {manifest['row_count']}",
        f"V2 working files: {v2['file_count']}",
        f"V2 working images: {v2['image_count']}",
    ]
    y = 220
    draw.text((36, y), "Inventory", fill=(42, 55, 72), font=head_font)
    y += 42
    for line in lines:
        draw.text((62, y), "- " + line, fill=(35, 35, 35), font=body_font)
        y += 32

    y += 20
    draw.text((36, y), "Consumption Guard", fill=(42, 55, 72), font=head_font)
    y += 42
    guard_lines = [
        "candidate_mask_batch_20260708T192941 is user-in-progress",
        "allowed for awareness and exclusion bookkeeping only",
        "not allowed for gold-standard validation",
        "not allowed for whole-body geometry authority",
        "not allowed for mask promotion or Wave71 activation",
        "wait for explicit user ready signal before consuming",
    ]
    for line in guard_lines:
        draw.text((62, y), "- " + line, fill=(35, 35, 35), font=body_font)
        y += 32

    draw.rectangle([36, 800, 1564, 892], outline=(160, 55, 45), width=3)
    draw.text((58, 824), "No masks promoted. No hard gates rerun. This artifact prevents accidental authority use.", fill=(125, 38, 28), font=small_font)
    img.save(PANEL)


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "70",
        "TRK-W70-0178",
        "Recorded candidate mask batch working guard after user stated candidate_mask_batch_20260708T192941 is still being perfected; batch is excluded from gold, authority, promotion, and hard-gate consumption until explicit ready signal.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; manifest aggregate scan; strict summary read; filesystem aggregate scan; JSON/panel evidence; tracker/item row verification",
        "CANDIDATE_MASK_BATCH_WORKING_GUARD_RECORDED_NO_PROMOTION",
        rel(EVIDENCE),
        "Wait for explicit user ready signal before using the candidate batch as reviewed mask input.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    rows = read_manifest_rows(MANIFEST)
    strict_summary = load_json(STRICT_SUMMARY)
    payload: dict[str, object] = {
        "timestamp": ISO_TS,
        "qa_decision": "candidate_mask_batch_user_in_progress_guarded_no_authority_no_promotion",
        "tracker_row": "TRK-W70-0178",
        "item_row": "ITEM-W70-0178",
        "user_instruction": "candidate_mask_batch_20260708T192941 is still being perfected and better masks are being created; user will say when it is ready.",
        "policy": {
            "batch_is_user_in_progress": True,
            "may_use_for_awareness_inventory": True,
            "may_use_for_exclusion_bookkeeping": True,
            "may_use_for_gold_standard_validation": False,
            "may_use_for_whole_body_geometry_authority": False,
            "may_use_for_mask_promotion": False,
            "may_trigger_hard_gate_rerun": False,
            "requires_explicit_user_ready_signal": True,
        },
        "candidate_batch": rel(CANDIDATE_BATCH),
        "candidate_batch_summary": file_counts(CANDIDATE_BATCH),
        "manifest": rel(MANIFEST) if MANIFEST.exists() else "",
        "manifest_summary": manifest_summary(rows),
        "strict_review_summary": {
            "path": rel(STRICT_SUMMARY) if STRICT_SUMMARY.exists() else "",
            "source_image_count": strict_summary.get("source_image_count"),
            "mask_label_count": strict_summary.get("mask_label_count"),
            "certified_mask_count": strict_summary.get("certified_mask_count"),
            "candidate_mask_count": strict_summary.get("candidate_mask_count"),
            "not_visible_or_unreliable_count": strict_summary.get("not_visible_or_unreliable_count"),
            "certification_result": strict_summary.get("certification_result"),
            "reason": strict_summary.get("reason"),
        },
        "v2_batch": rel(V2_BATCH),
        "v2_batch_summary": file_counts(V2_BATCH),
        "promotion_result": {
            "masks_promoted": 0,
            "gold_masks_created": 0,
            "hard_gates_rerun": False,
            "wave71_activation_allowed": False,
        },
        "evidence_paths": [
            rel(EVIDENCE),
            rel(CANONICAL_EVIDENCE),
            rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
            rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
            rel(PANEL),
        ],
    }

    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)
    draw_panel(payload)

    evidence_paths = payload["evidence_paths"]
    coverage_additions = [
        "candidate_mask_batch_working_guard_recorded",
        "candidate_mask_batch_user_in_progress",
        "candidate_masks_excluded_from_gold_authority_promotion_until_user_ready",
        "no_mask_promoted_candidate_working_guard",
    ]
    note = (
        f"Candidate mask batch working guard {STAMP}: user stated "
        "candidate_mask_batch_20260708T192941 is still being perfected and better masks are being created. "
        "Recorded inventory guard only; do not consume for gold-standard validation, whole-body geometry authority, "
        "mask promotion, hard-gate rerun, or Wave71 activation until explicit user ready signal. No masks promoted."
    )

    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_candidate_mask_batch_user_in_progress_guarded_no_authority_no_promotion",
                "Evidence_Link_or_File": evidence_paths,
                "Notes": [note],
                "Coverage_Audit_Status": coverage_additions,
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            "ITEM-W70-0178",
            {
                "Evidence_Required": evidence_paths,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Candidate Mask Batch Working Guard - {ISO_TS}

Recorded the user instruction that `Ref_Image_Canonical_Body/candidate_mask_batch_20260708T192941` is still being perfected and better masks are being created.

Decision: the batch is inventory-visible but consumption-guarded. It may be used only for awareness and exclusion bookkeeping until the user explicitly says it is ready. It cannot be used as gold-standard validation input, whole-body geometry authority, mask promotion evidence, hard-gate rerun trigger, or Wave71 activation proof.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(PANEL)}`

No masks were promoted. No hard gates were rerun. Next exact local action: wait for explicit user ready signal before consuming the candidate batch; continue using `Ref_Image_Canonical_Body/Main` as source-test imagery only.
"""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Candidate Mask Batch Working Guard - {ISO_TS}

User-in-progress guard recorded for `Ref_Image_Canonical_Body/candidate_mask_batch_20260708T192941`; no gold/authority/promotion use is allowed until explicit user ready signal.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "canonical_evidence": str(CANONICAL_EVIDENCE),
        "panel": str(PANEL),
        "qa_decision": payload["qa_decision"],
        "manifest_rows": payload["manifest_summary"]["row_count"],
        "candidate_batch_files": payload["candidate_batch_summary"]["file_count"],
        "v2_batch_files": payload["v2_batch_summary"]["file_count"],
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
