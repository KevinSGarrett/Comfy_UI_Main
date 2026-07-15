#!/usr/bin/env python3
"""Acquire, install, register, and wire exact model assets without exposing secrets."""

from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from email.message import Message
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("C:/Comfy_UI_Main")
CONTROL_REGISTRY = Path("Plan/10_REGISTRIES/model_acquisition_control_registry.json")
MODEL_REGISTRY = Path("Plan/Registries/Models/model_registry.jsonl")
RUNTIME_QUEUE = Path("Plan/Registries/Models/model_runtime_validation_queue.csv")
DEFAULT_OBJECT_INFO = "http://127.0.0.1:8188/object_info"
SECRET_KEYS = ("CIVITAI_API_TOKEN", "CIVITAI_TOKEN", "CIVITAI_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")
ALLOWED_LICENSE_STATES = {"verified_allowed", "public_permissive", "user_accepted", "source_terms_recorded"}
SAFE_EXTENSIONS = {
    ".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx",
    ".json", ".yaml", ".yml", ".txt", ".png", ".jpg", ".jpeg", ".webp",
    ".wav", ".flac", ".mp3", ".mp4", ".mkv", ".zip",
}
LEGACY_MODEL_ROOTS = (Path("C:/Comfy_UI/models"), Path("C:/Comfy_UI/Runtime_Data/models"))
HF_CACHE_ROOT = Path.home() / ".cache" / "huggingface" / "hub"


class AcquisitionError(RuntimeError):
    def __init__(self, classification: str, message: str) -> None:
        super().__init__(message)
        self.classification = classification


class CredentialSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep credentials on same-host redirects and strip them on CDN redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        old_host = urllib.parse.urlparse(req.full_url).hostname
        new_host = urllib.parse.urlparse(newurl).hostname
        if old_host and new_host and old_host.lower() != new_host.lower():
            redirected.remove_header("Authorization")
            redirected.unredirected_hdrs.pop("Authorization", None)
        return redirected


