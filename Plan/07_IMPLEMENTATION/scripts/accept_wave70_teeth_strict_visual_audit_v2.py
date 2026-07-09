#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import accept_wave70_teeth_strict_visual_audit as base  # noqa: E402


base.RUN_STAMP = "20260707T230500-0500"
base.TIMESTAMP = "2026-07-07T23:05:00-05:00"
ORIGINAL_BOUNDARY_LAYER = base.boundary_layer


def boundary_layer_v2(size: tuple[int, int], region_id: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if region_id == "inner_mouth_non_teeth":
        draw.polygon([(302, 451), (438, 452), (438, 468), (392, 471), (346, 468), (303, 461)], fill=255)
        # The active source exposes only a narrow teeth band; exclude that visible target from protected inner-mouth.
        draw.rectangle((318, 450, 422, 464), fill=0)
    elif region_id == "teeth_target_candidate":
        draw.polygon([(320, 451), (350, 450), (386, 451), (420, 451), (432, 455), (405, 459), (362, 459), (324, 456)], fill=255)
    else:
        return ORIGINAL_BOUNDARY_LAYER(size, region_id)
    return mask


base.boundary_layer = boundary_layer_v2


if __name__ == "__main__":
    raise SystemExit(base.main())
