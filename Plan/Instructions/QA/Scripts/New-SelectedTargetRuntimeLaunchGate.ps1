<#
.SYNOPSIS
Creates a local-only launch gate for the selected target-runtime lane.

.DESCRIPTION
Combines the target-runtime execution plan, selected-lane package readiness,
Git checkpoint gate, and S3 transfer readiness into one fail-closed launch
decision. This helper never contacts AWS, GitHub, Civitai, S3, ComfyUI, or EC2,
does not post prompts, does not generate images, and does not write an active
runtime marker.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$TargetRuntimePlanFile = "",
  [string]$SelectedPackageReadinessFile = "",
  [string]$GitCheckpointGateFile = "",
  [string]$S3TransferReadinessFile = "",
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

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$gitVerificationDir = Join-Path $qaRoot "Git_Verification"
$operationsStaticDir = Join-Path $qaRoot "Operations_Static_Validation"

if ([string]::IsNullOrWhiteSpace($TargetRuntimePlanFile)) {
  $TargetRuntimePlanFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($SelectedPackageReadinessFile)) {
  $SelectedPackageReadinessFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_TARGET_RUNTIME_LANE_PACKAGE_READINESS_*.json"
}
if ([string]::IsNullOrWhiteSpace($GitCheckpointGateFile)) {
  $GitCheckpointGateFile = Find-LatestFile -Directory $gitVerificationDir -Filter "W66_GITHUB_CHECKPOINT_DRY_RUN_JSON_GATE_*.json"
}
if ([string]::IsNullOrWhiteSpace($S3TransferReadinessFile)) {
  $S3TransferReadinessFile = Find-LatestFile -Directory $operationsStaticDir -Filter "W66_S3_RUNTIME_TRANSFER_READINESS_CURRENT_ACTIVE_LANES_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_TARGET_RUNTIME_LAUNCH_GATE_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$targetPlanResolved = Resolve-ProjectPath -Path $TargetRuntimePlanFile
$readinessResolved = Resolve-ProjectPath -Path $SelectedPackageReadinessFile
$gitGateResolved = Resolve-ProjectPath -Path $GitCheckpointGateFile
$s3ReadinessResolved = Resolve-ProjectPath -Path $S3TransferReadinessFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

foreach ($required in @(
  @{ label = "target_runtime_plan"; path = $targetPlanResolved },
  @{ label = "selected_package_readiness"; path = $readinessResolved },
  @{ label = "git_checkpoint_gate"; path = $gitGateResolved },
  @{ label = "s3_transfer_readiness"; path = $s3ReadinessResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$targetPlan = Read-JsonFile -Path $targetPlanResolved
$readiness = Read-JsonFile -Path $readinessResolved
$gitGate = Read-JsonFile -Path $gitGateResolved
$s3Readiness = Read-JsonFile -Path $s3ReadinessResolved

$laneId = [string]$targetPlan.selected_lane_id
$workOrderId = [string]$targetPlan.selected_work_order_id
$gitGatePasses = (
  [string]$gitGate.result -eq "pass_git_checkpoint_ready" -and
  [bool]$gitGate.clean_worktree -and
  [bool]$gitGate.local_matches_origin -and
  -not [bool]$gitGate.commit_attempted -and
  -not [bool]$gitGate.push_attempted
)
$s3ReadyLocalOnly = ([string]$s3Readiness.result -eq "ready_local_only")
$localPackageReady = (
  [string]$readiness.result -eq "pass_local_only_selected_target_runtime_lane_package_ready_ec2_blocked" -and
  [bool]$readiness.package_readiness_pass -and
  [int]$readiness.failed_check_count -eq 0
)
$explicitSelectionPresent = (-not [bool]$targetPlan.explicit_user_selection_required)
$bundleClean = [bool]$readiness.source_git_clean_in_bundle

$checks = @(
  (New-Check -Name "target_plan_still_selects_inpaint_lane" -Passed ([string]$targetPlan.result -eq "blocked_target_runtime_execution_plan_waiting_for_explicit_selection_and_clean_git" -and $laneId -eq "sdxl_realvisxl_inpaint_detail_lane" -and $workOrderId -eq "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF" -and -not [bool]$targetPlan.execute_allowed_now) -Observed ([ordered]@{ result = $targetPlan.result; lane_id = $laneId; work_order_id = $workOrderId; execute_allowed_now = $targetPlan.execute_allowed_now }) -Expected "selected inpaint target-runtime work order with execute_allowed_now=false"),
  (New-Check -Name "selected_package_readiness_passes_local_only" -Passed $localPackageReady -Observed ([ordered]@{ result = $readiness.result; package_readiness_pass = $readiness.package_readiness_pass; failed_check_count = $readiness.failed_check_count; target_runtime_execution_allowed = $readiness.target_runtime_execution_allowed }) -Expected "package readiness passes locally but does not allow target-runtime execution"),
  (New-Check -Name "local_package_uses_refreshed_masktoimage_object_info" -Passed ([string]$readiness.local_object_info_evidence -match "W66_LOCAL_OBJECT_INFO_INPAINT_DETAIL_MASKTOIMAGE_REFRESH_" -and @($readiness.exact_blockers | Where-Object { [string]$_ -eq "local_object_info_evidence_missing_runtime_required_node:MaskToImage" }).Count -eq 0) -Observed ([ordered]@{ local_object_info_evidence = $readiness.local_object_info_evidence; exact_blockers = @($readiness.exact_blockers) }) -Expected "refreshed MaskToImage object_info evidence and no stale MaskToImage blocker"),
  (New-Check -Name "s3_transfer_readiness_is_local_ready" -Passed $s3ReadyLocalOnly -Observed ([ordered]@{ result = $s3Readiness.result; local_only = $s3Readiness.local_only; aws_contacted = $s3Readiness.aws_contacted; ec2_started = $s3Readiness.ec2_started }) -Expected "S3 transfer readiness planner is ready_local_only without external contact"),
  (New-Check -Name "git_checkpoint_blocks_ec2_execute" -Passed (-not $gitGatePasses) -Observed ([ordered]@{ result = $gitGate.result; clean_worktree = $gitGate.clean_worktree; local_matches_origin = $gitGate.local_matches_origin; passes_for_ec2_execute = $gitGatePasses }) -Expected "dirty Git gate remains fail-closed for EC2"),
  (New-Check -Name "explicit_selection_blocks_launch" -Passed (-not $explicitSelectionPresent) -Observed ([ordered]@{ explicit_user_selection_required = $targetPlan.explicit_user_selection_required; execute_allowed_now = $targetPlan.execute_allowed_now }) -Expected "explicit user target-runtime selection is still required"),
  (New-Check -Name "dirty_source_bundle_blocks_launch" -Passed (-not $bundleClean) -Observed ([ordered]@{ source_git_clean_in_bundle = $readiness.source_git_clean_in_bundle; deploy_bundle_manifest = $readiness.deploy_bundle_manifest }) -Expected "deploy bundle source is dirty and must be rebuilt or revalidated from clean checkpoint")
)

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$exactBlockers = @(
  if (-not $localPackageReady) { "selected_package_readiness_not_passed" }
  if (-not $s3ReadyLocalOnly) { "s3_runtime_transfer_readiness_not_ready" }
  if (-not $gitGatePasses) { "git_checkpoint_gate_not_clean_for_ec2_execute" }
  if (-not $explicitSelectionPresent) { "explicit_user_target_runtime_selection_required" }
  if (-not $bundleClean) { "deploy_bundle_source_git_dirty_rebuild_required_before_ec2" }
)
$launchAllowed = ($exactBlockers.Count -eq 0 -and $failedChecks.Count -eq 0)
$result = if ($launchAllowed) { "pass_selected_target_runtime_launch_gate_ready_for_explicit_execute" } elseif ($localPackageReady) { "blocked_selected_target_runtime_launch_gate_package_ready_waiting_for_selection_and_clean_git" } else { "blocked_selected_target_runtime_launch_gate_package_not_ready" }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_target_runtime_launch_gate"
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
  local_package_ready = $localPackageReady
  target_runtime_launch_allowed = $launchAllowed
  explicit_user_selection_required = [bool]$targetPlan.explicit_user_selection_required
  git_checkpoint_passes_for_ec2 = $gitGatePasses
  source_git_clean_in_bundle = $bundleClean
  s3_transfer_ready_local_only = $s3ReadyLocalOnly
  target_runtime_plan = ConvertTo-ProjectRelativePath -Path $targetPlanResolved
  selected_package_readiness = ConvertTo-ProjectRelativePath -Path $readinessResolved
  local_object_info_evidence = [string]$readiness.local_object_info_evidence
  git_checkpoint_gate = ConvertTo-ProjectRelativePath -Path $gitGateResolved
  s3_transfer_readiness = ConvertTo-ProjectRelativePath -Path $s3ReadinessResolved
  deploy_bundle_manifest = [string]$readiness.deploy_bundle_manifest
  deploy_bundle_zip = [string]$readiness.deploy_bundle_zip
  deploy_bundle_zip_sha256 = [string]$readiness.deploy_bundle_zip_sha256
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  exact_blockers = @($exactBlockers | Select-Object -Unique)
  next_live_gate_sequence = @(
    "explicit_user_target_runtime_selection",
    "clean_git_checkpoint_gate",
    "rebuild_or_revalidate_deploy_bundle_from_clean_checkpoint",
    "s3_publish_proof",
    "ec2_static_proof",
    "bounded_workflow_smoke",
    "artifact_pullback_hash_qa",
    "strict_whole_image_visual_qa"
  )
  certification_boundary = "Local selected target-runtime launch gate only. This does not authorize or perform live upload, marker write, EC2 start, generation, target-runtime proof, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, or Wave71+ activation."
  next_action = "Keep EC2 stopped. If the user explicitly selects this target-runtime task later, resolve the Git checkpoint, rebuild/revalidate the deploy bundle from a clean checkpoint, publish through the approved S3 path, and then run EC2 static proof before any workflow smoke."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$checkLines = foreach ($check in $checks) {
  "- $($check.name): $($check.result)"
}
$markdown = @"
# Selected Target Runtime Launch Gate

- created_at: $($record.created_at)
- result: $result
- lane_id: $laneId
- selected_work_order_id: $workOrderId
- local_package_ready: $localPackageReady
- target_runtime_launch_allowed: $launchAllowed
- exact_blockers: $($record.exact_blockers -join ", ")

## Checks

$($checkLines -join "`n")

## Boundary

$($record.certification_boundary)

## Evidence

- $($record.target_runtime_plan)
- $($record.selected_package_readiness)
- $($record.local_object_info_evidence)
- $($record.git_checkpoint_gate)
- $($record.s3_transfer_readiness)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($result -like "fail_*") { exit 2 }
exit 0
