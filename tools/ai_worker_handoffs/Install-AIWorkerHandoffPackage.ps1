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

function Get-AutomationSemanticHash {
  param([Parameter(Mandatory = $true)][string]$Path)
  $semanticLines = @(
    Get-Content -LiteralPath $Path |
      Where-Object { $_ -notmatch '^\s*(created_at|updated_at)\s*=' } |
      ForEach-Object { $_.TrimEnd() }
  )
  $sha = [Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [Text.Encoding]::UTF8.GetBytes(($semanticLines -join "`n") + "`n")
    return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
  } finally {
    $sha.Dispose()
  }
}

function Get-PortableAutomationHash {
  param([Parameter(Mandatory = $true)][string]$Path)
  $text = [IO.File]::ReadAllText($Path).Replace("`r`n", "`n").Replace("`r", "`n")
  $sha = [Security.Cryptography.SHA256]::Create()
  try {
    return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($text)))).Replace('-', '').ToLowerInvariant()
  } finally {
    $sha.Dispose()
  }
}

$stamp = Get-Date -Format "yyyyMMddTHHmmsszzz"
$stamp = $stamp.Replace(":", "")
$backupRoot = Join-Path $CodexHome "ai_worker_handoff_package_backups\$stamp"
$results = @()
foreach ($entry in $manifest.files) {
  $source = Join-Path $PackageRoot ([string]$entry.relative_path).Replace("/", "\")
  if (!(Test-Path -LiteralPath $source -PathType Leaf)) { throw "Canonical source missing: $source" }
  $isAutomation = [string]$entry.relative_path -like "automations/*"
  $sourceHash = if ($isAutomation) { Get-PortableAutomationHash -Path $source } else { (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() }
  if ($sourceHash -ne ([string]$entry.sha256).ToLowerInvariant()) { throw "Canonical source hash mismatch: $($entry.relative_path)" }
  $destination = Get-Destination -RelativePath ([string]$entry.relative_path)
  $beforeHash = if (Test-Path -LiteralPath $destination -PathType Leaf) { (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() } else { "MISSING" }
  if ($isAutomation -and [string]::IsNullOrWhiteSpace([string]$entry.semantic_sha256)) {
    throw "Automation semantic hash missing from manifest: $($entry.relative_path)"
  }
  $beforeMatches = if ($isAutomation -and $beforeHash -ne "MISSING") {
    (Get-AutomationSemanticHash -Path $destination) -eq ([string]$entry.semantic_sha256).ToLowerInvariant()
  } else {
    $beforeHash -eq $sourceHash
  }
  $changed = -not $beforeMatches
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
  $afterMatches = if ($isAutomation -and $Apply) {
    (Get-AutomationSemanticHash -Path $destination) -eq ([string]$entry.semantic_sha256).ToLowerInvariant()
  } else {
    $afterHash -eq $sourceHash
  }
  if ($Apply -and -not $afterMatches) { throw "Installed file verification failed: $destination" }
  $results += [ordered]@{
    relative_path = $entry.relative_path
    destination = $destination
    comparison_mode = $(if ($isAutomation) { "semantic_ignore_app_metadata_timestamps" } else { "exact_sha256" })
    changed = $changed
    before_sha256 = $beforeHash
    canonical_sha256 = $sourceHash
    after_sha256 = $afterHash
  }
}

$snapshotDestination = Join-Path $CodexHome "ai_worker_dispatcher\canonical_package_manifest.json"
$snapshotBeforeHash = if (Test-Path -LiteralPath $snapshotDestination -PathType Leaf) {
  (Get-FileHash -LiteralPath $snapshotDestination -Algorithm SHA256).Hash.ToLowerInvariant()
} else { "MISSING" }
$snapshotCanonicalHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$snapshotChanged = $snapshotBeforeHash -ne $snapshotCanonicalHash
if ($Apply -and $snapshotChanged) {
  if (Test-Path -LiteralPath $snapshotDestination -PathType Leaf) {
    $snapshotBackup = Join-Path $backupRoot "dispatcher\canonical_package_manifest.json"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $snapshotBackup) | Out-Null
    Copy-Item -LiteralPath $snapshotDestination -Destination $snapshotBackup -Force
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $snapshotDestination) | Out-Null
  Copy-Item -LiteralPath $manifestPath -Destination $snapshotDestination -Force
}
$snapshotAfterHash = if ($Apply) {
  (Get-FileHash -LiteralPath $snapshotDestination -Algorithm SHA256).Hash.ToLowerInvariant()
} else { $snapshotBeforeHash }
if ($Apply -and $snapshotAfterHash -ne $snapshotCanonicalHash) {
  throw "Installed canonical package manifest verification failed: $snapshotDestination"
}

[ordered]@{
  status = "PASS"
  classification = $(if ($Apply) { "AI_WORKER_HANDOFF_PACKAGE_INSTALLED" } else { "AI_WORKER_HANDOFF_PACKAGE_INSTALL_DRY_RUN" })
  applied = [bool]$Apply
  active_locks = $activeLocks
  changed_file_count = @($results | Where-Object { $_.changed }).Count
  manifest_snapshot_changed = $snapshotChanged
  manifest_snapshot_path = $snapshotDestination
  backup_root = $(if ($Apply) { $backupRoot } else { $null })
  files = $results
} | ConvertTo-Json -Depth 8
