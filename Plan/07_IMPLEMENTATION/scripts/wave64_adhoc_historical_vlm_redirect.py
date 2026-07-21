#!/usr/bin/env python3
"""Fail-closed redirect for historical tmp_row010_*_vlm_score / tmp_row017_*_vlm_deepen.

Ad-hoc scripts must not approve product / identity climbs on weak qwen2.5vl:7b.
Default invocation exits with a clear "use durable helper" error.
Only ``--smoke`` may continue, and it delegates to wave64_climb_strict_visual_gate
(lane=SMOKE) — it does not re-embed 7b panel-v2 rubric logic.

RunPod ONLY. Never EC2. Never product COMPLETE.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from wave64_climb_strict_visual_gate import (  # noqa: E402
    ClimbStrictVisualGateError,
    invoke_climb_strict_visual_qa,
)

FAMILY_DURABLE = {
    "row010": {
        "helper": "wave64_row010_pulid_identity_climb_visual.py",
        "climb_kind_product": "row010_pulid_identity",
        "cli_example": (
            "python3 Plan/07_IMPLEMENTATION/scripts/"
            "wave64_row010_pulid_identity_climb_visual.py "
            "--images <calib.png> --out <strict_receipt.json>"
        ),
    },
    "row017": {
        "helper": "wave64_row017_global_review_deepen_visual.py",
        "climb_kind_product": "global_review_product",
        "cli_example": (
            "python3 Plan/07_IMPLEMENTATION/scripts/"
            "wave64_row017_global_review_deepen_visual.py "
            "--images <still.png> --out <strict_receipt.json>"
        ),
    },
}


def fail_closed_message(family: str, historical_name: str) -> str:
    meta = FAMILY_DURABLE[family]
    return (
        f"ADHOC_VLM_FAIL_CLOSED:{historical_name}: "
        f"historical qwen2.5vl:7b ad-hoc scripts must not approve product/"
        f"identity climbs. Use durable helper {meta['helper']} "
        f"(or wave64_climb_strict_visual_gate --climb-kind "
        f"{meta['climb_kind_product']}). "
        f"Example: {meta['cli_example']}. "
        f"Pass --smoke only for labeled SMOKE observation "
        f"(requires --images and --out; never GATE CLEARED / product PASS)."
    )


def main_redirect(
    family: str,
    historical_name: str,
    argv: list[str] | None = None,
) -> int:
    if family not in FAMILY_DURABLE:
        print(
            json.dumps(
                {"ok": False, "error": f"unknown_family:{family}"},
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(
        description=(
            f"Historical {historical_name} — fail closed unless --smoke; "
            "product climbs must use durable strict visual helpers."
        )
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="SMOKE observation only via durable helper (weak model allowed)",
    )
    parser.add_argument(
        "--images",
        nargs="+",
        default=None,
        help="Required with --smoke: image path(s) for SMOKE review",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Required with --smoke: receipt output path",
    )
    parser.add_argument("--intent", default=None)
    parser.add_argument("--prompt-id", default=None)
    parser.add_argument("--no-unload-comfy", action="store_true")
    parser.add_argument("--allow-busy-comfy", action="store_true")
    args = parser.parse_args(argv)

    if not args.smoke:
        msg = fail_closed_message(family, historical_name)
        print(json.dumps({"ok": False, "error": msg}, indent=2, sort_keys=True))
        print(msg, file=sys.stderr)
        return 2

    if not args.images or args.out is None:
        msg = (
            f"ADHOC_VLM_SMOKE_REQUIRES_ARGS:{historical_name}: "
            "pass --smoke --images <paths...> --out <receipt.json> "
            f"(delegates to durable smoke lane). Product path: "
            f"{FAMILY_DURABLE[family]['cli_example']}"
        )
        print(json.dumps({"ok": False, "error": msg}, indent=2, sort_keys=True))
        print(msg, file=sys.stderr)
        return 2

    try:
        receipt = invoke_climb_strict_visual_qa(
            [Path(p) for p in args.images],
            climb_kind="smoke",
            out_path=args.out,
            intent=args.intent
            or f"SMOKE only via historical redirect {historical_name}",
            prompt_id=args.prompt_id,
            require_pass=False,
            require_idle_comfy=not args.allow_busy_comfy,
            unload_comfy=not args.no_unload_comfy,
        )
    except ClimbStrictVisualGateError as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True)
        )
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "historical_script": historical_name,
                "redirect": "wave64_climb_strict_visual_gate",
                "climb_kind": "smoke",
                "lane": "SMOKE",
                "smoke_only": True,
                "product_authority": False,
                "product_completion_claimed": False,
                "strict_pod_llm_review": receipt.get("strict_pod_llm_review"),
                "out": str(args.out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main_redirect("row010", "wave64_adhoc_historical_vlm_redirect.py")
    )
