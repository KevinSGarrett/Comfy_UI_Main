param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"
Push-Location $ProjectRoot
try {
  python .\07_IMPLEMENTATION\scripts\run_wave08_local_validation.py --root .
} finally {
  Pop-Location
}
