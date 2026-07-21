#!/usr/bin/env python3
"""Wan TI2V Class E / Class A climb → strict pod LLM visual gate.

After frame extraction from a Wan climb, producers MUST call this helper
(or wave64_climb_strict_visual_gate --climb-kind wan_ti2v_class_e|wan_ti2v_class_a)
before claiming Proof_Landed / Class A product PASS.

Weak historical vlm_review.json (qwen2.5vl:7b) is SMOKE/observation only.
Dual-gate with human_frame_read remains in
validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py.

RunPod ONLY. Comfy /free then VLM unload arbitration is inside the shared gate.
Never product COMPLETE from this alone.
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
        "--class-ladder",
        choices=["class_e", "class_a", "smoke"],
        default="class_e",
        help="class_e→PROOF_LANDED, class_a→CLASS_A, smoke→SMOKE",
    )
    parser.add_argument("--images", nargs="+", required=True, help="Extracted frames")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--intent", default=None)
    parser.add_argument("--prompt-id", default=None)
    parser.add_argument(
        "--human-frame-read",
        default="not_run",
        choices=["pass", "fail", "not_run", "not_applicable"],
    )
    parser.add_argument(
        "--allow-non-pass",
        action="store_true",
        help="Record REJECT without exit 2 (Proof_Landed still forbidden)",
    )
    parser.add_argument("--no-unload-comfy", action="store_true")
    parser.add_argument("--allow-busy-comfy", action="store_true")
    args = parser.parse_args(argv)

    climb_kind = {
        "class_e": "wan_ti2v_class_e",
        "class_a": "wan_ti2v_class_a",
        "smoke": "smoke",
    }[args.class_ladder]

    try:
        receipt = invoke_climb_strict_visual_qa(
            [Path(p) for p in args.images],
            climb_kind=climb_kind,
            out_path=args.out,
            intent=args.intent,
            prompt_id=args.prompt_id,
            human_frame_read_status=args.human_frame_read,
            require_pass=not (args.allow_non_pass or args.class_ladder == "smoke"),
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
