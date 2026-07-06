<#
.SYNOPSIS
Runs the EC2 object-info/path/hash proof for a selected ComfyUI workflow lane.

.DESCRIPTION
This script is dry-run by default. With -Execute, it starts the approved EC2
instance, updates the remote project checkout, checks ComfyUI /object_info for
required nodes, resolves and hashes required model files, records output, then
stops the instance and verifies it is stopped. It performs no generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$LaneId = "sdxl_low_risk_fallback_lane",
  [string]$RemoteProjectRoot = "/home/ubuntu/Comfy_UI_Main",
  [string]$RemoteComfyRoot = "/home/ubuntu/ComfyUI",
  [string]$AuthGateFile = "",
  [string]$ReadinessFile = "",
  [string]$OutFile = "",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }

  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
  return $relativePath.Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Find-LatestFile {
  param(
    [string]$Directory,
    [string]$Filter
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $file = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
}

function Get-AuthGateStatus {
  param([string]$Path)

  $result = [ordered]@{
    file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    found = (![string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path))
    expected_account = "029530099913"
    account_match = $false
    ec2_work_allowed = $false
    safe_to_start_ec2 = $false
    generation_allowed = $false
    result = "missing_auth_gate"
    status = "missing_auth_gate"
    failure_category = "missing_auth_gate"
    remote_login_status = "missing_auth_gate"
  }

  if (!$result.found) { return $result }
  $auth = Read-JsonFile -Path $Path
  $result.failure_category = $null
  $result.remote_login_status = $null
  $result.expected_account = [string]$auth.expected_account
  $result.ec2_work_allowed = [bool]$auth.ec2_work_allowed
  $result.safe_to_start_ec2 = [bool]$auth.safe_to_start_ec2
  $result.generation_allowed = [bool]$auth.generation_allowed
  if (Has-Property -Object $auth -Name "result") {
    $result.result = [string]$auth.result
  } else {
    $result.result = $(if ($result.safe_to_start_ec2) { "pass" } else { "blocked" })
  }
  if (Has-Property -Object $auth -Name "failure_category") {
    $result.failure_category = $auth.failure_category
  }
  if (Has-Property -Object $auth -Name "account_match") {
    $result.account_match = [bool]$auth.account_match
  }
  if (Has-Property -Object $auth -Name "remote_login_status") {
    $result.remote_login_status = [string]$auth.remote_login_status
  }
  if (Has-Property -Object $auth -Name "sts_after" -and $null -ne $auth.sts_after) {
    $result.account_match = [bool]$auth.sts_after.account_match
    if ([string]::IsNullOrWhiteSpace([string]$result.failure_category)) {
      $result.failure_category = [string]$auth.sts_after.failure_category
    }
  } elseif (Has-Property -Object $auth -Name "sts_before" -and $null -ne $auth.sts_before) {
    $result.account_match = [bool]$auth.sts_before.account_match
    if ([string]::IsNullOrWhiteSpace([string]$result.failure_category)) {
      $result.failure_category = [string]$auth.sts_before.failure_category
    }
  }
  if (Has-Property -Object $auth -Name "remote_login" -and $null -ne $auth.remote_login) {
    $result.remote_login_status = [string]$auth.remote_login.status
  }
  $result.status = $(if ($result.safe_to_start_ec2) { "pass" } else { "blocked" })
  return $result
}

function Get-ReadinessStatus {
  param([string]$Path)

  $result = [ordered]@{
    file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    found = (![string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path))
    local_pre_ec2_ready = $false
    ready_for_ec2_static_proof = $false
    ready_for_generation = $false
    result = "missing_readiness_record"
    failure_category = "missing_readiness_record"
    status = "missing_readiness_record"
  }
  if (!$result.found) { return $result }
  $readiness = Read-JsonFile -Path $Path
  $result.failure_category = $null
  $result.local_pre_ec2_ready = [bool]$readiness.local_pre_ec2_ready
  $result.ready_for_ec2_static_proof = [bool]$readiness.ready_for_ec2_static_proof
  $result.ready_for_generation = [bool]$readiness.ready_for_generation
  if (Has-Property -Object $readiness -Name "result") {
    $result.result = [string]$readiness.result
  } else {
    $result.result = $(if ($result.ready_for_ec2_static_proof) { "ready_for_ec2_static_proof" } elseif ($result.local_pre_ec2_ready) { "local_pre_ec2_ready_runtime_blocked" } else { "not_ready" })
  }
  if (Has-Property -Object $readiness -Name "failure_category") {
    $result.failure_category = $readiness.failure_category
  }
  $result.status = $(if ($result.ready_for_ec2_static_proof) { "static_proof_ready" } elseif ($result.local_pre_ec2_ready) { "local_ready_runtime_blocked" } else { "not_ready" })
  return $result
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
if ([string]::IsNullOrWhiteSpace($AuthGateFile)) {
  $AuthGateFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_AUTH_GATE_*.json"
}
if ([string]::IsNullOrWhiteSpace($ReadinessFile)) {
  $ReadinessFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W61_LANE_RUNTIME_READINESS_*.json"
}

$authGate = Get-AuthGateStatus -Path $AuthGateFile
$readinessGate = Get-ReadinessStatus -Path $ReadinessFile
$blockedReasons = @()
if ($InstanceId -ne "i-0560bf8d143f93bb1") { $blockedReasons += "InstanceId is not the approved EC2 instance." }
if (!$authGate.safe_to_start_ec2) { $blockedReasons += "Auth gate does not allow EC2 start." }
if (!$readinessGate.ready_for_ec2_static_proof) { $blockedReasons += "Lane readiness gate does not allow EC2 static proof." }
$executeGatesPass = ($blockedReasons.Count -eq 0)
$gateFailureCategory = $null
if ($InstanceId -ne "i-0560bf8d143f93bb1") {
  $gateFailureCategory = "unapproved_instance"
} elseif (!$authGate.safe_to_start_ec2) {
  $gateFailureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$authGate.failure_category)) { [string]$authGate.failure_category } else { "aws_auth_blocked" })
} elseif (!$readinessGate.ready_for_ec2_static_proof) {
  $gateFailureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$readinessGate.failure_category)) { [string]$readinessGate.failure_category } else { "lane_readiness_blocked" })
}
$staticProofGateResult = $(if ($executeGatesPass) { "ready_for_ec2_static_proof_execute" } else { "blocked_before_ec2_start" })

