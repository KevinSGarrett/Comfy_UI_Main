from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T15:07:14-05:00"
CONSENSUS_STAMP = "20260708T150714-0500"
TRACKER_ID = "TRK-W70-0173"
ITEM_ID = "ITEM-W70-0173"
NEXT_TRACKER_ID = "TRK-W70-0174"
NEXT_ITEM_ID = "ITEM-W70-0174"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

CONSENSUS_STAMPED = QA_DIR / f"W70_MODEL_CONSENSUS_GEOMETRY_VALIDATOR_{CONSENSUS_STAMP}.json"
CONSENSUS_CANONICAL = QA_DIR / "model_consensus_geometry_validator.json"
TRACKER_CONSENSUS_STAMPED = TRACKER_EVIDENCE_DIR / CONSENSUS_STAMPED.name
TRACKER_CONSENSUS_CANONICAL = TRACKER_EVIDENCE_DIR / CONSENSUS_CANONICAL.name
GEOMETRY_GATE = QA_DIR / f"W70_MASK_GEOMETRY_HARD_GATE_POST_MODEL_CONSENSUS_REF_IMAGE_1_{CONSENSUS_STAMP}.json"
PROMOTION_GATE = QA_DIR / f"W70_MASK_PROMOTION_HARD_GATE_POST_MODEL_CONSENSUS_REF_IMAGE_1_{CONSENSUS_STAMP}.json"
TRACKER_GEOMETRY_GATE = TRACKER_EVIDENCE_DIR / GEOMETRY_GATE.name
TRACKER_PROMOTION_GATE = TRACKER_EVIDENCE_DIR / PROMOTION_GATE.name


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def gate_summary(path: Path) -> dict[str, int]:
    payload = read_json(path)
    checked = payload.get("checked_rows") or []
    failures = payload.get("failures") or []
    pass_like = [row for row in checked if row.get("pass_like_status")]
    return {"checked": len(checked), "pass_like": len(pass_like), "failures": len(failures)}


def append_unique(values: list[str], additions: list[str]) -> list[str]:
    result = list(values)
    for item in additions:
        if item and item not in result:
            result.append(item)
    return result


def update_consensus_payload() -> dict[str, int]:
    gate_paths = [rel(GEOMETRY_GATE), rel(PROMOTION_GATE), rel(TRACKER_GEOMETRY_GATE), rel(TRACKER_PROMOTION_GATE)]
    updates = {}
    for path in [CONSENSUS_STAMPED, CONSENSUS_CANONICAL, TRACKER_CONSENSUS_STAMPED, TRACKER_CONSENSUS_CANONICAL]:
        payload = read_json(path)
        artifacts = payload.setdefault("artifacts", {})
        artifacts["post_model_consensus_geometry_gate"] = rel(GEOMETRY_GATE)
        artifacts["post_model_consensus_promotion_gate"] = rel(PROMOTION_GATE)
        payload["post_evaluation_hard_gates"] = {
            "geometry": {"path": rel(GEOMETRY_GATE), **gate_summary(GEOMETRY_GATE)},
            "promotion": {"path": rel(PROMOTION_GATE), **gate_summary(PROMOTION_GATE)},
            "tracker_copies": [rel(TRACKER_GEOMETRY_GATE), rel(TRACKER_PROMOTION_GATE)],
        }
        payload["evidence_paths"] = append_unique(payload.get("evidence_paths") or [], gate_paths)
        write_json(path, payload)
        updates[rel(path)] = 1
    return updates


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def update_hydration(evidence_paths: list[str]) -> dict[str, bool]:
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Attached post-`{TRACKER_ID}` / `{ITEM_ID}` hard-gate evidence.

Model consensus remains `Required_Not_Complete`: Ref_Image_1 gold masks and Full references are registered, but independent model consensus metrics are not computable yet. The `Full/New folder` image remains knees-to-head only and is not used for feet/toes/ankles/lower-calf/support proof. No masks were promoted.

Post-consensus gates: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence_block}"""
    updates = {
        "CURRENT_SESSION_STATE.md": prepend(
            HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
            f"## Session State Update - 0173 Model Consensus Gates Attached - {ISO_TS}",
            body + f"\n\nNext local action: `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` soft-body protected anchor geometry authority.",
        ),
        "CURRENT_PURSUING_GOAL.md": prepend(
            HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
            f"## Current Pursuing Goal Update - 0173 Model Consensus Gates Attached - {ISO_TS}",
            body,
        ),
        "RESUME_HERE_NEXT_CODEX_SESSION.md": prepend(
            HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
            f"## Resume Update - 0173 Model Consensus Gates Attached - {ISO_TS}",
            body + f"\n\nResume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` soft-body protected anchor geometry authority.",
        ),
        "NEXT_ACTION.md": prepend(
            HYDRATION_DIR / "NEXT_ACTION.md",
            f"## Immediate Next Action - {ISO_TS} - Work TRK-W70-0174 Soft-Body Protected Anchor Geometry",
            body + f"\n\nNext exact local action: implement or exactly block `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` soft-body deformation and protected anchor geometry authority.",
        ),
        "QA_EVIDENCE_INDEX.md": prepend(
            HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
            f"## Wave70 0173 Model Consensus Gate Evidence - {ISO_TS}",
            body,
        ),
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 0173 model consensus hard gates",
                "Attached post-model-consensus geometry/promotion hard gates; both passed fail-closed with 332 checked rows, zero pass-like rows, and zero failures. No masks promoted.",
                "; ".join(evidence_paths),
                "Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; JSON summary validation; tracker evidence copy",
                "MODEL_CONSENSUS_REF_IMAGE_1_ROUTE_NOT_COMPLETE_GATES_PASS",
                rel(CONSENSUS_CANONICAL),
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} soft-body protected anchor geometry authority next.",
            ]
        )
    return updates


def main() -> None:
    for gate in [GEOMETRY_GATE, PROMOTION_GATE]:
        summary = gate_summary(gate)
        if summary != {"checked": 332, "pass_like": 0, "failures": 0}:
            raise RuntimeError(f"Unexpected gate summary for {gate}: {summary}")
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GEOMETRY_GATE, TRACKER_GEOMETRY_GATE)
    shutil.copy2(PROMOTION_GATE, TRACKER_PROMOTION_GATE)
    payload_updates = update_consensus_payload()
    evidence_paths = [
        rel(CONSENSUS_STAMPED),
        rel(CONSENSUS_CANONICAL),
        rel(TRACKER_CONSENSUS_STAMPED),
        rel(TRACKER_CONSENSUS_CANONICAL),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
        rel(TRACKER_GEOMETRY_GATE),
        rel(TRACKER_PROMOTION_GATE),
    ]
    hydration_updates = update_hydration(evidence_paths)
    print(
        json.dumps(
            {
                "payload_updates": payload_updates,
                "hydration_updates": hydration_updates,
                "geometry_gate": gate_summary(GEOMETRY_GATE),
                "promotion_gate": gate_summary(PROMOTION_GATE),
                "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
