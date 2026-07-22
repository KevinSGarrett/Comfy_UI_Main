#!/usr/bin/env python3
"""Install one admitted W64-AQA model package without loading or activating it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


class InstallError(RuntimeError):
    pass


ADMITTED_PRODUCTION_MANIFESTS = {
    "e733f6863ecf6e3cd2d5579cd50c6e8cd35c78739316757633ad70c879edba60": {
        "repository_id": "Qwen/Qwen3-ASR-1.7B",
        "revision": "7278e1e70fe206f11671096ffdd38061171dd6e5",
    },
    "46d9695468fac6ff986a683b42df3e8872a01f9e16703ee0772ca4ba2136d480": {
        "repository_id": "Qwen/Qwen3-Omni-30B-A3B-Thinking",
        "revision": "2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b",
    },
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def file_identity(path: Path, kind: str) -> str:
    if kind == "sha256":
        digest = hashlib.sha256()
        prefix = b""
    elif kind == "git_blob_sha1":
        digest = hashlib.sha1()  # noqa: S324 - Git blob identity is explicitly SHA-1.
        prefix = f"blob {path.stat().st_size}\0".encode("ascii")
    else:
        raise InstallError(f"unsupported identity kind: {kind}")
    digest.update(prefix)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise InstallError(f"missing, non-file, or symlink source: {record['path']}")
    size = path.stat().st_size
    expected_size = record.get("bytes")
    if expected_size is not None and size != expected_size:
        raise InstallError(f"byte count mismatch: {record['path']}")
    observed = file_identity(path, record["identity_kind"])
    if observed != record["identity"]:
        raise InstallError(f"content identity mismatch: {record['path']}")
    return {
        "path": record["path"],
        "bytes": size,
        "identity_kind": record["identity_kind"],
        "identity": observed,
    }


def _download(url: str, destination: Path, *, attempts: int = 3) -> None:
    if destination.exists():
        return
    partial = destination.with_name(destination.name + ".part")
    for attempt in range(1, attempts + 1):
        offset = partial.stat().st_size if partial.is_file() else 0
        request = urllib.request.Request(url, headers={"User-Agent": "Comfy-UI-Main-W64-AQA/1"})
        if offset:
            request.add_header("Range", f"bytes={offset}-")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - exact HTTPS source is manifest-bound.
                append = offset > 0 and getattr(response, "status", None) == 206
                mode = "ab" if append else "wb"
                with partial.open(mode) as handle:
                    while True:
                        chunk = response.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
            os.replace(partial, destination)
            return
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            if attempt == attempts:
                raise InstallError(f"download failed after {attempts} attempts: {destination.name}") from exc
            time.sleep(attempt)


def _nearest_existing(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        if candidate.parent == candidate:
            raise InstallError("no existing storage ancestor")
        candidate = candidate.parent
    return candidate


def _verify_manifest_shape(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != "wave64.aqa.model_install_admission.v1":
        raise InstallError("manifest schema mismatch")
    if manifest.get("status") != "STORAGE_INSTALL_ADMITTED_EXECUTION_PENDING":
        raise InstallError("manifest is not admitted for storage installation")
    source = manifest.get("source", {})
    identity = (source.get("repository_id"), source.get("revision"))
    admitted_identities = {
        (item["repository_id"], item["revision"])
        for item in ADMITTED_PRODUCTION_MANIFESTS.values()
    }
    if identity not in admitted_identities:
        raise InstallError("repository or revision is not admitted")
    forbidden = set(manifest.get("authority", {}).get("forbidden", []))
    for action in ("model_load", "inference", "gpu_probe", "lease_poll", "role_activation"):
        if action not in forbidden:
            raise InstallError(f"manifest does not forbid {action}")


def install(
    manifest: dict[str, Any],
    target: Path,
    *,
    fetch: Callable[[str, Path], None] = _download,
    free_bytes: int | None = None,
    production_target: bool = True,
    crash_after_files: int | None = None,
    download_workers: int = 1,
) -> dict[str, Any]:
    _verify_manifest_shape(manifest)
    if download_workers < 1 or download_workers > 8:
        raise InstallError("download_workers must be between 1 and 8")
    if download_workers > 1 and crash_after_files is not None:
        raise InstallError("crash injection requires serial download mode")
    declared_target = manifest["storage"]["target_root"]
    if production_target:
        manifest_hash = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
        admitted = ADMITTED_PRODUCTION_MANIFESTS.get(manifest_hash)
        if admitted is None:
            raise InstallError("production admission manifest identity mismatch")
        source = manifest["source"]
        if source.get("repository_id") != admitted["repository_id"]:
            raise InstallError("production repository identity mismatch")
        if source.get("revision") != admitted["revision"]:
            raise InstallError("production revision identity mismatch")
        if target.as_posix() != declared_target:
            raise InstallError("CLI target differs from admitted target")
        if not target.as_posix().startswith("/workspace/w64_aqa/models/"):
            raise InstallError("production target escaped admitted durable root")
    ancestor = _nearest_existing(target.parent)
    available = free_bytes if free_bytes is not None else shutil.disk_usage(ancestor).free
    if available < manifest["storage"]["minimum_free_bytes_before_install"]:
        raise InstallError("insufficient free space for admitted installation")

    manifest_hash = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    receipt_name = ".w64_aqa_install_receipt.json"
    if target.exists():
        receipt_path = target / receipt_name
        if not target.is_dir() or target.is_symlink() or not receipt_path.is_file():
            raise InstallError("target exists without a valid installation receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("manifest_sha256") != manifest_hash:
            raise InstallError("existing target receipt manifest mismatch")
        verified = [verify_file(target / record["path"], record) for record in manifest["files"]]
        if receipt.get("files") != verified:
            raise InstallError("existing target receipt file inventory mismatch")
        return {**receipt, "replay": "REUSED_VERIFIED_INSTALL"}

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.installing"
    if staging.exists() and (not staging.is_dir() or staging.is_symlink()):
        raise InstallError("unsafe staging path")
    staging.mkdir(exist_ok=True)

    source = manifest["source"]
    base = f"https://huggingface.co/{source['repository_id']}/resolve/{source['revision']}"
    def fetch_and_verify(record: dict[str, Any]) -> dict[str, Any]:
        relative = Path(record["path"])
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            try:
                return verify_file(destination, record)
            except InstallError:
                destination.unlink()
        quoted = "/".join(urllib.parse.quote(part) for part in record["path"].split("/"))
        fetch(f"{base}/{quoted}", destination)
        return verify_file(destination, record)

    records = manifest["files"]
    if download_workers == 1:
        verified_files = []
        for completed, record in enumerate(records, start=1):
            verified_files.append(fetch_and_verify(record))
            if crash_after_files is not None and completed == crash_after_files:
                raise InstallError("injected crash after verified file")
    else:
        with ThreadPoolExecutor(max_workers=download_workers) as executor:
            verified_files = list(executor.map(fetch_and_verify, records))

    expected_names = {record["path"] for record in manifest["files"]}
    observed_names = {
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file() and not path.name.endswith(".part") and path.name != receipt_name
    }
    if observed_names != expected_names:
        raise InstallError("staging contains an unexpected or missing file")
    if any(path.is_symlink() for path in staging.rglob("*")):
        raise InstallError("staging contains a symlink")

    receipt = {
        "schema_version": "wave64.aqa.model_install_receipt.v1",
        "program_id": "W64-AQA",
        "package_id": manifest["package_id"],
        "status": "INSTALLED_BYTES_VERIFIED_NOT_LOADED_OR_ACTIVATED",
        "manifest_sha256": manifest_hash,
        "source_revision": source["revision"],
        "target_root": declared_target,
        "files": verified_files,
        "runtime_claims": {
            "model_loaded": False,
            "inference_performed": False,
            "gpu_or_lease_polled": False,
            "role_activated": False,
            "product_authority": False,
        },
    }
    receipt_path = staging / receipt_name
    if receipt_path.exists():
        raise InstallError("staging receipt already exists")
    with receipt_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(staging, target)
    return {**receipt, "replay": "NEW_ATOMIC_INSTALL"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--download-workers", type=int, default=1)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    target = Path(manifest["storage"]["target_root"])
    try:
        result = install(manifest, target, download_workers=args.download_workers)
    except (InstallError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