def open_url(request: urllib.request.Request | str, timeout: int):
    return urllib.request.build_opener(CredentialSafeRedirectHandler()).open(request, timeout=timeout)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise AcquisitionError("INVALID_JSON_ROOT", f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_env(project_root: Path) -> list[str]:
    env_path = project_root / ".env"
    loaded: list[str] = []
    if not env_path.is_file():
        return loaded
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            continue
        if name not in os.environ:
            os.environ[name] = value.strip().strip('"').strip("'")
        loaded.append(name)
    return loaded


def secret_for(provider: str) -> str:
    keys = (
        ("CIVITAI_API_TOKEN", "CIVITAI_TOKEN", "CIVITAI_API_KEY")
        if provider == "civitai"
        else ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")
    )
    for key in keys:
        if os.environ.get(key):
            return os.environ[key]
    return ""


def redact(text: str) -> str:
    result = text
    for key in SECRET_KEYS:
        value = os.environ.get(key, "")
        if value:
            result = result.replace(value, "[REDACTED]")
    result = re.sub(r"([?&](?:token|api[_-]?key)=)[^&\s]+", r"\1[REDACTED]", result, flags=re.I)
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@contextmanager
def acquisition_update_lock(root: Path):
    lock_path = root / "runtime_artifacts" / "model_acquisition" / "model_registry_update.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise AcquisitionError(
            "MODEL_ACQUISITION_UPDATE_LOCKED",
            f"Another acquisition finalization owns {relative_or_absolute(root, lock_path)}",
        ) from exc
    try:
        os.write(descriptor, json.dumps({"pid": os.getpid(), "created_at": now_iso()}).encode("utf-8"))
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def relative_or_absolute(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def logical_install_path(manifest: dict[str, Any]) -> str:
    subdir = Path(str(manifest["install"]["target_subdir"]))
    filename = Path(str(manifest["install"]["local_filename"]))
    if subdir.is_absolute() or ".." in subdir.parts or filename.name != str(filename):
        raise AcquisitionError("INVALID_INSTALL_PATH", "Install target must remain under the logical models root")
    return (Path("models") / subdir / filename).as_posix()


def require_request(request: dict[str, Any]) -> None:
    for field in ("request_id", "capability_need", "provider", "source", "asset", "integration", "policy"):
        if field not in request:
            raise AcquisitionError("INVALID_ACQUISITION_REQUEST", f"Missing request field: {field}")
    provider = str(request["provider"]).lower()
    if provider not in {"civitai", "huggingface"}:
        raise AcquisitionError("UNSUPPORTED_PROVIDER", f"Unsupported provider: {provider}")
    if request["policy"].get("content_based_suppression") is not False:
        raise AcquisitionError("CONTENT_SUPPRESSION_POLICY_DRIFT", "content_based_suppression must be false")
    if request["policy"].get("license_status") not in ALLOWED_LICENSE_STATES:
        raise AcquisitionError("BLOCKED_LICENSE_OR_ACCESS_TERMS", "License/access state is not recorded as allowed")
    target_subdir = str(request["asset"].get("target_subdir", ""))
    if not target_subdir or Path(target_subdir).is_absolute() or ".." in Path(target_subdir).parts:
        raise AcquisitionError("INVALID_TARGET_SUBDIR", "asset.target_subdir must be a relative ComfyUI model folder")
    if provider == "civitai" and not request["source"].get("model_version_id"):
        raise AcquisitionError("CIVITAI_VERSION_REQUIRED", "Exact Civitai model_version_id is required")
    if provider == "huggingface":
        for field in ("repo_id", "revision", "filename", "sha256"):
            if not request["source"].get(field):
                raise AcquisitionError("HUGGINGFACE_EXACT_FILE_REQUIRED", f"Hugging Face source.{field} is required")
        if not re.fullmatch(r"[a-fA-F0-9]{40,64}", str(request["source"]["revision"])):
            raise AcquisitionError("HUGGINGFACE_IMMUTABLE_REVISION_REQUIRED", "Hugging Face revision must be an immutable commit hash")


def request_headers(provider: str) -> dict[str, str]:
    headers = {"User-Agent": os.environ.get("CIVITAI_USER_AGENT", "ComfyUIMainAssetAcquisition/1.0")}
    token = secret_for(provider)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_json(url: str, provider: str, timeout: int = 60) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=request_headers(provider))
    try:
        with open_url(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        classification = "BROWSER_DOWNLOAD_REQUIRED" if exc.code in {401, 403, 404} else "SOURCE_METADATA_REQUEST_FAILED"
        raise AcquisitionError(classification, f"Metadata request returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AcquisitionError("SOURCE_METADATA_REQUEST_FAILED", redact(str(exc))) from exc
    if not isinstance(payload, dict):
        raise AcquisitionError("SOURCE_METADATA_INVALID", "Source metadata root is not an object")
    return payload


def select_civitai_file(metadata: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    files = [item for item in metadata.get("files", []) if isinstance(item, dict)]
    file_id = str(source.get("file_id", ""))
    filename = str(source.get("filename", ""))
    if file_id:
        matches = [item for item in files if str(item.get("id", "")) == file_id]
    elif filename:
        matches = [item for item in files if str(item.get("name", "")).lower() == filename.lower()]
    else:
        matches = [item for item in files if item.get("primary") is True]
        if not matches and len(files) == 1:
            matches = files
    if len(matches) != 1:
        raise AcquisitionError("CIVITAI_FILE_SELECTION_AMBIGUOUS", f"Expected one exact Civitai file, found {len(matches)}")
    return matches[0]


def discover_civitai(query: str, types: str, limit: int, base_model: str = "") -> dict[str, Any]:
    parameters = {
        "query": query,
        "types": types,
        "limit": max(1, min(limit, 100)),
        "primaryFileOnly": "false",
    }
    url = "https://civitai.com/api/v1/models?" + urllib.parse.urlencode(parameters)
    payload = fetch_json(url, "civitai")
    candidates: list[dict[str, Any]] = []
    wanted_base = base_model.strip().lower()
    for model in payload.get("items", []):
        if not isinstance(model, dict):
            continue
        for version in model.get("modelVersions", []):
            if not isinstance(version, dict):
                continue
            version_base = str(version.get("baseModel", ""))
            if wanted_base and wanted_base not in version_base.lower():
                continue
            files = []
            for item in version.get("files", []):
                if not isinstance(item, dict):
                    continue
                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                hashes = item.get("hashes") if isinstance(item.get("hashes"), dict) else {}
                files.append(
                    {
                        "file_id": str(item.get("id", "")),
                        "filename": str(item.get("name", "")),
                        "file_type": str(item.get("type", "")),
                        "primary": bool(item.get("primary", False)),
                        "format": metadata.get("format"),
                        "size": metadata.get("size"),
                        "precision": metadata.get("fp"),
                        "sha256": str(hashes.get("SHA256", "")).lower(),
                        "size_kb": item.get("sizeKB"),
                        "pickle_scan_result": item.get("pickleScanResult"),
                        "virus_scan_result": item.get("virusScanResult"),
                    }
                )
            candidates.append(
                {
                    "model_id": str(model.get("id", "")),
                    "model_name": str(model.get("name", "")),
                    "model_type": str(model.get("type", "")),
                    "creator": str((model.get("creator") or {}).get("username", "")),
                    "nsfw_metadata": model.get("nsfw"),
                    "tags": model.get("tags") or [],
                    "model_version_id": str(version.get("id", "")),
                    "version_name": str(version.get("name", "")),
                    "base_model": version_base,
                    "trained_words": version.get("trainedWords") or [],
                    "files": files,
                }
            )
    return {
        "schema_version": "1.0",
        "created_at": now_iso(),
        "classification": "CIVITAI_DISCOVERY_CANDIDATES_RESOLVED",
        "query": query,
        "types": types,
        "base_model_filter": base_model,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "content_based_suppression": False,
        "adult_or_nsfw_metadata_used_as_filter": False,
        "selection_automated": False,
        "next_action": "Select one technically compatible exact model version and file ID, then create a schema-valid acquisition request.",
    }


def resolve_request(root: Path, request: dict[str, Any], metadata_override: Path | None = None) -> dict[str, Any]:
    require_request(request)
    control = load_json(root / CONTROL_REGISTRY)
    placement = control.get("placement_map", {})
    model_type = str(request["asset"]["model_type"])
    target_subdir = str(request["asset"]["target_subdir"]).replace("\\", "/").strip("/")
    expected_subdir = str(placement.get(model_type, "")).strip("/")
    if expected_subdir and not (target_subdir == expected_subdir or target_subdir.startswith(expected_subdir + "/")):
        raise AcquisitionError(
            "MODEL_PLACEMENT_MAP_MISMATCH",
            f"{model_type} assets must be placed under {expected_subdir}, not {target_subdir}",
        )
    provider = str(request["provider"]).lower()
    source = request["source"]
    metadata: dict[str, Any]
    selected: dict[str, Any]
    if provider == "civitai":
        version_id = str(source["model_version_id"])
        metadata_url = f"https://civitai.com/api/v1/model-versions/{urllib.parse.quote(version_id)}"
        metadata = load_json(metadata_override) if metadata_override else fetch_json(metadata_url, provider)
        selected = select_civitai_file(metadata, source)
        hashes = {str(key).upper(): str(value).lower() for key, value in (selected.get("hashes") or {}).items()}
        download_url = str(selected.get("downloadUrl") or metadata.get("downloadUrl") or f"https://civitai.com/api/download/models/{version_id}")
        file_metadata = selected.get("metadata") if isinstance(selected.get("metadata"), dict) else {}
        selectors = {
            "type": selected.get("type"),
            "format": file_metadata.get("format"),
            "size": file_metadata.get("size"),
            "fp": file_metadata.get("fp"),
        }
        query = urllib.parse.urlencode({key: value for key, value in selectors.items() if value})
        if query and not selected.get("downloadUrl"):
            download_url += ("&" if "?" in download_url else "?") + query
        filename = str(selected.get("name") or source.get("filename") or "")
        expected_sha256 = hashes.get("SHA256", "")
        expected_bytes = selected.get("sizeBytes")
        page_url = f"https://civitai.com/models/{metadata.get('modelId')}?modelVersionId={version_id}"
        source_identity = {
            "model_id": str(metadata.get("modelId", "")),
            "model_version_id": version_id,
            "file_id": str(selected.get("id", "")),
            "version_name": str(metadata.get("name", "")),
            "base_model": str(metadata.get("baseModel", "")),
            "trained_words": metadata.get("trainedWords") or [],
            "source_hashes": hashes,
        }
    else:
        repo_id = str(source["repo_id"])
        revision = str(source["revision"])
        filename = str(source["filename"])
        quoted_repo = "/".join(urllib.parse.quote(part) for part in repo_id.split("/"))
        quoted_file = "/".join(urllib.parse.quote(part) for part in filename.split("/"))
        download_url = f"https://huggingface.co/{quoted_repo}/resolve/{urllib.parse.quote(revision, safe='')}/{quoted_file}"
        page_url = f"https://huggingface.co/{quoted_repo}/blob/{urllib.parse.quote(revision, safe='')}/{quoted_file}"
        metadata = load_json(metadata_override) if metadata_override else {}
        expected_sha256 = str(source.get("sha256", "")).lower()
        expected_bytes = source.get("bytes")
        source_identity = {
            "repo_id": repo_id,
            "revision": revision,
            "file_path": filename,
            "source_hashes": {"SHA256": expected_sha256} if expected_sha256 else {},
        }

    if not expected_sha256 or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256):
        raise AcquisitionError("SOURCE_SHA256_REQUIRED", "Exact source SHA256 is required before acquisition")
    local_name = str(request["asset"].get("filename") or Path(filename).name)
    if not local_name or Path(local_name).suffix.lower() not in SAFE_EXTENSIONS:
        raise AcquisitionError("UNSUPPORTED_OR_UNSAFE_FILE_TYPE", f"Unsupported asset filename: {local_name}")
    target_subdir = Path(str(request["asset"]["target_subdir"]))
    if target_subdir.is_absolute() or ".." in target_subdir.parts:
        raise AcquisitionError("INVALID_INSTALL_PATH", "Model target_subdir must remain under the logical models root")
    target = Path("models") / target_subdir / local_name
    return {
        "schema_version": "1.0",
        "manifest_id": f"ACQ-{request['request_id']}",
        "created_at": now_iso(),
        "state": "resolved_not_downloaded",
        "request": request,
        "provider": provider,
        "source_identity": source_identity,
        "source_metadata": {
            "download_url": download_url,
            "page_url": page_url,
            "filename": filename,
            "expected_sha256": expected_sha256,
            "expected_bytes": expected_bytes,
            "metadata_snapshot": metadata,
        },
        "install": {
            "target_path": target.as_posix(),
            "target_subdir": str(request["asset"]["target_subdir"]),
            "local_filename": local_name,
        },
        "security": {
            "credential_source": ".env_or_process_environment",
            "credential_serialized": False,
            "browser_cookie_exported": False,
            "content_based_suppression": False,
        },
    }


def content_disposition_filename(headers: Message) -> str:
    disposition = headers.get("Content-Disposition", "")
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", disposition, flags=re.I)
    return urllib.parse.unquote(match.group(1).strip()) if match else ""


def ephemeral_token_url(url: str, token: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, value) for key, value in query if key.lower() != "token"]
    query.append(("token", token))
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment))