if (-not $Execute) {
  if ([string]::IsNullOrWhiteSpace($OutFile)) {
    $OutFile = Join-Path $workflowStaticDir "W61_EC2_LANE_STATIC_PROOF_DRY_RUN_GATED_$stamp.json"
  }
  $plan = [ordered]@{
    evidence_id = "EC2-LANE-STATIC-PROOF-DRY-RUN-" + $stamp
    timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    mode = "dry_run"
    instance_id = $InstanceId
    region = $Region
    lane_id = $LaneId
    result = $(if ($executeGatesPass) { "dry_run_ready_for_ec2_static_proof_execute" } else { "dry_run_blocked_before_ec2_start" })
    failure_category = $gateFailureCategory
    auth_gate = $authGate
    readiness_gate = $readinessGate
    execute_gates_pass = $executeGatesPass
    blocked_reasons = $blockedReasons
    actions = @(
      "Verify AWS account and EC2 identity.",
      "Require auth gate safe_to_start_ec2=true before EC2 start.",
      "Require lane readiness ready_for_ec2_static_proof=true before EC2 start.",
      "Start instance only if stopped.",
      "Wait for EC2 status checks and SSM online.",
      "Update remote project checkout and Git LFS.",
      "Read lane runtime_requirements.json.",
      "Launch ComfyUI only for /object_info.",
      "Resolve and sha256 required model files.",
      "Stop EC2 and verify stopped."
    )
    generation_executed = $false
  }
  if (![string]::IsNullOrWhiteSpace($OutFile)) {
    $outDir = Split-Path -Parent $OutFile
    if (![string]::IsNullOrWhiteSpace($outDir)) {
      $null = New-Item -ItemType Directory -Force -Path $outDir
    }
    $plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutFile -Encoding UTF8
    Write-Host "Wrote EC2 lane static proof dry-run plan: $OutFile"
  }
  $plan | ConvertTo-Json -Depth 8
  exit 0
}

if (!$executeGatesPass) {
  if ([string]::IsNullOrWhiteSpace($OutFile)) {
    $OutFile = Join-Path $workflowStaticDir "W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_$stamp.json"
  }
  $record = [ordered]@{
    evidence_id = "EC2-LANE-STATIC-PROOF-BLOCKED-" + $stamp
    timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    mode = "execute"
    instance_id = $InstanceId
    region = $Region
    lane_id = $LaneId
    result = "blocked_before_ec2_start"
    failure_category = $gateFailureCategory
    auth_gate = $authGate
    readiness_gate = $readinessGate
    execute_gates_pass = $false
    blocked_reasons = $blockedReasons
    start_state = $null
    ec2_started = $false
    ssm_available = $false
    command_id = $null
    command_status = "not_started"
    stdout = ""
    stderr = ""
    final_state = $null
    generation_executed = $false
    errors = @("Execution blocked before AWS identity check or EC2 start.")
    next_action = "Resolve blocked_reasons, then rerun EC2 static proof."
  }
  if (![string]::IsNullOrWhiteSpace($OutFile)) {
    $outDir = Split-Path -Parent $OutFile
    if (![string]::IsNullOrWhiteSpace($outDir)) {
      $null = New-Item -ItemType Directory -Force -Path $outDir
    }
    $record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutFile -Encoding UTF8
    Write-Host "Wrote blocked EC2 lane static proof record: $OutFile"
  }
  $record | ConvertTo-Json -Depth 20
  exit 2
}

