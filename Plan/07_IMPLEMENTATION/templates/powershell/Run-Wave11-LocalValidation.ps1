param(
  [string]$RepoRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"
Write-Host "Running Wave 11 local static validation from $RepoRoot"
python "$RepoRoot\07_IMPLEMENTATION\scripts\run_wave11_local_validation.py" --root "$RepoRoot"
