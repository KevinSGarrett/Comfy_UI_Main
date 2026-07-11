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
  [string]$DeployBundleS3Uri = "",
  [string]$DeployBundleSha256 = "",
  [int]$MaxEc2RuntimeMinutes = 25,
  [switch]$SkipGitLfsPull,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
$startFailureClassifier = Join-Path $PSScriptRoot "EC2StartFailureClassification.ps1"
. $startFailureClassifier

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

function Test-JsonMatchesLane {
  param(
    [object]$Payload,
    [string]$ExpectedLaneId
  )

  if ($null -eq $Payload -or [string]::IsNullOrWhiteSpace($ExpectedLaneId)) { return $false }
  if ((Has-Property -Object $Payload -Name "lane_id") -and [string]$Payload.lane_id -eq $ExpectedLaneId) {
    return $true
  }
  if (Has-Property -Object $Payload -Name "lane_dir") {
    $laneDirText = ([string]$Payload.lane_dir).Replace("\", "/").TrimEnd("/")
    return $laneDirText.EndsWith("/$ExpectedLaneId", [System.StringComparison]::OrdinalIgnoreCase)
  }
  return $false
}

function Find-LatestJsonByLaneId {
  param(
    [string]$Directory,
    [string]$Filter,
    [string]$ExpectedLaneId,
    [string]$ExcludePattern = ""
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $files = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File
  if (![string]::IsNullOrWhiteSpace($ExcludePattern)) {
    $files = $files | Where-Object { $_.Name -notmatch $ExcludePattern }
  }
  foreach ($file in @($files | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonFile -Path $file.FullName
      if (Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $ExpectedLaneId) {
        return $file.FullName
      }
    } catch {
      continue
    }
  }
  return $null
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
    lane_id = $null
    lane_match = $false
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
  if (Has-Property -Object $readiness -Name "lane_id") {
    $result.lane_id = [string]$readiness.lane_id
  }
  $result.lane_match = ([string]$result.lane_id -eq [string]$LaneId)
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

function Get-LocalGitCheckpointGate {
  $result = [ordered]@{
    git_root = $null
    head = $null
    origin_main = $null
    expected_remote_head = $null
    local_matches_origin = $false
    clean = $false
    porcelain_count = $null
    remote = $null
    result = "fail"
    error = $null
  }

  try {
    Push-Location $ProjectRoot
    try {
      $result.git_root = (git rev-parse --show-toplevel 2>$null)
      if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.git_root)) {
        throw "Project root is not a Git checkout."
      }
      $result.head = (git rev-parse HEAD 2>$null)
      if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.head)) {
        throw "Unable to resolve local HEAD."
      }
      $result.origin_main = (git rev-parse origin/main 2>$null)
      if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.origin_main)) {
        throw "Unable to resolve origin/main."
      }
      $result.expected_remote_head = $result.origin_main
      $result.local_matches_origin = ([string]$result.head -eq [string]$result.origin_main)
      $porcelain = @(git status --porcelain 2>$null)
      $result.porcelain_count = $porcelain.Count
      $result.clean = ($porcelain.Count -eq 0)
      $remoteLines = @(git remote -v 2>$null)
      $result.remote = (($remoteLines | Where-Object { $_ -match "^origin\s+" }) | Select-Object -First 1)
      $result.result = $(if ($result.local_matches_origin -and $result.clean) { "pass" } else { "fail" })
    } finally {
      Pop-Location
    }
  } catch {
    $result.error = $_.Exception.Message
    $result.result = "fail"
  }

  return $result
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
if ([string]::IsNullOrWhiteSpace($AuthGateFile)) {
  $AuthGateFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "*AWS_AUTH_GATE*.json"
}
if ([string]::IsNullOrWhiteSpace($ReadinessFile)) {
  $ReadinessFile = Find-LatestJsonByLaneId -Directory $runtimeReadinessDir -Filter "*LANE_RUNTIME_READINESS_*.json" -ExpectedLaneId $LaneId
}

