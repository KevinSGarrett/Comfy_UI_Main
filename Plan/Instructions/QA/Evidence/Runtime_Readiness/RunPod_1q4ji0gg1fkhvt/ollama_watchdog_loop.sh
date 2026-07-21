#!/bin/bash
# Persistent watchdog (no systemd/cron on this RunPod image).
LOG=/workspace/runtime_artifacts/ollama_durable/logs/watchdog_loop.log
mkdir -p "$(dirname "$LOG")"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) watchdog_loop_start pid=$$" >>"$LOG"
while true; do
  /workspace/runtime_artifacts/start_ollama_durable.sh >>"$LOG" 2>&1 || true
  sleep 30
done
