#!/usr/bin/env bash
set -euo pipefail
source /workspace/paths.env
export WAVE64_ROOT="${WAVE64_ROOT:-/workspace/wave64}"
export WAVE64="$WAVE64_ROOT"
export COMFY_URL="${COMFY_URL:-http://127.0.0.1:8188}"
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
cd "$WAVE64_ROOT"

echo "HOST=$(hostname)"
echo "WAVE64_ROOT=$WAVE64_ROOT"
echo "COMFY_URL=$COMFY_URL"

python3 - <<'PY'
import json, time, urllib.request, sys
API = "http://127.0.0.1:8188"
max_wait = 3600
start = time.time()
while True:
    try:
        data = json.load(urllib.request.urlopen(API + "/queue", timeout=5))
        r = len(data.get("queue_running") or [])
        p = len(data.get("queue_pending") or [])
        print(f"queue running={r} pending={p} elapsed={int(time.time()-start)}s", flush=True)
        if r == 0 and p == 0:
            stats = json.load(urllib.request.urlopen(API + "/system_stats", timeout=5))
            print("comfy_idle", stats.get("system", {}).get("comfyui_version"), flush=True)
            break
    except Exception as e:
        print("queue_poll_err", e, flush=True)
        # Comfy down: only fail if long outage; do not kill holders.
        try:
            urllib.request.urlopen(API + "/system_stats", timeout=3)
        except Exception:
            if time.time() - start > 120:
                print("FATAL comfy unreachable while waiting; not restarting (may be tournament/holder)", flush=True)
                sys.exit(2)
    if time.time() - start > max_wait:
        print("FATAL wait timeout", flush=True)
        sys.exit(3)
    time.sleep(10)
PY

echo "=== PRODUCER mf70_mouth_lips ==="
python3 /workspace/tmp_row017_runpod_mf70_mouth_lips_producer.py
echo "=== VLM DEEPEN mf70_mouth_lips ==="
python3 /workspace/tmp_row017_runpod_mf70_mouth_lips_vlm_deepen.py
echo "=== DONE mouth_lips climb ==="
