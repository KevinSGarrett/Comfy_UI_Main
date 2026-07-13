param(
  [Parameter(Mandatory=$true)][ValidateSet("Activate", "Complete", "Inspect")][string]$Action,
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$WindowId = "",
  [string]$LaneId = "",
  [string]$Purpose = "bounded_target_runtime_validation",
  [string]$DeployBundleS3Uri = "",
  [string]$DeployBundleSha256 = "",
  [string]$EmergencyStopEvidencePath = "",
  [int]$MaxRuntimeMinutes = 60,
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$ExpectedAccountId = "029530099913",
  [string]$OwnerThreadOrAutomation = "019f422f-88b1-7382-872b-21de2089e983",
  [string]$FinalInstanceState = "",
  [string]$CompletionResult = "",
  [string]$CompletionEvidencePath = ""
)

$ErrorActionPreference = "Stop"
$encoding = New-Object System.Text.UTF8Encoding($false)
$markerDirectory = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_windows"
$activeMarkerPath = Join-Path $markerDirectory "ACTIVE_EC2_RUNTIME_WINDOW.json"
$historyDirectory = Join-Path $markerDirectory "history"

function Write-JsonAtomic {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path
  )

  $directory = Split-Path -Parent $Path
  $null = New-Item -ItemType Directory -Force -Path $directory
  $temporaryPath = Join-Path $directory ((Split-Path -Leaf $Path) + "." + [guid]::NewGuid().ToString("N") + ".tmp")
  try {
    [System.IO.File]::WriteAllText($temporaryPath, ($Value | ConvertTo-Json -Depth 20), $encoding)
    Move-Item -LiteralPath $temporaryPath -Destination $Path -Force
  } finally {
    if (Test-Path -LiteralPath $temporaryPath) {
      Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
    }
  }
}

