<#
.SYNOPSIS
Creates a local-only package/deploy readiness matrix for the active runtime queue.

.DESCRIPTION
Validates that each active base-generation runtime lane has a local run package
manifest and deploy bundle manifest under the prepared queue artifact roots.
The helper verifies local-only boundaries, bundle zip existence/hash, and dirty
source bundle blockers. It does not contact AWS, GitHub, Civitai, S3, ComfyUI,
or EC2, does not execute generation, and does not certify target runtime.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RuntimeQueueFile = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json",
  [string]$RunPackageRoot = "runtime_artifacts\g9_20260709T030509\r",
  [string]$DeployBundleRoot = "runtime_artifacts\g9_20260709T030509\d",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return $null }
  $text = [string]$Path
  if ([string]::IsNullOrWhiteSpace($text)) { return $null }
  if ([System.IO.Path]::IsPathRooted($text)) { return [System.IO.Path]::GetFullPath($text) }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $text))
}

function ConvertTo-ProjectRelativePath {
  param([AllowNull()][object]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if ($null -eq $resolved) { return $null }
  $rootFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $targetFull = [System.IO.Path]::GetFullPath($resolved)
  if ($targetFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $targetFull.Substring($rootFull.Length).Replace("\", "/")
  }
  return $targetFull
}

function Read-JsonFile {
  param([Parameter(Mandatory = $true)][string]$Path)
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
}

function Get-FileSha256Lower {
  param([AllowNull()][string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Find-ManifestByLane {
  param(
    [string]$Root,
    [string]$ManifestName,
    [string]$LaneId
  )
  if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return $null }
  foreach ($file in @(Get-ChildItem -LiteralPath $Root -Recurse -Filter $ManifestName -File -ErrorAction SilentlyContinue)) {
    try {
      $payload = Read-JsonFile -Path $file.FullName
      if ([string]$payload.lane_id -eq $LaneId) {
        return [pscustomobject]@{ path = $file.FullName; payload = $payload }
      }
    } catch {
      continue
    }
  }
  return $null
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_PACKAGE_DEPLOY_MATRIX_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$queueResolved = Resolve-ProjectPath -Path $RuntimeQueueFile
$runRootResolved = Resolve-ProjectPath -Path $RunPackageRoot
$deployRootResolved = Resolve-ProjectPath -Path $DeployBundleRoot
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
foreach ($required in @(
  @{ label = "runtime_queue"; path = $queueResolved; type = "Leaf" },
  @{ label = "run_package_root"; path = $runRootResolved; type = "Container" },
  @{ label = "deploy_bundle_root"; path = $deployRootResolved; type = "Container" }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType $required.type)) {
    throw "Required input missing: $($required.label)"
  }
}

$queue = Read-JsonFile -Path $queueResolved
$lanes = @(Convert-ToArray -Value $queue.lanes | Sort-Object order)
$rows = @()
foreach ($lane in $lanes) {
  $laneId = [string]$lane.lane_id
  $run = Find-ManifestByLane -Root $runRootResolved -ManifestName "RUN_PACKAGE_MANIFEST.json" -LaneId $laneId
  $deploy = Find-ManifestByLane -Root $deployRootResolved -ManifestName "DEPLOY_BUNDLE_MANIFEST.json" -LaneId $laneId
  $runPayload = if ($null -ne $run) { $run.payload } else { $null }
  $deployPayload = if ($null -ne $deploy) { $deploy.payload } else { $null }
  $zipPath = $null
  $zipHash = ""
  $zipExists = $false
  $zipHashMatches = $false
  if ($null -ne $deployPayload) {
    $zipPath = Join-Path -Path (Split-Path -Path $deploy.path -Parent) -ChildPath ([string]$deployPayload.bundle_zip)
    $zipExists = Test-Path -LiteralPath $zipPath -PathType Leaf
    $zipHash = Get-FileSha256Lower -Path $zipPath
    $zipHashMatches = ($zipExists -and $zipHash -eq ([string]$deployPayload.bundle_zip_sha256).ToLowerInvariant())
  }
  $runPass = ($null -ne $runPayload -and [string]$runPayload.result -eq "pass_local_only" -and -not [bool]$runPayload.ec2_started -and -not [bool]$runPayload.generation_executed)
  $deployPass = ($null -ne $deployPayload -and [string]$deployPayload.result -eq "pass_local_only" -and -not [bool]$deployPayload.ec2_started -and -not [bool]$deployPayload.generation_executed -and $zipHashMatches)
  $sourceClean = ($null -ne $deployPayload -and [bool]$deployPayload.source_git_clean)
  $rows += [pscustomobject][ordered]@{
    order = [int]$lane.order
    lane_id = $laneId
    required_next_runtime_gate = [string]$lane.required_next_runtime_gate
    run_package_manifest = $(if ($null -ne $run) { ConvertTo-ProjectRelativePath -Path $run.path } else { $null })
    run_package_result = $(if ($null -ne $runPayload) { [string]$runPayload.result } else { "missing" })
    run_package_pass = $runPass
    deploy_bundle_manifest = $(if ($null -ne $deploy) { ConvertTo-ProjectRelativePath -Path $deploy.path } else { $null })
    deploy_bundle_result = $(if ($null -ne $deployPayload) { [string]$deployPayload.result } else { "missing" })
    deploy_bundle_pass = $deployPass
    deploy_bundle_zip = $(if ($null -ne $zipPath) { ConvertTo-ProjectRelativePath -Path $zipPath } else { $null })
    deploy_bundle_zip_sha256 = $zipHash
    deploy_bundle_zip_hash_match = $zipHashMatches
    source_git_clean_in_bundle = $sourceClean
    source_git_status_count = $(if ($null -ne $deployPayload) { [int]$deployPayload.source_git_status_count } else { $null })
    local_package_deploy_ready = ($runPass -and $deployPass)
    target_runtime_launch_allowed = $false
    exact_blockers = @(
      if (-not $runPass) { "run_package_missing_or_not_pass_local_only" }
      if (-not $deployPass) { "deploy_bundle_missing_or_hash_not_pass_local_only" }
      if (-not $sourceClean) { "deploy_bundle_source_git_dirty_rebuild_required_before_ec2" }
    )
  }
}

$readyRows = @($rows | Where-Object { [bool]$_.local_package_deploy_ready })
$dirtyBundleRows = @($rows | Where-Object { -not [bool]$_.source_git_clean_in_bundle })
$checks = @(
  (New-Check -Name "all_queue_lanes_have_run_packages" -Passed (@($rows | Where-Object { -not [bool]$_.run_package_pass }).Count -eq 0) -Observed (@($rows | Where-Object { -not [bool]$_.run_package_pass } | Select-Object -ExpandProperty lane_id)) -Expected "all active queue lanes have pass_local_only run packages"),
  (New-Check -Name "all_queue_lanes_have_deploy_bundles" -Passed (@($rows | Where-Object { -not [bool]$_.deploy_bundle_pass }).Count -eq 0) -Observed (@($rows | Where-Object { -not [bool]$_.deploy_bundle_pass } | Select-Object -ExpandProperty lane_id)) -Expected "all active queue lanes have pass_local_only deploy bundles with zip hash match"),
  (New-Check -Name "all_lanes_remain_local_only" -Passed (@($rows | Where-Object { [bool]$_.target_runtime_launch_allowed }).Count -eq 0) -Observed (@($rows | Where-Object { [bool]$_.target_runtime_launch_allowed } | Select-Object -ExpandProperty lane_id)) -Expected "no lane allows target-runtime launch from this matrix"),
  (New-Check -Name "dirty_source_bundle_gate_recorded" -Passed ($dirtyBundleRows.Count -eq $rows.Count) -Observed ([ordered]@{ dirty_bundle_count = $dirtyBundleRows.Count; lane_count = $rows.Count }) -Expected "every current deploy bundle records dirty source and must be rebuilt/revalidated before EC2")
)
$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$result = if ($failedChecks.Count -eq 0) { "pass_local_only_active_runtime_queue_package_deploy_matrix_ec2_blocked" } else { "fail_active_runtime_queue_package_deploy_matrix" }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "active_runtime_queue_package_deploy_matrix"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  active_runtime_marker_written = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  target_runtime_launch_allowed = $false
  runtime_queue = ConvertTo-ProjectRelativePath -Path $queueResolved
  run_package_root = ConvertTo-ProjectRelativePath -Path $runRootResolved
  deploy_bundle_root = ConvertTo-ProjectRelativePath -Path $deployRootResolved
  lane_count = $rows.Count
  local_package_deploy_ready_count = $readyRows.Count
  dirty_source_bundle_count = $dirtyBundleRows.Count
  clean_source_bundle_count = ($rows.Count - $dirtyBundleRows.Count)
  rows = @($rows)
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  exact_blockers = @(
    if ($dirtyBundleRows.Count -gt 0) { "deploy_bundle_source_git_dirty_rebuild_required_before_ec2" }
    "explicit_user_target_runtime_selection_required"
    "git_checkpoint_gate_not_clean_for_ec2_execute"
  ) | Select-Object -Unique
  certification_boundary = "Local active-runtime queue package/deploy matrix only. This does not authorize or perform live upload, marker write, EC2 start, generation, target-runtime proof, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, or Wave71+ activation."
  next_action = "Keep EC2 stopped. If a target-runtime lane is explicitly selected later, resolve the Git checkpoint and rebuild/revalidate the selected deploy bundle from a clean source checkpoint before S3 publish or EC2 static proof."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 40) + [Environment]::NewLine, $utf8NoBom)

$lines = foreach ($row in $rows) {
  "- $($row.order). $($row.lane_id): package=$($row.run_package_pass), deploy=$($row.deploy_bundle_pass), clean_source=$($row.source_git_clean_in_bundle)"
}
$markdown = @"
# Active Runtime Queue Package Deploy Matrix

- created_at: $($record.created_at)
- result: $result
- lane_count: $($record.lane_count)
- local_package_deploy_ready_count: $($record.local_package_deploy_ready_count)
- dirty_source_bundle_count: $($record.dirty_source_bundle_count)
- target_runtime_launch_allowed: false

## Rows

$($lines -join "`n")

## Boundary

$($record.certification_boundary)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 40
if ($result -like "fail_*") { exit 2 }
exit 0
