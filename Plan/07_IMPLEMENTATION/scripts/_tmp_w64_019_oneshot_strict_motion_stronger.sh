#!/usr/bin/env bash
# One-shot Class A strict gate once active tournament MVC bursts are clear.
# Does NOT wait for persistent hand_strict_vlm_sidecar_waiter daemon.
set -euo pipefail
source /workspace/paths.env
PROMPT_ID=6a5e81b8-b751-459e-a3cc-b9cb257a08f1
STAMP=20260721T164856Z
PREFIX=w64_019_023_runpod_wan_ti2v_motion_stronger_${STAMP}
SCRIPTS=/workspace/wave64_repo_scripts
FRAMES=/workspace/comfy_output/video/${PREFIX}_frames8
STRICT_OUT=/workspace/comfy_output/video/${PREFIX}_strict_class_a_receipt.json

echo "==== oneshot_strict $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
if [ "${WAVE64_RUNPOD_ID:-}" != "1q4ji0gg1fkhvt" ]; then echo POD_MISMATCH; exit 9; fi

for i in $(seq 1 180); do
  q=$(python3 -c 'import json,urllib.request;q=json.load(urllib.request.urlopen("http://127.0.0.1:8188/queue",timeout=10));print(len(q.get("queue_running",[])),len(q.get("queue_pending",[])))')
  set -- $q
  mvc=$(ps aux | grep 'run_tournament_mvc_visual_hard_qa' | grep -v grep | wc -l || true)
  echo "$(date -u +%H:%M:%S) running=$1 pending=$2 mvc=$mvc"
  if [ "$1" = "0" ] && [ "$2" = "0" ] && [ "$mvc" = "0" ]; then
    echo SLOT_OPEN
    break
  fi
  sleep 10
done
mvc=$(ps aux | grep 'run_tournament_mvc_visual_hard_qa' | grep -v grep | wc -l || true)
set -- $(python3 -c 'import json,urllib.request;q=json.load(urllib.request.urlopen("http://127.0.0.1:8188/queue",timeout=10));print(len(q.get("queue_running",[])),len(q.get("queue_pending",[])))')
if [ "$1" != "0" ] || [ "$2" != "0" ] || [ "$mvc" != "0" ]; then
  echo STILL_BUSY; exit 4
fi

curl -s -X POST http://127.0.0.1:8188/free -H 'Content-Type: application/json' -d '{"unload_models":true,"free_memory":true}' || true
sleep 3
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

cd "$SCRIPTS"
set +e
python3 wave64_wan_ti2v_climb_visual.py \
  --class-ladder class_a \
  --images \
    "$FRAMES/frame_01.png" "$FRAMES/frame_02.png" "$FRAMES/frame_03.png" \
    "$FRAMES/frame_04.png" "$FRAMES/frame_05.png" \
    "$FRAMES/hand_crop_center.png" "$FRAMES/skin_crop_face_shoulder.png" \
  --out "$STRICT_OUT" \
  --prompt-id "$PROMPT_ID" \
  --intent "class_a_motion_stronger_${STAMP}" \
  --human-frame-read not_run \
  --allow-non-pass
RC=$?
set -e
echo STRICT_GATE_RC=$RC
python3 - <<PY
import json
from pathlib import Path
p = Path("$STRICT_OUT")
if not p.is_file():
    print("MISSING")
else:
    d = json.loads(p.read_text(encoding="utf-8"))
    keys = [
        "strict_pod_llm_review",
        "lane",
        "climb_kind",
        "producer_gate",
        "model",
        "resolved_model",
        "vlm_model",
    ]
    print(json.dumps({k: d.get(k) for k in keys}, indent=2, sort_keys=True))
PY
exit $RC
