from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
HYDRATION = PROJECT_ROOT / "Plan" / "Instructions" / "Hydration_Rehydration"
WAVE70_EVIDENCE = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_EVIDENCE = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"

POST_GATE_NAME = "W70_0169_FEET_TOES_REENTRY_POST_GATES_20260708T190354-0500.json"
POST_GATE_FILES = [
    WAVE70_EVIDENCE / POST_GATE_NAME,
    WAVE70_EVIDENCE / "feet_toes_reentry_post_gates.json",
    TRACKER_EVIDENCE / POST_GATE_NAME,
    TRACKER_EVIDENCE / "feet_toes_reentry_post_gates.json",
]

OLD_HEADERS = [
    "## Immediate Next Action - Continue TRK-W70-0171 Contact Occlusion Ownership - 2026-07-08T19:03:54-05:00",
    "## Immediate Next Action - Continue TRK-W70-0172 Body Region Geometry Resolver - 2026-07-08T19:03:54-05:00",
]
NEW_HEADER = "## Immediate Next Action - Wave70 Terminal Prerequisite Gap - 2026-07-08T19:03:54-05:00"
OLD_NEXTS = [
    "Next exact local action: continue active Wave70 at `TRK-W70-0171` / `ITEM-W70-0171` contact occlusion ownership authority using combined Ref_Image_1+Ref_Image_2 references.",
    "Next exact local action: continue active Wave70 at `TRK-W70-0172` / `ITEM-W70-0172` body region geometry resolver using combined Ref_Image_1+Ref_Image_2 references; `TRK-W70-0171` already has combined-reference evidence and gates from 2026-07-08T18:13:00-05:00.",
]
NEW_NEXT = (
    "Next exact local action: stay at the Wave70 terminal prerequisite gap. Rows `TRK-W70-0169` through `TRK-W70-0178` already have "
    "combined-reference/blocker/gate evidence where defined, `TRK-W70-0173` is a recorded ledger gap mapped to actual model-consensus row `TRK-W70-0148`, "
    "and Wave71+ remains deferred. Acquire or integrate missing canonical whole-body geometry prerequisites before any promotion: side/profile, back, 3/4, contact/occlusion/support, "
    "multi-person owner-separation where applicable, and model-backed canonical pose/hand/human-parsing/contact/canonical-polygon evidence. Do not return to generic route registration, "
    "generic dependency probing, or looped hard-gate reruns unless a new exact route implementation artifact or new reference package exists first."
)
OLD_PROOF_NEXTS = [
    "Continue Wave70 at TRK-W70-0171 / ITEM-W70-0171 contact occlusion ownership authority with combined body references.",
    "Continue Wave70 at TRK-W70-0172 / ITEM-W70-0172 body region geometry resolver with combined body references; TRK-W70-0171 already has combined-reference gates.",
]
NEW_PROOF_NEXT = (
    "Stay at Wave70 terminal prerequisite gap: acquire/integrate missing canonical whole-body side/back/3-4/contact/occlusion/support/model-backed geometry prerequisites; "
    "do not activate Wave71+ or rerun generic route loops."
)


def replace_top_block_text(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for old in OLD_HEADERS:
        text = text.replace(old, NEW_HEADER, 1)
    for old in OLD_NEXTS:
        text = text.replace(old, NEW_NEXT, 1)
    path.write_text(text, encoding="utf-8")


def update_json(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["next_active_row"] = "WAVE70_TERMINAL_PREREQUISITE_GAP"
    payload["next_action"] = (
        "Acquire or integrate missing canonical whole-body geometry prerequisites before any promotion or Wave71+ activation; "
        "do not rerun generic route loops without a new exact route implementation artifact or new reference package."
    )
    corrections = payload.setdefault("next_action_corrections", [])
    corrections.append({
        "corrected_at": "2026-07-08T19:16:00-05:00",
        "reason": (
            "Rows 0170..0178 already have combined-reference/blocker/gate state where defined, and 0173 is a recorded ledger gap mapped to actual row 0148. "
            "The source-cited next state is the terminal canonical body geometry prerequisite gap."
        ),
    })
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def update_proof_log(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    for row in rows:
        if len(row) >= 9 and row[6] == "REF_IMAGES_1_2_FEET_TOES_REENTRY_POST_GATES_PASS_NO_PROMOTION":
            row[8] = NEW_PROOF_NEXT
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(rows)


def main() -> None:
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        replace_top_block_text(HYDRATION / name)
    for path in POST_GATE_FILES:
        update_json(path)
    update_proof_log(HYDRATION / "PROOF_OF_MOVEMENT_LOG.csv")
    print("Corrected post-gate next action to Wave70 terminal prerequisite gap.")


if __name__ == "__main__":
    main()
