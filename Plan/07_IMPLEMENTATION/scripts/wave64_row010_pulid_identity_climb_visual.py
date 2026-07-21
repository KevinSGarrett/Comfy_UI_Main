#!/usr/bin/env python3
"""Row010 PuLID identity climb → strict pod LLM visual gate (IDENTITY_GATE).

Product / GATE CLEARED claims fail closed without strict_pod_llm_review=PASS.
Panel-v2 qwen2.5vl:7b scoring remains calib/SMOKE observation only — call this
helper (or wave64_climb_strict_visual_gate --climb-kind row010_pulid_identity)
after each new identity climb before claiming GATE CLEARED.

RunPod ONLY. Never EC2. Never product COMPLETE from this alone.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--images",
        nargs="+",
        required=True,
        help="Calib / candidate still(s) for identity review",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--intent", default=None)
    parser.add_argument("--prompt-id", default=None)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Label SMOKE only (weak model allowed; never GATE CLEARED)",
    )
    parser.add_argument(
        "--allow-non-pass",
        action="store_true",
        help="Record REJECT/BLOCKED without exit 2 (still not a product PASS)",
    )
    parser.add_argument("--no-unload-comfy", action="store_true")
    parser.add_argument("--allow-busy-comfy", action="store_true")
    args = parser.parse_args(argv)

    climb_kind = "smoke" if args.smoke else "row010_pulid_identity"
    try:
        receipt = invoke_climb_strict_visual_qa(
            [Path(p) for p in args.images],
            climb_kind=climb_kind,
            out_path=args.out,
            intent=args.intent,
            prompt_id=args.prompt_id,
            require_pass=not (args.allow_non_pass or args.smoke),
            require_idle_comfy=not args.allow_busy_comfy,
            unload_comfy=not args.no_unload_comfy,
        )
    except ClimbStrictVisualGateError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "climb_kind": climb_kind,
                "strict_pod_llm_review": receipt.get("strict_pod_llm_review"),
                "out": str(args.out),
                "product_completion_claimed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
