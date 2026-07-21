#!/bin/bash
set -euo pipefail
MP4=/workspace/comfy_output/video/w64_019_023_runpod_wan_ti2v_sharp_hand_climb_20260721T094222Z_00001_.mp4
OUT=/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_20260721T094222Z_class_a_frames16
mkdir -p "$OUT"
ffmpeg -y -i "$MP4" -vf "select=not(mod(n\,5)),format=rgb24" -vsync vfr "$OUT/frame_%02d.png"
python3 - <<'PY'
from pathlib import Path
from PIL import Image
import json
import numpy as np

d = Path("/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_20260721T094222Z_class_a_frames16")
frames = sorted(d.glob("frame_*.png"))
print("n_frames", len(frames))

def mae(a, b):
    A = np.asarray(Image.open(a).convert("RGB"), dtype=np.float32)
    B = np.asarray(Image.open(b).convert("RGB"), dtype=np.float32)
    return float(np.mean(np.abs(A - B)))

pairs = []
if len(frames) >= 3:
    first, mid, last = frames[0], frames[len(frames) // 2], frames[-1]
    pairs = [
        ("first_mid", mae(first, mid)),
        ("mid_last", mae(mid, last)),
        ("first_last", mae(first, last)),
    ]
    im = Image.open(mid)
    w, h = im.size
    crop_box = (int(w * 0.15), int(h * 0.40), int(w * 0.85), int(h * 0.90))
    face_box = (int(w * 0.30), int(h * 0.05), int(w * 0.70), int(h * 0.40))
    for label, src in [("first", first), ("mid", mid), ("last", last)]:
        Image.open(src).crop(crop_box).save(d / f"hand_region_{label}.png")
        Image.open(src).crop(face_box).save(d / f"face_region_{label}.png")

meta = {
    "n_frames": len(frames),
    "mae_pairs": pairs,
    "frame_names": [p.name for p in frames],
    "source_frame_indices": list(range(0, 81, 5)),
}
(d / "motion_mae.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(meta, indent=2))
PY
ls -la "$OUT"
ffprobe -v error -show_entries format=duration,size,bit_rate -show_entries stream=codec_name,width,height,nb_frames,pix_fmt,r_frame_rate -of json "$MP4" > "$OUT/ffprobe.json"
echo EXTRACT_OK
