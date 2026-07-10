<#
.SYNOPSIS
Resolves dirty Git checkpoint review groups into local-only checkpoint guidance.

.DESCRIPTION
Consumes a dirty Git checkpoint scope plan and records which groups are
reasonable checkpoint candidates, which groups should stay local/excluded for
now, and which workflow gap remains before a clean checkpoint can be made.
The helper writes evidence only; it never stages, commits, pushes, resets,
checks out, contacts services, starts EC2, posts prompts, or generates.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ScopePlanFile = "",
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

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
}

function New-ResolutionRow {
  param(
    [string]$Category,
    [int]$Count,
    [string]$SourceDisposition,
    [string]$Resolution,
    [string]$CheckpointAction,
    [string]$Reason,
    [object[]]$SamplePaths = @()
  )
  return [ordered]@{
    category = $Category
    count = $Count
    source_disposition = $SourceDisposition
    resolution = $Resolution
    checkpoint_action = $CheckpointAction
    reason = $Reason
    sample_paths = @($SamplePaths)
  }
}

Set-Location -LiteralPath $ProjectRoot

if ([string]::IsNullOrWhiteSpace($ScopePlanFile)) {
  $ScopePlanFile = Find-LatestFile -Directory (Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Git_Verification") -Filter "W66_DIRTY_GIT_CHECKPOINT_SCOPE_PLAN_*.json"
}
$scopeResolved = Resolve-ProjectPath -Path $ScopePlanFile
if ([string]::IsNullOrWhiteSpace($scopeResolved) -or -not (Test-Path -LiteralPath $scopeResolved -PathType Leaf)) {
  throw "Dirty Git checkpoint scope plan evidence is required."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Git_Verification\W66_DIRTY_GIT_CHECKPOINT_REVIEW_RESOLUTION_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$scope = Get-Content -LiteralPath $scopeResolved -Raw | ConvertFrom-Json
$checkpointHelperPath = Resolve-ProjectPath -Path "Plan\Instructions\Operations\Scripts\Invoke-GitHubCheckpoint.ps1"
$checkpointScopeSupportPresent = $false
if ($null -ne $checkpointHelperPath -and (Test-Path -LiteralPath $checkpointHelperPath -PathType Leaf)) {
  $checkpointHelperContent = Get-Content -LiteralPath $checkpointHelperPath -Raw
  $checkpointScopeSupportPresent = (
    $checkpointHelperContent -match '\[string\[\]\]\$IncludePath' -and
    $checkpointHelperContent -match '\[string\[\]\]\$ExcludePath' -and
    $checkpointHelperContent -match "checkpoint_scope_mode" -and
    $checkpointHelperContent -match "scope_changed_path_count"
  )
}
$categoryRows = @(Convert-ToArray $scope.category_scope)
$resolutionRows = foreach ($category in $categoryRows) {
  $samples = @(Convert-ToArray $category.sample_paths)
  switch ([string]$category.category) {
    "project_plan_ledger_candidate" {
      New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "include_candidate" -CheckpointAction "include_in_intended_checkpoint" -Reason "Authoritative local Plan/Instructions/QA/Items/Tracker/implementation ledger should be checkpointed when the scope is accepted." -SamplePaths $samples
    }
    "runtime_orchestration_candidate" {
      if ($checkpointScopeSupportPresent) {
        New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "include_candidate" -CheckpointAction "include_in_intended_checkpoint" -Reason "Prompt profiles, workflows, config, root manifest, and GitHub workflow changes are runtime orchestration sources; the guarded checkpoint helper now supports explicit non-Plan include/exclude scope." -SamplePaths $samples
      } else {
        New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "include_candidate_with_checkpoint_workflow_gap" -CheckpointAction "include_after_guarded_checkpoint_supports_non_plan_paths" -Reason "Prompt profiles, workflows, config, root manifest, and GitHub workflow changes are part of runtime orchestration, but the current guarded checkpoint helper stages Plan only." -SamplePaths $samples
      }
    }
    "runtime_artifacts_review" {
      New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "exclude_from_checkpoint_for_now" -CheckpointAction "preserve_local_do_not_stage" -Reason "Runtime artifacts may be generated, bulky, or ephemeral; authoritative proof should be mirrored under Plan/Instructions/QA/Evidence before checkpointing." -SamplePaths $samples
    }
    "reference_or_mask_asset_review" {
      New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "local_dependency_do_not_checkpoint_by_default" -CheckpointAction "preserve_local_do_not_stage" -Reason "Reference and mask assets are user-provided or mask-dependent local dependencies; do not absorb them into a Git checkpoint without explicit asset policy." -SamplePaths $samples
    }
    "jira_control_plane_review" {
      New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "exclude_from_active_build_checkpoint" -CheckpointAction "preserve_local_do_not_stage" -Reason "Jira is a control-plane side state and must not switch the active build lane or bulk-import local ledger data." -SamplePaths $samples
    }
    "archive_or_temp_defer" {
      New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "exclude_or_cleanup_candidate" -CheckpointAction "do_not_stage" -Reason "Archives and temporary CI output should not enter an automatic checkpoint; remove or archive outside Git only after explicit cleanup decision." -SamplePaths $samples
    }
    default {
      New-ResolutionRow -Category $category.category -Count ([int]$category.count) -SourceDisposition $category.disposition -Resolution "unresolved_runtime_ready" -CheckpointAction "do_not_stage_until_reviewed" -Reason "Unrecognized category needs explicit review." -SamplePaths $samples
    }
  }
}
if (@($resolutionRows).Count -eq 0) {
  $resolutionRows = @(
    (New-ResolutionRow -Category "clean_worktree_noop" -Count 0 -SourceDisposition "no_dirty_paths" -Resolution "no_checkpoint_review_needed" -CheckpointAction "no_action_required" -Reason "The current scope plan has no dirty path categories to resolve." -SamplePaths @())
  )
}

$includeRows = @($resolutionRows | Where-Object { [string]$_["checkpoint_action"] -match "^include" })
$preserveRows = @($resolutionRows | Where-Object { [string]$_["checkpoint_action"] -eq "preserve_local_do_not_stage" })
$doNotStageRows = @($resolutionRows | Where-Object { [string]$_["checkpoint_action"] -eq "do_not_stage" -or [string]$_["checkpoint_action"] -eq "do_not_stage_until_reviewed" })
$workflowGapRows = @($resolutionRows | Where-Object { [string]$_["resolution"] -eq "include_candidate_with_checkpoint_workflow_gap" })
$unresolvedRows = @($resolutionRows | Where-Object { [string]$_["resolution"] -eq "unresolved_runtime_ready" })

$includePathCount = @($includeRows | ForEach-Object { [int]$_["count"] } | Measure-Object -Sum).Sum
$preservePathCount = @($preserveRows | ForEach-Object { [int]$_["count"] } | Measure-Object -Sum).Sum
$doNotStagePathCount = @($doNotStageRows | ForEach-Object { [int]$_["count"] } | Measure-Object -Sum).Sum
$workflowGapPathCount = @($workflowGapRows | ForEach-Object { [int]$_["count"] } | Measure-Object -Sum).Sum
$unresolvedPathCount = @($unresolvedRows | ForEach-Object { [int]$_["count"] } | Measure-Object -Sum).Sum
if ($null -eq $includePathCount) { $includePathCount = 0 }
if ($null -eq $preservePathCount) { $preservePathCount = 0 }
if ($null -eq $doNotStagePathCount) { $doNotStagePathCount = 0 }
if ($null -eq $workflowGapPathCount) { $workflowGapPathCount = 0 }
if ($null -eq $unresolvedPathCount) { $unresolvedPathCount = 0 }

$reviewGroupsResolved = ($unresolvedRows.Count -eq 0)
$checkpointWorkflowGapPresent = ($workflowGapRows.Count -gt 0)
$readyForGuardedCheckpointDryRun = (
  [bool]$scope.inventory_matches_current -and
  [int]$scope.blocked_changed_path_count -eq 0 -and
  $reviewGroupsResolved -and
  -not $checkpointWorkflowGapPresent
)

$result = if (-not [bool]$scope.inventory_matches_current) {
  "blocked_review_resolution_inventory_drift"
} elseif ([int]$scope.blocked_changed_path_count -gt 0) {
  "blocked_review_resolution_blocked_paths_present"
} elseif ($checkpointWorkflowGapPresent) {
  "checkpoint_review_resolved_workflow_gap_remaining"
} elseif ($reviewGroupsResolved) {
  "checkpoint_review_resolved_ready_for_guarded_dry_run"
} else {
  "checkpoint_review_unresolved"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "dirty_git_checkpoint_review_resolution"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  result = $result
  failure_category = $(if ($result -eq "checkpoint_review_resolved_ready_for_guarded_dry_run") { $null } elseif (-not [bool]$scope.inventory_matches_current) { "inventory_drift" } elseif ([int]$scope.blocked_changed_path_count -gt 0) { "blocked_changed_paths_present" } elseif ($checkpointWorkflowGapPresent) { "checkpoint_workflow_plan_only_gap" } else { "review_resolution_unresolved" })
  local_only = $true
  github_api_contacted = $false
  aws_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  s3_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  active_runtime_marker_written = $false
  commit_attempted = $false
  push_attempted = $false
  stage_attempted = $false
  reset_attempted = $false
  checkout_attempted = $false
  deploy_bundle_rebuilt = $false
  scope_plan_evidence = ConvertTo-ProjectRelativePath -Path $scopeResolved
  scope_plan_result = [string]$scope.result
  inventory_matches_current = [bool]$scope.inventory_matches_current
  source_porcelain_count = [int]$scope.porcelain_count
  include_candidate_path_count = [int]$includePathCount
  preserve_local_do_not_stage_path_count = [int]$preservePathCount
  do_not_stage_path_count = [int]$doNotStagePathCount
  checkpoint_workflow_gap_path_count = [int]$workflowGapPathCount
  unresolved_path_count = [int]$unresolvedPathCount
  review_groups_resolved = $reviewGroupsResolved
  checkpoint_scope_support_present = $checkpointScopeSupportPresent
  checkpoint_scope_support_script = ConvertTo-ProjectRelativePath -Path $checkpointHelperPath
  checkpoint_workflow_gap_present = $checkpointWorkflowGapPresent
  ready_for_guarded_checkpoint_dry_run = $readyForGuardedCheckpointDryRun
  resolution_rows = @($resolutionRows)
  intended_include_roots = @("Plan", ".github", "PromptProfiles", "Workflows", "config", "PROJECT_ROOT_MANIFEST.json")
  intended_include_roots_requiring_checkpoint_helper_support = @($(if (-not $checkpointScopeSupportPresent) { ".github"; "PromptProfiles"; "Workflows"; "config"; "PROJECT_ROOT_MANIFEST.json" }))
  intended_preserve_local_roots = @("runtime_artifacts", "Ref_Image_1", "Ref_Image_2", "Ref_Image_Canonical_Body", "Reference_Images", "masks", "Jira")
  intended_do_not_stage_roots = @("Plan.zip", "_ci_w64_20260708T232900-0500")
  checkpoint_boundary = "Review resolution only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = $(if ($checkpointWorkflowGapPresent) { "Patch or replace the guarded checkpoint workflow so an explicit include/exclude manifest can cover Plan plus runtime-orchestration roots without staging preserved local assets; then rerun review resolution before checkpoint dry-run." } elseif ($readyForGuardedCheckpointDryRun) { "Run the guarded Git checkpoint dry-run, then checkpoint only after explicit checkpoint intent is confirmed." } else { "Resolve remaining checkpoint review rows before any guarded checkpoint dry-run." })
}

$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 40) + [Environment]::NewLine, $utf8NoBom)

$rowLines = foreach ($row in $resolutionRows) {
  "- $($row.category): $($row.count), resolution=$($row.resolution), action=$($row.checkpoint_action)"
}
$markdown = @"
# Dirty Git Checkpoint Review Resolution

- created_at: $($record.created_at)
- result: $($record.result)
- ready_for_guarded_checkpoint_dry_run: $($record.ready_for_guarded_checkpoint_dry_run)
- checkpoint_workflow_gap_present: $($record.checkpoint_workflow_gap_present)
- include_candidate_path_count: $($record.include_candidate_path_count)
- preserve_local_do_not_stage_path_count: $($record.preserve_local_do_not_stage_path_count)
- do_not_stage_path_count: $($record.do_not_stage_path_count)
- checkpoint_workflow_gap_path_count: $($record.checkpoint_workflow_gap_path_count)

## Resolutions

$($rowLines -join [Environment]::NewLine)

## Boundary

$($record.checkpoint_boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote dirty Git checkpoint review resolution: $outFileResolved"
$record | ConvertTo-Json -Depth 40
