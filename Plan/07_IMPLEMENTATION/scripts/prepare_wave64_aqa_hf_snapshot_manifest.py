#!/usr/bin/env python3
"""Prepare a pinned W64-AQA install admission from official Hugging Face metadata."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def fetch_metadata(repository_id: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(repository_id, safe="/")
    request = urllib.request.Request(
        f"https://huggingface.co/api/models/{encoded}?blobs=true",
        headers={"User-Agent": "Comfy-UI-Main-W64-AQA/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def build_manifest(
    metadata: dict[str, Any],
    expected_revision: str,
    package_id: str,
    target_root: str,
    minimum_free_bytes: int,
) -> dict[str, Any]:
    actual_revision = metadata.get("sha")
    if actual_revision != expected_revision:
        raise ValueError(f"upstream revision changed: {actual_revision} != {expected_revision}")
    files = []
    for sibling in metadata.get("siblings", []):
        lfs = sibling.get("lfs")
        if lfs:
            digest_kind = "sha256"
            digest = lfs["sha256"]
        else:
            digest_kind = "git_blob_sha1"
            digest = sibling["blobId"]
        files.append(
            {
                "path": sibling["rfilename"],
                "bytes": int(sibling["size"]),
                "identity_kind": digest_kind,
                "identity": digest,
            }
        )
    files.sort(key=lambda item: item["path"])
    return {
        "schema_version": "wave64.aqa.model_install_admission.v1",
        "program_id": "W64-AQA",
        "package_id": package_id,
        "status": "STORAGE_INSTALL_ADMITTED_EXECUTION_PENDING",
        "source": {
            "repository_id": metadata["id"],
            "revision": actual_revision,
            "license": metadata.get("cardData", {}).get("license"),
            "license_decision": "ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE",
            "license_basis": "official model-card metadata and repository LICENSE at the pinned revision",
            "source_url": f"https://huggingface.co/{metadata['id']}",
        },
        "storage": {
            "target_root": target_root,
            "minimum_free_bytes_before_install": minimum_free_bytes,
            "weight_bytes": sum(
                item["bytes"] for item in files if item["path"].endswith(".safetensors")
            ),
            "atomic_publish": True,
            "overwrite_forbidden": True,
        },
        "files": files,
        "authority": {
            "allowed": [
                "storage_preflight",
                "exact_revision_download",
                "file_identity_verification",
                "atomic_no_overwrite_publish",
                "installation_receipt",
            ],
            "forbidden": [
                "model_load",
                "inference",
                "gpu_probe",
                "lease_poll",
                "service_restart",
                "runtime_dependency_install",
                "role_activation",
                "tool_authorization",
                "product_approval",
                "promotion",
                "migration",
                "current_pod_stop",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--minimum-free-bytes", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(
        fetch_metadata(args.repository_id),
        args.revision,
        args.package_id,
        args.target_root,
        args.minimum_free_bytes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "repository_id": manifest["source"]["repository_id"],
                "revision": manifest["source"]["revision"],
                "file_count": len(manifest["files"]),
                "weight_bytes": manifest["storage"]["weight_bytes"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
