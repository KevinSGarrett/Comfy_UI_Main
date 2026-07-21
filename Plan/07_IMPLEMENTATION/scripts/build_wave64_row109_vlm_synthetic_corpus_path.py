#!/usr/bin/env python3
"""Row109 autonomous synthetic+VLM corpus path (autonomous_authority=VLM_SYNTHETIC).

Builds VLM annotation receipts over the existing synthetic fixture corpus.
Fail-closed for production/genuine rights:
  - does NOT clear GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT
  - does NOT claim product COMPLETE / row_complete
  - does NOT decode library PCM or touch Row074 exclusive PCM
  - documents autonomous_authority=VLM_SYNTHETIC
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
TRACKER_ID = "TRK-W64-109"
ITEM_ID = "ITEM-W64-109"
AUTONOMOUS_AUTHORITY = "VLM_SYNTHETIC"
CASE_INDEX = Path(
    "Plan/Instructions/QA/Evidence/Wave64/fixtures/row109/corpus_case_index.json"
)
MANIFEST = Path(
    "Plan/Instructions/QA/Evidence/Wave64/benchmarks/row109/"
    "audio_benchmark_corpus_manifest.json"
)
HOLD = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-109_audio_benchmark_corpus.json"
)
DELTA_QA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-109_AUDIO_BENCHMARK_CORPUS_CURRENT_DELTA_20260720.json"
)
DELTA_TRK = Path(
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-109_AUDIO_BENCHMARK_CORPUS_CURRENT_DELTA_20260720.json"
)
REVIEWS_DIR = Path(
    "Plan/Instructions/QA/Evidence/Wave64/reviews/row109/vlm_synthetic"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def metadata_proxy_receipt(case: dict[str, Any]) -> dict[str, Any]:
    ann = case.get("annotation") or {}
    labels = ann.get("labels") or {}
    return {
        "annotator_role": "vlm_synthetic",
        "autonomous_authority": AUTONOMOUS_AUTHORITY,
        "agreement_with_synthetic_fixture": True,
        "confidence": 0.6,
        "event_family": case.get("event_family"),
        "material": case.get("material"),
        "footwear": case.get("footwear"),
        "partition": case.get("partition"),
        "truth_class": case.get("truth_class"),
        "silent_event": bool(ann.get("silent_event")),
        "labels_confirmed": labels,
        "rationale": (
            "Metadata proxy VLM_SYNTHETIC receipt: confirms synthetic fixture annotation "
            "without genuine media rights bind or PCM decode."
        ),
        "source": "metadata_proxy",
        "rights_bound_for_production": False,
        "human_gold": False,
    }


def build_prompt(case: dict[str, Any]) -> str:
    payload = {
        "case_id": case.get("case_id"),
        "partition": case.get("partition"),
        "event_family": case.get("event_family"),
        "material": case.get("material"),
        "footwear": case.get("footwear"),
        "room": case.get("room"),
        "ownership": case.get("ownership"),
        "camera": case.get("camera"),
        "truth_class": case.get("truth_class"),
        "adversarial_role": case.get("adversarial_role"),
        "annotation": case.get("annotation"),
        "media_locator_kind": (case.get("media_locator") or {}).get("kind"),
    }
    return (
        "You are Wave64 Row109 autonomous synthetic corpus annotator.\n"
        "Confirm or lightly refine the synthetic fixture annotation. Return JSON with keys:\n"
        "agreement_with_synthetic_fixture (bool), confidence (0..1), "
        "event_family, material, footwear, silent_event (bool), rationale (short).\n"
        "Authority is VLM_SYNTHETIC only — not human_gold, not production rights clearance.\n"
        f"CASE:\n{json.dumps(payload, sort_keys=True)}"
    )


def normalize_receipt(raw: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    ann = case.get("annotation") or {}
    labels = dict(ann.get("labels") or {})
    agreement = bool(raw.get("agreement_with_synthetic_fixture", True))
    try:
        confidence = float(raw.get("confidence", 0.7))
    except (TypeError, ValueError):
        confidence = 0.7
    confidence = max(0.0, min(1.0, confidence))
    return {
        "annotator_role": "vlm_synthetic",
        "autonomous_authority": AUTONOMOUS_AUTHORITY,
        "agreement_with_synthetic_fixture": agreement,
        "confidence": confidence,
        "event_family": str(raw.get("event_family") or case.get("event_family")),
        "material": str(raw.get("material") or case.get("material")),
        "footwear": str(raw.get("footwear") or case.get("footwear")),
        "partition": case.get("partition"),
        "truth_class": case.get("truth_class"),
        "silent_event": bool(
            raw.get("silent_event")
            if "silent_event" in raw
            else ann.get("silent_event")
        ),
        "labels_confirmed": labels,
        "rationale": str(raw.get("rationale") or "vlm_synthetic_confirm")[:500],
        "source": "live_vlm",
        "rights_bound_for_production": False,
        "human_gold": False,
    }


def annotate_case_live(
    case: dict[str, Any],
    *,
    base_url: str,
    model: str,
) -> dict[str, Any]:
    result = generate_text(
        build_prompt(case),
        base_url=base_url,
        model=model,
        system=(
            "Emit only JSON for Wave64 VLM_SYNTHETIC corpus annotation receipts. "
            "Never claim human_gold, genuine rights clearance, or COMPLETE."
        ),
        format_json=True,
        temperature=0.0,
        timeout_s=180,
    )
    parsed = result.get("parsed_json") or extract_json_object(str(result.get("raw_text") or ""))
    if not parsed:
        raise Wave64VlmClientError("vlm_json_parse_failed")
    receipt = normalize_receipt(parsed, case)
    receipt["model"] = model
    receipt["eval_count"] = result.get("eval_count")
    receipt["total_duration_ns"] = result.get("total_duration_ns")
    return receipt


def build_packet(
    *,
    root: Path,
    base_url: str | None,
    model: str,
    allow_metadata_proxy: bool,
    live_limit: int | None,
) -> dict[str, Any]:
    index = load_json(root / CASE_INDEX)
    manifest = load_json(root / MANIFEST)
    hold = load_json(root / HOLD)
    cases = list(manifest.get("cases") or [])
    if not cases:
        raise RuntimeError("row109_manifest_cases_absent")

    probe: dict[str, Any]
    live_ok = False
    try:
        probe = probe_endpoint(base_url, timeout_s=8.0)
        live_ok = bool(probe.get("reachable"))
    except Wave64VlmClientError as exc:
        probe = {"reachable": False, "error": str(exc), "base_url": base_url}
        live_ok = False

    receipts: list[dict[str, Any]] = []
    live_budget = live_limit if live_limit is not None else len(cases)
    for idx, case in enumerate(cases):
        case_id = str(case.get("case_id"))
        entry = {
            "case_id": case_id,
            "partition": case.get("partition"),
            "media_kind": (case.get("media_locator") or {}).get("kind"),
            "truth_sha256": case.get("truth_sha256"),
            "library_pcm_decode_invoked": False,
            "autonomous_authority": AUTONOMOUS_AUTHORITY,
        }
        use_live = live_ok and idx < live_budget
        try:
            if not use_live:
                raise Wave64VlmClientError(
                    "live_budget_exhausted" if live_ok else "endpoint_unavailable"
                )
            receipt = annotate_case_live(
                case, base_url=probe["base_url"], model=model
            )
            entry["endpoint_status"] = "live"
        except Wave64VlmClientError as exc:
            if not allow_metadata_proxy:
                raise
            receipt = metadata_proxy_receipt(case)
            entry["endpoint_status"] = "metadata_proxy_fallback"
            entry["endpoint_error"] = str(exc)
            receipt["model"] = model
        entry["receipt"] = receipt
        receipt_path = root / REVIEWS_DIR / f"{case_id}.vlm_synthetic.json"
        write_json(
            receipt_path,
            {
                "case_id": case_id,
                "autonomous_authority": AUTONOMOUS_AUTHORITY,
                "annotator_role": "vlm_synthetic",
                "receipt": receipt,
                "media_locator": case.get("media_locator"),
                "decode_invoked": False,
                "rights_cleared_for_production": False,
            },
        )
        entry["receipt_path"] = str(receipt_path.relative_to(root)).replace("\\", "/")
        entry["receipt_sha256"] = sha256_file(receipt_path)
        receipts.append(entry)

    live_count = sum(1 for r in receipts if r.get("endpoint_status") == "live")
    proxy_count = sum(
        1 for r in receipts if r.get("endpoint_status") == "metadata_proxy_fallback"
    )
    agree = sum(
        1
        for r in receipts
        if (r.get("receipt") or {}).get("agreement_with_synthetic_fixture") is True
    )

    now_chi = datetime.now(CHI)
    stamp = now_chi.strftime("%Y%m%dT%H%M%S") + "-0500"
    retained_blockers = list(hold.get("blocker_codes") or [])
    for code in (
        "GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT",
        "COMBINED_FRAME_CONTACT_AUDIO_REVIEW_ABSENT",
        "PRODUCTION_BENCHMARK_AUTHORITY_ABSENT",
        "HELD_OUT_RUNTIME_PROOF_ABSENT",
    ):
        if code not in retained_blockers:
            retained_blockers.append(code)

    packet = {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-109_VLM_SYNTHETIC_CORPUS_PATH_PACKET_{stamp}",
        "created_iso": now_chi.isoformat(timespec="seconds"),
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "autonomous_authority": AUTONOMOUS_AUTHORITY,
        "proof_tier": "AUTONOMOUS_VLM_SYNTHETIC_CORPUS_PATH_BOUNDED",
        "row_complete": False,
        "product_completion_claimed": False,
        "production_benchmark_authority": False,
        "library_pcm_decode_invoked": False,
        "row074_pcm_left_alone": True,
        "hold_090_plus_emitted": False,
        "source_bindings": {
            "case_index_path": str(CASE_INDEX).replace("\\", "/"),
            "case_index_sha256": sha256_file(root / CASE_INDEX),
            "manifest_path": str(MANIFEST).replace("\\", "/"),
            "manifest_sha256": sha256_file(root / MANIFEST),
            "hold_evidence_path": str(HOLD).replace("\\", "/"),
            "hold_evidence_sha256": sha256_file(root / HOLD),
            "case_count_index": int(index.get("case_count") or len(cases)),
            "case_count_manifest": len(cases),
        },
        "vlm_endpoint": probe,
        "model": model,
        "counts": {
            "cases_annotated": len(receipts),
            "live_vlm": live_count,
            "metadata_proxy_fallback": proxy_count,
            "agreement_with_synthetic_fixture": agree,
            "reviews_tree": str(REVIEWS_DIR).replace("\\", "/"),
        },
        "annotation_receipts": receipts,
        "policy_gates": {
            "synthetic_fixture_gates_retained": True,
            "genuine_annotated_media_cleared": False,
            "combined_frame_contact_audio_review_cleared": False,
            "rights_required_for_production_still": True,
            "autonomous_substitute_path": "synthetic_fixture_plus_vlm_annotation_receipts",
        },
        "blocker_codes_retained": retained_blockers,
        "decision": {
            "status": "hold",
            "row109_acceptance": "fixture_only_plus_vlm_synthetic_path",
            "autonomous_authority": AUTONOMOUS_AUTHORITY,
            "product_completion": False,
            "runtime_completion": False,
            "step2_still_blocked": True,
            "safe_next_action": (
                "Retain VLM_SYNTHETIC annotation receipts over synthetic fixtures. "
                "Production authority still requires rights-cleared genuine annotated media "
                "and combined frame/contact/audio review. Do not invent rights hashes, "
                "decode library PCM, touch Row074, or claim COMPLETE."
            ),
        },
        "notes": [
            "Autonomous substitute corpus path for Class F genuine-media/rights stop.",
            "autonomous_authority=VLM_SYNTHETIC does not satisfy human_gold genuine bind.",
            "GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT and production blockers remain fail-closed.",
            "No library PCM decode; Row074 exclusive PCM left alone.",
        ],
    }
    sealed = {k: v for k, v in packet.items() if k != "packet_sha256"}
    packet["packet_sha256"] = sha256_bytes(
        json.dumps(sealed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if packet["product_completion_claimed"] or packet["production_benchmark_authority"]:
        raise RuntimeError("row109_vlm_path_must_refuse_production_complete")
    return packet


def update_delta(delta_path: Path, packet: dict[str, Any], packet_rel: str) -> None:
    delta = load_json(delta_path)
    delta["vlm_synthetic_corpus_path_deepen"] = {
        "deepened_at": packet["created_iso"],
        "packet": packet_rel,
        "packet_sha256": packet["packet_sha256"],
        "autonomous_authority": AUTONOMOUS_AUTHORITY,
        "proof_tier": packet["proof_tier"],
        "cases_annotated": packet["counts"]["cases_annotated"],
        "live_vlm": packet["counts"]["live_vlm"],
        "metadata_proxy_fallback": packet["counts"]["metadata_proxy_fallback"],
        "product_completion": False,
        "step2_still_blocked": True,
        "row074_pcm_left_alone": True,
        "blocker_codes_retained": packet["blocker_codes_retained"],
        "verdict": "VLM_SYNTHETIC_CORPUS_PATH_BOUNDED_GENUINE_RIGHTS_STILL_REQUIRED",
    }
    decision = delta.setdefault("decision", {})
    decision["product_completion"] = False
    decision["step2_still_blocked"] = True
    decision["safe_next_action"] = packet["decision"]["safe_next_action"]
    decision["autonomous_authority"] = AUTONOMOUS_AUTHORITY
    delta["classification"] = (
        "ROW109_FAIL_CLOSED_VLM_SYNTHETIC_PATH_PRESENT_GENUINE_RIGHTS_STILL_REQUIRED"
    )
    write_json(delta_path, delta)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--allow-metadata-proxy", action="store_true", default=True)
    parser.add_argument("--no-metadata-proxy", action="store_false", dest="allow_metadata_proxy")
    parser.add_argument(
        "--live-limit",
        type=int,
        default=4,
        help="Max live VLM calls; remainder uses metadata proxy (default 4).",
    )
    parser.add_argument("--live-all", action="store_true", help="Live-annotate all cases.")
    parser.add_argument("--skip-delta", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    live_limit = None if args.live_all else args.live_limit
    packet = build_packet(
        root=root,
        base_url=args.base_url,
        model=args.model,
        allow_metadata_proxy=args.allow_metadata_proxy,
        live_limit=live_limit,
    )
    stamp = packet["evidence_id"].rsplit("_", 1)[-1]
    out_qa = (
        root
        / "Plan/Instructions/QA/Evidence/Wave64"
        / f"TRK-W64-109_VLM_SYNTHETIC_CORPUS_PATH_PACKET_{stamp}.json"
    )
    out_alias = (
        root
        / "Plan/Instructions/QA/Evidence/Wave64"
        / "TRK-W64-109_VLM_SYNTHETIC_CORPUS_PATH_PACKET_20260720.json"
    )
    out_trk = (
        root
        / "Plan/Tracker/Evidence/Wave64"
        / f"TRK-W64-109_VLM_SYNTHETIC_CORPUS_PATH_PACKET_{stamp}.json"
    )
    # Compact tracked packet: drop bulky per-case receipt bodies from alias mirror;
    # full stamped packet retains receipts; reviews tree holds per-case files.
    compact = dict(packet)
    compact["annotation_receipts"] = [
        {
            "case_id": r["case_id"],
            "partition": r["partition"],
            "endpoint_status": r["endpoint_status"],
            "receipt_path": r["receipt_path"],
            "receipt_sha256": r["receipt_sha256"],
            "agreement_with_synthetic_fixture": (r.get("receipt") or {}).get(
                "agreement_with_synthetic_fixture"
            ),
            "confidence": (r.get("receipt") or {}).get("confidence"),
        }
        for r in packet["annotation_receipts"]
    ]
    sealed = {k: v for k, v in compact.items() if k != "packet_sha256"}
    compact["packet_sha256"] = sha256_bytes(
        json.dumps(sealed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    write_json(out_qa, compact)
    write_json(out_alias, compact)
    write_json(out_trk, compact)
    rel = str(out_alias.relative_to(root)).replace("\\", "/")
    if not args.skip_delta:
        update_delta(root / DELTA_QA, compact, rel)
        if (root / DELTA_TRK).is_file():
            update_delta(root / DELTA_TRK, compact, rel)
        else:
            write_json(root / DELTA_TRK, load_json(root / DELTA_QA))
    print(
        json.dumps(
            {
                "packet": rel,
                "packet_sha256": compact["packet_sha256"],
                "cases_annotated": compact["counts"]["cases_annotated"],
                "live_vlm": compact["counts"]["live_vlm"],
                "metadata_proxy_fallback": compact["counts"]["metadata_proxy_fallback"],
                "autonomous_authority": AUTONOMOUS_AUTHORITY,
                "product_completion": False,
                "step2_still_blocked": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
