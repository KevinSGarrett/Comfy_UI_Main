from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = NOW.isoformat()
EVIDENCE_ID = f"W71_ACTIVATION_GATE_AUDIT_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/audit_wave71_activation_gate.py"

SOURCE_DOC = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/physics_deformation_system/WAVE71_SOFT_BODY_PHYSICS_DEFORMATION_MAP_SYSTEM.md"
SOURCE_MATRIX = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/physics_deformation_system/WAVE71_SOFT_BODY_PHYSICS_DEFORMATION_MAP_SYSTEM_MATRIX.csv"
W70_TRACKER = PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv"
W71_TRACKER = PROJECT_ROOT / "Plan/Tracker/wave71_soft_body_physics_deformation_map_system_tracker.csv"
W71_TRACKER_WAVE = PROJECT_ROOT / "Plan/Tracker/Waves/Wave71/WAVE71_SOFT_BODY_PHYSICS_DEFORMATION_MAP_SYSTEM_TRACKER_ROWS.csv"
W71_ITEMS = PROJECT_ROOT / "Plan/Items/wave71_soft_body_physics_deformation_map_system_itemized_list.csv"
W71_ITEMS_WAVE = PROJECT_ROOT / "Plan/Items/Waves/Wave71/WAVE71_SOFT_BODY_PHYSICS_DEFORMATION_MAP_SYSTEM_ITEM_ROWS.csv"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Physics_Deformation/Wave71"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence/Physics_Deformation/Wave71"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/physics_deformation/wave71_activation_gate" / RUN_STAMP
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

W70_EVIDENCE = [
    PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_reference_matrix.json",
    PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/redo_existing_body_hand_contact_masks.json",
    PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/whole_body_geometry_promotion_integration.json",
]


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("Status", "")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def w70_summary() -> dict[str, object]:
    rows = read_rows(W70_TRACKER)
    status = status_counts(rows)
    evidence_summaries = {}
    for path in W70_EVIDENCE:
        payload = read_json(path)
        evidence_summaries[rel(path)] = {
            "exists": path.exists(),
            "evidence_id": payload.get("evidence_id"),
            "qa_decision": payload.get("qa_decision"),
            "sha256": sha256_file(path) if path.exists() else "",
        }
    return {
        "tracker_path": rel(W70_TRACKER),
        "row_count": len(rows),
        "status_counts": status,
        "whole_body_authority_current_evidence": evidence_summaries,
        "activation_dependency_result": "not_stable_enough_for_wave71_activation",
        "reason": (
            "Wave70 still has fail-closed whole-body geometry authority blockers: body reference matrix context exists "
            "but has not passed, canonical body geometry is unavailable, and whole-body promotion integration remains blocked."
        ),
    }


def wave71_summary() -> dict[str, object]:
    rows = read_rows(W71_TRACKER)
    matrix_rows = read_rows(SOURCE_MATRIX)
    return {
        "source_doc": {
            "path": rel(SOURCE_DOC),
            "exists": SOURCE_DOC.exists(),
            "sha256": sha256_file(SOURCE_DOC) if SOURCE_DOC.exists() else "",
        },
        "source_matrix": {
            "path": rel(SOURCE_MATRIX),
            "exists": SOURCE_MATRIX.exists(),
            "sha256": sha256_file(SOURCE_MATRIX) if SOURCE_MATRIX.exists() else "",
            "row_count": len(matrix_rows),
        },
        "tracker": {
            "path": rel(W71_TRACKER),
            "row_count": len(rows),
            "status_counts": status_counts(rows),
            "first_row": rows[0].get("Tracker_ID", "") if rows else "",
            "last_row": rows[-1].get("Tracker_ID", "") if rows else "",
        },
        "activation_gate_text": (
            "Deferred. Activate only after current ComfyUI foundation, runtime lanes, cost controls, and Wave70 Mask "
            "Factory coverage are stable enough that physics-map work will not derail nearer project milestones."
        ),
    }


