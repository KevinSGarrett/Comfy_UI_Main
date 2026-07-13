param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$WorkOrderId,
  [Parameter(Mandatory=$true)][string]$LaneId,
  [Parameter(Mandatory=$true)][string]$DeployBundleS3Uri,
  [Parameter(Mandatory=$true)][string]$DeployBundleSha256,
  [Parameter(Mandatory=$true)][string[]]$UnitManifestFiles,
  [int]$MaxRuntimeMinutes = 60,
  [int]$ExpiresAfterMinutes = 240,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$encoding = New-Object System.Text.UTF8Encoding($false)
if ($WorkOrderId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') { throw "WorkOrderId is invalid." }
if ([string]::IsNullOrWhiteSpace($LaneId)) { throw "LaneId is required." }
if ($DeployBundleS3Uri -notmatch '^s3://[^/]+/.+') { throw "DeployBundleS3Uri must be a concrete S3 object URI." }
if ($DeployBundleSha256 -notmatch '^[0-9a-fA-F]{64}$') { throw "DeployBundleSha256 must be 64 hexadecimal characters." }
if (@($UnitManifestFiles).Count -lt 1 -or @($UnitManifestFiles).Count -gt 5) { throw "A batch must contain 1-5 compatible units." }
if ($MaxRuntimeMinutes -lt 10 -or $MaxRuntimeMinutes -gt 120) { throw "MaxRuntimeMinutes must be between 10 and 120." }
if ($ExpiresAfterMinutes -lt 30 -or $ExpiresAfterMinutes -gt 1440) { throw "ExpiresAfterMinutes must be between 30 and 1440." }

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_dispatch\READY_GPU_WORK.json"
}

$units = New-Object System.Collections.ArrayList
$seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($unitFile in $UnitManifestFiles) {
  $resolved = $(if ([System.IO.Path]::IsPathRooted($unitFile)) { [System.IO.Path]::GetFullPath($unitFile) } else { [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $unitFile)) })
  $projectPrefix = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  if (!$resolved.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Unit manifest must remain inside ProjectRoot: $unitFile" }
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Unit manifest is missing: $unitFile" }
  if (!$seen.Add($resolved)) { throw "Duplicate unit manifest: $unitFile" }
  $unit = Get-Content -Raw -LiteralPath $resolved | ConvertFrom-Json
  $unitLane = $(if ($unit.PSObject.Properties.Name -contains "lane_id") { [string]$unit.lane_id } else { [string]$unit.target_lane_id })
  if ($unitLane -cne $LaneId) { throw "Unit lane '$unitLane' does not match batch lane '$LaneId': $unitFile" }
  if (($unit.PSObject.Properties.Name -contains "requires_gold_masks") -and [bool]$unit.requires_gold_masks) {
    throw "Gold-mask-dependent work cannot enter a GPU runtime batch while that dependency is blocked: $unitFile"
  }
  $result = [string]$unit.result
  if ($result -notmatch '^(pass|ready|certified|.*_pass|pass_.*|.*_ready)$') {
    throw "Unit manifest is not in a passing or ready state: $unitFile (result=$result)"
  }
  [void]$units.Add([ordered]@{
    manifest_path = $resolved.Substring($projectPrefix.Length).Replace("\", "/")
    manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolved).Hash.ToLowerInvariant()
    lane_id = $unitLane
    result = $result
    run_id = $(if ($unit.PSObject.Properties.Name -contains "run_id") { [string]$unit.run_id } else { $null })
  })
}

$now = [datetimeoffset]::UtcNow
$workOrder = [ordered]@{
  schema_version = "1.0"
  work_order_id = $WorkOrderId
  status = "READY_WORK_WAITING_FOR_EC2"
  created_at = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
  expires_at = $now.AddMinutes($ExpiresAfterMinutes).ToString("yyyy-MM-ddTHH:mm:ssZ")
  lane_id = $LaneId
  deploy_bundle_s3_uri = $DeployBundleS3Uri
  deploy_bundle_sha256 = $DeployBundleSha256.ToLowerInvariant()
  max_runtime_minutes = $MaxRuntimeMinutes
  unit_count = $units.Count
  units = @($units)
  execution_contract = [ordered]@{
    one_ec2_start = $true
    one_static_environment_and_model_proof = $true
    execute_compatible_units_sequentially = $true
    upload_all_results_before_stop = $true
    pullback_and_hash_verify_all_results = $true
    final_instance_state_required = "stopped"
    active_runtime_marker_required = $true
    emergency_stop_schedule_required = $true
    instance_watchdog_required = $true
  }
  mask_truth_consumed = $false
  authorizes_ec2_start_by_automation = $false
  result = "pass_local_only"
}

$directory = Split-Path -Parent $OutFile
$null = New-Item -ItemType Directory -Force -Path $directory
$temporary = "$OutFile.$([guid]::NewGuid().ToString('N')).tmp"
try {
  [System.IO.File]::WriteAllText($temporary, ($workOrder | ConvertTo-Json -Depth 20), $encoding)
  Move-Item -LiteralPath $temporary -Destination $OutFile -Force
} finally {
  Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
}
$workOrder | ConvertTo-Json -Depth 20
