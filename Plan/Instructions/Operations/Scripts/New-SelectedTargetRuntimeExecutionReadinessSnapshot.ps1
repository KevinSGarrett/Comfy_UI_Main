<#
.SYNOPSIS
Creates a local-only selected target-runtime execution readiness snapshot.

.DESCRIPTION
Combines the selected target-runtime live execution runbook with the current
RealVisXL model install dry-run and selected inpaint input-asset install dry-run
evidence. This helper writes evidence only. It does not contact AWS, S3,
GitHub, Civitai, ComfyUI, or EC2; it does not rebuild deploy bundles, upload
assets or models, install remote files, start EC2, post prompts, run generation,
stage, commit, push, reset, checkout, promote masks, rerun Wave70 hard gates,
mutate Jira, or activate Wave71+.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LiveExecutionRunbookFile = "",
  [string]$ModelInstallDryRunFile = "",
  [string]$SourceInputInstallDryRunFile = "",
  [string]$MaskInputInstallDryRunFile = "",
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

function Find-LatestFile {
  param([string]$Directory, [string]$Filter)
  if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $item = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTimeUtc, Name -Descending |
    Select-Object -First 1
  if ($null -eq $item) { return $null }
  return $item.FullName
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

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function New-Proof {
  param(
    [string]$Name,
    [string]$EvidencePath,
    [object]$Payload,
    [string]$ExpectedResult
  )

  return [pscustomobject][ordered]@{
    name = $Name
    evidence_path = ConvertTo-ProjectRelativePath -Path $EvidencePath
    result = [string]$Payload.result
    expected_result = $ExpectedResult
    execute = [bool]$Payload.execute
    ec2_started = [bool]$Payload.ec2_started
    command_status = [string]$Payload.command_status
    generation_executed = [bool]$Payload.generation_executed
    git_lfs_used = [bool]$Payload.git_lfs_used
    error_count = @($Payload.errors).Count
    source_s3_uri = [string]$Payload.source_s3_uri
    remote_path = $(if ($Payload.PSObject.Properties["remote_model_path"]) { [string]$Payload.remote_model_path } else { [string]$Payload.remote_input_path })
    expected_sha256 = [string]$Payload.expected_sha256
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeDir = Join-Path $qaRoot "Runtime_Readiness"
$modelDir = Join-Path $qaRoot "Model_Registry"

if ([string]::IsNullOrWhiteSpace($LiveExecutionRunbookFile)) {
  $LiveExecutionRunbookFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_TARGET_RUNTIME_LIVE_EXECUTION_RUNBOOK_*.json"
}
if ([string]::IsNullOrWhiteSpace($ModelInstallDryRunFile)) {
  $ModelInstallDryRunFile = Find-LatestFile -Directory $modelDir -Filter "W66_SELECTED_MODEL_EC2_INSTALL_DRY_RUN_REALVISXL_*.json"
}
if ([string]::IsNullOrWhiteSpace($SourceInputInstallDryRunFile)) {
  $SourceInputInstallDryRunFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_INPUT_ASSET_INSTALL_DRY_RUN_SOURCE_*.json"
}
if ([string]::IsNullOrWhiteSpace($MaskInputInstallDryRunFile)) {
  $MaskInputInstallDryRunFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_INPUT_ASSET_INSTALL_DRY_RUN_MASK_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_TARGET_RUNTIME_EXECUTION_READINESS_SNAPSHOT_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$runbookResolved = Resolve-ProjectPath -Path $LiveExecutionRunbookFile
$modelResolved = Resolve-ProjectPath -Path $ModelInstallDryRunFile
$sourceResolved = Resolve-ProjectPath -Path $SourceInputInstallDryRunFile
$maskResolved = Resolve-ProjectPath -Path $MaskInputInstallDryRunFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

foreach ($required in @(
  @{ label = "live_execution_runbook"; path = $runbookResolved },
  @{ label = "model_install_dry_run"; path = $modelResolved },
  @{ label = "source_input_install_dry_run"; path = $sourceResolved },
  @{ label = "mask_input_install_dry_run"; path = $maskResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$runbook = Read-JsonFile -Path $runbookResolved
$modelInstall = Read-JsonFile -Path $modelResolved
$sourceInstall = Read-JsonFile -Path $sourceResolved
$maskInstall = Read-JsonFile -Path $maskResolved

$proofs = @(
  (New-Proof -Name "realvisxl_model_install_dry_run" -EvidencePath $modelResolved -Payload $modelInstall -ExpectedResult "dry_run_model_install_plan"),
  (New-Proof -Name "source_input_asset_install_dry_run" -EvidencePath $sourceResolved -Payload $sourceInstall -ExpectedResult "dry_run_input_asset_install_plan"),
  (New-Proof -Name "mask_input_asset_install_dry_run" -EvidencePath $maskResolved -Payload $maskInstall -ExpectedResult "dry_run_input_asset_install_plan")
)

$checks = @(
  (New-Check -Name "runbook_is_current_selected_lane_and_fail_closed" -Passed (
      [string]$runbook.result -eq "blocked_selected_target_runtime_live_execution_runbook_waiting_for_clean_git_and_explicit_live_intent" -and
      [string]$runbook.selected_lane_id -eq "sdxl_realvisxl_inpaint_detail_lane" -and
      [string]$runbook.selected_work_order_id -eq "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF" -and
      -not [bool]$runbook.ready_for_live_execution -and
      -not [bool]$runbook.execute_allowed_now -and
      -not [bool]$runbook.target_runtime_launch_allowed
    ) -Observed ([ordered]@{
      result = $runbook.result
      selected_lane_id = $runbook.selected_lane_id
      selected_work_order_id = $runbook.selected_work_order_id
      ready_for_live_execution = $runbook.ready_for_live_execution
      execute_allowed_now = $runbook.execute_allowed_now
      target_runtime_launch_allowed = $runbook.target_runtime_launch_allowed
    }) -Expected "selected inpaint runbook exists and remains fail-closed"),
  (New-Check -Name "runbook_has_full_ordered_path" -Passed (
      [int]$runbook.ordered_step_count -ge 17 -and
      @($runbook.ordered_live_execution_steps).Count -eq [int]$runbook.ordered_step_count -and
      @($runbook.ordered_live_execution_steps | Where-Object { [bool]$_.execute_allowed_now }).Count -eq 0
    ) -Observed ([ordered]@{
      ordered_step_count = $runbook.ordered_step_count
      observed_step_count = @($runbook.ordered_live_execution_steps).Count
      executable_step_count = @($runbook.ordered_live_execution_steps | Where-Object { [bool]$_.execute_allowed_now }).Count
    }) -Expected "runbook contains the ordered path and no currently executable steps"),
  (New-Check -Name "model_install_dry_run_is_local_only" -Passed (
      [string]$modelInstall.result -eq "dry_run_model_install_plan" -and
      -not [bool]$modelInstall.execute -and
      -not [bool]$modelInstall.ec2_started -and
      [string]$modelInstall.command_status -eq "not_started" -and
      -not [bool]$modelInstall.generation_executed -and
      -not [bool]$modelInstall.git_lfs_used -and
      @($modelInstall.errors).Count -eq 0
    ) -Observed ($proofs[0]) -Expected "RealVisXL install dry-run proves no execute/no EC2/no generation/no Git LFS/errors=0"),
  (New-Check -Name "source_input_install_dry_run_is_local_only" -Passed (
      [string]$sourceInstall.result -eq "dry_run_input_asset_install_plan" -and
      -not [bool]$sourceInstall.execute -and
      -not [bool]$sourceInstall.ec2_started -and
      [string]$sourceInstall.command_status -eq "not_started" -and
      -not [bool]$sourceInstall.generation_executed -and
      -not [bool]$sourceInstall.git_lfs_used -and
      @($sourceInstall.errors).Count -eq 0
    ) -Observed ($proofs[1]) -Expected "source input install dry-run proves no execute/no EC2/no generation/no Git LFS/errors=0"),
  (New-Check -Name "mask_input_install_dry_run_is_local_only" -Passed (
      [string]$maskInstall.result -eq "dry_run_input_asset_install_plan" -and
      -not [bool]$maskInstall.execute -and
      -not [bool]$maskInstall.ec2_started -and
      [string]$maskInstall.command_status -eq "not_started" -and
      -not [bool]$maskInstall.generation_executed -and
      -not [bool]$maskInstall.git_lfs_used -and
      @($maskInstall.errors).Count -eq 0
    ) -Observed ($proofs[2]) -Expected "mask input install dry-run proves no execute/no EC2/no generation/no Git LFS/errors=0")
)

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$exactBlockers = @(
  Convert-ToArray -Value $runbook.exact_blockers
  "selected_deploy_bundle_not_rebuilt_after_clean_checkpoint"
  "selected_s3_publish_proof_missing_for_deploy_bundle"
  "selected_input_asset_s3_publish_proof_missing_for_live_install"
  "selected_model_s3_publish_proof_missing_for_live_install"
  "explicit_live_execution_intent_required"
  "ec2_start_not_authorized"
) | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

$result = if ($failedChecks.Count -eq 0) {
  "blocked_selected_target_runtime_execution_readiness_local_proofs_complete_live_gates_closed"
} else {
  "fail_selected_target_runtime_execution_readiness_snapshot"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_target_runtime_execution_readiness_snapshot"
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
  selected_lane_id = [string]$runbook.selected_lane_id
  selected_work_order_id = [string]$runbook.selected_work_order_id
  live_execution_runbook = ConvertTo-ProjectRelativePath -Path $runbookResolved
  model_install_dry_run = ConvertTo-ProjectRelativePath -Path $modelResolved
  source_input_install_dry_run = ConvertTo-ProjectRelativePath -Path $sourceResolved
  mask_input_install_dry_run = ConvertTo-ProjectRelativePath -Path $maskResolved
  ready_for_live_execution = $false
  execute_allowed_now = $false
  target_runtime_launch_allowed = $false
  local_install_dry_run_proof_count = @($proofs).Count
  local_install_dry_run_proofs = @($proofs)
  runbook_ordered_step_count = [int]$runbook.ordered_step_count
  runbook_failed_check_count = [int]$runbook.failed_check_count
  runbook_git_local_matches_origin = [bool]$runbook.git_local_matches_origin
  runbook_ready_for_input_asset_publish = [bool]$runbook.ready_for_input_asset_publish
  runbook_ready_for_model_cache_publish = [bool]$runbook.ready_for_model_cache_publish
  runbook_ready_for_ec2_input_asset_install_execute = [bool]$runbook.ready_for_ec2_input_asset_install_execute
  runbook_ready_for_ec2_model_install_execute = [bool]$runbook.ready_for_ec2_model_install_execute
  exact_blockers = @($exactBlockers)
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  boundary = "Selected target-runtime execution readiness snapshot only. This artifact is local-only and does not rebuild deploy bundles, upload to S3, install assets or models, start EC2, post prompts, run generation, contact external services, mutate Git, consume or promote masks, rerun Wave70 hard gates, mutate Jira, or activate Wave71+."
  next_action = "Keep EC2 stopped. Future live execution still requires explicit live intent, viable clean Git/origin gate or approved release-path exception, clean selected deploy-bundle rebuild, S3 publish proof for deploy bundle/input/model assets, EC2 install hash proof, EC2 start authorization, and selected target-runtime gates."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 50) + [Environment]::NewLine, $utf8NoBom)

$proofLines = @($proofs | ForEach-Object {
  "- $($_.name): $($_.result), execute=$($_.execute), ec2_started=$($_.ec2_started), command_status=$($_.command_status), errors=$($_.error_count)"
}) -join [Environment]::NewLine
$checkLines = @($checks | ForEach-Object { "- $($_.name): $($_.result)" }) -join [Environment]::NewLine
$blockerLines = @($exactBlockers | ForEach-Object { "- $_" }) -join [Environment]::NewLine
$markdown = @"
# Selected Target Runtime Execution Readiness Snapshot

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $($record.selected_lane_id)
- selected_work_order_id: $($record.selected_work_order_id)
- ready_for_live_execution: $($record.ready_for_live_execution)
- execute_allowed_now: $($record.execute_allowed_now)
- target_runtime_launch_allowed: $($record.target_runtime_launch_allowed)
- local_install_dry_run_proof_count: $($record.local_install_dry_run_proof_count)
- failed_check_count: $($record.failed_check_count)

## Local Install Dry-Run Proofs

$proofLines

## Checks

$checkLines

## Exact Blockers

$blockerLines

## Boundary

$($record.boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 50
if ($result -like "fail_*") { exit 2 }
exit 0
