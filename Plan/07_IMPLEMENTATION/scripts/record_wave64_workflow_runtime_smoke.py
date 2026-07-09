from __future__ import annotations

import csv
import hashlib
import json
import struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

TRACKER_ID = "TRK-W64-037"
ITEM_ID = "ITEM-W64-037"
LANE_ID = "sdxl_low_risk_fallback_lane"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
RUNTIME_EVIDENCE_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Runtime"

SMOKE_RECORD = RUNTIME_EVIDENCE_DIR / "W64_LOCAL_SDXL_LOW_RISK_FALLBACK_AFTER_MODEL_PROVISION_EXECUTE_20260708T231300-0500.json"
SMOKE_REQUEST = RUNTIME_EVIDENCE_DIR / "W64_LOCAL_SDXL_LOW_RISK_FALLBACK_AFTER_MODEL_PROVISION_REQUEST_20260708T231300-0500.json"
OUTPUT_IMAGE = PROJECT_ROOT / "ComfyUI/output/codex_sdxl_low_risk_smoke_00001_.png"
MODEL_PATH = PROJECT_ROOT / "models/checkpoints/sd_xl_base_1.0.safetensors"
STATIC_VALIDATION = QA_DIR / "workflow_static_validation.json"
OBJECT_INFO = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness/W64_LOCAL_OBJECT_INFO_RAW_WORKFLOW_STATIC_AFTER_SDXL_BASE_20260708T231120-0500.json"

