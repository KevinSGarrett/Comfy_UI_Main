#!/usr/bin/env bash
# Wait for Comfy :8188 idle (do not kill foreign/tournament), then run pupils producer+VLM.
set -euo pipefail
source /workspace/paths.env
export WAVE64_ROOT="${WAVE64_ROOT:-/workspace/wave64}"
export COMFY_URL="${COMFY_URL:-http://127.0.0.1:8188}"
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export ROW017_VLM_MODEL="${ROW017_VLM_MODEL:-qwen2.5vl:7b}"

LOG=/workspace/tmp_row017_pupils_run.log
exec > >(tee -a "$LOG") 2>&1

echo "=== pupils wait/run $(date -Is) ==="
echo "WAVE64_ROOT=$WAVE64_ROOT COMFY_URL=$COMFY_URL"

python3 - <<'PY'
import json, time, urllib.request, os, sys
api = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")

def get(path, timeout=10):
    with urllib.request.urlopen(api + path, timeout=timeout) as r:
        return json.loads(r.read().decode())

for i in range(60):
    try:
        st = get("/system_stats", timeout=5)
        print("comfy_up", st.get("system", {}).get("comfyui_version"))
        break
    except Exception as e:
        print("comfy_down_wait", type(e).__name__, e)
        lock = "/tmp/mf_gpu_tournament.lockdir"
        if not os.path.exists(lock) and i > 0 and i % 6 == 0:
            print("attempt_start_comfy_no_tournament_lock")
            os.system("bash /workspace/04_start_comfy.sh >/workspace/tmp_start_comfy_pupils.log 2>&1 &")
        time.sleep(10)
else:
    print("FATAL comfy never came up")
    sys.exit(2)

deadline = time.time() + 7200
while time.time() < deadline:
    try:
        q = get("/queue", timeout=10)
    except Exception as e:
        print("queue_poll_err", e)
        time.sleep(10)
        continue
    running = len(q.get("queue_running") or [])
    pending = len(q.get("queue_pending") or [])
    rid = q["queue_running"][0][1] if q.get("queue_running") else None
    print(f"queue running={running} pending={pending} rid={rid}")
    if running == 0 and pending == 0:
        print("queue_idle")
        break
    time.sleep(20)
else:
    print("FATAL queue busy beyond 7200s")
    sys.exit(3)
print("idle_ok")
PY

cd "$WAVE64_ROOT"
test -f /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_producer.py
test -f /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_vlm_deepen.py

python3 /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_producer.py
PROD_RC=$?
echo "producer_rc=$PROD_RC"
if [[ $PROD_RC -ne 0 ]]; then
  exit $PROD_RC
fi

STAMP=$(python3 - <<'PY'
from pathlib import Path
base = Path("/workspace/wave64/Plan/Instructions/Operations/Pulled_Back_Artifacts")
cands = sorted(
    base.glob("runpod_comfyui_row017_mf70_pupils_iris_sclera_*"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
print(cands[0].name.split("runpod_comfyui_row017_mf70_pupils_iris_sclera_", 1)[1])
PY
)
export ROW017_PRODUCER_STAMP="$STAMP"
echo "ROW017_PRODUCER_STAMP=$STAMP"
python3 /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_vlm_deepen.py
echo "vlm_rc=$?"
echo "=== done $(date -Is) ==="
