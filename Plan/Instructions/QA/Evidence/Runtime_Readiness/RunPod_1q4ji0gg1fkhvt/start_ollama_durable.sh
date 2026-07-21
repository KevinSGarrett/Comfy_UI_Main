#!/bin/bash
set -euo pipefail
export OLLAMA_MODELS=/workspace/ollama
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_GPU_OVERHEAD=0
export OLLAMA_FLASH_ATTENTION=1
LOGDIR=/workspace/runtime_artifacts/ollama_durable/logs
mkdir -p "$OLLAMA_MODELS" "$LOGDIR"
if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) already_up" >>"$LOGDIR/watchdog.log"
  exit 0
fi
pkill -f '/usr/local/bin/ollama serve' 2>/dev/null || true
sleep 1
nohup /usr/local/bin/ollama serve >>"$LOGDIR/ollama_serve.log" 2>&1 &
echo $! > /workspace/runtime_artifacts/ollama_durable/ollama_serve.pid
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) started_ok i=$i pid=$(cat /workspace/runtime_artifacts/ollama_durable/ollama_serve.pid)" >>"$LOGDIR/watchdog.log"
    exit 0
  fi
  sleep 1
done
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) start_failed" >>"$LOGDIR/watchdog.log"
exit 1
