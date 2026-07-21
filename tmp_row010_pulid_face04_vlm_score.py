#!/usr/bin/env python3
"""Historical tmp_row010_pulid_face04_vlm_score.py ? FAIL CLOSED for product/identity climbs.

Do not approve GATE CLEARED / product PASS with weak qwen2.5vl:7b.
Use durable helper:
  Plan/07_IMPLEMENTATION/scripts/wave64_row010_pulid_identity_climb_visual.py
  (or wave64_climb_strict_visual_gate --climb-kind row010_pulid_identity)

Pass --smoke only for labeled SMOKE observation (delegates to durable smoke
lane; requires --images and --out). Never product COMPLETE.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent / "Plan" / "07_IMPLEMENTATION" / "scripts"
if not _SCRIPTS.is_dir():
    # Pod / nested copies may sit beside scripts or under /workspace
    for candidate in (
        Path(__file__).resolve().parent,
        Path("/workspace/wave64_repo_scripts"),
        Path("/workspace/wave64/Plan/07_IMPLEMENTATION/scripts"),
    ):
        if (candidate / "wave64_adhoc_historical_vlm_redirect.py").is_file():
            _SCRIPTS = candidate
            break
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from wave64_adhoc_historical_vlm_redirect import main_redirect  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main_redirect("row010", "tmp_row010_pulid_face04_vlm_score.py"))
