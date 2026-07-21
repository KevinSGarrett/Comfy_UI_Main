#!/usr/bin/env bash
# On-pod Wan 2.2 TI2V 5B fetch + sha256 verify.
# Deployed to: /workspace/tools/fetch_wan22_ti2v_5b_on_pod.sh
# Invoked by: tools/Fetch-RunPodWan22Ti2V5B.ps1
# Authority: RunPod only. Never EC2. Never local Comfy.
set -euo pipefail

HF_REPO="Comfy-Org/Wan_2.2_ComfyUI_Repackaged"
HF_REV="fb1388adc906ab39ffc26ee40e96b22886b56bc4"
HF_BASE="https://huggingface.co/${HF_REPO}/resolve/${HF_REV}/split_files"

LOG_DIR="${WAN22_FETCH_LOG_DIR:-/workspace/logs/wan22_ti2v_5b_fetch}"
STATE_DIR="${WAN22_FETCH_STATE_DIR:-/workspace/runtime_artifacts/wan22_ti2v_5b_fetch}"
mkdir -p "$LOG_DIR" "$STATE_DIR" \
  /workspace/ComfyUI/models/diffusion_models \
  /workspace/ComfyUI/models/text_encoders \
  /workspace/ComfyUI/models/vae \
  /workspace/tools

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="${WAN22_FETCH_LOG_FILE:-${LOG_DIR}/fetch_${STAMP}.log}"
STATUS_FILE="${WAN22_FETCH_STATUS_FILE:-${STATE_DIR}/status_latest.json}"
export WAN22_FETCH_LOG_FILE="$LOG_FILE"
export WAN22_FETCH_STATUS_FILE="$STATUS_FILE"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Wan22 TI2V 5B on-pod fetch start ${STAMP} ==="
echo "hostname=$(hostname)"
echo "log_file=${LOG_FILE}"

if [[ -f /workspace/paths.env ]]; then
  set +u
  # shellcheck source=/dev/null
  . /workspace/paths.env
  set -u
  echo "paths.env=sourced"
else
  echo "BLOCKER=NO_WORKSPACE_PATHS_ENV paths.env missing at /workspace/paths.env"
  exit 12
fi

resolve_hf_token() {
  if [[ -n "${HF_TOKEN:-}" ]]; then
    printf '%s' "$HF_TOKEN"
    return 0
  fi
  if [[ -n "${HUGGING_FACE_HUB_TOKEN:-}" ]]; then
    printf '%s' "$HUGGING_FACE_HUB_TOKEN"
    return 0
  fi
  if [[ -n "${HUGGINGFACE_TOKEN:-}" ]]; then
    printf '%s' "$HUGGINGFACE_TOKEN"
    return 0
  fi
  if [[ -f /root/.cache/huggingface/token ]]; then
    tr -d '\r\n' </root/.cache/huggingface/token
    return 0
  fi
  if [[ -f /root/.huggingface/token ]]; then
    tr -d '\r\n' </root/.huggingface/token
    return 0
  fi
  return 1
}

HF_AUTH_TOKEN=""
if HF_AUTH_TOKEN="$(resolve_hf_token)"; then
  export HF_TOKEN="$HF_AUTH_TOKEN"
  export HUGGING_FACE_HUB_TOKEN="$HF_AUTH_TOKEN"
  echo "hf_auth=present"
else
  HF_AUTH_TOKEN=""
  echo "hf_auth=absent"
fi

# filename|subdir|bytes|sha256
ASSETS=(
  "wan2.2_ti2v_5B_fp16.safetensors|diffusion_models|9999658848|456f901338bd9eadbded3828b819109a9b68e8a525ca5cf8d0049a69fcfeca1e"
  "umt5_xxl_fp8_e4m3fn_scaled.safetensors|text_encoders|6735906897|c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68"
  "wan2.2_vae.safetensors|vae|1409400960|e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156"
)

write_status_json() {
  local status="$1"
  local detail="$2"
  STATUS_VAL="$status" DETAIL_VAL="$detail" HF_AUTH_PRESENT="$([ -n "$HF_AUTH_TOKEN" ] && echo 1 || echo 0)" \
  LOG_FILE_VAL="$LOG_FILE" STATUS_FILE_VAL="$STATUS_FILE" \
  HF_REPO_VAL="$HF_REPO" HF_REV_VAL="$HF_REV" \
  python3 - <<'PY'
import json, os, time
obj = {
  "schema_version": "1.0",
  "status": os.environ["STATUS_VAL"],
  "detail": os.environ["DETAIL_VAL"],
  "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "hostname": os.uname().nodename,
  "log_file": os.environ["LOG_FILE_VAL"],
  "hf_repo": os.environ["HF_REPO_VAL"],
  "hf_rev": os.environ["HF_REV_VAL"],
  "hf_auth_present": os.environ.get("HF_AUTH_PRESENT") == "1",
  "ec2_touched": False,
  "local_comfy_touched": False,
  "row074_touched": False,
}
path = os.environ["STATUS_FILE_VAL"]
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2)
    f.write("\n")