function Read-JsonRequired {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (!(Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "Required JSON file is missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Resolve-ProjectPath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function ConvertTo-ProjectRelativePath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
  $full = [System.IO.Path]::GetFullPath($Path)
  $prefix = $root + [System.IO.Path]::DirectorySeparatorChar
  if ($full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $full.Substring($prefix.Length).Replace("\", "/")
  }
  return $full
}

if ($Action -eq "Inspect") {
  if (!(Test-Path -LiteralPath $activeMarkerPath -PathType Leaf)) {
    [ordered]@{
      result = "pass"
      classification = "NO_ACTIVE_EC2_RUNTIME_WINDOW"
      active_marker_path = $activeMarkerPath
      active = $false
    } | ConvertTo-Json -Depth 10
    return
  }
  $marker = Read-JsonRequired -Path $activeMarkerPath
  $expiresAt = [datetimeoffset]::Parse([string]$marker.expires_at)
  [ordered]@{
    result = "pass"
    classification = $(if ($expiresAt -le [datetimeoffset]::UtcNow) { "ACTIVE_EC2_RUNTIME_WINDOW_EXPIRED" } else { "ACTIVE_EC2_RUNTIME_WINDOW_PRESENT" })
    active_marker_path = $activeMarkerPath
    active = $true
    expired = ($expiresAt -le [datetimeoffset]::UtcNow)
    marker = $marker
  } | ConvertTo-Json -Depth 20
  return
}

if ($WindowId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') {
  throw "WindowId must use 8-128 safe identifier characters."
}

if ($Action -eq "Activate") {
  if ([string]::IsNullOrWhiteSpace($LaneId)) { throw "LaneId is required for marker activation." }
  if ($DeployBundleS3Uri -notmatch '^s3://[^/]+/.+') { throw "A concrete deploy-bundle S3 URI is required for marker activation." }
  if ($DeployBundleSha256 -notmatch '^[0-9a-fA-F]{64}$') { throw "A 64-character deploy-bundle SHA-256 is required for marker activation." }
  if ($MaxRuntimeMinutes -lt 5 -or $MaxRuntimeMinutes -gt 240) { throw "MaxRuntimeMinutes must be between 5 and 240." }
  if ($OwnerThreadOrAutomation -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') { throw "Owner identity is invalid." }

  if (Test-Path -LiteralPath $activeMarkerPath -PathType Leaf) {
    $existing = Read-JsonRequired -Path $activeMarkerPath
    throw "An active EC2 runtime marker already exists for window '$($existing.window_id)'."
  }

  $emergencyPath = Resolve-ProjectPath -Path $EmergencyStopEvidencePath
  $emergency = Read-JsonRequired -Path $emergencyPath
  $allowedEmergencyResults = @(
    "emergency_stop_schedule_created",
    "emergency_stop_schedule_created_verified",
    "emergency_stop_schedule_created_and_verified"
  )
  if ([string]$emergency.runtime_window_id -cne $WindowId -or [string]$emergency.result -notin $allowedEmergencyResults) {
    throw "Emergency-stop evidence is not verified for runtime window '$WindowId'."
  }

  $now = [datetimeoffset]::UtcNow
  $marker = [ordered]@{
    schema_version = "2.0"
    window_id = $WindowId
    status = "ACTIVE"
    created_at = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
    expires_at = $now.AddMinutes($MaxRuntimeMinutes).ToString("yyyy-MM-ddTHH:mm:ssZ")
    instance_id = $InstanceId
    region = $Region
    expected_account_id = $ExpectedAccountId
    purpose = $Purpose
    target_lane_id = $LaneId
    deploy_bundle_s3_uri = $DeployBundleS3Uri
    deploy_bundle_sha256 = $DeployBundleSha256.ToLowerInvariant()
    emergency_stop_evidence_path = ConvertTo-ProjectRelativePath -Path $emergencyPath
    max_runtime_minutes = $MaxRuntimeMinutes
    owner_thread_or_automation = $OwnerThreadOrAutomation
    allowed_stop_policy = "stop_when_expired_or_unapproved"
  }
  Write-JsonAtomic -Value $marker -Path $activeMarkerPath
  [ordered]@{
    result = "pass"
    classification = "ACTIVE_EC2_RUNTIME_WINDOW_CREATED"
    active_marker_path = $activeMarkerPath
    marker = $marker
  } | ConvertTo-Json -Depth 20
  return
}

$active = Read-JsonRequired -Path $activeMarkerPath
if ([string]$active.window_id -cne $WindowId) {
  throw "Runtime-window completion ID does not match the active marker."
}
if ($FinalInstanceState -cne "stopped") {
  throw "The active marker can be completed only after independently verified EC2 state 'stopped'."
}
if ([string]::IsNullOrWhiteSpace($CompletionResult)) {
  throw "CompletionResult is required when completing a runtime window."
}

$completed = [ordered]@{}
foreach ($property in $active.PSObject.Properties) {
  $completed[$property.Name] = $property.Value
}
$completed.status = "ENDED"
$completed.ended_at = [datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$completed.final_instance_state = $FinalInstanceState
$completed.completion_result = $CompletionResult
$completed.completion_evidence_path = ConvertTo-ProjectRelativePath -Path (Resolve-ProjectPath -Path $CompletionEvidencePath)

$null = New-Item -ItemType Directory -Force -Path $historyDirectory
$historyPath = Join-Path $historyDirectory ("$WindowId." + (Get-Date -Format "yyyyMMddTHHmmss") + ".json")
Write-JsonAtomic -Value $completed -Path $historyPath
Remove-Item -LiteralPath $activeMarkerPath -Force

[ordered]@{
  result = "pass"
  classification = "ACTIVE_EC2_RUNTIME_WINDOW_COMPLETED"
  active_marker_removed = !(Test-Path -LiteralPath $activeMarkerPath)
  history_path = $historyPath
  marker = $completed
} | ConvertTo-Json -Depth 20
