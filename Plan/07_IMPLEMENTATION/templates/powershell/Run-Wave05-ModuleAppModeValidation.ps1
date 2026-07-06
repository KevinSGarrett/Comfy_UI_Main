param(
  [string]$PackRoot = "."
)

$ErrorActionPreference = "Stop"

Write-Host "Wave 05 module/App Mode validation starting..."
$script = Join-Path $PackRoot "07_IMPLEMENTATION\scripts\validate_wave05_module_appmode_pack.py"

if (!(Test-Path $script)) {
  throw "Missing validation script: $script"
}

python $script --pack-root $PackRoot

if ($LASTEXITCODE -ne 0) {
  throw "Wave 05 validation failed."
}

Write-Host "Wave 05 validation completed."
