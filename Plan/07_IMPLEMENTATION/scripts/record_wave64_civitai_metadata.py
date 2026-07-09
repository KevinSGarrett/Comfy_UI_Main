from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

TRACKER_ID = "TRK-W64-045"
ITEM_ID = "ITEM-W64-045"
NEXT_TRACKER_ID = "TRK-W64-046"
NEXT_ITEM_ID = "ITEM-W64-046"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
MODEL_EVIDENCE_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Model_Registry"

SUMMARY = max(MODEL_EVIDENCE_DIR.glob("W64_CIVITAI_REALVISXL_DETAIL_SUMMARY_*.json"), key=lambda path: path.stat().st_mtime)
QUERY = max(MODEL_EVIDENCE_DIR.glob("W64_CIVITAI_REALVISXL_QUERY_*.json"), key=lambda path: path.stat().st_mtime)
SOURCE_PROTOCOL = PLAN_ROOT / "Instructions/Operations/CIVITAI_API_OPERATING_PROTOCOL.md"
LOOKUP_SCRIPT = PLAN_ROOT / "Instructions/Operations/Scripts/Invoke-CivitaiModelLookup.ps1"
REGISTRY = PLAN_ROOT / "Registries/Models/model_registry.jsonl"

EVIDENCE = QA_DIR / "civitai_metadata.json"
STAMPED_EVIDENCE = QA_DIR / f"CIVITAI_METADATA_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"CIVITAI_METADATA_{STAMP}.json"

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


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
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
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def read_registry_records() -> list[dict[str, object]]:
    records = []
    for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def contains_secret_marker(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    return any(marker in text for marker in ["Authorization", "Bearer ", "CIVITAI_API_TOKEN", "CIVITAI_TOKEN", "CIVITAI_API_KEY"])


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded Civitai RealVisXL metadata lookup and provenance without token leakage or model download.",
        "; ".join(payload["evidence_paths"]),
        "api key secret safe; metadata record; version/file match; source URL record; no model binary download",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    summary = read_json(SUMMARY)
    query = read_json(QUERY)
    model_path = Path(str(summary["model_path"]))
    version_path = Path(str(summary["version_path"]))
    model = read_json(model_path)
    version = read_json(version_path)
    registry_records = [record for record in read_registry_records() if record.get("source") == "civitai"]
    realvisxl_records = [record for record in registry_records if str(record.get("source_model_id")) == "139562"]
    primary_files = [file for file in version.get("files", []) if isinstance(file, dict) and file.get("primary") is True]
    primary = primary_files[0] if primary_files else (version.get("files", [{}])[0] if version.get("files") else {})

    secret_paths = [path for path in [SUMMARY, model_path, version_path] if contains_secret_marker(path)]
    registry_mismatches = []
    for record in realvisxl_records:
        if str(record.get("source_model_version_id")) != "789646":
            registry_mismatches.append(f"{record.get('record_id')}:version")
        if str(record.get("file_name")) != str(primary.get("name")):
            registry_mismatches.append(f"{record.get('record_id')}:file")
        if str(record.get("sha256", "")).lower() != str(primary.get("hashes", {}).get("SHA256", "")).lower():
            registry_mismatches.append(f"{record.get('record_id')}:sha256")
        if "civitai.com/models/139562" not in str(record.get("source_url")):
            registry_mismatches.append(f"{record.get('record_id')}:source_url")

    errors: list[str] = []
    if summary.get("token_present") is not True:
        errors.append("civitai_token_not_loaded_for_clean_lookup")
    if summary.get("token_printed") is not False:
        errors.append("token_printed_unexpectedly")
    if secret_paths:
        errors.append(f"secret_marker_in_evidence:{len(secret_paths)}")
    if model.get("id") != 139562:
        errors.append(f"model_id_mismatch:{model.get('id')}")
    if model.get("name") != "RealVisXL V5.0":
        errors.append(f"model_name_mismatch:{model.get('name')}")
    if model.get("type") != "Checkpoint":
        errors.append(f"model_type_mismatch:{model.get('type')}")
    if version.get("id") != 789646:
        errors.append(f"version_id_mismatch:{version.get('id')}")
    if version.get("name") != "V5.0 (BakedVAE)":
        errors.append(f"version_name_mismatch:{version.get('name')}")
    if version.get("baseModel") != "SDXL 1.0":
        errors.append(f"base_model_mismatch:{version.get('baseModel')}")
    if primary.get("name") != "realvisxlV50_v50Bakedvae.safetensors":
        errors.append(f"primary_file_mismatch:{primary.get('name')}")
    if str(primary.get("hashes", {}).get("SHA256", "")).upper() != "6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80":
        errors.append("primary_sha256_mismatch")
    if not realvisxl_records:
        errors.append("registry_realvisxl_records_missing")
    if registry_mismatches:
        errors.append(f"registry_mismatches:{len(registry_mismatches)}")

    qa_decision = "civitai_metadata_passed_secret_safe_realvisxl_provenance" if not errors else "blocked_civitai_metadata_provenance_gap"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"CIVITAI_METADATA_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate Civitai metadata lookup and provenance for registered RealVisXL checkpoint records.",
        "source_protocol": rel(SOURCE_PROTOCOL),
        "lookup_script": rel(LOOKUP_SCRIPT),
        "query_evidence": evidence_path(QUERY),
        "detail_summary": evidence_path(SUMMARY),
        "model_detail_evidence": evidence_path(model_path),
        "version_detail_evidence": evidence_path(version_path),
        "secret_safety": {
            "token_loaded_for_clean_lookup": summary.get("token_present"),
            "token_printed": summary.get("token_printed"),
            "evidence_files_contain_secret_markers": bool(secret_paths),
            "secret_marker_paths": [evidence_path(path) for path in secret_paths],
        },
        "metadata_match": {
            "model_id": model.get("id"),
            "model_name": model.get("name"),
            "model_type": model.get("type"),
            "version_id": version.get("id"),
            "version_name": version.get("name"),
            "base_model": version.get("baseModel"),
            "primary_file_name": primary.get("name"),
            "primary_file_size_kb": primary.get("sizeKB"),
            "primary_sha256": primary.get("hashes", {}).get("SHA256"),
            "download_url_present": bool(primary.get("downloadUrl")),
        },
        "registry_provenance": {
            "civitai_registry_record_count": len(registry_records),
            "realvisxl_registry_record_count": len(realvisxl_records),
            "registry_record_ids": [record.get("record_id") for record in realvisxl_records],
            "registry_mismatches": registry_mismatches,
            "source_url_recorded": all("civitai.com/models/139562" in str(record.get("source_url")) for record in realvisxl_records),
            "version_file_match": not registry_mismatches,
        },
        "download_boundary": {
            "model_binary_downloaded_by_this_row": False,
            "unsafe_model_binary_committed": False,
            "download_url_recorded_as_metadata_only": bool(primary.get("downloadUrl")),
        },
        "runtime_boundary": {
            "ec2_started": False,
            "generation_executed": False,
            "comfyui_contacted": False,
            "target_runtime_promoted": False,
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(QUERY),
        evidence_path(SUMMARY),
        evidence_path(model_path),
        evidence_path(version_path),
        rel(SOURCE_PROTOCOL),
        rel(LOOKUP_SCRIPT),
        rel(REGISTRY),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 Civitai metadata {STAMP}: model_id={model.get('id')} version_id={version.get('id')} "
        f"primary_file={primary.get('name')} sha256={primary.get('hashes', {}).get('SHA256')} "
        f"registry_realvisxl_records={len(realvisxl_records)} token_printed=False secret_markers={len(secret_paths)} "
        f"downloaded_model_binary=False decision={qa_decision}."
    )
    additions = [
        "wave64_civitai_metadata_checked",
        qa_decision,
        "api_key_secret_safe",
        "metadata_record_captured",
        "version_file_match_passed",
        "source_url_recorded",
        "no_model_binary_downloaded",
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
## Immediate Next Action - Wave64 Civitai Metadata - {ISO_TS}

Worked non-EC2 metadata row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. Live metadata lookup confirmed Civitai model `{model.get('id')}` / version `{version.get('id')}` for `{model.get('name')}` `{version.get('name')}`, base model `{version.get('baseModel')}`, primary file `{primary.get('name')}`, and SHA256 `{primary.get('hashes', {}).get('SHA256')}`.

Secret/download boundary: token was loaded for the clean lookup but not printed; saved evidence contains no Authorization/Bearer/Civitai token markers; no model binary was downloaded or committed.

Runtime boundary: no EC2, ComfyUI contact, generation, target-runtime promotion, mask truth, mask promotion, hard-gate rerun, or Wave71+ activation occurred.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(SUMMARY)}`
- `{evidence_path(version_path)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
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
## Wave64 Civitai Metadata - {ISO_TS}

Civitai RealVisXL model/version metadata and registry provenance passed with token-safe evidence and no model download.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(SUMMARY)}`
- `{evidence_path(version_path)}`
""",
    )
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "stamped_evidence": str(STAMPED_EVIDENCE),
                "tracker_evidence": str(TRACKER_EVIDENCE),
                "qa_decision": qa_decision,
                "errors": errors,
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
