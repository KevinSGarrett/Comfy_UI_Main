#!/usr/bin/env python3
"""Independently verify the Wave64 provider catalog and speech control package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
CATALOG = Path("Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json")
REQUIREMENTS = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json")
ITEMS = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv")
TRACKER = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv")
EVIDENCE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_HYPERREAL_AUDIO_SECOND_PASS_AUDIT_20260715.json")
EVIDENCE_MIRROR = Path("Plan/Tracker/Evidence/Audio_Asset_Intake/WAVE64_HYPERREAL_AUDIO_SECOND_PASS_AUDIT_20260715.json")
DOCS = [
    Path("Plan/00_PROJECT_CONTROL/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_AND_VOICE_MASTER_PLAN.md"),
    Path("Plan/02_TARGET_ARCHITECTURE/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ARCHITECTURE.md"),
    Path("Plan/05_AUDIO_SYSTEM/WAVE64_HYPERREAL_SPEECH_ENGINE_AND_MODEL_STRATEGY.md"),
    Path("Plan/Instructions/QA/AUTONOMOUS_HYPERREAL_SPEECH_AND_VOICE_QA_PROTOCOL.md"),
    Path("Plan/Instructions/Hydration_Rehydration/AUTONOMOUS_HYPERREAL_SPEECH_MAIN_SESSION_HANDOFF.md"),
]


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "ComfyUIMainWave64SecondPass/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object response from {urllib.parse.urlparse(url).netloc}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_huggingface(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for asset in catalog["official_asset_groups"]:
        repo = asset["repo_id"]
        live = fetch_json(f"https://huggingface.co/api/models/{repo}?blobs=true")
        live_files = {
            sibling["rfilename"]: sibling.get("lfs", {})
            for sibling in live.get("siblings", [])
            if sibling.get("lfs")
        }
        file_checks = []
        for expected in asset["key_files"]:
            actual = live_files.get(expected["filename"], {})
            file_checks.append({
                "filename": expected["filename"],
                "revision_match": live.get("sha") == asset["revision"],
                "bytes_match": actual.get("size") == expected["bytes"],
                "sha256_match": actual.get("sha256") == expected["sha256"],
            })
        results.append({
            "asset_id": asset["asset_id"],
            "repo_id": repo,
            "catalog_revision": asset["revision"],
            "live_revision": live.get("sha"),
            "revision_match": live.get("sha") == asset["revision"],
            "key_files": file_checks,
            "pass": live.get("sha") == asset["revision"] and all(check["bytes_match"] and check["sha256_match"] for check in file_checks),
        })
    return results


def verify_civitai(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for asset in catalog["civitai_integration_candidates"]:
        live = fetch_json(f"https://civitai.com/api/v1/model-versions/{asset['model_version_id']}")
        files = {str(file["id"]): file for file in live.get("files", [])}
        actual = files.get(asset["file_id"], {})
        hashes = actual.get("hashes", {})
        result = {
            "asset_id": asset["asset_id"],
            "model_id_match": str(live.get("modelId")) == asset["model_id"],
            "model_version_id_match": str(live.get("id")) == asset["model_version_id"],
            "file_id_match": str(actual.get("id")) == asset["file_id"],
            "filename_match": actual.get("name") == asset["filename"],
            "sha256_match": str(hashes.get("SHA256", "")).lower() == asset["sha256"].lower(),
        }
        result["pass"] = all(value for key, value in result.items() if key.endswith("_match"))
        results.append(result)
    return results


def main(root: Path = ROOT, network: bool = False) -> dict[str, Any]:
    root = root.resolve()
    catalog = json.loads((root / CATALOG).read_text(encoding="utf-8"))
    requirements = json.loads((root / REQUIREMENTS).read_text(encoding="utf-8"))
    items = read_csv(root / ITEMS)
    trackers = read_csv(root / TRACKER)
    asset_ids = {asset["asset_id"] for asset in catalog["official_asset_groups"] + catalog["civitai_integration_candidates"]}
    required_ids = {asset_id for row in requirements["requirements"] for asset_id in row.get("required_asset_ids", [])}

    with (root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        canonical_ids = {row["Tracker_ID"] for row in csv.DictReader(handle)}
    expected_tracker_ids = [f"TRK-W64-{row:03d}" for row in range(113, 149)]
    provider_reference = CATALOG.as_posix()

    hf_results = verify_huggingface(catalog) if network else []
    civitai_results = verify_civitai(catalog) if network else []
    checks = {
        "catalog_assets_unique": len(asset_ids) == len(catalog["official_asset_groups"]) + len(catalog["civitai_integration_candidates"]),
        "all_requirement_asset_ids_resolve": required_ids.issubset(asset_ids),
        "row117_binds_every_catalog_asset": set(next(row for row in requirements["requirements"] if row["tracker_id"] == "TRK-W64-117")["required_asset_ids"]) == asset_ids,
        "item_tracker_parity": [row["Item_ID"] for row in items] == [row["Source_Item_ID"] for row in trackers],
        "tracker_range_exact": [row["Tracker_ID"] for row in trackers] == expected_tracker_ids,
        "canonical_collision_count_zero": not canonical_ids.intersection(expected_tracker_ids),
        "all_rows_remain_planned": all(row["Status"] == "Planned_Autonomous_Implementation_Required" for row in items + trackers),
        "all_control_documents_reference_catalog": all(provider_reference in (root / path).read_text(encoding="utf-8") for path in DOCS),
        "requirements_mirror_exact": (root / REQUIREMENTS).read_bytes() == (root / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json").read_bytes(),
        "huggingface_live_exact_match": bool(hf_results) and all(result["pass"] for result in hf_results) if network else None,
        "civitai_live_exact_match": bool(civitai_results) and all(result["pass"] for result in civitai_results) if network else None,
        "content_based_suppression_false": catalog["boundaries"]["content_based_suppression"] is False,
        "no_runtime_or_download_claim": catalog["boundaries"]["runtime_or_generation_executed"] is False and catalog["boundaries"]["download_is_runtime_ready"] is False,
    }
    pass_values = [value for value in checks.values() if value is not None]
    evidence = {
        "schema_version": "1.0",
        "evidence_id": "WAVE64_HYPERREAL_AUDIO_SECOND_PASS_AUDIT_20260715",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": "pass_second_pass_provider_and_control_package_audit" if all(pass_values) else "fail_second_pass_provider_and_control_package_audit",
        "network_verification_requested": network,
        "catalog": CATALOG.as_posix(),
        "catalog_sha256": digest(root / CATALOG),
        "counts": {
            "official_asset_groups": len(catalog["official_asset_groups"]),
            "official_source_repositories": len(catalog["official_source_repositories"]),
            "civitai_integrations": len(catalog["civitai_integration_candidates"]),
            "requirement_rows": len(requirements["requirements"]),
            "bound_asset_ids": len(required_ids),
        },
        "checks": checks,
        "huggingface_live_results": hf_results,
        "civitai_live_results": civitai_results,
        "exact_blockers_preserved": catalog["deferred_or_exact_blocked"],
        "boundaries": catalog["boundaries"],
    }
    write_json(root / EVIDENCE, evidence)
    write_json(root / EVIDENCE_MIRROR, evidence)
    print(json.dumps({"result": evidence["result"], "counts": evidence["counts"], "checks": checks}, indent=2))
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--network", action="store_true")
    args = parser.parse_args()
    result = main(args.project_root, args.network)
    raise SystemExit(0 if result["result"].startswith("pass_") else 1)