def stream_download_once(url: str, headers: dict[str, str], partial: Path, timeout: int) -> None:
    existing = partial.stat().st_size if partial.exists() else 0
    current_headers = dict(headers)
    if existing:
        current_headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=current_headers)
    with open_url(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        content_type = str(response.headers.get("Content-Type", "")).lower()
        if "text/html" in content_type:
            raise AcquisitionError("BROWSER_DOWNLOAD_REQUIRED", "Download returned an HTML/login response")
        mode = "ab" if existing and status == 206 else "wb"
        reported_name = content_disposition_filename(response.headers)
        if reported_name and Path(reported_name).suffix.lower() not in SAFE_EXTENSIONS:
            raise AcquisitionError("UNSUPPORTED_OR_UNSAFE_FILE_TYPE", f"Unsafe source filename: {reported_name}")
        with partial.open(mode) as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)


def download_to_staging(root: Path, manifest: dict[str, Any]) -> Path:
    provider = manifest["provider"]
    url = str(manifest["source_metadata"]["download_url"])
    staging = root / "Models_Staging" / provider / "downloads" / manifest["manifest_id"]
    staging.mkdir(parents=True, exist_ok=True)
    final_name = manifest["install"]["local_filename"]
    reusable = find_reusable_candidate(root, manifest)
    if reusable is not None:
        manifest["reused_existing_path"] = relative_or_absolute(root, reusable)
        manifest["acquisition_method"] = "local_exact_hash_reuse"
        return reusable
    partial = staging / f"{final_name}.part"
    if partial.is_file():
        expected_sha = str(manifest["source_metadata"].get("expected_sha256") or "").lower()
        expected_bytes = manifest["source_metadata"].get("expected_bytes")
        size_matches = expected_bytes is None or partial.stat().st_size == int(expected_bytes)
        if expected_sha and size_matches and sha256_file(partial) == expected_sha:
            manifest["acquisition_method"] = "resumed_complete_staging_file"
            return partial
    headers = request_headers(provider)
    timeout = int(os.environ.get("CIVITAI_TIMEOUT_SECONDS", "120"))
    attempts = [(url, headers, False)]
    token = secret_for(provider)
    if provider == "civitai" and token:
        query_headers = {key: value for key, value in headers.items() if key.lower() != "authorization"}
        attempts.append((ephemeral_token_url(url, token), query_headers, True))
    last_error: Exception | None = None
    try:
        for attempt_index, (attempt_url, attempt_headers, query_token_used) in enumerate(attempts):
            try:
                stream_download_once(attempt_url, attempt_headers, partial, timeout)
                if query_token_used:
                    manifest["ephemeral_token_query_retry_used"] = True
                last_error = None
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if attempt_index + 1 < len(attempts) and exc.code in {401, 403}:
                    continue
                raise
            except AcquisitionError as exc:
                last_error = exc
                if attempt_index + 1 < len(attempts) and exc.classification == "BROWSER_DOWNLOAD_REQUIRED":
                    continue
                raise
        if last_error is not None:
            raise last_error
    except urllib.error.HTTPError as exc:
        classification = "BROWSER_DOWNLOAD_REQUIRED" if exc.code in {401, 403, 404} else "MODEL_DOWNLOAD_FAILED"
        raise AcquisitionError(classification, f"Download returned HTTP {exc.code}; partial bytes preserved") from exc
    except urllib.error.URLError as exc:
        raise AcquisitionError("MODEL_DOWNLOAD_FAILED", f"Download failed; partial bytes preserved: {redact(str(exc))}") from exc
    if not partial.is_file() or partial.stat().st_size < 1:
        raise AcquisitionError("MODEL_DOWNLOAD_EMPTY", "Downloaded file is empty")
    return partial


