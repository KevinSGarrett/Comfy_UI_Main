from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
EXAMPLE_ROOT = PLAN_ROOT / "09_EXAMPLES"
SCHEMA_ROOT = PLAN_ROOT / "08_SCHEMAS"
OUT_FILE = EXAMPLE_ROOT / "EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()

QA_KEYS = {
    "acceptance",
    "acceptance_criteria",
    "allowed_passes",
    "artifact",
    "artifacts",
    "blocked",
    "criteria",
    "evidence",
    "evidence_refs",
    "expected",
    "expected_character_count",
    "expected_output",
    "expected_outputs",
    "forbidden_passes",
    "gate",
    "gates",
    "mask",
    "masks",
    "must_not_crop",
    "output",
    "output_artifacts",
    "outputs",
    "promotion_allowed",
    "proof",
    "qa",
    "qa_gate",
    "qa_gates",
    "qa_goal",
    "qa_goals",
    "qa_report",
    "qa_required",
    "qa_rule",
    "qa_rules",
    "qa_scores",
    "quality",
    "report",
    "required",
    "required_evidence",
    "required_masks",
    "required_patch_groups",
    "required_scales",
    "required_subjects_in_frame",
    "result",
    "results",
    "runtime",
    "runtime_verification_status",
    "score",
    "scores",
    "status",
    "validation",
    "validation_status",
}

ROLE_TOKENS = {
    "bible": "domain_bible_contract",
    "catalog": "catalog_contract",
    "columns": "columns_fixture_contract",
    "contract": "explicit_contract_fixture",
    "decision": "decision_fixture_contract",
    "entry": "entry_fixture_contract",
    "evidence": "evidence_fixture_contract",
    "handoff": "handoff_fixture_contract",
    "index": "index_fixture_contract",
    "ledger": "ledger_fixture_contract",
    "manifest": "manifest_fixture_contract",
    "plan": "plan_fixture_contract",
    "profile": "profile_fixture_contract",
    "registry": "registry_fixture_contract",
    "report": "report_fixture_contract",
    "request": "request_fixture_contract",
    "state": "state_fixture_contract",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def list_files() -> list[Path]:
    return sorted(path for path in EXAMPLE_ROOT.rglob("*") if path.is_file() and path != OUT_FILE)


def parse_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def parse_csv_file(path: Path) -> dict[str, Any]:
    result = {"parsed": False, "row_count": 0, "field_count": 0, "columns": [], "error": None}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            first = next(reader, None)
            if first is None:
                result["parsed"] = True
                return result
            result["columns"] = first
            result["field_count"] = len(first)
            row_count = 1
            for row_count, _ in enumerate(reader, start=2):
                pass
            result["row_count"] = row_count
            result["parsed"] = True
            return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key).lower())
            keys.update(collect_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(collect_keys(item))
    return keys


def matching_schema_path(path: Path) -> Path | None:
    name = path.name
    candidates = []
    if name.endswith(".example.json"):
        candidates.append(SCHEMA_ROOT / (name.removesuffix(".example.json") + ".schema.json"))
    if name.endswith(".request.json"):
        candidates.append(SCHEMA_ROOT / (name.removesuffix(".request.json") + ".schema.json"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def fixture_role(path: Path) -> tuple[str, str]:
    name = path.name.lower()
    for token, role in ROLE_TOKENS.items():
        if token in name:
            return role, f"filename_token:{token}"
    return "example_fixture_contract", "default_example_fixture"


def json_entry(path: Path) -> dict[str, Any]:
    payload, error = parse_json(path)
    schema_path = matching_schema_path(path)
    role, role_source = fixture_role(path)
    keys = collect_keys(payload) if error is None else set()
    embedded = sorted(keys.intersection(QA_KEYS))
    sources = []
    if embedded:
        sources.append("embedded_qa_or_output_fields")
    if schema_path:
        sources.append("matching_schema_contract")
    sources.append(role)
    return {
        "path": rel(path),
        "fixture_type": "json",
        "parse_expectation": "must_parse_as_json",
        "parsed_for_manifest": error is None,
        "parse_error": error,
        "schema_path": rel(schema_path) if schema_path else None,
        "expected_output_defined": error is None,
        "qa_expectation_sources": sources,
        "embedded_signal_keys": embedded,
        "role_source": role_source,
        "stale_reference_policy": "Plan-relative and C:/Comfy_UI_Main/Plan references must resolve locally",
    }


def csv_entry(path: Path) -> dict[str, Any]:
    parsed = parse_csv_file(path)
    return {
        "path": rel(path),
        "fixture_type": "csv",
        "parse_expectation": "must_parse_as_csv",
        "parsed_for_manifest": parsed["parsed"],
        "parse_error": parsed["error"],
        "schema_path": None,
        "expected_output_defined": parsed["parsed"] and parsed["field_count"] > 0,
        "qa_expectation_sources": ["columns_fixture_contract"],
        "field_count": parsed["field_count"],
        "row_count": parsed["row_count"],
        "columns": parsed["columns"],
        "stale_reference_policy": "Plan-relative and C:/Comfy_UI_Main/Plan references must resolve locally",
    }


def main() -> int:
    entries = []
    for path in list_files():
        suffix = path.suffix.lower()
        if suffix == ".json":
            entries.append(json_entry(path))
        elif suffix == ".csv":
            entries.append(csv_entry(path))
        else:
            role, role_source = fixture_role(path)
            entries.append({
                "path": rel(path),
                "fixture_type": suffix.lstrip(".") or "unknown",
                "parse_expectation": "tracked_non_json_non_csv_example_asset",
                "parsed_for_manifest": True,
                "parse_error": None,
                "schema_path": None,
                "expected_output_defined": True,
                "qa_expectation_sources": [role],
                "role_source": role_source,
                "stale_reference_policy": "Plan-relative and C:/Comfy_UI_Main/Plan references must resolve locally",
            })

    payload = {
        "schema_version": "1.0",
        "manifest_id": "WAVE64_EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST",
        "created_iso": ISO_TS,
        "project_root": str(PROJECT_ROOT),
        "example_root": str(EXAMPLE_ROOT),
        "purpose": "Explicitly ties each Plan/09_EXAMPLES fixture to parse, expected-output, QA expectation, and stale-reference validation policy for TRK-W64-053 / ITEM-W64-053.",
        "manual_gold_mask_boundary": "This manifest does not promote masks, consume candidate masks as truth, or certify mask readiness.",
        "counts": {
            "entries": len(entries),
            "expected_output_defined": sum(1 for entry in entries if entry["expected_output_defined"]),
            "parse_errors": sum(1 for entry in entries if entry["parse_error"]),
        },
        "entries": entries,
    }
    OUT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": rel(OUT_FILE), "counts": payload["counts"]}, indent=2))
    return 0 if payload["counts"]["parse_errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
