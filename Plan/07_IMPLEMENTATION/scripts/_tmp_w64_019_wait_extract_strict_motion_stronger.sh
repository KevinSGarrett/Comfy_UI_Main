#!/usr/bin/env bash
# Wait for motion-stronger Wan climb, extract frames, run strict 32b Class A gate.
set -euo pipefail
# shellcheck disable=SC1091
source /workspace/paths.env

PROMPT_ID="${1:-6a5e81b8-b751-459e-a3cc-b9cb257a08f1}"
STAMP="${2:-20260721T164856Z}"
PREFIX="w64_019_023_runpod_wan_ti2v_motion_stronger_${STAMP}"
SCRIPTS=/workspace/wave64_repo_scripts
OUT_ROOT=/workspace/comfy_output/video
FRAMES="${OUT_ROOT}/${PREFIX}_frames8"
STRICT_OUT="${OUT_ROOT}/${PREFIX}_strict_class_a_receipt.json"

echo "==== wait_extract_strict $(date -u +%Y-%m-%dT%H:%M:%SZ) pod=${WAVE64_RUNPOD_ID:-unset} ===="
if [ "${WAVE64_RUNPOD_ID:-}" != "1q4ji0gg1fkhvt" ]; then
  echo "POD_MISMATCH ${WAVE64_RUNPOD_ID:-unset}"
  exit 9
fi

python3 - <<PY
import json, time, urllib.request
pid = "${PROMPT_ID}"
for i in range(240):
    try:
        h = json.load(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}", timeout=10))
    except Exception as e:
        print("poll_err", e)
        time.sleep(15)
        continue
    if pid in h:
        st = h[pid].get("status") or {}
        print("DONE", st.get("status_str"), st.get("completed"))
        with open("/tmp/motion_stronger_history.json", "w", encoding="utf-8") as f:
            json.dump(h[pid], f, indent=2)
        break
    q = json.load(urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=10))
    print(
        f"wait {i} running={len(q.get('queue_running', []))} "
        f"pending={len(q.get('queue_pending', []))}"
    )
    time.sleep(15)
else:
    raise SystemExit("TIMEOUT_WAITING_PROMPT")
PY

MP4=""
for cand in \
  "${OUT_ROOT}/${PREFIX}_00001_.mp4" \
  "/workspace/ComfyUI/output/video/${PREFIX}_00001_.mp4" \
  "/workspace/ComfyUI/output/${PREFIX}_00001_.mp4"
do
  if [ -f "$cand" ]; then MP4="$cand"; break; fi
done
if [ -z "$MP4" ]; then
  MP4=$(find /workspace -name "${PREFIX}*.mp4" 2>/dev/null | head -n 1 || true)
fi
if [ -z "$MP4" ] || [ ! -f "$MP4" ]; then
  echo "MP4_MISSING for ${PREFIX}"
  find /workspace/comfy_output /workspace/ComfyUI/output -name "*motion_stronger*" 2>/dev/null | head
  exit 3
fi
echo "MP4=$MP4"
stat -c '%n %s' "$MP4"

mkdir -p "$FRAMES"
ffmpeg -y -i "$MP4" \
  -vf "select=eq(n\,0)+eq(n\,20)+eq(n\,40)+eq(n\,60)+eq(n\,80),format=rgb24" \
  -vsync vfr "$FRAMES/frame_%02d.png"

python3 - <<PY
from pathlib import Path
from PIL import Image
d = Path("${FRAMES}")
im = Image.open(d / "frame_03.png")
w, h = im.size
im.crop((int(w * 0.05), int(h * 0.45), int(w * 0.55), int(h * 0.85))).save(d / "hand_crop_left.png")
im.crop((int(w * 0.45), int(h * 0.45), int(w * 0.95), int(h * 0.85))).save(d / "hand_crop_right.png")
im.crop((int(w * 0.15), int(h * 0.40), int(w * 0.85), int(h * 0.90))).save(d / "hand_crop_center.png")
im.crop((int(w * 0.30), int(h * 0.08), int(w * 0.70), int(h * 0.35))).save(d / "skin_crop_face_shoulder.png")
print("frames_ok", w, h, sorted(p.name for p in d.glob("*.png")))
PY

# Free Comfy before strict VLM (gate also unloads, but queue must be idle)
curl -s -X POST http://127.0.0.1:8188/free -H 'Content-Type: application/json' \
  -d '{"unload_models":true,"free_memory":true}' || true
sleep 3

cd "$SCRIPTS"
set +e
python3 wave64_wan_ti2v_climb_visual.py \
  --class-ladder class_a \
  --images \
    "$FRAMES/frame_01.png" \
    "$FRAMES/frame_02.png" \
    "$FRAMES/frame_03.png" \
    "$FRAMES/frame_04.png" \
    "$FRAMES/frame_05.png" \
    "$FRAMES/hand_crop_center.png" \
    "$FRAMES/skin_crop_face_shoulder.png" \
  --out "$STRICT_OUT" \
  --prompt-id "$PROMPT_ID" \
  --intent "class_a_motion_stronger_${STAMP}" \
  --human-frame-read not_run \
  --allow-non-pass
RC=$?
set -e
echo "STRICT_GATE_RC=$RC"
python3 - <<PY
import json
from pathlib import Path
p = Path("${STRICT_OUT}")
if p.is_file():
    d = json.loads(p.read_text(encoding="utf-8"))
    print(json.dumps({
        "strict_pod_llm_review": d.get("strict_pod_llm_review"),
        "model": (d.get("model") or d.get("strict_model") or d.get("vlm_model")),
        "lane": d.get("lane"),
        "climb_kind": d.get("climb_kind"),
        "producer_gate": d.get("producer_gate"),
        "product_completion_claimed": d.get("product_completion_claimed", False),
        "out": str(p),
    }, indent=2, sort_keys=True))
else:
    print("STRICT_RECEIPT_MISSING")
PY
echo "==== done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
exit "$RC"
