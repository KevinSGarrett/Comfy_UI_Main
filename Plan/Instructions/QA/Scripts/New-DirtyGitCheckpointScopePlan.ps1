<#
.SYNOPSIS
Creates a local-only checkpoint scope plan from the dirty Git inventory.

.DESCRIPTION
Reads the latest dirty Git inventory evidence and the current `git status`
state, then classifies dirty paths into checkpoint-scope dispositions. The
helper writes evidence only; it never stages, commits, pushes, resets,
checks out, contacts services, starts EC2, posts prompts, or generates.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$InventoryFile = "",
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

function New-CountBy {
  param([object[]]$Rows, [string]$Property)
  return @($Rows | Group-Object -Property { [string]$_[$Property] } | Sort-Object -Property @{ Expression = "Count"; Descending = $true }, Name | ForEach-Object {
    [ordered]@{
      name = [string]$_.Name
      count = [int]$_.Count
    }
  })
}

function Test-BlockedPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
  foreach ($pattern in @("\.env$", "\.pem$", "\.key$", "\.p12$", "\.pfx$", "\.safetensors$", "\.ckpt$", "\.pt$", "\.pth$", "\.onnx$", "\.bin$", "\.gguf$")) {
    if ($Path -match $pattern) { return $true }
  }
  return $false
}

