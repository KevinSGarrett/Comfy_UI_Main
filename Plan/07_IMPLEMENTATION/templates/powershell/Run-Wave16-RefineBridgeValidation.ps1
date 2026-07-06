param(
  [string]$Root = ".",
  [string]$Report = ".\11_RELEASES\WAVE16_VALIDATION_REPORT.json"
)

$ErrorActionPreference = "Stop"

$script = Join-Path $Root "07_IMPLEMENTATION\scripts\run_wave16_local_validation.py"
if (!(Test-Path $script)) {
  throw "Missing Wave16 validation script: $script"
}

python $script --root $Root --report $Report
if ($LASTEXITCODE -ne 0) {
  throw "Wave16 validation failed with exit code $LASTEXITCODE"
}