print(f"status_file={path} status={obj['status']}")
PY
}

preflight_url() {
  local url="$1"
  local code
  if [[ -n "$HF_AUTH_TOKEN" ]]; then
    code="$(curl -sS -o /dev/null -w '%{http_code}' -I -L --max-time 30 \
      -H "Authorization: Bearer ${HF_AUTH_TOKEN}" "$url" || echo 000)"
  else
    code="$(curl -sS -o /dev/null -w '%{http_code}' -I -L --max-time 30 "$url" || echo 000)"
  fi
  printf '%s' "$code"
}

echo "=== preflight HF accessibility ==="
NEED_AUTH=0
for row in "${ASSETS[@]}"; do
  IFS='|' read -r fname subdir expect_bytes expect_sha <<<"$row"
  url="${HF_BASE}/${subdir}/${fname}"
  code="$(preflight_url "$url")"
  echo "preflight ${fname} http=${code}"
  case "$code" in
    200|302|307|308) ;;
    401|403) NEED_AUTH=1 ;;
    *)
      write_status_json "blocked" "HF_PREFLIGHT_HTTP_${code}_for_${fname}"
      echo "BLOCKER=HF_PREFLIGHT_FAILED file=${fname} http=${code}"
      exit 13
      ;;
  esac
done

if [[ "$NEED_AUTH" -eq 1 && -z "$HF_AUTH_TOKEN" ]]; then
  write_status_json "blocked" "NO_HF_AUTH_ON_POD_GATED_ASSET"
  echo "BLOCKER=NO_HF_AUTH_ON_POD HF gated (401/403) and no HF_TOKEN/HUGGING_FACE_HUB_TOKEN/cache token after sourcing /workspace/paths.env"
  exit 14
fi

download_one() {
  local fname="$1"
  local subdir="$2"
  local expect_bytes="$3"
  local expect_sha="$4"
  local dest="/workspace/ComfyUI/models/${subdir}/${fname}"
  local url="${HF_BASE}/${subdir}/${fname}"
  local partial="${dest}.partial"
  local got_cli=0

  if [[ -f "$dest" ]]; then
    local cur_bytes cur_sha
    cur_bytes="$(stat -c %s "$dest")"
    if [[ "$cur_bytes" == "$expect_bytes" ]]; then
      cur_sha="$(sha256sum "$dest" | awk '{print $1}')"
      if [[ "$cur_sha" == "$expect_sha" ]]; then
        echo "SKIP_OK ${fname} already present+hash-verified"
        return 0
      fi
      echo "WARN existing ${fname} sha mismatch; re-fetching"
      rm -f "$dest"
    else
      echo "WARN existing ${fname} size ${cur_bytes} != ${expect_bytes}; re-fetching"
      rm -f "$dest"
    fi
  fi

  echo "DOWNLOAD_START ${fname} -> ${dest}"
  mkdir -p "$(dirname "$dest")"

  if command -v huggingface-cli >/dev/null 2>&1; then
    local tmpdir
    tmpdir="$(mktemp -d /tmp/wan22_fetch.XXXXXX)"
    set +e
    huggingface-cli download "$HF_REPO" \
      "split_files/${subdir}/${fname}" \
      --revision "$HF_REV" \
      --local-dir "$tmpdir" \
      --local-dir-use-symlinks False
    local rc=$?
    set -e
    if [[ $rc -eq 0 && -f "${tmpdir}/split_files/${subdir}/${fname}" ]]; then
      mv -f "${tmpdir}/split_files/${subdir}/${fname}" "$partial"
      got_cli=1
    else
      echo "WARN huggingface-cli failed rc=${rc}; falling back to wget/curl"
    fi
    rm -rf "$tmpdir"
  fi

  if [[ "$got_cli" -eq 0 ]]; then
    if command -v wget >/dev/null 2>&1; then
      if [[ -n "$HF_AUTH_TOKEN" ]]; then
        wget -c --progress=dot:giga \
          --header="Authorization: Bearer ${HF_AUTH_TOKEN}" \
          -O "$partial" "$url"
      else
        wget -c --progress=dot:giga -O "$partial" "$url"
      fi
    elif command -v curl >/dev/null 2>&1; then
      if [[ -n "$HF_AUTH_TOKEN" ]]; then
        curl -L --fail --retry 5 --retry-delay 5 -C - \
          -H "Authorization: Bearer ${HF_AUTH_TOKEN}" \
          -o "$partial" "$url"
      else
        curl -L --fail --retry 5 --retry-delay 5 -C - -o "$partial" "$url"
      fi
    else
      echo "BLOCKER=NO_DOWNLOAD_TOOL huggingface-cli/wget/curl unavailable"
      exit 15
    fi
  fi

  if [[ -f "$partial" ]]; then
    mv -f "$partial" "$dest"
  fi

  local got_bytes got_sha
  got_bytes="$(stat -c %s "$dest")"
  got_sha="$(sha256sum "$dest" | awk '{print $1}')"
  echo "VERIFY ${fname} bytes=${got_bytes} expected=${expect_bytes}"
  echo "VERIFY ${fname} sha256=${got_sha}"
  if [[ "$got_bytes" != "$expect_bytes" ]]; then
    echo "BLOCKER=SIZE_MISMATCH ${fname}"
    exit 16
  fi
  if [[ "$got_sha" != "$expect_sha" ]]; then
    echo "BLOCKER=SHA256_MISMATCH ${fname}"
    exit 17
  fi
  echo "OK ${fname}"
}

