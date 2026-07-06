param(
  [string]$RequestPath = "manifests\ec2_runtime_proof\request.json",
  [switch]$DryRun = $true
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $RequestPath)) {
  throw "Missing EC2 runtime proof request: $RequestPath"
}

$request = Get-Content $RequestPath -Raw | ConvertFrom-Json

if ($request.confirmation_token -ne "START_EC2_RUNTIME_PROOF") {
  throw "EC2 start blocked: confirmation_token must equal START_EC2_RUNTIME_PROOF"
}

if (-not $request.stop_instance_after) {
  throw "EC2 start blocked: stop_instance_after must be true"
}

if (-not $request.workflows -or $request.workflows.Count -lt 1) {
  throw "EC2 start blocked: no workflows listed"
}

if (-not $request.model_assets -or $request.model_assets.Count -lt 1) {
  throw "EC2 start blocked: no model assets listed"
}

Write-Host "EC2 proof request validated."
Write-Host "DryRun: $DryRun"

if ($DryRun) {
  Write-Host "DRY RUN ONLY: would start EC2 after final approval."
  exit 0
}

Write-Host "LIVE EC2 START WOULD OCCUR HERE ONLY IN FUTURE IMPLEMENTATION."
throw "Live EC2 start is intentionally not implemented in Wave 01."
