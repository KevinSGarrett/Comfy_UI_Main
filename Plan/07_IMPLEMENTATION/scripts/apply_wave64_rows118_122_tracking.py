from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


ITEMS_CSV = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv")
TRACKER_CSV = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv")
ITEMS_REQUIREMENTS = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json")
TRACKER_REQUIREMENTS = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json")
WORK_PACKAGE = Path("Plan/10_REGISTRIES/wave64_autonomous_hyperreal_speech_work_package_registry.json")
EVIDENCE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/W64_HYPERREAL_SPEECH_ROWS118_122_CONTROLS_20260715.json")
ROWS = range(118, 123)


class TrackingError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TrackingError(f"JSON root must be an object: {path}")
    return value


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise TrackingError(f"CSV header missing: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv_atomic(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_note(current: str, evidence_path: str) -> str:
    marker = f"Rows118-122 planning-control evidence: {evidence_path}"
    if marker in current:
        return current
    return f"{current.rstrip()} {marker}".strip()


def decision_map(evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    decisions = evidence.get("decisions")
    if not isinstance(decisions, dict):
        raise TrackingError("evidence decisions must be an object")
    expected = {f"TRK-W64-{row:03d}" for row in ROWS}
    if set(decisions) != expected:
        raise TrackingError("evidence must contain exactly Rows118-122 decisions")
    for tracker_id, decision in decisions.items():
        if not isinstance(decision, dict) or not str(decision.get("status", "")).strip():
            raise TrackingError(f"decision status missing for {tracker_id}")
    return decisions


def update_csvs(root: Path, decisions: dict[str, dict[str, Any]], evidence_path: str) -> None:
    item_fields, items = read_csv(root / ITEMS_CSV)
    tracker_fields, trackers = read_csv(root / TRACKER_CSV)
    for row in ROWS:
        item_id = f"ITEM-W64-{row:03d}"
        tracker_id = f"TRK-W64-{row:03d}"
        item_matches = [item for item in items if item.get("Item_ID") == item_id]
        tracker_matches = [item for item in trackers if item.get("Tracker_ID") == tracker_id]
        if len(item_matches) != 1 or len(tracker_matches) != 1:
            raise TrackingError(f"expected one Items/Tracker row for {tracker_id}")
        status = str(decisions[tracker_id]["status"])
        item_matches[0]["Status"] = status
        item_matches[0]["Notes"] = append_note(item_matches[0].get("Notes", ""), evidence_path)
        tracker_matches[0]["Status"] = status
        tracker_matches[0]["Status_Decision"] = status
        tracker_matches[0]["Notes"] = append_note(tracker_matches[0].get("Notes", ""), evidence_path)
    write_csv_atomic(root / ITEMS_CSV, item_fields, items)
    write_csv_atomic(root / TRACKER_CSV, tracker_fields, trackers)


def update_requirements(root: Path, decisions: dict[str, dict[str, Any]], evidence_path: str) -> None:
    value = load_json(root / ITEMS_REQUIREMENTS)
    for row in ROWS:
        tracker_id = f"TRK-W64-{row:03d}"
        matches = [item for item in value.get("requirements", []) if item.get("tracker_id") == tracker_id]
        if len(matches) != 1:
            raise TrackingError(f"expected one requirements row for {tracker_id}")
        matches[0]["status"] = decisions[tracker_id]["status"]
        matches[0]["decision_evidence"] = evidence_path
        matches[0]["remaining_blockers"] = list(decisions[tracker_id].get("blockers", []))
    value["status"] = "Implementation_Active_Rows113_115_117_119_122_PassLike_Rows116_118_Blocked"
    payload = json_bytes(value)
    write_bytes_atomic(root / ITEMS_REQUIREMENTS, payload)
    write_bytes_atomic(root / TRACKER_REQUIREMENTS, payload)


def update_work_package(root: Path, decisions: dict[str, dict[str, Any]], evidence_path: str) -> None:
    value = load_json(root / WORK_PACKAGE)
    for row in ROWS:
        tracker_id = f"TRK-W64-{row:03d}"
        matches = [item for item in value.get("work_packages", []) if item.get("tracker_id") == tracker_id]
        if len(matches) != 1:
            raise TrackingError(f"expected one work-package row for {tracker_id}")
        matches[0]["status"] = decisions[tracker_id]["status"]
        matches[0]["decision_evidence"] = evidence_path
    write_bytes_atomic(root / WORK_PACKAGE, json_bytes(value))


def mirror_evidence(root: Path) -> tuple[str, str]:
    source = root / EVIDENCE
    target = root / "Plan/Tracker/Evidence" / EVIDENCE.relative_to("Plan/Instructions/QA/Evidence")
    payload = source.read_bytes()
    write_bytes_atomic(target, payload)
    if sha256_file(source) != sha256_file(target):
        raise TrackingError("evidence mirror is not byte-identical")
    return EVIDENCE.as_posix(), target.relative_to(root).as_posix()


def apply(root: Path, out: Path) -> dict[str, Any]:
    evidence = load_json(root / EVIDENCE)
    if evidence.get("classification") != "W64_ROWS118_122_CONTROLS_PARTIAL_FAIL_CLOSED":
        raise TrackingError("Rows118-122 evidence classification is invalid")
    decisions = decision_map(evidence)
    evidence_path = EVIDENCE.as_posix()
    update_csvs(root, decisions, evidence_path)
    update_requirements(root, decisions, evidence_path)
    update_work_package(root, decisions, evidence_path)
    source, mirror = mirror_evidence(root)
    record = {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows118_122_tracking_reconciliation",
        "created_at": now_iso(),
        "classification": "W64_ROWS118_122_ITEMS_TRACKER_RECONCILED",
        "authority_evidence": {"path": evidence_path, "sha256": sha256_file(root / EVIDENCE)},
        "rows": decisions,
        "mirrors": {"instructions": source, "tracker": mirror, "byte_identical": True},
        "requirements_mirror_sha256": sha256_file(root / ITEMS_REQUIREMENTS),
        "boundaries": {"candidate_generated": False, "production_ready": False, "content_based_suppression": False},
    }
    write_bytes_atomic(out, json_bytes(record))
    tracker_out = root / "Plan/Tracker/Evidence" / out.relative_to(root / "Plan/Instructions/QA/Evidence")
    write_bytes_atomic(tracker_out, out.read_bytes())
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    out = args.out.resolve() if args.out.is_absolute() else (root / args.out).resolve()
    record = apply(root, out)
    print(json.dumps({"classification": record["classification"], "output": out.relative_to(root).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