. (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1") -ProjectRoot $ProjectRoot -Quiet

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $workflowStaticDir "W61_EC2_LANE_STATIC_PROOF_$stamp.json"
}

$identityScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-AwsComfyGpuIdentity.ps1"
& $identityScript -ProjectRoot $ProjectRoot -InstanceId $InstanceId -ExpectedAccount "029530099913"
if ($LASTEXITCODE -ne 0) { throw "AWS/EC2 identity check failed. EC2 lane static proof aborted." }

$startTime = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$commandId = $null
$commandStatus = "NotStarted"
$stdout = ""
$stderr = ""
$started = $false
$ssmAvailable = $false
$startState = ""
$finalState = ""

$remoteScript = @"
python3 - <<'PY'
import os, json, subprocess, glob, hashlib, time, urllib.request, signal, datetime, traceback

PROJECT = "$RemoteProjectRoot"
COMFY = "$RemoteComfyRoot"
LANE_ID = "$LaneId"
MODELS = os.path.join(COMFY, "models")
PORT = 8191

result = {
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "lane_id": LANE_ID,
    "remote_project": {"path": PROJECT},
    "remote_comfyui": {"path": COMFY},
    "object_info": {"executed": False, "status": "not_started"},
    "model_proofs": [],
    "errors": []
}

