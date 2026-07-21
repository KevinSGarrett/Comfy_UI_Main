#!/usr/bin/env python3
"""Wave64 RunPod strict self-hosted LLM visual QA (fail-closed product authority).

BINDING:
  - RunPod Ollama only (WAVE64_VLM_URL). NEVER EC2. NEVER local Comfy runtime.
  - Product / Class A / Proof_Landed / identity GATE CLEARED require
    strict_pod_llm_review=PASS from an approved high-end vision model.
  - Default decision is REJECT unless all high bars clear.
  - Generation receipt / pipeline-ran is NEVER visual approval.
  - Smoke may use a weaker model but MUST set lane=SMOKE.

Env:
  WAVE64_VLM_URL                 → OLLAMA_HOST → http://127.0.0.1:11434
  WAVE64_STRICT_VLM_MODEL        → qwen2.5vl:32b
  WAVE64_VLM_SMOKE_MODEL         → qwen2.5vl:7b
  WAVE64_COMFY_URL               → http://127.0.0.1:8188
  WAVE64_STRICT_VLM_KEEP_ALIVE   → 0 (unload after review)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from wave64_autonomous_vlm_client import (  # noqa: E402
    Wave64VlmClientError,
    chat_with_images,
    probe_endpoint,
    resolve_base_url,
    resolve_strict_vlm_model,
    resolve_smoke_vlm_model,
)

SCHEMA_VERSION = "wave64.pod_strict_visual_qa.v1"
DEFAULT_COMFY_URL = "http://127.0.0.1:8188"
DEFAULT_POD_ID = "1q4ji0gg1fkhvt"

# High bars — default REJECT. Do not weaken to chase PASS.
THRESHOLDS: dict[str, int | float] = {
    "anatomy_hands_fingers_min": 90,
    "identity_consistency_min": 85,
    "skin_realism_min": 85,
    "motion_temporal_min": 90,
    "artifacts_cleanliness_min": 85,
    "prompt_adherence_min": 85,
    "policy_project_min": 90,
    "reviewer_confidence_min": 0.75,
}

PRODUCT_LANES = frozenset({"PRODUCT", "CLASS_A", "PROOF_LANDED", "IDENTITY_GATE"})
APPROVED_STRICT_MODELS = frozenset(
    {
        "qwen2.5vl:32b",
        "qwen2.5vl:72b",
        "qwen2.5-vl:32b",
        "qwen2.5-vl:72b",
    }
)
# Explicitly forbidden as product authority (historical rubber-stamp / weak path).
FORBIDDEN_PRODUCT_MODELS = frozenset(
    {
        "qwen2.5vl:7b",
        "qwen3-vl:4b-instruct-q4_K_M",
        "qwen3-vl:8b-instruct-q4_K_M",
        "llava:13b",
        "llama3.2-vision:11b",
        "qwen2.5:7b-instruct",
    }
)

STRICT_SYSTEM_RUBRIC = """You are a STRICT visual QA reviewer for a self-hosted ComfyUI production system.
Default decision is REJECT. Approve ONLY when evidence is clearly strong.

You MUST inspect every provided frame carefully for:
1) anatomy_hands_fingers — finger count, separation, mush/fusion, joints
2) identity_consistency — face/body identity vs intent (or mark applicable=false if no identity claim)
3) skin_realism — plastic/waxy/oversmooth vs natural microdetail
4) motion_temporal — for multi-frame video: breath, blink, weight-shift, non-static living motion; REJECT near-static living-stills that claim motion
5) artifacts_cleanliness — warping, mush, compression, limb melt, background tears
6) prompt_adherence — does the image match the stated intent
7) policy_project — project/NSFW policy coherence when applicable

FORBIDDEN rubber-stamps:
- Do NOT PASS because a pipeline/job/receipt completed.
- Do NOT PASS because a weaker VLM previously said PASS.
- Do NOT PASS near-static video that only shows tiny pixel jitter.
- Do NOT PASS mushy/fused hands even if face looks OK.
- When uncertain, REJECT and give correction guidance.

