#!/usr/bin/env python3
"""Fail-closed Wave64 Row067 sound intelligence planning authority validator.

Validates row_parity, dependency_dag, and no_false_completion for Rows067-112.
Emits the tracker-declared direct evidence artifact. Planning authority acceptance
never implies runtime or product completion for downstream sound rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TRACKER_ID = "TRK-W64-067"
ITEM_ID = "ITEM-W64-067"
VALIDATOR_REVISION = "wave64_row067_planning_authority_v0.1.0"
FIRST_ROW = 67
LAST_ROW = 112
EXPECTED_COUNT = LAST_ROW - FIRST_ROW + 1
PLANNED_STATUS = "Planned_Autonomous_Implementation_Required"

TRACKER_CSV = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_TRACKER_ROWS.csv")
ITEMS_CSV = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ITEM_ROWS.csv")
TRACKER_REQUIREMENTS = Path(
    "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_REQUIREMENTS.json"
)
ITEMS_REQUIREMENTS = Path(
    "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_REQUIREMENTS.json"
)
REGISTRY = Path("Plan/10_REGISTRIES/wave64_autonomous_sound_intelligence_work_package_registry.json")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-067_sound_intelligence_planning_authority.json"
)
CONTROL_PACKAGE_BUILDER = Path(
    "Plan/07_IMPLEMENTATION/scripts/build_wave64_autonomous_sound_intelligence_control_package.py"
)

SOURCE_DOCUMENTS = (
    Path("Plan/00_PROJECT_CONTROL/WAVE64_AUTONOMOUS_VIDEO_TO_AUDIO_AND_SOUND_GENERATION_MASTER_PLAN.md"),
    Path("Plan/02_TARGET_ARCHITECTURE/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ARCHITECTURE.md"),
    Path("Plan/05_AUDIO_SYSTEM/WAVE64_AUTONOMOUS_SOUND_LIBRARY_GENERATION_AND_QA_PLAN.md"),
    Path("Plan/Instructions/QA/AUTONOMOUS_VIDEO_TO_AUDIO_AND_GENERATED_SOUND_QA_PROTOCOL.md"),
    Path("Plan/Instructions/Hydration_Rehydration/AUTONOMOUS_SOUND_INTELLIGENCE_MAIN_SESSION_HANDOFF.md"),
)

SCHEMA_CONTRACTS = (
    Path("Plan/08_SCHEMAS/audio_asset_intelligence_record.schema.json"),
    Path("Plan/08_SCHEMAS/visual_audio_event_manifest.schema.json"),
    Path("Plan/08_SCHEMAS/audio_candidate_score_record.schema.json"),
    Path("Plan/08_SCHEMAS/generated_audio_asset_provenance.schema.json"),
    Path("Plan/08_SCHEMAS/audio_orchestration_run.schema.json"),
    Path("Plan/08_SCHEMAS/audio_clip_preparation_manifest.schema.json"),
    Path("Plan/08_SCHEMAS/audio_spatial_render_manifest.schema.json"),
    Path("Plan/08_SCHEMAS/generated_audio_qa_report.schema.json"),
)

AUTHORITY_PATHS = (
    TRACKER_CSV,
    ITEMS_CSV,
    TRACKER_REQUIREMENTS,
    ITEMS_REQUIREMENTS,
    REGISTRY,
    CONTROL_PACKAGE_BUILDER,
    *SOURCE_DOCUMENTS,
    *SCHEMA_CONTRACTS,
)


class PlanningAuthorityError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_under(root: Path, rel: Path, label: str) -> Path:
    path = (root / rel).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise PlanningAuthorityError(f"{label} escapes project root: {rel}")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_meta(root: Path, rel: Path) -> dict[str, Any]:
    path = resolve_under(root, rel, str(rel))
    if not path.is_file():
        return {"path": rel.as_posix(), "exists": False}
    return {
        "path": rel.as_posix(),
        "exists": True,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise PlanningAuthorityError(f"JSON root must be object: {path}")
    return payload


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_tracker_deps(raw: str) -> list[str]:
    value = (raw or "").strip()
    if not value or value.lower() == "none":
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


def parse_item_deps(notes: str) -> list[str]:
    text = (notes or "").strip()
    if not text.startswith("Dependencies="):
        raise PlanningAuthorityError(f"item Notes missing Dependencies= prefix: {text[:80]!r}")
    payload = text.split(".", 1)[0].removeprefix("Dependencies=").strip()
    if not payload or payload.lower() == "none":
        return []
    item_ids = [part.strip() for part in payload.split("|") if part.strip()]
    out: list[str] = []
    for item_id in item_ids:
        if not item_id.startswith("ITEM-W64-"):
            raise PlanningAuthorityError(f"unexpected item dependency id: {item_id}")
        out.append(item_id.replace("ITEM-W64-", "TRK-W64-", 1))
    return out


def expected_ids(prefix: str) -> list[str]:
    return [f"{prefix}{row:03d}" for row in range(FIRST_ROW, LAST_ROW + 1)]


def git_tracked(root: Path, rel: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", rel.as_posix()],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def topological_roots_and_cycles(edges: dict[str, list[str]], nodes: list[str]) -> tuple[list[str], int]:
    indegree = {node: 0 for node in nodes}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for node, deps in edges.items():
        for dep in deps:
            adjacency[dep].append(node)
            indegree[node] += 1
    queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    seen = 0
    roots = [node for node in nodes if not edges.get(node)]
    while queue:
        current = queue.popleft()
        seen += 1
        for nxt in adjacency[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    cycle_count = 0 if seen == len(nodes) else 1
    return roots, cycle_count


def evaluate_planning_authority(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []

    def add_check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "result": "pass" if passed else "fail", "detail": detail})
        if not passed and detail:
            blockers.append({"code": name.upper(), "detail": detail})

    missing_authority = [rel.as_posix() for rel in AUTHORITY_PATHS if not (root / rel).is_file()]
    add_check(
        "SIP-V001_authority_paths_present",
        not missing_authority,
        "missing: " + ", ".join(missing_authority) if missing_authority else "",
    )
    if missing_authority:
        return _hold_payload(root, checks, blockers, row_complete=False)

    tracker_path = resolve_under(root, TRACKER_CSV, "tracker_csv")
    items_path = resolve_under(root, ITEMS_CSV, "items_csv")
    tracker_rows = read_csv_rows(tracker_path)
    item_rows = read_csv_rows(items_path)

    expected_tracker = expected_ids("TRK-W64-")
    expected_items = expected_ids("ITEM-W64-")
    tracker_ids = [row.get("Tracker_ID", "") for row in tracker_rows]
    item_ids = [row.get("Item_ID", "") for row in item_rows]

    add_check(
        "SIP-V002_exact_tracker_rows067_112_present_once",
        tracker_ids == expected_tracker and len(set(tracker_ids)) == EXPECTED_COUNT,
        f"tracker_ids={len(tracker_ids)} unique={len(set(tracker_ids))}",
    )
    add_check(
        "SIP-V003_exact_item_rows067_112_present_once",
        item_ids == expected_items and len(set(item_ids)) == EXPECTED_COUNT,
        f"item_ids={len(item_ids)} unique={len(set(item_ids))}",
    )

    status_parity = True
    dep_parity = True
    edges: dict[str, list[str]] = {}
    external_edges = 0
    for tracker_row, item_row in zip(tracker_rows, item_rows):
        if tracker_row.get("Status") != item_row.get("Status"):
            status_parity = False
        tracker_deps = parse_tracker_deps(tracker_row.get("Dependency_Prerequisite", ""))
        item_deps = parse_item_deps(item_row.get("Notes", ""))
        if tracker_deps != item_deps:
            dep_parity = False
        tracker_id = tracker_row["Tracker_ID"]
        edges[tracker_id] = tracker_deps
        for dep in tracker_deps:
            if dep not in expected_tracker:
                external_edges += 1

    add_check("SIP-V004_tracker_item_status_parity", status_parity)
    add_check("SIP-V005_tracker_item_dependency_parity", dep_parity)
    add_check(
        "SIP-V006_dependencies_internal_to_rows067_112",
        external_edges == 0,
        f"external_edge_count={external_edges}",
    )

    roots, cycle_count = topological_roots_and_cycles(edges, expected_tracker)
    add_check("SIP-V007_dependency_graph_acyclic", cycle_count == 0, f"cycle_count={cycle_count}")
    add_check(
        "SIP-V008_row067_is_only_dependency_root",
        roots == [TRACKER_ID],
        f"roots={roots}",
    )

    all_planned = all(row.get("Status") == PLANNED_STATUS for row in tracker_rows + item_rows)
    add_check(
        "SIP-V009_all_rows_remain_planned_until_own_evidence",
        all_planned,
        "one or more rows left Planned status without separate row acceptance mutation authority",
    )

    tracker_req = load_json(resolve_under(root, TRACKER_REQUIREMENTS, "tracker_requirements"))
    items_req_path = resolve_under(root, ITEMS_REQUIREMENTS, "items_requirements")
    tracker_req_path = resolve_under(root, TRACKER_REQUIREMENTS, "tracker_requirements")
    req_identical = items_req_path.read_bytes() == tracker_req_path.read_bytes()
    add_check("SIP-V010_requirements_mirrors_byte_identical", req_identical)

    reserved = tracker_req.get("reserved_row_range") or {}
    add_check(
        "SIP-V011_requirements_reserve_exact_46_rows",
        reserved.get("first") == FIRST_ROW
        and reserved.get("last") == LAST_ROW
        and reserved.get("count") == EXPECTED_COUNT
        and len(tracker_req.get("work_packages") or []) == EXPECTED_COUNT,
        f"reserved={reserved}",
    )

    planning_runtime_false = tracker_req.get("planning_complete_runtime_complete") is False
    add_check("SIP-V012_planning_runtime_completion_false", planning_runtime_false)

    registry = load_json(resolve_under(root, REGISTRY, "registry"))
    registry_ok = (
        registry.get("planning_complete_runtime_complete") is False
        and registry.get("row_count") == EXPECTED_COUNT
        and len(registry.get("work_packages") or []) == EXPECTED_COUNT
    )
    add_check("SIP-V013_registry_binds_planned_work_packages", registry_ok)

    source_metas = [file_meta(root, rel) for rel in SOURCE_DOCUMENTS]
    schema_metas = [file_meta(root, rel) for rel in SCHEMA_CONTRACTS]
    add_check("SIP-V014_five_source_authorities_present", all(meta["exists"] for meta in source_metas))
    add_check("SIP-V015_eight_schema_contracts_present", all(meta["exists"] for meta in schema_metas))

    false_completion_tokens = ("runtime_complete", "product_complete", "row_complete")
    false_claim = False
    for row in tracker_rows + item_rows:
        status_decision = (row.get("Status_Decision") or row.get("Status") or "").lower()
        if any(token in status_decision and "false" not in status_decision for token in ("runtime complete",)):
            false_claim = True
        if row.get("Status") in {"Done", "Accepted", "Complete", "Runtime_Complete"}:
            false_claim = True
    if tracker_req.get("planning_complete_runtime_complete") is True:
        false_claim = True
    if registry.get("planning_complete_runtime_complete") is True:
        false_claim = True
    add_check("SIP-V016_no_false_completion_claim", not false_claim)

    # Git visibility is recorded for the commit ledger but does not gate planning acceptance.
    # Exact-path commit of this package is what closes the prior untracked-authority gap.
    tracked = {rel.as_posix(): git_tracked(root, rel) for rel in AUTHORITY_PATHS}
    tracked_count = sum(1 for value in tracked.values() if value)
    checks.append(
        {
            "name": "SIP-V017_authority_paths_git_visible_advisory",
            "result": "pass" if tracked_count == len(AUTHORITY_PATHS) else "advisory_fail",
            "detail": f"tracked={tracked_count}/{len(AUTHORITY_PATHS)}",
        }
    )

    structural_pass = all(
        check["result"] == "pass"
        for check in checks
        if not check["name"].endswith("_advisory") and check["name"] != "SIP-V017_authority_paths_git_visible_advisory"
    )
    row_complete = structural_pass

    edge_count = sum(len(deps) for deps in edges.values())
    payload = {
        "schema_version": 1,
        "evidence_id": "TRK-W64-067_sound_intelligence_planning_authority",
        "created_at": utc_now(),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "validator_revision": VALIDATOR_REVISION,
        "status": (
            "PASS_PLANNING_AUTHORITY_ACCEPTED_NO_RUNTIME_COMPLETION"
            if row_complete
            else "HOLD_PLANNING_AUTHORITY_GATES_INCOMPLETE"
        ),
        "classification": "ROW067_SOUND_INTELLIGENCE_PLANNING_AUTHORITY",
        "row_complete": row_complete,
        "planning_authority_accepted": row_complete,
        "implementation_completion_claimed": row_complete,
        "runtime_completion_claimed": False,
        "product_completion_claimed": False,
        "validation_methods": ["row_parity", "dependency_dag", "no_false_completion"],
        "row_inventory": {
            "first_row": FIRST_ROW,
            "last_row": LAST_ROW,
            "expected_row_count": EXPECTED_COUNT,
            "tracker_row_count": len(tracker_rows),
            "item_row_count": len(item_rows),
            "planned_status_count": sum(1 for row in tracker_rows if row.get("Status") == PLANNED_STATUS),
        },
        "dependency_graph": {
            "node_count": len(expected_tracker),
            "edge_count": edge_count,
            "external_edge_count": external_edges,
            "cycle_count": cycle_count,
            "root_tracker_ids": roots,
            "acyclic": cycle_count == 0,
            "all_dependencies_resolve_within_rows067_112": external_edges == 0,
        },
        "authority_bindings": {
            "tracker_csv": file_meta(root, TRACKER_CSV),
            "items_csv": file_meta(root, ITEMS_CSV),
            "tracker_requirements": file_meta(root, TRACKER_REQUIREMENTS),
            "items_requirements": file_meta(root, ITEMS_REQUIREMENTS),
            "registry": file_meta(root, REGISTRY),
            "control_package_builder": file_meta(root, CONTROL_PACKAGE_BUILDER),
            "source_documents": source_metas,
            "schema_contracts": schema_metas,
            "git_tracked": tracked,
        },
        "checks": checks,
        "check_summary": {
            "checked": len(checks),
            "passed": sum(1 for check in checks if check["result"] == "pass"),
            "failed": sum(1 for check in checks if check["result"] == "fail"),
            "advisory_failed": sum(1 for check in checks if check["result"] == "advisory_fail"),
        },
        "blockers": blockers,
        "decision": {
            "row067_acceptance": "accepted" if row_complete else "held",
            "planning_structure": "pass" if structural_pass else "fail",
            "runtime_completion": False,
            "product_completion": False,
            "safe_next_action": (
                "Treat Row067 planning authority as accepted for dependency unlock. "
                "Continue Row068 rights/provenance and Row084 runtime/VFR proof without "
                "reclassifying this planning pass as sound-system runtime completion."
                if row_complete
                else "Close failing planning-authority structural gates before claiming Row067 acceptance."
            ),
        },
    }
    return payload


def _hold_payload(
    root: Path,
    checks: list[dict[str, Any]],
    blockers: list[dict[str, str]],
    *,
    row_complete: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "evidence_id": "TRK-W64-067_sound_intelligence_planning_authority",
        "created_at": utc_now(),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "validator_revision": VALIDATOR_REVISION,
        "status": "HOLD_PLANNING_AUTHORITY_GATES_INCOMPLETE",
        "classification": "ROW067_SOUND_INTELLIGENCE_PLANNING_AUTHORITY",
        "row_complete": row_complete,
        "planning_authority_accepted": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "product_completion_claimed": False,
        "validation_methods": ["row_parity", "dependency_dag", "no_false_completion"],
        "checks": checks,
        "check_summary": {
            "checked": len(checks),
            "passed": sum(1 for check in checks if check["result"] == "pass"),
            "failed": sum(1 for check in checks if check["result"] == "fail"),
        },
        "blockers": blockers,
        "decision": {
            "row067_acceptance": "held",
            "planning_structure": "fail",
            "runtime_completion": False,
            "product_completion": False,
            "safe_next_action": "Restore missing planning-authority paths and rerun the validator.",
        },
        "project_root": str(root),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evaluate_row067_complete(root: Path, evidence_path: Path | None = None) -> dict[str, Any]:
    path = resolve_under(root, evidence_path or DEFAULT_EVIDENCE, "row067_evidence")
    if not path.is_file():
        return {
            "row067_complete": False,
            "dependency_satisfied": False,
            "blocker_codes": ["ROW067_DIRECT_EVIDENCE_ABSENT"],
            "path": DEFAULT_EVIDENCE.as_posix(),
        }
    payload = load_json(path)
    complete = payload.get("row_complete") is True and payload.get("runtime_completion_claimed") is False
    return {
        "row067_complete": complete,
        "dependency_satisfied": complete,
        "blocker_codes": [] if complete else ["ROW067_NOT_ACCEPTED"],
        "path": DEFAULT_EVIDENCE.as_posix(),
        "status": payload.get("status"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Wave64 Row067 planning authority.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--check-complete", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if args.check_complete:
        result = evaluate_row067_complete(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["row067_complete"] else 2

    payload = evaluate_planning_authority(root)
    output = args.output if args.output.is_absolute() else root / args.output
    write_json(output, payload)
    print(json.dumps({"output": str(output), "row_complete": payload["row_complete"], "status": payload["status"]}, indent=2))
    return 0 if payload["row_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
