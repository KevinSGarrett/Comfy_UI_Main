<#
.SYNOPSIS
Executes one hash-bound 1-5 unit ComfyUI batch inside a single EC2 runtime window.

.DESCRIPTION
Dry-run by default. With -Execute, this coordinator exclusively owns runtime
marker activation, one EC2 start, one verified watchdog, one static proof,
sequential compatible smoke units, artifact pullback, one final stop, marker
completion, and post-stop EBS right-sizing readiness. Child helpers run in
caller-managed mode and cannot start or stop the instance.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$WorkOrderFile,
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$AuthGateFile = "",
  [string]$ReadinessFile = "",
  [string]$RuntimeWindowId = "",
  [string]$EmergencyStopEvidencePath = "",
  [string]$WatchdogEvidenceOutFile = "",
  [string[]]$PreservedGitExcludePath = @(),
  [string]$OutDirectory = "",
  [string]$S3Bucket = "",
  [string]$S3Prefix = "comfy-ui-main/batched-runtime",
  [int]$ComfyPort = 8192,
  [int]$UnitTimeoutSeconds = 900,
  [switch]$AllowWatchdogOsShutdownFallback,
  [switch]$SkipGitLfsPull,
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
  param([Parameter(Mandatory=$true)][object]$Value, [Parameter(Mandatory=$true)][string]$Path, [int]$Depth = 40)
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

function Has-Property {
  param([object]$Object, [Parameter(Mandatory=$true)][string]$Name)
  return ($null -ne $Object -and @($Object.PSObject.Properties.Name) -contains $Name)
}

