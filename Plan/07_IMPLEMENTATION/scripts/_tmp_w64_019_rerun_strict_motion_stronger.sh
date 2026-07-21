#!/usr/bin/env bash
# Re-run Class A strict 32b gate on already-extracted motion-stronger frames.
# Waits for idle :8188 AND no foreign hand_strict/tournament ollama load.
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

echo "==== rerun_strict $(date -u +%Y-%m-%dT%H:%M:%SZ) pod=${WAVE64_RUNPOD_ID:-unset} ===="
if [ "${WAVE64_RUNPOD_ID:-}" != "1q4ji0gg1fkhvt" ]; then
  echo "POD_MISMATCH"; exit 9
fi
if [ ! -d "$FRAMES" ]; then
  echo "FRAMES_MISSING $FRAMES"; exit 3
fi

for i in $(seq 1 240); do
  q=$(python3 - <<'PY'
import json, urllib.request
q=json.load(urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=10))
print(len(q.get("queue_running", [])), len(q.get("queue_pending", [])))
PY
)
  set -- $q
  foreign=$(ps aux | grep -E 'hand_strict_vlm_sidecar|run_tournament_mvc_visual_hard_qa' | grep -v grep | wc -l)
  echo "$(date -u +%H:%M:%S) queue_running=$1 pending=$2 foreign_tournament=$foreign"
  if [ "$1" = "0" ] && [ "$2" = "0" ] && [ "$foreign" = "0" ]; then
    echo IDLE_FOR_STRICT
    break
  fi
  sleep 20
done
set -- $(python3 - <<'PY'
import json, urllib.request
q=json.load(urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=10))
print(len(q.get("queue_running", [])), len(q.get("queue_pending", [])))
PY
)
foreign=$(ps aux | grep -E 'hand_strict_vlm_sidecar|run_tournament_mvc_visual_hard_qa' | grep -v grep | wc -l || true)
if [ "$1" != "0" ] || [ "$2" != "0" ] || [ "$foreign" != "0" ]; then
  echo "STILL_BUSY running=$1 pending=$2 foreign_tournament=$foreign"
  exit 4
fi

curl -s -X POST http://127.0.0.1:8188/free -H 'Content-Type: application/json' \
  -d '{"unload_models":true,"free_memory":true}' || true
sleep 5
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

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
if [ -f "$STRICT_OUT" ]; then
  python3 - <<PY
import json
from pathlib import Path
d=json.loads(Path("$STRICT_OUT").read_text(encoding="utf-8"))
print(json.dumps({
  "strict_pod_llm_review": d.get("strict_pod_llm_review"),
  "model": d.get("model") or d.get("resolved_model") or d.get("vlm_model"),
  "lane": d.get("lane"),
  "climb_kind": d.get("climb_kind"),
  "producer_gate": d.get("producer_gate"),
  "product_completion_claimed": False,
  "out": "$STRICT_OUT",
}, indent=2, sort_keys=True))
PY
fi
echo "==== done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
exit "$RC"
