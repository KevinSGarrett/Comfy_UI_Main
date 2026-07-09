<#
.SYNOPSIS
Creates a local-only pre-EC2 handoff bundle for the selected target-runtime lane.

.DESCRIPTION
Combines the latest target-runtime execution plan, selected-lane package
readiness, selected launch gate, and package/deploy matrix into a single
machine-readable handoff. The bundle is intentionally fail-closed: it does not
contact AWS, GitHub, Civitai, S3, ComfyUI, or EC2, does not post prompts, does
not generate images, does not write ACTIVE_EC2_RUNTIME_WINDOW.json, and does
not certify target-runtime or final quality.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$TargetRuntimePlanFile = "",
  [string]$SelectedPackageReadinessFile = "",
  [string]$SelectedLaunchGateFile = "",
  [string]$PackageDeployMatrixFile = "",
  [string]$SelectedS3PublishReadinessFile = "",
  [string]$SelectedInputAssetInstallReadinessFile = "",
  [string]$SelectedModelCacheReadinessFile = "",
  [string]$SelectedModelS3PublishDryRunFile = "",
  [string]$SelectedInputAssetSourceS3PublishDryRunFile = "",
  [string]$SelectedInputAssetMaskS3PublishDryRunFile = "",
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

function Find-LatestFileExcluding {
  param([string]$Directory, [string]$Filter, [string]$ExcludePattern)
  if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $item = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Where-Object { $_.Name -notlike $ExcludePattern } |
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

function New-HandoffStep {
  param(
    [object]$SourceStep,
    [int]$Order,
    [bool]$AllowedInCurrentLocalSession
  )

  return [pscustomobject][ordered]@{
    order = $Order
    name = [string]$SourceStep.name
    gate = [string]$SourceStep.gate
    command = [string]$SourceStep.command
    expected_evidence = [string]$SourceStep.expected_evidence
    when_to_run = [string]$SourceStep.when_to_run
    source_execute_allowed_now = [bool]$SourceStep.execute_allowed_now
    allowed_in_current_local_session = $AllowedInCurrentLocalSession
  }
}

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$modelRegistryDir = Join-Path $qaRoot "Model_Registry"

if ([string]::IsNullOrWhiteSpace($TargetRuntimePlanFile)) {
  $TargetRuntimePlanFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedPackageReadinessFile)) {
  $SelectedPackageReadinessFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_TARGET_RUNTIME_LANE_PACKAGE_READINESS_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedLaunchGateFile)) {
  $SelectedLaunchGateFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_TARGET_RUNTIME_LAUNCH_GATE_*.json"
}
if ([string]::IsNullOrWhiteSpace($PackageDeployMatrixFile)) {
  $PackageDeployMatrixFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_PACKAGE_DEPLOY_MATRIX_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedS3PublishReadinessFile)) {
  $SelectedS3PublishReadinessFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_S3_PUBLISH_READINESS_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedInputAssetInstallReadinessFile)) {
  $SelectedInputAssetInstallReadinessFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_INPUT_ASSET_INSTALL_READINESS_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedModelCacheReadinessFile)) {
  $SelectedModelCacheReadinessFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_MODEL_CACHE_READINESS_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedModelS3PublishDryRunFile)) {
  $SelectedModelS3PublishDryRunFile = Find-LatestFile -Directory $modelRegistryDir -Filter "W66_SELECTED_MODEL_S3_PUBLISH_DRY_RUN_REALVISXL_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedInputAssetSourceS3PublishDryRunFile)) {
  $SelectedInputAssetSourceS3PublishDryRunFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_INPUT_ASSET_S3_PUBLISH_DRY_RUN_SOURCE_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedInputAssetMaskS3PublishDryRunFile)) {
  $SelectedInputAssetMaskS3PublishDryRunFile = Find-LatestFileExcluding -Directory $runtimeReadinessDir -Filter "W66_SELECTED_INPUT_ASSET_S3_PUBLISH_DRY_RUN_*.json" -ExcludePattern "*SOURCE*"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_TARGET_RUNTIME_PRE_EC2_HANDOFF_BUNDLE_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$targetPlanResolved = Resolve-ProjectPath -Path $TargetRuntimePlanFile
$readinessResolved = Resolve-ProjectPath -Path $SelectedPackageReadinessFile
$launchGateResolved = Resolve-ProjectPath -Path $SelectedLaunchGateFile
$matrixResolved = Resolve-ProjectPath -Path $PackageDeployMatrixFile
$s3PublishReadinessResolved = Resolve-ProjectPath -Path $SelectedS3PublishReadinessFile
$inputAssetInstallReadinessResolved = Resolve-ProjectPath -Path $SelectedInputAssetInstallReadinessFile
$modelCacheReadinessResolved = Resolve-ProjectPath -Path $SelectedModelCacheReadinessFile
$modelS3PublishDryRunResolved = Resolve-ProjectPath -Path $SelectedModelS3PublishDryRunFile
$inputAssetSourceS3PublishDryRunResolved = Resolve-ProjectPath -Path $SelectedInputAssetSourceS3PublishDryRunFile
$inputAssetMaskS3PublishDryRunResolved = Resolve-ProjectPath -Path $SelectedInputAssetMaskS3PublishDryRunFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

foreach ($required in @(
  @{ label = "target_runtime_plan"; path = $targetPlanResolved },
  @{ label = "selected_package_readiness"; path = $readinessResolved },
  @{ label = "selected_launch_gate"; path = $launchGateResolved },
  @{ label = "package_deploy_matrix"; path = $matrixResolved },
  @{ label = "selected_s3_publish_readiness"; path = $s3PublishReadinessResolved },
  @{ label = "selected_input_asset_install_readiness"; path = $inputAssetInstallReadinessResolved },
  @{ label = "selected_model_cache_readiness"; path = $modelCacheReadinessResolved },
  @{ label = "selected_model_s3_publish_dry_run"; path = $modelS3PublishDryRunResolved },
  @{ label = "selected_input_asset_source_s3_publish_dry_run"; path = $inputAssetSourceS3PublishDryRunResolved },
  @{ label = "selected_input_asset_mask_s3_publish_dry_run"; path = $inputAssetMaskS3PublishDryRunResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$targetPlan = Read-JsonFile -Path $targetPlanResolved
$readiness = Read-JsonFile -Path $readinessResolved
$launchGate = Read-JsonFile -Path $launchGateResolved
$matrix = Read-JsonFile -Path $matrixResolved
$s3PublishReadiness = Read-JsonFile -Path $s3PublishReadinessResolved
$inputAssetInstallReadiness = Read-JsonFile -Path $inputAssetInstallReadinessResolved
$modelCacheReadiness = Read-JsonFile -Path $modelCacheReadinessResolved
$modelS3PublishDryRun = Read-JsonFile -Path $modelS3PublishDryRunResolved
$inputAssetSourceS3PublishDryRun = Read-JsonFile -Path $inputAssetSourceS3PublishDryRunResolved
$inputAssetMaskS3PublishDryRun = Read-JsonFile -Path $inputAssetMaskS3PublishDryRunResolved

$laneId = [string]$targetPlan.selected_lane_id
$workOrderId = [string]$targetPlan.selected_work_order_id
$matrixRows = @(Convert-ToArray -Value $matrix.rows)
$selectedMatrixRows = @($matrixRows | Where-Object { [string]$_.lane_id -eq $laneId })
$selectedMatrixRow = if ($selectedMatrixRows.Count -gt 0) { $selectedMatrixRows[0] } else { $null }

$allowedLocalStepNames = @(
  "closure_rollup_recheck",
  "git_checkpoint_recheck",
  "runtime_unblock_handoff_recheck",
  "active_runtime_queue_local_support_recheck",
  "runtime_lane_queue_recheck",
  "model_registry_coverage_recheck"
)
$liveBlockedStepNames = @(
  "explicit_target_runtime_selection",
  "lane_runtime_readiness_recheck",
  "deploy_bundle_build",
  "deploy_bundle_s3_publish",
  "active_runtime_marker_plan_or_write",
  "ec2_static_proof_execute",
  "workflow_smoke_execute"
)

$commandSteps = @()
$index = 0
foreach ($step in @(Convert-ToArray -Value $targetPlan.command_sequence)) {
  $index += 1
  $allowed = (@($allowedLocalStepNames) -contains [string]$step.name) -and [bool]$step.execute_allowed_now
  $commandSteps += New-HandoffStep -SourceStep $step -Order $index -AllowedInCurrentLocalSession $allowed
}

$allowedLocalRecheckSteps = @($commandSteps | Where-Object { [bool]$_.allowed_in_current_local_session })
$blockedLiveSteps = @($commandSteps | Where-Object { -not [bool]$_.allowed_in_current_local_session })
$missingAllowedLocalSteps = @($allowedLocalStepNames | Where-Object { @($commandSteps.name) -notcontains $_ })
$missingLiveBlockedSteps = @($liveBlockedStepNames | Where-Object { @($commandSteps.name) -notcontains $_ })
$unexpectedAllowedLiveSteps = @($commandSteps | Where-Object { [bool]$_.allowed_in_current_local_session -and (@($liveBlockedStepNames) -contains [string]$_.name) })

$launchBlockers = @(Convert-ToArray -Value $launchGate.exact_blockers | ForEach-Object { [string]$_ })
$targetBlockers = @(Convert-ToArray -Value $targetPlan.blocker_summary | ForEach-Object { [string]$_ })
$readinessBlockers = @(Convert-ToArray -Value $readiness.exact_blockers | ForEach-Object { [string]$_ })
$matrixBlockers = @(Convert-ToArray -Value $matrix.exact_blockers | ForEach-Object { [string]$_ })
$s3PublishBlockers = @(Convert-ToArray -Value $s3PublishReadiness.blockers_before_publish | ForEach-Object { [string]$_ })
$inputAssetBlockers = @(Convert-ToArray -Value $inputAssetInstallReadiness.exact_blockers | ForEach-Object { [string]$_ })
$modelCacheBlockers = @(Convert-ToArray -Value $modelCacheReadiness.exact_blockers | ForEach-Object { [string]$_ })
$exactBlockers = @($launchBlockers + $targetBlockers + $readinessBlockers + $matrixBlockers + $s3PublishBlockers + $inputAssetBlockers + $modelCacheBlockers |
  Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
  Select-Object -Unique)

$requiredBlockers = @(
  "explicit_user_target_runtime_selection_required",
  "git_checkpoint_gate_not_clean_for_ec2_execute",
  "deploy_bundle_source_git_dirty_rebuild_required_before_ec2"
)
$missingRequiredBlockers = @($requiredBlockers | Where-Object { $exactBlockers -notcontains $_ })

$checks = @(
  (New-Check -Name "target_plan_is_latest_authority_for_selected_inpaint_lane" -Passed ([string]$targetPlan.result -eq "blocked_target_runtime_execution_plan_waiting_for_explicit_selection_and_clean_git" -and $laneId -eq "sdxl_realvisxl_inpaint_detail_lane" -and $workOrderId -eq "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF" -and -not [bool]$targetPlan.execute_allowed_now) -Observed ([ordered]@{ result = $targetPlan.result; lane_id = $laneId; work_order_id = $workOrderId; execute_allowed_now = $targetPlan.execute_allowed_now }) -Expected "latest target plan selects blocked inpaint target-runtime proof"),
  (New-Check -Name "selected_package_ready_but_execution_blocked" -Passed ([string]$readiness.lane_id -eq $laneId -and [bool]$readiness.package_readiness_pass -and -not [bool]$readiness.target_runtime_execution_allowed -and [int]$readiness.failed_check_count -eq 0) -Observed ([ordered]@{ lane_id = $readiness.lane_id; package_readiness_pass = $readiness.package_readiness_pass; target_runtime_execution_allowed = $readiness.target_runtime_execution_allowed; failed_check_count = $readiness.failed_check_count }) -Expected "selected package is locally ready but does not authorize execution"),
  (New-Check -Name "launch_gate_blocks_target_runtime_launch" -Passed ([string]$launchGate.lane_id -eq $laneId -and [bool]$launchGate.local_package_ready -and -not [bool]$launchGate.target_runtime_launch_allowed -and [int]$launchGate.failed_check_count -eq 0) -Observed ([ordered]@{ lane_id = $launchGate.lane_id; local_package_ready = $launchGate.local_package_ready; target_runtime_launch_allowed = $launchGate.target_runtime_launch_allowed; failed_check_count = $launchGate.failed_check_count }) -Expected "launch gate blocks target runtime while package is locally ready"),
  (New-Check -Name "package_deploy_matrix_has_selected_lane_dirty_bundle" -Passed ($null -ne $selectedMatrixRow -and [bool]$selectedMatrixRow.local_package_deploy_ready -and -not [bool]$selectedMatrixRow.target_runtime_launch_allowed -and -not [bool]$selectedMatrixRow.source_git_clean_in_bundle) -Observed ([ordered]@{ selected_row_found = ($null -ne $selectedMatrixRow); lane_id = if ($null -ne $selectedMatrixRow) { $selectedMatrixRow.lane_id } else { $null }; local_package_deploy_ready = if ($null -ne $selectedMatrixRow) { $selectedMatrixRow.local_package_deploy_ready } else { $null }; target_runtime_launch_allowed = if ($null -ne $selectedMatrixRow) { $selectedMatrixRow.target_runtime_launch_allowed } else { $null }; source_git_clean_in_bundle = if ($null -ne $selectedMatrixRow) { $selectedMatrixRow.source_git_clean_in_bundle } else { $null } }) -Expected "selected lane exists in package/deploy matrix with dirty source launch blocker"),
  (New-Check -Name "selected_s3_publish_waits_for_clean_rebuild" -Passed ([string]$s3PublishReadiness.result -eq "blocked_selected_s3_publish_readiness_waiting_for_clean_rebuild" -and [string]$s3PublishReadiness.selected_lane_id -eq $laneId -and [bool]$s3PublishReadiness.s3_runtime_transfer_ready_local_only -and [bool]$s3PublishReadiness.selected_rebuild_ready_after_clean_checkpoint -and -not [bool]$s3PublishReadiness.selected_rebuild_current_git_clean -and -not [bool]$s3PublishReadiness.ready_for_s3_publish_after_rebuild) -Observed ([ordered]@{ result = $s3PublishReadiness.result; selected_lane_id = $s3PublishReadiness.selected_lane_id; s3_runtime_transfer_ready_local_only = $s3PublishReadiness.s3_runtime_transfer_ready_local_only; selected_rebuild_ready_after_clean_checkpoint = $s3PublishReadiness.selected_rebuild_ready_after_clean_checkpoint; selected_rebuild_current_git_clean = $s3PublishReadiness.selected_rebuild_current_git_clean; ready_for_s3_publish_after_rebuild = $s3PublishReadiness.ready_for_s3_publish_after_rebuild }) -Expected "deploy bundle S3 publish remains blocked until clean checkpoint and clean rebuild"),
  (New-Check -Name "selected_input_assets_publish_ready_install_execute_blocked" -Passed ([string]$inputAssetInstallReadiness.result -eq "blocked_selected_input_asset_install_readiness_waiting_for_s3_publish_and_live_gates" -and [string]$inputAssetInstallReadiness.selected_lane_id -eq $laneId -and [string]$inputAssetInstallReadiness.selected_work_order_id -eq $workOrderId -and [bool]$inputAssetInstallReadiness.ready_for_input_asset_publish -and -not [bool]$inputAssetInstallReadiness.ready_for_ec2_input_asset_install_execute -and [bool]$inputAssetInstallReadiness.input_asset_local_hash_all_pass -and [int]$inputAssetInstallReadiness.required_input_asset_count -eq 2) -Observed ([ordered]@{ result = $inputAssetInstallReadiness.result; selected_lane_id = $inputAssetInstallReadiness.selected_lane_id; selected_work_order_id = $inputAssetInstallReadiness.selected_work_order_id; ready_for_input_asset_publish = $inputAssetInstallReadiness.ready_for_input_asset_publish; ready_for_ec2_input_asset_install_execute = $inputAssetInstallReadiness.ready_for_ec2_input_asset_install_execute; input_asset_local_hash_all_pass = $inputAssetInstallReadiness.input_asset_local_hash_all_pass; required_input_asset_count = $inputAssetInstallReadiness.required_input_asset_count }) -Expected "selected input assets are hash-verified and publish-ready, but EC2 install execute is blocked"),
  (New-Check -Name "selected_model_cache_publish_ready_install_execute_blocked" -Passed ([string]$modelCacheReadiness.result -eq "blocked_selected_model_cache_readiness_waiting_for_s3_publish_and_live_gates" -and [string]$modelCacheReadiness.selected_lane_id -eq $laneId -and [string]$modelCacheReadiness.selected_work_order_id -eq $workOrderId -and [bool]$modelCacheReadiness.ready_for_model_cache_publish -and -not [bool]$modelCacheReadiness.ready_for_ec2_model_install_execute -and [bool]$modelCacheReadiness.model_local_hash_all_pass_from_object_info -and [int]$modelCacheReadiness.required_model_count -eq 1) -Observed ([ordered]@{ result = $modelCacheReadiness.result; selected_lane_id = $modelCacheReadiness.selected_lane_id; selected_work_order_id = $modelCacheReadiness.selected_work_order_id; ready_for_model_cache_publish = $modelCacheReadiness.ready_for_model_cache_publish; ready_for_ec2_model_install_execute = $modelCacheReadiness.ready_for_ec2_model_install_execute; model_local_hash_all_pass_from_object_info = $modelCacheReadiness.model_local_hash_all_pass_from_object_info; required_model_count = $modelCacheReadiness.required_model_count }) -Expected "RealVisXL model cache is hash-verified and publish-ready, but EC2 install execute is blocked"),
  (New-Check -Name "selected_model_s3_dry_run_hash_verified_no_live_contact" -Passed ([string]$modelS3PublishDryRun.result -eq "dry_run_ready_to_upload_model" -and [bool]$modelS3PublishDryRun.local_hash_match -and [bool]$modelS3PublishDryRun.local_only -and -not [bool]$modelS3PublishDryRun.aws_contacted -and -not [bool]$modelS3PublishDryRun.s3_contacted -and -not [bool]$modelS3PublishDryRun.git_lfs_used -and [string]$modelS3PublishDryRun.expected_sha256 -eq [string]$modelS3PublishDryRun.observed_sha256) -Observed ([ordered]@{ result = $modelS3PublishDryRun.result; file_name = $modelS3PublishDryRun.file_name; local_only = $modelS3PublishDryRun.local_only; aws_contacted = $modelS3PublishDryRun.aws_contacted; s3_contacted = $modelS3PublishDryRun.s3_contacted; git_lfs_used = $modelS3PublishDryRun.git_lfs_used; local_hash_match = $modelS3PublishDryRun.local_hash_match; expected_sha256 = $modelS3PublishDryRun.expected_sha256; observed_sha256 = $modelS3PublishDryRun.observed_sha256 }) -Expected "RealVisXL model S3 publish dry-run is hash-verified and made no live contact"),
  (New-Check -Name "selected_input_asset_s3_dry_runs_hash_verified_no_live_contact" -Passed ([string]$inputAssetSourceS3PublishDryRun.result -eq "dry_run_ready_to_upload_input_asset" -and [string]$inputAssetMaskS3PublishDryRun.result -eq "dry_run_ready_to_upload_input_asset" -and [bool]$inputAssetSourceS3PublishDryRun.local_hash_match -and [bool]$inputAssetMaskS3PublishDryRun.local_hash_match -and [bool]$inputAssetSourceS3PublishDryRun.local_only -and [bool]$inputAssetMaskS3PublishDryRun.local_only -and -not [bool]$inputAssetSourceS3PublishDryRun.aws_contacted -and -not [bool]$inputAssetMaskS3PublishDryRun.aws_contacted -and -not [bool]$inputAssetSourceS3PublishDryRun.s3_contacted -and -not [bool]$inputAssetMaskS3PublishDryRun.s3_contacted -and [string]$inputAssetSourceS3PublishDryRun.expected_sha256 -eq [string]$inputAssetSourceS3PublishDryRun.observed_sha256 -and [string]$inputAssetMaskS3PublishDryRun.expected_sha256 -eq [string]$inputAssetMaskS3PublishDryRun.observed_sha256) -Observed ([ordered]@{ source = [ordered]@{ result = $inputAssetSourceS3PublishDryRun.result; file_name = $inputAssetSourceS3PublishDryRun.file_name; local_only = $inputAssetSourceS3PublishDryRun.local_only; aws_contacted = $inputAssetSourceS3PublishDryRun.aws_contacted; s3_contacted = $inputAssetSourceS3PublishDryRun.s3_contacted; local_hash_match = $inputAssetSourceS3PublishDryRun.local_hash_match; expected_sha256 = $inputAssetSourceS3PublishDryRun.expected_sha256; observed_sha256 = $inputAssetSourceS3PublishDryRun.observed_sha256 }; mask = [ordered]@{ result = $inputAssetMaskS3PublishDryRun.result; file_name = $inputAssetMaskS3PublishDryRun.file_name; local_only = $inputAssetMaskS3PublishDryRun.local_only; aws_contacted = $inputAssetMaskS3PublishDryRun.aws_contacted; s3_contacted = $inputAssetMaskS3PublishDryRun.s3_contacted; local_hash_match = $inputAssetMaskS3PublishDryRun.local_hash_match; expected_sha256 = $inputAssetMaskS3PublishDryRun.expected_sha256; observed_sha256 = $inputAssetMaskS3PublishDryRun.observed_sha256 } }) -Expected "both selected input asset S3 publish dry-runs are hash-verified and made no live contact"),
  (New-Check -Name "handoff_command_partition_is_fail_closed" -Passed ($missingAllowedLocalSteps.Count -eq 0 -and $missingLiveBlockedSteps.Count -eq 0 -and $unexpectedAllowedLiveSteps.Count -eq 0 -and $allowedLocalRecheckSteps.Count -eq 6 -and $blockedLiveSteps.Count -eq 7) -Observed ([ordered]@{ allowed_local_recheck_count = $allowedLocalRecheckSteps.Count; blocked_live_step_count = $blockedLiveSteps.Count; missing_allowed_local_steps = @($missingAllowedLocalSteps); missing_live_blocked_steps = @($missingLiveBlockedSteps); unexpected_allowed_live_steps = @($unexpectedAllowedLiveSteps | ForEach-Object { [string]$_.name }) }) -Expected "six local rechecks allowed and all seven live/marker/S3/EC2/generation steps blocked"),
  (New-Check -Name "required_blockers_are_preserved" -Passed ($missingRequiredBlockers.Count -eq 0) -Observed ([ordered]@{ required_blockers = @($requiredBlockers); missing_required_blockers = @($missingRequiredBlockers); exact_blockers = @($exactBlockers) }) -Expected "explicit selection, dirty Git, and dirty bundle blockers preserved")
)

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$result = if ($failedChecks.Count -eq 0) {
  "pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked"
} else {
  "fail_selected_target_runtime_pre_ec2_handoff_bundle"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_target_runtime_pre_ec2_handoff_bundle"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  lane_id = $laneId
  selected_work_order_id = $workOrderId
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  active_runtime_marker_written = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  target_runtime_launch_allowed = $false
  execute_allowed_now = $false
  target_runtime_plan = ConvertTo-ProjectRelativePath -Path $targetPlanResolved
  selected_package_readiness = ConvertTo-ProjectRelativePath -Path $readinessResolved
  selected_launch_gate = ConvertTo-ProjectRelativePath -Path $launchGateResolved
  package_deploy_matrix = ConvertTo-ProjectRelativePath -Path $matrixResolved
  selected_s3_publish_readiness = ConvertTo-ProjectRelativePath -Path $s3PublishReadinessResolved
  selected_input_asset_install_readiness = ConvertTo-ProjectRelativePath -Path $inputAssetInstallReadinessResolved
  selected_model_cache_readiness = ConvertTo-ProjectRelativePath -Path $modelCacheReadinessResolved
  selected_model_s3_publish_dry_run = ConvertTo-ProjectRelativePath -Path $modelS3PublishDryRunResolved
  selected_input_asset_source_s3_publish_dry_run = ConvertTo-ProjectRelativePath -Path $inputAssetSourceS3PublishDryRunResolved
  selected_input_asset_mask_s3_publish_dry_run = ConvertTo-ProjectRelativePath -Path $inputAssetMaskS3PublishDryRunResolved
  run_package_manifest = [string]$readiness.run_package_manifest
  deploy_bundle_manifest = [string]$readiness.deploy_bundle_manifest
  deploy_bundle_zip = [string]$readiness.deploy_bundle_zip
  deploy_bundle_zip_sha256 = [string]$readiness.deploy_bundle_zip_sha256
  local_object_info_evidence = [string]$readiness.local_object_info_evidence
  ready_for_s3_publish_after_rebuild = [bool]$s3PublishReadiness.ready_for_s3_publish_after_rebuild
  ready_for_input_asset_publish = [bool]$inputAssetInstallReadiness.ready_for_input_asset_publish
  ready_for_ec2_input_asset_install_execute = [bool]$inputAssetInstallReadiness.ready_for_ec2_input_asset_install_execute
  ready_for_model_cache_publish = [bool]$modelCacheReadiness.ready_for_model_cache_publish
  ready_for_ec2_model_install_execute = [bool]$modelCacheReadiness.ready_for_ec2_model_install_execute
  selected_input_asset_count = [int]$inputAssetInstallReadiness.required_input_asset_count
  selected_model_cache_count = [int]$modelCacheReadiness.required_model_count
  exact_blockers = @($exactBlockers)
  allowed_local_recheck_step_count = $allowedLocalRecheckSteps.Count
  blocked_live_step_count = $blockedLiveSteps.Count
  allowed_local_recheck_steps = @($allowedLocalRecheckSteps)
  blocked_live_steps = @($blockedLiveSteps)
  command_steps = @($commandSteps)
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  handoff_boundary = "Local pre-EC2 handoff bundle only. Allowed local rechecks are listed, but live upload, S3 publish with Execute, marker write, EC2 start, prompt post, generation, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, and Wave71+ activation remain blocked."
  next_action = "Keep EC2 stopped. Use this bundle as the selected inpaint target-runtime handoff anchor only after explicit live-window selection; then rerun the allowed local rechecks, require a clean Git checkpoint, rebuild or revalidate the deploy bundle from that clean checkpoint, publish the selected deploy bundle, input assets, and RealVisXL model through explicit Execute-only S3 steps, and proceed to EC2 install/launch only after all live gates pass."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$checkLines = foreach ($check in $checks) {
  "- $($check.name): $($check.result)"
}
$localStepLines = foreach ($step in $allowedLocalRecheckSteps) {
  "- $($step.order). $($step.name)"
}
$blockedStepLines = foreach ($step in $blockedLiveSteps) {
  "- $($step.order). $($step.name)"
}
$markdown = @"
# Selected Target Runtime Pre-EC2 Handoff Bundle

- created_at: $($record.created_at)
- result: $result
- lane_id: $laneId
- selected_work_order_id: $workOrderId
- target_runtime_launch_allowed: false
- execute_allowed_now: false
- ready_for_s3_publish_after_rebuild: $($record.ready_for_s3_publish_after_rebuild)
- ready_for_input_asset_publish: $($record.ready_for_input_asset_publish)
- ready_for_ec2_input_asset_install_execute: $($record.ready_for_ec2_input_asset_install_execute)
- ready_for_model_cache_publish: $($record.ready_for_model_cache_publish)
- ready_for_ec2_model_install_execute: $($record.ready_for_ec2_model_install_execute)
- allowed_local_recheck_step_count: $($record.allowed_local_recheck_step_count)
- blocked_live_step_count: $($record.blocked_live_step_count)
- exact_blockers: $($record.exact_blockers -join ", ")

## Allowed Local Rechecks

$($localStepLines -join "`n")

## Blocked Live Steps

$($blockedStepLines -join "`n")

## Checks

$($checkLines -join "`n")

## Boundary

$($record.handoff_boundary)

## Evidence

- $($record.target_runtime_plan)
- $($record.selected_package_readiness)
- $($record.selected_launch_gate)
- $($record.package_deploy_matrix)
- $($record.selected_s3_publish_readiness)
- $($record.selected_input_asset_install_readiness)
- $($record.selected_model_cache_readiness)
- $($record.selected_model_s3_publish_dry_run)
- $($record.selected_input_asset_source_s3_publish_dry_run)
- $($record.selected_input_asset_mask_s3_publish_dry_run)
- $($record.run_package_manifest)
- $($record.deploy_bundle_manifest)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($result -like "fail_*") { exit 2 }
exit 0
