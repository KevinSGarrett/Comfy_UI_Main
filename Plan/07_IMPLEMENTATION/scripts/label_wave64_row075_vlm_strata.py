#!/usr/bin/env python3
"""Row075 autonomous VLM strata labeling (metadata + self-hosted VLM).

Labels the library_unlabeled shortlist under autonomous_authority=VLM_METADATA.
Does NOT:
  - unfreeze threshold authority
  - claim product COMPLETE / row_complete
  - promote labels to human_gold truth
  - decode library PCM (leave Row074 exclusive PCM alone)
  - emit HOLD 090+
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Plan" / "07_IMPLEMENTATION" / "scripts"))

from wave64_autonomous_vlm_client import (  # noqa: E402
    DEFAULT_MODEL,
    Wave64VlmClientError,
    extract_json_object,
    generate_text,
    probe_endpoint,
)

CHI = ZoneInfo("America/Chicago")
TRACKER_ID = "TRK-W64-075"
ITEM_ID = "ITEM-W64-075"
AUTONOMOUS_AUTHORITY = "VLM_METADATA"
ALLOWED_DEFECT_CODES = (
    "clipping",
    "hiss",
    "hum",
    "clicks",
    "dropouts",
    "codec_damage",
    "excessive_noise",
    "unintelligible_speech_contamination",
    "truncation",
    "unsuitable_background_layers",
    "severe_pre_reverb",
    "none",
)
STRATA_PACKET = Path(
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-075_LIBRARY_BENCHMARK_STRATA_CANDIDATE_PACKET_20260720.json"
)
DELTA_QA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-075_AUDIO_QUALITY_DEFECT_CURRENT_DELTA_20260719.json"
)
DELTA_TRK = Path(
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-075_AUDIO_QUALITY_DEFECT_CURRENT_DELTA_20260719.json"
)
THRESHOLD_REGISTRY = Path(
    "Plan/10_REGISTRIES/wave64_row075_audio_defect_threshold_registry.json"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def metadata_proxy_label(candidate: dict[str, Any]) -> dict[str, Any]:
    """Deterministic metadata proxy when live VLM unavailable (still not human_gold)."""
    status = str(candidate.get("truth_label_status") or "pending")
    measured = [
        str(c)
        for c in (candidate.get("severe_defect_codes") or [])
        if isinstance(c, str) and c in ALLOWED_DEFECT_CODES and c != "none"
    ]
    if status == "blocked":
        return {
            "vlm_label_status": "blocked",
            "vlm_severe_defect_codes": [],
            "confidence": 0.35,
            "rationale": (
                "Metadata proxy: retained defect_status=blocked; no library PCM decode; "
                "autonomous VLM authority records blocked without inventing human-gold truth."
            ),
            "source": "metadata_proxy",
        }
    return {
        "vlm_label_status": "labeled",
        "vlm_severe_defect_codes": measured,
        "confidence": 0.55 if measured else 0.45,
        "rationale": (
            "Metadata proxy: propose measured severe codes as VLM_METADATA candidates only; "
            "not promoted to human_gold or threshold unfreeze."
        ),
        "source": "metadata_proxy",
    }


def build_prompt(candidate: dict[str, Any]) -> str:
    payload = {
        "candidate_id": candidate.get("candidate_id"),
        "stratum_id": candidate.get("stratum_id"),
        "role": candidate.get("role"),
        "event_type": candidate.get("event_type"),
        "extension": candidate.get("extension"),
        "defect_status": candidate.get("defect_status"),
        "technical_defect_pass": candidate.get("technical_defect_pass"),
        "blocker_code": candidate.get("blocker_code"),
        "severe_defect_codes_measured": candidate.get("severe_defect_codes"),
        "sample_rate_hz": candidate.get("sample_rate_hz"),
        "channels": candidate.get("channels"),
        "frame_count": candidate.get("frame_count"),
        "production_eligibility": candidate.get("production_eligibility"),
        "allowed_defect_codes": list(ALLOWED_DEFECT_CODES),
    }
    return (
        "You are Wave64 Row075 autonomous audio-defect strata labeler.\n"
        "Using ONLY the metadata JSON (no waveform access), propose severe defect codes.\n"
        "Return JSON object with keys: vlm_severe_defect_codes (array of allowed codes or empty), "
        "vlm_label_status (labeled|blocked), confidence (0..1), rationale (short string).\n"
        "If defect_status is blocked or blocker_code is set, prefer vlm_label_status=blocked.\n"
        "Do not invent human_gold truth. Do not claim COMPLETE.\n"
        f"METADATA:\n{json.dumps(payload, sort_keys=True)}"
    )


def normalize_vlm_label(raw: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    status = str(raw.get("vlm_label_status") or "").strip().lower()
    if status not in {"labeled", "blocked"}:
        status = "blocked" if candidate.get("truth_label_status") == "blocked" else "labeled"
    codes_in = raw.get("vlm_severe_defect_codes") or []
    codes: list[str] = []
    if isinstance(codes_in, list):
        for item in codes_in:
            code = str(item).strip()
            if code in ALLOWED_DEFECT_CODES and code != "none" and code not in codes:
                codes.append(code)
    conf = raw.get("confidence")
    try:
        confidence = float(conf)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))
    rationale = str(raw.get("rationale") or "vlm_label").strip()[:500]
    return {
        "vlm_label_status": status,
        "vlm_severe_defect_codes": codes,
        "confidence": confidence,
        "rationale": rationale,
        "source": "live_vlm",
    }


def label_candidate_live(
    candidate: dict[str, Any],
    *,
    base_url: str,
    model: str,
) -> dict[str, Any]:
    result = generate_text(
        build_prompt(candidate),
        base_url=base_url,
        model=model,
        system=(
            "Emit only JSON for Wave64 autonomous VLM_METADATA defect strata labels. "
            "Never claim human_gold or product completion."
        ),
        format_json=True,
        temperature=0.0,
        timeout_s=180,
    )
    parsed = result.get("parsed_json") or extract_json_object(str(result.get("raw_text") or ""))
    if not parsed:
        raise Wave64VlmClientError("vlm_json_parse_failed")
    label = normalize_vlm_label(parsed, candidate)
    label["model"] = model
    label["eval_count"] = result.get("eval_count")
    label["total_duration_ns"] = result.get("total_duration_ns")
    return label


def apply_labels(
    strata: dict[str, Any],
    *,
    base_url: str | None,
    model: str,
    allow_metadata_proxy: bool,
) -> dict[str, Any]:
    unlabeled = [
        c
        for c in strata.get("candidates") or []
        if isinstance(c, dict) and c.get("truth_label_status") in {"pending", "blocked"}
    ]
    probe: dict[str, Any]
    live_ok = False
    try:
        probe = probe_endpoint(base_url, timeout_s=8.0)
        live_ok = bool(probe.get("reachable")) and model in (probe.get("models") or [])
        if not live_ok and probe.get("reachable") and (probe.get("models") or []):
            # model missing: still attempt if any models present (fail per-call)
            live_ok = True
    except Wave64VlmClientError as exc:
        probe = {"reachable": False, "error": str(exc), "base_url": base_url}
        live_ok = False

    labeled_rows: list[dict[str, Any]] = []
    for candidate in unlabeled:
        row = {
            "candidate_id": candidate.get("candidate_id"),
            "stratum_id": candidate.get("stratum_id"),
            "truth_label_status_retained": candidate.get("truth_label_status"),
            "measured_severe_defect_codes_not_promoted_to_human_gold": list(
                candidate.get("severe_defect_codes") or []
            ),
            "relative_path": candidate.get("relative_path"),
            "asset_id": candidate.get("asset_id"),
            "canonical_pcm_sha256": candidate.get("canonical_pcm_sha256"),
            "library_pcm_decode_invoked": False,
            "human_gold": False,
            "autonomous_authority": AUTONOMOUS_AUTHORITY,
        }
        try:
            if not live_ok:
                raise Wave64VlmClientError("endpoint_or_model_unavailable")
            label = label_candidate_live(candidate, base_url=probe["base_url"], model=model)
            row.update(label)
            row["endpoint_status"] = "live"
        except Wave64VlmClientError as exc:
            if not allow_metadata_proxy:
                raise
            proxy = metadata_proxy_label(candidate)
            row.update(proxy)
            row["endpoint_status"] = "metadata_proxy_fallback"
            row["endpoint_error"] = str(exc)
            row["model"] = model
        labeled_rows.append(row)

    vlm_labeled = sum(1 for r in labeled_rows if r.get("vlm_label_status") == "labeled")
    vlm_blocked = sum(1 for r in labeled_rows if r.get("vlm_label_status") == "blocked")
    live_count = sum(1 for r in labeled_rows if r.get("endpoint_status") == "live")
    proxy_count = sum(
        1 for r in labeled_rows if r.get("endpoint_status") == "metadata_proxy_fallback"
    )

    now_chi = datetime.now(CHI)
    stamp = now_chi.strftime("%Y%m%dT%H%M%S") + "-0500"
    packet = {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-075_VLM_AUTONOMOUS_STRATA_LABEL_PACKET_{stamp}",
        "created_iso": now_chi.isoformat(timespec="seconds"),
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "autonomous_authority": AUTONOMOUS_AUTHORITY,
        "proof_tier": "AUTONOMOUS_VLM_STRATA_LABEL_BOUNDED",
        "row_complete": False,
        "product_completion_claimed": False,
        "threshold_authority_unfrozen": False,
        "library_pcm_decode_invoked": False,
        "row074_pcm_left_alone": True,
        "hold_090_plus_emitted": False,
        "source_strata_packet": {
            "path": str(STRATA_PACKET).replace("\\", "/"),
            "sha256": sha256_file(ROOT / STRATA_PACKET),
        },
        "threshold_registry": {
            "path": str(THRESHOLD_REGISTRY).replace("\\", "/"),
            "active_revision": "wave64_row075_audio_defect_thresholds_v0.1.0",
            "still_frozen_synthetic_only": True,
        },
        "vlm_endpoint": probe,
        "model": model,
        "counts": {
            "shortlist_unlabeled_input": len(unlabeled),
            "vlm_labeled": vlm_labeled,
            "vlm_blocked": vlm_blocked,
            "live_vlm": live_count,
            "metadata_proxy_fallback": proxy_count,
            "truth_human_gold_still_absent": True,
            "synthetic_fixture_truth_labeled_retained": 5,
        },
        "labels": labeled_rows,
        "blocker_codes_retained": [
            "CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT",
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "LIBRARY_DEFECT_TRUTH_HUMAN_GOLD_LABELS_ABSENT",
        ],
        "decision": {
            "status": "blocked",
            "row075_acceptance": "held",
            "autonomous_vlm_strata_labels_present": len(labeled_rows) == 8,
            "human_gold_cleared": False,
            "threshold_authority_unfrozen": False,
            "product_completion": False,
            "safe_next_action": (
                "Retain VLM_METADATA strata labels as autonomous non-human-gold authority. "
                "Do not unfreeze thresholds or claim COMPLETE until calibrated library strata "
                "policy accepts this authority tier (or human-gold arrives). Leave Row074 PCM alone."
            ),
        },
        "notes": [
            "Autonomous substitute for prior Class F human-gold stop on 8 unlabeled shortlist rows.",
            "truth_label_status human_gold fields remain pending/blocked; VLM labels are parallel.",
            "Measured severities are never silently promoted to human_gold.",
            "No library PCM decode; Row074 exclusive PCM lane left alone.",
        ],
    }
    sealed = {k: v for k, v in packet.items() if k != "packet_sha256"}
    packet["packet_sha256"] = sha256_bytes(
        json.dumps(sealed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if packet["product_completion_claimed"] or packet["threshold_authority_unfrozen"]:
        raise RuntimeError("row075_vlm_packet_must_refuse_complete_and_unfreeze")
    if len(labeled_rows) != 8:
        raise RuntimeError(f"expected_8_unlabeled_got_{len(labeled_rows)}")
    return packet


def update_delta(delta_path: Path, packet: dict[str, Any], packet_rel: str) -> None:
    delta = load_json(delta_path)
    delta["updated_at"] = packet["created_utc"]
    delta["vlm_autonomous_strata_label_deepen"] = {
        "deepened_at": packet["created_iso"],
        "packet": packet_rel,
        "packet_sha256": packet["packet_sha256"],
        "autonomous_authority": AUTONOMOUS_AUTHORITY,
        "proof_tier": packet["proof_tier"],
        "vlm_labeled": packet["counts"]["vlm_labeled"],
        "vlm_blocked": packet["counts"]["vlm_blocked"],
        "live_vlm": packet["counts"]["live_vlm"],
        "metadata_proxy_fallback": packet["counts"]["metadata_proxy_fallback"],
        "threshold_authority_unfrozen": False,
        "product_completion": False,
        "row074_pcm_left_alone": True,
        "blocker_codes_retained": packet["blocker_codes_retained"],
        "verdict": "VLM_METADATA_STRATA_LABELS_BOUNDED_THRESHOLDS_STILL_FROZEN",
    }
    caps = delta.setdefault("implemented_slice", {}).setdefault("capabilities_now_present", [])
    if isinstance(caps, list) and "vlm_metadata_autonomous_strata_labels" not in caps:
        caps.append("vlm_metadata_autonomous_strata_labels")
    not_claimed = delta.setdefault("implemented_slice", {}).setdefault(
        "explicitly_not_claimed", []
    )
    for item in (
        "threshold_authority_unfrozen",
        "row075_product_completion",
        "human_gold_library_defect_truth_labels",
    ):
        if isinstance(not_claimed, list) and item not in not_claimed:
            not_claimed.append(item)
    decision = delta.setdefault("decision", {})
    decision["threshold_authority_unfrozen"] = False
    decision["product_completion"] = False
    decision["status"] = "blocked"
    decision["safe_next_action"] = packet["decision"]["safe_next_action"]
    delta["row_complete"] = False
    delta["qa_decision"] = (
        "vlm_metadata_autonomous_strata_labels_bounded;"
        "thresholds_still_frozen;human_gold_absent;no_product_complete"
    )
    write_json(delta_path, delta)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--allow-metadata-proxy",
        action="store_true",
        default=True,
        help="Fall back to deterministic metadata proxy if live VLM fails (default on).",
    )
    parser.add_argument("--no-metadata-proxy", action="store_false", dest="allow_metadata_proxy")
    parser.add_argument("--skip-delta", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    strata = load_json(root / STRATA_PACKET)
    packet = apply_labels(
        strata,
        base_url=args.base_url,
        model=args.model,
        allow_metadata_proxy=args.allow_metadata_proxy,
    )
    stamp = packet["evidence_id"].rsplit("_", 1)[-1]
    out_qa = (
        root
        / "Plan/Instructions/QA/Evidence/Wave64"
        / f"TRK-W64-075_VLM_AUTONOMOUS_STRATA_LABEL_PACKET_{stamp}.json"
    )
    out_alias = (
        root
        / "Plan/Instructions/QA/Evidence/Wave64"
        / "TRK-W64-075_VLM_AUTONOMOUS_STRATA_LABEL_PACKET_20260720.json"
    )
    out_trk = (
        root
        / "Plan/Tracker/Evidence/Wave64"
        / f"TRK-W64-075_VLM_AUTONOMOUS_STRATA_LABEL_PACKET_{stamp}.json"
    )
    write_json(out_qa, packet)
    write_json(out_alias, packet)
    write_json(out_trk, packet)
    rel = str(out_alias.relative_to(root)).replace("\\", "/")
    if not args.skip_delta:
        update_delta(root / DELTA_QA, packet, rel)
        if (root / DELTA_TRK).is_file():
            update_delta(root / DELTA_TRK, packet, rel)
        else:
            write_json(root / DELTA_TRK, load_json(root / DELTA_QA))
    print(
        json.dumps(
            {
                "packet": rel,
                "packet_sha256": packet["packet_sha256"],
                "vlm_labeled": packet["counts"]["vlm_labeled"],
                "vlm_blocked": packet["counts"]["vlm_blocked"],
                "live_vlm": packet["counts"]["live_vlm"],
                "metadata_proxy_fallback": packet["counts"]["metadata_proxy_fallback"],
                "threshold_authority_unfrozen": False,
                "product_completion": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
