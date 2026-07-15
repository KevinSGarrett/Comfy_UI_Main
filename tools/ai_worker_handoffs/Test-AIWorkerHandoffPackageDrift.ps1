[CmdletBinding()]
param(
  [string]$PackageRoot = "",
  [string]$CodexHome = "C:\Users\kevin\.codex"
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
  $PackageRoot = $PSScriptRoot
}
$PackageRoot = (Resolve-Path -LiteralPath $PackageRoot).Path
$manifest = Get-Content -Raw -LiteralPath (Join-Path $PackageRoot "worker_handoff_package_manifest.json") | ConvertFrom-Json

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
  $text = ($semanticLines -join "`n") + "`n"
  $sha = [Security.Cryptography.SHA256]::Create()
  try {
    return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($text)))).Replace('-', '').ToLowerInvariant()
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

$files = @($manifest.files | ForEach-Object {
  $source = Join-Path $PackageRoot ([string]$_.relative_path).Replace("/", "\")
  $destination = Get-Destination -RelativePath ([string]$_.relative_path)
  $isAutomation = [string]$_.relative_path -like 'automations/*'
  $canonicalHash = if ($isAutomation) { Get-PortableAutomationHash -Path $source } else { (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() }
  $liveHash = if (Test-Path -LiteralPath $destination -PathType Leaf) { (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() } else { "MISSING" }
  $semanticMatch = $false
  if ($isAutomation -and $liveHash -ne 'MISSING') {
    $semanticMatch = (Get-AutomationSemanticHash -Path $source) -eq (Get-AutomationSemanticHash -Path $destination)
  }
  [ordered]@{
    relative_path = $_.relative_path
    destination = $destination
    comparison_mode = $(if ($isAutomation) { 'semantic_ignore_app_metadata_timestamps' } else { 'exact_sha256' })
    manifest_hash_valid = ($canonicalHash -eq ([string]$_.sha256).ToLowerInvariant())
    live_matches_canonical = $(if ($isAutomation) { $semanticMatch } else { $liveHash -eq $canonicalHash })
    canonical_sha256 = $canonicalHash
    live_sha256 = $liveHash
  }
})

$automationFiles = @($manifest.files | Where-Object { [string]$_.relative_path -like "automations/*" })
$activeAutomationCount = 0
$activeAutomationContractFailures = @()
foreach ($entry in $automationFiles) {
  $text = Get-Content -Raw -LiteralPath (Join-Path $PackageRoot ([string]$entry.relative_path).Replace("/", "\"))
  if ($text -match '(?m)^status\s*=\s*"ACTIVE"\s*$') {
    $activeAutomationCount++
    $ok = $text -match '(?m)^model\s*=\s*"gpt-5\.4-mini"\s*$' -and $text -match '(?m)^reasoning_effort\s*=\s*"low"\s*$' -and $text -match 'C:\\\\Comfy_UI_Main'
    if (-not $ok) { $activeAutomationContractFailures += [string]$entry.relative_path }
  }
}

$failed = @($files | Where-Object { -not $_.manifest_hash_valid -or -not $_.live_matches_canonical })
$checks = [ordered]@{
  manifest_file_count_matches = ([int]$manifest.file_count -eq $files.Count)
  manifest_hashes_valid = (@($files | Where-Object { -not $_.manifest_hash_valid }).Count -eq 0)
  live_matches_canonical = (@($files | Where-Object { -not $_.live_matches_canonical }).Count -eq 0)
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
