<#
.SYNOPSIS
Creates a local-only package readiness packet for the selected target-runtime lane.

.DESCRIPTION
Validates that the selected lane in the target-runtime execution plan has a
current local run package, deploy bundle, runtime requirements, local object-info
hash proof, and prepared input assets. This is a package/readiness packet only:
it does not contact AWS, GitHub, Civitai, S3, ComfyUI, or EC2, does not execute
generation, and does not certify target-runtime or final quality.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$TargetRuntimePlanFile = "",
  [string]$RunPackageManifestFile = "runtime_artifacts\g9_20260709T030509\r\sdxl_realvisxl_inpaint_detail_lane_ci_preflight\RUN_PACKAGE_MANIFEST.json",
  [string]$DeployBundleManifestFile = "runtime_artifacts\g9_20260709T030509\d\sdxl_realvisxl_inpaint_detail_lane_ci_preflight\DEPLOY_BUNDLE_MANIFEST.json",
  [string]$RuntimeRequirementsFile = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\sdxl_realvisxl_inpaint_detail_lane\runtime_requirements.json",
  [string]$LocalObjectInfoEvidenceFile = "",
  [string]$InputAssetManifestFile = "Plan\Instructions\Operations\Prepared_Input_Assets\sdxl_inpaint_detail_micro_nomouth_v4_20260707T034500-0500\INPAINT_MICRO_NOMOUTH_INPUT_ASSET_MANIFEST.json",
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

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Get-FileSha256Lower {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
if ([string]::IsNullOrWhiteSpace($TargetRuntimePlanFile)) {
  $TargetRuntimePlanFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($LocalObjectInfoEvidenceFile)) {
  $LocalObjectInfoEvidenceFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_LOCAL_OBJECT_INFO_INPAINT_DETAIL_MASKTOIMAGE_REFRESH_*.json"
  if ([string]::IsNullOrWhiteSpace($LocalObjectInfoEvidenceFile)) {
    $LocalObjectInfoEvidenceFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W69_LOCAL_OBJECT_INFO_INPAINT_DETAIL_NOMOUTH_V4_20260707T045500-0500.json"
  }
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_TARGET_RUNTIME_LANE_PACKAGE_READINESS_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$targetPlanResolved = Resolve-ProjectPath -Path $TargetRuntimePlanFile
$runPackageResolved = Resolve-ProjectPath -Path $RunPackageManifestFile
$deployBundleResolved = Resolve-ProjectPath -Path $DeployBundleManifestFile
$runtimeRequirementsResolved = Resolve-ProjectPath -Path $RuntimeRequirementsFile
$localObjectInfoResolved = Resolve-ProjectPath -Path $LocalObjectInfoEvidenceFile
$inputAssetResolved = Resolve-ProjectPath -Path $InputAssetManifestFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

foreach ($required in @(
  @{ label = "target_runtime_plan"; path = $targetPlanResolved },
  @{ label = "run_package_manifest"; path = $runPackageResolved },
  @{ label = "deploy_bundle_manifest"; path = $deployBundleResolved },
  @{ label = "runtime_requirements"; path = $runtimeRequirementsResolved },
  @{ label = "local_object_info"; path = $localObjectInfoResolved },
  @{ label = "input_asset_manifest"; path = $inputAssetResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$targetPlan = Read-JsonFile -Path $targetPlanResolved
$runPackage = Read-JsonFile -Path $runPackageResolved
$deployBundle = Read-JsonFile -Path $deployBundleResolved
$runtimeRequirements = Read-JsonFile -Path $runtimeRequirementsResolved
$objectInfo = Read-JsonFile -Path $localObjectInfoResolved
$inputAsset = Read-JsonFile -Path $inputAssetResolved

$laneId = [string]$targetPlan.selected_lane_id
$bundleZipPath = Resolve-ProjectPath -Path (Join-Path -Path (Split-Path -Path (ConvertTo-ProjectRelativePath -Path $deployBundleResolved) -Parent) -ChildPath ([string]$deployBundle.bundle_zip))
$bundleZipHash = Get-FileSha256Lower -Path $bundleZipPath

$requiredNodes = @(Convert-ToArray -Value $runtimeRequirements.required_nodes | ForEach-Object { [string]$_ })
$presentNodes = @(Convert-ToArray -Value $objectInfo.object_info.required_nodes_present | ForEach-Object { [string]$_ })
$missingNodes = @($requiredNodes | Where-Object { $presentNodes -notcontains $_ })

$packageFiles = @(Convert-ToArray -Value $runPackage.packaged_files)
$packageHashFailures = @($packageFiles | Where-Object { -not [bool]$_.source_hash_match })
$generatedFiles = @(Convert-ToArray -Value $runPackage.generated_files)
$missingGeneratedFiles = @($generatedFiles | Where-Object { -not (Test-Path -LiteralPath (Resolve-ProjectPath -Path $_.path) -PathType Leaf) })

$modelReq = @(Convert-ToArray -Value $runtimeRequirements.required_models | Select-Object -First 1)
$modelInfo = @(Convert-ToArray -Value $objectInfo.required_models | Select-Object -First 1)
$sourceAssetInfo = @(Convert-ToArray -Value $objectInfo.required_input_assets | Where-Object { [string]$_.role -eq "source_image" } | Select-Object -First 1)
$maskAssetInfo = @(Convert-ToArray -Value $objectInfo.required_input_assets | Where-Object { [string]$_.role -eq "mask_image" } | Select-Object -First 1)

$checks = @(
  (New-Check -Name "target_plan_selects_lane_and_blocks_execution" -Passed ([string]$targetPlan.result -eq "blocked_target_runtime_execution_plan_waiting_for_explicit_selection_and_clean_git" -and $laneId -eq "sdxl_realvisxl_inpaint_detail_lane" -and -not [bool]$targetPlan.execute_allowed_now) -Observed ([ordered]@{ result = $targetPlan.result; lane_id = $laneId; execute_allowed_now = $targetPlan.execute_allowed_now }) -Expected "blocked plan for sdxl_realvisxl_inpaint_detail_lane with execute_allowed_now=false"),
  (New-Check -Name "run_package_passes_local_only" -Passed ([string]$runPackage.result -eq "pass_local_only" -and [string]$runPackage.lane_id -eq $laneId -and -not [bool]$runPackage.ec2_started -and -not [bool]$runPackage.generation_executed) -Observed ([ordered]@{ result = $runPackage.result; lane_id = $runPackage.lane_id; ec2_started = $runPackage.ec2_started; generation_executed = $runPackage.generation_executed }) -Expected "run package pass_local_only for selected lane without EC2/generation"),
  (New-Check -Name "run_package_hashes_and_dry_run_pass" -Passed ($packageHashFailures.Count -eq 0 -and [string]$runPackage.workflow_static.qa_status -eq "pass" -and [int]$runPackage.workflow_static.defect_count -eq 0 -and [bool]$runPackage.smoke_dry_run.request_body_written -and -not [bool]$runPackage.smoke_dry_run.execution_allowed -and [int]$runPackage.smoke_dry_run.error_count -eq 0 -and $missingGeneratedFiles.Count -eq 0) -Observed ([ordered]@{ package_hash_failures = $packageHashFailures.Count; workflow_static = $runPackage.workflow_static.qa_status; smoke_errors = $runPackage.smoke_dry_run.error_count; missing_generated_files = $missingGeneratedFiles.Count }) -Expected "all package hashes match, static QA passes, dry-run writes request without execution"),
  (New-Check -Name "deploy_bundle_passes_local_only_and_zip_hashes" -Passed ([string]$deployBundle.result -eq "pass_local_only" -and [string]$deployBundle.lane_id -eq $laneId -and -not [bool]$deployBundle.ec2_started -and -not [bool]$deployBundle.generation_executed -and (Test-Path -LiteralPath $bundleZipPath -PathType Leaf) -and $bundleZipHash -eq ([string]$deployBundle.bundle_zip_sha256).ToLowerInvariant()) -Observed ([ordered]@{ result = $deployBundle.result; lane_id = $deployBundle.lane_id; bundle_zip_hash = $bundleZipHash; expected = $deployBundle.bundle_zip_sha256 }) -Expected "deploy bundle pass_local_only and zip SHA256 matches manifest"),
  (New-Check -Name "deploy_bundle_source_git_status_recorded" -Passed (([bool]$deployBundle.source_git_clean -and [int]$deployBundle.source_git_status_count -eq 0) -or (-not [bool]$deployBundle.source_git_clean -and [int]$deployBundle.source_git_status_count -gt 0)) -Observed ([ordered]@{ source_git_clean = $deployBundle.source_git_clean; source_git_status_count = $deployBundle.source_git_status_count; source_git_status_all_count = $deployBundle.source_git_status_all_count; source_git_status_excluded_count = $deployBundle.source_git_status_excluded_count }) -Expected "bundle records either clean scoped source or explicit dirty source blocker"),
  (New-Check -Name "runtime_requirements_match_local_object_info" -Passed ([string]$runtimeRequirements.lane_id -eq $laneId -and [string]$objectInfo.result -eq "pass_local_object_info_model_input_hash_proof" -and $missingNodes.Count -eq 0 -and @($objectInfo.object_info.missing_required_nodes).Count -eq 0) -Observed ([ordered]@{ runtime_lane = $runtimeRequirements.lane_id; object_info_result = $objectInfo.result; missing_required_nodes = $missingNodes.Count }) -Expected "runtime requirements lane matches object_info and all required nodes are present"),
  (New-Check -Name "model_hash_matches_runtime_requirement" -Passed ($modelReq.Count -eq 1 -and $modelInfo.Count -eq 1 -and [bool]$modelInfo[0].exists -and [bool]$modelInfo[0].sha256_match -and [string]$modelReq[0].sha256 -eq [string]$modelInfo[0].sha256) -Observed ([ordered]@{ required_sha256 = $modelReq[0].sha256; object_info_sha256 = $modelInfo[0].sha256; exists = $modelInfo[0].exists; sha256_match = $modelInfo[0].sha256_match }) -Expected "RealVisXL checkpoint hash matches runtime requirement and local object_info evidence"),
  (New-Check -Name "source_and_mask_assets_match_manifests" -Passed ($sourceAssetInfo.Count -eq 1 -and $maskAssetInfo.Count -eq 1 -and [bool]$sourceAssetInfo[0].sha256_match -and [bool]$maskAssetInfo[0].sha256_match -and [string]$inputAsset.source_image.sha256 -eq [string]$sourceAssetInfo[0].sha256 -and [string]$inputAsset.mask_image.sha256 -eq [string]$maskAssetInfo[0].sha256) -Observed ([ordered]@{ source_asset_hash = $sourceAssetInfo[0].sha256; manifest_source_hash = $inputAsset.source_image.sha256; mask_asset_hash = $maskAssetInfo[0].sha256; manifest_mask_hash = $inputAsset.mask_image.sha256 }) -Expected "source and mask input asset hashes match manifest and object_info evidence")
)

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$objectInfoRefreshRequired = (
  $failedChecks.Count -eq 1 -and
  [string]$failedChecks[0].name -eq "runtime_requirements_match_local_object_info"
)
$result = if ($failedChecks.Count -eq 0) {
  "pass_local_only_selected_target_runtime_lane_package_ready_ec2_blocked"
} elseif ($objectInfoRefreshRequired) {
  "blocked_selected_target_runtime_lane_package_readiness_object_info_refresh_required"
} else {
  "fail_selected_target_runtime_lane_package_readiness"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_target_runtime_lane_package_readiness"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  lane_id = $laneId
  selected_work_order_id = [string]$targetPlan.selected_work_order_id
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
  target_runtime_execution_allowed = $false
  package_readiness_pass = ($failedChecks.Count -eq 0)
  explicit_user_selection_required = [bool]$targetPlan.explicit_user_selection_required
  git_checkpoint_passes_for_ec2 = [bool]$targetPlan.git_checkpoint_summary.passes_for_ec2_execute
  source_git_clean_in_bundle = [bool]$deployBundle.source_git_clean
  run_package_manifest = ConvertTo-ProjectRelativePath -Path $runPackageResolved
  deploy_bundle_manifest = ConvertTo-ProjectRelativePath -Path $deployBundleResolved
  deploy_bundle_zip = ConvertTo-ProjectRelativePath -Path $bundleZipPath
  deploy_bundle_zip_sha256 = $bundleZipHash
  target_runtime_plan = ConvertTo-ProjectRelativePath -Path $targetPlanResolved
  runtime_requirements = ConvertTo-ProjectRelativePath -Path $runtimeRequirementsResolved
  local_object_info_evidence = ConvertTo-ProjectRelativePath -Path $localObjectInfoResolved
  input_asset_manifest = ConvertTo-ProjectRelativePath -Path $inputAssetResolved
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  exact_blockers = @(
    if ($objectInfoRefreshRequired) {
      "local_object_info_evidence_missing_runtime_required_node:MaskToImage"
    }
    if (-not [bool]$targetPlan.git_checkpoint_summary.passes_for_ec2_execute) {
      "git_checkpoint_gate_not_clean_for_ec2_execute"
    }
    if ([bool]$targetPlan.explicit_user_selection_required) {
      "explicit_user_target_runtime_selection_required"
    }
    if (-not [bool]$deployBundle.source_git_clean) {
      "deploy_bundle_source_git_dirty_rebuild_required_before_ec2"
    }
  )
  certification_boundary = "Local selected-lane package readiness only. This does not authorize or perform live upload, marker write, EC2 start, generation, target-runtime proof, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, or Wave71+ activation."
  next_action = if ($objectInfoRefreshRequired) { "Refresh local object_info evidence for the selected inpaint lane so it proves MaskToImage, then rerun this readiness packet. Keep EC2 stopped." } else { "Keep EC2 stopped. If target-runtime proof is explicitly selected later, rebuild or revalidate the bundle after a clean Git checkpoint, publish through the approved S3 path, then run EC2 static proof before any workflow smoke." }
}

$outDir = Split-Path -Path $outFileResolved -Parent
$mdDir = Split-Path -Path $markdownResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($mdDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$checkLines = foreach ($check in $checks) {
  "- $($check.name): $($check.result)"
}
$markdown = @"
# Selected Target Runtime Lane Package Readiness

- created_at: $($record.created_at)
- result: $result
- lane_id: $laneId
- selected_work_order_id: $($record.selected_work_order_id)
- package_readiness_pass: $($record.package_readiness_pass)
- target_runtime_execution_allowed: false
- full_project_certification_allowed: false
- deploy_bundle_zip_sha256: $bundleZipHash

## Checks

$($checkLines -join "`n")

## Boundary

$($record.certification_boundary)

## Evidence

- $($record.target_runtime_plan)
- $($record.run_package_manifest)
- $($record.deploy_bundle_manifest)
- $($record.local_object_info_evidence)
- $($record.input_asset_manifest)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($result -like "fail_*") { exit 2 }
exit 0
