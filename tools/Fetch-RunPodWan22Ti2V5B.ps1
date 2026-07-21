<#
.SYNOPSIS
Approved RunPod-only fetch for Wan 2.2 TI2V 5B ComfyUI model payloads.

.DESCRIPTION
SSHs to the authorized RunPod pod, sources /workspace/paths.env, deploys the
on-pod companion script, and downloads three HF split_files assets directly onto
the pod into /workspace/ComfyUI/models/{diffusion_models,text_encoders,vae}/.

Never touches EC2. Never mutates local Comfy models. Resume-safe. sha256+bytes
verify after each file. Fail-closed if HF returns 401/403 and no pod HF auth is
available after sourcing paths.env.

Default mode detaches the download on the pod (nohup) because total payload is
~17 GB. Use -Foreground to block until complete.

.EXAMPLE
.\tools\Fetch-RunPodWan22Ti2V5B.ps1

.EXAMPLE
.\tools\Fetch-RunPodWan22Ti2V5B.ps1 -StatusOnly

.EXAMPLE
.\tools\Fetch-RunPodWan22Ti2V5B.ps1 -Foreground
#>
[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RemoteHost = "195.26.233.100",
  [string]$RemoteUser = "root",
  [int]$RemotePort = 52077,
  [string]$IdentityFile = "",
  [string]$PodId = "1q4ji0gg1fkhvt",
  [switch]$Foreground,
  [switch]$StatusOnly,
  [switch]$SkipDeploy,
  [switch]$ForwardLocalHfToken
)

$ErrorActionPreference = "Stop"

function Resolve-IdentityPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) {
    $Path = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
  }
  if ($Path -like "~/*") {
    $Path = Join-Path $env:USERPROFILE ($Path.Substring(2))
  } elseif ($Path -like "~\*") {
    $Path = Join-Path $env:USERPROFILE ($Path.Substring(2))
  }
  return [System.IO.Path]::GetFullPath($Path)
}

function Get-SshExecutable {
  param([string]$Name)
  $candidate = Join-Path $env:WINDIR "System32\OpenSSH\$Name.exe"
  if (Test-Path -LiteralPath $candidate) { return $candidate }
  $fromPath = Get-Command $Name -ErrorAction SilentlyContinue
  if ($fromPath) { return $fromPath.Source }
  throw "OpenSSH client ($Name.exe) not found on PATH or in System32\\OpenSSH."
}

function Invoke-PodBash {
  param(
    [Parameter(Mandatory = $true)][string]$ScriptBody
  )
  $sshArgs = @(
    "-i", $script:KeyPath,
    "-p", "$RemotePort",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=20",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=240",
    "${RemoteUser}@${RemoteHost}",
    "bash -s"
  )
  $ScriptBody | & $script:SshExe @sshArgs
  return $LASTEXITCODE
}

function Get-LocalHfTokenPresence {
  $present = $false
  $source = $null
  if (-not [string]::IsNullOrWhiteSpace($env:HF_TOKEN)) {
    $present = $true; $source = "env:HF_TOKEN"
  } elseif (-not [string]::IsNullOrWhiteSpace($env:HUGGING_FACE_HUB_TOKEN)) {
    $present = $true; $source = "env:HUGGING_FACE_HUB_TOKEN"
  } elseif (-not [string]::IsNullOrWhiteSpace($env:HUGGINGFACE_TOKEN)) {
    $present = $true; $source = "env:HUGGINGFACE_TOKEN"
  } else {
    $cache = Join-Path $env:USERPROFILE ".cache\huggingface\token"
    if (Test-Path -LiteralPath $cache) {
      $present = $true; $source = "file:~/.cache/huggingface/token"
    }
  }
  return [ordered]@{ present = $present; source = $source }
}

