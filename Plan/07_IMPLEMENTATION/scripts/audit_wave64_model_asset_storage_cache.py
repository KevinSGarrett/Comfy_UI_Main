from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TZ = ZoneInfo("America/Chicago")
TRK, ITEM = "TRK-W64-007", "ITEM-W64-007"
STATUS = "Blocked_State_Reconciliation_Static_Governance_Pass"
GATES = ["model_registry_required", "sha256_required", "non_git_model_path", "required_model_presence"]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def add(current: str, values: list[str]) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def update_csv(path: Path, key: str, expected: str, changes: dict[str, object]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames or [], list(reader)
    matched = 0
    for row in rows:
        if row.get(key) == expected:
            matched += 1
            for field, value in changes.items():
                if field in fields:
                    row[field] = add(row.get(field, ""), value) if isinstance(value, list) else str(value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return matched


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row007 Model Asset Storage And Cache Governance"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "model_asset_storage_cache.json"
    now = datetime.now(TZ)
    iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    source_path = PLAN / "02_TARGET_ARCHITECTURE/MODEL_ASSET_STORAGE_AND_CACHE_STRATEGY.md"
    contract_path = PLAN / "10_REGISTRIES/model_asset_storage_cache_contract.json"
    registry_path = PLAN / "Registries/Models/model_registry.jsonl"
    validation_path = PLAN / "Registries/Models/model_runtime_validation_queue.csv"
    governance_path = QA / "model_registry_governance.json"
    queue_path = PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    flux_candidates = sorted(
        (PLAN / "Instructions/QA/Evidence/Runtime_Readiness").glob(
            "W66_FLUX1_DEV_EXISTING_EXTERNAL_MODEL_PREFLIGHT_*.json"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not flux_candidates:
        raise SystemExit("missing current FLUX external-model preflight")
    flux_path = flux_candidates[0]
    realvis_path = PLAN / "Instructions/QA/Evidence/Model_Registry/W66_LOCAL_REALVISXL_MODEL_DOWNLOAD_20260706T204500-0500.json"
    gitignore_path = ROOT / ".gitignore"
    source, contract = source_path.read_text(encoding="utf-8-sig"), load(contract_path)
    registry = [json.loads(line) for line in registry_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    with validation_path.open("r", encoding="utf-8-sig", newline="") as handle:
        validation = list(csv.DictReader(handle))
    governance, queue, flux, realvis = load(governance_path), load(queue_path), load(flux_path), load(realvis_path)
    flux_model_record = flux["local_required_models"][0]
    flux_model_path = (ROOT / str(flux_model_record["existing_path"])).resolve()
    flux_model_exists = flux_model_path.is_file()
    flux_model_bytes = flux_model_path.stat().st_size if flux_model_exists else 0
    flux_model_sha256 = sha(flux_model_path) if flux_model_exists else ""
    flux_model_current_match = (
        flux_model_exists
        and flux_model_bytes == 17246524772
        and flux_model_sha256 == "8e91b68084b53a7fc44ed2a3756d821e355ac1a7b6fe29be760c1db532f3d88a"
    )
    gitignore = gitignore_path.read_text(encoding="utf-8-sig")
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    binary_exts = tuple(contract["rules"]["non_git_model_path"]["ignored_binary_extensions"])
    tracked_binaries = [path for path in tracked if path.lower().endswith(binary_exts)]
    status_counts = Counter(row["status"] for row in validation)
    queued = [row for row in validation if row["status"] == "queued"]
    registry_keys = Counter((row["workflow_lane"], row["local_path"]) for row in registry)
    declaration_pairs_match = all(registry_keys[(row["workflow_lane"], row["local_path"])] == 1 for row in validation)
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    inpaint_queue = [row for row in queued if row["workflow_lane"] == "sdxl_realvisxl_inpaint_detail_lane"]
    flux_queue = [row for row in queued if row["workflow_lane"] == "flux1_dev_primary_base"]
    checks = {
        "MSC-001_row007_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "MSC-002_source_contract_linked": rel(contract_path) in source and "## Fail-closed precedence" in source,
        "MSC-003_contract_schema_identity": contract["schema_version"] == "1.0" and contract["contract_id"] == "wave64_model_asset_storage_cache_contract" and contract["tracker_id"] == TRK,
        "MSC-004_gate_order_exact": contract["checks_required"] == GATES,
        "MSC-005_registry_exact_15": len(registry) == 15 and len({row["record_id"] for row in registry}) == 15,
        "MSC-006_validation_queue_exact_15": len(validation) == 15 and len({row["queue_id"] for row in validation}) == 15,
        "MSC-007_declaration_pairs_unique": declaration_pairs_match,
        "MSC-008_all_registry_hashes_valid": all(len(row.get("sha256", "")) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in row["sha256"]) for row in registry),
        "MSC-009_all_registry_paths_non_git": all(row.get("local_path", "").startswith("models/") and row["local_path"].lower().endswith(binary_exts) for row in registry),
        "MSC-010_all_queue_paths_non_git": all(row.get("local_path", "").startswith("models/") and row["local_path"].lower().endswith(binary_exts) for row in validation),
        "MSC-011_binary_ignore_policy_complete": all(f"*{ext}" in gitignore for ext in binary_exts),
        "MSC-012_zero_tracked_model_binaries": tracked_binaries == [],
        "MSC-013_governance_current_pass": governance["status"] == "Completed_Local_Model_Registry_Governance_Pass" and governance["coverage"]["registry_record_count"] == 15 and governance["coverage"]["runtime_validation_queue_row_count"] == 15 and governance["coverage"]["failed_check_count"] == 0,
        "MSC-014_status_distribution_exact": status_counts == {"runtime_smoke_complete": 8, "local_generation_smoke_complete": 5, "queued": 2},
        "MSC-015_realvis_local_hash_proven": realvis["result"] == "local_model_download_verified" and realvis["size_match"] is True and realvis["sha256_match"] is True and realvis["actual_sha256"] == realvis["expected_sha256"],
        "MSC-016_flux_registered_fail_closed": governance["flux_boundary"]["registered"] is True and governance["flux_boundary"]["license_acceptance_asserted"] is False and governance["flux_boundary"]["promotion_allowed"] is False,
        "MSC-017_flux_external_presence_and_hash_verified": len(flux_queue) == 1 and flux["lane_id"] == "flux1_dev_primary_base" and flux["result"] == "pass_local_gpu_generation_candidate" and flux["failed_check_count"] == 0 and flux["configured_extra_model_paths"]["status"] == "ready" and len(flux["local_required_models"]) == 1 and flux_model_record["filename"] == "flux1-dev-fp8.safetensors" and flux_model_record["exists_locally"] is True and flux_model_record["hash_match"] is True and flux_model_record["observed_sha256"] == "8e91b68084b53a7fc44ed2a3756d821e355ac1a7b6fe29be760c1db532f3d88a" and flux_model_current_match and flux["generation_executed"] is False and flux["comfyui_contacted"] is False and flux["ec2_started"] is False,
        "MSC-018_inpaint_declaration_proof_conflict_recorded": len(inpaint_queue) == 1 and "sdxl_realvisxl_inpaint_detail_lane" in queue["selection_policy"]["target_runtime_proof_present_lane_ids"] and contract["current_blockers"][0]["strict_state"] == "queued",
        "MSC-019_precedence_and_scope_fail_closed": contract["state_precedence_strictest_first"] == ["blocked", "missing", "queued", "local_validated", "target_runtime_validated"] and all(blocker["promotion_allowed"] is False for blocker in contract["current_blockers"]),
        "MSC-020_no_download_runtime_or_promotion": all(contract[key] is False for key in ("runtime_action_allowed", "model_download_allowed", "promotion_allowed", "full_project_completion_implied")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed model-storage invariants: " + ", ".join(failed))
    groups = {
        "model_registry_required": [name for name in checks if name.startswith(("MSC-001", "MSC-002", "MSC-003", "MSC-004", "MSC-005", "MSC-006", "MSC-007", "MSC-013"))],
        "sha256_required": [name for name in checks if name.startswith(("MSC-008", "MSC-015", "MSC-017"))],
        "non_git_model_path": [name for name in checks if name.startswith(("MSC-009", "MSC-010", "MSC-011", "MSC-012"))],
        "required_model_presence": [name for name in checks if name.startswith(("MSC-014", "MSC-016", "MSC-018", "MSC-019", "MSC-020"))],
    }
    stamped = QA / f"MODEL_ASSET_STORAGE_CACHE_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "model_asset_storage_cache_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-007_model_asset_storage_cache.json"
    blockers = contract["current_blockers"]
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": "static_model_storage_governance_pass_flux_external_presence_verified_inpaint_state_reconciliation_blocked",
        "validation_gates": {
            "model_registry_required": {"status": "pass", "checks": groups["model_registry_required"]},
            "sha256_required": {"status": "pass_policy_realvis_and_flux_external_hash_proof", "checks": groups["sha256_required"]},
            "non_git_model_path": {"status": "pass", "checks": groups["non_git_model_path"]},
            "required_model_presence": {"status": "blocked_one_declaration_proof_state_reconciliation", "checks": groups["required_model_presence"]},
        },
        "inventory": {"registry_records": len(registry), "validation_queue_rows": len(validation), "status_counts": dict(status_counts), "tracked_model_binary_count": 0},
        "bounded_presence_proof": {
            "realvisxl": {"model": "realvisxlV50_v50Bakedvae.safetensors", "local_hash_match": True},
            "flux1_dev": {
                "model": "flux1-dev-fp8.safetensors",
                "existing_path": flux["local_required_models"][0]["existing_path"],
                "local_hash_match": True,
                "current_file_rehashed_by_audit": True,
                "observed_bytes": flux_model_bytes,
                "observed_sha256": flux_model_sha256,
                "configured_external_path": True,
                "license_acceptance_asserted": False,
                "runtime_proof_present": False,
            },
            "scope": "local static model presence and exact hash only",
        },
        "blockers": blockers,
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"model_files_hashed_by_audit": True, "model_files_hashed_by_audit_scope": [str(flux_model_path)], "model_downloaded": False, "registry_modified": False, "validation_queue_modified": False, "aws_contacted": False, "ec2_started": False, "comfyui_contacted": False, "generation_executed": False, "promotion_executed": False, "mask_or_wave71_touched": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, contract_path, registry_path, validation_path, governance_path, queue_path, flux_path, realvis_path, gitignore_path)],
        "next_action": "Preserve the verified external FLUX bytes without copying or downloading; reconcile the remaining inpaint declaration/proof state independently, while keeping FLUX license and live-runtime gates fail-closed.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_static_governance_presence_blocked", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "inventory": payload["inventory"], "bounded_presence_proof": payload["bounded_presence_proof"], "blockers": blockers, "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})
    note = f"Wave64 Row007 {stamp}: 15 registry and 15 validation rows, all expected hashes/paths valid, zero tracked model binaries, bounded RealVisXL and configured-external FLUX hash proof, and 20/20 controls pass. FLUX is no longer missing; license/live-runtime gates remain fail-closed. Inpaint declaration/proof reconciliation remains the sole Row007 blocker."
    tags = ["wave64_row007_static_model_governance_pass", "zero_model_binaries_tracked", "flux_external_presence_hash_verified", "flux_license_runtime_still_fail_closed", "inpaint_state_reconciliation_blocked"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row007 Model Asset Storage And Cache Governance - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The direct contract verifies 15/15 registry-to-validation declarations, valid expected SHA256 values, non-Git model paths, complete binary ignore policy, zero tracked model binaries, bounded RealVisXL proof, and configured-external FLUX presence with the exact required SHA256. FLUX is not copied or downloaded; license acceptance and every live-runtime/promotion gate remain unproven. Inpaint declaration/proof reconciliation is the sole Row007 blocker. No broad model hashing, download, registry/queue mutation, AWS, EC2, ComfyUI, generation, mask, Jira, or Wave71+ action occurred.

Next safe local action: preserve existing FLUX bytes and reconcile the independent inpaint declaration/proof state only when that lane is intentionally selected.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "BLOCKERS.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and rel(stamped) in row.get("Evidence_Path", "") for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Reconciled configured-external FLUX model presence without copying or downloading bytes.", "; ".join(evidence_paths), "20/20 checks; 15/15 declarations; exact FLUX SHA256; one independent inpaint state blocker", payload["qa_decision"], rel(canonical), payload["next_action"]])
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": {gate: payload["validation_gates"][gate]["status"] for gate in GATES}, "inventory": payload["inventory"], "blockers": blockers, "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
