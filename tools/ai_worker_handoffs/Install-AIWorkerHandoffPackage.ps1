[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [string]$PackageRoot = "",
  [string]$CodexHome = "C:\Users\kevin\.codex",
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
  $PackageRoot = $PSScriptRoot
}
$PackageRoot = (Resolve-Path -LiteralPath $PackageRoot).Path
$manifestPath = Join-Path $PackageRoot "worker_handoff_package_manifest.json"
if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Canonical package manifest missing: $manifestPath" }
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ($manifest.artifact_type -ne "ai_worker_handoff_canonical_package_manifest") { throw "Unexpected package manifest type." }

$lockPaths = @(
  (Join-Path $CodexHome "cursor_handoff\cursor_agent.lock"),
  (Join-Path $CodexHome "claude_subscription_handoff\claude_subscription.lock"),
  (Join-Path $CodexHome "ai_worker_dispatcher\dispatcher.lock"),
  (Join-Path $CodexHome "ai_worker_dispatcher\admission.lock"),
  (Join-Path $CodexHome "ai_worker_dispatcher\locks\cursor.lock"),
  (Join-Path $CodexHome "ai_worker_dispatcher\locks\claude.lock"),
  (Join-Path $CodexHome "ai_worker_dispatcher\locks\lifecycle.lock")
)
$activeLocks = @($lockPaths | Where-Object { Test-Path -LiteralPath $_ })
if ($Apply -and $activeLocks.Count -gt 0) { throw "Worker package installation blocked by active lock(s): $($activeLocks -join ', ')" }

function Get-Destination {
  param([string]$RelativePath)
  $parts = $RelativePath.Replace("/", "\").Split("\")
  switch ($parts[0]) {
    "claude" { return Join-Path $CodexHome ("claude_subscription_handoff\" + ($parts[1..($parts.Count - 1)] -join "\")) }
    "cursor" { return Join-Path $CodexHome ("cursor_handoff\" + ($parts[1..($parts.Count - 1)] -join "\")) }
    "dispatcher" { return Join-Path $CodexHome ("ai_worker_dispatcher\" + ($parts[1..($parts.Count - 1)] -join "\")) }
    "automations" {
      $id = [IO.Path]::GetFileNameWithoutExtension($parts[-1])
      return Join-Path $CodexHome ("automations\$id\automation.toml")
    }
    default { throw "Unsupported canonical package path: $RelativePath" }
  }
}

$stamp = Get-Date -Format "yyyyMMddTHHmmsszzz"
$stamp = $stamp.Replace(":", "")
$backupRoot = Join-Path $CodexHome "ai_worker_handoff_package_backups\$stamp"
$results = @()
foreach ($entry in $manifest.files) {
  $source = Join-Path $PackageRoot ([string]$entry.relative_path).Replace("/", "\")
  if (!(Test-Path -LiteralPath $source -PathType Leaf)) { throw "Canonical source missing: $source" }
  $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($sourceHash -ne ([string]$entry.sha256).ToLowerInvariant()) { throw "Canonical source hash mismatch: $($entry.relative_path)" }
  $destination = Get-Destination -RelativePath ([string]$entry.relative_path)
  $beforeHash = if (Test-Path -LiteralPath $destination -PathType Leaf) { (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() } else { "MISSING" }
  $changed = $beforeHash -ne $sourceHash
  if ($Apply -and $changed) {
    $backup = Join-Path $backupRoot ([string]$entry.relative_path).Replace("/", "\")
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
      Copy-Item -LiteralPath $destination -Destination $backup
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
  $afterHash = if ($Apply) { (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() } else { $beforeHash }
  if ($Apply -and $afterHash -ne $sourceHash) { throw "Installed file hash mismatch: $destination" }
  $results += [ordered]@{ relative_path = $entry.relative_path; destination = $destination; changed = $changed; before_sha256 = $beforeHash; canonical_sha256 = $sourceHash; after_sha256 = $afterHash }
}

[ordered]@{
  status = "PASS"
  classification = $(if ($Apply) { "AI_WORKER_HANDOFF_PACKAGE_INSTALLED" } else { "AI_WORKER_HANDOFF_PACKAGE_INSTALL_DRY_RUN" })
  applied = [bool]$Apply
  active_locks = $activeLocks
  changed_file_count = @($results | Where-Object { $_.changed }).Count
  backup_root = $(if ($Apply) { $backupRoot } else { $null })
  files = $results
} | ConvertTo-Json -Depth 8
