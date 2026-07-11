<#
.SYNOPSIS
Installs one EC2 ComfyUI model from S3 and verifies its SHA256.

.DESCRIPTION
Dry-run by default. With -Execute, starts the approved EC2 instance only long
enough to download one model binary from S3 into ComfyUI, verify SHA256, then
stops and verifies the instance is stopped. This script intentionally does not
use Git or Git LFS for model binaries.
#>
param(
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$SourceS3Uri = "",
  [string]$RemoteComfyRoot = "/home/ubuntu/ComfyUI",
  [string]$ModelSubdir = "checkpoints",
  [string]$ModelFileName = "realvisxlV50_v50Bakedvae.safetensors",
  [string]$ExpectedSha256 = "6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80",
  [string]$OutFile = "",
  [int]$MaxEc2RuntimeMinutes = 20,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
$startFailureClassifier = Join-Path $PSScriptRoot "EC2StartFailureClassification.ps1"
. $startFailureClassifier
$stopFailureClassifier = Join-Path $PSScriptRoot "EC2StopFailureClassification.ps1"
. $stopFailureClassifier

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Wait-InstanceState {
  param(
    [Parameter(Mandatory=$true)][string]$DesiredState,
    [int]$MaxAttempts = 80,
    [int]$SleepSeconds = 5
  )
  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    if ($state -eq $DesiredState) { return $state }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Instance $InstanceId did not reach state $DesiredState."
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W63_EC2_MODEL_INSTALL_$stamp.json"
}

$remoteModelPath = "$RemoteComfyRoot/models/$ModelSubdir/$ModelFileName"
$record = [ordered]@{
  schema_version = "1.0"
  evidence_id = "EC2-MODEL-INSTALL-$stamp"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "install_ec2_model_from_s3"
  instance_id = $InstanceId
  region = $Region
  source_s3_uri = $SourceS3Uri
  remote_comfy_root = $RemoteComfyRoot
  remote_model_path = $remoteModelPath
  model_subdir = $ModelSubdir
  model_file_name = $ModelFileName
  expected_sha256 = $ExpectedSha256.ToLowerInvariant()
  max_ec2_runtime_minutes = $MaxEc2RuntimeMinutes
  execute = [bool]$Execute
  ec2_started = $false
  ssm_available = $false
  command_id = $null
  command_status = "not_started"
  start_state = $null
  start_exit_code = $null
  start_output_tail = $null
  stop_exit_code = $null
  stop_output_tail = $null
  stop_failure_category = $null
  final_state = $null
  remote_result = $null
  generation_executed = $false
  git_lfs_used = $false
  result = $(if ($Execute) { "ready_for_model_install_execute" } else { "dry_run_model_install_plan" })
  failure_category = $null
  errors = @()
  next_action = "After install_model_hash_verified, rerun EC2 static proof with -SkipGitLfsPull and -MaxEc2RuntimeMinutes."
}

if ([string]::IsNullOrWhiteSpace($SourceS3Uri)) {
  $record.result = "blocked_missing_source_s3_uri"
  $record.failure_category = "missing_source_s3_uri"
  $record.next_action = "Upload the model binary to an approved S3 model-cache prefix first; do not use Git LFS for the checkpoint."
}
if ([string]::IsNullOrWhiteSpace($ExpectedSha256)) {
  $record.result = "blocked_missing_expected_sha256"
  $record.failure_category = "missing_expected_sha256"
}

if (!$Execute -or $record.failure_category) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 20
  $record | ConvertTo-Json -Depth 20
  if ($record.failure_category) { exit 1 }
  exit 0
}

$ssmExecutionTimeoutSeconds = [Math]::Max(600, $MaxEc2RuntimeMinutes * 60)
$remoteScript = @"
python3 - <<'PY'
import datetime, hashlib, json, os, shutil, subprocess, tempfile, traceback

SOURCE_S3_URI = "$SourceS3Uri"
REMOTE_MODEL_PATH = "$remoteModelPath"
EXPECTED_SHA256 = "$($ExpectedSha256.ToLowerInvariant())"

result = {
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_s3_uri": SOURCE_S3_URI,
    "remote_model_path": REMOTE_MODEL_PATH,
    "download_attempted": False,
    "sha256_verified": False,
    "errors": []
}

