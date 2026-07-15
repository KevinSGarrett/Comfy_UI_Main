[CmdletBinding()]
param([string]$PackageRoot = "")

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
  $PackageRoot = $PSScriptRoot
}
$PackageRoot = (Resolve-Path -LiteralPath $PackageRoot).Path
$deployableRoots = @("claude", "cursor", "dispatcher", "automations")

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

$files = @()
foreach ($name in $deployableRoots) {
  $root = Join-Path $PackageRoot $name
  if (!(Test-Path -LiteralPath $root -PathType Container)) { throw "Canonical package directory missing: $root" }
  foreach ($item in Get-ChildItem -LiteralPath $root -File -Recurse | Sort-Object FullName) {
    $relative = $item.FullName.Substring($PackageRoot.Length).TrimStart("\").Replace("\", "/")
    $record = [ordered]@{
      relative_path = $relative
      bytes = $item.Length
      sha256 = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    if ($relative -like "automations/*") {
      $record["semantic_sha256"] = Get-AutomationSemanticHash -Path $item.FullName
    }
    $files += $record
  }
}

$manifest = [ordered]@{
  schema_version = 1
  artifact_type = "ai_worker_handoff_canonical_package_manifest"
  generated_at = (Get-Date).ToString("o")
  project_root = "C:/Comfy_UI_Main"
  cursor_model = "gpt-5.3-codex"
  claude_models = @("claude-sonnet-5", "claude-opus-4-8")
  immutable_opus_daily_ceiling = 2
  file_count = $files.Count
  files = $files
}
$outFile = Join-Path $PackageRoot "worker_handoff_package_manifest.json"
[IO.File]::WriteAllText($outFile, ($manifest | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
$manifest | ConvertTo-Json -Depth 8