def read_registry(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AcquisitionError("MODEL_REGISTRY_INVALID", f"Invalid JSONL at line {line_number}") from exc
        if not isinstance(value, dict):
            raise AcquisitionError("MODEL_REGISTRY_INVALID", f"Non-object JSONL row at line {line_number}")
        records.append(value)
    return records


def find_reusable_candidate(root: Path, manifest: dict[str, Any]) -> Path | None:
    expected_sha = str(manifest["source_metadata"].get("expected_sha256") or "").lower()
    if not expected_sha:
        return None
    subdir = str(manifest["install"]["target_subdir"])
    filename = str(manifest["install"]["local_filename"])
    candidates = [
        project_path(root, manifest["install"]["target_path"]),
        root / "ComfyUI" / "models" / subdir / filename,
    ]
    candidates.extend(model_root / subdir / filename for model_root in LEGACY_MODEL_ROOTS)
    identity = manifest.get("source_identity", {})
    repo_id = str(identity.get("repo_id", "")).strip()
    revision = str(identity.get("revision", "")).strip()
    file_path = str(identity.get("file_path", "")).strip()
    if repo_id and revision and file_path:
        repo_cache_name = "models--" + repo_id.replace("/", "--")
        candidates.append(HF_CACHE_ROOT / repo_cache_name / "snapshots" / revision / file_path)
    for record in read_registry(root / MODEL_REGISTRY):
        if str(record.get("sha256", "")).lower() != expected_sha:
            continue
        local_path = str(record.get("local_path", "")).strip()
        if local_path:
            candidates.append(project_path(root, local_path))
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        if sha256_file(resolved) == expected_sha:
            return resolved
    return None


def verify_candidate(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    actual_sha = sha256_file(path)
    actual_bytes = path.stat().st_size
    expected_sha = str(manifest["source_metadata"].get("expected_sha256") or "").lower()
    expected_bytes = manifest["source_metadata"].get("expected_bytes")
    if expected_sha and actual_sha != expected_sha:
        raise AcquisitionError("MODEL_HASH_MISMATCH", f"Expected SHA256 {expected_sha}, observed {actual_sha}")
    if expected_bytes is not None and int(expected_bytes) != actual_bytes:
        raise AcquisitionError("MODEL_SIZE_MISMATCH", f"Expected {expected_bytes} bytes, observed {actual_bytes}")
    return {"sha256": actual_sha, "bytes": actual_bytes}


def install_candidate(root: Path, manifest: dict[str, Any], candidate: Path) -> tuple[Path, dict[str, Any], bool]:
    proof = verify_candidate(manifest, candidate)
    registry_path = root / MODEL_REGISTRY
    existing = read_registry(registry_path)
    same_hash = [record for record in existing if str(record.get("sha256", "")).lower() == proof["sha256"]]
    destination = project_path(root, manifest["install"]["target_path"])
    if destination.exists():
        destination_hash = sha256_file(destination)
        if destination_hash != proof["sha256"]:
            raise AcquisitionError("TARGET_PATH_HASH_CONFLICT", f"Target exists with a different hash: {destination}")
        duplicate = True
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if manifest.get("reused_existing_path"):
            try:
                os.link(candidate, destination)
            except OSError:
                shutil.copy2(candidate, destination)
        else:
            try:
                os.replace(candidate, destination)
            except OSError as exc:
                if exc.errno != errno.EXDEV and getattr(exc, "winerror", None) != 17:
                    raise
                temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
                try:
                    shutil.copy2(candidate, temporary)
                    if temporary.stat().st_size != proof["bytes"] or sha256_file(temporary) != proof["sha256"]:
                        raise AcquisitionError("CROSS_VOLUME_COPY_HASH_MISMATCH", f"Copied target failed verification: {temporary}")
                    os.replace(temporary, destination)
                    candidate.unlink()
                finally:
                    temporary.unlink(missing_ok=True)
        duplicate = bool(same_hash) or bool(manifest.get("reused_existing_path"))
    return destination, proof, duplicate


def upsert_registry(root: Path, manifest: dict[str, Any], destination: Path, proof: dict[str, Any]) -> str:
    path = root / MODEL_REGISTRY
    records = read_registry(path)
    request = manifest["request"]
    asset = request["asset"]
    integration = request["integration"]
    lane = str(integration["workflow_lane"])
    identity = manifest["source_identity"]
    matches = [
        record for record in records
        if str(record.get("sha256", "")).lower() == proof["sha256"]
        and str(record.get("workflow_lane", "")) == lane
    ]
    if len(matches) > 1:
        raise AcquisitionError("DUPLICATE_ACTIVE_REGISTRY_RECORD", "More than one registry record matches hash and lane")
    record_id = (
        str(matches[0]["record_id"])
        if matches
        else f"MODEL-ACQ-{hashlib.sha256((proof['sha256'] + lane).encode()).hexdigest()[:16].upper()}"
    )
    record = {
        "registry_schema_version": "1.0",
        "record_id": record_id,
        "created_at": matches[0].get("created_at", now_iso()) if matches else now_iso(),
        "updated_at": now_iso(),
        "source": manifest["provider"],
        "source_url": manifest["source_metadata"]["page_url"],
        "source_model_id": identity.get("model_id") or identity.get("repo_id") or "",
        "source_model_version_id": identity.get("model_version_id") or identity.get("revision") or "",
        "model_name": asset["model_name"],
        "model_type": asset["model_type"],
        "base_model": asset["base_model"],
        "version_name": identity.get("version_name", ""),
        "file_name": destination.name,
        "file_extension": destination.suffix.lower(),
        "file_size_bytes": proof["bytes"],
        "sha256": proof["sha256"],
        "source_hashes": identity.get("source_hashes", {}),
        "local_path": logical_install_path(manifest),
        "storage_location": "local",
        "workflow_lane": lane,
        "compatibility_status": "needs_runtime_validation",
        "compatible_engines": integration.get("compatible_engines", []),
        "trigger_words": identity.get("trained_words", []),
        "intended_use": request["intended_use"],
        "prompt_notes": integration.get("prompt_notes", ""),
        "negative_prompt_notes": integration.get("negative_prompt_notes", ""),
        "qa_status": "not_tested",
        "runtime_validation_status": "queued",
        "visual_impact": asset.get("visual_impact", ""),
        "video_impact": asset.get("video_impact", ""),
        "audio_impact": asset.get("audio_impact", ""),
        "known_issues": ["Downloaded and hash-verified; runtime and output QA remain required."],
        "last_tested_at": "",
        "evidence_paths": [],
        "acquisition": {
            "request_id": request["request_id"],
            "method": manifest.get("acquisition_method", "api"),
            "content_based_suppression": False,
            "license_status": request["policy"]["license_status"],
        },
    }
    if matches:
        records[records.index(matches[0])] = record
    else:
        records.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(item, separators=(",", ":"), sort_keys=False) for item in records) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return record_id


def upsert_runtime_queue(root: Path, manifest: dict[str, Any], destination: Path, record_id: str) -> str:
    path = root / RUNTIME_QUEUE
    fieldnames = [
        "queue_id", "created_at", "model_name", "model_type", "base_model", "local_path",
        "workflow_lane", "test_workflow_path", "expected_result", "priority", "status", "evidence_path",
    ]
    rows: list[dict[str, str]] = []
    if path.is_file():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != fieldnames:
                raise AcquisitionError("RUNTIME_QUEUE_SCHEMA_MISMATCH", "Runtime queue columns do not match expected schema")
            rows = list(reader)
    request = manifest["request"]
    integration = request["integration"]
    queue_id = f"MRQ-ACQ-{record_id.rsplit('-', 1)[-1]}"
    row = {
        "queue_id": queue_id,
        "created_at": now_iso(),
        "model_name": str(request["asset"]["model_name"]),
        "model_type": str(request["asset"]["model_type"]),
        "base_model": str(request["asset"]["base_model"]),
        "local_path": logical_install_path(manifest),
        "workflow_lane": str(integration["workflow_lane"]),
        "test_workflow_path": str(integration.get("test_workflow_path", "")),
        "expected_result": str(integration.get("expected_runtime_result", "load_model_and_run_bounded_smoke_then_modality_qa")),
        "priority": str(integration.get("priority", 100)),
        "status": "queued",
        "evidence_path": "",
    }
    matches = [index for index, existing in enumerate(rows) if existing["queue_id"] == queue_id]
    if len(matches) > 1:
        raise AcquisitionError("DUPLICATE_RUNTIME_QUEUE_ID", f"Duplicate queue ID: {queue_id}")
    if matches:
        row["created_at"] = rows[matches[0]]["created_at"]
        rows[matches[0]] = row
    else:
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)
    return queue_id


