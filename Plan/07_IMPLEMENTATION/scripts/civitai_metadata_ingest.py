#!/usr/bin/env python3
"""
Wave 02 Civitai metadata ingest helper.

Purpose:
- Scan local model files.
- Compute SHA256.
- Resolve Civitai metadata by hash when possible.
- Fetch model/version/images metadata.
- Cache raw JSON.
- Write a wide normalized registry CSV.

This script is designed for the future local repo at C:\Comfy_UI_Main.
It intentionally uses only the Python standard library.

Real API keys must come from a local .env file or process environment.
Do not commit real .env files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


MODEL_EXTENSIONS = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx"}

DEFAULT_COLUMNS = [
    "asset_id_internal","asset_uuid","asset_status","asset_origin","source_system","source_url","source_download_url",
    "civitai_model_id","civitai_model_version_id","civitai_model_name","civitai_model_version_name","civitai_model_type",
    "civitai_model_url","civitai_model_slug","civitai_air_identifier","creator_username","creator_id","creator_profile_url",
    "model_published_at","model_updated_at","version_published_at","version_updated_at","metadata_first_seen_at","metadata_last_seen_at",
    "metadata_fetch_status","metadata_fetch_error","metadata_raw_cache_path","metadata_raw_cache_sha256",
    "base_model_raw","base_model_normalized","base_model_type","engine_family","engine_variant","engine_compatibility_status",
    "resource_type","asset_type","comfyui_loader_class","comfyui_target_folder","comfyui_relative_path",
    "original_filename","normalized_filename","file_extension","file_format","file_primary","file_size_bytes","file_size_mb",
    "hash_sha256","hash_autov1","hash_autov2","hash_crc32","hash_blake3","hash_other_json",
    "pickle_scan_result","virus_scan_result","file_scan_status","file_scan_at",
    "license_raw","license_normalized","commercial_use_raw","allow_derivatives_raw","allow_different_license_raw","credit_required_raw",
    "nsfw_flag","content_rating_raw","content_rating_normalized","availability_status","deleted_or_hidden_flag",
    "tags_raw","tags_normalized","category_primary","category_secondary","scene_role_primary","scene_role_secondary",
    "trigger_words_raw","trigger_words_normalized","trained_words_raw","trained_words_normalized","prompt_keywords_inferred",
    "description_html_cache_path","description_text_cache_path","description_summary","description_sha256",
    "stats_download_count","stats_favorite_count","stats_comment_count","stats_rating","stats_rating_count","stats_thumbs_up_count",
    "version_download_count","version_rating","version_rating_count",
    "sample_image_count","sample_image_ids","sample_image_urls_manifest","sample_image_metadata_available",
    "sample_prompt_keywords","sample_negative_keywords","sample_generation_params_manifest",
    "local_original_path","local_cache_path","local_cache_exists","local_cache_verified_at","local_cache_sha256_match",
    "s3_bucket","s3_key","s3_uri","s3_storage_class","s3_etag","s3_last_modified","s3_sha256_tag","s3_verified_at",
    "ec2_model_path","ec2_cache_exists","ec2_cache_verified_at","ec2_sha256_match",
    "dedupe_group_id","duplicate_of_asset_id","duplicate_reason","preferred_version_flag","superseded_by_asset_id",
    "recommended_pass_scope","recommended_mask_scope","recommended_mask_size_class","recommended_use_phase",
    "recommended_weight_min","recommended_weight_max","recommended_denoise_min","recommended_denoise_max",
    "identity_drift_risk","pose_drift_risk","style_drift_risk","anatomy_risk","artifact_risk","bleed_risk",
    "allowed_pass_types","incompatible_pass_types","required_control_maps","required_masks","required_qa_tests",
    "qa_status","qa_last_run_at","qa_evidence_manifest_path","promotion_status","promotion_notes","human_notes","ai_pm_notes"
]


def load_dotenv(path: Optional[Path]) -> None:
    if not path or not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def request_json(url: str, api_key: str = "", user_agent: str = "Comfy_UI_Main_Model_Metadata_Manager/1.0", retries: int = 5, timeout: int = 60) -> Dict[str, Any]:
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    last_error: Optional[str] = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
            if e.code in {401, 403, 404}:
                break
        except Exception as e:
            last_error = repr(e)

        sleep = min(30, 2 ** attempt)
        time.sleep(sleep)

    return {"__fetch_error__": last_error or "unknown_error", "__url__": url}


def normalize_engine(base_model: str, file_name: str = "") -> str:
    text = f"{base_model} {file_name}".lower()
    if "flux" in text:
        return "flux"
    if "pony" in text:
        return "pony"
    if "sdxl" in text or "xl" in text:
        return "sdxl"
    if "sd 1.5" in text or "sd15" in text or "1.5" in text:
        return "sd15"
    if "sd 2" in text or "2.1" in text:
        return "sd2"
    if "sd3" in text or "stable diffusion 3" in text:
        return "sd3"
    if any(x in text for x in ["wan", "hunyuan", "ltxv", "animatediff"]):
        return "video"
    return "unknown"


def normalize_asset_type(model_type: str, filename: str) -> str:
    text = f"{model_type} {filename}".lower()
    if "lora" in text:
        return "lora"
    if "checkpoint" in text:
        return "checkpoint"
    if "controlnet" in text:
        return "controlnet"
    if "vae" in text:
        return "vae"
    if "embedding" in text or "textual inversion" in text:
        return "embedding"
    if "upscale" in text or "esrgan" in text:
        return "upscale"
    if "motion" in text or "animatediff" in text:
        return "motion_module"
    return "unknown"


def target_folder(asset_type: str, engine: str, category: str) -> str:
    base = {
        "checkpoint": "checkpoints",
        "lora": "loras",
        "controlnet": "controlnet",
        "vae": "vae",
        "embedding": "embeddings",
        "upscale": "upscale_models",
        "motion_module": "animatediff_models",
    }.get(asset_type, "unknown_assets")
    return f"{base}/wave42/{engine}/{category}".replace("\\", "/")


def safe_get(d: Dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def write_json(path: Path, data: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(raw, encoding="utf-8")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_registry_row(file_path: Path, file_hash: str, model_data: Dict[str, Any], version_data: Dict[str, Any], images_data: Dict[str, Any], raw_cache_dir: Path, args: argparse.Namespace) -> Dict[str, Any]:
    model_id = model_data.get("id") or safe_get(version_data, "modelId")
    version_id = version_data.get("id")
    model_name = model_data.get("name")
    version_name = version_data.get("name")
    model_type = model_data.get("type") or ""
    base_model = version_data.get("baseModel") or ""
    engine = normalize_engine(base_model, file_path.name)
    asset_type = normalize_asset_type(model_type, file_path.name)
    tags = model_data.get("tags") or []
    trained_words = version_data.get("trainedWords") or []
    category = "uncategorized"
    if tags:
        category = str(tags[0]).lower().replace(" ", "_")[:80]

    row = {col: "" for col in DEFAULT_COLUMNS}
    row.update({
        "asset_id_internal": f"CIVITAI-{model_id or 'UNKNOWN'}-{version_id or file_hash[:12]}",
        "asset_status": "metadata_ingested" if model_id or version_id else "unresolved_civitai_origin",
        "asset_origin": "civitai",
        "source_system": "civitai_api",
        "source_url": f"https://civitai.com/models/{model_id}" if model_id else "",
        "civitai_model_id": model_id or "",
        "civitai_model_version_id": version_id or "",
        "civitai_model_name": model_name or "",
        "civitai_model_version_name": version_name or "",
        "civitai_model_type": model_type,
        "civitai_model_url": f"https://civitai.com/models/{model_id}" if model_id else "",
        "creator_username": safe_get(model_data, "creator", "username") or "",
        "creator_id": safe_get(model_data, "creator", "id") or "",
        "model_published_at": model_data.get("publishedAt") or "",
        "model_updated_at": model_data.get("updatedAt") or "",
        "version_published_at": version_data.get("publishedAt") or "",
        "version_updated_at": version_data.get("updatedAt") or "",
        "metadata_first_seen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metadata_last_seen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metadata_fetch_status": "ok" if "__fetch_error__" not in model_data and "__fetch_error__" not in version_data else "partial_or_failed",
        "metadata_fetch_error": model_data.get("__fetch_error__") or version_data.get("__fetch_error__") or "",
        "metadata_raw_cache_path": str(raw_cache_dir),
        "base_model_raw": base_model,
        "base_model_normalized": base_model,
        "engine_family": engine,
        "engine_compatibility_status": "pending_runtime_proof" if engine != "unknown" else "unknown_engine_blocked",
        "resource_type": asset_type,
        "asset_type": asset_type,
        "comfyui_target_folder": target_folder(asset_type, engine, category),
        "original_filename": file_path.name,
        "normalized_filename": file_path.name,
        "file_extension": file_path.suffix.lower(),
        "file_format": file_path.suffix.lower().lstrip("."),
        "file_size_bytes": file_path.stat().st_size,
        "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 3),
        "hash_sha256": file_hash,
        "hash_other_json": json.dumps(safe_get(version_data, "files", 0, "hashes") or {}, ensure_ascii=False),
        "license_raw": model_data.get("license") or "",
        "nsfw_flag": model_data.get("nsfw") if model_data.get("nsfw") is not None else "",
        "tags_raw": json.dumps(tags, ensure_ascii=False),
        "tags_normalized": json.dumps([str(t).lower().replace(" ", "_") for t in tags], ensure_ascii=False),
        "category_primary": category,
        "scene_role_primary": "pending_ai_pm_classification",
        "trigger_words_raw": json.dumps(trained_words, ensure_ascii=False),
        "trained_words_raw": json.dumps(trained_words, ensure_ascii=False),
        "trained_words_normalized": json.dumps([str(t).strip().lower() for t in trained_words], ensure_ascii=False),
        "description_sha256": hashlib.sha256(str(model_data.get("description") or "").encode("utf-8")).hexdigest(),
        "stats_download_count": safe_get(model_data, "stats", "downloadCount") or "",
        "stats_favorite_count": safe_get(model_data, "stats", "favoriteCount") or "",
        "stats_comment_count": safe_get(model_data, "stats", "commentCount") or "",
        "stats_rating": safe_get(model_data, "stats", "rating") or "",
        "stats_rating_count": safe_get(model_data, "stats", "ratingCount") or "",
        "sample_image_count": len(images_data.get("items", [])) if isinstance(images_data.get("items"), list) else "",
        "sample_image_ids": json.dumps([img.get("id") for img in images_data.get("items", [])[:20] if isinstance(img, dict)], ensure_ascii=False) if isinstance(images_data.get("items"), list) else "",
        "local_original_path": str(file_path),
        "local_cache_path": str(file_path),
        "local_cache_exists": True,
        "local_cache_verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "local_cache_sha256_match": True,
        "s3_bucket": args.s3_bucket or "",
        "s3_key": "",
        "s3_uri": "",
        "recommended_pass_scope": "pending_ai_pm_classification",
        "recommended_mask_scope": "pending_ai_pm_classification",
        "recommended_mask_size_class": "pending_ai_pm_classification",
        "allowed_pass_types": "[]",
        "incompatible_pass_types": "[]",
        "required_qa_tests": json.dumps(["hash_match", "metadata_completeness", "engine_compatibility"], ensure_ascii=False),
        "qa_status": "pending",
        "promotion_status": "blocked_until_runtime_proof",
    })
    return row


def scan_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in MODEL_EXTENSIONS:
            yield p


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--scan-root", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=Path("registries/civitai_model_registry.csv"))
    parser.add_argument("--raw-cache-root", type=Path, default=None)
    parser.add_argument("--s3-bucket", default=os.getenv("S3_MODEL_BUCKET", ""))
    parser.add_argument("--limit", type=int, default=0, help="0 means no limit")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    load_dotenv(args.env)

    api_base = os.getenv("CIVITAI_API_BASE_URL", "https://civitai.com/api/v1").rstrip("/")
    api_key = os.getenv("CIVITAI_API_KEY", "")
    user_agent = os.getenv("CIVITAI_USER_AGENT", "Comfy_UI_Main_Model_Metadata_Manager/1.0")
    retries = int(os.getenv("CIVITAI_MAX_RETRIES", "5"))
    timeout = int(os.getenv("CIVITAI_TIMEOUT_SECONDS", "60"))

    scan_root = args.scan_root or Path(os.getenv("CIVITAI_HASH_SCAN_ROOT", os.getenv("LOCAL_MODEL_CACHE_ROOT", ".")))
    raw_cache_root = args.raw_cache_root or Path(os.getenv("CIVITAI_CACHE_RAW_JSON_ROOT", "metadata/civitai_raw"))

    rows: List[Dict[str, Any]] = []
    for idx, file_path in enumerate(scan_files(scan_root), start=1):
        if args.limit and idx > args.limit:
            break

        print(f"[{idx}] hashing {file_path}")
        file_hash = sha256_file(file_path)

        version_by_hash_url = f"{api_base}/model-versions/by-hash/{urllib.parse.quote(file_hash)}"
        version_data = request_json(version_by_hash_url, api_key=api_key, user_agent=user_agent, retries=retries, timeout=timeout)

        model_id = version_data.get("modelId")
        version_id = version_data.get("id")

        if model_id:
            model_url = f"{api_base}/models/{model_id}"
            model_data = request_json(model_url, api_key=api_key, user_agent=user_agent, retries=retries, timeout=timeout)
        else:
            model_data = {"__fetch_error__": "model_id_unresolved_from_hash", "__url__": version_by_hash_url}

        if version_id:
            version_url = f"{api_base}/model-versions/{version_id}"
            version_data_full = request_json(version_url, api_key=api_key, user_agent=user_agent, retries=retries, timeout=timeout)
            if "__fetch_error__" not in version_data_full:
                version_data = version_data_full

        images_data = {}
        if model_id:
            images_url = f"{api_base}/images?modelId={urllib.parse.quote(str(model_id))}&limit=20"
            images_data = request_json(images_url, api_key=api_key, user_agent=user_agent, retries=retries, timeout=timeout)

        cache_dir = raw_cache_root / str(model_id or "unresolved") / str(version_id or file_hash[:16])
        model_sha = write_json(cache_dir / "model.json", model_data)
        version_sha = write_json(cache_dir / "version.json", version_data)
        images_sha = write_json(cache_dir / "images.json", images_data)
        write_json(cache_dir / "fetch_manifest.json", {
            "model_id": model_id,
            "model_version_id": version_id,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "api_base_url": api_base,
            "request_urls": [version_by_hash_url],
            "raw_files": {
                "model": "model.json",
                "version": "version.json",
                "images": "images.json",
            },
            "raw_sha256": {
                "model": model_sha,
                "version": version_sha,
                "images": images_sha,
            },
            "fetch_status": "ok" if model_id or version_id else "unresolved",
            "errors": [],
            "normalization_version": "wave02_v1"
        })

        row = build_registry_row(file_path, file_hash, model_data, version_data, images_data, cache_dir, args)
        rows.append(row)

    if args.dry_run:
        print(f"Dry run complete. Rows that would be written: {len(rows)}")
        return 0

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DEFAULT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
