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

SOURCE_KEY = "c45e2efa43da01fd"
TRACKER_ID = "TRK-051560"
ITEM_ID = "ITEM-051584"

TRACKER_MASTER = PLAN_ROOT / "Tracker/wave48_52_master_autonomous_tracker.csv"
ITEMS_MASTER = PLAN_ROOT / "Items/wave53_57_master_itemized_list.csv"
TRACKER_INDEX = PLAN_ROOT / "Tracker/Coverage_Audit/ultra_blueprint_source_section_index.csv"
ITEMS_INDEX = PLAN_ROOT / "Items/Coverage_Audit/ultra_blueprint_source_section_index.csv"
EVIDENCE_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
EVIDENCE = EVIDENCE_DIR / f"SINGLE_MISSING_ULTRA_SOURCE_KEY_REPAIR_{STAMP}.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def find_source_row(path: Path) -> dict[str, str]:
    _, rows = read_csv(path)
    for row in rows:
        if row.get("Source_Key") == SOURCE_KEY:
            return row
    raise RuntimeError(f"Source key {SOURCE_KEY} not found in {path}")


def insert_after_source_key(rows: list[dict[str, str]], after_key: str, new_row: dict[str, str]) -> tuple[list[dict[str, str]], int]:
    for index, row in enumerate(rows):
        if row.get("Source_Key") == after_key:
            return rows[: index + 1] + [new_row] + rows[index + 1 :], index + 1
    rows.append(new_row)
    return rows, len(rows) - 1


def repair_tracker(source: dict[str, str]) -> dict[str, object]:
    fieldnames, rows = read_csv(TRACKER_MASTER)
    if any(row.get("Source_Key") == SOURCE_KEY or row.get("Tracker_ID") == TRACKER_ID for row in rows):
        return {"changed": False, "reason": "tracker_row_already_present"}

    new_row = {field: "" for field in fieldnames}
    new_row.update(
        {
            "Tracker_ID": TRACKER_ID,
            "Wave": "48",
            "Phase": "Wave 48 — Ultra Blueprint Source Coverage",
            "Workstream": "General Blueprint Requirement",
            "Priority": "P2",
            "Risk_Level": "LOW",
            "Owner_Role": "Codex Desktop Autonomous Agent",
            "Environment": "local_repo_plan",
            "Status": "Ready for Autonomous Build",
            "Task_Name": "Implement/validate Ultra source section: Soft-body region profiles",
            "Detailed_Action": f"Autonomously implement, validate, test, and evidence the source-cited Ultra blueprint section from {source['Citation_File']} lines {source['Citation_Line_Start']}-{source['Citation_Line_End']}. No human input or manual work is allowed.",
            "Completion_Criteria": "Requirement is implemented or explicitly blocked with source citation, owner, validation, and next action.",
            "Acceptance_Evidence": "Source-linked validation and evidence report",
            "Dependency_Prerequisite": "Ultra blueprint source citation must be reviewed; catalog/search/traceability entry must exist before promotion.",
            "Validation_Method": "schema_validation|catalog_entry|evidence_required|proof_boundary_check",
            "Output_Artifact": "general_blueprint_requirement_implementation",
            "Source_Path": source["Citation_Full_Path"],
            "Related_Source_Paths": source["Citation_Full_Path"],
            "Package_Top_Level_Directory": str(PLAN_ROOT),
            "Autonomous_Execution_Mode": "Codex Desktop fully autonomous, no human input, no human manual work",
            "Human_Input_Allowed": "FALSE",
            "Human_Work_Allowed": "FALSE",
            "Codex_Desktop_Action": f"Read cited source, implement required project artifact, run validation, attach evidence, update tracker status, and never request human work. SourceKey={SOURCE_KEY}",
            "QA_Strictness": "STRICT",
            "Visual_Review_Required": "FALSE",
            "Visual_Review_Method": "Not required unless generated artifact becomes visual",
            "Test_Required": "TRUE",
            "Runtime_Proof_Required": "FALSE",
            "EC2_Allowed": "FALSE",
            "Preview_Required": "FALSE",
            "Final_Render_Gate": "FALSE",
            "Evidence_Path": str(PLAN_ROOT / f"Tracker/Evidence/{SOURCE_KEY}.json"),
            "Citation_File": source["Citation_File"],
            "Citation_Full_Path": source["Citation_Full_Path"],
            "Citation_Section": source["Citation_Section"],
            "Citation_Line_Start": source["Citation_Line_Start"],
            "Citation_Line_End": source["Citation_Line_End"],
            "Citation_Excerpt": source["Citation_Excerpt"],
            "Source_Package": "Ultra_Hyperrealism_System_Blueprint_Wave47_Blueprint_ProjectPlan_Combined_SecondPass_Cumulative",
            "Source_Type": source["Source_Type"],
            "Source_Item_ID": f"SRC-{SOURCE_KEY}",
            "Blocker_Policy": "No human work. Create blocker record, retry safe autonomous route, or mark blocked with exact source-cited reason.",
            "Rerun_Policy": "Targeted rerun only; preserve passed evidence; never rerun full project unless dependency graph requires it.",
            "Status_Decision": "autonomous_ready_or_blocked_by_evidence_only",
            "Notes": "Added by bounded Wave64 single-key coverage repair after validator identified this exact missing Ultra source key.",
            "Source_Key": SOURCE_KEY,
            "Source_File_Relative": source["Source_File_Relative"],
            "Coverage_Level": source["Coverage_Level"],
            "Coverage_Audit_Status": "ADDED_FOR_ULTRA_SOURCE_COVERAGE",
            "Ultra_Source_Coverage_Record": "TRUE",
        }
    )
    repaired_rows, insert_index = insert_after_source_key(rows, "eaa511a6fdb66a57", new_row)
    write_csv(TRACKER_MASTER, fieldnames, repaired_rows)
    return {"changed": True, "insert_index": insert_index, "id": TRACKER_ID, "path": rel(TRACKER_MASTER)}


