<#
.SYNOPSIS
Creates a local-only EC2 runtime-window marker plan.

.DESCRIPTION
Builds the ACTIVE_EC2_RUNTIME_WINDOW.json payload that should be written only
after an explicitly approved live EC2 window is actually starting. This helper
does not contact AWS, does not start EC2, and does not write the active marker.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$WindowId = "",
  [string]$LaneId = "sdxl_realvisxl_base_lane",
  [string]$Purpose = "bounded_target_runtime_validation",
  [string]$Command = "",
  [string]$DeployBundleS3Uri = "",
  [string]$DeployBundleSha256 = "",
  [string]$EmergencyStopEvidencePath = "",
  [string]$WatchdogEvidencePath = "",
  [int]$MaxRuntimeMinutes = 60,
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$ExpectedAccountId = "029530099913",
  [string]$OwnerThreadOrAutomation = "019f422f-88b1-7382-872b-21de2089e983",
  [string]$AllowedStopPolicy = "stop_when_expired_or_unapproved",
  [string]$OutFile = "",
  [string]$MarkerTemplateOutFile = ""
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $dir = Split-Path -Parent $Path
  if (![string]::IsNullOrWhiteSpace($dir)) {
    $null = New-Item -ItemType Directory -Force -Path $dir
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Resolve-ProjectPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function ConvertTo-ProjectRelativePath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  try {
    $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
    $full = [System.IO.Path]::GetFullPath($Path)
    $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
    if ($full.Equals($root, [System.StringComparison]::OrdinalIgnoreCase)) { return "." }
    if ($full.StartsWith("$root$separator", [System.StringComparison]::OrdinalIgnoreCase)) {
      return $full.Substring($root.Length + 1).Replace("\", "/")
    }
  } catch {
    return $Path
  }
  return $Path
}

function New-Check {
  param(
    [string]$Name,
    [bool]$Passed,
    [object]$Observed,
    [object]$Expected
  )
  return [ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Get-JsonResult {
  param([string]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if ([string]::IsNullOrWhiteSpace($resolved) -or !(Test-Path -LiteralPath $resolved)) { return $null }
  try {
    $json = Get-Content -LiteralPath $resolved -Raw | ConvertFrom-Json
    if ($null -ne $json.PSObject.Properties["result"]) { return [string]$json.result }
    return "json_parsed_no_result"
  } catch {
    return "json_parse_failed"
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
if ([string]::IsNullOrWhiteSpace($WindowId)) {
  $WindowId = "ec2-window-plan-$stamp"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_EC2_RUNTIME_WINDOW_MARKER_PLAN_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkerTemplateOutFile)) {
  $MarkerTemplateOutFile = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_windows\ACTIVE_EC2_RUNTIME_WINDOW.template.$stamp.json"
}

$activeMarkerPath = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_windows\ACTIVE_EC2_RUNTIME_WINDOW.json"
$expiresAt = (Get-Date).ToUniversalTime().AddMinutes($MaxRuntimeMinutes).ToString("yyyy-MM-ddTHH:mm:ssZ")
$gitOrBundle = $(if (![string]::IsNullOrWhiteSpace($DeployBundleSha256)) { $DeployBundleSha256 } else { "missing_bundle_sha256" })
$emergencyResult = Get-JsonResult -Path $EmergencyStopEvidencePath
$watchdogResult = Get-JsonResult -Path $WatchdogEvidencePath

$markerPayload = [ordered]@{
  schema_version = "1.0"
  window_id = $WindowId
  status = "ACTIVE"
  created_at = "<write-actual-window-start-time>"
  expires_at = $expiresAt
  instance_id = $InstanceId
  region = $Region
  expected_account_id = $ExpectedAccountId
  purpose = $Purpose
  target_lane_id = $LaneId
  command = $Command
  max_runtime_minutes = $MaxRuntimeMinutes
  emergency_stop_evidence_path = ConvertTo-ProjectRelativePath -Path (Resolve-ProjectPath -Path $EmergencyStopEvidencePath)
  watchdog_evidence_path_or_null = ConvertTo-ProjectRelativePath -Path (Resolve-ProjectPath -Path $WatchdogEvidencePath)
  git_head_or_bundle_sha = $gitOrBundle
  owner_thread_or_automation = $OwnerThreadOrAutomation
  allowed_stop_policy = $AllowedStopPolicy
}

$checks = @(
  (New-Check -Name "project_root_exists" -Passed (Test-Path -LiteralPath $ProjectRoot) -Observed $ProjectRoot -Expected "existing project root"),
  (New-Check -Name "active_marker_not_written" -Passed (!(Test-Path -LiteralPath $activeMarkerPath)) -Observed (Test-Path -LiteralPath $activeMarkerPath) -Expected $false),
  (New-Check -Name "lane_id_supplied" -Passed (![string]::IsNullOrWhiteSpace($LaneId)) -Observed $LaneId -Expected "non-empty lane id"),
  (New-Check -Name "command_supplied" -Passed (![string]::IsNullOrWhiteSpace($Command)) -Observed $Command -Expected "future live command string"),
  (New-Check -Name "deploy_bundle_uri_supplied" -Passed (![string]::IsNullOrWhiteSpace($DeployBundleS3Uri)) -Observed $DeployBundleS3Uri -Expected "s3:// deploy bundle URI"),
  (New-Check -Name "deploy_bundle_sha_supplied" -Passed ($DeployBundleSha256 -match "^[a-fA-F0-9]{64}$") -Observed $DeployBundleSha256 -Expected "64 character SHA256"),
  (New-Check -Name "max_runtime_minutes_bounded" -Passed ($MaxRuntimeMinutes -ge 5 -and $MaxRuntimeMinutes -le 240) -Observed $MaxRuntimeMinutes -Expected "5..240"),
  (New-Check -Name "emergency_stop_evidence_parsed" -Passed ($emergencyResult -in @("dry_run_emergency_stop_schedule_plan", "emergency_stop_schedule_created", "emergency_stop_schedule_created_verified")) -Observed $emergencyResult -Expected "dry-run or created emergency-stop evidence"),
  (New-Check -Name "watchdog_evidence_optional_or_parsed" -Passed ([string]::IsNullOrWhiteSpace($WatchdogEvidencePath) -or $watchdogResult -in @("dry_run_instance_watchdog_plan", "instance_stop_watchdog_started")) -Observed $watchdogResult -Expected "empty, dry-run, or started watchdog evidence"),
  (New-Check -Name "owner_thread_current" -Passed ($OwnerThreadOrAutomation -eq "019f422f-88b1-7382-872b-21de2089e983") -Observed $OwnerThreadOrAutomation -Expected "019f422f-88b1-7382-872b-21de2089e983")
)

$failureCount = @($checks | Where-Object { $_.result -ne "pass" }).Count
$record = [ordered]@{
  schema_version = "1.0"
  evidence_id = "W66-EC2-RUNTIME-WINDOW-MARKER-PLAN-$stamp"
  created_at = $createdAt
  artifact_type = "ec2_runtime_window_marker_plan"
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  active_marker_written = $false
  active_marker_path = ConvertTo-ProjectRelativePath -Path $activeMarkerPath
  marker_template_path = ConvertTo-ProjectRelativePath -Path $MarkerTemplateOutFile
  marker_payload = $markerPayload
  deploy_bundle_s3_uri = $DeployBundleS3Uri
  deploy_bundle_sha256 = $DeployBundleSha256
  emergency_stop_result = $emergencyResult
  watchdog_result = $watchdogResult
  checks = $checks
  failure_count = $failureCount
  result = $(if ($failureCount -eq 0) { "pass_local_only_marker_plan_ready" } else { "fail_local_marker_plan_validation" })
  next_action = "Write this marker payload to runtime_artifacts/ec2_runtime_windows/ACTIVE_EC2_RUNTIME_WINDOW.json only after an explicit live EC2 window is selected and actually starting; remove or mark ENDED after final stopped-state verification."
}

Write-JsonNoBom -Value $markerPayload -Path $MarkerTemplateOutFile -Depth 20
Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
$record | ConvertTo-Json -Depth 30
if ($failureCount -gt 0) { exit 2 }
