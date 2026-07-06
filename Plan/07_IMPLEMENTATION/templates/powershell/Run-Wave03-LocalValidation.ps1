# Wave03 local validation runner for Windows PowerShell.
# Runs static validation locally with EC2 off. Does not render images.
param(
  [string]$RepoRoot = "C:\Comfy_UI_Main",
  [string]$Workflow = "C:\Comfy_UI_Main\workflows\main\WAVE42_MAIN_FLOW_20260702.json",
  [string]$EnvFile = "C:\Comfy_UI_Main\.env",
  [string]$ObjectInfo = ""
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$OutDir = Join-Path $RepoRoot "Implementation\manifests\wave03_local_validation"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$Script = Join-Path $RepoRoot "07_IMPLEMENTATION\scripts\run_wave03_local_validation.py"

$argsList = @(
  $Script,
  "--repo-root", $RepoRoot,
  "--workflow", $Workflow,
  "--out-dir", $OutDir
)

if (Test-Path $EnvFile) {
  $argsList += @("--env-file", $EnvFile)
}

if ($ObjectInfo -ne "") {
  $argsList += @("--object-info", $ObjectInfo)
}

python @argsList

Write-Host ""
Write-Host "Wave03 validation outputs:"
Write-Host $OutDir
