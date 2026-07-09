#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import repair_wave70_mouth_lips_source_landmark_mask_v2 as v2  # noqa: E402


v2.RUN_STAMP = "20260707T223000-0500"
v2.TIMESTAMP = "2026-07-07T22:30:00-05:00"
v2.V1_PANEL = (
    "runtime_artifacts/mask_factory/wave70_mf70_mouth_lips/source_landmark_repair_v2/"
    "20260707T222500-0500/mf70_mouth_lips_source_landmark_repair_v2_panel.png"
)
v2.V1_EVIDENCE = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_V2_20260707T222500-0500.json"
)


def inner_mouth_protected_v3() -> list[tuple[int, int]]:
    return [
        (305, 452),
        (350, 453),
        (398, 455),
        (434, 454),
        (433, 467),
        (390, 470),
        (346, 467),
        (306, 461),
    ]


def philtrum_skin_protected_v3() -> list[tuple[int, int]]:
    return [(344, 424), (428, 424), (420, 439), (354, 439)]


v2.inner_mouth_protected = inner_mouth_protected_v3
v2.philtrum_skin_protected = philtrum_skin_protected_v3


if __name__ == "__main__":
    raise SystemExit(v2.main())
