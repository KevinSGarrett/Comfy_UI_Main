param(
    [string]$Root = "."
)

$ErrorActionPreference = "Stop"

Write-Host "Running Wave 15 base lane local validation..."
python ".\07_IMPLEMENTATION\scripts\run_wave15_local_validation.py" --root $Root --out "11_RELEASES/WAVE15_VALIDATION_REPORT.json"
if ($LASTEXITCODE -ne 0) {
    throw "Wave 15 validation failed with exit code $LASTEXITCODE"
}
Write-Host "Wave 15 validation complete."
