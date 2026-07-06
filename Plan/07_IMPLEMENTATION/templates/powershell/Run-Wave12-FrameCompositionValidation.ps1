param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Write-Host "Running Wave12 frame composition static validation..."
& $Python "$ProjectRoot\07_IMPLEMENTATION\scripts\run_wave12_local_validation.py" --root $ProjectRoot
Write-Host "Wave12 validation complete."
