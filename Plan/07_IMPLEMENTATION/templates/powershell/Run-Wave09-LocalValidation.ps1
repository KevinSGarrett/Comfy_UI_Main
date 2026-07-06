param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"

Write-Host "Wave09 local validation starting..."
Push-Location $ProjectRoot
try {
  python .\07_IMPLEMENTATION\scripts\run_wave09_local_validation.py --root .
  Write-Host "Wave09 local validation complete."
}
finally {
  Pop-Location
}
