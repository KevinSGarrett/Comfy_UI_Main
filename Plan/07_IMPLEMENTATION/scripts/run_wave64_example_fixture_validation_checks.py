from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import jsonschema


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
EXAMPLE_ROOT = PLAN_ROOT / "09_EXAMPLES"
SCHEMA_ROOT = PLAN_ROOT / "08_SCHEMAS"
EXPECTATIONS_MANIFEST = EXAMPLE_ROOT / "EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
OUT_FILE = OUT_DIR / f"EXAMPLE_FIXTURE_VALIDATION_CHECKS_{STAMP}.json"

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
    "gate",
    "gates",
    "mask",
    "masks",
    "output",
    "output_artifacts",
    "outputs",
    "proof",
    "qa",
    "qa_goal",
    "qa_goals",
    "qa_gate",
    "qa_gates",
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
    "required_scales",
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
PATH_RE = re.compile(r"(?:C:\\Comfy_UI_Main\\Plan\\[^\s\"']+|Plan[/\\][^\s\"']+)")


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def list_files() -> list[Path]:
    return sorted(path for path in EXAMPLE_ROOT.rglob("*") if path.is_file())


def parse_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def parse_csv_file(path: Path) -> dict[str, Any]:
    result = {"path": rel(path), "parsed": False, "row_count": 0, "field_count": 0, "error": None}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            first = next(reader, None)
            if first is None:
                result["parsed"] = True
                return result
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


def walk_values(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, dict):
        for item in value.values():
            values.extend(walk_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(walk_values(item))
    return values


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


def schema_validate(path: Path, payload: Any) -> dict[str, Any]:
    schema_path = matching_schema_path(path)
    result = {
        "path": rel(path),
        "schema_found": schema_path is not None,
        "schema_path": rel(schema_path) if schema_path else None,
        "validated": False,
        "valid": None,
        "error": None,
    }
    if schema_path is None:
        return result
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
        jsonschema.validators.validator_for(schema).check_schema(schema)
        jsonschema.validate(payload, schema)
        result["validated"] = True
        result["valid"] = True
    except Exception as exc:
        result["validated"] = True
        result["valid"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def load_expectations_manifest() -> dict[str, Any]:
    if not EXPECTATIONS_MANIFEST.exists():
        return {}
    try:
        payload = json.loads(EXPECTATIONS_MANIFEST.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return {}
    by_path = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str):
            by_path[path] = entry
    return by_path


def normalize_path(raw: str) -> Path | None:
    cleaned = raw.strip().strip("`.,;:)(")
    if cleaned.startswith("Plan/") or cleaned.startswith("Plan\\"):
        return PROJECT_ROOT / cleaned.replace("/", "\\")
    if cleaned.startswith(r"C:\Comfy_UI_Main\Plan"):
        return Path(cleaned)
    return None


def stale_path_refs(path: Path, text: str) -> list[dict[str, Any]]:
    stale = []
    for match in PATH_RE.findall(text):
        candidate = normalize_path(match)
        if candidate is None:
            continue
        if not candidate.exists():
            stale.append({"source": rel(path), "reference": match, "resolved": str(candidate)})
    return stale


def has_expected_output_signal(path: Path, payload: Any, expectations: dict[str, Any]) -> bool:
    manifest_entry = expectations.get(rel(path))
    if isinstance(manifest_entry, dict) and manifest_entry.get("expected_output_defined") is True:
        return True
    name = path.name.lower()
    if "columns.csv" in name:
        return True
    keys = collect_keys(payload)
    if keys.intersection(QA_KEYS):
        return True
    if any(token in name for token in ["qa", "evidence", "report", "manifest", "request"]):
        return True
    return False


def main() -> int:
    expectations = load_expectations_manifest()
    files = list_files()
    json_files = [path for path in files if path.suffix.lower() == ".json"]
    csv_files = [path for path in files if path.suffix.lower() == ".csv"]
    other_files = [path for path in files if path.suffix.lower() not in {".json", ".csv"}]

    json_errors = []
    schema_results = []
    expected_output_gaps = []
    stale_refs = []
    parsed_json_count = 0
    schema_validated_count = 0
    schema_invalid = []
    for path in json_files:
        text = path.read_text(encoding="utf-8-sig")
        stale_refs.extend(stale_path_refs(path, text))
        payload, error = parse_json(path)
        if error:
            json_errors.append({"path": rel(path), "error": error})
            continue
        parsed_json_count += 1
        if not has_expected_output_signal(path, payload, expectations):
            expected_output_gaps.append({"path": rel(path), "reason": "no_qa_evidence_expected_output_signal"})
        schema_result = schema_validate(path, payload)
        schema_results.append(schema_result)
        if schema_result["validated"]:
            schema_validated_count += 1
        if schema_result["valid"] is False:
            schema_invalid.append(schema_result)

    csv_results = [parse_csv_file(path) for path in csv_files]
    csv_errors = [row for row in csv_results if not row["parsed"]]
    for path in csv_files:
        stale_refs.extend(stale_path_refs(path, path.read_text(encoding="utf-8-sig")))

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"EXAMPLE_FIXTURE_VALIDATION_CHECKS_{STAMP}",
        "created_iso": ISO_TS,
        "project_root": str(PROJECT_ROOT),
        "example_root": str(EXAMPLE_ROOT),
        "scope": {
            "fixture_parse": "Plan/09_EXAMPLES/**/*.json and *.csv",
            "example_request_valid": "JSON parse plus schema validation when a matching schema exists",
            "expected_output_defined": "QA/evidence/expected/result/report key or request/evidence/report/manifest filename signal",
            "expectations_manifest": rel(EXPECTATIONS_MANIFEST) if EXPECTATIONS_MANIFEST.exists() else None,
            "stale_example_scan": "Plan-relative and C:/Comfy_UI_Main/Plan path-like references",
            "ec2_contacted": False,
            "comfyui_contacted": False,
            "runtime_mutation": False,
        },
        "counts": {
            "files": len(files),
            "json_files": len(json_files),
            "json_parsed": parsed_json_count,
            "json_parse_errors": len(json_errors),
            "csv_files": len(csv_files),
            "csv_parse_errors": len(csv_errors),
            "other_files": len(other_files),
            "schema_validated_examples": schema_validated_count,
            "schema_invalid_examples": len(schema_invalid),
            "expected_output_gaps": len(expected_output_gaps),
            "expectations_manifest_entries": len(expectations),
            "stale_references": len(stale_refs),
        },
        "fixture_parse": {
            "pass": len(json_errors) == 0 and len(csv_errors) == 0,
            "json_errors": json_errors[:100],
            "csv_errors": csv_errors[:100],
            "csv_results": csv_results,
        },
        "example_request_valid": {
            "pass": len(schema_invalid) == 0,
            "schema_results": schema_results,
            "schema_invalid": schema_invalid[:100],
        },
        "expected_output_defined": {
            "pass": len(expected_output_gaps) == 0,
            "gaps": expected_output_gaps[:100],
        },
        "stale_example_scan": {
            "pass": len(stale_refs) == 0,
            "stale_references": stale_refs[:100],
        },
        "structured_report": {
            "pass": len(json_errors) == 0 and len(csv_errors) == 0 and len(schema_invalid) == 0 and len(expected_output_gaps) == 0 and len(stale_refs) == 0,
            "report_path": rel(OUT_FILE),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": rel(OUT_FILE),
        "pass": payload["structured_report"]["pass"],
        "counts": payload["counts"],
    }, indent=2))
    return 0 if payload["structured_report"]["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
