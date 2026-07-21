#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import json
import numpy as np

d = Path(
    r"C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts"
    r"\runpod_wan_ti2v_motion_stronger_20260721T100010Z\frames"
)
frames = sorted(d.glob("frame_*.png"))
print("local_frames", [p.name for p in frames])


def region_stats(im, box):
    a = np.asarray(im.crop(box).convert("RGB"), dtype=np.float32)
    return {"mean": float(a.mean()), "std": float(a.std())}


rows = []
for p in frames:
    im = Image.open(p)
    w, h = im.size
    eye = region_stats(im, (int(w * 0.30), int(h * 0.16), int(w * 0.70), int(h * 0.28)))
    chest = region_stats(
        im, (int(w * 0.28), int(h * 0.38), int(w * 0.72), int(h * 0.55))
    )
    hip = region_stats(im, (int(w * 0.25), int(h * 0.70), int(w * 0.75), int(h * 0.90)))
    rows.append(
        {
            "f": p.name,
            "eye_mean": eye["mean"],
            "chest_mean": chest["mean"],
            "hip_mean": hip["mean"],
        }
    )
for r in rows:
    r["d_eye"] = r["eye_mean"] - rows[0]["eye_mean"]
    r["d_chest"] = r["chest_mean"] - rows[0]["chest_mean"]
    r["d_hip"] = r["hip_mean"] - rows[0]["hip_mean"]
print(json.dumps(rows, indent=2))
print(
    "eye_delta_range",
    max(r["d_eye"] for r in rows) - min(r["d_eye"] for r in rows),
)
print(
    "chest_delta_range",
    max(r["d_chest"] for r in rows) - min(r["d_chest"] for r in rows),
)
print(
    "hip_delta_range",
    max(r["d_hip"] for r in rows) - min(r["d_hip"] for r in rows),
)
