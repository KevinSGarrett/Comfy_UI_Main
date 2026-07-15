#!/usr/bin/env python3
"""Resolve and acquire a pinned speech-engine Hugging Face repository file set."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import manage_model_asset_acquisition as acquisition


ROOT = Path("C:/Comfy_UI_Main")
CATALOG = Path("Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json")
EXCLUDED_REPOSITORY_FILES = {".gitattributes", "README.md", "README.rst"}


class RepositoryAcquisitionError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RepositoryAcquisitionError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    acquisition.write_json_atomic(path, value)


def find_asset(catalog: dict[str, Any], asset_id: str) -> dict[str, Any]:
    matches = [item for item in catalog.get("official_asset_groups", []) if item.get("asset_id") == asset_id]
    if len(matches) != 1:
        raise RepositoryAcquisitionError(f"Expected one official asset entry for {asset_id}, found {len(matches)}")
    asset = matches[0]
    if asset.get("provider") != "huggingface":
        raise RepositoryAcquisitionError("Speech repository bundle currently requires an official Hugging Face asset")
    revision = str(asset.get("revision", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", revision):
        raise RepositoryAcquisitionError("Catalog asset does not bind an immutable revision")
    if asset.get("license") in {None, "", "unknown", "provider_custom_terms_verify_before_use"}:
        raise RepositoryAcquisitionError("Selected asset license is not cleared for this acquisition batch")
    return asset


def urlopen_bytes(url: str, timeout: int = 60) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers=acquisition.request_headers("huggingface"))
    with acquisition.open_url(request, timeout=timeout) as response:
        headers = {str(key): str(value) for key, value in response.headers.items()}
        return response.read(), headers


def fetch_repository_tree(repo_id: str, revision: str) -> list[dict[str, Any]]:
    quoted_repo = "/".join(urllib.parse.quote(part) for part in repo_id.split("/"))
    url = f"https://huggingface.co/api/models/{quoted_repo}/tree/{revision}?recursive=true&expand=true"
    payload, _ = urlopen_bytes(url)
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, list):
        raise RepositoryAcquisitionError("Hugging Face repository tree response is not an array")
    return [item for item in value if isinstance(item, dict)]


def raw_file_url(repo_id: str, revision: str, filename: str) -> str:
    quoted_repo = "/".join(urllib.parse.quote(part) for part in repo_id.split("/"))
    quoted_file = "/".join(urllib.parse.quote(part) for part in filename.split("/"))
    return f"https://huggingface.co/{quoted_repo}/resolve/{revision}/{quoted_file}"


def source_identity(
    repo_id: str,
    revision: str,
    item: dict[str, Any],
    small_file_fetcher: Callable[[str], tuple[bytes, dict[str, str]]],
) -> tuple[str, int, str]:
    filename = str(item.get("path", ""))
    size = int(item.get("size") or 0)
    if not filename or size < 1:
        raise RepositoryAcquisitionError(f"Repository file identity incomplete: {filename!r}")
    lfs = item.get("lfs") if isinstance(item.get("lfs"), dict) else {}
    oid = str(lfs.get("oid", "")).lower()
    if oid:
        if not re.fullmatch(r"[0-9a-f]{64}", oid):
            raise RepositoryAcquisitionError(f"Invalid LFS SHA-256 for {filename}")
        return oid, size, "huggingface_lfs_oid_sha256"
    if size > 16 * 1024 * 1024:
        raise RepositoryAcquisitionError(f"Large non-LFS file cannot be pre-hashed safely: {filename}")
    payload, _ = small_file_fetcher(raw_file_url(repo_id, revision, filename))
    if len(payload) != size:
        raise RepositoryAcquisitionError(f"Small-file byte count mismatch for {filename}: expected {size}, observed {len(payload)}")
    return hashlib.sha256(payload).hexdigest(), size, "downloaded_official_small_file_sha256"


def runtime_repository_files(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    files = []
    for item in tree:
        if item.get("type") != "file":
            continue
        path = str(item.get("path", ""))
        if path in EXCLUDED_REPOSITORY_FILES or Path(path).name in EXCLUDED_REPOSITORY_FILES:
            continue
        files.append(item)
    if not files:
        raise RepositoryAcquisitionError("Pinned repository has no runtime files")
    return sorted(files, key=lambda item: str(item.get("path", "")))


def request_for_file(asset: dict[str, Any], item: dict[str, Any], sha256: str, size: int) -> dict[str, Any]:
    asset_id = str(asset["asset_id"])
    repo_id = str(asset["repo_id"])
    revision = str(asset["revision"])
    source_path = str(item["path"])
    parent = Path(source_path).parent.as_posix()
    target_root = f"audio/tts/{asset_id}"
    target_subdir = target_root if parent == "." else f"{target_root}/{parent}"
    safe_id = re.sub(r"[^a-z0-9]+", "-", source_path.lower()).strip("-")
    return {
        "schema_version": "1.0",
        "request_id": f"w64-{asset_id}-{safe_id}",
        "capability_need": f"Pinned runtime file for Wave64 speech engine {asset_id}",
        "intended_use": "Rows113-117 isolated speech-engine acquisition and loader validation",
        "selection_rationale": "Official immutable repository selected by the Wave64 provider catalog; no rejected candidate is rerun.",
        "provider": "huggingface",
        "source": {
            "repo_id": repo_id,
            "revision": revision,
            "filename": source_path,
            "sha256": sha256,
            "bytes": size,
        },
        "asset": {
            "model_name": asset_id,
            "model_type": "audio_model",
            "base_model": str(asset.get("capability", "speech_engine")),
            "target_subdir": target_subdir,
            "filename": Path(source_path).name,
            "audio_impact": "new speech engine file; runtime and listening QA remain required",
        },
        "integration": {
            "workflow_lane": "wave64_hyperreal_speech_rows113_117",
            "compatible_engines": [asset_id],
            "model_role": f"speech_engine_repository_file:{source_path}",
            "expected_runtime_result": "load pinned repository in isolated environment; do not claim candidate or production readiness",
            "priority": 1,
        },
        "policy": {
            "license_status": "public_permissive",
            "license_id": str(asset["license"]),
            "license_url": f"https://huggingface.co/{repo_id}",
            "commercial_use_scope": "subject to recorded upstream license terms",
            "content_based_suppression": False,
            "adult_or_nsfw_metadata_is_not_a_filter": True,
            "allow_browser_fallback": False,
        },
    }


def prepare_bundle(
    root: Path,
    asset_id: str,
    output_dir: Path,
    tree_fetcher: Callable[[str, str], list[dict[str, Any]]] = fetch_repository_tree,
    small_file_fetcher: Callable[[str], tuple[bytes, dict[str, str]]] = urlopen_bytes,
) -> dict[str, Any]:
    catalog = load_json(root / CATALOG)
    asset = find_asset(catalog, asset_id)
    tree = runtime_repository_files(tree_fetcher(str(asset["repo_id"]), str(asset["revision"])))
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for item in tree:
        sha256, size, hash_source = source_identity(
            str(asset["repo_id"]), str(asset["revision"]), item, small_file_fetcher
        )
        request = request_for_file(asset, item, sha256, size)
        request_path = output_dir / "requests" / f"{request['request_id']}.json"
        manifest_path = output_dir / "manifests" / f"{request['request_id']}.json"
        write_json(request_path, request)
        manifest = acquisition.resolve_request(root, request)
        write_json(manifest_path, manifest)
        records.append(
            {
                "source_path": str(item["path"]),
                "sha256": sha256,
                "bytes": size,
                "hash_source": hash_source,
                "request_path": acquisition.relative_or_absolute(root, request_path),
                "manifest_path": acquisition.relative_or_absolute(root, manifest_path),
                "target_path": manifest["install"]["target_path"],
            }
        )
    bundle = {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_engine_repository_acquisition_bundle",
        "created_at": now_iso(),
        "classification": "HF_SPEECH_REPOSITORY_EXACT_FILE_SET_RESOLVED",
        "asset_id": asset_id,
        "repo_id": asset["repo_id"],
        "revision": asset["revision"],
        "license": asset["license"],
        "file_count": len(records),
        "total_bytes": sum(record["bytes"] for record in records),
        "files": records,
        "runtime_status": "not_acquired",
        "content_based_suppression": False,
    }
    write_json(output_dir / "bundle.json", bundle)
    return bundle


def acquire_bundle(root: Path, bundle_path: Path, object_info_url: str) -> dict[str, Any]:
    bundle = load_json(bundle_path)
    results = []
    for record in bundle.get("files", []):
        manifest_path = acquisition.project_path(root, record["manifest_path"])
        manifest = load_json(manifest_path)
        manifest["acquisition_method"] = "api"
        candidate = acquisition.download_to_staging(root, manifest)
        result = acquisition.finalize(root, manifest, candidate, False, object_info_url)
        results.append(
            {
                "source_path": record["source_path"],
                "target_path": result["destination_path"],
                "sha256": result["sha256"],
                "bytes": result["bytes"],
                "acquisition_method": result["acquisition_method"],
                "runtime_validation_status": result["runtime_validation_status"],
            }
        )
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_engine_repository_acquisition_result",
        "created_at": now_iso(),
        "classification": "HF_SPEECH_REPOSITORY_ACQUIRED_HASH_VERIFIED_RUNTIME_PENDING",
        "asset_id": bundle["asset_id"],
        "repo_id": bundle["repo_id"],
        "revision": bundle["revision"],
        "license": bundle["license"],
        "file_count": len(results),
        "files": results,
        "runtime_status": "queued_load_and_modality_qa",
        "production_ready": False,
        "content_based_suppression": False,
    }


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--asset-id", required=True)
    prepare.add_argument("--out-dir", type=Path, required=True)
    acquire = sub.add_parser("acquire")
    acquire.add_argument("--bundle", type=Path, required=True)
    acquire.add_argument("--out", type=Path, required=True)
    acquire.add_argument("--object-info-url", default=acquisition.DEFAULT_OBJECT_INFO)
    args = parser.parse_args()
    root = args.project_root.resolve()
    acquisition.load_env(root)
    try:
        if args.command == "prepare":
            output_dir = acquisition.project_path(root, args.out_dir)
            result = prepare_bundle(root, args.asset_id, output_dir)
            print(json.dumps({"classification": result["classification"], "bundle": acquisition.relative_or_absolute(root, output_dir / "bundle.json"), "file_count": result["file_count"], "total_bytes": result["total_bytes"]}, indent=2))
            return 0
        bundle_path = acquisition.project_path(root, args.bundle)
        result = acquire_bundle(root, bundle_path, args.object_info_url)
        output = acquisition.project_path(root, args.out)
        write_json(output, result)
        print(json.dumps({"classification": result["classification"], "output": acquisition.relative_or_absolute(root, output), "file_count": result["file_count"]}, indent=2))
        return 0
    except (RepositoryAcquisitionError, acquisition.AcquisitionError, OSError, ValueError, json.JSONDecodeError) as exc:
        classification = getattr(exc, "classification", "HF_SPEECH_REPOSITORY_ACQUISITION_FAILED")
        print(json.dumps({"classification": classification, "error": acquisition.redact(str(exc)), "secret_values_reported": False}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
