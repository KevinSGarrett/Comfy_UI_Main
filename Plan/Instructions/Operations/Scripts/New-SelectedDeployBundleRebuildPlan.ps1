<#
.SYNOPSIS
Creates a local-only selected-lane deploy-bundle rebuild plan.

.DESCRIPTION
Consumes the active target-runtime execution plan and package/deploy matrix,
then records the exact selected lane run package and deploy-bundle rebuild
command to use after the manifest-scoped checkpoint is explicitly completed.
The helper writes evidence only; it does not rebuild deploy bundles, stage,
commit, push, contact services, upload to S3, start EC2, or generate.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$PackageDeployMatrixFile = "",
  [string]$TargetRuntimeExecutionPlanFile = "",
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

function Find-LatestFile {
  param([string]$Directory, [string]$Filter)
  if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $item = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTimeUtc, Name -Descending |
    Select-Object -First 1
  if ($null -eq $item) { return $null }
  return $item.FullName
}

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$runtimeDir = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence\Runtime_Readiness"
if ([string]::IsNullOrWhiteSpace($PackageDeployMatrixFile)) {
  $PackageDeployMatrixFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_PACKAGE_DEPLOY_MATRIX_*.json"
}
if ([string]::IsNullOrWhiteSpace($TargetRuntimeExecutionPlanFile)) {
  $TargetRuntimeExecutionPlanFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_DEPLOY_BUNDLE_REBUILD_PLAN_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$matrixResolved = Resolve-ProjectPath -Path $PackageDeployMatrixFile
$targetResolved = Resolve-ProjectPath -Path $TargetRuntimeExecutionPlanFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
foreach ($required in @(
  @{ label = "package_deploy_matrix"; path = $matrixResolved },
  @{ label = "target_runtime_execution_plan"; path = $targetResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$matrix = Read-JsonFile -Path $matrixResolved
$target = Read-JsonFile -Path $targetResolved
$selectedLaneId = [string]$target.selected_lane_id
if ([string]::IsNullOrWhiteSpace($selectedLaneId)) {
  throw "Target runtime execution plan does not contain selected_lane_id."
}

$selectedRows = @(Convert-ToArray -Value $matrix.rows | Where-Object { [string]$_.lane_id -eq $selectedLaneId } | Select-Object -First 1)
$selectedRow = if ($selectedRows.Count -gt 0) { $selectedRows[0] } else { $null }
$runPackageRel = if ($null -ne $selectedRow) { [string]$selectedRow.run_package_manifest } else { "" }
$runPackageResolved = Resolve-ProjectPath -Path $runPackageRel
$runPackageExists = (![string]::IsNullOrWhiteSpace($runPackageResolved) -and (Test-Path -LiteralPath $runPackageResolved -PathType Leaf))
$runPackage = if ($runPackageExists) { Read-JsonFile -Path $runPackageResolved } else { $null }
$runPackagePass = ($runPackageExists -and [string]$runPackage.result -eq "pass_local_only" -and [string]$runPackage.lane_id -eq $selectedLaneId -and -not [bool]$runPackage.ec2_started -and -not [bool]$runPackage.generation_executed)

$existingDeployManifestRel = if ($null -ne $selectedRow) { [string]$selectedRow.deploy_bundle_manifest } else { "" }
$existingDeployManifestResolved = Resolve-ProjectPath -Path $existingDeployManifestRel
$existingDeployManifestExists = (![string]::IsNullOrWhiteSpace($existingDeployManifestResolved) -and (Test-Path -LiteralPath $existingDeployManifestResolved -PathType Leaf))
$sourceGitDirtyInExistingBundle = ($null -ne $selectedRow -and -not [bool]$selectedRow.source_git_clean_in_bundle)

$currentGitStatus = @(git -C $ProjectRoot status --porcelain=v1 2>$null)
if ($LASTEXITCODE -ne 0) { $currentGitStatus = @("git_status_unavailable") }
$currentGitClean = (@($currentGitStatus).Count -eq 0)

$readyAfterCheckpoint = (
  $runPackagePass -and
  $sourceGitDirtyInExistingBundle -and
  -not $currentGitClean
)

$result = if (-not $runPackagePass) {
  "blocked_selected_deploy_bundle_rebuild_run_package_not_ready"
} elseif (-not $sourceGitDirtyInExistingBundle) {
  "selected_deploy_bundle_rebuild_not_required_existing_bundle_clean"
} else {
  "selected_deploy_bundle_rebuild_plan_ready_after_clean_checkpoint"
}

$bundleNameTemplate = "deploy_bundle_$selectedLaneId`_<timestamp>"
$outDirTemplate = "runtime_artifacts/deploy_bundles/$bundleNameTemplate"
$rebuildCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $selectedLaneId -RunPackageManifestFile C:\Comfy_UI_Main\$runPackageRel -BundleName $bundleNameTemplate -OutDir C:\Comfy_UI_Main\$outDirTemplate"

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_deploy_bundle_rebuild_plan"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  local_only = $true
  github_api_contacted = $false
  aws_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  active_runtime_marker_written = $false
  stage_attempted = $false
  commit_attempted = $false
  push_attempted = $false
  reset_attempted = $false
  checkout_attempted = $false
  deploy_bundle_rebuilt = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  selected_lane_id = $selectedLaneId
  selected_work_order_id = [string]$target.selected_work_order_id
  package_deploy_matrix = ConvertTo-ProjectRelativePath -Path $matrixResolved
  target_runtime_execution_plan = ConvertTo-ProjectRelativePath -Path $targetResolved
  run_package_manifest = ConvertTo-ProjectRelativePath -Path $runPackageResolved
  run_package_exists = $runPackageExists
  run_package_pass_local_only = $runPackagePass
  existing_deploy_bundle_manifest = ConvertTo-ProjectRelativePath -Path $existingDeployManifestResolved
  existing_deploy_bundle_manifest_exists = $existingDeployManifestExists
  existing_deploy_bundle_source_git_clean = $(if ($null -ne $selectedRow) { [bool]$selectedRow.source_git_clean_in_bundle } else { $false })
  existing_deploy_bundle_source_git_status_count = $(if ($null -ne $selectedRow) { [int]$selectedRow.source_git_status_count } else { $null })
  current_git_clean = $currentGitClean
  current_git_status_count = @($currentGitStatus).Count
  ready_to_rebuild_after_clean_checkpoint = $readyAfterCheckpoint
  rebuild_command = $rebuildCommand
  expected_manifest_after_rebuild = "$outDirTemplate/DEPLOY_BUNDLE_MANIFEST.json"
  expected_zip_after_rebuild = "$outDirTemplate/$bundleNameTemplate.zip"
  required_post_rebuild_checks = @(
    "DEPLOY_BUNDLE_MANIFEST.json result=pass_local_only",
    "source_git_clean=true",
    "source_git_status_count=0",
    "bundle_zip exists",
    "bundle_zip_sha256 matches actual zip hash",
    "ec2_started=false",
    "generation_executed=false"
  )
  blockers_before_rebuild = @(
    if (-not $runPackagePass) { "selected_run_package_not_pass_local_only" }
    if (-not $currentGitClean) { "manifest_scoped_checkpoint_not_yet_executed_clean" }
    if ([bool]$target.explicit_user_selection_required) { "explicit_user_target_runtime_selection_required" }
  ) | Select-Object -Unique
  checkpoint_boundary = "Selected deploy-bundle rebuild plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = "After explicit manifest-scoped checkpoint and clean Git proof, run the rebuild command, then rerun package/deploy matrix and S3/runtime gates before any EC2 proof."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 40) + [Environment]::NewLine, $utf8NoBom)

$markdown = @"
# Selected Deploy Bundle Rebuild Plan

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $selectedLaneId
- run_package_pass_local_only: $($record.run_package_pass_local_only)
- existing_deploy_bundle_source_git_clean: $($record.existing_deploy_bundle_source_git_clean)
- current_git_clean: $($record.current_git_clean)
- ready_to_rebuild_after_clean_checkpoint: $($record.ready_to_rebuild_after_clean_checkpoint)

## Rebuild Command

```powershell
$rebuildCommand
```

## Boundary

$($record.checkpoint_boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote selected deploy-bundle rebuild plan: $outFileResolved"
$record | ConvertTo-Json -Depth 40
