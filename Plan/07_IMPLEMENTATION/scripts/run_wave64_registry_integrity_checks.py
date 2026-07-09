from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
REGISTRY_ROOT = PLAN_ROOT / "10_REGISTRIES"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
OUT_FILE = OUT_DIR / f"REGISTRY_INTEGRITY_CHECKS_{STAMP}.json"

PATH_RE = re.compile(r"(?:C:\\Comfy_UI_Main\\Plan\\[^\s\"'<>|]+|Plan[/\\][^\s\"'<>|]+)")
ID_KEY_RE = re.compile(r"(^id$|_id$|_ids$|_key$|^key$)", re.IGNORECASE)
PATH_KEY_TOKENS = ("path", "file", "uri", "artifact", "evidence", "source")
STATUS_KEY_TOKENS = ("status", "state", "readiness")
STALE_STATUS_VALUES = {
    "stale",
    "deprecated",
    "obsolete",
    "unknown",
    "todo",
    "tbd",
    "missing",
    "not_current",
    "outdated",
}
ALWAYS_FOREIGN_ID_KEYS = {"cnr_id", "source_node_id", "target_node_id"}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def list_files() -> list[Path]:
    return sorted(path for path in REGISTRY_ROOT.rglob("*") if path.is_file())


def parse_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def parse_csv_file(path: Path) -> dict[str, Any]:
    result = {"path": rel(path), "parsed": False, "row_count": 0, "field_count": 0, "columns": [], "error": None}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            result["columns"] = reader.fieldnames or []
            result["field_count"] = len(result["columns"])
            rows = list(reader)
            result["row_count"] = len(rows)
            result["parsed"] = True
            return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def normalize_path(raw: str) -> Path | None:
    cleaned = raw.strip().strip("`.,;:)(")
    if cleaned.startswith("Plan/") or cleaned.startswith("Plan\\"):
        return PROJECT_ROOT / cleaned.replace("/", "\\")
    if cleaned.startswith(r"C:\Comfy_UI_Main\Plan"):
        return Path(cleaned)
    return None


def path_refs_from_text(path: Path, text: str) -> list[dict[str, Any]]:
    refs = []
    for match in PATH_RE.findall(text):
        candidate = normalize_path(match)
        if candidate is None:
            continue
        refs.append({"source": rel(path), "reference": match, "resolved": str(candidate), "exists": candidate.exists()})
    return refs


