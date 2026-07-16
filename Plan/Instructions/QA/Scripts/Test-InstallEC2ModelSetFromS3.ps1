param([string]$ProjectRoot = "C:\Comfy_UI_Main")

$ErrorActionPreference = "Stop"
$script = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Install-EC2ModelSetFromS3.ps1"
$tempRoot = Join-Path $ProjectRoot "runtime_artifacts\tests\install_ec2_model_set"
$null = New-Item -ItemType Directory -Force -Path $tempRoot

function Write-JsonNoBom([object]$Value, [string]$Path) {
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 20), $encoding)
}

$manifestPath = Join-Path $tempRoot "asset_manifest.json"
$outPath = Join-Path $tempRoot "dry_run.json"
$manifest = [ordered]@{
  schema_version = "1.0"
  lane_id = "flux2_dev_primary_base"
  assets = @(
    [ordered]@{ source_s3_uri="s3://example-bucket/model-cache/flux2/dev.safetensors"; model_subdir="diffusion_models"; filename="dev.safetensors"; sha256=("a" * 64); size_bytes=1234 },
    [ordered]@{ source_s3_uri="s3://example-bucket/model-cache/flux2/encoder.safetensors"; model_subdir="text_encoders"; filename="encoder.safetensors"; sha256=("b" * 64); size_bytes=5678 }
  )
}
Write-JsonNoBom -Value $manifest -Path $manifestPath

$json = & $script -ProjectRoot $ProjectRoot -AssetManifestFile $manifestPath -OutFile $outPath | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Valid dry run failed." }
if ($json.result -ne "dry_run_model_set_install_plan") { throw "Unexpected dry-run result: $($json.result)" }
if ($json.asset_count -ne 2 -or $json.execute -or $json.ec2_started -or $json.generation_executed) { throw "Dry-run boundaries are incorrect." }
if (!(Test-Path -LiteralPath $outPath)) { throw "Dry-run evidence was not written." }

$singleManifestPath = Join-Path $tempRoot "single_asset_manifest.json"
$singleOut = Join-Path $tempRoot "single_asset_dry_run.json"
$singleManifest = [ordered]@{ schema_version="1.0"; lane_id="single_asset_lane"; assets=@($manifest.assets[0]) }
Write-JsonNoBom -Value $singleManifest -Path $singleManifestPath
$single = & $script -ProjectRoot $ProjectRoot -AssetManifestFile $singleManifestPath -OutFile $singleOut | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $single.asset_count -ne 1) { throw "Single-asset manifest did not preserve array semantics." }

$invalidPath = Join-Path $tempRoot "invalid_manifest.json"
$invalidOut = Join-Path $tempRoot "invalid.json"
$manifest.assets[1].filename = "../escape.safetensors"
Write-JsonNoBom -Value $manifest -Path $invalidPath
$previous = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try { $invalidText = & $script -ProjectRoot $ProjectRoot -AssetManifestFile $invalidPath -OutFile $invalidOut 2>&1; $invalidExit = $LASTEXITCODE }
finally { $ErrorActionPreference = $previous }
if ($invalidExit -eq 0) { throw "Invalid manifest unexpectedly passed." }
$invalid = Get-Content -Raw -LiteralPath $invalidOut | ConvertFrom-Json
if ($invalid.result -ne "blocked_pre_ec2_validation" -or $invalid.validation_errors.Count -lt 1) { throw "Invalid manifest did not fail closed." }

$executeBlockedOut = Join-Path $tempRoot "execute_blocked.json"
$previous = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
  $executeBlockedText = & $script -ProjectRoot $ProjectRoot -AssetManifestFile $manifestPath -OutFile $executeBlockedOut -DeployBundleS3Uri "s3://example-bucket/deploy/test.zip" -DeployBundleSha256 ("c" * 64) -RuntimeWindowId "rw-test-model-set-001" -Execute 2>&1
  $executeBlockedExit = $LASTEXITCODE
} finally { $ErrorActionPreference = $previous }
if ($executeBlockedExit -eq 0) { throw "Execute without emergency-stop proof unexpectedly passed." }
$executeBlocked = Get-Content -Raw -LiteralPath $executeBlockedOut | ConvertFrom-Json
if ($executeBlocked.ec2_started -or $executeBlocked.result -ne "blocked_pre_ec2_validation" -or @($executeBlocked.validation_errors) -notmatch "emergency-stop") {
  throw "Missing emergency-stop proof did not block before EC2 start."
}

$source = Get-Content -Raw -LiteralPath $script
foreach ($required in @(
  'requires the approved instance to begin stopped',
  'model_set_install_hash_verified',
  'Get-EC2StartFailureCategory',
  'Get-EC2StopFailureCategory',
  'Stop/final-state verification failed:',
  'generation_executed = $false',
  'ConvertTo-Json -InputObject @($validatedAssets)',
  'Get-EmergencyStopScheduleStatus',
  'Set-EC2RuntimeWindowMarker.ps1',
  'Start-EC2InstanceStopWatchdog.ps1',
  'stop_capability_verified',
  'instance_stop_watchdog_started_and_capability_verified'
)) {
  if (!$source.Contains($required)) { throw "Installer is missing required guard: $required" }
}

[pscustomobject]@{ result="pass"; checks=22; script=$script } | ConvertTo-Json -Compress
exit 0
