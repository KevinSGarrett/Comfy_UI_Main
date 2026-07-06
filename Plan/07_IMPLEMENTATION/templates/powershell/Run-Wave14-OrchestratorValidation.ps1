param(
  [string]$Root = ".",
  [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
Write-Host "Running Wave14 local orchestrator validation..."
& $Python (Join-Path $Root "07_IMPLEMENTATION\scripts\run_wave14_local_validation.py") --root $Root --out (Join-Path $Root "11_RELEASES\WAVE14_VALIDATION_REPORT.json")
Write-Host "Wave14 validation complete."