def run(cmd, cwd=None, timeout=240, check=False):
    p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError("command failed rc=%s: %s\nSTDOUT=%s\nSTDERR=%s" % (p.returncode, " ".join(cmd), p.stdout[-1000:], p.stderr[-1000:]))
    return {"rc": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

try:
    if not os.path.isdir(PROJECT):
        raise RuntimeError("remote project missing: " + PROJECT)
    if not os.path.exists(os.path.join(COMFY, "main.py")):
        raise RuntimeError("ComfyUI main.py missing under " + COMFY)

    before = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
    pull = run(["git", "pull", "--ff-only", "origin", "main"], cwd=PROJECT, timeout=300, check=True)
    lfs = run(["git", "lfs", "pull"], cwd=PROJECT, timeout=300, check=True)
    after = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
    status = run(["git", "status", "--porcelain"], cwd=PROJECT, check=True)["stdout"]
    result["remote_project"].update({
        "head_before": before,
        "head_after": after,
        "status_clean": status == "",
        "git_pull_summary": pull["stdout"][-500:],
        "git_lfs_pull_rc": lfs["rc"]
    })

    lane_dir = os.path.join(PROJECT, "Plan", "07_IMPLEMENTATION", "workflow_templates", "base_generation", LANE_ID)
    runtime_path = os.path.join(lane_dir, "runtime_requirements.json")
    if not os.path.exists(runtime_path):
        raise RuntimeError("runtime_requirements.json missing for " + LANE_ID)
    with open(runtime_path, "r", encoding="utf-8") as f:
        runtime = json.load(f)

    required_nodes = runtime.get("required_nodes", [])
    py_candidates = [
        os.path.join(COMFY, "venv", "bin", "python"),
        os.path.join(COMFY, ".venv", "bin", "python"),
        "/usr/bin/python3",
        "python3"
    ]
    py_exec = next((p for p in py_candidates if (os.path.isabs(p) and os.path.exists(p)) or not os.path.isabs(p)), "python3")
    log_path = "/tmp/codex_comfy_object_info_%s.log" % int(time.time())
    proc = None
    try:
        result["object_info"] = {"executed": True, "status": "starting", "port": PORT, "log_path": log_path, "python": py_exec}
        log = open(log_path, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen([py_exec, "main.py", "--listen", "127.0.0.1", "--port", str(PORT)], cwd=COMFY, stdout=log, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        obj = None
        last_error = ""
        for _ in range(90):
            if proc.poll() is not None:
                last_error = "ComfyUI exited early rc=%s" % proc.returncode
                break
            try:
                with urllib.request.urlopen("http://127.0.0.1:%s/object_info" % PORT, timeout=2) as resp:
                    obj = json.loads(resp.read().decode("utf-8"))
                    break
            except Exception as exc:
                last_error = str(exc)
                time.sleep(2)
        if obj is None:
            result["object_info"].update({"status": "fail", "last_error": last_error})
        else:
            presence = {node: (node in obj) for node in required_nodes}
            result["object_info"].update({
                "status": "pass" if all(presence.values()) else "partial",
                "node_count": len(obj),
                "required_node_presence": presence
            })
    finally:
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=15)
            except Exception:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                result["object_info"]["log_tail"] = "".join(f.readlines()[-40:])[-3000:]

    for model in runtime.get("required_models", []):
        subdir = model.get("comfyui_model_subdir", "")
        filename = model.get("filename", "")
        path = os.path.join(MODELS, subdir, filename)
        proof = {
            "role": model.get("role"),
            "relative_path": os.path.relpath(path, MODELS).replace(os.sep, "/"),
            "exists": os.path.exists(path)
        }
        if os.path.exists(path):
            proof["bytes"] = os.path.getsize(path)
            proof["sha256"] = sha256_file(path)
        result["model_proofs"].append(proof)
except Exception as exc:
    result["errors"].append(str(exc))
    result["traceback"] = traceback.format_exc()[-4000:]

print(json.dumps(result, sort_keys=True))
PY
"@

try {
  $startState = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($startState -ne "running") {
    aws ec2 start-instances --region $Region --instance-ids $InstanceId --output json | Out-Null
    $started = $true
  }
  aws ec2 wait instance-running --region $Region --instance-ids $InstanceId
  aws ec2 wait instance-status-ok --region $Region --instance-ids $InstanceId

  for ($i = 0; $i -lt 30; $i++) {
    $ping = (aws ssm describe-instance-information --region $Region --filters "Key=InstanceIds,Values=$InstanceId" --query "InstanceInformationList[0].PingStatus" --output text 2>$null).Trim()
    if ($ping -eq "Online") { $ssmAvailable = $true; break }
    Start-Sleep -Seconds 10
  }
  if (-not $ssmAvailable) { throw "SSM did not become Online for $InstanceId" }

  $payloadPath = Join-Path $env:TEMP ("codex_ec2_lane_static_proof_{0}.json" -f $stamp)
  $payload = @{
    DocumentName = "AWS-RunShellScript"
    InstanceIds = @($InstanceId)
    Parameters = @{ commands = @($remoteScript); executionTimeout = @("1200") }
    CloudWatchOutputConfig = @{ CloudWatchOutputEnabled = $false }
  } | ConvertTo-Json -Depth 8
  [System.IO.File]::WriteAllText($payloadPath, $payload, [System.Text.UTF8Encoding]::new($false))

  $commandId = (aws ssm send-command --region $Region --cli-input-json "file://$payloadPath" --query "Command.CommandId" --output text).Trim()
  for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep -Seconds 5
    $commandStatus = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $commandId --query "Status" --output text 2>$null).Trim()
    if ($commandStatus -in @("Success", "Cancelled", "TimedOut", "Failed", "Cancelling")) { break }
  }
  $stdout = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $commandId --query "StandardOutputContent" --output text
  $stderr = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $commandId --query "StandardErrorContent" --output text
}
finally {
  aws ec2 stop-instances --region $Region --instance-ids $InstanceId --output json | Out-Null
  aws ec2 wait instance-stopped --region $Region --instance-ids $InstanceId
  $finalState = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
}

$record = [ordered]@{
  evidence_id = "EC2-LANE-STATIC-PROOF-" + $stamp
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  start_time = $startTime
  instance_id = $InstanceId
  region = $Region
  lane_id = $LaneId
  auth_gate = $authGate
  readiness_gate = $readinessGate
  execute_gates_pass = $executeGatesPass
  blocked_reasons = $blockedReasons
  result = $staticProofGateResult
  failure_category = $gateFailureCategory
  start_state = $startState
  ec2_started = $started
  ssm_available = $ssmAvailable
  command_id = $commandId
  command_status = $commandStatus
  stdout = $stdout
  stderr = $stderr
  final_state = $finalState
  generation_executed = $false
}

if ($commandStatus -eq "Success" -and $finalState -eq "stopped") {
  $record.result = "ec2_static_proof_recorded"
  $record.failure_category = $null
} elseif ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) {
  $record.result = "ec2_static_proof_failed"
  $record.failure_category = "ec2_static_proof_failed"
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote EC2 lane static proof record: $OutFile"
}

$record | ConvertTo-Json -Depth 20
if ($commandStatus -ne "Success" -or $finalState -ne "stopped") { exit 2 }
