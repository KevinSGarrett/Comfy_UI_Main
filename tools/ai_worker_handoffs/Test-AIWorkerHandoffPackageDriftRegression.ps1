[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$temp = Join-Path $env:TEMP ('ai-worker-drift-' + [guid]::NewGuid().ToString('N'))
$package = (Resolve-Path $PSScriptRoot).Path
try {
  $portablePackage = Join-Path $temp 'portable-package'
  $portableHome = Join-Path $temp 'portable-home'
  New-Item -ItemType Directory -Force -Path $portablePackage | Out-Null
  Copy-Item -Path (Join-Path $package '*') -Destination $portablePackage -Recurse -Force
  $portableAutomation = Join-Path $portablePackage 'automations\comfy-ui-main-automation-fleet-health-supervisor-2.toml'
  $portableText = [IO.File]::ReadAllText($portableAutomation).Replace("`r`n", "`n").Replace("`r", "`n").Replace("`n", "`r`n")
  [IO.File]::WriteAllText($portableAutomation, $portableText, (New-Object Text.UTF8Encoding($false)))
  $portableInstall = & (Join-Path $portablePackage 'Install-AIWorkerHandoffPackage.ps1') -PackageRoot $portablePackage -CodexHome $portableHome -Apply | ConvertFrom-Json

  $install = & (Join-Path $package 'Install-AIWorkerHandoffPackage.ps1') -PackageRoot $package -CodexHome $temp -Apply | ConvertFrom-Json
  $id = 'comfy-ui-main-ec2-cost-safety-sentinel-2'
  $path = Join-Path $temp "automations\$id\automation.toml"
  $installedVerifier = Join-Path $temp 'ai_worker_dispatcher\Test-AIWorkerHandoffPackageDrift.ps1'
  $installedManifest = Join-Path $temp 'ai_worker_dispatcher\canonical_package_manifest.json'
  $text = Get-Content $path -Raw

  $metadataChanged = $text -replace '(?m)^updated_at\s*=\s*\d+\s*$', 'updated_at = 9999999999999'
  [IO.File]::WriteAllText($path, $metadataChanged, (New-Object Text.UTF8Encoding($false)))
  $reinstall = & (Join-Path $package 'Install-AIWorkerHandoffPackage.ps1') -PackageRoot $package -CodexHome $temp -Apply | ConvertFrom-Json
  $metadataPreserved = (Get-Content -Raw -LiteralPath $path) -match '(?m)^updated_at\s*=\s*9999999999999\s*$'
  $metadataResult = & $installedVerifier -ManifestPath $installedManifest -CodexHome $temp | ConvertFrom-Json

  $semanticChanged = $metadataChanged -replace 'RRULE:FREQ=HOURLY;INTERVAL=6', 'RRULE:FREQ=HOURLY;INTERVAL=5'
  [IO.File]::WriteAllText($path, $semanticChanged, (New-Object Text.UTF8Encoding($false)))
  $semanticResult = & $installedVerifier -ManifestPath $installedManifest -CodexHome $temp | ConvertFrom-Json

  $checks = [ordered]@{
    automation_line_endings_portable = ($portableInstall.status -eq 'PASS')
    package_installed = ($install.status -eq 'PASS')
    canonical_manifest_snapshot_installed = (Test-Path -LiteralPath $installedManifest -PathType Leaf)
    reinstall_accepted_semantic_automation_match = ($reinstall.status -eq 'PASS' -and $metadataPreserved)
    metadata_only_change_accepted = ($metadataResult.status -eq 'PASS')
    semantic_change_rejected = ($semanticResult.status -eq 'FAIL' -and $semanticResult.drift_count -eq 1)
  }
  $failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key })
  [ordered]@{
    status = $(if ($failed.Count) { 'FAIL' } else { 'PASS' })
    classification = 'AI_WORKER_AUTOMATION_SEMANTIC_DRIFT_REGRESSION'
    checks = $checks
    failed = $failed
  } | ConvertTo-Json -Depth 6
  if ($failed.Count) { exit 1 }
} finally {
  Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
}
