<#
.SYNOPSIS
Installs a hash-bound set of ComfyUI model assets from S3 in one EC2 window.

.DESCRIPTION
Dry-run by default. With -Execute, validates a 1-8 asset manifest, starts the
approved stopped instance once, installs or reuses every exact asset through
one SSM command, verifies hashes and sizes, and stops the instance in finally.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$AssetManifestFile,
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$RemoteComfyRoot = "/home/ubuntu/ComfyUI",
  [string]$OutFile = "",
  [string]$RuntimeWindowId = "",
  [string]$EmergencyStopEvidencePath = "",
  [string]$DeployBundleS3Uri = "",
  [string]$DeployBundleSha256 = "",
  [string]$WatchdogEvidenceOutFile = "",
  [int]$MaxEc2RuntimeMinutes = 90,
  [switch]$AllowWatchdogOsShutdownFallback,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
$encoding = New-Object System.Text.UTF8Encoding($false)
$startFailureClassifier = Join-Path $PSScriptRoot "EC2StartFailureClassification.ps1"
. $startFailureClassifier
$stopFailureClassifier = Join-Path $PSScriptRoot "EC2StopFailureClassification.ps1"
. $stopFailureClassifier
$runtimeSafetyGate = Join-Path $PSScriptRoot "EC2RuntimeWindowSafetyGate.ps1"
. $runtimeSafetyGate