function Resolve-ContainedProjectFile {
  param([Parameter(Mandatory=$true)][string]$Path, [switch]$MustExist)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
  $resolved = if ([System.IO.Path]::IsPathRooted($Path)) {
    [System.IO.Path]::GetFullPath($Path)
  } else {
    [System.IO.Path]::GetFullPath((Join-Path $root $Path.Replace("/", "\")))
  }
  if (!$resolved.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path must remain inside ProjectRoot: $Path"
  }
  if ($MustExist -and !(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Required file is missing: $resolved" }
  return $resolved
}

function ConvertTo-ProjectRelativePath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
  $full = [System.IO.Path]::GetFullPath($Path)
  return $full.Substring($root.Length).TrimStart("\", "/").Replace("\", "/")
}

function Wait-InstanceState {
  param([Parameter(Mandatory=$true)][string]$DesiredState, [int]$MaxAttempts = 120, [int]$SleepSeconds = 5)
  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    Write-Host "EC2 batch state wait $i/$MaxAttempts desired=$DesiredState observed=$state"
    if ($state -eq $DesiredState) { return $state }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Timed out waiting for EC2 state '$DesiredState'."
}

function Wait-InstanceStatusOk {
  for ($i = 1; $i -le 80; $i++) {
    $status = aws ec2 describe-instance-status --region $Region --instance-ids $InstanceId --include-all-instances --query "InstanceStatuses[0].{system:SystemStatus.Status,instance:InstanceStatus.Status,state:InstanceState.Name}" --output json | ConvertFrom-Json
    if ($status.state -eq "running" -and $status.system -eq "ok" -and $status.instance -eq "ok") { return $true }
    Start-Sleep -Seconds 5
  }
  throw "Timed out waiting for EC2 instance status checks."
}

function Wait-SsmOnline {
  for ($i = 1; $i -le 30; $i++) {
    $ping = (aws ssm describe-instance-information --region $Region --filters "Key=InstanceIds,Values=$InstanceId" --query "InstanceInformationList[0].PingStatus" --output text 2>$null).Trim()
    Write-Host "EC2 batch SSM wait $i/30 ping=$ping"
    if ($ping -eq "Online") { return $true }
    Start-Sleep -Seconds 10
  }
  throw "SSM did not become Online for $InstanceId."
}

function Read-JsonRequired {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "JSON file is missing: $Path" }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Set-WorkOrderField {
  param([Parameter(Mandatory=$true)][object]$WorkOrder, [Parameter(Mandatory=$true)][string]$Name, [object]$Value)
  if (Has-Property -Object $WorkOrder -Name $Name) { $WorkOrder.$Name = $Value }
  else { $WorkOrder | Add-Member -NotePropertyName $Name -NotePropertyValue $Value }
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if (!(Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "ProjectRoot is missing: $ProjectRoot" }
$WorkOrderFile = Resolve-ContainedProjectFile -Path $WorkOrderFile -MustExist
$workOrder = Read-JsonRequired -Path $WorkOrderFile

$validationErrors = New-Object System.Collections.ArrayList
if ([string]$workOrder.schema_version -cne "1.0") { [void]$validationErrors.Add("Unsupported work-order schema_version.") }
if ([string]$workOrder.status -cne "READY_WORK_WAITING_FOR_EC2") { [void]$validationErrors.Add("Work order is not READY_WORK_WAITING_FOR_EC2.") }
if ([string]$workOrder.work_order_id -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') { [void]$validationErrors.Add("Work-order ID is invalid.") }
try {
  if ([datetimeoffset]::Parse([string]$workOrder.expires_at) -le [datetimeoffset]::UtcNow) { [void]$validationErrors.Add("Work order is expired.") }
} catch { [void]$validationErrors.Add("Work-order expires_at is invalid.") }
$laneId = [string]$workOrder.lane_id
$deployBundleS3Uri = [string]$workOrder.deploy_bundle_s3_uri
$deployBundleSha256 = ([string]$workOrder.deploy_bundle_sha256).ToLowerInvariant()
$maxRuntimeMinutes = [int]$workOrder.max_runtime_minutes
if ([string]::IsNullOrWhiteSpace($laneId)) { [void]$validationErrors.Add("Work-order lane_id is missing.") }
if ($deployBundleS3Uri -notmatch '^s3://[^/]+/.+') { [void]$validationErrors.Add("Work-order deploy bundle URI is invalid.") }
if ($deployBundleSha256 -notmatch '^[0-9a-f]{64}$') { [void]$validationErrors.Add("Work-order deploy bundle SHA-256 is invalid.") }
if ($maxRuntimeMinutes -lt 10 -or $maxRuntimeMinutes -gt 120) { [void]$validationErrors.Add("Work-order max_runtime_minutes is outside 10-120.") }
$unitRows = @($workOrder.units)
if ($unitRows.Count -lt 1 -or $unitRows.Count -gt 5 -or [int]$workOrder.unit_count -ne $unitRows.Count) { [void]$validationErrors.Add("Work order must contain exactly 1-5 declared units.") }

$validatedUnits = New-Object System.Collections.ArrayList
$seenRunIds = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($unitRow in $unitRows) {
  try {
    $manifestPath = Resolve-ContainedProjectFile -Path ([string]$unitRow.manifest_path) -MustExist
    $actualManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
    if ($actualManifestHash -cne ([string]$unitRow.manifest_sha256).ToLowerInvariant()) { throw "Unit manifest hash mismatch." }
    $manifest = Read-JsonRequired -Path $manifestPath
    if ([string]$manifest.lane_id -cne $laneId -or [string]$unitRow.lane_id -cne $laneId) { throw "Unit lane does not match work-order lane." }
    if ([string]$manifest.result -cne "pass_local_only" -or ![bool]$manifest.local_only) { throw "Unit is not a validated local-only run package." }
    if ([bool]$manifest.aws_contacted -or [bool]$manifest.ec2_started -or [bool]$manifest.generation_executed) { throw "Unit violates local-only execution boundaries." }
    $runId = [string]$manifest.run_id
    if ([string]::IsNullOrWhiteSpace($runId) -or !$seenRunIds.Add($runId)) { throw "Unit run_id is missing or duplicated." }
    $promptRows = @($manifest.generated_files | Where-Object { [System.IO.Path]::GetFileName([string]$_.path) -ieq "prompt_request.json" })
    if ($promptRows.Count -ne 1) { throw "Unit must declare exactly one generated prompt_request.json." }
    $promptPath = Resolve-ContainedProjectFile -Path ([string]$promptRows[0].path) -MustExist
    $promptHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $promptPath).Hash.ToLowerInvariant()
    if ($promptHash -cne ([string]$promptRows[0].sha256).ToLowerInvariant() -or $promptHash -cne ([string]$manifest.prompt_request.sha256).ToLowerInvariant()) { throw "Unit prompt-request hash mismatch." }
    $prompt = Read-JsonRequired -Path $promptPath
    if ($null -eq $prompt.prompt -or @($prompt.prompt.PSObject.Properties).Count -eq 0) { throw "Unit prompt request has no prompt graph." }
    [void]$validatedUnits.Add([pscustomobject][ordered]@{
      index = $validatedUnits.Count + 1
      run_id = $runId
      manifest_path = $manifestPath
      manifest_sha256 = $actualManifestHash
      prompt_path = $promptPath
      prompt_sha256 = $promptHash
    })
  } catch {
    [void]$validationErrors.Add("Unit '$([string]$unitRow.manifest_path)' is invalid: $($_.Exception.Message)")
  }
}

$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
if ([string]::IsNullOrWhiteSpace($AuthGateFile)) {
  $AuthGateFile = @(Get-ChildItem -LiteralPath $runtimeReadinessDir -Filter "*AWS_AUTH_GATE*.json" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}
if ([string]::IsNullOrWhiteSpace($ReadinessFile)) {
  $ReadinessFile = @(Get-ChildItem -LiteralPath $runtimeReadinessDir -Filter "*LANE_RUNTIME_READINESS*.json" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}
$authGate = $null
try { $authGate = Read-JsonRequired -Path $AuthGateFile } catch { [void]$validationErrors.Add("AWS auth gate is unavailable: $($_.Exception.Message)") }
if ($null -ne $authGate) {
  if ([string]$authGate.account_actual -cne "029530099913" -or ![bool]$authGate.safe_to_start_ec2 -or ![bool]$authGate.ec2_work_allowed) { [void]$validationErrors.Add("AWS auth gate does not authorize the approved account and EC2 scope.") }
}
$readinessGate = Get-EC2LaneReadinessStatus -Path $ReadinessFile -ExpectedLaneId $laneId
if (!$readinessGate.lane_match -or !$readinessGate.ready_for_ec2_static_proof) { [void]$validationErrors.Add("Lane readiness does not authorize static proof for this lane.") }
$gitGate = Get-LocalGitCheckpointGate -ProjectRoot $ProjectRoot -PreservedExcludePath $PreservedGitExcludePath
if ([string]$gitGate.result -ne "pass") { [void]$validationErrors.Add("Local Git checkpoint gate did not pass.") }

if ([string]::IsNullOrWhiteSpace($RuntimeWindowId)) { $RuntimeWindowId = "rw-batch-$([string]$workOrder.work_order_id)" }
if ($RuntimeWindowId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') { [void]$validationErrors.Add("RuntimeWindowId is invalid.") }
$emergencyStopGate = Get-EmergencyStopScheduleStatus -Path $EmergencyStopEvidencePath -ExpectedWindowId $RuntimeWindowId -ExpectedInstanceId $InstanceId -ExpectedRegion $Region
if ($Execute -and !$emergencyStopGate.verified) { [void]$validationErrors.Add("Same-window emergency-stop schedule is not verified.") }

if ([string]::IsNullOrWhiteSpace($OutDirectory)) {
  $OutDirectory = Join-Path $ProjectRoot "runtime_artifacts\batched_runtime\$([string]$workOrder.work_order_id)"
}
$OutDirectory = [System.IO.Path]::GetFullPath($OutDirectory)
$projectPrefix = $ProjectRoot.TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
if (!$OutDirectory.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw "OutDirectory must remain inside ProjectRoot." }
$null = New-Item -ItemType Directory -Force -Path $OutDirectory
$aggregateOutFile = Join-Path $OutDirectory "BATCH_RUNTIME_EXECUTION.json"
if ([string]::IsNullOrWhiteSpace($WatchdogEvidenceOutFile)) { $WatchdogEvidenceOutFile = Join-Path $OutDirectory "INSTANCE_WATCHDOG.json" }

$record = [ordered]@{
  schema_version = "1.0"
  created_at = [datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  operation = "invoke_ec2_batched_runtime_window"
  execute = [bool]$Execute
  result = $(if ($validationErrors.Count -eq 0) { "batch_runtime_ready_local_only" } else { "blocked_before_ec2_start" })
  failure_category = $(if ($validationErrors.Count -eq 0) { $null } else { "batch_preflight_failed" })
  work_order_file = ConvertTo-ProjectRelativePath $WorkOrderFile
  work_order_id = [string]$workOrder.work_order_id
  lane_id = $laneId
  unit_count = $validatedUnits.Count
  runtime_window_id = $RuntimeWindowId
  instance_id = $InstanceId
  region = $Region
  deploy_bundle_s3_uri = $deployBundleS3Uri
  deploy_bundle_sha256 = $deployBundleSha256
  max_runtime_minutes = $maxRuntimeMinutes
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  auth_gate_file = ConvertTo-ProjectRelativePath $AuthGateFile
  readiness_gate = $readinessGate
  emergency_stop_gate = $emergencyStopGate
  local_git_checkpoint_gate = $gitGate
  validation_errors = @($validationErrors)
  units = @($validatedUnits | ForEach-Object { [ordered]@{ index=$_.index; run_id=$_.run_id; manifest_path=(ConvertTo-ProjectRelativePath $_.manifest_path); manifest_sha256=$_.manifest_sha256; prompt_sha256=$_.prompt_sha256; result="pending"; smoke_record=$null; pullback_status=$null } })
  marker_activation = $null
  marker_completion = $null
  capacity_backoff = $null
  watchdog = $null
  identity_gate = $null
  start_state = $null
  start_exit_code = $null
  start_output_tail = $null
  static_proof = $null
  stop_exit_code = $null
  stop_output_tail = $null
  final_state = $null
  ebs_right_sizing_readiness = $null
  errors = @()
}

Write-JsonAtomic -Value $record -Path $aggregateOutFile
if ($validationErrors.Count -gt 0) {
  $record | ConvertTo-Json -Depth 40
  exit 2
}
if (!$Execute) {
  $record | ConvertTo-Json -Depth 40
  return
}

$markerActivated = $false
$staticProofFile = Join-Path $OutDirectory "EC2_STATIC_PROOF.json"
$batchReadinessFile = Join-Path $OutDirectory "BATCH_POST_STATIC_READINESS.json"
$firstSuccessfulSmokeFile = $null
Set-WorkOrderField -WorkOrder $workOrder -Name "status" -Value "EXECUTING"
Set-WorkOrderField -WorkOrder $workOrder -Name "execution_started_at" -Value ([datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"))
Set-WorkOrderField -WorkOrder $workOrder -Name "runtime_window_id" -Value $RuntimeWindowId
Set-WorkOrderField -WorkOrder $workOrder -Name "execution_record" -Value (ConvertTo-ProjectRelativePath $aggregateOutFile)
Write-JsonAtomic -Value $workOrder -Path $WorkOrderFile
try {
  $record.aws_contacted = $true
  $identityScript = Join-Path $PSScriptRoot "Test-AwsComfyGpuIdentity.ps1"
  $identityOutput = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $identityScript -ProjectRoot $ProjectRoot -InstanceId $InstanceId -ExpectedAccount "029530099913" -Json 2>&1)
  $identityExitCode = $LASTEXITCODE
  $identityText = (($identityOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
  try { $record.identity_gate = $identityText | ConvertFrom-Json } catch { throw "AWS/EC2 identity check returned invalid JSON." }
  if ($identityExitCode -ne 0 -or ![bool]$record.identity_gate.passed) { throw "AWS/EC2 identity check failed." }

  $record.start_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($record.start_state -ne "stopped") { throw "Batched runtime requires the approved instance to begin stopped; observed $($record.start_state)." }
  $capacityHelper = Join-Path $PSScriptRoot "Set-EC2CapacityBackoffState.ps1"
  $record.capacity_backoff = & $capacityHelper -Action Inspect -ProjectRoot $ProjectRoot | ConvertFrom-Json
  if ([bool]$record.capacity_backoff.active) { throw "EC2 capacity backoff is active until $($record.capacity_backoff.state.not_before)." }

  $markerHelper = Join-Path $PSScriptRoot "Set-EC2RuntimeWindowMarker.ps1"
  $record.marker_activation = & $markerHelper -Action Activate -ProjectRoot $ProjectRoot -WindowId $RuntimeWindowId -LaneId $laneId -Purpose "batched_target_runtime_validation" -DeployBundleS3Uri $deployBundleS3Uri -DeployBundleSha256 $deployBundleSha256 -EmergencyStopEvidencePath $EmergencyStopEvidencePath -MaxRuntimeMinutes $maxRuntimeMinutes -InstanceId $InstanceId -Region $Region | ConvertFrom-Json
  $markerActivated = $true

  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $startOutput = @(aws ec2 start-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
    $record.start_exit_code = $LASTEXITCODE
  } finally { $ErrorActionPreference = $previousErrorActionPreference }
  $startText = (($startOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
  $record.start_output_tail = $(if ($startText.Length -gt 2000) { $startText.Substring($startText.Length - 2000) } else { $startText })
  if ($record.start_exit_code -ne 0) {
    $record.failure_category = Get-EC2StartFailureCategory -ExitCode $record.start_exit_code -OutputText $startText
    if ($record.failure_category -eq "ec2_insufficient_instance_capacity") { $record.capacity_backoff = & $capacityHelper -Action RecordFailure -ProjectRoot $ProjectRoot -RuntimeWorkOrderId ([string]$workOrder.work_order_id) | ConvertFrom-Json }
    throw "EC2 start failed with exit code $($record.start_exit_code)."
  }
  $record.ec2_started = $true
  $record.capacity_backoff = & $capacityHelper -Action Clear -ProjectRoot $ProjectRoot -ClearReason "ec2_start_succeeded" | ConvertFrom-Json
  $null = Wait-InstanceState -DesiredState "running"
  $null = Wait-InstanceStatusOk
  $null = Wait-SsmOnline
  $record.watchdog = Invoke-VerifiedInstanceWatchdog -WatchdogScriptPath (Join-Path $PSScriptRoot "Start-EC2InstanceStopWatchdog.ps1") -InstanceId $InstanceId -Region $Region -RuntimeWindowId $RuntimeWindowId -OutFile $WatchdogEvidenceOutFile -StopAfterMinutes $maxRuntimeMinutes -TrackerId "TRK-W64-BATCH" -ItemId "ITEM-W64-BATCH" -AllowOsShutdownFallback:$AllowWatchdogOsShutdownFallback

  $staticParams = @{
    ProjectRoot=$ProjectRoot; InstanceId=$InstanceId; Region=$Region; LaneId=$laneId; AuthGateFile=$AuthGateFile; ReadinessFile=$ReadinessFile
    RuntimeWindowId=$RuntimeWindowId; EmergencyStopEvidencePath=$EmergencyStopEvidencePath; WatchdogEvidenceOutFile=$WatchdogEvidenceOutFile
    PreservedGitExcludePath=$PreservedGitExcludePath; OutFile=$staticProofFile; DeployBundleS3Uri=$deployBundleS3Uri; DeployBundleSha256=$deployBundleSha256
    MaxEc2RuntimeMinutes=$maxRuntimeMinutes; CallerManagedRuntimeWindow=$true; Execute=$true
  }
  if ($AllowWatchdogOsShutdownFallback) { $staticParams.AllowWatchdogOsShutdownFallback = $true }
  if ($SkipGitLfsPull) { $staticParams.SkipGitLfsPull = $true }
  & (Join-Path $PSScriptRoot "Invoke-EC2LaneStaticProof.ps1") @staticParams | Out-Null
  $staticProof = Read-JsonRequired -Path $staticProofFile
  if ([string]$staticProof.result -ne "ec2_static_proof_recorded" -or ![bool]$staticProof.static_proof_summary.pass -or [string]$staticProof.final_state -ne "running") { throw "Caller-managed EC2 static proof did not pass." }
  $record.static_proof = [ordered]@{ result=$staticProof.result; path=(ConvertTo-ProjectRelativePath $staticProofFile); sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $staticProofFile).Hash.ToLowerInvariant(); final_state=$staticProof.final_state }

  $batchReadiness = [ordered]@{
    schema_version="1.0"; created_at=[datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"); result="ready_for_generation"
    lane_id=$laneId; local_pre_ec2_ready=$true; ready_for_ec2_static_proof=$true; ready_for_generation=$true
    source_static_proof=(ConvertTo-ProjectRelativePath $staticProofFile); source_static_proof_sha256=$record.static_proof.sha256
    runtime_window_id=$RuntimeWindowId; caller_managed_runtime_window=$true
  }
  Write-JsonAtomic -Value $batchReadiness -Path $batchReadinessFile

  for ($i = 0; $i -lt $validatedUnits.Count; $i++) {
    $unit = $validatedUnits[$i]
    $unitDir = Join-Path $OutDirectory ("unit-{0:D2}-{1}" -f $unit.index, $unit.run_id)
    $null = New-Item -ItemType Directory -Force -Path $unitDir
    $smokeOut = Join-Path $unitDir "WORKFLOW_SMOKE.json"
    $runRecord = Join-Path $unitDir "RUN_RECORD.json"
    $requestOut = Join-Path $unitDir "PROMPT_REQUEST.json"
    try {
      $smokeParams = @{
        ProjectRoot=$ProjectRoot; LaneId=$laneId; InstanceId=$InstanceId; Region=$Region; AuthGateFile=$AuthGateFile; StaticProofFile=$staticProofFile
        ReadinessFile=$batchReadinessFile; RuntimeWindowId=$RuntimeWindowId; EmergencyStopEvidencePath=$EmergencyStopEvidencePath; WatchdogEvidenceOutFile=$WatchdogEvidenceOutFile
        PreservedGitExcludePath=$PreservedGitExcludePath; OutFile=$smokeOut; OutRequestFile=$requestOut; RunPackageManifestFile=$unit.manifest_path; RunRecordFile=$runRecord
        S3Bucket=$S3Bucket; S3Prefix=("{0}/{1}/unit-{2:D2}" -f $S3Prefix.Trim('/'), [string]$workOrder.work_order_id, $unit.index)
        DeployBundleS3Uri=$deployBundleS3Uri; DeployBundleSha256=$deployBundleSha256; ComfyPort=$ComfyPort; TimeoutSeconds=$UnitTimeoutSeconds
        MaxEc2RuntimeMinutes=$maxRuntimeMinutes; CallerManagedRuntimeWindow=$true; Execute=$true
      }
      if ($AllowWatchdogOsShutdownFallback) { $smokeParams.AllowWatchdogOsShutdownFallback = $true }
      if ($SkipGitLfsPull) { $smokeParams.SkipGitLfsPull = $true }
      & (Join-Path $PSScriptRoot "Invoke-EC2WorkflowSmokeRun.ps1") @smokeParams | Out-Null
      $smoke = Read-JsonRequired -Path $smokeOut
      if ([string]$smoke.result -ne "workflow_smoke_generation_complete" -or ![bool]$smoke.generation_executed -or [string]$smoke.final_state -ne "running" -or [string]$smoke.local_pullback.status -ne "pullback_record_created") { throw "Smoke unit did not complete generation and pullback inside the shared window." }
      $record.units[$i].result = "pass"
      $record.units[$i].smoke_record = ConvertTo-ProjectRelativePath $smokeOut
      $record.units[$i].pullback_status = [string]$smoke.local_pullback.status
      $record.generation_executed = $true
      if ($null -eq $firstSuccessfulSmokeFile) { $firstSuccessfulSmokeFile = $smokeOut }
      Write-JsonAtomic -Value $record -Path $aggregateOutFile
    } catch {
      $record.units[$i].result = "fail"
      $record.units[$i].smoke_record = $(if (Test-Path -LiteralPath $smokeOut) { ConvertTo-ProjectRelativePath $smokeOut } else { $null })
      throw "Batch unit $($unit.index) failed: $($_.Exception.Message)"
    }
  }
} catch {
  $record.errors += $_.Exception.Message
  if ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) { $record.failure_category = "batch_runtime_execution_failed" }
} finally {
  try {
    $currentState = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    if ($currentState -ne "stopped") {
      $previousErrorActionPreference = $ErrorActionPreference
      $ErrorActionPreference = "Continue"
      try {
        $stopOutput = @(aws ec2 stop-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
        $record.stop_exit_code = $LASTEXITCODE
      } finally { $ErrorActionPreference = $previousErrorActionPreference }
      $stopText = (($stopOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
      $record.stop_output_tail = $(if ($stopText.Length -gt 2000) { $stopText.Substring($stopText.Length - 2000) } else { $stopText })
      if ($record.stop_exit_code -ne 0) { throw "EC2 stop failed [$((Get-EC2StopFailureCategory -ExitCode $record.stop_exit_code -OutputText $stopText))]." }
      $null = Wait-InstanceState -DesiredState "stopped"
    }
    $record.final_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    if ($markerActivated -and $record.final_state -eq "stopped") {
      $record.marker_completion = & (Join-Path $PSScriptRoot "Set-EC2RuntimeWindowMarker.ps1") -Action Complete -ProjectRoot $ProjectRoot -WindowId $RuntimeWindowId -FinalInstanceState "stopped" -CompletionResult $(if ($record.errors.Count -eq 0) { "batched_runtime_complete" } else { "batched_runtime_failed_closed" }) -CompletionEvidencePath $aggregateOutFile | ConvertFrom-Json
    }
  } catch {
    $record.errors += "Batch cleanup failed: $($_.Exception.Message)"
    $record.failure_category = "batch_stop_or_marker_cleanup_failed"
  }
}

if ($null -ne $firstSuccessfulSmokeFile -and $record.final_state -eq "stopped") {
  try {
    $firstSuccessfulSmoke = Read-JsonRequired -Path $firstSuccessfulSmokeFile
    if ($null -eq $firstSuccessfulSmoke.remote_result.root_filesystem) { throw "Successful smoke record has no root_filesystem telemetry." }
    $filesystemEvidenceFile = Join-Path $OutDirectory "EBS_FILESYSTEM_EVIDENCE.json"
    $filesystemEvidence = [ordered]@{
      schema_version="1.0"; created_at=[datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
      result="filesystem_usage_captured_after_completed_runtime_window"; instance_id=$InstanceId; region=$Region; final_state=$record.final_state
      runtime_window_id=$RuntimeWindowId; work_order_id=[string]$workOrder.work_order_id
      source_smoke_record=(ConvertTo-ProjectRelativePath $firstSuccessfulSmokeFile)
      source_smoke_record_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $firstSuccessfulSmokeFile).Hash.ToLowerInvariant()
      root_filesystem=$firstSuccessfulSmoke.remote_result.root_filesystem
      ebs_mutation_authorized=$false
    }
    Write-JsonAtomic -Value $filesystemEvidence -Path $filesystemEvidenceFile
    $ebsOut = Join-Path $OutDirectory "EBS_RIGHT_SIZING_READINESS.json"
    $ebsOutput = & (Join-Path $PSScriptRoot "Test-EC2EbsRightSizingReadiness.ps1") -ProjectRoot $ProjectRoot -InstanceId $InstanceId -Region $Region -FilesystemEvidenceFile $filesystemEvidenceFile -OutFile $ebsOut | ConvertFrom-Json
    $record.ebs_right_sizing_readiness = [ordered]@{ classification=$ebsOutput.classification; path=(ConvertTo-ProjectRelativePath $ebsOut); filesystem_evidence=(ConvertTo-ProjectRelativePath $filesystemEvidenceFile); recommended_target_size_gib=$ebsOutput.recommended_target_size_gib; migration_target_size_gib=$ebsOutput.migration_target_size_gib; mutation_authorized=$false }
  } catch { $record.errors += "Post-stop EBS readiness check failed: $($_.Exception.Message)" }
}

$allUnitsPassed = ($record.units.Count -ge 1 -and @($record.units | Where-Object { [string]$_.result -ne "pass" }).Count -eq 0)
if ($record.errors.Count -eq 0 -and $allUnitsPassed -and $record.final_state -eq "stopped" -and $null -ne $record.marker_completion) {
  $record.result = "batch_runtime_generation_and_pullback_complete"
  $record.failure_category = $null
} else {
  $record.result = "batch_runtime_failed_closed"
  if ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) { $record.failure_category = "batch_runtime_incomplete" }
}
Write-JsonAtomic -Value $record -Path $aggregateOutFile
$completionStatus = if ($record.result -eq "batch_runtime_generation_and_pullback_complete") {
  "COMPLETED"
} elseif ($record.failure_category -eq "ec2_insufficient_instance_capacity") {
  "READY_WORK_WAITING_FOR_EC2"
} else {
  "FAILED_CLOSED"
}
Set-WorkOrderField -WorkOrder $workOrder -Name "status" -Value $completionStatus
Set-WorkOrderField -WorkOrder $workOrder -Name "result" -Value $(if ($completionStatus -eq "READY_WORK_WAITING_FOR_EC2") { "pass_local_only" } else { [string]$record.result })
Set-WorkOrderField -WorkOrder $workOrder -Name "execution_finished_at" -Value ([datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"))
Set-WorkOrderField -WorkOrder $workOrder -Name "final_instance_state" -Value $record.final_state
Set-WorkOrderField -WorkOrder $workOrder -Name "completion_evidence" -Value (ConvertTo-ProjectRelativePath $aggregateOutFile)
Write-JsonAtomic -Value $workOrder -Path $WorkOrderFile
$record | ConvertTo-Json -Depth 40
if ($record.result -ne "batch_runtime_generation_and_pullback_complete") { exit 2 }
