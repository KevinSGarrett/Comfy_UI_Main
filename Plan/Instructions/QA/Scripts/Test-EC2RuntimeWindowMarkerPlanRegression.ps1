<#
.SYNOPSIS
Exercises runtime-window marker evidence binding without contacting AWS.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$helper = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-EC2RuntimeWindowMarkerPlan.ps1"
$windowId = "rw-normal-20260713T105243-0500-57f1f908"
$laneId = "sdxl_realvisxl_controlnet_normal_lane"
$sha256 = "a" * 64
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$tempRoot = Join-Path $ProjectRoot "runtime_artifacts\regression_temp\ec2_runtime_window_marker_$stamp"
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null

function Write-JsonNoBom {
  param([string]$Path, [object]$Payload)
  $dir = Split-Path -Parent $Path
  [System.IO.Directory]::CreateDirectory($dir) | Out-Null
  [System.IO.File]::WriteAllText($Path, ($Payload | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-Case {
  param(
    [string]$Name,
    [string]$EmergencyResult = "dry_run_emergency_stop_schedule_plan",
    [string]$WatchdogResult = "dry_run_instance_watchdog_plan",
    [string]$EmergencyWindowId = $windowId,
    [string]$WatchdogWindowId = $windowId,
    [string]$SuppliedWindowId = $windowId,
    [string]$Owner = "codex-main-session",
    [bool]$SupplyWatchdog = $true,
    [bool]$CreateActiveMarker = $false,
    [string]$ExpectedResult = "pass_local_only_marker_plan_ready",
    [string]$ExpectedFailedCheck = ""
  )

  $caseRoot = Join-Path $tempRoot $Name
  [System.IO.Directory]::CreateDirectory($caseRoot) | Out-Null
  $emergencyPath = Join-Path $caseRoot "emergency.json"
  $watchdogPath = Join-Path $caseRoot "watchdog.json"
  $recordPath = Join-Path $caseRoot "marker_plan.json"
  $templatePath = Join-Path $caseRoot "marker_template.json"
  Write-JsonNoBom -Path $emergencyPath -Payload ([ordered]@{ result = $EmergencyResult; runtime_window_id = $EmergencyWindowId })
  if ($SupplyWatchdog) {
    Write-JsonNoBom -Path $watchdogPath -Payload ([ordered]@{ result = $WatchdogResult; runtime_window_id = $WatchdogWindowId })
  }
  if ($CreateActiveMarker) {
    Write-JsonNoBom -Path (Join-Path $caseRoot "runtime_artifacts\ec2_runtime_windows\ACTIVE_EC2_RUNTIME_WINDOW.json") -Payload ([ordered]@{ status = "ACTIVE" })
  }

  $childArgs = @(
    "-NoProfile", "-File", $helper,
    "-ProjectRoot", $caseRoot,
    "-WindowId", $SuppliedWindowId,
    "-LaneId", $laneId,
    "-Purpose", "normal_target_runtime_static_proof",
    "-Command", "bounded-normal-static-proof",
    "-DeployBundleS3Uri", "s3://example-bucket/normal/bundle.zip",
    "-DeployBundleSha256", $sha256,
    "-EmergencyStopEvidencePath", $emergencyPath,
    "-MaxRuntimeMinutes", "60",
    "-OwnerThreadOrAutomation", $Owner,
    "-OutFile", $recordPath,
    "-MarkerTemplateOutFile", $templatePath
  )
  if ($SupplyWatchdog) { $childArgs += @("-WatchdogEvidencePath", $watchdogPath) }
  & powershell @childArgs *> $null
  $exitCode = $LASTEXITCODE
  $payload = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
  $failedChecks = @($payload.checks | Where-Object { $_.result -ne "pass" } | ForEach-Object { [string]$_.name })
  $passed = (
    [string]$payload.result -ceq $ExpectedResult -and
    (($ExpectedResult -eq "pass_local_only_marker_plan_ready" -and $exitCode -eq 0) -or ($ExpectedResult -eq "fail_local_marker_plan_validation" -and $exitCode -eq 2)) -and
    ([string]::IsNullOrWhiteSpace($ExpectedFailedCheck) -or $failedChecks -contains $ExpectedFailedCheck) -and
    [string]$payload.marker_payload.window_id -ceq $SuppliedWindowId -and
    [string]$payload.emergency_stop_evidence.runtime_window_id -ceq $EmergencyWindowId -and
    -not [bool]$payload.aws_contacted -and -not [bool]$payload.ec2_started -and
    -not [bool]$payload.generation_executed -and -not [bool]$payload.active_marker_written
  )
  return [ordered]@{
    name = $Name
    result = $(if ($passed) { "pass" } else { "fail" })
    observed_result = [string]$payload.result
    exit_code = $exitCode
    failed_checks = $failedChecks
  }
}

$cases = @(
  (Invoke-Case -Name "matching_dry_run_evidence"),
  (Invoke-Case -Name "matching_verified_live_control_evidence" -EmergencyResult "emergency_stop_schedule_created_and_verified" -WatchdogResult "instance_stop_watchdog_started_and_capability_verified"),
  (Invoke-Case -Name "watchdog_optional_before_instance_start" -SupplyWatchdog $false),
  (Invoke-Case -Name "emergency_window_mismatch_rejected" -EmergencyWindowId "rw-normal-20260713T105243-0500-deadbeef" -ExpectedResult "fail_local_marker_plan_validation" -ExpectedFailedCheck "emergency_stop_runtime_window_matches"),
  (Invoke-Case -Name "watchdog_window_mismatch_rejected" -WatchdogWindowId "rw-normal-20260713T105243-0500-deadbeef" -ExpectedResult "fail_local_marker_plan_validation" -ExpectedFailedCheck "watchdog_runtime_window_matches_when_supplied"),
  (Invoke-Case -Name "unsafe_window_id_rejected" -SuppliedWindowId "bad window id" -EmergencyWindowId "bad window id" -WatchdogWindowId "bad window id" -ExpectedResult "fail_local_marker_plan_validation" -ExpectedFailedCheck "window_id_safe"),
  (Invoke-Case -Name "unsafe_owner_rejected" -Owner "bad owner" -ExpectedResult "fail_local_marker_plan_validation" -ExpectedFailedCheck "owner_identity_safe"),
  (Invoke-Case -Name "existing_active_marker_rejected" -CreateActiveMarker $true -ExpectedResult "fail_local_marker_plan_validation" -ExpectedFailedCheck "active_marker_not_written")
)

$failed = @($cases | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "ec2_runtime_window_marker_plan_regression"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
  local_only = $true
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  test_count = $cases.Count
  passing_test_count = @($cases | Where-Object { $_.result -eq "pass" }).Count
  failed_test_count = $failed.Count
  tests = $cases
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W64_EC2_RUNTIME_WINDOW_MARKER_PLAN_REGRESSION_$stamp.json"
}
Write-JsonNoBom -Path $OutFile -Payload $record

$tempBase = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "runtime_artifacts\regression_temp")).TrimEnd("\") + "\"
$tempResolved = [System.IO.Path]::GetFullPath($tempRoot)
if ($tempResolved.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $tempResolved -Recurse -Force
}

$record | ConvertTo-Json -Depth 20
if ($failed.Count -gt 0) { exit 1 }
exit 0