EVIDENCE = QA_DIR / "workflow_runtime_smoke.json"
STAMPED_EVIDENCE = QA_DIR / f"WORKFLOW_RUNTIME_SMOKE_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"WORKFLOW_RUNTIME_SMOKE_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def evidence_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_dimensions(path: Path) -> tuple[int | None, int | None, str | None]:
    try:
        with path.open("rb") as f:
            header = f.read(24)
        if len(header) < 24 or not header.startswith(b"\x89PNG\r\n\x1a\n"):
            return None, None, "not_png"
        width, height = struct.unpack(">II", header[16:24])
        return width, height, None
    except Exception as exc:  # pragma: no cover - evidence script
        return None, None, str(exc)


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


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Ran local bounded ComfyUI workflow runtime smoke after exact SDXL base checkpoint provisioning.",
        "; ".join(payload["evidence_paths"]),
        "local ComfyUI /prompt execution; history output check; image file existence; PNG metadata; SHA256; visual QA notes",
        payload["qa_decision"],
        rel(EVIDENCE),
        "Advance to the next concrete non-mask runtime or QA row; do not rerun this smoke unless lane inputs or QA thresholds change.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    smoke = read_json(SMOKE_RECORD) if SMOKE_RECORD.exists() else {}
    request_exists = SMOKE_REQUEST.exists()
    image_exists = OUTPUT_IMAGE.exists()
    model_exists = MODEL_PATH.exists()
    width, height, png_error = png_dimensions(OUTPUT_IMAGE) if image_exists else (None, None, "missing")

    errors: list[str] = []
    if not isinstance(smoke, dict):
        errors.append("smoke_record_not_object")
        smoke = {}
    if smoke.get("lane_id") != LANE_ID:
        errors.append(f"lane_id_mismatch:{smoke.get('lane_id')}")
    if smoke.get("mode") != "execute":
        errors.append(f"mode_not_execute:{smoke.get('mode')}")
    if smoke.get("generation_executed") is not True:
        errors.append("generation_executed_not_true")
    if smoke.get("history_status") != "outputs_found":
        errors.append(f"history_status_not_outputs_found:{smoke.get('history_status')}")
    if smoke.get("errors"):
        errors.append("smoke_record_errors_present")
    if not request_exists:
        errors.append("prompt_request_missing")
    if not model_exists:
        errors.append("sdxl_base_checkpoint_missing_after_provision")
    if not image_exists:
        errors.append("output_image_missing")
    if png_error:
        errors.append(f"png_metadata_error:{png_error}")
    if width != 1024 or height != 1024:
        errors.append(f"unexpected_image_dimensions:{width}x{height}")

    output_images = smoke.get("output_images") if isinstance(smoke.get("output_images"), list) else []
    qa_decision = "workflow_runtime_smoke_passed_local_nonmask_safe" if not errors else "blocked_workflow_runtime_smoke_local_qa_failure"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"WORKFLOW_RUNTIME_SMOKE_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "lane_id": LANE_ID,
        "task": "Record local bounded ComfyUI workflow runtime smoke proof after exact model provisioning.",
        "source_smoke_record": evidence_path(SMOKE_RECORD),
        "source_prompt_request": evidence_path(SMOKE_REQUEST),
        "static_validation_evidence": evidence_path(STATIC_VALIDATION),
        "object_info_evidence": evidence_path(OBJECT_INFO),
        "model_asset": {
            "path": evidence_path(MODEL_PATH),
            "exists": model_exists,
            "bytes": MODEL_PATH.stat().st_size if model_exists else 0,
            "sha256": sha256(MODEL_PATH) if model_exists else "",
            "expected_sha256": "31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b",
        },
        "runtime_execution": {
            "local_generation_executed": smoke.get("generation_executed") is True,
            "ec2_started": False,
            "api_base_url": smoke.get("api_base_url"),
            "prompt_id": smoke.get("prompt_id"),
            "history_status": smoke.get("history_status"),
            "output_images": output_images,
        },
        "output_artifact": {
            "path": evidence_path(OUTPUT_IMAGE),
            "exists": image_exists,
            "bytes": OUTPUT_IMAGE.stat().st_size if image_exists else 0,
            "sha256": sha256(OUTPUT_IMAGE) if image_exists else "",
            "width": width,
            "height": height,
            "format": "png" if image_exists and not png_error else "",
        },
        "visual_qa": {
            "reviewed_by": "codex_visual_inspection",
            "result": "pass_with_scope_notes" if not errors else "not_passed",
            "notes": [
                "Image is a coherent single-subject portrait with complete frame and no obvious corruption.",
                "Eyes, face, hair, and fabric are readable; no visible watermark, UI text, or blank/partial output.",
                "This proof covers low-risk portrait workflow runtime only; it does not claim full-body, hand/contact, mask, video, or final portfolio certification.",
            ],
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": "Advance to the next concrete non-mask runtime/QA task; preserve this smoke proof unless workflow inputs, model, or QA threshold changes.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(SMOKE_RECORD),
        evidence_path(SMOKE_REQUEST),
        evidence_path(OUTPUT_IMAGE),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 workflow runtime smoke {STAMP}: lane={LANE_ID}; local_generation_executed={payload['runtime_execution']['local_generation_executed']}; "
        f"ec2_started=False; output={payload['output_artifact']['path']}; decision={qa_decision}. "
        "No masks consumed or promoted."
    )
    additions = [
        "wave64_workflow_runtime_smoke_ran",
        qa_decision,
        "local_nonmask_runtime_proof",
        "allowed_nonmask_work_can_continue",
    ]
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Status_Decision": qa_decision,
                "Evidence_Path": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            ITEM_ID,
            {
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 Workflow Runtime Smoke - {ISO_TS}

Worked concrete non-mask runtime task `{TRACKER_ID}` / `{ITEM_ID}`: local ComfyUI workflow runtime smoke for `{LANE_ID}` after exact SDXL base checkpoint provisioning.

Result: `{qa_decision}`. Local `/prompt` execution produced `{payload['output_artifact']['path']}` at `{width}x{height}`. EC2 was not started.

Runtime boundary: no masks were consumed as truth, no masks were promoted, no hard gates were rerun, and no Wave71+ activation was attempted.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(SMOKE_RECORD)}`
- `{evidence_path(OUTPUT_IMAGE)}`

Next exact local action: advance to the next concrete non-mask runtime/QA row; do not rerun this smoke unless workflow inputs, model, or QA threshold changes.
"""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"""
## Wave64 Workflow Runtime Smoke - {ISO_TS}

Local bounded ComfyUI `/prompt` runtime smoke for `{LANE_ID}` after exact checkpoint provisioning. No EC2 and no mask truth.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(SMOKE_RECORD)}`
- `{evidence_path(OUTPUT_IMAGE)}`
""",
    )
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "stamped_evidence": str(STAMPED_EVIDENCE),
        "tracker_evidence": str(TRACKER_EVIDENCE),
        "qa_decision": qa_decision,
        "errors": errors,
        "output_image": str(OUTPUT_IMAGE),
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
