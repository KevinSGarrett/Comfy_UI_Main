<#
.SYNOPSIS
Creates a local-only manifest for the guarded scoped Git checkpoint path.

.DESCRIPTION
Consumes checkpoint review-resolution evidence plus an explicit-scope checkpoint
dry-run and writes a manifest that can be passed back to Invoke-GitHubCheckpoint
with -ScopeManifestFile. The helper does not stage, commit, push, reset,
checkout, contact services, rebuild deploy bundles, start EC2, or generate.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ReviewResolutionFile = "",
  [string]$GitCheckpointDryRunFile = "",
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

function ConvertTo-GitRelativePath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return "" }
  $value = ([string]$Path).Trim().Replace("\", "/")
  while ($value.StartsWith("./")) {
    $value = $value.Substring(2)
  }
  return $value.Trim("/")
}

function Test-BlockedPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
  foreach ($pattern in @("\.env$", "\.pem$", "\.key$", "\.p12$", "\.pfx$", "\.safetensors$", "\.ckpt$", "\.pt$", "\.pth$", "\.onnx$", "\.bin$", "\.gguf$")) {
    if ($Path -match $pattern) { return $true }
  }
  return $false
}

Set-Location -LiteralPath $ProjectRoot

$gitEvidenceDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Git_Verification"
if ([string]::IsNullOrWhiteSpace($ReviewResolutionFile)) {
  $ReviewResolutionFile = Find-LatestFile -Directory $gitEvidenceDir -Filter "W66_DIRTY_GIT_CHECKPOINT_REVIEW_RESOLUTION_*.json"
}
if ([string]::IsNullOrWhiteSpace($GitCheckpointDryRunFile)) {
  $GitCheckpointDryRunFile = Find-LatestFile -Directory $gitEvidenceDir -Filter "W66_GITHUB_CHECKPOINT_EXPLICIT_SCOPE_DRY_RUN_*.json"
}