def repair_items(source: dict[str, str]) -> dict[str, object]:
    fieldnames, rows = read_csv(ITEMS_MASTER)
    if any(row.get("Source_Key") == SOURCE_KEY or row.get("Item_ID") == ITEM_ID for row in rows):
        return {"changed": False, "reason": "item_row_already_present"}

    new_row = {field: "" for field in fieldnames}
    new_row.update(
        {
            "Item_ID": ITEM_ID,
            "Item_Wave": "53",
            "Item_Type": "ultra_blueprint_source_section",
            "Item_Title": "SOFT_BODY_MECHANICS_ULTIMATE_SPEC — Soft-body region profiles",
            "Item_Category": "General Blueprint Requirement",
            "Item_Domain": "general_blueprint_requirement",
            "Owner_Domain": "General Blueprint Requirement",
            "Autonomous_Required": "TRUE",
            "Human_Input_Allowed": "FALSE",
            "Human_Work_Allowed": "FALSE",
            "Codex_Action": f"Autonomously implement and validate the Ultra blueprint source section {source['Citation_File']} L{source['Citation_Line_Start']}-L{source['Citation_Line_End']}; no human input allowed.",
            "Implementation_Target": "general_blueprint_requirement_implementation",
            "Deliverable_Type": "code_config_workflow_manifest_qa_evidence",
            "Acceptance_Criteria": "Requirement is implemented or explicitly blocked with source citation, owner, validation, and next action.",
            "QA_Gates_Required": "schema_validation|catalog_entry|evidence_required|proof_boundary_check",
            "Visual_Review_Required": "FALSE",
            "Visual_Review_Method": "Not required unless generated artifact becomes visual",
            "Test_Required": "TRUE",
            "Evidence_Required": "Source-linked validation and evidence report",
            "Runtime_Proof_Required": "FALSE",
            "EC2_Allowed": "FALSE",
            "Blocker_Policy": "Do not ask for human work. Create blocker record, preserve logs/evidence, retry safe autonomous path, or mark blocked with exact reason.",
            "Source_Plan_Root": str(PLAN_ROOT),
            "Citation_File": source["Citation_File"],
            "Citation_Full_Path": source["Citation_Full_Path"],
            "Citation_Section": source["Citation_Section"],
            "Citation_Line_Start": source["Citation_Line_Start"],
            "Citation_Line_End": source["Citation_Line_End"],
            "Citation_Excerpt": source["Citation_Excerpt"],
            "Source_Package": "Ultra_Hyperrealism_System_Blueprint_Wave47_Blueprint_ProjectPlan_Combined_SecondPass_Cumulative",
            "Source_Type": source["Source_Type"],
            "Source_File_Size": source["Source_Size_Bytes"],
            "Priority": "P2",
            "Risk_Level": "LOW",
            "Status": "Ready for Autonomous Build",
            "Created_From": "ultra_source_coverage_audit",
            "Notes": "Added by bounded Wave64 single-key coverage repair after validator identified this exact missing Ultra source key.",
            "Source_Key": SOURCE_KEY,
            "Source_File_Relative": source["Source_File_Relative"],
            "Coverage_Level": source["Coverage_Level"],
            "Coverage_Audit_Status": "ADDED_FOR_ULTRA_SOURCE_COVERAGE",
            "Ultra_Source_Coverage_Record": "TRUE",
        }
    )
    repaired_rows, insert_index = insert_after_source_key(rows, "eaa511a6fdb66a57", new_row)
    write_csv(ITEMS_MASTER, fieldnames, repaired_rows)
    return {"changed": True, "insert_index": insert_index, "id": ITEM_ID, "path": rel(ITEMS_MASTER)}


def main() -> None:
    tracker_source = find_source_row(TRACKER_INDEX)
    items_source = find_source_row(ITEMS_INDEX)
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"SINGLE_MISSING_ULTRA_SOURCE_KEY_REPAIR_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "source_key": SOURCE_KEY,
        "source_file": tracker_source["Source_File_Relative"],
        "citation_section": tracker_source["Citation_Section"],
        "citation_lines": [tracker_source["Citation_Line_Start"], tracker_source["Citation_Line_End"]],
        "tracker_repair": repair_tracker(tracker_source),
        "items_repair": repair_items(items_source),
        "bounded_repair_policy": {
            "single_missing_key_only": True,
            "broad_coverage_generation": False,
            "rerun_verifier_allowed_once_after_repair": True,
        },
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