function Read-LocalHfToken {
  if (-not [string]::IsNullOrWhiteSpace($env:HF_TOKEN)) { return $env:HF_TOKEN }
  if (-not [string]::IsNullOrWhiteSpace($env:HUGGING_FACE_HUB_TOKEN)) { return $env:HUGGING_FACE_HUB_TOKEN }
  if (-not [string]::IsNullOrWhiteSpace($env:HUGGINGFACE_TOKEN)) { return $env:HUGGINGFACE_TOKEN }
  $cache = Join-Path $env:USERPROFILE ".cache\huggingface\token"
  if (Test-Path -LiteralPath $cache) {
    return (Get-Content -LiteralPath $cache -Raw).Trim()
  }
  return $null
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$script:KeyPath = Resolve-IdentityPath -Path $IdentityFile
if (!(Test-Path -LiteralPath $script:KeyPath)) {
  throw "SSH identity not found: $($script:KeyPath)"
}
$script:SshExe = Get-SshExecutable -Name "ssh"
$script:ScpExe = Get-SshExecutable -Name "scp"

$localOnPodSh = Join-Path $ProjectRoot "tools\fetch_wan22_ti2v_5b_on_pod.sh"
if (!(Test-Path -LiteralPath $localOnPodSh)) {
  throw "Companion on-pod script missing: $localOnPodSh"
}

$remoteOnPodSh = "/workspace/tools/fetch_wan22_ti2v_5b_on_pod.sh"
$remoteLogDir = "/workspace/logs/wan22_ti2v_5b_fetch"
$remoteStateDir = "/workspace/runtime_artifacts/wan22_ti2v_5b_fetch"
$remoteStatus = "$remoteStateDir/status_latest.json"
$remotePidFile = "$remoteStateDir/fetch.pid"

$result = [ordered]@{
  schema_version = "1.0"
  script = "tools/Fetch-RunPodWan22Ti2V5B.ps1"
  created_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  authority = "RunPod_ONLY"
  pod_id = $PodId
  ssh = "${RemoteUser}@${RemoteHost}:${RemotePort}"
  identity_file = $script:KeyPath
  companion_local = "tools/fetch_wan22_ti2v_5b_on_pod.sh"
  companion_remote = $remoteOnPodSh
  status = "unknown"
  mode = $(if ($StatusOnly) { "status_only" } elseif ($Foreground) { "foreground" } else { "detached" })
  ec2_touched = $false
  local_comfy_touched = $false
  row074_touched = $false
  hf_auth = [ordered]@{}
  blockers = @()
}

Write-Host "Fetch-RunPodWan22Ti2V5B: pod=$PodId ssh=$($result.ssh) mode=$($result.mode)"

$probeCmd = @'
set -e
hostname
test -f /workspace/paths.env
. /workspace/paths.env
echo PATHS_ENV=ok
if [ -n "${HF_TOKEN:-}" ] || [ -n "${HUGGING_FACE_HUB_TOKEN:-}" ] || [ -n "${HUGGINGFACE_TOKEN:-}" ] || [ -f /root/.cache/huggingface/token ] || [ -f /root/.huggingface/token ]; then
  echo POD_HF_AUTH=present
else
  echo POD_HF_AUTH=absent
fi
command -v huggingface-cli >/dev/null && echo HF_CLI=present || echo HF_CLI=absent
command -v wget >/dev/null && echo WGET=present || echo WGET=absent
command -v curl >/dev/null && echo CURL=present || echo CURL=absent
df -h /workspace | tail -n 1
if [ -f /workspace/runtime_artifacts/wan22_ti2v_5b_fetch/status_latest.json ]; then
  echo STATUS_JSON_PRESENT=1
  python3 -c "import json; o=json.load(open('/workspace/runtime_artifacts/wan22_ti2v_5b_fetch/status_latest.json')); print('STATUS='+str(o.get('status','?'))); print('RATIO='+str(o.get('present_ratio','?')))"
else
  echo STATUS_JSON_PRESENT=0
fi
if [ -f /workspace/runtime_artifacts/wan22_ti2v_5b_fetch/fetch.pid ]; then
  pid=$(cat /workspace/runtime_artifacts/wan22_ti2v_5b_fetch/fetch.pid)
  if kill -0 "$pid" 2>/dev/null; then echo FETCH_PID_ALIVE=$pid; else echo FETCH_PID_STALE=$pid; fi
else
  echo FETCH_PID=none
fi
for p in \
  /workspace/ComfyUI/models/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors \
  /workspace/ComfyUI/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  /workspace/ComfyUI/models/vae/wan2.2_vae.safetensors
do
  if [ -f "$p" ]; then echo "ASSET_PRESENT $(stat -c %s "$p") $p"; else echo "ASSET_ABSENT $p"; fi
done
'@

$probeCapture = $probeCmd | & $script:SshExe -i $script:KeyPath -p $RemotePort -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new "${RemoteUser}@${RemoteHost}" "bash -s" 2>&1
$probeRc = $LASTEXITCODE
if ($probeRc -ne 0) {
  $result.status = "blocked"
  $result.blockers += "SSH_PROBE_FAILED_rc=$probeRc"
  $result.probe = ($probeCapture | Out-String)
  $result | ConvertTo-Json -Depth 8
  exit 2
}
$result.probe = ($probeCapture | Out-String)
$podHfAuthPresent = ($result.probe -match "POD_HF_AUTH=present")
$localHf = Get-LocalHfTokenPresence
$result.hf_auth = [ordered]@{
  pod_present = [bool]$podHfAuthPresent
  local_present = [bool]$localHf.present
  local_source = $localHf.source
  secrets_printed = $false
}

if ($StatusOnly) {
  $result.status = "status_only"
  $result | ConvertTo-Json -Depth 8
  exit 0
}

if (-not $SkipDeploy) {
  Write-Host "Deploying companion script to $remoteOnPodSh"
  $mkdirBody = "mkdir -p /workspace/tools '$remoteLogDir' '$remoteStateDir' && chmod +x '$remoteOnPodSh' 2>/dev/null || true"
  $null = $mkdirBody | & $script:SshExe -i $script:KeyPath -p $RemotePort -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new "${RemoteUser}@${RemoteHost}" "bash -s"
  & $script:ScpExe -i $script:KeyPath -P $RemotePort -o BatchMode=yes -o StrictHostKeyChecking=accept-new `
    $localOnPodSh "${RemoteUser}@${RemoteHost}:${remoteOnPodSh}"
  if ($LASTEXITCODE -ne 0) {
    $result.status = "blocked"
    $result.blockers += "SCP_DEPLOY_FAILED"
    $result | ConvertTo-Json -Depth 8
    exit 3
  }
  $chmodBody = "chmod +x '$remoteOnPodSh'"
  $null = $chmodBody | & $script:SshExe -i $script:KeyPath -p $RemotePort -o BatchMode=yes -o ConnectTimeout=20 "${RemoteUser}@${RemoteHost}" "bash -s"
}

$tokenExportPrefix = ""
$result.hf_auth.forwarded_local_token = $false
if ($ForwardLocalHfToken) {
  $token = Read-LocalHfToken
  if ([string]::IsNullOrWhiteSpace($token)) {
    $result.status = "blocked"
    $result.blockers += "FORWARD_LOCAL_HF_TOKEN_REQUESTED_BUT_MISSING"
    $result | ConvertTo-Json -Depth 8
    exit 14
  }
  $escaped = $token.Replace("'", "'\''")
  $tokenExportPrefix = "export HF_TOKEN='$escaped'; export HUGGING_FACE_HUB_TOKEN='$escaped';`n"
  $result.hf_auth.forwarded_local_token = $true
  $result.hf_auth.forward_note = "token forwarded to remote process env only; not written to disk by this script; value never printed"
  Write-Host "HF auth: forwarding local token to pod process env (value not printed)"
}

$preflight = @"
set -e
. /workspace/paths.env
$tokenExportPrefix
URL="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/fb1388adc906ab39ffc26ee40e96b22886b56bc4/split_files/vae/wan2.2_vae.safetensors"
if [ -n "`${HF_TOKEN:-}" ]; then
  code=`$(curl -sS -o /dev/null -w "%{http_code}" -I -L --max-time 30 -H "Authorization: Bearer `${HF_TOKEN}" "`$URL" || echo 000)
else
  code=`$(curl -sS -o /dev/null -w "%{http_code}" -I -L --max-time 30 "`$URL" || echo 000)
fi
echo PREFLIGHT_HTTP=`$code
if [ -n "`${HF_TOKEN:-}" ] || [ -n "`${HUGGING_FACE_HUB_TOKEN:-}" ] || [ -f /root/.cache/huggingface/token ]; then
  echo AUTH_EFFECTIVE=present
else
  echo AUTH_EFFECTIVE=absent
fi
"@

$preOut = $preflight | & $script:SshExe -i $script:KeyPath -p $RemotePort -o BatchMode=yes -o ConnectTimeout=20 "${RemoteUser}@${RemoteHost}" "bash -s" 2>&1
$preHttp = $null
foreach ($line in $preOut) {
  if ($line -match "PREFLIGHT_HTTP=(\d+)") { $preHttp = $Matches[1] }
}
$authEff = (($preOut | Out-String) -match "AUTH_EFFECTIVE=present")
$result.preflight_http = $preHttp
$result.hf_auth.effective_present = [bool]$authEff

if ($preHttp -in @("401", "403") -and -not $authEff) {
  $result.status = "blocked"
  $result.blockers += "NO_HF_AUTH_ON_POD_GATED_ASSET"
  $result.blocker_detail = "HF returned $preHttp and no effective HF auth after paths.env / optional local forward. Fail closed."
  $result | ConvertTo-Json -Depth 8
  Write-Error $result.blocker_detail
  exit 14
}

if ($preHttp -and $preHttp -notin @("200", "302", "307", "308", "401", "403")) {
  $result.status = "blocked"
  $result.blockers += "HF_PREFLIGHT_HTTP_$preHttp"
  $result | ConvertTo-Json -Depth 8
  exit 13
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$remoteLog = "$remoteLogDir/fetch_${stamp}.log"

if ($Foreground) {
  Write-Host "Starting foreground on-pod fetch (blocking). log=$remoteLog"
  $fg = @"
set -e
$tokenExportPrefix
export WAN22_FETCH_LOG_FILE='$remoteLog'
export WAN22_FETCH_STATUS_FILE='$remoteStatus'
bash '$remoteOnPodSh'
"@
  $fg | & $script:SshExe -i $script:KeyPath -p $RemotePort -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=240 "${RemoteUser}@${RemoteHost}" "bash -s"
  $rc = $LASTEXITCODE
  $result.log_file = $remoteLog
  $result.status_file = $remoteStatus
  if ($rc -eq 0) {
    $result.status = "complete_3_of_3_verified"
  } else {
    $result.status = "failed"
    $result.exit_code = $rc
  }
  $result | ConvertTo-Json -Depth 8
  exit $rc
}

Write-Host "Starting detached on-pod fetch. log=$remoteLog status=$remoteStatus"
$detach = @"
set -e
mkdir -p '$remoteLogDir' '$remoteStateDir'
$tokenExportPrefix
export WAN22_FETCH_LOG_FILE='$remoteLog'
export WAN22_FETCH_STATUS_FILE='$remoteStatus'
if [ -f '$remotePidFile' ]; then
  old=`$(cat '$remotePidFile')
  if kill -0 "`$old" 2>/dev/null; then
    echo ALREADY_RUNNING pid=`$old
    echo LOG_FILE=`$(tr -d '\n' < /proc/`$old/environ 2>/dev/null | tr '\0' '\n' | awk -F= '/^WAN22_FETCH_LOG_FILE=/{print substr(`$0,21); exit}')
    echo STATUS_FILE='$remoteStatus'
    exit 0
  fi
