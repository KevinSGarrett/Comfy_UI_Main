[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$temp = Join-Path $env:TEMP ('ai-worker-drift-' + [guid]::NewGuid().ToString('N'))
$package = (Resolve-Path $PSScriptRoot).Path
try {
  $install = & (Join-Path $package 'Install-AIWorkerHandoffPackage.ps1') -PackageRoot $package -CodexHome $temp -Apply | ConvertFrom-Json
  $id = 'comfy-ui-main-ec2-cost-safety-sentinel-2'
  $path = Join-Path $temp "automations\$id\automation.toml"
  $text = Get-Content $path -Raw

  $metadataChanged = $text -replace '(?m)^updated_at\s*=\s*\d+\s*$', 'updated_at = 9999999999999'
  [IO.File]::WriteAllText($path, $metadataChanged, (New-Object Text.UTF8Encoding($false)))
  $metadataResult = & (Join-Path $package 'Test-AIWorkerHandoffPackageDrift.ps1') -PackageRoot $package -CodexHome $temp | ConvertFrom-Json

  $semanticChanged = $metadataChanged -replace 'RRULE:FREQ=HOURLY;INTERVAL=6', 'RRULE:FREQ=HOURLY;INTERVAL=5'
  [IO.File]::WriteAllText($path, $semanticChanged, (New-Object Text.UTF8Encoding($false)))
  $semanticResult = & (Join-Path $package 'Test-AIWorkerHandoffPackageDrift.ps1') -PackageRoot $package -CodexHome $temp | ConvertFrom-Json

  $checks = [ordered]@{
    package_installed = ($install.status -eq 'PASS')
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
