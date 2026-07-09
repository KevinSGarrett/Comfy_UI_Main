#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import repair_wave70_mouth_lips_source_landmark_mask_v2 as v2  # noqa: E402


v2.RUN_STAMP = "20260707T223500-0500"
v2.TIMESTAMP = "2026-07-07T22:35:00-05:00"
v2.V1_PANEL = (
    "runtime_artifacts/mask_factory/wave70_mf70_mouth_lips/source_landmark_repair_v2/"
    "20260707T223000-0500/mf70_mouth_lips_source_landmark_repair_v2_panel.png"
)
v2.V1_EVIDENCE = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_V2_20260707T223000-0500.json"
)


def inner_mouth_protected_v4() -> list[tuple[int, int]]:
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


def philtrum_skin_protected_v4() -> list[tuple[int, int]]:
    return [(344, 424), (428, 424), (420, 439), (354, 439)]


def boundary_layer_v4(size: tuple[int, int], region_id: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if region_id == "inner_mouth_teeth":
        draw.polygon(inner_mouth_protected_v4(), fill=255)
        return mask
    if region_id == "philtrum":
        draw.polygon(philtrum_skin_protected_v4(), fill=255)
        return mask
    if region_id == "nose":
        draw.polygon([(384, 326), (403, 326), (408, 360), (416, 393), (424, 419), (415, 431), (394, 436), (371, 431), (360, 419), (366, 394), (377, 360)], fill=255)
        draw.ellipse((356, 407, 385, 435), fill=255)
        draw.ellipse((401, 407, 427, 435), fill=255)
    elif region_id == "chin_lower_skin":
        draw.polygon([(306, 480), (448, 480), (476, 546), (276, 546)], fill=255)
    elif region_id == "left_cheek_skin":
        draw.polygon([(230, 405), (304, 432), (303, 492), (238, 510)], fill=255)
    elif region_id == "right_cheek_skin":
        draw.polygon([(445, 420), (536, 390), (540, 520), (445, 492)], fill=255)
    elif region_id == "mouth_lips_target_candidate":
        draw.polygon(v2.upper_lip_polygon(), fill=255)
        draw.polygon(v2.lower_lip_polygon(), fill=255)
        draw.polygon(inner_mouth_protected_v4(), fill=0)
    else:
        raise ValueError(f"unknown boundary region: {region_id}")
    return mask.filter(ImageFilter.GaussianBlur(radius=0.25))


v2.inner_mouth_protected = inner_mouth_protected_v4
v2.philtrum_skin_protected = philtrum_skin_protected_v4
v2.boundary_layer = boundary_layer_v4


if __name__ == "__main__":
    raise SystemExit(v2.main())