$reviewResolved = Resolve-ProjectPath -Path $ReviewResolutionFile
$dryRunResolved = Resolve-ProjectPath -Path $GitCheckpointDryRunFile
if ([string]::IsNullOrWhiteSpace($reviewResolved) -or -not (Test-Path -LiteralPath $reviewResolved -PathType Leaf)) {
  throw "Checkpoint review-resolution evidence is required."
}
if ([string]::IsNullOrWhiteSpace($dryRunResolved) -or -not (Test-Path -LiteralPath $dryRunResolved -PathType Leaf)) {
  throw "Explicit-scope checkpoint dry-run evidence is required."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Git_Verification\W66_SCOPED_GIT_CHECKPOINT_MANIFEST_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$review = Get-Content -LiteralPath $reviewResolved -Raw | ConvertFrom-Json
$dryRun = Get-Content -LiteralPath $dryRunResolved -Raw | ConvertFrom-Json

$includePaths = @(Convert-ToArray $dryRun.checkpoint_include_paths | ForEach-Object { ConvertTo-GitRelativePath -Path $_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$excludePaths = @(Convert-ToArray $dryRun.checkpoint_exclude_paths | ForEach-Object { ConvertTo-GitRelativePath -Path $_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$blockedIncludePaths = @($includePaths | Where-Object { Test-BlockedPath -Path $_ })
$blockedExcludePaths = @($excludePaths | Where-Object { Test-BlockedPath -Path $_ })

$reviewReady = ([string]$review.result -eq "checkpoint_review_resolved_ready_for_guarded_dry_run" -and [bool]$review.ready_for_guarded_checkpoint_dry_run)
$dryRunScoped = ([string]$dryRun.checkpoint_scope_mode -in @("explicit_paths", "explicit_manifest"))
$dryRunNonMutating = (-not [bool]$dryRun.stage_attempted -and -not [bool]$dryRun.commit_attempted -and -not [bool]$dryRun.push_attempted -and -not [bool]$dryRun.reset_attempted -and -not [bool]$dryRun.checkout_attempted)
$requiredIncludePaths = @("Plan", ".github", "PromptProfiles", "Workflows", "config", "PROJECT_ROOT_MANIFEST.json")
$requiredExcludePaths = @("runtime_artifacts", "Ref_Image_1", "Ref_Image_2", "Ref_Image_Canonical_Body", "Reference_Images", "masks", "Jira", "Plan.zip", "_ci_w64_20260708T232900-0500")
$missingRequiredIncludes = @($requiredIncludePaths | Where-Object { $_ -notin $includePaths })
$missingRequiredExcludes = @($requiredExcludePaths | Where-Object { $_ -notin $excludePaths })

$manifestReady = (
  $reviewReady -and
  $dryRunScoped -and
  $dryRunNonMutating -and
  @($includePaths).Count -gt 0 -and
  @($missingRequiredIncludes).Count -eq 0 -and
  @($missingRequiredExcludes).Count -eq 0 -and
  @($blockedIncludePaths).Count -eq 0 -and
  @($blockedExcludePaths).Count -eq 0
)

$result = if ($manifestReady) {
  "scoped_git_checkpoint_manifest_ready_pending_explicit_intent"
} elseif (-not $reviewReady) {
  "blocked_scoped_checkpoint_manifest_review_not_ready"
} elseif (-not $dryRunScoped) {
  "blocked_scoped_checkpoint_manifest_dry_run_not_explicit_scope"
} elseif (-not $dryRunNonMutating) {
  "blocked_scoped_checkpoint_manifest_dry_run_mutated_git"
} elseif (@($missingRequiredIncludes).Count -gt 0 -or @($missingRequiredExcludes).Count -gt 0) {
  "blocked_scoped_checkpoint_manifest_required_roots_missing"
} elseif (@($blockedIncludePaths).Count -gt 0 -or @($blockedExcludePaths).Count -gt 0) {
  "blocked_scoped_checkpoint_manifest_blocked_path_root"
} else {
  "blocked_scoped_checkpoint_manifest_unknown"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "scoped_git_checkpoint_manifest"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  result = $result
  failure_category = $(if ($manifestReady) { $null } else { $result })
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
  stage_attempted = $false
  commit_attempted = $false
  push_attempted = $false
  reset_attempted = $false
  checkout_attempted = $false
  deploy_bundle_rebuilt = $false
  checkpoint_intent_required = $true
  ready_for_checkpoint_execute_after_explicit_intent = $manifestReady
  review_resolution_evidence = ConvertTo-ProjectRelativePath -Path $reviewResolved
  checkpoint_dry_run_evidence = ConvertTo-ProjectRelativePath -Path $dryRunResolved
  review_result = [string]$review.result
  review_ready_for_guarded_checkpoint_dry_run = [bool]$review.ready_for_guarded_checkpoint_dry_run
  dry_run_result = [string]$dryRun.result
  dry_run_checkpoint_scope_mode = [string]$dryRun.checkpoint_scope_mode
  dry_run_clean_worktree = [bool]$dryRun.clean_worktree
  dry_run_local_matches_origin = [bool]$dryRun.local_matches_origin
  dry_run_scope_changed_path_count = [int]$dryRun.scope_changed_path_count
  dry_run_scope_excluded_changed_path_count = [int]$dryRun.scope_excluded_changed_path_count
  include_paths = @($includePaths)
  exclude_paths = @($excludePaths)
  missing_required_include_paths = @($missingRequiredIncludes)
  missing_required_exclude_paths = @($missingRequiredExcludes)
  blocked_include_paths = @($blockedIncludePaths)
  blocked_exclude_paths = @($blockedExcludePaths)
  dry_run_command = "powershell -NoProfile -ExecutionPolicy Bypass -File Plan/Instructions/Operations/Scripts/Invoke-GitHubCheckpoint.ps1 -ProjectRoot C:\Comfy_UI_Main -ScopeManifestFile <this-manifest> -OutFile <dry-run-evidence>"
  execute_command_requires_explicit_user_intent = "powershell -NoProfile -ExecutionPolicy Bypass -File Plan/Instructions/Operations/Scripts/Invoke-GitHubCheckpoint.ps1 -ProjectRoot C:\Comfy_UI_Main -ScopeManifestFile <this-manifest> -Message <checkpoint-message> -Execute"
  push_command_requires_explicit_user_intent = "Add -Push only after local commit result is inspected and pushing is explicitly selected."
  checkpoint_boundary = "Manifest evidence only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = $(if ($manifestReady) { "Use this manifest for one guarded checkpoint dry-run or execute path only after explicit checkpoint intent; then revalidate clean Git, deploy bundle, and runtime gates." } else { "Resolve the manifest blocker before any checkpoint execute path." })
}

$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 40) + [Environment]::NewLine, $utf8NoBom)

$markdown = @"
# Scoped Git Checkpoint Manifest

- created_at: $($record.created_at)
- result: $($record.result)
- ready_for_checkpoint_execute_after_explicit_intent: $($record.ready_for_checkpoint_execute_after_explicit_intent)
- checkpoint_intent_required: $($record.checkpoint_intent_required)
- dry_run_result: $($record.dry_run_result)
- dry_run_scope_changed_path_count: $($record.dry_run_scope_changed_path_count)
- dry_run_scope_excluded_changed_path_count: $($record.dry_run_scope_excluded_changed_path_count)

## Include Paths

$(@($includePaths | ForEach-Object { "- $_" }) -join [Environment]::NewLine)

## Exclude Paths

$(@($excludePaths | ForEach-Object { "- $_" }) -join [Environment]::NewLine)

## Boundary

$($record.checkpoint_boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote scoped Git checkpoint manifest: $outFileResolved"
$record | ConvertTo-Json -Depth 40
