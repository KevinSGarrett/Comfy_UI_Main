<#
.SYNOPSIS
Creates a local-only selected target-runtime live execution runbook.

.DESCRIPTION
Combines the selected deploy-bundle S3 publish readiness plan, selected input
asset install readiness plan, selected model-cache readiness plan, pre-EC2
handoff bundle, and project readiness snapshot into one ordered runbook for the
selected inpaint target-runtime path. This helper writes evidence only. It does
not contact AWS, S3, GitHub, Civitai, ComfyUI, or EC2; it does not rebuild
deploy bundles, upload assets or models, install remote files, start EC2, post
prompts, run generation, stage, commit, push, reset, checkout, promote masks,
rerun Wave70 hard gates, mutate Jira, or activate Wave71+.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$SelectedS3PublishReadinessFile = "",
  [string]$SelectedInputAssetInstallReadinessFile = "",
  [string]$SelectedModelCacheReadinessFile = "",
  [string]$PreEC2HandoffBundleFile = "",
  [string]$ProjectReadinessSnapshotFile = "",
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

function New-RunbookStep {
  param(
    [int]$Order,
    [string]$Name,
    [string]$Phase,
    [string]$Command,
    [string]$CommandSource,
    [bool]$RequiresExplicitIntent,
    [bool]$ExternalContact
  )

  return [pscustomobject][ordered]@{
    order = $Order
    name = $Name
    phase = $Phase
    command = $Command
    command_source = $CommandSource
    requires_explicit_intent = $RequiresExplicitIntent
    external_contact = $ExternalContact
    execute_allowed_now = $false
    mutates_git = $false
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeDir = Join-Path $qaRoot "Runtime_Readiness"

if ([string]::IsNullOrWhiteSpace($SelectedS3PublishReadinessFile)) {
  $SelectedS3PublishReadinessFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_S3_PUBLISH_READINESS_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedInputAssetInstallReadinessFile)) {
  $SelectedInputAssetInstallReadinessFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_INPUT_ASSET_INSTALL_READINESS_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedModelCacheReadinessFile)) {
  $SelectedModelCacheReadinessFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_MODEL_CACHE_READINESS_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($PreEC2HandoffBundleFile)) {
  $PreEC2HandoffBundleFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_TARGET_RUNTIME_PRE_EC2_HANDOFF_BUNDLE_*.json"
}
if ([string]::IsNullOrWhiteSpace($ProjectReadinessSnapshotFile)) {
  $ProjectReadinessSnapshotFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_PROJECT_READINESS_SNAPSHOT_SELECTED_INPAINT_*.json"
}
if ([string]::IsNullOrWhiteSpace($ProjectReadinessSnapshotFile)) {
  $ProjectReadinessSnapshotFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_PROJECT_READINESS_SNAPSHOT_AFTER_GIT_DIVERGENCE_WARNING_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_TARGET_RUNTIME_LIVE_EXECUTION_RUNBOOK_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$s3Resolved = Resolve-ProjectPath -Path $SelectedS3PublishReadinessFile
$inputResolved = Resolve-ProjectPath -Path $SelectedInputAssetInstallReadinessFile
$modelResolved = Resolve-ProjectPath -Path $SelectedModelCacheReadinessFile
$handoffResolved = Resolve-ProjectPath -Path $PreEC2HandoffBundleFile
$snapshotResolved = Resolve-ProjectPath -Path $ProjectReadinessSnapshotFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

foreach ($required in @(
  @{ label = "selected_s3_publish_readiness"; path = $s3Resolved },
  @{ label = "selected_input_asset_install_readiness"; path = $inputResolved },
  @{ label = "selected_model_cache_readiness"; path = $modelResolved },
  @{ label = "pre_ec2_handoff_bundle"; path = $handoffResolved },
  @{ label = "project_readiness_snapshot"; path = $snapshotResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$s3Plan = Read-JsonFile -Path $s3Resolved
$inputPlan = Read-JsonFile -Path $inputResolved
$modelPlan = Read-JsonFile -Path $modelResolved
$handoff = Read-JsonFile -Path $handoffResolved
$snapshot = Read-JsonFile -Path $snapshotResolved
$s3PublishDryRunReady = (
  [string]$s3Plan.result -eq "pass_local_only_selected_s3_publish_readiness_dry_run_ready_execute_blocked" -and
  [bool]$s3Plan.ready_for_s3_publish_now_local_dry_run -and
  -not [bool]$s3Plan.s3_upload_execute_allowed
)
$s3PublishWaitingForRebuild = (
  [string]$s3Plan.result -eq "blocked_selected_s3_publish_readiness_waiting_for_clean_rebuild" -and
  -not [bool]$s3Plan.ready_for_s3_publish_after_rebuild
)

$laneId = [string]$handoff.lane_id
if ([string]::IsNullOrWhiteSpace($laneId)) { $laneId = [string]$inputPlan.selected_lane_id }
$workOrderId = [string]$handoff.selected_work_order_id
if ([string]::IsNullOrWhiteSpace($workOrderId)) { $workOrderId = [string]$inputPlan.selected_work_order_id }

$steps = @()
$order = 0
function Add-Step {
  param(
    [string]$Name,
    [string]$Phase,
    [string]$Command,
    [string]$CommandSource,
    [bool]$RequiresExplicitIntent,
    [bool]$ExternalContact
  )
  $script:order += 1
  $script:steps += New-RunbookStep -Order $script:order -Name $Name -Phase $Phase -Command $Command -CommandSource $CommandSource -RequiresExplicitIntent $RequiresExplicitIntent -ExternalContact $ExternalContact
}

Add-Step -Name "pre_ec2_handoff_recheck" -Phase "local_recheck" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-SelectedTargetRuntimePreEC2HandoffBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_TARGET_RUNTIME_PRE_EC2_HANDOFF_BUNDLE_<timestamp>.json" -CommandSource "runbook" -RequiresExplicitIntent $false -ExternalContact $false
Add-Step -Name "project_readiness_snapshot_recheck" -Phase "local_recheck" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-ProjectReadinessSnapshot.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $laneId -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_PROJECT_READINESS_SNAPSHOT_<timestamp>.json" -CommandSource "runbook" -RequiresExplicitIntent $false -ExternalContact $false
Add-Step -Name "manifest_scoped_checkpoint_execute_blocked" -Phase "git_checkpoint" -Command "Remain blocked until the user explicitly selects a checkpoint attempt and the Git/LFS remote gate is viable." -CommandSource "runbook" -RequiresExplicitIntent $true -ExternalContact $true
Add-Step -Name "selected_deploy_bundle_rebuild_after_clean_checkpoint" -Phase "deploy_bundle" -Command ([string]$s3Plan.selected_rebuild_command) -CommandSource "selected_s3_publish_readiness.selected_rebuild_command" -RequiresExplicitIntent $true -ExternalContact $false
Add-Step -Name "selected_deploy_bundle_s3_publish_dry_run" -Phase "deploy_bundle_s3" -Command ([string]$s3Plan.publish_dry_run_command) -CommandSource "selected_s3_publish_readiness.publish_dry_run_command" -RequiresExplicitIntent $false -ExternalContact $false
Add-Step -Name "selected_deploy_bundle_s3_publish_execute_after_explicit_intent" -Phase "deploy_bundle_s3" -Command ([string]$s3Plan.publish_execute_command_requires_explicit_user_intent) -CommandSource "selected_s3_publish_readiness.publish_execute_command_requires_explicit_user_intent" -RequiresExplicitIntent $true -ExternalContact $true

foreach ($asset in @(Convert-ToArray -Value $inputPlan.input_asset_plans)) {
  Add-Step -Name "input_asset_publish_dry_run:$($asset.filename)" -Phase "input_asset_s3" -Command ([string]$asset.publish_dry_run_command) -CommandSource "selected_input_asset_install_readiness.input_asset_plans.publish_dry_run_command" -RequiresExplicitIntent $false -ExternalContact $false
}
foreach ($asset in @(Convert-ToArray -Value $inputPlan.input_asset_plans)) {
  Add-Step -Name "input_asset_publish_execute_after_explicit_intent:$($asset.filename)" -Phase "input_asset_s3" -Command ([string]$asset.publish_execute_command_requires_explicit_user_intent) -CommandSource "selected_input_asset_install_readiness.input_asset_plans.publish_execute_command_requires_explicit_user_intent" -RequiresExplicitIntent $true -ExternalContact $true
}

foreach ($model in @(Convert-ToArray -Value $modelPlan.model_cache_plans)) {
  Add-Step -Name "model_cache_publish_dry_run:$($model.filename)" -Phase "model_cache_s3" -Command ([string]$model.publish_dry_run_command) -CommandSource "selected_model_cache_readiness.model_cache_plans.publish_dry_run_command" -RequiresExplicitIntent $false -ExternalContact $false
}
foreach ($model in @(Convert-ToArray -Value $modelPlan.model_cache_plans)) {
  Add-Step -Name "model_cache_publish_execute_after_explicit_intent:$($model.filename)" -Phase "model_cache_s3" -Command ([string]$model.publish_execute_command_requires_explicit_user_intent) -CommandSource "selected_model_cache_readiness.model_cache_plans.publish_execute_command_requires_explicit_user_intent" -RequiresExplicitIntent $true -ExternalContact $true
}
foreach ($model in @(Convert-ToArray -Value $modelPlan.model_cache_plans)) {
  Add-Step -Name "model_install_dry_run:$($model.filename)" -Phase "ec2_model_install" -Command ([string]$model.install_dry_run_command) -CommandSource "selected_model_cache_readiness.model_cache_plans.install_dry_run_command" -RequiresExplicitIntent $false -ExternalContact $false
}
foreach ($model in @(Convert-ToArray -Value $modelPlan.model_cache_plans)) {
  Add-Step -Name "model_install_execute_after_live_gates:$($model.filename)" -Phase "ec2_model_install" -Command ([string]$model.install_execute_command_requires_explicit_user_intent) -CommandSource "selected_model_cache_readiness.model_cache_plans.install_execute_command_requires_explicit_user_intent" -RequiresExplicitIntent $true -ExternalContact $true
}

foreach ($asset in @(Convert-ToArray -Value $inputPlan.input_asset_plans)) {
  Add-Step -Name "input_asset_install_dry_run:$($asset.filename)" -Phase "ec2_input_asset_install" -Command ([string]$asset.install_dry_run_command) -CommandSource "selected_input_asset_install_readiness.input_asset_plans.install_dry_run_command" -RequiresExplicitIntent $false -ExternalContact $false
}
foreach ($asset in @(Convert-ToArray -Value $inputPlan.input_asset_plans)) {
  Add-Step -Name "input_asset_install_execute_after_live_gates:$($asset.filename)" -Phase "ec2_input_asset_install" -Command ([string]$asset.install_execute_command_requires_explicit_user_intent) -CommandSource "selected_input_asset_install_readiness.input_asset_plans.install_execute_command_requires_explicit_user_intent" -RequiresExplicitIntent $true -ExternalContact $true
}

$handoffSteps = @(Convert-ToArray -Value $handoff.blocked_live_steps)
$ec2Static = $handoffSteps | Where-Object { [string]$_.name -eq "ec2_static_proof_execute" } | Select-Object -First 1
$workflowSmoke = $handoffSteps | Where-Object { [string]$_.name -eq "workflow_smoke_execute" } | Select-Object -First 1
Add-Step -Name "ec2_static_proof_execute_blocked" -Phase "ec2_static_proof" -Command ([string]$ec2Static.command) -CommandSource "pre_ec2_handoff.blocked_live_steps.ec2_static_proof_execute" -RequiresExplicitIntent $true -ExternalContact $true
Add-Step -Name "workflow_smoke_execute_blocked" -Phase "workflow_smoke" -Command ([string]$workflowSmoke.command) -CommandSource "pre_ec2_handoff.blocked_live_steps.workflow_smoke_execute" -RequiresExplicitIntent $true -ExternalContact $true

$allBlockers = @(
  Convert-ToArray -Value $handoff.exact_blockers
  Convert-ToArray -Value $s3Plan.blockers_before_publish
  Convert-ToArray -Value $inputPlan.exact_blockers
  Convert-ToArray -Value $modelPlan.exact_blockers
  $(if (-not [bool]$snapshot.local_ready) { "selected_project_readiness_snapshot_not_local_ready" } else { $null })
  $(if (-not [bool]$snapshot.local_ready) { "selected_project_readiness_local_ready_false" } else { $null })
  Convert-ToArray -Value $snapshot.errors
  "explicit_live_execution_intent_required"
  "live_s3_uploads_not_authorized"
  "ec2_start_not_authorized"
) | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
if ($s3PublishDryRunReady) {
  $supersededDeployBundleBlockers = @(
    "deploy_bundle_source_git_dirty_rebuild_required_before_ec2",
    "manifest_scoped_checkpoint_not_yet_executed_clean",
    "selected_deploy_bundle_rebuild_not_completed",
    "selected_deploy_bundle_manifest_missing_until_rebuild",
    "selected_deploy_bundle_zip_missing_until_rebuild"
  )
  $allBlockers = @($allBlockers | Where-Object { $supersededDeployBundleBlockers -notcontains [string]$_ })
}
$gitCheckpointStillBlocked = @($allBlockers | Where-Object { [string]$_ -eq "git_checkpoint_gate_not_clean_for_ec2_execute" }).Count -gt 0
$projectReadinessStaticReady = (
  [string]$snapshot.result -eq "pass_local_ready_for_ec2_static_proof" -and
  [bool]$snapshot.runtime_gates.ec2_start_allowed -and
  [string]$snapshot.failure_category -eq "missing_ec2_static_proof"
)
$projectReadinessRuntimeBlocked = (
  [string]$snapshot.result -in @("pass_local_ready_runtime_blocked", "pass_local_ready_runtime_blocked_auth") -and
  -not [bool]$snapshot.runtime_gates.ec2_start_allowed -and
  [string]$snapshot.failure_category -eq "expired_session"
)

$checks = @(
  (New-Check -Name "pre_ec2_handoff_passes_and_blocks_execution" -Passed ([string]$handoff.result -eq "pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked" -and -not [bool]$handoff.target_runtime_launch_allowed -and -not [bool]$handoff.execute_allowed_now) -Observed ([ordered]@{ result = $handoff.result; target_runtime_launch_allowed = $handoff.target_runtime_launch_allowed; execute_allowed_now = $handoff.execute_allowed_now }) -Expected "pre-EC2 handoff passes locally while blocking launch and execute"),
  (New-Check -Name "project_readiness_snapshot_targets_selected_lane_and_is_fail_closed" -Passed ([string]$snapshot.lane_id -eq $laneId -and [bool]$snapshot.local_ready -and ($projectReadinessStaticReady -or $projectReadinessRuntimeBlocked) -and -not [bool]$snapshot.runtime_gates.generation_allowed -and [string]$snapshot.git.result -eq "pass") -Observed ([ordered]@{ result = $snapshot.result; failure_category = $snapshot.failure_category; lane_id = $snapshot.lane_id; local_ready = $snapshot.local_ready; ec2_start_allowed = $snapshot.runtime_gates.ec2_start_allowed; generation_allowed = $snapshot.runtime_gates.generation_allowed; git_result = $snapshot.git.result; git_local_matches_origin = $snapshot.git.local_matches_origin; errors = @($snapshot.errors); warnings = @($snapshot.warnings) }) -Expected "selected project readiness snapshot targets selected lane, is local-ready, and is either static-proof-ready or correctly fail-closed by expired auth while generation remains blocked"),
  (New-Check -Name "selected_s3_publish_is_fail_closed_local_state" -Passed ($s3PublishWaitingForRebuild -or $s3PublishDryRunReady) -Observed ([ordered]@{ result = $s3Plan.result; ready_for_s3_publish_after_rebuild = $s3Plan.ready_for_s3_publish_after_rebuild; ready_for_s3_publish_now_local_dry_run = $s3Plan.ready_for_s3_publish_now_local_dry_run; s3_upload_execute_allowed = $s3Plan.s3_upload_execute_allowed }) -Expected "deploy bundle S3 publish is either waiting for rebuild or locally dry-run ready with upload execute blocked"),
  (New-Check -Name "input_assets_publish_ready_but_install_blocked" -Passed ([bool]$inputPlan.ready_for_input_asset_publish -and -not [bool]$inputPlan.ready_for_ec2_input_asset_install_execute -and [int]$inputPlan.required_input_asset_count -eq 2) -Observed ([ordered]@{ ready_for_input_asset_publish = $inputPlan.ready_for_input_asset_publish; ready_for_ec2_input_asset_install_execute = $inputPlan.ready_for_ec2_input_asset_install_execute; required_input_asset_count = $inputPlan.required_input_asset_count }) -Expected "input assets are locally publish-ready but EC2 install execute is blocked"),
  (New-Check -Name "model_cache_publish_ready_but_install_blocked" -Passed ([bool]$modelPlan.ready_for_model_cache_publish -and -not [bool]$modelPlan.ready_for_ec2_model_install_execute -and [int]$modelPlan.required_model_count -eq 1) -Observed ([ordered]@{ ready_for_model_cache_publish = $modelPlan.ready_for_model_cache_publish; ready_for_ec2_model_install_execute = $modelPlan.ready_for_ec2_model_install_execute; required_model_count = $modelPlan.required_model_count }) -Expected "model cache is locally publish-ready but EC2 install execute is blocked"),
  (New-Check -Name "runbook_sequence_is_complete_and_fail_closed" -Passed (@($steps).Count -ge 17 -and @($steps | Where-Object { [bool]$_.execute_allowed_now }).Count -eq 0 -and @($steps.name) -contains "ec2_static_proof_execute_blocked" -and @($steps.name) -contains "workflow_smoke_execute_blocked") -Observed ([ordered]@{ step_count = @($steps).Count; execute_allowed_now_count = @($steps | Where-Object { [bool]$_.execute_allowed_now }).Count; step_names = @($steps.name) }) -Expected "runbook has the selected live path and no currently executable live steps")
)

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$result = if ($failedChecks.Count -eq 0) {
  if ($gitCheckpointStillBlocked) {
    "blocked_selected_target_runtime_live_execution_runbook_waiting_for_clean_git_and_explicit_live_intent"
  } else {
    "blocked_selected_target_runtime_live_execution_runbook_waiting_for_explicit_live_intent"
  }
} else {
  "fail_selected_target_runtime_live_execution_runbook"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_target_runtime_live_execution_runbook"
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
  s3_upload_attempted = $false
  model_install_attempted = $false
  input_asset_install_attempted = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  jira_mutated = $false
  full_project_certification_allowed = $false
  selected_lane_id = $laneId
  selected_work_order_id = $workOrderId
  selected_s3_publish_readiness = ConvertTo-ProjectRelativePath -Path $s3Resolved
  selected_input_asset_install_readiness = ConvertTo-ProjectRelativePath -Path $inputResolved
  selected_model_cache_readiness = ConvertTo-ProjectRelativePath -Path $modelResolved
  pre_ec2_handoff_bundle = ConvertTo-ProjectRelativePath -Path $handoffResolved
  project_readiness_snapshot = ConvertTo-ProjectRelativePath -Path $snapshotResolved
  project_readiness_result = [string]$snapshot.result
  project_readiness_failure_category = [string]$snapshot.failure_category
  project_readiness_errors = @(Convert-ToArray -Value $snapshot.errors)
  project_readiness_warnings = @(Convert-ToArray -Value $snapshot.warnings)
  project_local_ready = [bool]$snapshot.local_ready
  git_local_matches_origin = [bool]$snapshot.git.local_matches_origin
  ready_for_live_execution = $false
  ready_for_s3_publish_after_rebuild = [bool]$s3Plan.ready_for_s3_publish_after_rebuild
  ready_for_s3_publish_now_local_dry_run = [bool]$s3Plan.ready_for_s3_publish_now_local_dry_run
  selected_deploy_bundle_s3_publish_dry_run_ready = [bool]$s3Plan.selected_deploy_bundle_s3_publish_dry_run_ready
  selected_deploy_bundle_s3_upload_execute_allowed = [bool]$s3Plan.s3_upload_execute_allowed
  ready_for_input_asset_publish = [bool]$inputPlan.ready_for_input_asset_publish
  ready_for_ec2_input_asset_install_execute = [bool]$inputPlan.ready_for_ec2_input_asset_install_execute
  ready_for_model_cache_publish = [bool]$modelPlan.ready_for_model_cache_publish
  ready_for_ec2_model_install_execute = [bool]$modelPlan.ready_for_ec2_model_install_execute
  target_runtime_launch_allowed = [bool]$handoff.target_runtime_launch_allowed
  execute_allowed_now = $false
  exact_blockers = @($allBlockers)
  ordered_live_execution_steps = @($steps)
  ordered_step_count = @($steps).Count
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  boundary = "Selected target-runtime live execution runbook only. This artifact is local-only and does not rebuild deploy bundles, upload to S3, install assets or models, start EC2, post prompts, run generation, contact external services, mutate Git, consume or promote masks, rerun Wave70 hard gates, mutate Jira, or activate Wave71+."
  next_action = $(if ($s3PublishDryRunReady) { "Keep EC2 stopped. The selected deploy bundle is locally dry-run ready for S3, but actual upload, input/model publish, EC2 install, and runtime proof still require explicit live execution intent and live gates." } else { "Keep EC2 stopped. Use this runbook only after explicit live-window selection, viable clean Git/origin gate, clean selected deploy-bundle rebuild, S3 publish proof for bundle/input/model assets, EC2 install hash proof, and selected target-runtime gates pass." })
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 50) + [Environment]::NewLine, $utf8NoBom)

$stepLines = @($steps | ForEach-Object {
  "- $($_.order). $($_.name) [$($_.phase)] execute_allowed_now=$($_.execute_allowed_now)"
}) -join [Environment]::NewLine
$checkLines = @($checks | ForEach-Object { "- $($_.name): $($_.result)" }) -join [Environment]::NewLine
$markdown = @"
# Selected Target Runtime Live Execution Runbook

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $($record.selected_lane_id)
- selected_work_order_id: $($record.selected_work_order_id)
- ready_for_live_execution: $($record.ready_for_live_execution)
- ready_for_s3_publish_now_local_dry_run: $($record.ready_for_s3_publish_now_local_dry_run)
- git_local_matches_origin: $($record.git_local_matches_origin)
- ordered_step_count: $($record.ordered_step_count)
- failed_check_count: $($record.failed_check_count)

## Ordered Steps

$stepLines

## Checks

$checkLines

## Boundary

$($record.boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 50
if ($result -like "fail_*") { exit 2 }
exit 0