function Write-JsonAtomic {
  param([Parameter(Mandatory=$true)][object]$Value, [Parameter(Mandatory=$true)][string]$Path, [int]$Depth = 30)
  $directory = Split-Path -Parent $Path
  if (![string]::IsNullOrWhiteSpace($directory)) { $null = New-Item -ItemType Directory -Force -Path $directory }
  $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
  try {
    [System.IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
  } finally {
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
  }
}

function Wait-InstanceState {
  param([Parameter(Mandatory=$true)][string]$DesiredState, [int]$MaxAttempts = 120, [int]$SleepSeconds = 5)
  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    if ($state -eq $DesiredState) { return $state }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Instance $InstanceId did not reach state $DesiredState."
}

function ConvertTo-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path, [switch]$MustExist)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
  $resolved = if ([System.IO.Path]::IsPathRooted($Path)) {
    [System.IO.Path]::GetFullPath($Path)
  } else {
    [System.IO.Path]::GetFullPath((Join-Path $root $Path.Replace("/", "\")))
  }
  if (!$resolved.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "AssetManifestFile must remain inside ProjectRoot."
  }
  if ($MustExist -and !(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Asset manifest is missing: $resolved" }
  return $resolved
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$AssetManifestFile = ConvertTo-ProjectPath -Path $AssetManifestFile -MustExist
$manifest = Get-Content -Raw -LiteralPath $AssetManifestFile | ConvertFrom-Json
$assets = @($manifest.assets)
$validationErrors = New-Object System.Collections.ArrayList
if ([string]$manifest.schema_version -cne "1.0") { [void]$validationErrors.Add("Unsupported asset manifest schema_version.") }
if ([string]::IsNullOrWhiteSpace([string]$manifest.lane_id)) { [void]$validationErrors.Add("Asset manifest lane_id is missing.") }
if ($assets.Count -lt 1 -or $assets.Count -gt 8) { [void]$validationErrors.Add("Asset manifest must contain 1-8 assets.") }

$validatedAssets = New-Object System.Collections.ArrayList
$seenRemotePaths = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
foreach ($asset in $assets) {
  $source = [string]$asset.source_s3_uri
  $subdir = ([string]$asset.model_subdir).Replace("\", "/").Trim("/")
  $filename = [string]$asset.filename
  $sha256 = ([string]$asset.sha256).ToLowerInvariant()
  $sizeBytes = [long]$asset.size_bytes
  if ($source -notmatch '^s3://[^/]+/.+') { [void]$validationErrors.Add("Invalid source_s3_uri for '$filename'."); continue }
  if ($subdir -notmatch '^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$') { [void]$validationErrors.Add("Invalid model_subdir for '$filename'."); continue }
  if ($filename -notmatch '^[A-Za-z0-9][A-Za-z0-9_.+-]{0,254}$') { [void]$validationErrors.Add("Invalid filename '$filename'."); continue }
  if ($sha256 -notmatch '^[0-9a-f]{64}$') { [void]$validationErrors.Add("Invalid SHA-256 for '$filename'."); continue }
  if ($sizeBytes -lt 1) { [void]$validationErrors.Add("Invalid size_bytes for '$filename'."); continue }
  $remotePath = "$RemoteComfyRoot/models/$subdir/$filename"
  if (!$seenRemotePaths.Add($remotePath)) { [void]$validationErrors.Add("Duplicate remote path '$remotePath'."); continue }
  [void]$validatedAssets.Add([ordered]@{
    source_s3_uri = $source
    model_subdir = $subdir
    filename = $filename
    sha256 = $sha256
    size_bytes = $sizeBytes
    remote_path = $remotePath
  })
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($RuntimeWindowId)) { $RuntimeWindowId = "rw-flux-model-set-$stamp" }
if ($RuntimeWindowId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') { [void]$validationErrors.Add("RuntimeWindowId is invalid.") }
if ($Execute -and $DeployBundleS3Uri -notmatch '^s3://[^/]+/.+') { [void]$validationErrors.Add("Execute requires a concrete deploy-bundle S3 URI for runtime-window marking.") }
if ($Execute -and $DeployBundleSha256 -notmatch '^[0-9a-fA-F]{64}$') { [void]$validationErrors.Add("Execute requires a 64-character deploy-bundle SHA-256.") }
$emergencyStopGate = Get-EmergencyStopScheduleStatus -Path $EmergencyStopEvidencePath -ExpectedWindowId $RuntimeWindowId -ExpectedInstanceId $InstanceId -ExpectedRegion $Region
if ($Execute -and !$emergencyStopGate.verified) { [void]$validationErrors.Add("Execute requires a verified same-window emergency-stop schedule.") }
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "runtime_artifacts\ec2_model_install\MODEL_SET_INSTALL_$stamp.json"
} elseif (![System.IO.Path]::IsPathRooted($OutFile)) {
  $OutFile = Join-Path $ProjectRoot $OutFile
}
if ([string]::IsNullOrWhiteSpace($WatchdogEvidenceOutFile)) {
  $WatchdogEvidenceOutFile = Join-Path (Split-Path -Parent $OutFile) "MODEL_SET_INSTALL_WATCHDOG_$stamp.json"
} elseif (![System.IO.Path]::IsPathRooted($WatchdogEvidenceOutFile)) {
  $WatchdogEvidenceOutFile = Join-Path $ProjectRoot $WatchdogEvidenceOutFile
}
$record = [ordered]@{
  schema_version = "1.0"
  evidence_id = "EC2-MODEL-SET-INSTALL-$stamp"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "install_ec2_model_set_from_s3"
  lane_id = [string]$manifest.lane_id
  instance_id = $InstanceId
  region = $Region
  runtime_window_id = $RuntimeWindowId
  emergency_stop_gate = $emergencyStopGate
  deploy_bundle_s3_uri = $DeployBundleS3Uri
  deploy_bundle_sha256 = $(if ([string]::IsNullOrWhiteSpace($DeployBundleSha256)) { $null } else { $DeployBundleSha256.ToLowerInvariant() })
  asset_manifest_file = $AssetManifestFile.Substring($ProjectRoot.TrimEnd("\").Length).TrimStart("\").Replace("\", "/")
  asset_manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $AssetManifestFile).Hash.ToLowerInvariant()
  asset_count = $validatedAssets.Count
  assets = @($validatedAssets)
  execute = [bool]$Execute
  start_state = $null
  ec2_started = $false
  ssm_available = $false
  command_id = $null
  command_status = "not_started"
  remote_result = $null
  marker_activation = $null
  marker_completion = $null
  watchdog = $null
  final_state = $null
  generation_executed = $false
  validation_errors = @($validationErrors)
  errors = @()
  result = $(if ($validationErrors.Count -eq 0) { $(if ($Execute) { "ready_for_model_set_install_execute" } else { "dry_run_model_set_install_plan" }) } else { "blocked_pre_ec2_validation" })
  failure_category = $(if ($validationErrors.Count -eq 0) { $null } else { "pre_ec2_validation_failed" })
}

if (!$Execute -or $validationErrors.Count -gt 0) {
  Write-JsonAtomic -Value $record -Path $OutFile
  $record | ConvertTo-Json -Depth 30
  if ($validationErrors.Count -gt 0) { exit 1 }
  exit 0
}

$payloadJson = ConvertTo-Json -InputObject @($validatedAssets) -Depth 10 -Compress
$payloadBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payloadJson))
$ssmExecutionTimeoutSeconds = [Math]::Max(900, $MaxEc2RuntimeMinutes * 60)
$remoteScript = @"
python3 - <<'PY'
import base64, datetime, hashlib, json, os, shutil, subprocess, tempfile, traceback

ASSETS = json.loads(base64.b64decode("$payloadBase64").decode("utf-8"))
result = {"timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "assets": [], "errors": []}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

try:
    for asset in ASSETS:
        row = {"source_s3_uri": asset["source_s3_uri"], "remote_path": asset["remote_path"], "expected_sha256": asset["sha256"], "expected_size_bytes": asset["size_bytes"], "reused": False, "downloaded": False, "sha256_verified": False, "size_verified": False, "errors": []}
        result["assets"].append(row)
        destination = asset["remote_path"]
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            if os.path.isfile(destination) and os.path.getsize(destination) == asset["size_bytes"] and sha256_file(destination) == asset["sha256"]:
                row["reused"] = True
            else:
                temp_dir = tempfile.mkdtemp(prefix="codex_model_set_install_")
                try:
                    temp_path = os.path.join(temp_dir, asset["filename"])
                    completed = subprocess.run(["aws", "s3", "cp", asset["source_s3_uri"], temp_path, "--only-show-errors"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=$ssmExecutionTimeoutSeconds)
                    if completed.returncode != 0:
                        raise RuntimeError("aws s3 cp failed rc=%s stderr=%s" % (completed.returncode, completed.stderr[-2000:]))
                    if os.path.getsize(temp_path) != asset["size_bytes"]:
                        raise RuntimeError("downloaded size mismatch")
                    if sha256_file(temp_path) != asset["sha256"]:
                        raise RuntimeError("downloaded SHA-256 mismatch")
                    os.replace(temp_path, destination)
                    os.chmod(destination, 0o644)
                    row["downloaded"] = True
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            row["observed_size_bytes"] = os.path.getsize(destination)
            row["observed_sha256"] = sha256_file(destination)
            row["size_verified"] = row["observed_size_bytes"] == asset["size_bytes"]
            row["sha256_verified"] = row["observed_sha256"] == asset["sha256"]
            if not row["size_verified"] or not row["sha256_verified"]:
                raise RuntimeError("installed asset verification failed")
            row["result"] = "exact_asset_reused" if row["reused"] else "asset_downloaded_and_verified"
        except Exception as exc:
            row["errors"].append(str(exc))
            row["result"] = "asset_install_failed"
            raise
    result["result"] = "model_set_install_hash_verified"
except Exception as exc:
    result["errors"].append(str(exc))
    result["traceback_tail"] = traceback.format_exc()[-4000:]
    result["result"] = "model_set_install_failed"

print(json.dumps(result, sort_keys=True))
PY
"@.Replace("`r`n", "`n").Replace("`r", "`n")

try {
  $markerHelper = Join-Path $PSScriptRoot "Set-EC2RuntimeWindowMarker.ps1"
  $record.marker_activation = & $markerHelper -Action Activate -ProjectRoot $ProjectRoot -WindowId $RuntimeWindowId -LaneId ([string]$manifest.lane_id) -Purpose "hash_bound_model_set_install" -DeployBundleS3Uri $DeployBundleS3Uri -DeployBundleSha256 $DeployBundleSha256 -EmergencyStopEvidencePath $EmergencyStopEvidencePath -MaxRuntimeMinutes $MaxEc2RuntimeMinutes -InstanceId $InstanceId -Region $Region | ConvertFrom-Json
  $record.start_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($record.start_state -ne "stopped") { throw "Model-set installer requires the approved instance to begin stopped; observed '$($record.start_state)'." }
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $startOutput = @(aws ec2 start-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
    $startExitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($startExitCode -ne 0) {
    $startText = (($startOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
    $record.failure_category = Get-EC2StartFailureCategory -ExitCode $startExitCode -OutputText $startText
    throw "EC2 start-instances failed with exit code $startExitCode. $startText"
  }
  $record.ec2_started = $true
  $null = Wait-InstanceState -DesiredState "running"
  for ($i = 1; $i -le 90; $i++) {
    $ping = (aws ssm describe-instance-information --region $Region --filters "Key=InstanceIds,Values=$InstanceId" --query "InstanceInformationList[0].PingStatus" --output text 2>$null).Trim()
    if ($ping -eq "Online") { $record.ssm_available = $true; break }
    Start-Sleep -Seconds 5
  }
  if (!$record.ssm_available) { throw "SSM did not become Online for $InstanceId." }

  $watchdogHelper = Join-Path $PSScriptRoot "Start-EC2InstanceStopWatchdog.ps1"
  $watchdogArgs = @{
    InstanceId=$InstanceId; Region=$Region; RuntimeWindowId=$RuntimeWindowId; StopAfterMinutes=$MaxEc2RuntimeMinutes;
    OutFile=$WatchdogEvidenceOutFile; Execute=$true
  }
  if ($AllowWatchdogOsShutdownFallback) { $watchdogArgs.AllowOsShutdownFallback = $true }
  $record.watchdog = & $watchdogHelper @watchdogArgs | ConvertFrom-Json
  if ([string]$record.watchdog.result -ne "instance_stop_watchdog_started_and_capability_verified" -or ![bool]$record.watchdog.stop_capability_verified) {
    throw "Instance stop watchdog did not verify before model installation."
  }

  $ssmPayload = @{ DocumentName="AWS-RunShellScript"; InstanceIds=@($InstanceId); TimeoutSeconds=$ssmExecutionTimeoutSeconds; Parameters=@{ commands=@($remoteScript); executionTimeout=@([string]$ssmExecutionTimeoutSeconds) } }
  $payloadPath = Join-Path $env:TEMP "codex_model_set_install_$stamp.json"
  Write-JsonAtomic -Value $ssmPayload -Path $payloadPath -Depth 10
  $record.command_id = (aws ssm send-command --region $Region --cli-input-json "file://$payloadPath" --query "Command.CommandId" --output text).Trim()
  for ($i = 1; $i -le [Math]::Ceiling($ssmExecutionTimeoutSeconds / 5); $i++) {
    $record.command_status = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "Status" --output text 2>$null).Trim()
    if ($record.command_status -in @("Success","Failed","Cancelled","TimedOut","Cancelling")) { break }
    Start-Sleep -Seconds 5
  }
  $stdout = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "StandardOutputContent" --output text).Trim()
  $stderr = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "StandardErrorContent" --output text).Trim()
  if (![string]::IsNullOrWhiteSpace($stdout)) { $record.remote_result = $stdout | ConvertFrom-Json }
  if ($record.command_status -ne "Success" -or [string]$record.remote_result.result -ne "model_set_install_hash_verified") {
    throw "Remote model-set install failed with status '$($record.command_status)': $stderr"
  }
  $record.result = "model_set_install_hash_verified"
} catch {
  $record.errors += $_.Exception.Message
  if ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) { $record.failure_category = "model_set_install_failed" }
  $record.result = "model_set_install_failed"
} finally {
  Remove-Item -LiteralPath (Join-Path $env:TEMP "codex_model_set_install_$stamp.json") -Force -ErrorAction SilentlyContinue
  if ($record.ec2_started) {
    try {
      $previousErrorActionPreference = $ErrorActionPreference
      $ErrorActionPreference = "Continue"
      try {
        $stopOutput = @(aws ec2 stop-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
        $stopExitCode = $LASTEXITCODE
      } finally {
        $ErrorActionPreference = $previousErrorActionPreference
      }
      if ($stopExitCode -ne 0) {
        $stopText = (($stopOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
        $record.failure_category = Get-EC2StopFailureCategory -ExitCode $stopExitCode -OutputText $stopText
        throw "EC2 stop-instances failed with exit code $stopExitCode. $stopText"
      }
      $null = Wait-InstanceState -DesiredState "stopped"
    } catch {
      $record.errors += "Stop/final-state verification failed: $($_.Exception.Message)"
      $record.result = "model_set_install_stop_verification_failed"
    }
  }
  $record.final_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($record.final_state -ne "stopped") {
    $record.errors += "Final EC2 state is '$($record.final_state)', expected 'stopped'."
    $record.result = "model_set_install_stop_verification_failed"
  } elseif ($null -ne $record.marker_activation) {
    try {
      $markerHelper = Join-Path $PSScriptRoot "Set-EC2RuntimeWindowMarker.ps1"
      $record.marker_completion = & $markerHelper -Action Complete -ProjectRoot $ProjectRoot -WindowId $RuntimeWindowId -FinalInstanceState "stopped" -CompletionResult ([string]$record.result) -CompletionEvidencePath $OutFile | ConvertFrom-Json
    } catch {
      $record.errors += "Runtime-window marker completion failed: $($_.Exception.Message)"
      $record.result = "model_set_install_marker_completion_failed"
    }
  }
  Write-JsonAtomic -Value $record -Path $OutFile
}

$record | ConvertTo-Json -Depth 30
if ($record.result -ne "model_set_install_hash_verified") { exit 1 }
