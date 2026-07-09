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

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

ALIGNMENT = QA_DIR / "available_route_runtime_validation_alignment.json"
GEOMETRY_GATE = QA_DIR / "W70_MASK_GEOMETRY_HARD_GATE_POST_AVAILABLE_ROUTE_RUNTIME_VALIDATION_20260708T185104-0500.json"
PROMOTION_GATE = QA_DIR / "W70_MASK_PROMOTION_HARD_GATE_POST_AVAILABLE_ROUTE_RUNTIME_VALIDATION_20260708T185104-0500.json"
EVIDENCE = QA_DIR / f"W70_AVAILABLE_ROUTE_RUNTIME_VALIDATION_GATES_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "available_route_runtime_validation_gates.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def gate_summary(path: Path) -> dict[str, int]:
    payload = read_json(path)
    checked = payload.get("checked_rows") or []
    failures = payload.get("failures") or []
    pass_like = [row for row in checked if row.get("pass_like_status")]
    return {"checked": len(checked), "pass_like": len(pass_like), "failures": len(failures)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def tracker_copy(path: Path) -> str:
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = TRACKER_EVIDENCE_DIR / path.name
    shutil.copy2(path, target)
    return rel(target)


def main() -> None:
    alignment = read_json(ALIGNMENT)
    geometry = gate_summary(GEOMETRY_GATE)
    promotion = gate_summary(PROMOTION_GATE)
    require(alignment.get("qa_decision") == "available_routes_runtime_executed_partial_but_whole_body_stack_still_blocked_no_promotion", "Unexpected available-route alignment decision")
    require(geometry == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected geometry gate: {geometry}")
    require(promotion == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected promotion gate: {promotion}")
    tracker_gate_paths = [tracker_copy(GEOMETRY_GATE), tracker_copy(PROMOTION_GATE)]

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_AVAILABLE_ROUTE_RUNTIME_VALIDATION_GATES_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Record post-gate verification for Wave70 available-route runtime validation alignment.",
        "alignment": {
            "path": rel(ALIGNMENT),
            "evidence_id": alignment.get("evidence_id"),
            "qa_decision": alignment.get("qa_decision"),
        },
        "gates": {
            "geometry": {"path": rel(GEOMETRY_GATE), **geometry},
            "promotion": {"path": rel(PROMOTION_GATE), **promotion},
            "tracker_copies": tracker_gate_paths,
        },
        "promotion_policy": {
            "masks_changed": [],
            "masks_promoted": [],
            "completion_allowed": False,
            "wave71_activation_allowed": False,
        },
        "qa_decision": "available_route_runtime_validation_post_gates_pass_fail_closed_no_promotion",
        "next_step": alignment.get("next_step"),
    }
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)

    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(ALIGNMENT),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
        *tracker_gate_paths,
    ]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Post-gate verification completed for Wave70 available-route runtime validation alignment.

The route state remains fail-closed: pose, hand, and SAM2/promptable refinement have runtime evidence, but they are partial or source-limited and do not create whole-body authority. Human parsing, person-instance segmentation, temporal propagation, and contact ownership remain missing required routes.

Wave70 hard gates passed fail-closed after the row/evidence update: geometry and promotion each checked 332 rows with zero pass-like rows and zero failures. No masks were changed or promoted; Wave71+ remains deferred.

Evidence:

{evidence_block}

Next exact local action: resolve/register the missing required whole-body routes before canonical polygon work."""
    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - Available Route Runtime Validation Gates",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - Available Route Runtime Validation Gates",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - Available Route Runtime Validation Gates",
            "NEXT_ACTION.md": "Immediate Next Action - Resolve Missing Required Whole Body Routes",
            "QA_EVIDENCE_INDEX.md": "Wave70 Available Route Runtime Validation Gate Evidence",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 available-route runtime validation post-gates recorded",
                "Verified geometry and promotion gates after available-route runtime alignment; no promotion.",
                "; ".join(evidence_paths),
                "Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1",
                "AVAILABLE_ROUTE_RUNTIME_VALIDATION_POST_GATES_FAIL_CLOSED",
                rel(EVIDENCE),
                "Resolve/register missing required whole-body routes before canonical polygon work.",
            ]
        )
    print(json.dumps({"evidence": rel(EVIDENCE), "hydration_updates": updates, "qa_decision": payload["qa_decision"]}, indent=2))


if __name__ == "__main__":
    main()
