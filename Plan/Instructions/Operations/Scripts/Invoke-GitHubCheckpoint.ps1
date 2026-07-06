<#
.SYNOPSIS
Creates a guarded GitHub checkpoint after checking for common secret/binary mistakes.
Requires -Execute to commit/push. Without -Execute, reports intended actions.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$Message = "Wave checkpoint: verified autonomous update",
  [switch]$Push,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

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
  $files = git diff --cached --name-only --diff-filter=ACMRT
  return @($files | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
}

function Find-StagedSecretMatch {
  param([string[]]$Files)

  $secretRules = @(
    [ordered]@{ name = "github_classic_token"; pattern = "ghp_[A-Za-z0-9_]{30,}" },
    [ordered]@{ name = "github_fine_grained_token"; pattern = "github_pat_[A-Za-z0-9_]{40,}" },
    [ordered]@{ name = "aws_access_key_id"; pattern = "AKIA[0-9A-Z]{16}" },
    [ordered]@{ name = "aws_secret_access_key_assignment"; pattern = "(?i)aws_secret_access_key\s*=\s*[^#\s]+" },
    [ordered]@{ name = "civitai_api_key_assignment"; pattern = "(?i)civitai_api_key\s*=\s*(?!$|<|`"|\s|REDACTED|placeholder|your_|CHANGEME|example)[^#\s]+" }
  )

  $matches = @()
  foreach ($file in @($Files)) {
    $content = git show --textconv ":$file" 2>$null
    if ($LASTEXITCODE -ne 0) { continue }

    $lineNumber = 0
    foreach ($line in @($content)) {
      $lineNumber += 1
      foreach ($rule in $secretRules) {
        if ($line -match $rule.pattern) {
          $matches += [ordered]@{
            file = $file
            line = $lineNumber
            rule = $rule.name
          }
        }
      }
    }
  }
  return $matches
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

$changed = git status --porcelain
Write-Host "Changed files:"
$changed

$staged = git diff --cached --name-only
if ($staged) {
  Assert-NoBlockedStagedPath -Files $staged
  Assert-NoStagedSecret
}

if (-not $Execute) {
  Write-Host "DRY RUN: no commit or push performed. Re-run with -Execute to commit. Add -Push to push."
  exit 0
}

git add Plan
$stagedAfter = git diff --cached --name-only
if (-not $stagedAfter) {
  Write-Host "Nothing staged after git add Plan."
  exit 0
}

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
  git push origin main
}
git rev-parse HEAD
