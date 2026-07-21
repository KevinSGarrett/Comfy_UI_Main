#!/usr/bin/env bash
set -euo pipefail
# shellcheck disable=SC1091
source /workspace/paths.env
STAMP="${1:?stamp}"
MP4="/workspace/comfy_output/video/w64_019_023_runpod_wan_ti2v_motion_stronger_${STAMP}_00001_.mp4"
OUTDIR="/workspace/comfy_output/video/w64_019_023_motion_stronger_${STAMP}_frames"
mkdir -p "$OUTDIR"
rm -f "$OUTDIR"/frame_*.png "$OUTDIR"/hand_*.png "$OUTDIR"/skin_*.png
ffprobe -v quiet -print_format json -show_streams -show_format "$MP4" > "$OUTDIR/ffprobe.json"
stat -c '%n %s' "$MP4" | tee "$OUTDIR/bytes.txt"
# dense 17-frame sample across 81 frames for motion Read
ffmpeg -y -i "$MP4" -vf "select='eq(n\,0)+eq(n\,5)+eq(n\,10)+eq(n\,15)+eq(n\,20)+eq(n\,25)+eq(n\,30)+eq(n\,35)+eq(n\,40)+eq(n\,45)+eq(n\,50)+eq(n\,55)+eq(n\,60)+eq(n\,65)+eq(n\,70)+eq(n\,75)+eq(n\,80)'" -vsync vfr "$OUTDIR/frame_%02d.png"
# hand/skin crops from mid frame
python3 - <<PY
from pathlib import Path
from PIL import Image
d = Path("$OUTDIR")
frames = sorted(d.glob("frame_*.png"))
mid = frames[len(frames)//2]
im = Image.open(mid)
w, h = im.size
# palms-forward hands typically lower-center / mid
hand_l = im.crop((int(w*0.08), int(h*0.42), int(w*0.48), int(h*0.78)))
hand_r = im.crop((int(w*0.52), int(h*0.42), int(w*0.92), int(h*0.78)))
hand_c = im.crop((int(w*0.25), int(h*0.48), int(w*0.75), int(h*0.82)))
skin = im.crop((int(w*0.28), int(h*0.08), int(w*0.72), int(h*0.38)))
hand_l.save(d / "hand_crop_left.png")
hand_r.save(d / "hand_crop_right.png")
hand_c.save(d / "hand_crop_center.png")
skin.save(d / "skin_crop_face_shoulder.png")
print("frames", len(frames), "mid", mid.name, "size", w, h)
PY
ls -la "$OUTDIR"
# VLM secondary (not authoritative)
python3 - <<PY
import json, base64, urllib.request, os
frames_dir = "$OUTDIR"
frames = sorted([f for f in os.listdir(frames_dir) if f.startswith("frame_") and f.endswith(".png")])
use = [frames[0], frames[len(frames)//4], frames[len(frames)//2], frames[(3*len(frames))//4], frames[-1]]
images = []
for f in use:
    with open(os.path.join(frames_dir, f), "rb") as fh:
        images.append(base64.b64encode(fh.read()).decode())
prompt = """You are a strict video QA reviewer for temporal motion + hands.
Return ONLY JSON with keys:
verdict (PASS|FAIL), hands_ok (bool), fingers_separated (bool), plastic_skin (bool),
breathing_visible (bool), blink_visible (bool), weight_shift_visible (bool),
motion_natural (bool), near_static (bool), identity_stable (bool),
defects (list of strings), summary (string).
FAIL if near_static=true OR no clear breath/blink/weight-shift OR mushy fused hands."""
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
out = {"model": "qwen2.5vl:7b", "frames": use}
try:
  with urllib.request.urlopen(req, timeout=360) as resp:
    raw = json.load(resp)
  text = raw.get("response", "")
  out["raw_response"] = text
  try:
    out["parsed"] = json.loads(text)
  except Exception:
    out["parsed"] = None
    out["parse_error"] = True
except Exception as e:
  out["error"] = str(e)
  out["performed"] = False
path = f"/workspace/comfy_output/video/w64_019_023_motion_stronger_{STAMP}_vlm.json"
open(path, "w", encoding="utf-8").write(json.dumps(out, indent=2) + "\n")
print(path)
print(json.dumps(out.get("parsed") or out, indent=2)[:2500])
PY
