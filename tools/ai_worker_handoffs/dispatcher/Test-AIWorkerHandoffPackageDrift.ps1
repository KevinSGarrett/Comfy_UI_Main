[CmdletBinding()]
param(
  [string]$ManifestPath = "",
  [string]$CodexHome = "C:\Users\kevin\.codex"
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
  $ManifestPath = Join-Path $PSScriptRoot "canonical_package_manifest.json"
}
if (!(Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
  throw "Installed canonical package manifest missing: $ManifestPath"
}
$manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
if ($manifest.artifact_type -ne "ai_worker_handoff_canonical_package_manifest") {
  throw "Unexpected installed package manifest type."
}

function Get-Destination {
  param([string]$RelativePath)
  $parts = $RelativePath.Replace("/", "\").Split("\")
  if ($parts[0] -eq "claude") { return Join-Path $CodexHome ("claude_subscription_handoff\" + ($parts[1..($parts.Count - 1)] -join "\")) }
  if ($parts[0] -eq "cursor") { return Join-Path $CodexHome ("cursor_handoff\" + ($parts[1..($parts.Count - 1)] -join "\")) }
  if ($parts[0] -eq "dispatcher") { return Join-Path $CodexHome ("ai_worker_dispatcher\" + ($parts[1..($parts.Count - 1)] -join "\")) }
  if ($parts[0] -eq "automations") {
    $id = [IO.Path]::GetFileNameWithoutExtension($parts[-1])
    return Join-Path $CodexHome ("automations\$id\automation.toml")
  }
  throw "Unsupported package path: $RelativePath"
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

$files = @($manifest.files | ForEach-Object {
  $destination = Get-Destination -RelativePath ([string]$_.relative_path)
  $liveHash = if (Test-Path -LiteralPath $destination -PathType Leaf) {
    (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
  } else { "MISSING" }
  $isAutomation = [string]$_.relative_path -like "automations/*"
  $matches = if ($isAutomation -and $liveHash -ne "MISSING") {
    -not [string]::IsNullOrWhiteSpace([string]$_.semantic_sha256) -and
      (Get-AutomationSemanticHash -Path $destination) -eq ([string]$_.semantic_sha256).ToLowerInvariant()
  } else {
    $liveHash -eq ([string]$_.sha256).ToLowerInvariant()
  }
  [ordered]@{
    relative_path = $_.relative_path
    destination = $destination
    comparison_mode = $(if ($isAutomation) { "semantic_ignore_app_metadata_timestamps" } else { "exact_sha256" })
    live_matches_canonical = $matches
    canonical_sha256 = ([string]$_.sha256).ToLowerInvariant()
    live_sha256 = $liveHash
  }
})

$activeAutomationCount = 0
$activeAutomationContractFailures = @()
foreach ($entry in @($manifest.files | Where-Object { [string]$_.relative_path -like "automations/*" })) {
  $destination = Get-Destination -RelativePath ([string]$entry.relative_path)
  if (!(Test-Path -LiteralPath $destination -PathType Leaf)) { continue }
  $text = Get-Content -Raw -LiteralPath $destination
  if ($text -match '(?m)^status\s*=\s*"ACTIVE"\s*$') {
    $activeAutomationCount++
    $ok = $text -match '(?m)^model\s*=\s*"gpt-5\.4-mini"\s*$' -and
      $text -match '(?m)^reasoning_effort\s*=\s*"low"\s*$' -and
      $text -match 'C:\\\\Comfy_UI_Main'
    if (-not $ok) { $activeAutomationContractFailures += [string]$entry.relative_path }
  }
}

$failed = @($files | Where-Object { -not $_.live_matches_canonical })
$checks = [ordered]@{
  manifest_file_count_matches = ([int]$manifest.file_count -eq $files.Count)
  live_matches_canonical = ($failed.Count -eq 0)
  exact_cursor_model = ([string]$manifest.cursor_model -eq "gpt-5.3-codex")
  exact_claude_models = ((@($manifest.claude_models) -join ",") -eq "claude-sonnet-5,claude-opus-4-8")
  immutable_opus_ceiling = ([int]$manifest.immutable_opus_daily_ceiling -eq 2)
  active_automation_count = ($activeAutomationCount -eq 8)
  active_automation_contracts = ($activeAutomationContractFailures.Count -eq 0)
}
[ordered]@{
  status = $(if (@($checks.Values | Where-Object { $_ -eq $false }).Count -eq 0) { "PASS" } else { "FAIL" })
  classification = $(if ($failed.Count -eq 0) { "AI_WORKER_HANDOFF_PACKAGE_NO_DRIFT" } else { "AI_WORKER_HANDOFF_PACKAGE_DRIFT_DETECTED" })
  checks = $checks
  drift_count = $failed.Count
  drift = $failed
  active_automation_contract_failures = $activeAutomationContractFailures
} | ConvertTo-Json -Depth 8
