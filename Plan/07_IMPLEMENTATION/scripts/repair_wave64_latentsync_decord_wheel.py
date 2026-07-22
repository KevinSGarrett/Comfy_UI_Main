#!/usr/bin/env python3
"""Repair only the false internal Python tag in the admitted decord wheel."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import urllib.parse
import urllib.request
import zipfile


EXPECTED_ADMISSION_SHA256 = "72b269534e497270c846fddca7539e16aa9a57b58609ff0ca0113102cb758b5c"
EXPECTED_SOURCE_SHA256 = "51997f20be8958e23b7c4061ba45d0efcd86bffd5fe81c695d0befee0d442976"
EXPECTED_SOURCE_BYTES = 13602299
EXPECTED_ENTRY_COUNT = 70
EXPECTED_WHEEL_METADATA_SHA256 = "d24f09731316657ed32488ba245812cbb5047342b148776a371264e69966d856"
EXPECTED_BINARY_PATH = "decord/libdecord.so"
EXPECTED_BINARY_BYTES = 12465984
EXPECTED_BINARY_SHA256 = "98b260c5812106648ba299279916fbe98439893e346d4efdcf5cde66ba8973da"
WHEEL_PATH = "decord-0.6.0.dist-info/WHEEL"
RECORD_PATH = "decord-0.6.0.dist-info/RECORD"
OLD_TAG = b"Tag: cp36-cp36m-manylinux2010_x86_64"
NEW_TAG = b"Tag: py3-none-manylinux2010_x86_64"
OUTPUT_FILENAME = "decord-0.6.0-py3-none-manylinux2010_x86_64.whl"
ALLOWED_CHANGED_ENTRIES = {WHEEL_PATH, RECORD_PATH}
EXPECTED_RECORD_DEFECTS = [
    {
        "path": "decord-0.6.0.dist-info/top_level.txt",
        "record_hash": "sha256=8TBMC8W9caRfSBphoy47j2wFImKqCOgWKD3JVELo5e0",
        "record_bytes": 17,
        "actual_hash": "sha256=2gcXRGxvur2Z1iLmIE4fxL6cmywVZYD__8rzDGIEZDM",
        "actual_bytes": 7,
    }
]
RUNTIME_CLAIMS = {
    "package_installed": False,
    "package_imported": False,
    "project_code_imported": False,
    "model_loaded": False,
    "tensor_allocated": False,
    "gpu_or_lease_polled": False,
    "inference_performed": False,
    "service_changed": False,
    "role_activated": False,
    "product_authority": False,
}


class RepairError(RuntimeError):
    """A fail-closed wheel-repair error."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_digest(value: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode()


def safe_member_path(name: str) -> bool:
    pure = PurePosixPath(name)
    return bool(name) and not pure.is_absolute() and ".." not in pure.parts


def load_admission(path: Path) -> dict:
    if sha256_file(path) != EXPECTED_ADMISSION_SHA256:
        raise RepairError("admission hash mismatch")
    admission = json.loads(path.read_text(encoding="utf-8"))
    if admission.get("status") != "DECORD_WHEEL_METADATA_REPAIR_ADMITTED_EXECUTION_PENDING":
        raise RepairError("wheel repair is not admitted")
    authority = admission.get("authority", {})
    allowed_true = {
        "exact_wheel_download",
        "wheel_metadata_retag",
        "record_regeneration",
        "repaired_wheel_publish",
    }
    if any(authority.get(name) is not True for name in allowed_true):
        raise RepairError("required wheel repair authority missing")
    if any(value is not False for name, value in authority.items() if name not in allowed_true):
        raise RepairError("admission exceeds wheel repair authority")
    return admission


