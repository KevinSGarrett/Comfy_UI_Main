# Run-Wave07-SceneDirectorValidation.ps1
# Validates Wave07 Scene Director static package from repo root.

param(
  [string]$RepoRoot = "C:\Comfy_UI_Main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
  python ".\07_IMPLEMENTATION\scripts\run_wave07_local_validation.py" --root "."
}
finally {
  Pop-Location
}
