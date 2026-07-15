#!/usr/bin/env python3
"""Install the exact ModelScope emotion2vec+ large payload into a local cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


MODEL_ID = "iic/emotion2vec_plus_large"
MODEL_REVISION = "v2.0.5"
TOKEN_REVISION = "767b2e00f04e0b75b5408c73be0d666328808af5"
EXPECTED_LICENSE = "Apache License 2.0"
MODEL_INFO_URL = f"https://www.modelscope.cn/api/v1/models/{MODEL_ID}"
FILE_API_URL = f"https://www.modelscope.cn/api/v1/models/{MODEL_ID}/repo/files"
RESOLVE_URL = f"https://www.modelscope.cn/models/{MODEL_ID}/resolve"
FILES = {
    "model.pt": {
        "revision": MODEL_REVISION,
        "sha256": "be501a01f26fcdc7663a062dff86af839afbaef7c4de32f5e42d7e1ad2784da4",
        "bytes": 1_945_790_254,
    },
    "config.yaml": {
        "revision": MODEL_REVISION,
        "sha256": "f4fa0eb82cc78bfebb43c56d68791afb01788085a18897d20999af7bc45d51d3",
        "bytes": 5_552,
    },
    "configuration.json": {
        "revision": MODEL_REVISION,
        "sha256": "8b6a745213025c7d4565f9f074cfef1b5cd5ef76e38e2a8f7f8a3db271e735b2",
        "bytes": 343,
    },
    "requirements.txt": {
        "revision": MODEL_REVISION,
        "sha256": "a6cfc40c2000a5eaa04ff73b46923df09112ec489082e84205ece2b8f788ddbc",
        "bytes": 43,
    },
    "tokens.txt": {
        "revision": TOKEN_REVISION,
        "sha256": "866121e470057b847d7a50e9923509141fb2924392f53385a186482a1ec0fb7f",
        "bytes": 119,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_url(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "ComfyUI-Main-Wave64/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("Code") != 200 or payload.get("Success") is not True:
        raise ValueError(f"ModelScope API did not return a successful object: {url}")
    return payload


def file_inventory(payload: dict) -> dict[str, dict]:
    files = payload.get("Data", {}).get("Files", [])
    if not isinstance(files, list):
        raise ValueError("ModelScope repository response has no Files array")
    return {str(item.get("Path")): item for item in files if isinstance(item, dict)}


def verify_remote_authority() -> dict:
    model_info = read_json_url(MODEL_INFO_URL)
    data = model_info.get("Data", {})
    if data.get("License") != EXPECTED_LICENSE:
        raise ValueError(
            f"ModelScope license mismatch: expected {EXPECTED_LICENSE!r}, got {data.get('License')!r}"
        )
    if data.get("Name") != "emotion2vec_plus_large" or data.get("Path") != "iic":
        raise ValueError("ModelScope model identity does not match iic/emotion2vec_plus_large")

    inventories = {}
    for revision in (MODEL_REVISION, TOKEN_REVISION):
        url = f"{FILE_API_URL}?Revision={revision}&Root="
        inventories[revision] = file_inventory(read_json_url(url))

    for name, expected in FILES.items():
        remote = inventories[expected["revision"]].get(name)
        if not remote:
            raise ValueError(f"ModelScope revision {expected['revision']} is missing {name}")
        if str(remote.get("Sha256", "")).lower() != expected["sha256"]:
            raise ValueError(f"ModelScope published SHA256 changed for {name}")
        if int(remote.get("Size", -1)) != expected["bytes"]:
            raise ValueError(f"ModelScope published byte size changed for {name}")

    return {
        "model_id": MODEL_ID,
        "license": data["License"],
        "license_source_url": MODEL_INFO_URL,
        "model_revision": MODEL_REVISION,
        "token_revision": TOKEN_REVISION,
        "modelscope_last_updated_time": data.get("LastUpdatedTime"),
        "modelscope_storage_size": data.get("StorageSize"),
    }


def verify_local(path: Path, expected: dict) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == expected["bytes"]
        and sha256(path) == expected["sha256"]
    )


def download(url: str, destination: Path, expected: dict) -> None:
    if verify_local(destination, expected):
        return
    partial = destination.with_suffix(destination.suffix + ".partial")
    if partial.exists() and partial.stat().st_size > expected["bytes"]:
        partial.unlink()

    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "ComfyUI-Main-Wave64/1.0"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        status = getattr(response, "status", 200)
        if offset and status != 206:
            offset = 0
            partial.unlink(missing_ok=True)
        mode = "ab" if offset else "wb"
        with partial.open(mode) as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)

    if partial.stat().st_size != expected["bytes"]:
        raise ValueError(f"Downloaded byte size mismatch for {destination.name}")
    actual = sha256(partial)
    if actual != expected["sha256"]:
        raise ValueError(f"Downloaded SHA256 mismatch for {destination.name}: {actual}")
    os.replace(partial, destination)


def build(cache_dir: Path) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)
    authority = verify_remote_authority()
    bindings = {}
    for name, expected in FILES.items():
        path = cache_dir / name
        url = f"{RESOLVE_URL}/{expected['revision']}/{name}"
        download(url, path, expected)
        bindings[name] = {
            "path": str(path.resolve()),
            "source_url": url,
            "revision": expected["revision"],
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }

    manifest = {
        "schema_version": "1.0",
        "classification": "W64_EMOTION2VEC_MODELSCOPE_INTAKE_PASS",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "authority": authority,
        "files": bindings,
        "runtime_contract": {
            "funasr_requirement": "funasr==1.0.27",
            "input_sample_rate_hz": 16_000,
            "model_classes": [
                "angry",
                "disgusted",
                "fearful",
                "happy",
                "neutral",
                "other",
                "sad",
                "surprised",
                "unknown",
            ],
        },
        "boundaries": {
            "model_payload_is_git_tracked": False,
            "model_execution_proves_emotion_authority": False,
            "cv3_calibration_required": True,
            "production_promotion_allowed": False,
        },
    }
    output = cache_dir / "model_intake_manifest.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    return {"manifest_path": str(output), "manifest_sha256": sha256(output), **manifest}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build(Path(args.cache_dir).resolve())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
