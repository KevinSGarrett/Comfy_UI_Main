#!/usr/bin/env bash
set -euo pipefail
# shellcheck disable=SC1091
source /workspace/paths.env
echo "==== wait idle motion-stronger $(date -u +%Y-%m-%dT%H:%M:%SZ) pod=${RUNPOD_POD_ID:-unset} ===="
if [ "${RUNPOD_POD_ID:-}" != "1q4ji0gg1fkhvt" ]; then
  echo "POD_MISMATCH ${RUNPOD_POD_ID:-unset}"
  exit 9
fi
for i in $(seq 1 240); do
  if ! curl -sS -m 3 http://127.0.0.1:8188/system_stats >/dev/null; then
    echo "$(date -u +%H:%M:%S) comfy down; starting"
    bash /workspace/04_start_comfy.sh || true
    sleep 20
    continue
  fi
  q=$(python3 /workspace/_tmp_w64_019_queue_status.py)
  echo "$(date -u +%H:%M:%S) $q"
  set -- $q
  if [ "$1" = "running=0" ] && [ "$2" = "pending=0" ]; then
    echo IDLE
    break
  fi
  sleep 20
done
set -- $(python3 /workspace/_tmp_w64_019_queue_status.py)
if [ "$1" != "running=0" ] || [ "$2" != "pending=0" ]; then
  echo "STILL_BUSY $*"
  exit 4
fi
mapfile -t OUT < <(python3 /workspace/_tmp_w64_019_submit_motion_stronger_wan.py)
PROMPT_ID="${OUT[0]}"
PREFIX="${OUT[1]}"
META="${OUT[2]}"
echo "SUBMITTED $PROMPT_ID $PREFIX $META"
echo "$PROMPT_ID" > /workspace/comfy_output/video/w64_019_023_motion_stronger_latest_prompt_id.txt
echo "$PREFIX" > /workspace/comfy_output/video/w64_019_023_motion_stronger_latest_prefix.txt
python3 /workspace/_tmp_w64_019_wait_prompt.py "$PROMPT_ID"
BASE=$(basename "$PREFIX")
ls -la /workspace/comfy_output/video/${BASE}*.mp4
stat -c '%n %s' /workspace/comfy_output/video/${BASE}*.mp4
echo "==== done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