def validate_paths(admission: dict) -> tuple[Path, Path, Path]:
    target = Path(admission["targets"]["wheelhouse_root"])
    receipt = Path(admission["targets"]["receipt_path"])
    if not target.as_posix().startswith("/workspace/w64_aqa/wheelhouse/LatentSync-1.6/"):
        raise RepairError("unsafe repaired wheel target")
    if target.name != EXPECTED_SOURCE_SHA256:
        raise RepairError("repaired wheel target is not source-hash addressed")
    staging = target.with_name(f".{target.name}.repairing")
    if not receipt.as_posix().startswith("/workspace/w64_aqa/control/receipts/"):
        raise RepairError("unsafe repaired wheel receipt target")
    if any(path.is_symlink() for path in (target, staging, receipt)):
        raise RepairError("target, staging, or receipt path is a symlink")
    return target, staging, receipt


def download_source(admission: dict, destination: Path) -> dict:
    source = admission["source"]
    parsed = urllib.parse.urlparse(source["url"])
    if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org":
        raise RepairError("source wheel URL is outside the allowlist")
    request = urllib.request.Request(source["url"], headers={"User-Agent": "W64-AQA/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "files.pythonhosted.org":
            raise RepairError("source wheel redirect left the allowlist")
        with destination.open("xb") as handle:
            shutil.copyfileobj(response, handle)
    observed = {"bytes": destination.stat().st_size, "sha256": sha256_file(destination)}
    if observed != {"bytes": EXPECTED_SOURCE_BYTES, "sha256": EXPECTED_SOURCE_SHA256}:
        raise RepairError("source wheel hash or size mismatch")
    return {"url": source["url"], "filename": source["filename"], **observed}


def record_findings(contents: dict[str, bytes]) -> list[dict[str, str | int]]:
    rows = list(csv.reader(io.StringIO(contents[RECORD_PATH].decode("utf-8"))))
    file_names = {name for name in contents if not name.endswith("/")}
    if len(rows) != len(file_names):
        raise RepairError("wheel RECORD entry count mismatch")
    observed_names: set[str] = set()
    findings: list[dict[str, str | int]] = []
    for row in rows:
        if len(row) != 3 or row[0] in observed_names or row[0] not in contents:
            raise RepairError("wheel RECORD identity is malformed")
        observed_names.add(row[0])
        if row[0] == RECORD_PATH:
            if row[1:] != ["", ""]:
                raise RepairError("wheel RECORD self-entry must be unhashed")
        else:
            if not row[2].isdigit():
                raise RepairError(f"wheel RECORD size is malformed: {row[0]}")
            actual_hash = record_digest(contents[row[0]])
            actual_bytes = len(contents[row[0]])
            if row[1] != actual_hash or int(row[2]) != actual_bytes:
                findings.append(
                    {
                        "path": row[0],
                        "record_hash": row[1],
                        "record_bytes": int(row[2]),
                        "actual_hash": actual_hash,
                        "actual_bytes": actual_bytes,
                    }
                )
    if observed_names != file_names:
        raise RepairError("wheel RECORD does not cover every non-directory entry")
    return findings


def verify_record(contents: dict[str, bytes]) -> None:
    findings = record_findings(contents)
    if findings:
        raise RepairError(f"wheel RECORD hash or size mismatch: {findings}")


def inspect_source(
    path: Path,
) -> tuple[list[zipfile.ZipInfo], dict[str, bytes], list[dict[str, str | int]]]:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RepairError("source wheel ZIP integrity failed")
        infos = archive.infolist()
        if len(infos) != EXPECTED_ENTRY_COUNT or len({info.filename for info in infos}) != len(infos):
            raise RepairError("source wheel entry count or uniqueness mismatch")
        for info in infos:
            if not safe_member_path(info.filename):
                raise RepairError("unsafe source wheel path")
            if ((info.external_attr >> 16) & 0o170000) == stat.S_IFLNK:
                raise RepairError("source wheel symlink entry rejected")
        contents = {info.filename: archive.read(info.filename) for info in infos}
    wheel_metadata = contents.get(WHEEL_PATH, b"")
    if sha256_bytes(wheel_metadata) != EXPECTED_WHEEL_METADATA_SHA256:
        raise RepairError("source WHEEL metadata hash mismatch")
    if wheel_metadata.count(OLD_TAG) != 1 or NEW_TAG in wheel_metadata:
        raise RepairError("source WHEEL tag defect is not exact")
    binary_entries = [name for name in contents if name.endswith((".so", ".pyd"))]
    if binary_entries != [EXPECTED_BINARY_PATH]:
        raise RepairError("source wheel binary entry set mismatch")
    binary = contents[EXPECTED_BINARY_PATH]
    if len(binary) != EXPECTED_BINARY_BYTES or sha256_bytes(binary) != EXPECTED_BINARY_SHA256:
        raise RepairError("source wheel binary identity mismatch")
    record_defects = record_findings(contents)
    if record_defects != EXPECTED_RECORD_DEFECTS:
        raise RepairError("source wheel RECORD defect identity mismatch")
    return infos, contents, record_defects


def regenerate_record(contents: dict[str, bytes], original_record: bytes) -> bytes:
    rows = list(csv.reader(io.StringIO(original_record.decode("utf-8"))))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for row in rows:
        name = row[0]
        if name == RECORD_PATH:
            writer.writerow([name, "", ""])
        else:
            writer.writerow([name, record_digest(contents[name]), str(len(contents[name]))])
    return output.getvalue().encode("utf-8")


def write_repaired_wheel(
    destination: Path,
    infos: list[zipfile.ZipInfo],
    original_contents: dict[str, bytes],
) -> None:
    repaired = dict(original_contents)
    repaired[WHEEL_PATH] = repaired[WHEEL_PATH].replace(OLD_TAG, NEW_TAG)
    repaired[RECORD_PATH] = regenerate_record(repaired, original_contents[RECORD_PATH])
    with zipfile.ZipFile(destination, "x", allowZip64=True) as archive:
        for info in infos:
            archive.writestr(info, repaired[info.filename])


def inspect_repaired(source: Path, repaired: Path) -> dict:
    _, source_contents, _ = inspect_source(source)
    with zipfile.ZipFile(repaired) as archive:
        if archive.testzip() is not None:
            raise RepairError("repaired wheel ZIP integrity failed")
        infos = archive.infolist()
        repaired_contents = {info.filename: archive.read(info.filename) for info in infos}
    if set(source_contents) != set(repaired_contents):
        raise RepairError("repaired wheel entry identity set changed")
    changed = sorted(
        name for name in source_contents if source_contents[name] != repaired_contents[name]
    )
    if set(changed) != ALLOWED_CHANGED_ENTRIES:
        raise RepairError("repaired wheel changed an unauthorized entry")
    wheel_metadata = repaired_contents[WHEEL_PATH]
    if wheel_metadata.count(NEW_TAG) != 1 or OLD_TAG in wheel_metadata:
        raise RepairError("repaired WHEEL tag mismatch")
    verify_record(repaired_contents)
    return {
        "filename": repaired.name,
        "bytes": repaired.stat().st_size,
        "sha256": sha256_file(repaired),
        "entry_count": len(infos),
        "changed_entries": changed,
        "wheel_metadata_sha256": sha256_bytes(wheel_metadata),
        "binary_path": EXPECTED_BINARY_PATH,
        "binary_bytes": len(repaired_contents[EXPECTED_BINARY_PATH]),
        "binary_sha256": sha256_bytes(repaired_contents[EXPECTED_BINARY_PATH]),
        "record_integrity": "PASS",
    }


def tree_manifest(root: Path) -> dict:
    paths = list(root.iterdir())
    if len(paths) != 1 or not paths[0].is_file() or paths[0].is_symlink():
        raise RepairError("repaired wheelhouse must contain exactly one regular file")
    path = paths[0]
    payload = f"F\0{path.name}\0{path.stat().st_size}\0{sha256_file(path)}\n".encode()
    return {"sha256": hashlib.sha256(payload).hexdigest(), "file_count": 1, "total_bytes": path.stat().st_size}


def write_receipt_temp(path: Path, receipt: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.installing")
    if path.exists() or temporary.exists() or path.is_symlink() or temporary.is_symlink():
        raise RepairError("receipt target already exists")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def verify_replay(target: Path, receipt_path: Path) -> dict:
    if not target.is_dir() or not receipt_path.is_file():
        raise RepairError("partial prior wheel repair cannot be reused")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("wheelhouse_tree") != tree_manifest(target):
        raise RepairError("repaired wheelhouse tree does not match receipt")
    wheel = target / OUTPUT_FILENAME
    if receipt.get("repaired_wheel", {}).get("sha256") != sha256_file(wheel):
        raise RepairError("repaired wheel hash does not match receipt")
    return {"status": "REUSED_VERIFIED_REPAIRED_WHEEL", "receipt": str(receipt_path)}


def repair(admission_path: Path) -> dict:
    admission = load_admission(admission_path)
    target, staging, receipt_path = validate_paths(admission)
    if target.exists() or receipt_path.exists():
        return verify_replay(target, receipt_path)
    if staging.exists():
        raise RepairError("stale wheel-repair staging path requires independent disposition")
    receipt_temp: Path | None = None
    try:
        source_dir = staging / "source"
        output_dir = staging / "output"
        source_dir.mkdir(parents=True)
        output_dir.mkdir()
        source_path = source_dir / OUTPUT_FILENAME
        source_binding = download_source(admission, source_path)
        infos, contents, source_record_defects = inspect_source(source_path)
        repaired_path = output_dir / OUTPUT_FILENAME
        write_repaired_wheel(repaired_path, infos, contents)
        repaired_wheel = inspect_repaired(source_path, repaired_path)
        shutil.rmtree(source_dir)
        os.replace(repaired_path, staging / OUTPUT_FILENAME)
        output_dir.rmdir()
        wheelhouse_tree = tree_manifest(staging)
        receipt = {
            "schema_version": "wave64.aqa.latentsync_decord_wheel_repair_receipt.v1",
            "program_id": "W64-AQA",
            "package_id": "W64-AQA-PKG-LATENTSYNC-1.6",
            "status": "DECORD_WHEEL_METADATA_REPAIRED_HASHED_INSTALL_IMPORT_PENDING",
            "admission_commit": "c7ac27e0",
            "admission_sha256": EXPECTED_ADMISSION_SHA256,
            "source_wheel": source_binding,
            "observed_defect": {
                "filename_tag": "py3-none-manylinux2010_x86_64",
                "internal_tag": "cp36-cp36m-manylinux2010_x86_64",
                "record_defects": source_record_defects,
            },
            "prior_attempts": [
                {
                    "controller_commit": "60a488d0",
                    "result": "FAIL_CLOSED_BEFORE_WHEEL_PUBLICATION",
                    "reason": "source RECORD correctly omits twelve explicit ZIP directory entries; the first validator incorrectly compared RECORD rows with total ZIP entries",
                    "staging_removed": True,
                },
                {
                    "controller_commit": "ef5d752b",
                    "result": "FAIL_CLOSED_BEFORE_WHEEL_PUBLICATION",
                    "reason": "source RECORD has one upstream hash and size defect for top_level.txt; admission did not yet bind that defect",
                    "staging_removed": True,
                },
            ],
            "repair": {
                "replacement_internal_tag": "py3-none-manylinux2010_x86_64",
                "allowed_changed_entries": sorted(ALLOWED_CHANGED_ENTRIES),
            },
            "repaired_wheel": repaired_wheel,
            "wheelhouse_root": str(target),
            "wheelhouse_tree": wheelhouse_tree,
            "runtime_claims": RUNTIME_CLAIMS,
        }
        receipt_temp = write_receipt_temp(receipt_path, receipt)
        os.replace(staging, target)
        os.replace(receipt_temp, receipt_path)
        receipt_temp = None
        return {"status": "CREATED_VERIFIED_REPAIRED_WHEEL", "receipt": str(receipt_path)}
    except Exception:
        if receipt_temp and receipt_temp.exists() and not receipt_temp.is_symlink():
            receipt_temp.unlink()
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(repair(args.admission), sort_keys=True))
    except (RepairError, OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