def update_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updates: dict[str, int] = {}
    targets = [
        (W71_TRACKER, "Tracker_ID"),
        (W71_TRACKER_WAVE, "Tracker_ID"),
        (W71_ITEMS, "Item_ID"),
        (W71_ITEMS_WAVE, "Item_ID"),
    ]
    for path, _key in targets:
        if not path.exists():
            updates[rel(path)] = 0
            continue
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        changed = 0
        for row in rows:
            status = row.get("Status", "")
            if status != "Deferred_Required_Not_Complete":
                continue
            changed += 1
            for field in ("Evidence_Path", "Evidence_Required", "Acceptance_Evidence"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "deferred_wave71_activation_gate_not_met_wave70_not_stable"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "wave71_activation_gate_checked",
                        "deferred_wave71_activation_gate_not_met",
                        "wave70_whole_body_geometry_stability_not_met",
                    ],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        updates[rel(path)] = changed
    return updates


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def update_hydration(evidence_paths: list[str], w71: dict[str, object], w70: dict[str, object]) -> None:
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    status_counts_text = json.dumps(w71["tracker"]["status_counts"], sort_keys=True)
    body = f"""Audited Wave71 activation gate after Wave70 row `TRK-W70-0178`.

Wave71 remains deferred by its own source rule. Current Wave71 tracker rows: `{w71['tracker']['row_count']}`, status counts `{status_counts_text}`. Wave70 is not stable enough to activate Wave71 because whole-body geometry authority, canonical body geometry, and promotion integration remain fail-closed.

Decision: keep Wave71 rows `Deferred_Required_Not_Complete`; do not start physics/deformation map generation, simulation backends, target runtime proof, or EC2 from Wave71 yet.

Evidence:

{evidence_block}"""
    prepend(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - Wave71 Activation Gate Deferred - {ISO_STAMP}",
        body,
    )
    prepend(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Current Pursuing Goal Update - Wave71 Activation Gate Deferred - {ISO_STAMP}",
        body,
    )
    prepend(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - Wave71 Activation Gate Deferred - {ISO_STAMP}",
        body + "\n\nResume by selecting the next local-first non-deferred requirement, or re-audit Wave72+ activation gates if all immediate rows are deferred.",
    )
    prepend(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Inspect Next Non-Deferred Project Row",
        body + "\n\nNext exact local action: inspect Wave72+ trackers and continue only with rows whose activation gate is met, keeping deferred physics/simulation rows fail-closed.",
    )
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave71 Activation Gate Evidence - {ISO_STAMP}",
        body,
    )


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    w70 = w70_summary()
    w71 = wave71_summary()

    qa_stamped = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical = QA_DIR / "wave71_activation_gate.json"
    tracker_stamped = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical = TRACKER_EVIDENCE_DIR / "wave71_activation_gate.json"
    runtime_evidence = RUNTIME_DIR / "wave71_activation_gate.json"
    evidence_paths = [
        rel(qa_stamped),
        rel(qa_canonical),
        rel(tracker_stamped),
        rel(tracker_canonical),
        rel(runtime_evidence),
    ]
    note = (
        f"Wave71 activation gate audit {RUN_STAMP}: deferred by source rule. Wave70 whole-body geometry/promotion "
        "stability is not met, so Wave71 physics/deformation rows remain Deferred_Required_Not_Complete."
    )
    row_updates = update_rows(evidence_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "script": SCRIPT_REL,
        "task": "Audit Wave71 activation gate after Wave70 fail-closed whole-body authority work.",
        "wave71_activation_gate": {
            "result": "deferred_required_not_complete",
            "activation_gate_met": False,
            "deferred_status_preserved": True,
            "reason": "Wave70/current foundation is not stable enough for Wave71 physics-map activation.",
            "no_physics_map_generation_started": True,
            "no_simulation_backend_started": True,
            "ec2_started": False,
        },
        "wave70_dependency_summary": w70,
        "wave71_summary": w71,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "tracker_item_updates": row_updates,
        "qa_decision": "deferred_wave71_activation_gate_not_met_wave70_not_stable",
        "next_step": "Inspect Wave72+ trackers or other project trackers for the next non-deferred local-first task.",
    }
    for path in [qa_stamped, qa_canonical, tracker_stamped, tracker_canonical, runtime_evidence]:
        write_json(path, payload)
    update_hydration(evidence_paths, w71, w70)
    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "qa_decision": payload["qa_decision"],
                "wave71_rows": w71["tracker"]["row_count"],
                "row_updates": row_updates,
                "evidence": rel(qa_stamped),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