def run(cmd, timeout=1800, check=False):
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError("command failed rc=%s: %s\nSTDOUT=%s\nSTDERR=%s" % (p.returncode, " ".join(cmd), p.stdout[-1000:], p.stderr[-1000:]))
    return {"rc": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

try:
    if not SOURCE_S3_URI.startswith("s3://"):
        raise RuntimeError("SourceS3Uri must be an s3:// URI.")
    os.makedirs(os.path.dirname(REMOTE_MODEL_PATH), exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix="codex_model_install_")
    tmp_path = os.path.join(tmp_dir, os.path.basename(REMOTE_MODEL_PATH))
    result["download_attempted"] = True
    download = run(["aws", "s3", "cp", SOURCE_S3_URI, tmp_path, "--only-show-errors"], check=True)
    actual = sha256_file(tmp_path).lower()
    result["download_rc"] = download["rc"]
    result["observed_sha256"] = actual
    result["expected_sha256"] = EXPECTED_SHA256
    if actual != EXPECTED_SHA256:
        raise RuntimeError("model sha256 mismatch: expected %s observed %s" % (EXPECTED_SHA256, actual))
    shutil.move(tmp_path, REMOTE_MODEL_PATH)
    os.chmod(REMOTE_MODEL_PATH, 0o644)
    result["sha256_verified"] = sha256_file(REMOTE_MODEL_PATH).lower() == EXPECTED_SHA256
    result["size_bytes"] = os.path.getsize(REMOTE_MODEL_PATH)
    result["result"] = "install_model_hash_verified" if result["sha256_verified"] else "install_model_hash_failed_after_move"
except Exception as exc:
    result["errors"].append(str(exc))
    result["traceback_tail"] = traceback.format_exc()[-4000:]
finally:
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass

print(json.dumps(result, sort_keys=True))
PY
"@

try {
  $record.start_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($record.start_state -ne "running") {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
      $startOutput = @(aws ec2 start-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
      $record.start_exit_code = $LASTEXITCODE
    } finally {
      $ErrorActionPreference = $previousErrorActionPreference
    }
    $startText = (($startOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
    $record.start_output_tail = $(if ($startText.Length -gt 2000) { $startText.Substring($startText.Length - 2000) } else { $startText })
    if ($record.start_exit_code -ne 0) {
      $record.failure_category = Get-EC2StartFailureCategory -ExitCode $record.start_exit_code -OutputText $startText
      $record.result = "model_install_start_failed"
      throw "EC2 start-instances failed with exit code $($record.start_exit_code). $startText"
    }
    $record.ec2_started = $true
    $null = Wait-InstanceState -DesiredState "running" -MaxAttempts 120 -SleepSeconds 5
  }
  for ($i = 1; $i -le 90; $i++) {
    $ping = (aws ssm describe-instance-information --region $Region --filters "Key=InstanceIds,Values=$InstanceId" --query "InstanceInformationList[0].PingStatus" --output text 2>$null).Trim()
    if ($ping -eq "Online") { $record.ssm_available = $true; break }
    Start-Sleep -Seconds 5
  }
  if (!$record.ssm_available) { throw "SSM did not become Online for $InstanceId." }

  $payload = @{
    DocumentName = "AWS-RunShellScript"
    InstanceIds = @($InstanceId)
    TimeoutSeconds = $ssmExecutionTimeoutSeconds
    Parameters = @{ commands = @($remoteScript); executionTimeout = @([string]$ssmExecutionTimeoutSeconds) }
  }
  $payloadPath = Join-Path $env:TEMP "codex_model_install_payload_$stamp.json"
  Write-JsonNoBom -Value $payload -Path $payloadPath -Depth 10
  $record.command_id = (aws ssm send-command --region $Region --cli-input-json "file://$payloadPath" --query "Command.CommandId" --output text).Trim()
  $maxPolls = [Math]::Max(1, [int][Math]::Ceiling($ssmExecutionTimeoutSeconds / 5))
  for ($i = 1; $i -le $maxPolls; $i++) {
    $record.command_status = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "Status" --output text 2>$null).Trim()
    if (@("Success","Failed","Cancelled","TimedOut","Cancelling").Contains($record.command_status)) { break }
    Start-Sleep -Seconds 5
  }
  if ($record.command_status -notin @("Success","Failed","Cancelled","TimedOut","Cancelling")) {
    $record.command_status = "LocalTimeout"
    try { aws ssm cancel-command --region $Region --command-id $record.command_id --instance-ids $InstanceId --output json | Out-Null } catch {}
  }
  $stdout = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "StandardOutputContent" --output text
  $stderr = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "StandardErrorContent" --output text
  $stderrText = [string]$stderr
  $record.stderr_tail = $(if ($stderrText.Length -gt 2000) { $stderrText.Substring($stderrText.Length - 2000) } else { $stderrText })
  $stdoutText = ([string]$stdout).Trim()
  if (![string]::IsNullOrWhiteSpace($stdoutText)) {
    $record.remote_result = $stdoutText | ConvertFrom-Json
  }
} catch {
  $record.errors += $_.Exception.Message
} finally {
  try {
    $shouldStopInstance = ($record.ec2_started -or $record.start_state -eq "running" -or $record.command_status -ne "not_started")
    if ($shouldStopInstance) {
      $previousErrorActionPreference = $ErrorActionPreference
      $ErrorActionPreference = "Continue"
      try {
        $stopOutput = @(aws ec2 stop-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
        $record.stop_exit_code = $LASTEXITCODE
      } finally {
        $ErrorActionPreference = $previousErrorActionPreference
      }
      $stopText = (($stopOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
      $record.stop_output_tail = $(if ($stopText.Length -gt 2000) { $stopText.Substring($stopText.Length - 2000) } else { $stopText })
      if ($record.stop_exit_code -ne 0) {
        $record.stop_failure_category = Get-EC2StopFailureCategory -ExitCode $record.stop_exit_code -OutputText $stopText
        throw "EC2 stop-instances failed with exit code $($record.stop_exit_code). $stopText"
      }
      $null = Wait-InstanceState -DesiredState "stopped" -MaxAttempts 120 -SleepSeconds 5
      $record.final_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    } else {
      $record.final_state = $record.start_state
    }
  } catch {
    if ([string]::IsNullOrWhiteSpace([string]$record.stop_failure_category)) {
      $record.stop_failure_category = "ec2_stop_or_final_state_verification_failed"
    }
    $record.errors += "Stop/final-state verification failed: $($_.Exception.Message)"
  }
}

if ($record.remote_result -and $record.remote_result.sha256_verified -eq $true -and $record.command_status -eq "Success" -and $record.final_state -eq "stopped" -and $record.errors.Count -eq 0) {
  $record.result = "install_model_hash_verified"
  $record.failure_category = $null
} else {
  if ($record.result -ne "model_install_start_failed") {
    $record.result = "install_model_incomplete"
  }
  if ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) {
    $record.failure_category = "install_model_incomplete"
  }
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
$record | ConvertTo-Json -Depth 30
if ($record.result -ne "install_model_hash_verified") { exit 2 }
