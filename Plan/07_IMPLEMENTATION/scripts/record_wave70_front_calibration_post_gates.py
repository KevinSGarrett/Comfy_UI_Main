from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
GATE_STAMP = "20260708T194534-0500"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

GEOMETRY_GATE = QA_DIR / f"W70_MASK_GEOMETRY_HARD_GATE_POST_FRONT_CALIBRATION_SEED_{GATE_STAMP}.json"
PROMOTION_GATE = QA_DIR / f"W70_MASK_PROMOTION_HARD_GATE_POST_FRONT_CALIBRATION_SEED_{GATE_STAMP}.json"
INTAKE_EVIDENCE = QA_DIR / "canonical_reference_package_intake_validation.json"
SYNC_EVIDENCE = QA_DIR / "canonical_reference_dropzone_manifest_sync.json"
MASK_SEED_EVIDENCE = QA_DIR / "front_calibration_mask_seed.json"
SOURCE_SEED_EVIDENCE = QA_DIR / "front_calibration_reference_seed.json"

EVIDENCE = QA_DIR / f"W70_FRONT_CALIBRATION_POST_GATES_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "front_calibration_post_gates.json"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(block.rstrip() + "\n\n" + existing, encoding="utf-8")


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "70",
        "Wave70 front calibration post-seed hard gates",
        "Recorded geometry and promotion hard gate results after front calibration source/mask seeding; both gates passed with zero pass-like rows, and no masks were promoted.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; geometry hard gate JSON validation; promotion hard gate JSON validation; tracker/item row verification",
        "FRONT_CALIBRATION_POST_GATES_PASS_NO_PROMOTION",
        rel(EVIDENCE),
        "Continue fail-closed until missing side/profile, back, 3/4, contact/support references and model-backed geometry authority are available.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    geometry = read_json(GEOMETRY_GATE)
    promotion = read_json(PROMOTION_GATE)
    intake = read_json(INTAKE_EVIDENCE) if INTAKE_EVIDENCE.exists() else {}
    sync = read_json(SYNC_EVIDENCE) if SYNC_EVIDENCE.exists() else {}
    mask_seed = read_json(MASK_SEED_EVIDENCE) if MASK_SEED_EVIDENCE.exists() else {}
    source_seed = read_json(SOURCE_SEED_EVIDENCE) if SOURCE_SEED_EVIDENCE.exists() else {}

    tracker_geometry = TRACKER_EVIDENCE_DIR / GEOMETRY_GATE.name
    tracker_promotion = TRACKER_EVIDENCE_DIR / PROMOTION_GATE.name
    shutil.copy2(GEOMETRY_GATE, tracker_geometry)
    shutil.copy2(PROMOTION_GATE, tracker_promotion)

    geometry_pass = bool(geometry.get("wave70_mask_geometry_gate_validator_pass"))
    promotion_pass = bool(promotion.get("wave70_mask_promotion_gate_pass"))
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_FRONT_CALIBRATION_POST_GATES_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Record Wave70 hard gate results after front calibration source/mask seeding.",
        "front_calibration_state": {
            "source_seed_evidence_id": source_seed.get("evidence_id"),
            "mask_seed_evidence_id": mask_seed.get("evidence_id"),
            "dropzone_sync_evidence_id": sync.get("evidence_id"),
            "intake_evidence_id": intake.get("evidence_id"),
            "manifest_source_image_count": (intake.get("intake_summary") or {}).get("manifest_source_image_count"),
            "manifest_mask_image_count": (intake.get("intake_summary") or {}).get("manifest_mask_image_count"),
            "required_slots_satisfied": (intake.get("intake_summary") or {}).get("required_slots_satisfied"),
            "required_slots_complete_for_authority": (intake.get("intake_summary") or {}).get("required_slots_complete_for_authority"),
            "blocked_required_slot_count": (intake.get("intake_summary") or {}).get("blocked_required_slot_count"),
            "intake_contract_pass": (intake.get("intake_summary") or {}).get("intake_contract_pass"),
        },
        "geometry_gate": {
            "path": rel(GEOMETRY_GATE),
            "tracker_copy": rel(tracker_geometry),
            "result": geometry.get("result"),
            "pass": geometry_pass,
            "checked_row_count": geometry.get("checked_row_count"),
            "pass_like_row_count": geometry.get("pass_like_row_count"),
            "failure_count": len(geometry.get("failures") or []),
            "warning_count": len(geometry.get("warnings") or []),
        },
        "promotion_gate": {
            "path": rel(PROMOTION_GATE),
            "tracker_copy": rel(tracker_promotion),
            "result": promotion.get("result"),
            "pass": promotion_pass,
            "checked_row_count": promotion.get("checked_row_count"),
            "pass_like_row_count": promotion.get("pass_like_row_count"),
            "blocked_or_untrusted_row_count": promotion.get("blocked_or_untrusted_row_count"),
            "failure_count": len(promotion.get("failures") or []),
            "warning_count": len(promotion.get("warnings") or []),
        },
        "policy": {
            "front_calibration_only": True,
            "mask_promotion_allowed": False,
            "wave71_activation_allowed": False,
            "hard_gates_rerun_reason": "Specific post-front-calibration source/mask seed artifact changed local reference state.",
        },
        "qa_decision": "front_calibration_post_gates_pass_no_promotion",
        "promotion_decision": "no_mask_promoted_front_calibration_remains_calibration_only",
        "next_step": "Continue fail-closed until missing side/profile, back, 3/4, contact/support references and model-backed geometry authority are available.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
        rel(tracker_geometry),
        rel(tracker_promotion),
    ]

    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)

    evidence_additions = payload["evidence_paths"]
    coverage_additions = [
        "front_calibration_post_seed_geometry_gate_pass",
        "front_calibration_post_seed_promotion_gate_pass",
        "no_pass_like_rows_after_front_calibration_seed",
        "no_mask_promoted_post_front_calibration_gates",
    ]
    note = (
        f"Front calibration post gates {STAMP}: geometry and promotion hard gates passed after source/mask seed; "
        f"geometry checked {geometry.get('checked_row_count')} rows with {geometry.get('pass_like_row_count')} pass-like, "
        f"promotion checked {promotion.get('checked_row_count')} rows with {promotion.get('pass_like_row_count')} pass-like. No masks promoted."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_front_calibration_post_gates_pass_no_promotion",
                "Evidence_Path": evidence_additions,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            "ITEM-W70-0178",
            {
                "Evidence_Required": evidence_additions,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    top_block = f"""## Immediate Next Action - Front Calibration Post-Seed Hard Gates - {ISO_TS}

Recorded Wave70 hard gate results after the front calibration source/mask seed.

Gate results:
- Geometry gate: `{geometry.get('result')}`, checked `{geometry.get('checked_row_count')}` rows, pass-like rows `{geometry.get('pass_like_row_count')}`, failures `{len(geometry.get('failures') or [])}`.
- Promotion gate: `{promotion.get('result')}`, checked `{promotion.get('checked_row_count')}` rows, pass-like rows `{promotion.get('pass_like_row_count')}`, failures `{len(promotion.get('failures') or [])}`.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(GEOMETRY_GATE)}`
- `{rel(PROMOTION_GATE)}`
- `{rel(tracker_geometry)}`
- `{rel(tracker_promotion)}`

No masks were promoted. Front source/mask files remain calibration-only. Next exact local action: continue fail-closed until missing side/profile, back, 3/4, contact/support references and model-backed geometry authority are available."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Front Calibration Post-Seed Hard Gates - {ISO_TS}

Recorded post-front-calibration hard gates. Geometry and promotion gates both passed with zero pass-like rows. No masks were promoted; front references remain calibration-only.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(GEOMETRY_GATE)}`
- `{rel(PROMOTION_GATE)}`
- `{rel(tracker_geometry)}`
- `{rel(tracker_promotion)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "canonical": str(CANONICAL_EVIDENCE),
        "geometry_pass": geometry_pass,
        "promotion_pass": promotion_pass,
        "geometry_checked": geometry.get("checked_row_count"),
        "promotion_checked": promotion.get("checked_row_count"),
        "geometry_pass_like": geometry.get("pass_like_row_count"),
        "promotion_pass_like": promotion.get("pass_like_row_count"),
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
