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

$changed = git status --porcelain
Write-Host "Changed files:"
$changed

$staged = git diff --cached --name-only
if ($staged) {
  foreach ($file in $staged) {
    foreach ($pat in $blockedPatterns) {
      if ($file -match $pat) {
        throw "Blocked staged file detected: $file"
      }
    }
  }
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
  foreach ($pat in $blockedPatterns) {
    if ($file -match $pat) {
      git restore --staged $file
      throw "Blocked file unstaged: $file"
    }
  }
}

git commit -m $Message
if ($Push) {
  git push origin main
}
git rev-parse HEAD
