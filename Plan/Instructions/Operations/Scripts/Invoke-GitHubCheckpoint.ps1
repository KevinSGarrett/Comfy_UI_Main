<#
.SYNOPSIS
Creates a guarded GitHub checkpoint after checking for common secret/binary mistakes.
Requires -Execute to commit/push. Without -Execute, reports intended actions.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$Message = "Wave checkpoint: verified autonomous update",
  [string]$OutFile = "",
  [string]$ScopeManifestFile = "",
  [string[]]$IncludePath = @(),
  [string[]]$ExcludePath = @(),
  [switch]$Push,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 40
  )

  $dir = Split-Path -Parent $Path
  if (![string]::IsNullOrWhiteSpace($dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

$blockedPatterns = @(
  "\.env$",
  "\.pem$",
  "\.key$",
  "\.p12$",
  "\.pfx$",
  "\.safetensors$",
  "\.ckpt$",
  "\.pt$",
  "\.pth$",
  "\.onnx$",
  "\.bin$",
  "\.gguf$"
)

function Test-BlockedPath {
  param([Parameter(Mandatory=$true)][string]$Path)

  foreach ($pat in $blockedPatterns) {
    if ($Path -match $pat) { return $true }
  }
  return $false
}

function Assert-NoBlockedStagedPath {
  param([string[]]$Files)

  foreach ($file in @($Files)) {
    if (Test-BlockedPath -Path $file) {
      throw "Blocked staged file detected: $file"
    }
  }
  Write-Host "Blocked path scan: pass"
}

function Get-StagedContentFiles {
  $files = git diff --cached --name-only --diff-filter=ACMRT 2>$null
  return @($files | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
}

function Find-StagedSecretMatch {
  param([string[]]$Files)

  $secretRules = @(
    [ordered]@{ name = "github_classic_token"; pattern = "ghp_[A-Za-z0-9_]{30,}" },
    [ordered]@{ name = "github_fine_grained_token"; pattern = "github_pat_[A-Za-z0-9_]{40,}" },
    [ordered]@{ name = "aws_access_key_id"; pattern = "AKIA[0-9A-Z]{16}" },
    [ordered]@{ name = "aws_secret_access_key_assignment"; pattern = "(?i)aws_secret_access_key\s*=\s*(?!$|<|`"|\s|REDACTED|placeholder|your_|CHANGEME|example|\[|\(|\{|AWS_ACCESS_KEY_ID\b|CIVITAI_API_KEY\b|GITHUB_TOKEN\b)[^#\s]+" },
    [ordered]@{ name = "civitai_api_key_assignment"; pattern = "(?i)civitai_api_key\s*=\s*(?!$|<|`"|\s|REDACTED|placeholder|your_|CHANGEME|example|\[|\(|\{|CIVITAI_AUTH_MODE\b|AWS_SECRET_ACCESS_KEY\b|AWS_ACCESS_KEY_ID\b|GITHUB_TOKEN\b)[^#\s]+" }
  )

  $findings = @()
  foreach ($file in @($Files)) {
    $content = git show --textconv ":$file" 2>$null
    if ($LASTEXITCODE -ne 0) { continue }

    $lineNumber = 0
    foreach ($line in @($content)) {
      $lineNumber += 1
      foreach ($rule in $secretRules) {
        if ($line -match $rule.pattern) {
          $findings += [pscustomobject]@{
            file = $file
            line = $lineNumber
            rule = $rule.name
          }
        }
      }
    }
  }
  return $findings
}

function Assert-NoStagedSecret {
  $contentFiles = Get-StagedContentFiles
  $matches = Find-StagedSecretMatch -Files $contentFiles
  if (@($matches).Count -gt 0) {
    Write-Host "Staged secret scan failed. Redacted findings:"
    $matches | ConvertTo-Json -Depth 4
    throw "Blocked staged secret pattern detected. No values were printed."
  }
  Write-Host "Staged secret scan: pass"
}

function Get-GitValue {
  param([string[]]$Arguments)
  $value = & git @Arguments 2>$null
  if ($LASTEXITCODE -ne 0) { return $null }
  return [string]($value | Select-Object -First 1)
}

function ConvertTo-GitRelativePath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  $value = $Path.Trim().Replace("\", "/")
  while ($value.StartsWith("./")) {
    $value = $value.Substring(2)
  }
  return $value.Trim("/")
}

function Test-GitPathUnderRoot {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Root
  )

  $normalizedPath = ConvertTo-GitRelativePath -Path $Path
  $normalizedRoot = ConvertTo-GitRelativePath -Path $Root
  if ([string]::IsNullOrWhiteSpace($normalizedPath) -or [string]::IsNullOrWhiteSpace($normalizedRoot)) { return $false }
  return ($normalizedPath -eq $normalizedRoot -or $normalizedPath.StartsWith("$normalizedRoot/"))
}

function ConvertTo-Array {
  param([object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [System.Array]) { return @($Value) }
  return @($Value)
}

function Expand-CheckpointPathValues {
  param([object[]]$Values)

  $expanded = @()
  foreach ($value in @($Values)) {
    if ($null -eq $value) { continue }
    foreach ($part in ([string]$value -split "[,;]")) {
      $normalized = ConvertTo-GitRelativePath -Path $part
      if (![string]::IsNullOrWhiteSpace($normalized)) {
        $expanded += $normalized
      }
    }
  }
  return $expanded
}

function Resolve-CheckpointScope {
  param(
    [string]$ManifestFile,
    [string[]]$RequestedIncludePath,
    [string[]]$RequestedExcludePath
  )

  $mode = "default_plan_only"
  $manifestPath = ""
  $manifestValid = $false
  $manifestError = $null
  $includes = @(Expand-CheckpointPathValues -Values $RequestedIncludePath)
  $excludes = @(Expand-CheckpointPathValues -Values $RequestedExcludePath)

  if (![string]::IsNullOrWhiteSpace($ManifestFile)) {
    $mode = "explicit_manifest"
    $manifestPath = $ManifestFile
    try {
      $resolvedManifest = $ManifestFile
      if (-not [System.IO.Path]::IsPathRooted($resolvedManifest)) {
        $resolvedManifest = Join-Path $ProjectRoot $resolvedManifest
      }
      $manifest = Get-Content -LiteralPath $resolvedManifest -Raw | ConvertFrom-Json
      $manifestPath = $resolvedManifest
      $manifestValid = $true
      $manifestIncludes = @()
      $manifestExcludes = @()
      foreach ($prop in @("include_paths", "checkpoint_include_paths", "intended_include_roots")) {
        if ($manifest.PSObject.Properties.Name -contains $prop) {
          $manifestIncludes += @(ConvertTo-Array -Value $manifest.$prop)
        }
      }
      foreach ($prop in @("exclude_paths", "checkpoint_exclude_paths", "intended_exclude_roots", "intended_preserve_local_roots", "intended_do_not_stage_roots")) {
        if ($manifest.PSObject.Properties.Name -contains $prop) {
          $manifestExcludes += @(ConvertTo-Array -Value $manifest.$prop)
        }
      }
      $includes += @(Expand-CheckpointPathValues -Values $manifestIncludes)
      $excludes += @(Expand-CheckpointPathValues -Values $manifestExcludes)
    } catch {
      $manifestValid = $false
      $manifestError = $_.Exception.Message
    }
  } elseif (@($includes).Count -gt 0 -or @($excludes).Count -gt 0) {
    $mode = "explicit_paths"
  }

  if (@($includes).Count -eq 0) {
    $includes = @("Plan")
    if ($mode -ne "explicit_manifest") { $mode = "default_plan_only" }
  }

  $includes = @($includes | Select-Object -Unique)
  $excludes = @($excludes | Select-Object -Unique)

  return [ordered]@{
    mode = $mode
    manifest_path = $manifestPath
    manifest_valid = $manifestValid
    manifest_error = $manifestError
    include_paths = $includes
    exclude_paths = $excludes
  }
}

function Get-PorcelainPath {
  param([string]$Line)
  if ([string]::IsNullOrWhiteSpace($Line)) { return "" }
  if ($Line.Length -gt 3) { return (ConvertTo-GitRelativePath -Path $Line.Substring(3).Trim()) }
  return (ConvertTo-GitRelativePath -Path $Line.Trim())
}

function Test-InCheckpointScope {
  param(
    [string]$Path,
    [string[]]$Includes,
    [string[]]$Excludes
  )

  $included = $false
  foreach ($include in @($Includes)) {
    if (Test-GitPathUnderRoot -Path $Path -Root $include) {
      $included = $true
      break
    }
  }
  if (-not $included) { return $false }
  foreach ($exclude in @($Excludes)) {
    if (Test-GitPathUnderRoot -Path $Path -Root $exclude) { return $false }
  }
  return $true
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$scope = Resolve-CheckpointScope -ManifestFile $ScopeManifestFile -RequestedIncludePath $IncludePath -RequestedExcludePath $ExcludePath
$changed = @(git status --porcelain 2>$null)
$changedPaths = @($changed | ForEach-Object { Get-PorcelainPath -Line $_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
$scopeChangedPaths = @($changedPaths | Where-Object { Test-InCheckpointScope -Path $_ -Includes @($scope.include_paths) -Excludes @($scope.exclude_paths) })
$scopeExcludedChangedPaths = @($changedPaths | Where-Object { -not (Test-InCheckpointScope -Path $_ -Includes @($scope.include_paths) -Excludes @($scope.exclude_paths)) })
$branchStatus = [string](@(git status --short --branch 2>$null | Select-Object -First 1) | Select-Object -First 1)
$head = Get-GitValue -Arguments @("rev-parse", "HEAD")
$originMain = Get-GitValue -Arguments @("rev-parse", "origin/main")
$untracked = @($changed | Where-Object { $_ -match "^\?\?" })
$trackedPorcelain = @($changed | Where-Object { $_ -notmatch "^\?\?" })
$staged = @($trackedPorcelain | Where-Object { $_.Length -gt 0 -and $_.Substring(0, 1) -ne " " })
$unstaged = @($trackedPorcelain | Where-Object { $_.Length -gt 1 -and $_.Substring(1, 1) -ne " " })
$blockedChangedPaths = @($changed | ForEach-Object {
  if ($_.Length -gt 3) { $_.Substring(3).Trim() } else { $_.Trim() }
} | Where-Object { ![string]::IsNullOrWhiteSpace($_) -and (Test-BlockedPath -Path $_) })
$stagedSecretMatches = @(Find-StagedSecretMatch -Files (Get-StagedContentFiles))
$cleanWorktree = (@($changed).Count -eq 0)
$localMatchesOrigin = (![string]::IsNullOrWhiteSpace($head) -and ![string]::IsNullOrWhiteSpace($originMain) -and $head -eq $originMain)
$dryRunWouldCommit = (@($changed).Count -gt 0 -and @($blockedChangedPaths).Count -eq 0 -and @($stagedSecretMatches).Count -eq 0)
$result = "blocked_git_checkpoint_dirty_worktree"
$failureCategory = "local_git_worktree_dirty"
if ($cleanWorktree -and $localMatchesOrigin) {
  $result = "pass_git_checkpoint_ready"
  $failureCategory = $null
} elseif ($cleanWorktree -and -not $localMatchesOrigin) {
  $result = "blocked_git_checkpoint_not_synced_to_origin"
  $failureCategory = "local_git_not_synced_to_origin"
} elseif (@($blockedChangedPaths).Count -gt 0) {
  $result = "blocked_git_checkpoint_blocked_paths"
  $failureCategory = "blocked_changed_paths_present"
} elseif (@($stagedSecretMatches).Count -gt 0) {
  $result = "blocked_git_checkpoint_staged_secret_pattern"
  $failureCategory = "staged_secret_pattern_detected"
} elseif ([string]$scope.mode -eq "explicit_manifest" -and -not [bool]$scope.manifest_valid) {
  $result = "blocked_git_checkpoint_invalid_scope_manifest"
  $failureCategory = "invalid_scope_manifest"
}
$record = [ordered]@{
  evidence_id = "W66-GITHUB-CHECKPOINT-DRY-RUN-$stamp"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  artifact_type = "github_checkpoint_gate_dry_run"
  project_root = $ProjectRoot
  local_only = $true
  github_api_contacted = $false
  aws_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  execute_requested = [bool]$Execute
  push_requested = [bool]$Push
  commit_attempted = $false
  push_attempted = $false
  stage_attempted = $false
  reset_attempted = $false
  checkout_attempted = $false
  result = $result
  failure_category = $failureCategory
  checkpoint_scope_mode = $scope.mode
  checkpoint_scope_manifest = $scope.manifest_path
  checkpoint_scope_manifest_valid = $scope.manifest_valid
  checkpoint_scope_manifest_error = $scope.manifest_error
  checkpoint_include_paths = @($scope.include_paths)
  checkpoint_exclude_paths = @($scope.exclude_paths)
  scope_changed_path_count = @($scopeChangedPaths).Count
  scope_excluded_changed_path_count = @($scopeExcludedChangedPaths).Count
  scope_changed_preview = @($scopeChangedPaths | Select-Object -First 80)
  scope_excluded_changed_preview = @($scopeExcludedChangedPaths | Select-Object -First 80)
  head = $head
  origin_main = $originMain
  local_matches_origin = $localMatchesOrigin
  clean_worktree = $cleanWorktree
  porcelain_count = @($changed).Count
  tracked_porcelain_count = @($trackedPorcelain).Count
  untracked_porcelain_count = @($untracked).Count
  staged_count = @($staged).Count
  unstaged_count = @($unstaged).Count
  blocked_changed_path_count = @($blockedChangedPaths).Count
  staged_secret_match_count = @($stagedSecretMatches).Count
  branch_status = $branchStatus
  changed_preview = @($changed | Select-Object -First 80)
  blocked_changed_paths = @($blockedChangedPaths | Select-Object -First 80)
  staged_secret_matches = $stagedSecretMatches
  next_action = $(if ($cleanWorktree -and $localMatchesOrigin) { "Use this gate immediately before any explicitly selected EC2 execute path." } else { "Do not start EC2 or run target-runtime execution until the worktree is intentionally checkpointed clean and local HEAD equals origin/main." })
}
Write-Host "Changed files: $(@($changed).Count)"
if (@($changed).Count -gt 0) {
  Write-Host "Changed file preview:"
  @($changed | Select-Object -First 80)
}

if ($staged) {
  Assert-NoBlockedStagedPath -Files $staged
  Assert-NoStagedSecret
}

if (-not $Execute) {
  if (![string]::IsNullOrWhiteSpace($OutFile)) {
    Write-JsonNoBom -Value $record -Path $OutFile -Depth 40
    Write-Host "Wrote GitHub checkpoint dry-run evidence: $OutFile"
  }
  $record | ConvertTo-Json -Depth 40
  Write-Host "DRY RUN: no commit or push performed. Re-run with -Execute to commit. Add -Push to push."
  exit 0
}

$record.stage_attempted = $true
foreach ($path in @($scope.include_paths)) {
  git add -- $path
}
$record.commit_attempted = $true
$stagedAfter = git diff --cached --name-only 2>$null
if (-not $stagedAfter) {
  Write-Host "Nothing staged after git add for checkpoint include paths."
  exit 0
}

foreach ($file in @($stagedAfter)) {
  foreach ($exclude in @($scope.exclude_paths)) {
    if (Test-GitPathUnderRoot -Path $file -Root $exclude) {
      git restore --staged -- $file
      $record.reset_attempted = $true
      break
    }
  }
}

$stagedAfter = git diff --cached --name-only 2>$null

foreach ($file in $stagedAfter) {
  if (Test-BlockedPath -Path $file) {
    git restore --staged $file
    throw "Blocked file unstaged: $file"
  }
}
Write-Host "Blocked path scan: pass"
Assert-NoStagedSecret

git commit -m $Message
if ($Push) {
  $record.push_attempted = $true
  git push origin main
}
$record.head = Get-GitValue -Arguments @("rev-parse", "HEAD")
$record.origin_main = Get-GitValue -Arguments @("rev-parse", "origin/main")
$record.local_matches_origin = (![string]::IsNullOrWhiteSpace($record.head) -and ![string]::IsNullOrWhiteSpace($record.origin_main) -and $record.head -eq $record.origin_main)
$record.clean_worktree = (@(git status --porcelain).Count -eq 0)
$record.result = $(if ($record.clean_worktree -and $record.local_matches_origin) { "pass_git_checkpoint_committed" } elseif ($record.clean_worktree) { "checkpoint_committed_not_pushed" } else { "checkpoint_committed_worktree_still_dirty" })
$record.failure_category = $(if ($record.clean_worktree -and $record.local_matches_origin) { $null } elseif (-not $record.clean_worktree) { "local_git_worktree_dirty" } else { "local_git_not_synced_to_origin" })
if (![string]::IsNullOrWhiteSpace($OutFile)) {
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 40
  Write-Host "Wrote GitHub checkpoint evidence: $OutFile"
}
$record.head