fi
nohup bash '$remoteOnPodSh' >>'$remoteLog' 2>&1 &
echo `$! > '$remotePidFile'
sleep 2
if kill -0 "`$(cat '$remotePidFile')" 2>/dev/null; then
  echo STARTED_PID=`$(cat '$remotePidFile')
else
  echo START_FAILED
  tail -n 40 '$remoteLog' || true
  exit 1
fi
echo LOG_FILE='$remoteLog'
echo STATUS_FILE='$remoteStatus'
sleep 3
tail -n 40 '$remoteLog' || true
"@

$detOut = $detach | & $script:SshExe -i $script:KeyPath -p $RemotePort -o BatchMode=yes -o ConnectTimeout=20 "${RemoteUser}@${RemoteHost}" "bash -s" 2>&1
$detRc = $LASTEXITCODE
$result.detached_output = ($detOut | Out-String)
$result.log_file = $remoteLog
$result.status_file = $remoteStatus

if ($detRc -ne 0) {
  $result.status = "blocked"
  $result.blockers += "DETACH_START_FAILED"
  $result | ConvertTo-Json -Depth 8
  exit 4
}

$startedPid = $null
foreach ($line in $detOut) {
  if ($line -match "STARTED_PID=(\d+)") { $startedPid = $Matches[1]; break }
  if ($line -match "ALREADY_RUNNING pid=(\d+)") { $startedPid = $Matches[1]; break }
}

$result.fetch_pid = $startedPid
if (($detOut | Out-String) -match "ALREADY_RUNNING") {
  $result.status = "in_progress_already_running"
} else {
  $result.status = "in_progress_detached"
}
$result.next_action = "Poll with -StatusOnly; when present_ratio=3/3 and status=complete_3_of_3_verified, land evidence + Tracker Notes ASSET_PRESENT only (no COMPLETE). Row074 untouched."

$result | ConvertTo-Json -Depth 8
Write-Host "status=$($result.status) pid=$startedPid log=$remoteLog"
exit 0
