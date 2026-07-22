from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any, Callable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_blob_sha1(path: Path) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    size = path.stat().st_size
    digest.update(f"blob {size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_provider(repository: str, revision: str) -> dict[str, Any]:
    url = f"https://huggingface.co/api/models/{repository}/revision/{revision}?blobs=true"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def audit_snapshot(
    root: Path,
    repository: str,
    revision: str,
    provider_loader: Callable[[str, str], dict[str, Any]] = _load_provider,
) -> dict[str, Any]:
    root = root.resolve()
    provider = provider_loader(repository, revision)
    if provider.get("sha") != revision:
        raise ValueError("provider revision mismatch")
    expected = {item["rfilename"]: item for item in provider["siblings"]}
    actual = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    files: list[dict[str, Any]] = []
    for name, item in sorted(expected.items()):
        path = actual.get(name)
        record: dict[str, Any] = {"filename": name, "expected_bytes": item["size"], "present": path is not None}
        if path is not None:
            record["actual_bytes"] = path.stat().st_size
            if "lfs" in item:
                record.update(digest_type="sha256", expected_digest=item["lfs"]["sha256"], actual_digest=_sha256(path))
            else:
                record.update(digest_type="git_blob_sha1", expected_digest=item["blobId"], actual_digest=_git_blob_sha1(path))
            record["match"] = record["actual_bytes"] == record["expected_bytes"] and record["actual_digest"] == record["expected_digest"]
        else:
            record["match"] = False
        files.append(record)
    return {
        "schema_version": "wave64.hf_snapshot_storage_audit.v1",
        "repository": repository,
        "revision": revision,
        "license_metadata": provider.get("cardData", {}).get("license"),
        "root": str(root),
        "expected_files": len(expected),
        "actual_primary_files": len(actual),
        "extra_primary_files": sorted(set(actual) - set(expected)),
        "total_primary_bytes": sum(path.stat().st_size for path in actual.values()),
        "matching_files": sum(record["match"] for record in files),
        "mismatches": [record for record in files if not record["match"]],
        "files": files,
        "authority": {"storage_identity": all(record["match"] for record in files) and not set(actual) - set(expected), "model_load": False, "runtime": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    print(json.dumps(audit_snapshot(args.root, args.repository, args.revision), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
