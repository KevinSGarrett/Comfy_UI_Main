#!/usr/bin/env python3
"""Shared fail-closed strict visual QA gate for Wave64 climb producers.

BINDING:
  - Product / Class A / Proof_Landed / identity GATE CLEARED climbs MUST call
    invoke_climb_strict_visual_qa (or the CLI) and fail closed unless
    strict_pod_llm_review=PASS from the approved RunPod model (default
    qwen2.5vl:32b via wave64_pod_strict_visual_qa.review_images).
  - Weak qwen2.5vl:7b / panel-v2 / historical vlm_review.json paths are
    observation or SMOKE only (lane=SMOKE).
  - Respects Comfy POST /free then VLM unload arbitration inside review_images.
  - RunPod ONLY. NEVER EC2. Never claims product COMPLETE.

Climb kinds (producer presets):
  row010_pulid_identity  → IDENTITY_GATE / still
  wan_ti2v_class_e       → PROOF_LANDED / video_frames
  wan_ti2v_class_a       → CLASS_A / video_frames
  global_review_product  → PRODUCT / still
  smoke                  → SMOKE (weak model allowed; never product PASS)

Producers should import this helper rather than copy-pasting Ollama chat.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from wave64_pod_strict_visual_qa import (  # noqa: E402
    PRODUCT_LANES,
    StrictVisualQaError,
    review_images,
)
from validate_wave64_pod_strict_visual_qa_receipt import (  # noqa: E402
    validate_receipt,
)

CLIMB_PRESETS: dict[str, dict[str, str]] = {
    "row010_pulid_identity": {
        "lane": "IDENTITY_GATE",
        "media_kind": "still",
        "default_intent": (
            "Row010 PuLID identity climb: same-person lock vs authority refs; "
            "fail closed without strict_pod_llm_review=PASS for GATE CLEARED"
        ),
    },
    "wan_ti2v_class_e": {
        "lane": "PROOF_LANDED",
        "media_kind": "video_frames",
        "default_intent": (
            "Wan TI2V Class E Proof_Landed: living motion, sharp separated hands, "
            "natural skin; generation receipt is not visual approval"
        ),
    },
    "wan_ti2v_class_a": {
        "lane": "CLASS_A",
        "media_kind": "video_frames",
        "default_intent": (
            "Wan TI2V Class A product climb: strong temporal living motion with "
            "sharp hands and identity preservation"
        ),
    },
    "global_review_product": {
        "lane": "PRODUCT",
        "media_kind": "still",
        "default_intent": (
            "Row017 GLOBAL_REVIEW product deepen: whole-image identity/region "
            "preservation; weak VLM observation is not product PASS"
        ),
    },
    "smoke": {
        "lane": "SMOKE",
        "media_kind": "still",
        "default_intent": "SMOKE canary only — never product COMPLETE / Proof_Landed",
    },
}


class ClimbStrictVisualGateError(RuntimeError):
    """Raised when a product climb lacks strict_pod_llm_review=PASS."""


def resolve_climb_preset(climb_kind: str) -> dict[str, str]:
    key = climb_kind.strip().lower().replace("-", "_")
    if key not in CLIMB_PRESETS:
        raise ClimbStrictVisualGateError(
            f"unknown_climb_kind:{climb_kind}:allowed={sorted(CLIMB_PRESETS)}"
        )
    return dict(CLIMB_PRESETS[key])


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def invoke_climb_strict_visual_qa(
    image_paths: list[Path],
    *,
    climb_kind: str,
    out_path: Path,
    intent: str | None = None,
    lane: str | None = None,
    media_kind: str | None = None,
    model: str | None = None,
    require_pass: bool | None = None,
    require_idle_comfy: bool = True,
    unload_comfy: bool = True,
    unload_vlm_after: bool = True,
    timeout_s: float = 600.0,
    prompt_id: str | None = None,
    human_frame_read_status: str = "not_run",
    fixture_role: str = "live_climb",
    validate: bool = True,
) -> dict[str, Any]:
    """Run strict pod LLM visual QA for a climb and optionally fail closed on PASS.

    Product lanes default require_pass=True. SMOKE defaults require_pass=False
    (receipt still written and labeled lane=SMOKE).
    """
    preset = resolve_climb_preset(climb_kind)
    resolved_lane = (lane or preset["lane"]).strip().upper()
    resolved_media = media_kind or preset["media_kind"]
    resolved_intent = (intent if intent is not None else preset["default_intent"]).strip()
    if require_pass is None:
        require_pass = resolved_lane in PRODUCT_LANES

    paths = [Path(p) for p in image_paths]
    try:
        receipt = review_images(
            paths,
            lane=resolved_lane,
            intent=resolved_intent,
            media_kind=resolved_media,
            model=model,
            require_idle_comfy=require_idle_comfy,
            unload_comfy=unload_comfy,
            unload_vlm_after=unload_vlm_after,
            timeout_s=timeout_s,
            prompt_id=prompt_id,
            human_frame_read_status=human_frame_read_status,
            fixture_role=fixture_role,
        )
    except StrictVisualQaError as exc:
        blocked = {
            "schema_version": "wave64.pod_strict_visual_qa.v1",
            "climb_kind": climb_kind,
            "lane": resolved_lane,
            "overall_decision": "BLOCKED",
            "strict_pod_llm_review": "BLOCKED",
            "error": str(exc),
            "product_completion_claimed": False,
            "generation_receipt_is_not_visual_approval": True,
            "producer_gate": "wave64_climb_strict_visual_gate",
        }
        write_receipt(out_path, blocked)
        raise ClimbStrictVisualGateError(
            f"strict_visual_qa_blocked:{exc}:receipt={out_path}"
        ) from exc

    receipt = dict(receipt)
    receipt["climb_kind"] = climb_kind
    receipt["producer_gate"] = "wave64_climb_strict_visual_gate"
    receipt["product_completion_claimed"] = False
    if resolved_lane == "SMOKE":
        receipt["lane_label"] = "SMOKE"
        receipt["smoke_only"] = True
        receipt["product_authority"] = False

    write_receipt(out_path, receipt)

    if validate:
        receipt_errors = validate_receipt(receipt)
        if receipt_errors:
            raise ClimbStrictVisualGateError(
                "strict_receipt_invalid:"
                + ";".join(receipt_errors)
                + ":receipt="
                + str(out_path)
            )

    verdict = str(receipt.get("strict_pod_llm_review") or "").strip().upper()
    if require_pass and verdict != "PASS":
        raise ClimbStrictVisualGateError(
            f"strict_pod_llm_review_required_pass_got_{verdict or 'MISSING'}:"
            f"climb_kind={climb_kind}:lane={resolved_lane}:receipt={out_path}"
        )
    return receipt


def require_strict_pod_llm_pass(
    receipt: dict[str, Any] | Path,
    *,
    climb_kind: str | None = None,
) -> dict[str, Any]:
    """Fail closed unless an existing receipt already has strict_pod_llm_review=PASS."""
    if isinstance(receipt, Path):
        payload = json.loads(receipt.read_text(encoding="utf-8-sig"))
    else:
        payload = receipt
    if not isinstance(payload, dict):
        raise ClimbStrictVisualGateError("receipt_not_object")
    verdict = str(payload.get("strict_pod_llm_review") or "").strip().upper()
    lane = str(payload.get("lane") or "").strip().upper()
    if lane == "SMOKE":
        raise ClimbStrictVisualGateError(
            "smoke_receipt_cannot_authorize_product:"
            f"climb_kind={climb_kind or payload.get('climb_kind')}"
        )
    if verdict != "PASS":
        raise ClimbStrictVisualGateError(
            f"strict_pod_llm_review_required_pass_got_{verdict or 'MISSING'}:"
            f"climb_kind={climb_kind or payload.get('climb_kind')}"
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--climb-kind",
        required=True,
        choices=sorted(CLIMB_PRESETS),
        help="Producer preset (maps to lane + media_kind defaults)",
    )
    parser.add_argument("--images", nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--intent", default=None)
    parser.add_argument("--lane", default=None, choices=sorted(PRODUCT_LANES | {"SMOKE"}))
    parser.add_argument(
        "--media-kind",
        default=None,
        choices=["still", "video_frames", "video"],
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt-id", default=None)
    parser.add_argument(
        "--human-frame-read",
        default="not_run",
        choices=["pass", "fail", "not_run", "not_applicable"],
    )
    parser.add_argument("--timeout-s", type=float, default=600.0)
    parser.add_argument("--no-unload-comfy", action="store_true")
    parser.add_argument("--allow-busy-comfy", action="store_true")
    parser.add_argument("--keep-vlm-loaded", action="store_true")
    parser.add_argument(
        "--allow-non-pass",
        action="store_true",
        help="Write receipt and exit 0 even on REJECT (still fail closed on BLOCKED). "
        "Product climbs should omit this so missing PASS fails closed.",
    )
    parser.add_argument(
        "--smoke-ok-non-pass",
        action="store_true",
        help="Alias for --allow-non-pass when climb-kind=smoke",
    )
    args = parser.parse_args(argv)

    require_pass = not (args.allow_non_pass or args.smoke_ok_non_pass)
    if args.climb_kind == "smoke" and args.smoke_ok_non_pass:
        require_pass = False

    try:
        receipt = invoke_climb_strict_visual_qa(
            [Path(p) for p in args.images],
            climb_kind=args.climb_kind,
            out_path=args.out,
            intent=args.intent,
            lane=args.lane,
            media_kind=args.media_kind,
            model=args.model,
            require_pass=require_pass,
            require_idle_comfy=not args.allow_busy_comfy,
            unload_comfy=not args.no_unload_comfy,
            unload_vlm_after=not args.keep_vlm_loaded,
            timeout_s=args.timeout_s,
            prompt_id=args.prompt_id,
            human_frame_read_status=args.human_frame_read,
        )
    except ClimbStrictVisualGateError as exc:
        err = {
            "ok": False,
            "error": str(exc),
            "climb_kind": args.climb_kind,
            "out": str(args.out),
            "product_completion_claimed": False,
        }
        print(json.dumps(err, indent=2, sort_keys=True))
        # Missing PASS / BLOCKED → fail closed for product climbs.
        return 2

    summary = {
        "ok": True,
        "climb_kind": args.climb_kind,
        "lane": receipt.get("lane"),
        "strict_pod_llm_review": receipt.get("strict_pod_llm_review"),
        "out": str(args.out),
        "product_completion_claimed": False,
        "generation_receipt_is_not_visual_approval": True,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