def wire_workflows(root: Path, manifest: dict[str, Any], destination: Path, proof: dict[str, Any]) -> list[str]:
    request = manifest["request"]
    integration = request["integration"]
    updated: list[str] = []
    for binding in integration.get("workflow_bindings", []):
        path = project_path(root, binding["workflow_path"])
        workflow = load_json(path)
        node_id = str(binding["node_id"])
        input_name = str(binding["input_name"])
        if node_id not in workflow or not isinstance(workflow[node_id], dict):
            raise AcquisitionError("WORKFLOW_BINDING_NODE_MISSING", f"Node {node_id} missing in {path}")
        inputs = workflow[node_id].get("inputs")
        if not isinstance(inputs, dict) or input_name not in inputs:
            raise AcquisitionError("WORKFLOW_BINDING_INPUT_MISSING", f"Input {input_name} missing on node {node_id}")
        inputs[input_name] = str(binding.get("value") or destination.name)
        write_json_atomic(path, workflow)
        updated.append(relative_or_absolute(root, path))

    requirements_value = integration.get("runtime_requirements_path")
    if requirements_value:
        path = project_path(root, requirements_value)
        requirements = load_json(path)
        required_models = requirements.setdefault("required_models", [])
        if not isinstance(required_models, list):
            raise AcquisitionError("RUNTIME_REQUIREMENTS_INVALID", "required_models must be an array")
        role = str(integration.get("model_role") or request["asset"]["model_type"]).lower().replace(" ", "_")
        record = {
            "role": role,
            "model_type": request["asset"]["model_type"],
            "comfyui_model_subdir": request["asset"]["target_subdir"],
            "filename": destination.name,
            "bytes": proof["bytes"],
            "sha256": proof["sha256"],
            "hash_status": "verified_local_acquisition",
            "path_status": "verified_local_acquisition_pending_runtime",
            "source_url": manifest["source_metadata"]["page_url"],
        }
        matches = [index for index, item in enumerate(required_models) if isinstance(item, dict) and item.get("role") == role]
        if len(matches) > 1:
            raise AcquisitionError("RUNTIME_REQUIREMENTS_DUPLICATE_ROLE", f"Duplicate required model role: {role}")
        if matches:
            preserved = {key: value for key, value in required_models[matches[0]].items() if key in {"node_id", "node_class", "input"}}
            record.update(preserved)
            required_models[matches[0]] = record
        else:
            required_models.append(record)
        write_json_atomic(path, requirements)
        updated.append(relative_or_absolute(root, path))
    return sorted(set(updated))