write_status_json "in_progress" "download_started"
echo "=== download assets ==="
for row in "${ASSETS[@]}"; do
  IFS='|' read -r fname subdir expect_bytes expect_sha <<<"$row"
  download_one "$fname" "$subdir" "$expect_bytes" "$expect_sha"
done

echo "=== final inventory ==="
python3 - <<'PY'
import hashlib, json, os, time

assets = [
  ("wan2.2_ti2v_5B_fp16.safetensors", "diffusion_models", 9999658848, "456f901338bd9eadbded3828b819109a9b68e8a525ca5cf8d0049a69fcfeca1e"),
  ("umt5_xxl_fp8_e4m3fn_scaled.safetensors", "text_encoders", 6735906897, "c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68"),
  ("wan2.2_vae.safetensors", "vae", 1409400960, "e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156"),
]
rows = []
ok = 0
for fname, subdir, expect_bytes, expect_sha in assets:
  path = f"/workspace/ComfyUI/models/{subdir}/{fname}"
  exists = os.path.isfile(path)
  got_bytes = os.path.getsize(path) if exists else 0
  got_sha = ""
  verified = False
  if exists:
    h = hashlib.sha256()
    with open(path, "rb") as f:
      for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
    got_sha = h.hexdigest()
    verified = got_bytes == expect_bytes and got_sha == expect_sha
    if verified:
      ok += 1
  rows.append({
    "filename": fname,
    "path": path,
    "exists": exists,
    "bytes": got_bytes,
    "expected_bytes": expect_bytes,
    "sha256": got_sha,
    "expected_sha256": expect_sha,
    "verified": verified,
  })
  print(f"{'VERIFIED' if verified else 'MISSING_OR_BAD'} {path} bytes={got_bytes}")

status = "complete_3_of_3_verified" if ok == 3 else f"incomplete_{ok}_of_3"
out = {
  "schema_version": "1.0",
  "status": status,
  "detail": "final_inventory",
  "present_ratio": f"{ok}/3",
  "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "hostname": os.uname().nodename,
  "log_file": os.environ.get("WAN22_FETCH_LOG_FILE", ""),
  "assets": rows,
  "ec2_touched": False,
  "local_comfy_touched": False,
  "row074_touched": False,
}
status_path = os.environ.get(
  "WAN22_FETCH_STATUS_FILE",
  "/workspace/runtime_artifacts/wan22_ti2v_5b_fetch/status_latest.json",
)
os.makedirs(os.path.dirname(status_path), exist_ok=True)
with open(status_path, "w", encoding="utf-8") as f:
  json.dump(out, f, indent=2)
  f.write("\n")
print(f"present_ratio={ok}/3")
print(f"status_file={status_path}")
if ok != 3:
  raise SystemExit(18)
PY

echo "=== Wan22 TI2V 5B on-pod fetch COMPLETE 3/3 ==="