Return ONLY JSON with this shape:
{
  "anatomy_hands_fingers": {"score": 0-100, "applicable": true, "notes": "..."},
  "identity_consistency": {"score": 0-100, "applicable": true/false, "notes": "..."},
  "skin_realism": {"score": 0-100, "applicable": true, "notes": "..."},
  "motion_temporal": {"score": 0-100, "applicable": true/false, "notes": "..."},
  "artifacts_cleanliness": {"score": 0-100, "applicable": true, "notes": "..."},
  "prompt_adherence": {"score": 0-100, "applicable": true, "notes": "..."},
  "policy_project": {"score": 0-100, "applicable": true, "notes": "..."},
  "blocking_defects": [{"code":"...","severity":"blocking|major|minor","detail":"...","region":"..."}],
  "correction_guidance": ["..."],
  "reviewer_confidence": 0.0-1.0,
  "proposed_decision": "PASS"|"REJECT",
  "summary": "..."
}
"""


class StrictVisualQaError(RuntimeError):
    pass


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise StrictVisualQaError(f"http_{exc.code}:{detail[:400]}") from exc
    except Exception as exc:  # noqa: BLE001
        raise StrictVisualQaError(f"transport_error:{type(exc).__name__}:{exc}") from exc
    if not body.strip():
        return {}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise StrictVisualQaError(f"non_json_response:{body[:200]}") from exc
    if not isinstance(parsed, dict):
        raise StrictVisualQaError("response_not_object")
    return parsed


def resolve_comfy_url(explicit: str | None = None) -> str:
    raw = explicit or os.environ.get("WAVE64_COMFY_URL") or DEFAULT_COMFY_URL
    return str(raw).strip().rstrip("/")


def gpu_memory_mib() -> dict[str, float | None]:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=15,
        ).strip()
        total_s, used_s, free_s = [p.strip() for p in out.split(",")[:3]]
        return {
            "total_mib": float(total_s),
            "used_mib": float(used_s),
            "free_mib": float(free_s),
        }
    except Exception:  # noqa: BLE001
        return {"total_mib": None, "used_mib": None, "free_mib": None}


def comfy_queue_idle(comfy_url: str | None = None, *, timeout_s: float = 10.0) -> bool:
    base = resolve_comfy_url(comfy_url)
    try:
        q = _http_json("GET", f"{base}/queue", timeout_s=timeout_s)
    except StrictVisualQaError:
        return False
    running = q.get("queue_running") or []
    pending = q.get("queue_pending") or []
    return len(running) == 0 and len(pending) == 0


def comfy_unload_models(comfy_url: str | None = None, *, timeout_s: float = 120.0) -> dict[str, Any]:
    base = resolve_comfy_url(comfy_url)
    before = gpu_memory_mib()
    try:
        _http_json(
            "POST",
            f"{base}/free",
            {"unload_models": True, "free_memory": True},
            timeout_s=timeout_s,
        )
        ok = True
        err = None
    except StrictVisualQaError as exc:
        ok = False
        err = str(exc)
    time.sleep(2.0)
    after = gpu_memory_mib()
    return {
        "ok": ok,
        "error": err,
        "before": before,
        "after": after,
        "comfy_url": base,
    }


def ollama_show(model: str, *, base_url: str | None = None, timeout_s: float = 60.0) -> dict[str, Any]:
    base = resolve_base_url(base_url)
    return _http_json("POST", f"{base}/api/show", {"name": model}, timeout_s=timeout_s)


def ollama_model_present(model: str, *, base_url: str | None = None) -> bool:
    probe = probe_endpoint(base_url)
    names = set(probe.get("models") or [])
    if model in names:
        return True
    # tolerate tagless / alternate separators
    alts = {model.replace("-", ""), model.replace(":", "-")}
    return bool(names & alts) or any(model in n or n in model for n in names)


def unload_ollama_model(model: str, *, base_url: str | None = None) -> None:
    base = resolve_base_url(base_url)
    keep = os.environ.get("WAVE64_STRICT_VLM_KEEP_ALIVE", "0").strip() or "0"
    try:
        _http_json(
            "POST",
            f"{base}/api/generate",
            {"model": model, "prompt": "", "keep_alive": 0 if keep == "0" else keep},
            timeout_s=60.0,
        )
    except StrictVisualQaError:
        pass


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def encode_image(path: Path, *, max_side: int = 896) -> str:
    """Return base64 PNG/JPEG bytes; optionally downscale large frames via ffmpeg-free path."""
    raw = path.read_bytes()
    # Prefer pillow when available for resize; else raw bytes.
    try:
        from io import BytesIO

        from PIL import Image  # type: ignore

        img = Image.open(BytesIO(raw)).convert("RGB")
        w, h = img.size
        scale = min(1.0, float(max_side) / float(max(w, h)))
        if scale < 1.0:
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:  # noqa: BLE001
        return base64.b64encode(raw).decode("ascii")


def _score_cell(raw: Any, *, min_score: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"score": None, "applicable": True, "pass": False, "notes": "missing_score_cell"}
    applicable = raw.get("applicable", True)
    if applicable is False:
        return {
            "score": None,
            "applicable": False,
            "pass": True,
            "notes": str(raw.get("notes") or "not_applicable"),
        }
    score = raw.get("score")
    try:
        score_i = int(score)
    except (TypeError, ValueError):
        return {"score": None, "applicable": True, "pass": False, "notes": "non_integer_score"}
    score_i = max(0, min(100, score_i))
    return {
        "score": score_i,
        "applicable": True,
        "pass": score_i >= int(min_score),
        "notes": str(raw.get("notes") or ""),
    }


def apply_thresholds(parsed: dict[str, Any], *, media_kind: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], str, float]:
    scores = {
        "anatomy_hands_fingers": _score_cell(
            parsed.get("anatomy_hands_fingers"),
            min_score=int(THRESHOLDS["anatomy_hands_fingers_min"]),
        ),
        "identity_consistency": _score_cell(
            parsed.get("identity_consistency"),
            min_score=int(THRESHOLDS["identity_consistency_min"]),
        ),
        "skin_realism": _score_cell(
            parsed.get("skin_realism"),
            min_score=int(THRESHOLDS["skin_realism_min"]),
        ),
        "motion_temporal": _score_cell(
            parsed.get("motion_temporal"),
            min_score=int(THRESHOLDS["motion_temporal_min"]),
        ),
        "artifacts_cleanliness": _score_cell(
            parsed.get("artifacts_cleanliness"),
            min_score=int(THRESHOLDS["artifacts_cleanliness_min"]),
        ),
        "prompt_adherence": _score_cell(
            parsed.get("prompt_adherence"),
            min_score=int(THRESHOLDS["prompt_adherence_min"]),
        ),
        "policy_project": _score_cell(
            parsed.get("policy_project"),
            min_score=int(THRESHOLDS["policy_project_min"]),
        ),
    }
    # Stills: motion may be N/A unless model marked applicable.
    if media_kind == "still" and scores["motion_temporal"]["applicable"] and scores["motion_temporal"]["score"] is None:
        scores["motion_temporal"] = {
            "score": None,
            "applicable": False,
            "pass": True,
            "notes": "still_image_motion_not_applicable",
        }

    defects_raw = parsed.get("blocking_defects") if isinstance(parsed.get("blocking_defects"), list) else []
    defects: list[dict[str, Any]] = []
    for item in defects_raw:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "unspecified").strip() or "unspecified"
        sev = str(item.get("severity") or "blocking").strip().lower()
        if sev not in {"blocking", "major", "minor"}:
            sev = "blocking"
        defects.append(
            {
                "code": code,
                "severity": sev,
                "detail": str(item.get("detail") or "").strip() or code,
                "region": str(item.get("region") or "unspecified"),
            }
        )

    guidance = []
    for g in parsed.get("correction_guidance") or []:
        if isinstance(g, str) and g.strip():
            guidance.append(g.strip())

    try:
        confidence = float(parsed.get("reviewer_confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    blocking = [d for d in defects if d["severity"] == "blocking"]
    category_fail = [k for k, v in scores.items() if not v.get("pass")]
    proposed = str(parsed.get("proposed_decision") or "REJECT").strip().upper()
    if proposed not in {"PASS", "REJECT"}:
        proposed = "REJECT"

    decision = "REJECT"
    if (
        proposed == "PASS"
        and not blocking
        and not category_fail
        and confidence >= float(THRESHOLDS["reviewer_confidence_min"])
    ):
        decision = "PASS"
    else:
        decision = "REJECT"
        if not guidance:
            if category_fail:
                guidance.append(
                    "Raise quality on failing rubric cells: " + ", ".join(category_fail)
                )
            if blocking:
                guidance.append("Fix blocking defects before re-submit.")
            guidance.append("Default is REJECT; regenerate with stronger anatomy/motion controls.")

    return scores, defects, guidance, decision, confidence


def build_prompt(*, intent: str, media_kind: str, frame_names: list[str], lane: str) -> str:
    return (
        f"LANE={lane}. MEDIA_KIND={media_kind}. FRAMES={frame_names}.\n"
        f"STATED_INTENT:\n{intent.strip() or '(unspecified)'}\n\n"
        "Score strictly. Near-static video claiming living motion must REJECT. "
        "Mushy/fused/melted hands must REJECT. Plastic/waxy skin in product lanes should REJECT. "
        "Return JSON only."
    )


def review_images(
    image_paths: list[Path],
    *,
    lane: str,
    intent: str,
    media_kind: str,
    model: str | None = None,
    require_idle_comfy: bool = True,
    unload_comfy: bool = True,
    unload_vlm_after: bool = True,
    timeout_s: float = 600.0,
    expected_decision: str | None = None,
    fixture_role: str = "none",
    prompt_id: str | None = None,
    human_frame_read_status: str = "not_run",
) -> dict[str, Any]:
    lane_u = lane.strip().upper()
    if lane_u not in PRODUCT_LANES | {"SMOKE"}:
        raise StrictVisualQaError(f"invalid_lane:{lane}")

    if lane_u == "SMOKE":
        resolved_model = model or resolve_smoke_vlm_model()
        approved = False
        role = "smoke_only_reviewer"
    else:
        resolved_model = model or resolve_strict_vlm_model()
        if resolved_model in FORBIDDEN_PRODUCT_MODELS:
            raise StrictVisualQaError(
                f"forbidden_product_model:{resolved_model}:"
                "weak VLM cannot authorize PRODUCT/CLASS_A/PROOF_LANDED/IDENTITY_GATE"
            )
        if resolved_model not in APPROVED_STRICT_MODELS and not str(
            os.environ.get("WAVE64_STRICT_VLM_ALLOW_UNLISTED", "")
        ).strip():
            # Allow exact env override when operator pins a newer high-end tag.
            if not os.environ.get("WAVE64_STRICT_VLM_MODEL"):
                raise StrictVisualQaError(f"unapproved_strict_model:{resolved_model}")
        approved = True
        role = "strict_product_reviewer"

    if not image_paths:
        raise StrictVisualQaError("images_required")
    for path in image_paths:
        if not path.is_file():
            raise StrictVisualQaError(f"missing_image:{path}")

    base = resolve_base_url()
    if not ollama_model_present(resolved_model, base_url=base):
        raise StrictVisualQaError(
            f"strict_model_missing:{resolved_model}:fail_closed_pull_required"
        )

    vram_before = gpu_memory_mib()
    unload_receipt: dict[str, Any] | None = None
    if unload_comfy:
        if require_idle_comfy and not comfy_queue_idle():
            raise StrictVisualQaError("comfy_queue_not_idle_refuse_unload")
        unload_receipt = comfy_unload_models()
        if not unload_receipt.get("ok"):
            # Still continue if free VRAM looks ample, else fail closed for large models.
            free = (vram_before.get("free_mib") or 0.0)
            if free < 22000 and lane_u != "SMOKE":
                raise StrictVisualQaError(
                    f"comfy_unload_failed_insufficient_free_vram:{free}:{unload_receipt.get('error')}"
                )

    vram_after_unload = gpu_memory_mib()
    show: dict[str, Any] = {}
    try:
        show = ollama_show(resolved_model, base_url=base)
    except StrictVisualQaError as exc:
        if lane_u != "SMOKE":
            raise StrictVisualQaError(f"ollama_show_failed:{exc}") from exc

    images_b64 = [encode_image(p) for p in image_paths]
    user_prompt = build_prompt(
        intent=intent,
        media_kind=media_kind,
        frame_names=[p.name for p in image_paths],
        lane=lane_u,
    )
    # Prepend rubric as part of user content (Ollama chat path used by client).
    full_prompt = STRICT_SYSTEM_RUBRIC + "\n\n" + user_prompt

    try:
        chat = chat_with_images(
            full_prompt,
            images_b64,
            base_url=base,
            model=resolved_model,
            timeout_s=timeout_s,
            temperature=0.0,
            format_json=True,
            num_predict=1200,
            # 128k default ctx OOMs vision+32b on 48GB when Comfy residue exists;
            # product review does not need long context.
            num_ctx=int(os.environ.get("WAVE64_STRICT_VLM_NUM_CTX", "8192")),
        )
    except Wave64VlmClientError as exc:
        raise StrictVisualQaError(f"vlm_chat_failed:{exc}") from exc
    finally:
        if unload_vlm_after:
            unload_ollama_model(resolved_model, base_url=base)

    parsed = chat.get("parsed_json") if isinstance(chat.get("parsed_json"), dict) else {}
    if not parsed:
        # Fail closed — unparseable model output is REJECT/BLOCKED for product.
        receipt = _blocked_receipt(
            lane=lane_u,
            model_name=resolved_model,
            role=role,
            approved=approved,
            image_paths=image_paths,
            media_kind=media_kind,
            reason="unparseable_model_json",
            raw=str(chat.get("raw_text") or "")[:4000],
            show=show,
            vram_before=vram_before,
            vram_after_unload=vram_after_unload,
            unload_receipt=unload_receipt,
            prompt_id=prompt_id,
            human_frame_read_status=human_frame_read_status,
            fixture_role=fixture_role,
            expected_decision=expected_decision,
        )
        return receipt

    scores, defects, guidance, decision, confidence = apply_thresholds(
        parsed, media_kind=media_kind
    )

    # Product lanes: smoke/weak model already blocked above; also refuse PASS if model not approved.
    if lane_u in PRODUCT_LANES and not approved:
        decision = "REJECT"
        guidance.append("Model not approved for product strict review.")

    sha = file_sha256(image_paths[0]) if len(image_paths) == 1 else None
    expectation_met = None
    if expected_decision:
        expectation_met = decision == expected_decision.strip().upper()

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "authority": {
            "host": "runpod",
            "runtime": "ollama_self_hosted",
            "pod_id": os.environ.get("WAVE64_RUNPOD_ID", DEFAULT_POD_ID),
            "endpoint": base,
            "fail_closed": True,
            "ec2_forbidden": True,
            "local_comfy_runtime_forbidden": True,
        },
        "lane": lane_u,
        "model": {
            "name": resolved_model,
            "role": role,
            "approved_for_product": approved,
            "ollama_show_digest": (show.get("details") or {}).get("parent_model")
            if isinstance(show.get("details"), dict)
            else show.get("modelfile", "")[:80] or None,
            "ollama_show_family": (show.get("details") or {}).get("family")
            if isinstance(show.get("details"), dict)
            else None,
            "parameter_size": (show.get("details") or {}).get("parameter_size")
            if isinstance(show.get("details"), dict)
            else None,
            "ollama_show": {
                "details": show.get("details"),
                "model_info_keys": sorted(list((show.get("model_info") or {}).keys()))[:40]
                if isinstance(show.get("model_info"), dict)
                else [],
            },
        },
        "artifact": {
            "paths": [str(p) for p in image_paths],
            "sha256": sha,
            "media_kind": media_kind,
            "prompt_id": prompt_id,
            "bytes": image_paths[0].stat().st_size if len(image_paths) == 1 else None,
        },
        "vram_arbitration": {
            "comfy_unload_before_review": bool(unload_comfy),
            "comfy_queue_idle_required": bool(require_idle_comfy),
            "gpu_memory_free_mib_before": vram_before.get("free_mib"),
            "gpu_memory_free_mib_after_unload": vram_after_unload.get("free_mib"),
            "ollama_keep_alive": os.environ.get("WAVE64_STRICT_VLM_KEEP_ALIVE", "0"),
            "unload_vlm_after_review": bool(unload_vlm_after),
            "comfy_unload_receipt": unload_receipt,
            "notes": (
                "Comfy and qwen2.5vl:32b must not co-reside on RTX 6000 Ada ~48GB when "
                "Wan/Flux weights are loaded; unload Comfy via /free before strict review, "
                "then unload VLM (keep_alive=0) before the next generation."
            ),
        },
        "rubric_scores": scores,
        "thresholds": {**THRESHOLDS, "default_decision": "REJECT"},
        "blocking_defects": defects,
        "correction_guidance": guidance,
        "reviewer_confidence": confidence,
        "raw_model_response": str(chat.get("raw_text") or "")[:8000],
        "model_summary": str(parsed.get("summary") or ""),
        "overall_decision": decision,
        "strict_pod_llm_review": decision,
        "forbidden_rubber_stamp_signals": {
            "pipeline_ran_is_not_pass": True,
            "generation_receipt_is_not_pass": True,
            "weak_vlm_pass_alone_is_not_product_pass": True,
            "smoke_model_forbidden_for_product": True,
        },
        "generation_receipt_is_not_visual_approval": True,
        "product_completion_claimed": False,
        "row074_pcm_left_alone": True,
        "human_frame_read_retained": {
            "required_when_already_gated": True,
            "status": human_frame_read_status,
        },
        "self_test": {
            "fixture_role": fixture_role,
            "expected_decision": expected_decision,
            "expectation_met": expectation_met,
        },
    }
    return receipt


def _blocked_receipt(**kwargs: Any) -> dict[str, Any]:
    image_paths: list[Path] = kwargs["image_paths"]
    show = kwargs.get("show") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "authority": {
            "host": "runpod",
            "runtime": "ollama_self_hosted",
            "pod_id": os.environ.get("WAVE64_RUNPOD_ID", DEFAULT_POD_ID),
            "endpoint": resolve_base_url(),
            "fail_closed": True,
            "ec2_forbidden": True,
            "local_comfy_runtime_forbidden": True,
        },
        "lane": kwargs["lane"],
        "model": {
            "name": kwargs["model_name"],
            "role": kwargs["role"],
            "approved_for_product": kwargs["approved"],
            "ollama_show_digest": None,
            "ollama_show_family": (show.get("details") or {}).get("family")
            if isinstance(show.get("details"), dict)
            else None,
            "parameter_size": (show.get("details") or {}).get("parameter_size")
            if isinstance(show.get("details"), dict)
            else None,
        },
        "artifact": {
            "paths": [str(p) for p in image_paths],
            "sha256": file_sha256(image_paths[0]) if image_paths else None,
            "media_kind": kwargs["media_kind"],
            "prompt_id": kwargs.get("prompt_id"),
            "bytes": None,
        },
        "vram_arbitration": {
            "comfy_unload_before_review": True,
            "comfy_queue_idle_required": True,
            "gpu_memory_free_mib_before": (kwargs.get("vram_before") or {}).get("free_mib"),
            "gpu_memory_free_mib_after_unload": (kwargs.get("vram_after_unload") or {}).get(
                "free_mib"
            ),
            "ollama_keep_alive": os.environ.get("WAVE64_STRICT_VLM_KEEP_ALIVE", "0"),
            "unload_vlm_after_review": True,
            "comfy_unload_receipt": kwargs.get("unload_receipt"),
            "notes": "Blocked before or during strict review.",
        },
        "rubric_scores": {
            k: {"score": None, "applicable": True, "pass": False, "notes": kwargs["reason"]}
            for k in (
                "anatomy_hands_fingers",
                "identity_consistency",
                "skin_realism",
                "motion_temporal",
                "artifacts_cleanliness",
                "prompt_adherence",
                "policy_project",
            )
        },
        "thresholds": {**THRESHOLDS, "default_decision": "REJECT"},
        "blocking_defects": [
            {
                "code": kwargs["reason"],
                "severity": "blocking",
                "detail": kwargs["reason"],
                "region": "reviewer",
            }
        ],
        "correction_guidance": [
            "Ensure approved strict model is pulled and returns parseable JSON.",
            "Re-run after Comfy /free VRAM arbitration.",
        ],
        "reviewer_confidence": 0.0,
        "raw_model_response": kwargs.get("raw"),
        "overall_decision": "BLOCKED",
        "strict_pod_llm_review": "BLOCKED",
        "forbidden_rubber_stamp_signals": {
            "pipeline_ran_is_not_pass": True,
            "generation_receipt_is_not_pass": True,
            "weak_vlm_pass_alone_is_not_product_pass": True,
            "smoke_model_forbidden_for_product": True,
        },
        "generation_receipt_is_not_visual_approval": True,
        "product_completion_claimed": False,
        "row074_pcm_left_alone": True,
        "human_frame_read_retained": {
            "required_when_already_gated": True,
            "status": kwargs.get("human_frame_read_status") or "not_run",
        },
        "self_test": {
            "fixture_role": kwargs.get("fixture_role") or "none",
            "expected_decision": kwargs.get("expected_decision"),
            "expectation_met": (
                ("BLOCKED" == str(kwargs.get("expected_decision") or "").upper())
                if kwargs.get("expected_decision")
                else None
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", nargs="+", required=True, help="Image paths to review")
    parser.add_argument(
        "--lane",
        default="PRODUCT",
        choices=sorted(PRODUCT_LANES | {"SMOKE"}),
        help="PRODUCT/CLASS_A/PROOF_LANDED/IDENTITY_GATE require approved strict model",
    )
    parser.add_argument("--intent", default="", help="Stated generation intent / prompt summary")
    parser.add_argument(
        "--media-kind",
        default="video_frames",
        choices=["still", "video_frames", "video"],
    )
    parser.add_argument("--model", default=None, help="Override model tag")
    parser.add_argument("--out", type=Path, required=True, help="Receipt JSON output path")
    parser.add_argument("--prompt-id", default=None)
    parser.add_argument("--no-unload-comfy", action="store_true")
    parser.add_argument("--allow-busy-comfy", action="store_true")
    parser.add_argument("--keep-vlm-loaded", action="store_true")
    parser.add_argument("--timeout-s", type=float, default=600.0)
    parser.add_argument("--expected-decision", default=None, choices=["PASS", "REJECT", "BLOCKED"])
    parser.add_argument(
        "--fixture-role",
        default="none",
        choices=["known_bad", "known_better", "live_climb", "none"],
    )
    parser.add_argument(
        "--human-frame-read",
        default="not_run",
        choices=["pass", "fail", "not_run", "not_applicable"],
    )
    parser.add_argument(
        "--require-expectation",
        action="store_true",
        help="Exit non-zero if expected_decision not met",
    )
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.images]
    try:
        receipt = review_images(
            paths,
            lane=args.lane,
            intent=args.intent,
            media_kind=args.media_kind,
            model=args.model,
            require_idle_comfy=not args.allow_busy_comfy,
            unload_comfy=not args.no_unload_comfy,
            unload_vlm_after=not args.keep_vlm_loaded,
            timeout_s=args.timeout_s,
            expected_decision=args.expected_decision,
            fixture_role=args.fixture_role,
            prompt_id=args.prompt_id,
            human_frame_read_status=args.human_frame_read,
        )
    except StrictVisualQaError as exc:
        err = {
            "schema_version": SCHEMA_VERSION,
            "overall_decision": "BLOCKED",
            "strict_pod_llm_review": "BLOCKED",
            "error": str(exc),
            "product_completion_claimed": False,
            "generation_receipt_is_not_visual_approval": True,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(err, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(err, indent=2, sort_keys=True))
        return 3

    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(text)
    if args.require_expectation and args.expected_decision:
        if receipt.get("self_test", {}).get("expectation_met") is not True:
            return 2
    if receipt.get("strict_pod_llm_review") == "BLOCKED":
        return 3
    # Reviewer exit 0 even on REJECT (valid strict outcome); callers gate on field.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