def walk(value: Any, trail: str = "$") -> list[tuple[str, Any]]:
    rows = [(trail, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            rows.extend(walk(item, f"{trail}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(walk(item, f"{trail}[{index}]"))
    return rows


def duplicate_ids_in_json(path: Path, payload: Any) -> list[dict[str, Any]]:
    duplicates = []

    def candidate_id_keys(keys: list[str]) -> list[str]:
        candidates = [key for key in keys if ID_KEY_RE.search(key) and not key.lower().endswith("_ids")]
        candidates = [key for key in candidates if key.lower() not in ALWAYS_FOREIGN_ID_KEYS]
        if "node_id" in [key.lower() for key in candidates] and len(candidates) > 1:
            candidates = [key for key in candidates if key.lower() != "node_id"]
        return candidates

    def inspect_list(items: list[Any], trail: str) -> None:
        values_by_key: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for key in candidate_id_keys([str(candidate) for candidate in item.keys()]):
                value = item.get(key)
                if value in (None, "") or isinstance(value, (dict, list)):
                    continue
                values_by_key[str(key)][str(value)].append(index)
        for key, values in values_by_key.items():
            for value, indexes in values.items():
                if len(indexes) > 1:
                    duplicates.append({
                        "path": rel(path),
                        "container": trail,
                        "id_key": key,
                        "id_value": value,
                        "indexes": indexes,
                    })

    def descend(value: Any, trail: str = "$") -> None:
        if isinstance(value, list):
            inspect_list(value, trail)
            for index, item in enumerate(value):
                descend(item, f"{trail}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                descend(item, f"{trail}.{key}")

    descend(payload)
    return duplicates


def duplicate_ids_in_csv(path: Path) -> list[dict[str, Any]]:
    duplicates = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        id_columns = [col for col in fieldnames if ID_KEY_RE.search(col) and not col.lower().endswith("_ids")]
        id_columns = [col for col in id_columns if col.lower() not in ALWAYS_FOREIGN_ID_KEYS]
        if any(col.lower() == "node_id" for col in id_columns) and len(id_columns) > 1:
            id_columns = [col for col in id_columns if col.lower() != "node_id"]
        if path.name.lower() != "main_flow_node_inventory.csv":
            id_columns = [col for col in id_columns if col.lower() != "node_id"]
        seen: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        for row_number, row in enumerate(reader, start=2):
            for col in id_columns:
                value = (row.get(col) or "").strip()
                if value:
                    seen[col][value].append(row_number)
    for col, values in seen.items():
        for value, rows in values.items():
            if len(rows) > 1:
                duplicates.append({"path": rel(path), "id_key": col, "id_value": value, "rows": rows[:25], "count": len(rows)})
    return duplicates


def stale_status_values(path: Path, payload: Any) -> list[dict[str, Any]]:
    stale = []
    def inspect(value: Any, trail: str = "$") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key).lower()
                child_trail = f"{trail}.{key}"
                if any(token in key_text for token in STATUS_KEY_TOKENS) and isinstance(item, str):
                    normalized = item.strip().lower()
                    if normalized in STALE_STATUS_VALUES:
                        stale.append({"path": rel(path), "location": child_trail, "value": item})
                inspect(item, child_trail)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                inspect(item, f"{trail}[{index}]")

    inspect(payload)
    return stale


def main() -> int:
    files = list_files()
    json_files = [path for path in files if path.suffix.lower() == ".json"]
    csv_files = [path for path in files if path.suffix.lower() == ".csv"]
    other_files = [path for path in files if path.suffix.lower() not in {".json", ".csv"}]

    json_errors = []
    csv_results = []
    csv_errors = []
    missing_refs = []
    duplicate_ids = []
    stale_status = []
    parsed_json_count = 0
    plan_path_ref_count = 0

    for path in json_files:
        text = path.read_text(encoding="utf-8-sig")
        refs = path_refs_from_text(path, text)
        plan_path_ref_count += len(refs)
        missing_refs.extend(ref for ref in refs if not ref["exists"])
        payload, error = parse_json(path)
        if error:
            json_errors.append({"path": rel(path), "error": error})
            continue
        parsed_json_count += 1
        duplicate_ids.extend(duplicate_ids_in_json(path, payload))
        stale_status.extend(stale_status_values(path, payload))

    for path in csv_files:
        text = path.read_text(encoding="utf-8-sig")
        refs = path_refs_from_text(path, text)
        plan_path_ref_count += len(refs)
        missing_refs.extend(ref for ref in refs if not ref["exists"])
        parsed = parse_csv_file(path)
        csv_results.append(parsed)
        if not parsed["parsed"]:
            csv_errors.append(parsed)
        else:
            duplicate_ids.extend(duplicate_ids_in_csv(path))

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"REGISTRY_INTEGRITY_CHECKS_{STAMP}",
        "created_iso": ISO_TS,
        "project_root": str(PROJECT_ROOT),
        "registry_root": str(REGISTRY_ROOT),
        "scope": {
            "unique_ids": "duplicate ID-like values are checked within JSON object lists and CSV ID-like columns",
            "cross_reference_check": "Plan-relative and C:/Comfy_UI_Main/Plan path-like references are extracted from registry text",
            "stale_status_scan": "status/state/readiness fields are scanned for explicitly stale values",
            "missing_file_check": "Plan-local path-like references must exist",
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
            "plan_path_references": plan_path_ref_count,
            "missing_plan_references": len(missing_refs),
            "duplicate_id_findings": len(duplicate_ids),
            "stale_status_findings": len(stale_status),
        },
        "parse_check": {
            "pass": len(json_errors) == 0 and len(csv_errors) == 0,
            "json_errors": json_errors[:100],
            "csv_errors": csv_errors[:100],
            "csv_results": csv_results,
        },
        "unique_ids": {
            "pass": len(duplicate_ids) == 0,
            "duplicate_ids": duplicate_ids[:100],
        },
        "cross_reference_check": {
            "pass": len(missing_refs) == 0,
            "missing_references": missing_refs[:100],
        },
        "stale_status_scan": {
            "pass": len(stale_status) == 0,
            "stale_status_values": stale_status[:100],
        },
        "missing_file_check": {
            "pass": len(missing_refs) == 0,
            "missing_references": missing_refs[:100],
        },
        "structured_report": {
            "pass": len(json_errors) == 0 and len(csv_errors) == 0 and len(duplicate_ids) == 0 and len(missing_refs) == 0 and len(stale_status) == 0,
            "report_path": rel(OUT_FILE),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": rel(OUT_FILE), "pass": payload["structured_report"]["pass"], "counts": payload["counts"]}, indent=2))
    return 0 if payload["structured_report"]["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
