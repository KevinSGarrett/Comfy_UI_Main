from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import jsonschema
except Exception:  # pragma: no cover - recorded in evidence when absent.
    jsonschema = None


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
SCHEMA_ROOT = PLAN_ROOT / "08_SCHEMAS"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
OUT_FILE = OUT_DIR / f"SCHEMA_VALIDATION_CHECKS_{STAMP}.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def list_files(pattern: str) -> list[Path]:
    return sorted(path for path in PLAN_ROOT.rglob(pattern) if path.is_file())


def parse_json_file(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def parse_csv_file(path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "path": rel(path),
        "parsed": False,
        "row_count": 0,
        "field_count": 0,
        "fieldnames_present": False,
        "error": None,
    }
    try:
        with path.open("r", encoding="utf-8-sig", newline="", errors="strict") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(handle, dialect)
            first = next(reader, None)
            if first is None:
                result["parsed"] = True
                return result
            result["field_count"] = len(first)
            result["fieldnames_present"] = any(str(cell).strip() for cell in first)
            row_count = 1
            for row_count, _ in enumerate(reader, start=2):
                pass
            result["row_count"] = row_count
            result["parsed"] = True
            return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def validate_schema_file(path: Path, payload: object) -> dict[str, object]:
    is_legacy_descriptor = (
        isinstance(payload, dict)
        and isinstance(payload.get("schema_name"), str)
        and isinstance(payload.get("required_fields"), list)
    )
    result: dict[str, object] = {
        "path": rel(path),
        "schema_checked": False,
        "schema_valid": False,
        "schema_form": "legacy_required_fields_descriptor" if is_legacy_descriptor else "json_schema",
        "has_schema_uri": False,
        "declared_schema": None,
        "has_type_or_anyof": False,
        "has_properties_or_items": False,
        "has_legacy_required_fields": is_legacy_descriptor,
        "required_is_array_if_present": True,
        "error": None,
    }
    if not isinstance(payload, dict):
        result["error"] = "schema_root_not_object"
        return result

    result["has_schema_uri"] = "$schema" in payload
    result["declared_schema"] = payload.get("$schema")
    result["has_type_or_anyof"] = any(key in payload for key in ["type", "anyOf", "oneOf", "allOf", "$ref"])
    result["has_properties_or_items"] = any(key in payload for key in ["properties", "items", "anyOf", "oneOf", "allOf", "$ref"])
    result["required_is_array_if_present"] = "required" not in payload or isinstance(payload.get("required"), list)
    if is_legacy_descriptor:
        result["schema_checked"] = True
        result["schema_valid"] = True
        return result
    if jsonschema is None:
        result["error"] = "jsonschema_package_missing"
        return result

    try:
        validator_cls = jsonschema.validators.validator_for(payload)
        validator_cls.check_schema(payload)
        result["schema_checked"] = True
        result["schema_valid"] = True
    except Exception as exc:
        result["schema_checked"] = True
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    json_files = list_files("*.json")
    csv_files = list_files("*.csv")
    schema_files = sorted(path for path in SCHEMA_ROOT.rglob("*.schema.json") if path.is_file())

    json_errors = []
    parsed_json: dict[Path, object] = {}
    for path in json_files:
        payload, error = parse_json_file(path)
        if error:
            json_errors.append({"path": rel(path), "error": error})
        else:
            parsed_json[path] = payload

    csv_results = [parse_csv_file(path) for path in csv_files]
    csv_errors = [row for row in csv_results if not row["parsed"]]
    csv_header_gaps = [row for row in csv_results if row["parsed"] and not row["fieldnames_present"]]

    schema_results = []
    for path in schema_files:
        payload = parsed_json.get(path)
        if payload is None:
            schema_results.append({
                "path": rel(path),
                "schema_checked": False,
                "schema_valid": False,
                "error": "schema_json_parse_failed",
            })
            continue
        schema_results.append(validate_schema_file(path, payload))

    schema_errors = [row for row in schema_results if not row.get("schema_valid")]
    schema_required_field_gaps = [
        row
        for row in schema_results
        if row.get("schema_form") == "json_schema"
        and (
            not row.get("has_type_or_anyof")
            or not row.get("required_is_array_if_present")
            or not row.get("has_properties_or_items")
        )
    ]

    duplicate_schema_names = []
    seen_names: dict[str, str] = {}
    for path in schema_files:
        name = path.name
        if name in seen_names:
            duplicate_schema_names.append({"name": name, "first": seen_names[name], "second": rel(path)})
        else:
            seen_names[name] = rel(path)

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"SCHEMA_VALIDATION_CHECKS_{STAMP}",
        "created_iso": ISO_TS,
        "project_root": str(PROJECT_ROOT),
        "plan_root": str(PLAN_ROOT),
        "python": sys.version,
        "jsonschema_available": jsonschema is not None,
        "scope": {
            "json_glob": "Plan/**/*.json",
            "csv_glob": "Plan/**/*.csv",
            "schema_glob": "Plan/08_SCHEMAS/**/*.schema.json",
            "ec2_contacted": False,
            "comfyui_contacted": False,
            "runtime_mutation": False,
        },
        "counts": {
            "json_files": len(json_files),
            "json_parse_errors": len(json_errors),
            "csv_files": len(csv_files),
            "csv_parse_errors": len(csv_errors),
            "csv_header_gaps": len(csv_header_gaps),
            "schema_files": len(schema_files),
            "schema_errors": len(schema_errors),
            "schema_required_field_gaps": len(schema_required_field_gaps),
            "duplicate_schema_names": len(duplicate_schema_names),
        },
        "json_parse": {
            "pass": len(json_errors) == 0,
            "errors": json_errors[:100],
        },
        "csv_parse": {
            "pass": len(csv_errors) == 0 and len(csv_header_gaps) == 0,
            "errors": csv_errors[:100],
            "header_gaps": csv_header_gaps[:100],
            "largest_csv_files": sorted(
                [{"path": rel(path), "bytes": path.stat().st_size} for path in csv_files],
                key=lambda row: row["bytes"],
                reverse=True,
            )[:20],
        },
        "schema_required_fields": {
            "pass": len(schema_errors) == 0 and len(schema_required_field_gaps) == 0 and len(duplicate_schema_names) == 0,
            "schema_errors": schema_errors[:100],
            "schema_required_field_gaps": schema_required_field_gaps[:100],
            "duplicate_schema_names": duplicate_schema_names,
        },
        "structured_report": {
            "pass": len(json_errors) == 0
            and len(csv_errors) == 0
            and len(csv_header_gaps) == 0
            and len(schema_errors) == 0
            and len(schema_required_field_gaps) == 0
            and len(duplicate_schema_names) == 0,
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
