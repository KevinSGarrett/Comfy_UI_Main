<#
.SYNOPSIS
Creates a local-only post-checkpoint runtime revalidation plan.

.DESCRIPTION
Consumes the scoped checkpoint manifest, manifest-based checkpoint dry-run,
active runtime package/deploy matrix, and target-runtime execution plan. It
emits the exact gate sequence to run after the manifest-scoped checkpoint is
explicitly selected and completed. The helper writes evidence only; it never
stages, commits, pushes, resets, checks out, contacts services, rebuilds deploy
bundles, uploads to S3, starts EC2, posts prompts, writes runtime markers, or
generates images.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ScopedCheckpointManifestFile = "",
  [string]$ManifestCheckpointDryRunFile = "",
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

function New-CommandStep {
  param(
    [string]$Name,
    [string]$Gate,
    [string]$Command,
    [string]$ExpectedEvidence,
    [string]$WhenToRun,
    [bool]$ExecuteAllowedNow = $false
  )

  return [pscustomobject][ordered]@{
    name = $Name
    gate = $Gate
    command = $Command
    expected_evidence = $ExpectedEvidence
    when_to_run = $WhenToRun
    execute_allowed_now = $ExecuteAllowedNow
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$gitDir = Join-Path $qaRoot "Git_Verification"
$runtimeDir = Join-Path $qaRoot "Runtime_Readiness"

if ([string]::IsNullOrWhiteSpace($ScopedCheckpointManifestFile)) {
  $ScopedCheckpointManifestFile = Find-LatestFile -Directory $gitDir -Filter "W66_SCOPED_GIT_CHECKPOINT_MANIFEST_*.json"
}
if ([string]::IsNullOrWhiteSpace($ManifestCheckpointDryRunFile)) {
  $ManifestCheckpointDryRunFile = Find-LatestFile -Directory $gitDir -Filter "W66_GITHUB_CHECKPOINT_MANIFEST_SCOPE_DRY_RUN_*.json"
}
if ([string]::IsNullOrWhiteSpace($PackageDeployMatrixFile)) {
  $PackageDeployMatrixFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_PACKAGE_DEPLOY_MATRIX_*.json"
}
if ([string]::IsNullOrWhiteSpace($TargetRuntimeExecutionPlanFile)) {
  $TargetRuntimeExecutionPlanFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_POST_CHECKPOINT_RUNTIME_REVALIDATION_PLAN_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$manifestResolved = Resolve-ProjectPath -Path $ScopedCheckpointManifestFile
$dryRunResolved = Resolve-ProjectPath -Path $ManifestCheckpointDryRunFile
$packageMatrixResolved = Resolve-ProjectPath -Path $PackageDeployMatrixFile
$targetPlanResolved = Resolve-ProjectPath -Path $TargetRuntimeExecutionPlanFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

foreach ($required in @(
  @{ label = "scoped_checkpoint_manifest"; path = $manifestResolved },
  @{ label = "manifest_checkpoint_dry_run"; path = $dryRunResolved },
  @{ label = "package_deploy_matrix"; path = $packageMatrixResolved },
  @{ label = "target_runtime_execution_plan"; path = $targetPlanResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$manifest = Read-JsonFile -Path $manifestResolved
$dryRun = Read-JsonFile -Path $dryRunResolved
$packageMatrix = Read-JsonFile -Path $packageMatrixResolved
$targetPlan = Read-JsonFile -Path $targetPlanResolved

$selectedLaneId = [string]$targetPlan.selected_lane_id
if ([string]::IsNullOrWhiteSpace($selectedLaneId)) { $selectedLaneId = "unknown_selected_lane" }
$selectedPackageRow = @(Convert-ToArray -Value $packageMatrix.rows | Where-Object { [string]$_.lane_id -eq $selectedLaneId } | Select-Object -First 1)
$selectedPackageReady = ($selectedPackageRow.Count -gt 0 -and [bool]$selectedPackageRow[0].local_package_deploy_ready)
$selectedBundleDirty = ($selectedPackageRow.Count -gt 0 -and -not [bool]$selectedPackageRow[0].source_git_clean_in_bundle)

$manifestReady = ([string]$manifest.result -eq "scoped_git_checkpoint_manifest_ready_pending_explicit_intent" -and [bool]$manifest.ready_for_checkpoint_execute_after_explicit_intent)
$manifestDryRunValid = ([string]$dryRun.checkpoint_scope_mode -eq "explicit_manifest" -and [bool]$dryRun.checkpoint_scope_manifest_valid)
$manifestDryRunNonMutating = (-not [bool]$dryRun.stage_attempted -and -not [bool]$dryRun.commit_attempted -and -not [bool]$dryRun.push_attempted -and -not [bool]$dryRun.reset_attempted -and -not [bool]$dryRun.checkout_attempted)
$cleanGitAfterCheckpoint = ([string]$dryRun.result -eq "pass_git_checkpoint_ready" -and [bool]$dryRun.clean_worktree -and [bool]$dryRun.local_matches_origin)

$blockers = New-Object System.Collections.Generic.List[string]
if (-not $manifestReady) { [void]$blockers.Add("scoped_checkpoint_manifest_not_ready") }
if (-not $manifestDryRunValid) { [void]$blockers.Add("manifest_checkpoint_dry_run_not_valid") }
if (-not $manifestDryRunNonMutating) { [void]$blockers.Add("manifest_checkpoint_dry_run_mutated_git") }
if (-not $cleanGitAfterCheckpoint) { [void]$blockers.Add("manifest_scoped_checkpoint_not_yet_executed_clean") }
if ($selectedBundleDirty) { [void]$blockers.Add("selected_deploy_bundle_source_git_dirty_rebuild_required_before_ec2") }
if (-not $selectedPackageReady) { [void]$blockers.Add("selected_package_deploy_matrix_not_ready") }
if ([bool]$targetPlan.explicit_user_selection_required) { [void]$blockers.Add("explicit_user_target_runtime_selection_required") }
foreach ($blocker in @(Convert-ToArray -Value $targetPlan.blocker_summary | ForEach-Object { [string]$_ })) {
  if (![string]::IsNullOrWhiteSpace($blocker)) { [void]$blockers.Add($blocker) }
}

$postCheckpointReady = (
  $manifestReady -and
  $manifestDryRunValid -and
  $manifestDryRunNonMutating -and
  $cleanGitAfterCheckpoint -and
  $selectedPackageReady -and
  -not $selectedBundleDirty -and
  -not [bool]$targetPlan.explicit_user_selection_required
)

$manifestRel = ConvertTo-ProjectRelativePath -Path $manifestResolved
$commandSequence = @(
  (New-CommandStep -Name "manifest_scoped_checkpoint_execute" -Gate "explicit_checkpoint_intent_required" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-GitHubCheckpoint.ps1 -ProjectRoot C:\Comfy_UI_Main -ScopeManifestFile C:\Comfy_UI_Main\$manifestRel -Message `"Wave66: manifest-scoped runtime checkpoint`" -Execute" -ExpectedEvidence "Checkpoint evidence with no blocked paths, expected include/exclude manifest, and a post-execute clean or explicitly inspected worktree state." -WhenToRun "Only after explicit checkpoint intent is selected." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "post_checkpoint_git_gate" -Gate "after_checkpoint_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-GitHubCheckpoint.ps1 -ProjectRoot C:\Comfy_UI_Main -ScopeManifestFile C:\Comfy_UI_Main\$manifestRel -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Git_Verification\W66_GITHUB_CHECKPOINT_POST_MANIFEST_GATE_<timestamp>.json" -ExpectedEvidence "result=pass_git_checkpoint_ready, clean_worktree=true, local_matches_origin=true, commit_attempted=false, push_attempted=false." -WhenToRun "Immediately after checkpoint execute and before any deploy-bundle rebuild." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "active_runtime_queue_package_deploy_matrix_recheck" -Gate "post_checkpoint_clean_git" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ActiveRuntimeQueuePackageDeployMatrix.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_PACKAGE_DEPLOY_MATRIX_<timestamp>.json" -ExpectedEvidence "Selected lane package/deploy row exists; any dirty source bundle blocker remains explicit until bundle rebuild." -WhenToRun "After clean Git checkpoint and before any deploy-bundle rebuild or S3 publish." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "selected_lane_deploy_bundle_rebuild" -Gate "post_checkpoint_clean_git" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $selectedLaneId -RunPackageManifestFile <selected-run-package-manifest>" -ExpectedEvidence "Deploy bundle manifest and zip built from clean checkpoint source for lane $selectedLaneId." -WhenToRun "After checkpoint clean gate and selected lane/run package are confirmed." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "s3_runtime_transfer_readiness_recheck" -Gate "before_s3_publish" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-S3RuntimeTransferReadiness.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_RUNTIME_TRANSFER_READINESS_POST_CHECKPOINT_<timestamp>.json" -ExpectedEvidence "S3 runtime transfer readiness result allows deploy-bundle publish without starting EC2." -WhenToRun "After bundle rebuild, before S3 publish." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "target_runtime_execution_plan_recheck" -Gate "post_checkpoint_and_bundle_rebuild" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ActiveRuntimeQueueTargetRuntimeExecutionPlan.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_<timestamp>.json" -ExpectedEvidence "Selected lane remains $selectedLaneId or newer queue policy explains the next selected target-runtime lane." -WhenToRun "After Git, package/deploy, and S3 readiness are rechecked." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "runtime_unblock_handoff_recheck" -Gate "before_any_live_ec2" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-RuntimeUnblockHandoff.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $selectedLaneId -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_RUNTIME_UNBLOCK_HANDOFF_${selectedLaneId}_<timestamp>.json" -ExpectedEvidence "Handoff shows selected lane, clean Git, deploy bundle path, S3 readiness, and exact live EC2 blockers." -WhenToRun "After post-checkpoint local gates pass, before EC2 execute." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "ec2_static_proof_execute_still_blocked" -Gate "explicit_live_window_and_all_gates" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId $selectedLaneId -Execute -SkipGitLfsPull -DeployBundleS3Uri <s3-bundle-uri> -DeployBundleSha256 <bundle-sha256> -MaxEc2RuntimeMinutes 25" -ExpectedEvidence "Object-info, model path/hash, bundle hash verification, lane match, and final EC2 stopped state." -WhenToRun "Only after explicit live EC2 selection and all revalidation gates pass." -ExecuteAllowedNow $false)
)

$result = if ($postCheckpointReady) {
  "post_checkpoint_runtime_revalidation_ready"
} else {
  "blocked_post_checkpoint_runtime_revalidation_waiting_for_manifest_checkpoint"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "post_checkpoint_runtime_revalidation_plan"
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
  post_checkpoint_ready_to_run = $postCheckpointReady
  scoped_checkpoint_manifest = ConvertTo-ProjectRelativePath -Path $manifestResolved
  manifest_checkpoint_dry_run = ConvertTo-ProjectRelativePath -Path $dryRunResolved
  package_deploy_matrix = ConvertTo-ProjectRelativePath -Path $packageMatrixResolved
  target_runtime_execution_plan = ConvertTo-ProjectRelativePath -Path $targetPlanResolved
  selected_lane_id = $selectedLaneId
  selected_package_deploy_ready = $selectedPackageReady
  selected_deploy_bundle_source_dirty = $selectedBundleDirty
  manifest_ready = $manifestReady
  manifest_checkpoint_dry_run_valid = $manifestDryRunValid
  manifest_checkpoint_dry_run_non_mutating = $manifestDryRunNonMutating
  clean_git_after_checkpoint = $cleanGitAfterCheckpoint
  blocker_summary = @($blockers | Select-Object -Unique)
  command_sequence = @($commandSequence)
  checkpoint_boundary = "Post-checkpoint revalidation plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = "Keep EC2 stopped. After explicit manifest-scoped checkpoint execute and clean Git proof, rerun package/deploy matrix, rebuild the selected deploy bundle from clean source, recheck S3/runtime gates, and only then consider bounded EC2 static proof."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 40) + [Environment]::NewLine, $utf8NoBom)

$stepLines = foreach ($step in $commandSequence) {
  "- $($step.name): gate=$($step.gate); execute_allowed_now=$($step.execute_allowed_now)"
}
$markdown = @"
# Post-Checkpoint Runtime Revalidation Plan

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $selectedLaneId
- post_checkpoint_ready_to_run: $($record.post_checkpoint_ready_to_run)
- manifest_ready: $($record.manifest_ready)
- manifest_checkpoint_dry_run_valid: $($record.manifest_checkpoint_dry_run_valid)
- clean_git_after_checkpoint: $($record.clean_git_after_checkpoint)

## Command Sequence

$($stepLines -join [Environment]::NewLine)

## Boundary

$($record.checkpoint_boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote post-checkpoint runtime revalidation plan: $outFileResolved"
$record | ConvertTo-Json -Depth 40
