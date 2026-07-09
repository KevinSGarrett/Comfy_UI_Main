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

OLD_HEADER = "## Immediate Next Action - Continue TRK-W70-0171 Contact Occlusion Ownership - 2026-07-08T19:03:54-05:00"
NEW_HEADER = "## Immediate Next Action - Continue TRK-W70-0172 Body Region Geometry Resolver - 2026-07-08T19:03:54-05:00"
OLD_NEXT = "Next exact local action: continue active Wave70 at `TRK-W70-0171` / `ITEM-W70-0171` contact occlusion ownership authority using combined Ref_Image_1+Ref_Image_2 references."
NEW_NEXT = "Next exact local action: continue active Wave70 at `TRK-W70-0172` / `ITEM-W70-0172` body region geometry resolver using combined Ref_Image_1+Ref_Image_2 references; `TRK-W70-0171` already has combined-reference evidence and gates from 2026-07-08T18:13:00-05:00."
OLD_PROOF_NEXT = "Continue Wave70 at TRK-W70-0171 / ITEM-W70-0171 contact occlusion ownership authority with combined body references."
NEW_PROOF_NEXT = "Continue Wave70 at TRK-W70-0172 / ITEM-W70-0172 body region geometry resolver with combined body references; TRK-W70-0171 already has combined-reference gates."


def replace_top_block_text(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace(OLD_HEADER, NEW_HEADER, 1)
    text = text.replace(OLD_NEXT, NEW_NEXT, 1)
    path.write_text(text, encoding="utf-8")


def update_json(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["next_active_row"] = "TRK-W70-0172 / ITEM-W70-0172"
    payload["next_action"] = (
        "Continue body region geometry resolver with combined Ref_Image_1+Ref_Image_2 references; "
        "TRK-W70-0171 already has combined-reference contact/occlusion evidence and gates."
    )
    payload["next_action_correction"] = {
        "corrected_at": "2026-07-08T19:10:00-05:00",
        "reason": "TRK-W70-0171 already has combined Ref_Image_1+2 rerun and gates from 2026-07-08T18:13:00-05:00.",
    }
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
    print("Corrected post-gate next action to TRK-W70-0172 / ITEM-W70-0172.")


if __name__ == "__main__":
    main()
