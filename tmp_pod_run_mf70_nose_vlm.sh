#!/usr/bin/env bash
set -euo pipefail
source /workspace/paths.env
cd /workspace/wave64
echo SUMMARY=$(test -f Plan/Instructions/Operations/Pulled_Back_Artifacts/runpod_comfyui_row017_mf70_nose_20260721T041254-0500/RUN_SUMMARY.json && echo OK || echo MISSING)
curl -s http://127.0.0.1:8188/queue
echo
export ROW017_PRODUCER_STAMP=20260721T041254-0500
python3 -u tmp_row017_runpod_mf70_nose_vlm_deepen.py 2>&1 | tee /tmp/row017_mf70_nose_vlm.log
echo VLM_EXIT:${PIPESTATUS[0]}
