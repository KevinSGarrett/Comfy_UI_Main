param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"
$helper = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Set-EC2RuntimeWindowMarker.ps1"
if (!(Test-Path -LiteralPath $helper -PathType Leaf)) { throw "Runtime-window marker helper is missing." }

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cu-marker-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$evidenceDir = Join-Path $tempRoot "evidence"
$null = New-Item -ItemType Directory -Force -Path $evidenceDir
$windowId = "rw-marker-regression-001"
$emergencyPath = Join-Path $evidenceDir "emergency.json"
$encoding = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($emergencyPath, ([ordered]@{
  result = "emergency_stop_schedule_created_and_verified"
  runtime_window_id = $windowId
} | ConvertTo-Json), $encoding)

$results = New-Object System.Collections.ArrayList
try {
  $activate = & $helper -Action Activate -ProjectRoot $tempRoot -WindowId $windowId -LaneId "test_lane" -DeployBundleS3Uri "s3://test-bucket/deploy/test.zip" -DeployBundleSha256 ("a" * 64) -EmergencyStopEvidencePath $emergencyPath -OwnerThreadOrAutomation "marker-regression-owner" | ConvertFrom-Json
  [void]$results.Add([ordered]@{ case = "activate"; passed = ([string]$activate.classification -eq "ACTIVE_EC2_RUNTIME_WINDOW_CREATED") })

  $duplicateRejected = $false
  try {
    $null = & $helper -Action Activate -ProjectRoot $tempRoot -WindowId $windowId -LaneId "test_lane" -DeployBundleS3Uri "s3://test-bucket/deploy/test.zip" -DeployBundleSha256 ("a" * 64) -EmergencyStopEvidencePath $emergencyPath -OwnerThreadOrAutomation "marker-regression-owner"
  } catch {
    $duplicateRejected = $_.Exception.Message -like "*already exists*"
  }
  [void]$results.Add([ordered]@{ case = "duplicate_activation_rejected"; passed = $duplicateRejected })

  $runningRejected = $false
  try {
    $null = & $helper -Action Complete -ProjectRoot $tempRoot -WindowId $windowId -FinalInstanceState "running" -CompletionResult "test"
  } catch {
    $runningRejected = $_.Exception.Message -like "*state 'stopped'*"
  }
  [void]$results.Add([ordered]@{ case = "running_completion_rejected"; passed = $runningRejected })

  $complete = & $helper -Action Complete -ProjectRoot $tempRoot -WindowId $windowId -FinalInstanceState "stopped" -CompletionResult "regression_complete" | ConvertFrom-Json
  $activePath = Join-Path $tempRoot "runtime_artifacts\ec2_runtime_windows\ACTIVE_EC2_RUNTIME_WINDOW.json"
  [void]$results.Add([ordered]@{ case = "stopped_completion_archived"; passed = ([string]$complete.classification -eq "ACTIVE_EC2_RUNTIME_WINDOW_COMPLETED" -and !(Test-Path -LiteralPath $activePath) -and (Test-Path -LiteralPath ([string]$complete.history_path)) ) })
} finally {
  Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$failed = @($results | Where-Object { !$_.passed })
[ordered]@{
  result = $(if ($failed.Count -eq 0) { "pass" } else { "fail" })
  classification = $(if ($failed.Count -eq 0) { "EC2_RUNTIME_WINDOW_MARKER_LIFECYCLE_REGRESSION_PASS" } else { "EC2_RUNTIME_WINDOW_MARKER_LIFECYCLE_REGRESSION_FAIL" })
  checked = $results.Count
  failed = $failed.Count
  cases = @($results)
} | ConvertTo-Json -Depth 10
if ($failed.Count -gt 0) { throw "Runtime-window marker regression failed." }
