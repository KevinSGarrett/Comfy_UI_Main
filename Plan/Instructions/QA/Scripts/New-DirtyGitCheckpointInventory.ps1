<#
.SYNOPSIS
Creates a local-only dirty Git checkpoint inventory before any clean checkpoint.

.DESCRIPTION
Classifies the current `git status --porcelain` output into tracked,
untracked, staged, unstaged, blocked-path, and top-level directory buckets.
The helper writes evidence only; it does not stage, commit, push, reset,
checkout, contact external services, start EC2, post prompts, or generate.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
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

function Get-GitValue {
  param([string[]]$Arguments)
  $value = & git @Arguments 2>$null
  if ($LASTEXITCODE -ne 0) { return $null }
  return [string]($value | Select-Object -First 1)
}

function New-CountBy {
  param([object[]]$Rows, [string]$Property)
  $items = @($Rows | Group-Object -Property { [string]$_[$Property] } | Sort-Object -Property @{ Expression = "Count"; Descending = $true }, Name | ForEach-Object {
    [ordered]@{
      name = [string]$_.Name
      count = [int]$_.Count
    }
  })
  return $items
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

Set-Location -LiteralPath $ProjectRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Git_Verification\W66_DIRTY_GIT_CHECKPOINT_INVENTORY_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$rawStatus = @(git status --porcelain=v1 2>$null)
if ($LASTEXITCODE -ne 0) {
  throw "git status failed under $ProjectRoot"
}

$rows = foreach ($line in $rawStatus) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  $indexStatus = if ($line.Length -ge 1) { $line.Substring(0, 1) } else { "" }
  $worktreeStatus = if ($line.Length -ge 2) { $line.Substring(1, 1) } else { "" }
  $path = if ($line.Length -gt 3) { $line.Substring(3).Trim() } else { $line.Trim() }
  if ($path -match " -> ") {
    $path = ($path -split " -> ")[-1].Trim()
  }
  [ordered]@{
    status = $line.Substring(0, [Math]::Min(2, $line.Length)).Trim()
    index_status = $indexStatus
    worktree_status = $worktreeStatus
    path = $path
    top_level = Get-TopLevel -Path $path
    tracked = ($line -notmatch "^\?\?")
    untracked = ($line -match "^\?\?")
    staged = ($line -notmatch "^\?\?" -and $indexStatus -ne " ")
    unstaged = ($line -notmatch "^\?\?" -and $worktreeStatus -ne " ")
    blocked_path = (Test-BlockedPath -Path $path)
  }
}

$trackedRows = @($rows | Where-Object { [bool]$_.tracked })
$untrackedRows = @($rows | Where-Object { [bool]$_.untracked })
$stagedRows = @($rows | Where-Object { [bool]$_.staged })
$unstagedRows = @($rows | Where-Object { [bool]$_.unstaged })
$blockedRows = @($rows | Where-Object { [bool]$_.blocked_path })
$head = Get-GitValue -Arguments @("rev-parse", "HEAD")
$originMain = Get-GitValue -Arguments @("rev-parse", "origin/main")
$localMatchesOrigin = (![string]::IsNullOrWhiteSpace($head) -and ![string]::IsNullOrWhiteSpace($originMain) -and $head -eq $originMain)
$cleanWorktree = ($rows.Count -eq 0)

$result = if ($cleanWorktree -and $localMatchesOrigin) {
  "pass_clean_git_checkpoint_inventory"
} elseif ($blockedRows.Count -gt 0) {
  "blocked_dirty_git_inventory_blocked_paths_present"
} else {
  "blocked_dirty_git_inventory_checkpoint_required"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "dirty_git_checkpoint_inventory"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  result = $result
  failure_category = $(if ($result -eq "pass_clean_git_checkpoint_inventory") { $null } elseif ($blockedRows.Count -gt 0) { "blocked_changed_paths_present" } else { "local_git_worktree_dirty" })
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
  head = $head
  origin_main = $originMain
  local_matches_origin = $localMatchesOrigin
  clean_worktree = $cleanWorktree
  porcelain_count = $rows.Count
  tracked_porcelain_count = $trackedRows.Count
  untracked_porcelain_count = $untrackedRows.Count
  staged_count = $stagedRows.Count
  unstaged_count = $unstagedRows.Count
  blocked_changed_path_count = $blockedRows.Count
  top_level_counts = @(New-CountBy -Rows $rows -Property "top_level")
  status_counts = @(New-CountBy -Rows $rows -Property "status")
  tracked_top_level_counts = @(New-CountBy -Rows $trackedRows -Property "top_level")
  untracked_top_level_counts = @(New-CountBy -Rows $untrackedRows -Property "top_level")
  changed_preview = @($rows | Select-Object -First 160)
  blocked_changed_paths = @($blockedRows | Select-Object -First 160)
  checkpoint_boundary = "Inventory only. Do not use this artifact as approval to commit, push, reset, checkout, start EC2, upload to S3, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, or activate Wave71+."
  next_action = $(if ($cleanWorktree -and $localMatchesOrigin) { "Run Invoke-GitHubCheckpoint.ps1 dry-run immediately before any explicitly selected EC2 execute path." } else { "Review dirty inventory, decide intentional checkpoint scope, then use the guarded checkpoint workflow; rebuild/revalidate deploy bundles only after a clean checkpoint exists." })
}

$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$topLines = foreach ($row in @($record.top_level_counts | Select-Object -First 20)) {
  "- $($row.name): $($row.count)"
}
$markdown = @"
# Dirty Git Checkpoint Inventory

- created_at: $($record.created_at)
- result: $($record.result)
- clean_worktree: $($record.clean_worktree)
- local_matches_origin: $($record.local_matches_origin)
- porcelain_count: $($record.porcelain_count)
- tracked_porcelain_count: $($record.tracked_porcelain_count)
- untracked_porcelain_count: $($record.untracked_porcelain_count)
- staged_count: $($record.staged_count)
- unstaged_count: $($record.unstaged_count)
- blocked_changed_path_count: $($record.blocked_changed_path_count)

## Top-Level Counts

$($topLines -join [Environment]::NewLine)

## Boundary

$($record.checkpoint_boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote dirty Git checkpoint inventory: $outFileResolved"
$record | ConvertTo-Json -Depth 30
