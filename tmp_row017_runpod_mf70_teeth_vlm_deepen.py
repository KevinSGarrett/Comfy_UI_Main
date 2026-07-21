#!/usr/bin/env python3
"""Deepen Row017 mf70_teeth producer with Ollama qwen2.5vl:7b (no COMPLETE)."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CHI = ZoneInfo("America/Chicago")
NOW = datetime.now(CHI)
VLM_STAMP = NOW.strftime("%Y%m%dT%H%M%S") + "-0500"
CREATED = NOW.isoformat(timespec="seconds")

ROOT = Path(os.environ.get("WAVE64_ROOT") or os.environ.get("WAVE64") or "/workspace/wave64")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
VLM_MODEL = os.environ.get("ROW017_VLM_MODEL", "qwen2.5vl:7b")
REGION = "mf70_teeth"
STAMP = os.environ.get("ROW017_PRODUCER_STAMP", "").strip()

WAVE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64"
TRK_DIR = ROOT / "Plan/Tracker/Evidence"
ITEM = ROOT / "Plan/Items/Reports/ITEM-W64-017_global_visual_review_not_local_only.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def http_json(url: str, payload: dict | None = None, timeout: float = 900.0) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="GET" if data is None else "POST",
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body.decode("utf-8")) if body else {}


def discover_stamp() -> str:
    if STAMP:
        return STAMP
    base = ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
    cands = sorted(
        base.glob("runpod_comfyui_row017_mf70_teeth_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not cands:
        raise FileNotFoundError("no mf70_teeth pullback dirs found")
    name = cands[0].name
    prefix = "runpod_comfyui_row017_mf70_teeth_"
    return name[len(prefix) :]


def run_vlm(image_path: Path, panel_path: Path | None) -> dict:
    images = [base64.b64encode(image_path.read_bytes()).decode("ascii")]
    if panel_path and panel_path.exists():
        images.append(base64.b64encode(panel_path.read_bytes()).decode("ascii"))
    prompt = (
        "You are a bounded Wave64 Row017 VLM critic for a localized SDXL mf70_teeth inpaint. Image 1 is the producer output; image 2 (if present) is source|output side-by-side. The mask covers the tiny visible teeth band; planned change is a very subtle visible teeth preservation pass while preserving identity, closed relaxed mouth, lip line/shape, philtrum, nose, chin, cheeks, tongue/inner mouth hidden or unchanged, eyes/gaze, eyebrows, hair occlusion, clothing, background, lighting, and framing. Assess whole-frame identity preservation, natural tooth appearance, no smile/open-mouth/tooth-count rewrite, hard mask edges, and whether refinement stayed inside the teeth mask. Return ONLY compact JSON with keys: frame_ok (bool), identity_preserved (bool), eyes_ok (bool), mouth_ok (bool), background_ok (bool), hard_mask_edge (bool), target_region_refined (bool), global_defects (array of strings), summary (string <= 280 chars), promotion_allowed (always false), row_complete_allowed (always false), uncertainty (0..1). Do not invent media. Do not claim COMPLETE."
    )
    payload = {
        "model": VLM_MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
        "messages": [{"role": "user", "content": prompt, "images": images}],
    }
    try:
        resp = http_json(f"{OLLAMA}/api/chat", payload, timeout=900.0)
    except Exception as exc:  # noqa: BLE001
        return {
            "attempted": True,
            "ok": False,
            "model": VLM_MODEL,
            "error": str(exc),
            "raw": None,
            "parsed": None,
        }
    content = ((resp.get("message") or {}).get("content") or "").strip()
    parsed = None
    parse_error = None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
                parse_error = None
            except json.JSONDecodeError as exc2:
                parse_error = str(exc2)
    if isinstance(parsed, dict):
        parsed["promotion_allowed"] = False
        parsed["row_complete_allowed"] = False
    return {
        "attempted": True,
        "ok": parsed is not None and bool(parsed.get("frame_ok", False)),
        "model": VLM_MODEL,
        "endpoint": f"{OLLAMA}/api/chat",
        "raw_content": content[:8000],
        "parse_error": parse_error,
        "parsed": parsed,
        "ollama_eval_count": resp.get("eval_count"),
        "ollama_prompt_eval_count": resp.get("prompt_eval_count"),
        "total_duration_ns": resp.get("total_duration"),
    }


def main() -> int:
    stamp = discover_stamp()
    out_dir = (
        ROOT
        / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
        / f"runpod_comfyui_row017_mf70_teeth_{stamp}"
    )
    img_dir = out_dir / "images"
    runtime_dir = ROOT / "runtime_artifacts" / f"wave64_row017_runpod_mf70_teeth_{stamp}"
    receipt_path = out_dir / "LOCAL_RUNTIME_RECEIPT.json"
    if not receipt_path.exists():
        raise FileNotFoundError(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    out_name = receipt.get("output_filename")
    out_path = img_dir / out_name if out_name else None
    if out_path is None or not out_path.exists():
        cands = sorted(
            p
            for p in img_dir.glob(f"codex_row017_mf70_teeth_{stamp}_*.png")
            if "mask_preview" not in p.name
        )
        if not cands:
            raise FileNotFoundError("output image missing")
        out_path = cands[0]
    out_sha = receipt.get("output_sha256") or sha256_file(out_path)
    if sha256_file(out_path) != out_sha:
        raise RuntimeError("output sha mismatch vs receipt")

    global_review = (
        "Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/"
        f"ROW017_RUNPOD_MF70_TEETH_{stamp}_GLOBAL_REVIEW.json"
    )
    visual_qa = (
        "Plan/Instructions/QA/Evidence/Image_Artifact_QA/"
        f"ROW017_RUNPOD_MF70_TEETH_VISUAL_QA_{stamp}.json"
    )
    producer_packet = (
        "Plan/Instructions/QA/Evidence/Wave64/"
        f"TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_{stamp}.json"
    )

    cache_path = runtime_dir / "vlm_raw_response.json"
    if cache_path.exists() and os.environ.get("ROW017_FORCE_VLM") != "1":
        print("reusing_cached_vlm", rel(cache_path))
        vlm = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        print("running_vlm", VLM_MODEL, "stamp", stamp)
        vlm = run_vlm(out_path, img_dir / "qa_full_side_by_side.png")
        runtime_dir.mkdir(parents=True, exist_ok=True)
        write_json(cache_path, vlm)
    print("vlm_ok", vlm.get("ok"), "error", vlm.get("error"), "parse_error", vlm.get("parse_error"))
    if vlm.get("error"):
        raise RuntimeError(f"VLM failed: {vlm['error']}")
    if vlm.get("parsed") is None:
        raise RuntimeError(
            f"VLM parse failed: {vlm.get('parse_error')} raw={(vlm.get('raw_content') or '')[:500]}"
        )

    parsed = vlm.get("parsed") or {}
    obs_path = WAVE_DIR / f"TRK-W64-017_RUNPOD_MF70_TEETH_VLM_OBSERVATION_{VLM_STAMP}.json"
    obs_trk = TRK_DIR / f"TRK-W64-017_RUNPOD_MF70_TEETH_VLM_OBSERVATION_{VLM_STAMP}.json"
    vlm_path = WAVE_DIR / f"ROW017_RUNPOD_MF70_TEETH_VLM_DEEPEN_{VLM_STAMP}.json"
    vlm_trk = TRK_DIR / f"ROW017_RUNPOD_MF70_TEETH_VLM_DEEPEN_{VLM_STAMP}.json"

    observation = {
        "schema_version": "1.0.0",
        "record_type": "autonomous_reviewer_observation",
        "reviewer_observation_id": f"row017_runpod_mf70_teeth_vlm_{VLM_STAMP}",
        "revision": "1",
        "status": "candidate_observation",
        "created_at": CREATED,
        "role": "vlm_critic",
        "model": VLM_MODEL,
        "runtime_host": "runpod",
        "endpoint": f"{OLLAMA}/api/chat",
        "artifact_ids": [out_sha],
        "artifact": {"path": rel(out_path), "sha256": out_sha},
        "scope_bindings": [{"region": REGION, "owner": "character_instance_row017"}],
        "observations": [
            {"defect": d, "region": "whole_frame"} for d in (parsed.get("global_defects") or [])
        ]
        or [{"defect": "none_detected", "region": REGION}],
        "metric_observations": [],
        "uncertainty": parsed.get("uncertainty"),
        "parsed_review": parsed,
        "promotion_authority": "none",
        "promotion_allowed": False,
        "row_complete_allowed": False,
        "evidence_ids": [global_review, visual_qa],
        "provenance": {
            "producer": "tmp_row017_runpod_mf70_teeth_vlm_deepen.py",
            "source_refs": [rel(receipt_path), rel(out_path)],
            "evidence_refs": [global_review, producer_packet],
        },
    }

    deepen = {
        "schema_version": "1.0",
        "evidence_id": f"ROW017-RUNPOD-MF70-TEETH-VLM-DEEPEN-{VLM_STAMP}",
        "created_iso": CREATED,
        "tracker_id": "TRK-W64-017",
        "item_id": "ITEM-W64-017",
        "mutation_this_landing": "mf70_teeth_producer_plus_ollama_vlm_deepen",
        "producer_stamp": stamp,
        "vlm_stamp": VLM_STAMP,
        "proof_tier": "VISUAL_QA_PASS_BOUNDED",
        "vlm_tier": "VLM_OBSERVATION_BOUNDED",
        "highest_proof_tier_achieved": "VISUAL_QA_PASS_BOUNDED",
        "row_complete": False,
        "product_completion_claimed": False,
        "runtime_host": "runpod",
        "vlm_model": VLM_MODEL,
        "vlm_ok": bool(vlm.get("ok")),
        "vlm_attempted": bool(vlm.get("attempted")),
        "output_sha256": out_sha,
        "producer_packet": producer_packet,
        "global_review": global_review,
        "visual_qa": visual_qa,
        "vlm_observation": rel(obs_path),
        "vlm_raw": {
            "ok": vlm.get("ok"),
            "parse_error": vlm.get("parse_error"),
            "eval_count": vlm.get("ollama_eval_count"),
            "prompt_eval_count": vlm.get("ollama_prompt_eval_count"),
            "total_duration_ns": vlm.get("total_duration_ns"),
            "error": vlm.get("error"),
        },
        "decision": {
            "status": "advanced_bounded_with_vlm",
            "row_complete": False,
            "product_completion": False,
            "safe_next_action": (
                "Keep Row017 blocked/non-complete; prefer next unused prepared localized lane "
                "(e.g. mf70_eyelashes / mf70_eyebrows) when queue idle, or Row010 face-tighter personal-calib re-VLM; "
                "leave Row074 alone; no HOLD 090+; no COMPLETE."
            ),
        },
        "boundaries": {
            "complete_claimed": False,
            "csv_mutated": False,
            "row074_touched": False,
            "hold_090_plus_touched": False,
            "media_invented": False,
            "comfy_rerun": False,
        },
        "ledger_status_unchanged": "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending",
    }

    for path, payload in (
        (obs_path, observation),
        (obs_trk, observation),
        (vlm_path, deepen),
        (vlm_trk, deepen),
    ):
        write_json(path, payload)
        print("wrote", rel(path))

    if ITEM.exists():
        item = json.loads(ITEM.read_text(encoding="utf-8"))
        note = (
            f"RunPod mf70_teeth producer+VLM {stamp}/{VLM_STAMP}: Ollama {VLM_MODEL}; "
            f"output sha {out_sha[:12]}...; Status remains "
            "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending; not COMPLETE."
        )
        item["exact_blocker"] = (
            "Class E residual active — future localized producer GLOBAL_REVIEW contract now has "
            "RunPod mf70_teeth emission packaging + bounded VLM observation, but product "
            "campaign acceptance still pending; not COMPLETE."
        )
        item["next_action"] = deepen["decision"]["safe_next_action"]
        evid = item.setdefault("evidence", [])
        for p in [global_review, visual_qa, producer_packet, rel(vlm_path), rel(obs_path)]:
            if p not in evid:
                evid.append(p)
        item["future_producer_emission_proof_readiness"] = {
            "future_producer_emission_proof_package_present": True,
            "runtime_host": "runpod",
            "latest_producer_stamp": stamp,
            "latest_vlm_stamp": VLM_STAMP,
            "latest_region": REGION,
            "vlm_model": VLM_MODEL,
            "output_sha256": out_sha,
            "row_complete": False,
        }
        item["notes"] = note
        item["row_complete"] = False
        item["status"] = "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending"
        write_json(ITEM, item)
        print("patched", rel(ITEM))

    handoff = {
        "created_iso": CREATED,
        "producer_stamp": stamp,
        "vlm_stamp": VLM_STAMP,
        "output_sha256": out_sha,
        "prompt_id": receipt.get("prompt_id"),
        "vlm_model": VLM_MODEL,
        "vlm_ok": vlm.get("ok"),
        "parsed": parsed,
        "paths": {
            "global_review": global_review,
            "visual_qa": visual_qa,
            "producer_packet": producer_packet,
            "vlm_deepen": rel(vlm_path),
            "vlm_observation": rel(obs_path),
            "pullback": rel(out_dir),
            "item": rel(ITEM),
        },
        "row_complete": False,
        "next_action": deepen["decision"]["safe_next_action"],
    }
    write_json(out_dir / "VLM_DEEPEN_SUMMARY.json", handoff)
    write_json(runtime_dir / "VLM_DEEPEN_SUMMARY.json", handoff)
    print(json.dumps(handoff, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print("FATAL", exc, file=sys.stderr)
        raise
