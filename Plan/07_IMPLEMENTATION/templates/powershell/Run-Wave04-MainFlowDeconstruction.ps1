param(
  [Parameter(Mandatory=$true)]
  [string]$WorkflowJson,

  [Parameter(Mandatory=$false)]
  [string]$OutDir = "C:\Comfy_UI_Main\reports\wave04_main_flow_deconstruction"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $WorkflowJson)) {
  throw "Workflow JSON not found: $WorkflowJson"
}

$ScriptPath = Join-Path $PSScriptRoot "..\scripts\deconstruct_main_flow_wave04.py"
$ScriptPath = [System.IO.Path]::GetFullPath($ScriptPath)

if (!(Test-Path $ScriptPath)) {
  throw "Python deconstruction script not found: $ScriptPath"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

python $ScriptPath --workflow $WorkflowJson --out-dir $OutDir

Write-Host "Wave 04 deconstruction complete."
Write-Host "Output: $OutDir"