function Get-TopLevel {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  $normalized = $Path.Replace("\", "/")
  $parts = $normalized.Split("/")
  if ($parts.Count -eq 0) { return $normalized }
  return $parts[0]
}

function Get-ScopeClassification {
  param([string]$Path)
  $normalized = $Path.Replace("\", "/")
  $top = Get-TopLevel -Path $normalized

  if ($normalized -eq "Plan.zip" -or $top -like "_ci_*") {
    return [ordered]@{ category = "archive_or_temp_defer"; disposition = "defer_or_exclude_candidate"; reason = "archive or temporary CI output should not enter an automatic checkpoint without explicit review" }
  }
  if ($top -eq "runtime_artifacts") {
    return [ordered]@{ category = "runtime_artifacts_review"; disposition = "review_before_checkpoint"; reason = "runtime artifacts can be evidence but may include bulky/generated runtime state" }
  }
  if ($top -eq "Jira") {
    return [ordered]@{ category = "jira_control_plane_review"; disposition = "review_before_checkpoint"; reason = "Jira state is control-plane cleanup data and should not switch the active lane" }
  }
  if ($top -in @("Ref_Image_1", "Ref_Image_2", "Ref_Image_Canonical_Body", "Reference_Images", "masks")) {
    return [ordered]@{ category = "reference_or_mask_asset_review"; disposition = "review_before_checkpoint"; reason = "reference and mask assets may be user-provided or mask-dependent and need explicit scope review" }
  }
  if ($top -eq "Plan") {
    return [ordered]@{ category = "project_plan_ledger_candidate"; disposition = "include_candidate"; reason = "Plan, Instructions, QA evidence, Items, Tracker, and implementation files are the authoritative local execution ledger" }
  }
  if ($top -in @(".github", "PromptProfiles", "Workflows", "config") -or $normalized -eq "PROJECT_ROOT_MANIFEST.json") {
    return [ordered]@{ category = "runtime_orchestration_candidate"; disposition = "include_candidate"; reason = "workflow, prompt, config, GitHub workflow, and root manifest changes support runtime orchestration" }
  }
  return [ordered]@{ category = "other_review"; disposition = "review_before_checkpoint"; reason = "unrecognized top-level path needs explicit scope review" }
}

Set-Location -LiteralPath $ProjectRoot

if ([string]::IsNullOrWhiteSpace($InventoryFile)) {
  $InventoryFile = Find-LatestFile -Directory (Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Git_Verification") -Filter "W66_DIRTY_GIT_CHECKPOINT_INVENTORY_*.json"
}
$inventoryResolved = Resolve-ProjectPath -Path $InventoryFile
if ([string]::IsNullOrWhiteSpace($inventoryResolved) -or -not (Test-Path -LiteralPath $inventoryResolved -PathType Leaf)) {
  throw "Dirty Git inventory evidence is required."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Git_Verification\W66_DIRTY_GIT_CHECKPOINT_SCOPE_PLAN_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$inventory = Get-Content -LiteralPath $inventoryResolved -Raw | ConvertFrom-Json
$inventoryRelative = ConvertTo-ProjectRelativePath -Path $inventoryResolved
$inventoryMarkdownRelative = ConvertTo-ProjectRelativePath -Path ([System.IO.Path]::ChangeExtension($inventoryResolved, ".md"))
$rawStatus = @(git status --porcelain=v1 2>$null)
if ($LASTEXITCODE -ne 0) {
  throw "git status failed under $ProjectRoot"
}

$rows = foreach ($line in $rawStatus) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  $indexStatus = if ($line.Length -ge 1) { $line.Substring(0, 1) } else { "" }
  $worktreeStatus = if ($line.Length -ge 2) { $line.Substring(1, 1) } else { "" }
  $path = if ($line.Length -gt 3) { $line.Substring(3).Trim() } else { $line.Trim() }
  if ($path -match " -> ") { $path = ($path -split " -> ")[-1].Trim() }
  $scope = Get-ScopeClassification -Path $path
  [ordered]@{
    status = $line.Substring(0, [Math]::Min(2, $line.Length)).Trim()
    path = $path
    top_level = Get-TopLevel -Path $path
    tracked = ($line -notmatch "^\?\?")
    untracked = ($line -match "^\?\?")
    staged = ($line -notmatch "^\?\?" -and $indexStatus -ne " ")
    unstaged = ($line -notmatch "^\?\?" -and $worktreeStatus -ne " ")
    blocked_path = (Test-BlockedPath -Path $path)
    category = [string]$scope.category
    disposition = [string]$scope.disposition
    reason = [string]$scope.reason
  }
}

$trackedRows = @($rows | Where-Object { [bool]$_.tracked })
$untrackedRows = @($rows | Where-Object { [bool]$_.untracked })
$blockedRows = @($rows | Where-Object { [bool]$_.blocked_path })
$inventorySelfEvidenceRows = @($rows | Where-Object { [string]$_["path"] -in @($inventoryRelative, $inventoryMarkdownRelative) })
$comparisonRows = @($rows | Where-Object { [string]$_["path"] -notin @($inventoryRelative, $inventoryMarkdownRelative) })
$comparisonTrackedRows = @($comparisonRows | Where-Object { [bool]$_.tracked })
$comparisonUntrackedRows = @($comparisonRows | Where-Object { [bool]$_.untracked })
$comparisonBlockedRows = @($comparisonRows | Where-Object { [bool]$_.blocked_path })
$includeRows = @($rows | Where-Object { [string]$_.disposition -eq "include_candidate" })
$reviewRows = @($rows | Where-Object { [string]$_.disposition -eq "review_before_checkpoint" })
$deferRows = @($rows | Where-Object { [string]$_.disposition -eq "defer_or_exclude_candidate" })
$inventoryMatchesCurrent = (
  [int]$inventory.porcelain_count -eq $comparisonRows.Count -and
  [int]$inventory.tracked_porcelain_count -eq $comparisonTrackedRows.Count -and
  [int]$inventory.untracked_porcelain_count -eq $comparisonUntrackedRows.Count -and
  [int]$inventory.blocked_changed_path_count -eq $comparisonBlockedRows.Count
)

$scopeReadyForCheckpoint = (
  $rows.Count -gt 0 -and
  $inventoryMatchesCurrent -and
  $blockedRows.Count -eq 0 -and
  $reviewRows.Count -eq 0 -and
  $deferRows.Count -eq 0
)

$result = if (-not $inventoryMatchesCurrent) {
  "blocked_checkpoint_scope_inventory_drift"
} elseif ($blockedRows.Count -gt 0) {
  "blocked_checkpoint_scope_blocked_paths_present"
} elseif ($reviewRows.Count -gt 0 -or $deferRows.Count -gt 0) {
  "checkpoint_scope_runtime_ready"
} elseif ($scopeReadyForCheckpoint) {
  "checkpoint_scope_include_candidates_only"
} else {
  "checkpoint_scope_no_dirty_paths"
}

$categoryRows = @($rows | Group-Object -Property { [string]$_["category"] } | Sort-Object -Property @{ Expression = "Count"; Descending = $true }, Name | ForEach-Object {
  $groupRows = @($_.Group)
  [ordered]@{
    category = [string]$_.Name
    count = [int]$_.Count
    disposition = [string]($groupRows[0].disposition)
    reason = [string]($groupRows[0].reason)
    tracked_count = @($groupRows | Where-Object { [bool]$_.tracked }).Count
    untracked_count = @($groupRows | Where-Object { [bool]$_.untracked }).Count
    sample_paths = @($groupRows | Select-Object -First 25 | ForEach-Object { [string]$_["path"] })
  }
})

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "dirty_git_checkpoint_scope_plan"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  result = $result
  failure_category = $(if ($result -eq "checkpoint_scope_include_candidates_only") { $null } elseif (-not $inventoryMatchesCurrent) { "inventory_drift" } elseif ($blockedRows.Count -gt 0) { "blocked_changed_paths_present" } else { "checkpoint_scope_runtime_ready" })
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
  inventory_evidence = ConvertTo-ProjectRelativePath -Path $inventoryResolved
  inventory_matches_current = $inventoryMatchesCurrent
  ignored_inventory_self_evidence_path_count = $inventorySelfEvidenceRows.Count
  porcelain_count = $rows.Count
  comparison_porcelain_count = $comparisonRows.Count
  tracked_porcelain_count = $trackedRows.Count
  untracked_porcelain_count = $untrackedRows.Count
  blocked_changed_path_count = $blockedRows.Count
  include_candidate_count = $includeRows.Count
  review_before_checkpoint_count = $reviewRows.Count
  defer_or_exclude_candidate_count = $deferRows.Count
  scope_ready_for_checkpoint = $scopeReadyForCheckpoint
  top_level_counts = @(New-CountBy -Rows $rows -Property "top_level")
  disposition_counts = @(New-CountBy -Rows $rows -Property "disposition")
  category_scope = @($categoryRows)
  include_candidate_samples = @($includeRows | Select-Object -First 80 | ForEach-Object { [string]$_["path"] })
  runtime_ready_samples = @($reviewRows | Select-Object -First 80 | ForEach-Object { [string]$_["path"] })
  defer_or_exclude_samples = @($deferRows | Select-Object -First 80 | ForEach-Object { [string]$_["path"] })
  checkpoint_boundary = "Scope plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = $(if ($scopeReadyForCheckpoint) { "Run the guarded Git checkpoint dry-run, then checkpoint only after explicit checkpoint intent is confirmed." } else { "Review review_before_checkpoint and defer_or_exclude_candidate groups, decide the checkpoint scope, then run the guarded checkpoint workflow only when ready." })
}

$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 40) + [Environment]::NewLine, $utf8NoBom)

$categoryLines = foreach ($row in $categoryRows) {
  "- $($row.category): $($row.count), disposition=$($row.disposition)"
}
$markdown = @"
# Dirty Git Checkpoint Scope Plan

- created_at: $($record.created_at)
- result: $($record.result)
- inventory_matches_current: $($record.inventory_matches_current)
- porcelain_count: $($record.porcelain_count)
- include_candidate_count: $($record.include_candidate_count)
- review_before_checkpoint_count: $($record.review_before_checkpoint_count)
- defer_or_exclude_candidate_count: $($record.defer_or_exclude_candidate_count)
- scope_ready_for_checkpoint: $($record.scope_ready_for_checkpoint)

## Categories

$($categoryLines -join [Environment]::NewLine)

## Boundary

$($record.checkpoint_boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote dirty Git checkpoint scope plan: $outFileResolved"
$record | ConvertTo-Json -Depth 40
