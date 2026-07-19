param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$WorkOrderFile = "",
  [string]$BackoffStateFile = "",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [switch]$IncludeAwsState,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) { $WorkOrderFile = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_dispatch\READY_GPU_WORK.json" }
if ([string]::IsNullOrWhiteSpace($BackoffStateFile)) { $BackoffStateFile = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_dispatch\CAPACITY_BACKOFF_STATE.json" }
$activeMarker = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_windows\ACTIVE_EC2_RUNTIME_WINDOW.json"
$classification = "NO_ELIGIBLE_GPU_WORK"
$workOrder = $null
$backoff = $null
$instanceState = "not_queried"
$now = [datetimeoffset]::UtcNow

if (Test-Path -LiteralPath $WorkOrderFile -PathType Leaf) {
  $workOrder = Get-Content -Raw -LiteralPath $WorkOrderFile | ConvertFrom-Json
  $workOrderStatus = [string]$workOrder.status
  $validReady = (
    $workOrderStatus -ceq "READY_WORK_WAITING_FOR_EC2" -and
    [string]$workOrder.result -ceq "pass_local_only" -and
    [int]$workOrder.unit_count -ge 1 -and [int]$workOrder.unit_count -le 5 -and
    [string]$workOrder.deploy_bundle_s3_uri -match '^s3://[^/]+/.+' -and
    [string]$workOrder.deploy_bundle_sha256 -match '^[0-9a-f]{64}$' -and
    ![bool]$workOrder.mask_truth_consumed -and
    ![bool]$workOrder.authorizes_ec2_start_by_automation
  )
  if ($workOrderStatus -ceq "COMPLETED") {
    $classification = "NO_ELIGIBLE_GPU_WORK"
  } elseif ($workOrderStatus -ceq "EXECUTING") {
    $classification = "GPU_RUNTIME_WINDOW_STARTING"
  } elseif ($workOrderStatus -ceq "FAILED_CLOSED") {
    $classification = "BLOCKED_FAILED_GPU_WORK_ORDER"
  } elseif (!$validReady) {
    $classification = "BLOCKED_INVALID_GPU_WORK_ORDER"
  } elseif ([datetimeoffset]::Parse([string]$workOrder.expires_at) -le $now) {
    $classification = "BLOCKED_STALE_GPU_WORK_ORDER"
  } else {
    $classification = "READY_WORK_WAITING_FOR_EC2"
  }
}

if ($classification -eq "READY_WORK_WAITING_FOR_EC2" -and (Test-Path -LiteralPath $BackoffStateFile -PathType Leaf)) {
  $backoff = Get-Content -Raw -LiteralPath $BackoffStateFile | ConvertFrom-Json
  if ([string]$backoff.runtime_work_order_id -ceq [string]$workOrder.work_order_id -and [datetimeoffset]::Parse([string]$backoff.not_before) -gt $now) {
    $classification = "CAPACITY_BACKOFF_ACTIVE"
  }
}

if ($IncludeAwsState) {
  $previousAwsMaxAttempts = $env:AWS_MAX_ATTEMPTS
  try {
    # This script runs from a frequent safety-monitor task. Bound AWS network
    # retries so a transient endpoint failure cannot occupy the scheduler for
    # most of the 15-minute interval or overlap worker/WSL recovery activity.
    $env:AWS_MAX_ATTEMPTS = "1"
    $instanceState = (& aws ec2 describe-instances --instance-ids $InstanceId --region $Region --query "Reservations[0].Instances[0].State.Name" --output text --cli-connect-timeout 5 --cli-read-timeout 20 --no-cli-pager).Trim()
    $awsExitCode = $LASTEXITCODE
  } finally {
    if ($null -eq $previousAwsMaxAttempts) {
      Remove-Item Env:AWS_MAX_ATTEMPTS -ErrorAction SilentlyContinue
    } else {
      $env:AWS_MAX_ATTEMPTS = $previousAwsMaxAttempts
    }
  }
  if ($awsExitCode -ne 0) { throw "Unable to read the approved EC2 instance state." }
  if ($instanceState -eq "running") {
    if (Test-Path -LiteralPath $activeMarker -PathType Leaf) {
      $classification = "GPU_RUNTIME_WINDOW_ACTIVE"
    } else {
      $classification = "RUNNING_MARKER_UNKNOWN_REVIEW_NEEDED"
    }
  } elseif ($instanceState -ne "stopped" -and $classification -eq "READY_WORK_WAITING_FOR_EC2") {
    $classification = "BLOCKED_EC2_LIFECYCLE_TRANSITION"
  }
}

$record = [ordered]@{
  schema_version = "1.0"
  created_at = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
  result = "pass"
  classification = $classification
  work_order_present = ($null -ne $workOrder)
  work_order_id = $(if ($null -ne $workOrder) { [string]$workOrder.work_order_id } else { $null })
  unit_count = $(if ($null -ne $workOrder) { [int]$workOrder.unit_count } else { 0 })
  capacity_backoff = $backoff
  instance_state = $instanceState
  active_marker_present = (Test-Path -LiteralPath $activeMarker -PathType Leaf)
  automation_may_start_ec2 = $false
  next_action = $(if ($classification -eq "READY_WORK_WAITING_FOR_EC2") { "Notify the main session to evaluate one guarded batched runtime window; do not start EC2 from automation." } else { "Preserve the classification and do not start EC2." })
}
if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $directory = Split-Path -Parent $OutFile
  $null = New-Item -ItemType Directory -Force -Path $directory
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 15), $encoding)
}
$record | ConvertTo-Json -Depth 15