def validate_wiring_targets(root: Path, manifest: dict[str, Any]) -> None:
    integration = manifest["request"]["integration"]
    for binding in integration.get("workflow_bindings", []):
        path = project_path(root, binding["workflow_path"])
        workflow = load_json(path)
        node_id = str(binding["node_id"])
        input_name = str(binding["input_name"])
        if node_id not in workflow or not isinstance(workflow[node_id], dict):
            raise AcquisitionError("WORKFLOW_BINDING_NODE_MISSING", f"Node {node_id} missing in {path}")
        inputs = workflow[node_id].get("inputs")
        if not isinstance(inputs, dict) or input_name not in inputs:
            raise AcquisitionError("WORKFLOW_BINDING_INPUT_MISSING", f"Input {input_name} missing on node {node_id}")
    requirements_value = integration.get("runtime_requirements_path")
    if requirements_value:
        requirements = load_json(project_path(root, requirements_value))
        if not isinstance(requirements.get("required_models", []), list):
            raise AcquisitionError("RUNTIME_REQUIREMENTS_INVALID", "required_models must be an array")


def object_info_visibility(filename: str, url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        serialized = json.dumps(payload, separators=(",", ":"))
        visible = filename in serialized
        return {"contacted": True, "visible": visible, "classification": "OBJECT_INFO_VISIBLE" if visible else "OBJECT_INFO_MODEL_NOT_VISIBLE"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"contacted": False, "visible": False, "classification": "OBJECT_INFO_UNAVAILABLE", "error": redact(str(exc))}


def finalize(root: Path, manifest: dict[str, Any], candidate: Path, wire: bool, object_info_url: str) -> dict[str, Any]:
    if wire:
        validate_wiring_targets(root, manifest)
    with acquisition_update_lock(root):
        destination, proof, duplicate = install_candidate(root, manifest, candidate)
        record_id = upsert_registry(root, manifest, destination, proof)
        queue_id = upsert_runtime_queue(root, manifest, destination, record_id)
        wired = wire_workflows(root, manifest, destination, proof) if wire else []
    visibility = object_info_visibility(destination.name, object_info_url)
    result = {
        "schema_version": "1.0",
        "record_id": f"ACQUISITION-{manifest['request']['request_id']}-{proof['sha256'][:12]}",
        "created_at": now_iso(),
        "classification": "MODEL_ASSET_INSTALLED_REGISTERED_AND_QUEUED",
        "request_id": manifest["request"]["request_id"],
        "provider": manifest["provider"],
        "acquisition_method": manifest.get("acquisition_method", "api"),
        "source_page_url": manifest["source_metadata"]["page_url"],
        "destination_path": logical_install_path(manifest),
        "sha256": proof["sha256"],
        "bytes": proof["bytes"],
        "duplicate_bytes_reused": duplicate,
        "registry_record_id": record_id,
        "runtime_queue_id": queue_id,
        "wired_files": wired,
        "object_info": visibility,
        "runtime_validation_status": "queued",
        "qa_status": "not_tested",
        "production_ready": False,
        "content_based_suppression": False,
        "credential_serialized": False,
        "browser_cookie_exported": False,
        "next_action": "Run the declared bounded workflow smoke and modality-specific QA; promote only after evidence passes.",
    }
    record_path = root / "runtime_artifacts" / "model_acquisition" / "records" / f"{result['record_id']}.json"
    write_json_atomic(record_path, result)
    result["record_path"] = relative_or_absolute(root, record_path)
    return result


def browser_request(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "request_id": manifest["request"]["request_id"],
        "classification": "BROWSER_DOWNLOAD_REQUIRED",
        "created_at": now_iso(),
        "page_url": manifest["source_metadata"]["page_url"],
        "expected_filename": manifest["install"]["local_filename"],
        "expected_sha256": manifest["source_metadata"].get("expected_sha256", ""),
        "expected_bytes": manifest["source_metadata"].get("expected_bytes"),
        "allowed_download_roots": [str(path) for path in browser_download_roots(root)],
        "browser_contract": {
            "use_signed_in_browser_session": True,
            "export_browser_cookies": False,
            "paste_api_token_into_page": False,
            "download_only_exact_resolved_file": True,
            "ingest_through_same_hash_and_registry_path": True,
        },
        "content_based_suppression": False,
        "next_action": "Run the dedicated background browser worker; use ingest-browser only for an explicitly authorized pre-existing download.",
    }


def preflight(root: Path, network: bool) -> dict[str, Any]:
    load_env(root)
    civitai_key = bool(secret_for("civitai"))
    hf_key = bool(secret_for("huggingface"))
    download_allowed = os.environ.get("CIVITAI_DOWNLOAD_ALLOWED", "true").strip().lower() in {"1", "true", "yes", "on"}
    skip_by_default = os.environ.get("CIVITAI_SKIP_DOWNLOADS_BY_DEFAULT", "false").strip().lower() in {"1", "true", "yes", "on"}
    browser_worker = root / "Plan/07_IMPLEMENTATION/scripts/run_background_browser_asset_download.py"
    checks = {
        "project_root_exists": root.is_dir(),
        "control_registry_exists": (root / CONTROL_REGISTRY).is_file(),
        "model_registry_exists": (root / MODEL_REGISTRY).is_file(),
        "runtime_queue_exists": (root / RUNTIME_QUEUE).is_file(),
        "civitai_credential_present": civitai_key,
        "civitai_download_allowed": download_allowed,
        "civitai_skip_downloads_by_default_disabled": not skip_by_default,
        "background_browser_worker_present": browser_worker.is_file(),
        "browser_session_credential_present": bool(os.environ.get("CIVITAI_SESSION_COOKIE", "").strip()),
        "browser_fallback_available": browser_worker.is_file(),
        "content_based_suppression_disabled": True,
    }
    network_result: dict[str, Any] = {"attempted": False}
    if network:
        network_result["attempted"] = True
        try:
            payload = fetch_json("https://civitai.com/api/v1/models?limit=1", "civitai")
            network_result.update({"passed": isinstance(payload.get("items"), list), "classification": "CIVITAI_API_REACHABLE"})
        except AcquisitionError as exc:
            network_result.update({"passed": False, "classification": exc.classification, "error": str(exc)})
    required = [
        "project_root_exists",
        "control_registry_exists",
        "model_registry_exists",
        "runtime_queue_exists",
        "civitai_credential_present",
        "civitai_download_allowed",
        "civitai_skip_downloads_by_default_disabled",
        "background_browser_worker_present",
    ]
    return {
        "schema_version": "1.0",
        "created_at": now_iso(),
        "classification": "MODEL_ACQUISITION_PREFLIGHT_PASS" if all(checks[name] for name in required) else "MODEL_ACQUISITION_PREFLIGHT_BLOCKED",
        "checks": checks,
        "huggingface_credential_present": hf_key,
        "network": network_result,
        "secret_values_reported": False,
    }


def browser_download_roots(root: Path) -> list[Path]:
    roots = [root / "runtime_artifacts" / "model_acquisition" / "browser_inbox"]
    configured = os.environ.get("MODEL_ACQUISITION_BROWSER_DOWNLOAD_ROOT", "").strip()
    roots.append(Path(configured) if configured else Path.home() / "Downloads")
    unique: list[Path] = []
    for path in roots:
        resolved = path.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def run_background_browser_fallback(
    root: Path,
    manifest_path: Path,
    wire: bool,
    object_info_url: str,
) -> dict[str, Any]:
    worker = root / "Plan/07_IMPLEMENTATION/scripts/run_background_browser_asset_download.py"
    if not worker.is_file():
        raise AcquisitionError("BACKGROUND_BROWSER_WORKER_MISSING", f"Background browser worker not found: {worker}")
    command = [
        sys.executable,
        str(worker),
        "--project-root",
        str(root),
        "--manifest",
        str(manifest_path),
        "--install",
        "--object-info-url",
        object_info_url,
    ]
    if wire:
        command.append("--wire")
    timeout = int(os.environ.get("BACKGROUND_BROWSER_TIMEOUT_SECONDS", "180")) + 30
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AcquisitionError(
            "BACKGROUND_BROWSER_DOWNLOAD_TIMEOUT",
            f"Background browser worker exceeded {timeout} seconds",
        ) from exc
    output = completed.stdout.strip()
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise AcquisitionError(
            "BACKGROUND_BROWSER_OUTPUT_INVALID",
            f"Background browser worker returned invalid output (exit {completed.returncode})",
        ) from exc
    if completed.returncode != 0:
        raise AcquisitionError(
            str(payload.get("classification", "BACKGROUND_BROWSER_DOWNLOAD_FAILED")),
            redact(str(payload.get("error", "Background browser worker failed"))),
        )
    return payload


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--network", action="store_true")
    discover = sub.add_parser("discover-civitai")
    discover.add_argument("--query", required=True)
    discover.add_argument("--types", default="LORA")
    discover.add_argument("--base-model", default="")
    discover.add_argument("--limit", type=int, default=20)
    discover.add_argument("--out", type=Path)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--request", type=Path, required=True)
    resolve.add_argument("--out", type=Path, required=True)
    resolve.add_argument("--metadata-json", type=Path)
    acquire = sub.add_parser("acquire")
    acquire.add_argument("--manifest", type=Path, required=True)
    acquire.add_argument("--wire", action="store_true")
    acquire.add_argument("--object-info-url", default=DEFAULT_OBJECT_INFO)
    prepare = sub.add_parser("prepare-browser")
    prepare.add_argument("--manifest", type=Path, required=True)
    prepare.add_argument("--out", type=Path, required=True)
    ingest = sub.add_parser("ingest-browser")
    ingest.add_argument("--manifest", type=Path, required=True)
    ingest.add_argument("--downloaded-file", type=Path, required=True)
    ingest.add_argument("--wire", action="store_true")
    ingest.add_argument("--object-info-url", default=DEFAULT_OBJECT_INFO)
    args = parser.parse_args()

    root = args.project_root.resolve()
    load_env(root)
    try:
        if args.command == "preflight":
            result = preflight(root, args.network)
            print(json.dumps(result, indent=2))
            return 0 if result["classification"] == "MODEL_ACQUISITION_PREFLIGHT_PASS" else 2
        if args.command == "discover-civitai":
            result = discover_civitai(args.query, args.types, args.limit, args.base_model)
            if args.out:
                output = project_path(root, args.out)
                write_json_atomic(output, result)
                result = {"classification": result["classification"], "candidate_count": result["candidate_count"], "output": relative_or_absolute(root, output)}
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "resolve":
            request = load_json(project_path(root, args.request))
            metadata = project_path(root, args.metadata_json) if args.metadata_json else None
            manifest = resolve_request(root, request, metadata)
            output = project_path(root, args.out)
            write_json_atomic(output, manifest)
            print(json.dumps({"classification": "MODEL_ACQUISITION_REQUEST_RESOLVED", "manifest": relative_or_absolute(root, output)}, indent=2))
            return 0
        manifest = load_json(project_path(root, args.manifest))
        if args.command == "prepare-browser":
            output = project_path(root, args.out)
            value = browser_request(root, manifest)
            write_json_atomic(output, value)
            print(json.dumps({"classification": value["classification"], "browser_request": relative_or_absolute(root, output)}, indent=2))
            return 0
        if args.command == "acquire":
            manifest["acquisition_method"] = "api"
            try:
                candidate = download_to_staging(root, manifest)
            except AcquisitionError as exc:
                fallback_allowed = bool(manifest.get("request", {}).get("policy", {}).get("allow_browser_fallback"))
                if exc.classification != "BROWSER_DOWNLOAD_REQUIRED" or manifest.get("provider") != "civitai" or not fallback_allowed:
                    raise
                result = run_background_browser_fallback(
                    root,
                    project_path(root, args.manifest),
                    args.wire,
                    args.object_info_url,
                )
                print(json.dumps(result, indent=2))
                return 0
            result = finalize(root, manifest, candidate, args.wire, args.object_info_url)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "ingest-browser":
            candidate = project_path(root, args.downloaded_file)
            if not candidate.is_file():
                raise AcquisitionError("BROWSER_DOWNLOAD_FILE_MISSING", f"Downloaded file not found: {candidate}")
            allowed_roots = browser_download_roots(root)
            if not any(candidate.resolve().is_relative_to(item.resolve()) for item in allowed_roots):
                raise AcquisitionError("BROWSER_DOWNLOAD_PATH_NOT_ALLOWED", "Downloaded file is outside approved browser download roots")
            manifest["acquisition_method"] = "browser_authenticated_session"
            result = finalize(root, manifest, candidate, args.wire, args.object_info_url)
            print(json.dumps(result, indent=2))
            return 0
    except AcquisitionError as exc:
        print(json.dumps({"classification": exc.classification, "error": redact(str(exc)), "secret_values_reported": False}, indent=2))
        return 3 if exc.classification == "BROWSER_DOWNLOAD_REQUIRED" else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