$authGate = Get-AuthGateStatus -Path $AuthGateFile
$readinessGate = Get-ReadinessStatus -Path $ReadinessFile
$localGitGate = Get-LocalGitCheckpointGate
$blockedReasons = @()
if ($InstanceId -ne "i-0560bf8d143f93bb1") { $blockedReasons += "InstanceId is not the approved EC2 instance." }
if ($localGitGate.result -ne "pass") { $blockedReasons += "Local Git checkpoint gate is not clean and synced to origin/main." }
if (!$authGate.safe_to_start_ec2) { $blockedReasons += "Auth gate does not allow EC2 start." }
if ($readinessGate.found -and !$readinessGate.lane_match) { $blockedReasons += "Lane readiness file does not match selected lane $LaneId." }
if (!$readinessGate.ready_for_ec2_static_proof) { $blockedReasons += "Lane readiness gate does not allow EC2 static proof." }
$executeGatesPass = ($blockedReasons.Count -eq 0)
$gateFailureCategory = $null
if ($InstanceId -ne "i-0560bf8d143f93bb1") {
  $gateFailureCategory = "unapproved_instance"
} elseif ($localGitGate.result -ne "pass") {
  $gateFailureCategory = $(if ($localGitGate.clean -ne $true) { "local_git_worktree_dirty" } elseif ($localGitGate.local_matches_origin -ne $true) { "local_git_not_synced_to_origin" } else { "local_git_checkpoint_invalid" })
} elseif (!$authGate.safe_to_start_ec2) {
  $gateFailureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$authGate.failure_category)) { [string]$authGate.failure_category } else { "aws_auth_blocked" })
} elseif ($readinessGate.found -and !$readinessGate.lane_match) {
  $gateFailureCategory = "lane_readiness_mismatch"
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
    max_ec2_runtime_minutes = $MaxEc2RuntimeMinutes
    git_lfs_pull_skipped = [bool]$SkipGitLfsPull.IsPresent
    deploy_bundle_s3_uri = $DeployBundleS3Uri
    deploy_bundle_sha256 = $DeployBundleSha256
    result = $(if ($executeGatesPass) { "dry_run_ready_for_ec2_static_proof_execute" } else { "dry_run_blocked_before_ec2_start" })
    failure_category = $gateFailureCategory
    local_git_checkpoint_gate = $localGitGate
    auth_gate = $authGate
    readiness_gate = $readinessGate
    execute_gates_pass = $executeGatesPass
    blocked_reasons = $blockedReasons
    ec2_started = $false
    actions = @(
      "Verify AWS account and EC2 identity.",
      "Require auth gate safe_to_start_ec2=true before EC2 start.",
      "Require lane readiness ready_for_ec2_static_proof=true before EC2 start.",
      "Start instance only if stopped.",
      "Wait for EC2 status checks and SSM online.",
      "Update remote project checkout and run Git LFS only when the lane explicitly needs it.",
      "Read lane runtime_requirements.json.",
      "Launch ComfyUI only for /object_info.",
      "Resolve and sha256 required model files.",
      "Stop EC2 and verify stopped."
    )
    generation_executed = $false
    active_runtime_marker_written = $false
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
    max_ec2_runtime_minutes = $MaxEc2RuntimeMinutes
    git_lfs_pull_skipped = [bool]$SkipGitLfsPull.IsPresent
    deploy_bundle_s3_uri = $DeployBundleS3Uri
    deploy_bundle_sha256 = $DeployBundleSha256
    result = "blocked_before_ec2_start"
    failure_category = $gateFailureCategory
    local_git_checkpoint_gate = $localGitGate
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
$executionErrorMessage = ""
$executionFailureCategory = $null
$expectedRemoteGitHead = [string]$localGitGate.expected_remote_head
$ssmExecutionTimeoutSeconds = [Math]::Max(600, $MaxEc2RuntimeMinutes * 60)

$remoteScript = @"
python3 - <<'PY'
import os, json, subprocess, glob, hashlib, time, urllib.request, signal, datetime, traceback, tempfile, shutil, zipfile

PROJECT = "$RemoteProjectRoot"
COMFY = "$RemoteComfyRoot"
LANE_ID = "$LaneId"
EXPECTED_GIT_HEAD = "$expectedRemoteGitHead"
SKIP_GIT_LFS_PULL = "$($SkipGitLfsPull.IsPresent)".lower() == "true"
DEPLOY_BUNDLE_S3_URI = "$DeployBundleS3Uri"
DEPLOY_BUNDLE_SHA256 = "$DeployBundleSha256".strip().lower()
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

def apply_deploy_bundle_if_configured():
    if not DEPLOY_BUNDLE_S3_URI:
        return None
    os.makedirs(PROJECT, exist_ok=True)
    bundle_path = os.path.join(tempfile.gettempdir(), "codex_deploy_bundle_%s.zip" % int(time.time()))
    download = run(["aws", "s3", "cp", DEPLOY_BUNDLE_S3_URI, bundle_path, "--only-show-errors"], timeout=900, check=True)
    actual_sha = sha256_file(bundle_path).lower()
    if DEPLOY_BUNDLE_SHA256 and actual_sha != DEPLOY_BUNDLE_SHA256:
        raise RuntimeError("deploy bundle sha256 mismatch: expected %s observed %s" % (DEPLOY_BUNDLE_SHA256, actual_sha))
    extract_root = tempfile.mkdtemp(prefix="codex_deploy_bundle_")
    try:
        with zipfile.ZipFile(bundle_path, "r") as zf:
            for member in zf.infolist():
                member_name = member.filename.replace("\\", "/")
                normalized = os.path.normpath(member_name)
                if normalized.startswith("..") or os.path.isabs(member_name):
                    raise RuntimeError("unsafe deploy bundle path: " + member.filename)
                target_path = os.path.join(extract_root, normalized)
                if member.is_dir() or member_name.endswith("/"):
                    os.makedirs(target_path, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zf.open(member, "r") as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        manifest = {}
        manifest_name = None
        for candidate in ["DEPLOY_BUNDLE_MANIFEST.json", "DEPLOY_BUNDLE_MATRIX_MANIFEST.json"]:
            manifest_path = os.path.join(extract_root, candidate)
            if os.path.exists(manifest_path):
                manifest_name = candidate
                with open(manifest_path, "r", encoding="utf-8-sig") as f:
                    manifest = json.load(f)
                break
        source_head = str(manifest.get("source_git_head") or "")
        if EXPECTED_GIT_HEAD and source_head and source_head != EXPECTED_GIT_HEAD:
            raise RuntimeError("deploy bundle source head %s did not match expected origin/main %s" % (source_head, EXPECTED_GIT_HEAD))
        copied_file_count = 0
        extracted_top_level = sorted(os.listdir(extract_root))
        for name in extracted_top_level:
            src = os.path.join(extract_root, name)
            dst = os.path.join(PROJECT, name)
            if os.path.isdir(src):
                for _, _, files in os.walk(src):
                    copied_file_count += len(files)
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied_file_count += 1
        return {
            "deployment_method": "s3_deploy_bundle",
            "s3_uri": DEPLOY_BUNDLE_S3_URI,
            "download_rc": download["rc"],
            "sha256": actual_sha,
            "sha256_expected": DEPLOY_BUNDLE_SHA256,
            "sha256_verified": (not DEPLOY_BUNDLE_SHA256) or actual_sha == DEPLOY_BUNDLE_SHA256,
            "manifest_name": manifest_name,
            "manifest_bundle_type": manifest.get("bundle_type"),
            "manifest_source_git_head": source_head,
            "manifest_lane_id": manifest.get("lane_id"),
            "manifest_matrix_id": manifest.get("matrix_id"),
            "manifest_sample_count": manifest.get("sample_count"),
            "manifest_file_count": manifest.get("file_count"),
            "extracted_top_level": extracted_top_level,
            "copied_file_count": copied_file_count,
            "git_lfs_pull_skipped": True
        }
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)

try:
    deployment = apply_deploy_bundle_if_configured()
    if deployment:
        result["remote_project"].update(deployment)
    if not os.path.isdir(PROJECT):
        raise RuntimeError("remote project missing: " + PROJECT)
    if not os.path.exists(os.path.join(COMFY, "main.py")):
        raise RuntimeError("ComfyUI main.py missing under " + COMFY)

    if not deployment:
        before = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
        pull = run(["git", "pull", "--ff-only", "origin", "main"], cwd=PROJECT, timeout=300, check=True)
        if SKIP_GIT_LFS_PULL:
            lfs = {"rc": 0, "stdout": "", "stderr": "", "skipped": True}
        else:
            lfs = run(["git", "lfs", "pull"], cwd=PROJECT, timeout=300, check=True)
            lfs["skipped"] = False
        after = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
        status = run(["git", "status", "--porcelain"], cwd=PROJECT, check=True)["stdout"]
        result["remote_project"].update({
            "deployment_method": "git_pull",
            "expected_head": EXPECTED_GIT_HEAD,
            "head_before": before,
            "head_after": after,
            "head_matches_expected": (not EXPECTED_GIT_HEAD) or after == EXPECTED_GIT_HEAD,
            "status_clean": status == "",
            "git_pull_summary": pull["stdout"][-500:],
            "git_lfs_pull_rc": lfs["rc"],
            "git_lfs_pull_skipped": lfs["skipped"]
        })
        if EXPECTED_GIT_HEAD and after != EXPECTED_GIT_HEAD:
            raise RuntimeError("remote project HEAD %s did not match expected origin/main %s" % (after, EXPECTED_GIT_HEAD))

    runtime_candidates = [
        os.path.join(PROJECT, "Plan", "07_IMPLEMENTATION", "workflow_templates", "base_generation", LANE_ID, "runtime_requirements.json"),
        os.path.join(PROJECT, "Workflows", "base_generation", LANE_ID, "runtime_requirements.json"),
        os.path.join(PROJECT, "runtime_artifacts", "run_packages", LANE_ID + "_static_package_v1", "lane_files", "runtime_requirements.json"),
    ]
    runtime_path = next((candidate for candidate in runtime_candidates if os.path.exists(candidate)), None)
    result["runtime_requirements"] = {
        "candidate_paths": runtime_candidates,
        "selected_path": runtime_path,
        "found": runtime_path is not None
    }
    if not runtime_path:
        raise RuntimeError("runtime_requirements.json missing for " + LANE_ID + "; candidates=" + "; ".join(runtime_candidates))
    with open(runtime_path, "r", encoding="utf-8-sig") as f:
        runtime = json.load(f)

    required_nodes = runtime.get("required_nodes", [])
    py_candidates = [
        os.path.join(COMFY, "venv", "bin", "python"),
        os.path.join(COMFY, ".venv", "bin", "python"),
        "/usr/bin/python3",
        "python3"
    ]
    py_exec = next((p for p in py_candidates if (os.path.isabs(p) and os.path.exists(p)) or not os.path.isabs(p)), "python3")
    log_path = os.path.join(tempfile.gettempdir(), "codex_comfy_object_info_%s.log" % int(time.time()))
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

function Wait-InstanceState {
  param(
    [Parameter(Mandatory=$true)][string]$DesiredState,
    [int]$MaxAttempts = 80,
    [int]$SleepSeconds = 5
  )

  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    Write-Host "EC2 state wait $i/$MaxAttempts desired=$DesiredState observed=$state"
    if ($state -eq $DesiredState) { return $state }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Timed out waiting for EC2 state '$DesiredState' on $InstanceId"
}

function Wait-InstanceStatusOk {
  param(
    [int]$MaxAttempts = 80,
    [int]$SleepSeconds = 5
  )

  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $status = aws ec2 describe-instance-status --region $Region --instance-ids $InstanceId --include-all-instances --query "InstanceStatuses[0].{system:SystemStatus.Status,instance:InstanceStatus.Status,state:InstanceState.Name}" --output json | ConvertFrom-Json
    Write-Host "EC2 status wait $i/$MaxAttempts state=$($status.state) system=$($status.system) instance=$($status.instance)"
    if ($status.state -eq "running" -and $status.system -eq "ok" -and $status.instance -eq "ok") { return $true }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Timed out waiting for EC2 instance status checks on $InstanceId"
}

try {
  $startState = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($startState -ne "running") {
    Write-Host "Starting EC2 instance $InstanceId from state $startState"
    $startOutput = @(aws ec2 start-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
    $startExitCode = $LASTEXITCODE
    if ($startExitCode -ne 0) {
      $startText = (($startOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
      $executionFailureCategory = Get-EC2StartFailureCategory -ExitCode $startExitCode -OutputText $startText
      throw "EC2 start-instances failed with exit code $startExitCode. $startText"
    }
    $started = $true
  }
  $null = Wait-InstanceState -DesiredState "running"
  $null = Wait-InstanceStatusOk

  for ($i = 0; $i -lt 30; $i++) {
    $ping = (aws ssm describe-instance-information --region $Region --filters "Key=InstanceIds,Values=$InstanceId" --query "InstanceInformationList[0].PingStatus" --output text 2>$null).Trim()
    Write-Host "SSM wait $($i + 1)/30 ping=$ping"
    if ($ping -eq "Online") { $ssmAvailable = $true; break }
    Start-Sleep -Seconds 10
  }
  if (-not $ssmAvailable) { throw "SSM did not become Online for $InstanceId" }

  $payloadPath = Join-Path $env:TEMP ("codex_ec2_lane_static_proof_{0}.json" -f $stamp)
  $payload = @{
    DocumentName = "AWS-RunShellScript"
    InstanceIds = @($InstanceId)
    TimeoutSeconds = $ssmExecutionTimeoutSeconds
    Parameters = @{ commands = @($remoteScript); executionTimeout = @([string]$ssmExecutionTimeoutSeconds) }
    CloudWatchOutputConfig = @{ CloudWatchOutputEnabled = $false }
  } | ConvertTo-Json -Depth 8
  [System.IO.File]::WriteAllText($payloadPath, $payload, [System.Text.UTF8Encoding]::new($false))

  $commandId = (aws ssm send-command --region $Region --cli-input-json "file://$payloadPath" --query "Command.CommandId" --output text).Trim()
  Write-Host "SSM command sent: $commandId"
  $maxCommandPolls = [Math]::Max(1, [int][Math]::Ceiling($ssmExecutionTimeoutSeconds / 5))
  for ($i = 0; $i -lt $maxCommandPolls; $i++) {
    Start-Sleep -Seconds 5
    $commandStatus = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $commandId --query "Status" --output text 2>$null).Trim()
    Write-Host "SSM command wait $($i + 1)/$maxCommandPolls status=$commandStatus"
    if ($commandStatus -in @("Success", "Cancelled", "TimedOut", "Failed", "Cancelling")) { break }
  }
  if ($commandStatus -notin @("Success", "Cancelled", "TimedOut", "Failed", "Cancelling")) {
    $commandStatus = "LocalTimeout"
    try {
      aws ssm cancel-command --region $Region --command-id $commandId --instance-ids $InstanceId --output json | Out-Null
    } catch {
      Write-Host "SSM cancel-command after local timeout failed: $($_.Exception.Message)"
    }
  }
  $stdout = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $commandId --query "StandardOutputContent" --output text
  $stderr = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $commandId --query "StandardErrorContent" --output text
}
catch {
  $executionErrorMessage = $_.Exception.Message
  if ([string]::IsNullOrWhiteSpace([string]$executionFailureCategory)) {
    $executionFailureCategory = "ec2_static_proof_exception"
  }
}
finally {
  $currentState = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($currentState -ne "stopped") {
    Write-Host "Stopping EC2 instance $InstanceId after static proof attempt"
    aws ec2 stop-instances --region $Region --instance-ids $InstanceId --output json | Out-Null
    $null = Wait-InstanceState -DesiredState "stopped" -MaxAttempts 120 -SleepSeconds 5
  }
  $finalState = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
}

$record = [ordered]@{
  evidence_id = "EC2-LANE-STATIC-PROOF-" + $stamp
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  start_time = $startTime
  instance_id = $InstanceId
  region = $Region
  lane_id = $LaneId
  max_ec2_runtime_minutes = $MaxEc2RuntimeMinutes
  ssm_execution_timeout_seconds = $ssmExecutionTimeoutSeconds
  git_lfs_pull_skipped = [bool]$SkipGitLfsPull.IsPresent
  deploy_bundle_s3_uri = $DeployBundleS3Uri
  deploy_bundle_sha256 = $DeployBundleSha256
  auth_gate = $authGate
  readiness_gate = $readinessGate
  execute_gates_pass = $executeGatesPass
  blocked_reasons = $blockedReasons
  result = $staticProofGateResult
  failure_category = $gateFailureCategory
  local_git_checkpoint_gate = $localGitGate
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

$staticProofErrors = @()
$staticProofFailureCategory = $executionFailureCategory
$remoteProofPayload = $null

if (![string]::IsNullOrWhiteSpace($executionErrorMessage)) {
  $staticProofErrors += $executionErrorMessage
}

if ($commandStatus -ne "Success") {
  $staticProofErrors += "SSM command status was $commandStatus."
  $staticProofFailureCategory = "ssm_command_failed"
}
if ($finalState -ne "stopped") {
  $staticProofErrors += "Final EC2 state was $finalState, expected stopped."
  if ([string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
    $staticProofFailureCategory = "ec2_stop_not_verified"
  }
}

foreach ($line in @($stdout)) {
  $candidate = ([string]$line).Trim()
  if ([string]::IsNullOrWhiteSpace($candidate) -or !$candidate.StartsWith("{")) { continue }
  try {
    $remoteProofPayload = $candidate | ConvertFrom-Json
    break
  } catch {
    continue
  }
}
if ($null -eq $remoteProofPayload) {
  $stdoutText = (($stdout | Out-String).Trim())
  if (![string]::IsNullOrWhiteSpace($stdoutText)) {
    try {
      $remoteProofPayload = $stdoutText | ConvertFrom-Json
    } catch {
      $staticProofErrors += "Remote static proof stdout was not parseable JSON."
      if ([string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
        $staticProofFailureCategory = "remote_static_proof_stdout_unparseable"
      }
    }
  } else {
    $staticProofErrors += "Remote static proof stdout was empty."
    if ([string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
      $staticProofFailureCategory = "remote_static_proof_stdout_empty"
    }
  }
}

$staticProofSummary = [ordered]@{
  remote_payload_parsed = ($null -ne $remoteProofPayload)
  remote_errors = @()
  object_info_pass = $false
  model_proof_count = 0
  model_missing_count = 0
  model_hash_missing_count = 0
  required_models_present = $false
  required_model_hashes_present = $false
  pass = $false
}

if ($null -ne $remoteProofPayload) {
  if (Has-Property -Object $remoteProofPayload -Name "remote_project") {
    $record.remote_project = $remoteProofPayload.remote_project
  }
  if (Has-Property -Object $remoteProofPayload -Name "errors") {
    $staticProofSummary.remote_errors = @($remoteProofPayload.errors)
    foreach ($remoteError in @($remoteProofPayload.errors)) {
      if (![string]::IsNullOrWhiteSpace([string]$remoteError)) {
        $staticProofErrors += "Remote proof error: $remoteError"
        if ([string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
          $staticProofFailureCategory = "remote_static_proof_error"
        }
      }
    }
  }
  if (Has-Property -Object $remoteProofPayload -Name "object_info") {
    $staticProofSummary.object_info_pass = ([string]$remoteProofPayload.object_info.status -eq "pass")
  }
  if (!$staticProofSummary.object_info_pass) {
    $staticProofErrors += "ComfyUI object_info proof did not pass."
    if ([string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
      $staticProofFailureCategory = "object_info_not_pass"
    }
  }
  if (Has-Property -Object $remoteProofPayload -Name "model_proofs") {
    $models = @($remoteProofPayload.model_proofs)
    $staticProofSummary.model_proof_count = $models.Count
    $staticProofSummary.model_missing_count = @($models | Where-Object { -not [bool]$_.exists }).Count
    $staticProofSummary.model_hash_missing_count = @($models | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.sha256) }).Count
    foreach ($model in $models) {
      if (-not [bool]$model.exists) {
        $staticProofErrors += "Required model missing in EC2 static proof: $($model.relative_path)"
      }
      if ([string]::IsNullOrWhiteSpace([string]$model.sha256)) {
        $staticProofErrors += "Required model missing sha256 in EC2 static proof: $($model.relative_path)"
      }
    }
    $staticProofSummary.required_models_present = ($models.Count -gt 0 -and $staticProofSummary.model_missing_count -eq 0)
    $staticProofSummary.required_model_hashes_present = ($models.Count -gt 0 -and $staticProofSummary.model_hash_missing_count -eq 0)
    if ($staticProofSummary.model_missing_count -gt 0 -and [string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
      $staticProofFailureCategory = "required_model_missing"
    } elseif ($staticProofSummary.model_hash_missing_count -gt 0 -and [string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
      $staticProofFailureCategory = "required_model_hash_missing"
    }
  } else {
    $staticProofErrors += "Remote static proof payload has no model_proofs."
    if ([string]::IsNullOrWhiteSpace($staticProofFailureCategory)) {
      $staticProofFailureCategory = "model_proofs_missing"
    }
  }
}

$staticProofSummary.pass = (
  $commandStatus -eq "Success" -and
  $finalState -eq "stopped" -and
  $staticProofSummary.remote_payload_parsed -eq $true -and
  $staticProofSummary.object_info_pass -eq $true -and
  $staticProofSummary.required_models_present -eq $true -and
  $staticProofSummary.required_model_hashes_present -eq $true -and
  $staticProofSummary.remote_errors.Count -eq 0 -and
  $staticProofErrors.Count -eq 0
)
$record.static_proof_summary = $staticProofSummary
$record.errors = $staticProofErrors

if ($staticProofSummary.pass) {
  $record.result = "ec2_static_proof_recorded"
  $record.failure_category = $null
} elseif ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) {
  $record.result = "ec2_static_proof_failed"
  $record.failure_category = $(if (![string]::IsNullOrWhiteSpace($staticProofFailureCategory)) { $staticProofFailureCategory } else { "ec2_static_proof_failed" })
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
