#!/bin/bash
set -euo pipefail
# shellcheck disable=SC1091
source /workspace/paths.env
MP4=/workspace/comfy_output/video/w64_019_023_runpod_wan_ti2v_sharp_hand_climb_20260721T092833Z_00001_.mp4
OUTDIR=/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_20260721T092833Z_frames
mkdir -p "$OUTDIR"
BYTES=$(stat -c '%s' "$MP4")
echo "MP4_BYTES=$BYTES"
ffprobe -v quiet -print_format json -show_streams -show_format "$MP4" > "$OUTDIR/ffprobe.json"
python3 - <<'PY'
import json
from pathlib import Path
from PIL import Image
d = Path("/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_20260721T092833Z_frames")
p = json.loads((d / "ffprobe.json").read_text())
v = [s for s in p["streams"] if s.get("codec_type") == "video"][0]
print(
    "w", v.get("width"),
    "h", v.get("height"),
    "frames", v.get("nb_frames"),
    "dur", p["format"].get("duration"),
    "size", p["format"].get("size"),
)
im = Image.open(d / "frame_03.png")
w, h = im.size
im.crop((int(w * 0.05), int(h * 0.45), int(w * 0.55), int(h * 0.85))).save(d / "hand_crop_left.png")
im.crop((int(w * 0.45), int(h * 0.45), int(w * 0.95), int(h * 0.85))).save(d / "hand_crop_right.png")
im.crop((int(w * 0.15), int(h * 0.40), int(w * 0.85), int(h * 0.90))).save(d / "hand_crop_center.png")
im.crop((int(w * 0.30), int(h * 0.08), int(w * 0.70), int(h * 0.35))).save(d / "skin_crop_face_shoulder.png")
# also crops from first and last for motion/hand stability
for name in ("frame_01.png", "frame_05.png"):
    im2 = Image.open(d / name)
    stem = name.replace(".png", "")
    im2.crop((int(w * 0.15), int(h * 0.40), int(w * 0.85), int(h * 0.90))).save(d / f"hand_crop_center_{stem}.png")
print("crops_ok", w, h)
PY
python3 - <<'PY'
import base64
import json
import os
import urllib.request

frames_dir = "/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_20260721T092833Z_frames"
frames = sorted(
    f for f in os.listdir(frames_dir) if f.startswith("frame_") and f.endswith(".png")
)
use = [frames[0], frames[len(frames) // 2], frames[-1]]
images = []
for f in use:
    with open(os.path.join(frames_dir, f), "rb") as fh:
        images.append(base64.b64encode(fh.read()).decode())
prompt = (
    "You are a strict video QA reviewer. Look at these frames from a short studio video.\n"
    "Return ONLY JSON with keys:\n"
    "verdict (PASS|FAIL), hands_ok (bool), plastic_skin (bool), motion_plausible (bool), "
    "near_static (bool), identity_stable (bool), garment_ok (bool), defects (list of strings), "
    "summary (string).\n"
    "Fail if hands look mushy/fused/deformed OR skin looks plastic/waxy/oversmoothed."
)
payload = {
    "model": "qwen2.5vl:7b",
    "prompt": prompt,
    "images": images,
    "stream": False,
    "format": "json",
    "options": {"temperature": 0},
}
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = json.load(resp)
    text = raw.get("response", "")
    out = {"model": "qwen2.5vl:7b", "frames": use, "raw_response": text, "performed": True}
    try:
        out["parsed"] = json.loads(text)
    except Exception:
        out["parsed"] = None
        out["parse_error"] = True
except Exception as e:
    out = {"model": "qwen2.5vl:7b", "error": str(e), "performed": False}
path = "/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_20260721T092833Z_vlm.json"
open(path, "w", encoding="utf-8").write(json.dumps(out, indent=2) + "\n")
print(path)
print(json.dumps(out.get("parsed") or out, indent=2)[:2500])
PY
ls -la "$OUTDIR"
sha256sum "$MP4"
