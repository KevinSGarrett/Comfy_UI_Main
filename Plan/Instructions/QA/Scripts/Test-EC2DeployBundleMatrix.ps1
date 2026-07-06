<#
.SYNOPSIS
Validates local-only EC2 deploy bundle creation for a run package matrix.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RunPackageMatrixManifestFile = "runtime_artifacts\run_package_matrices\realvisxl_multisample_certification_v1\RUN_PACKAGE_MATRIX_MANIFEST.json",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function ConvertTo-ProjectRelativePath {
  param([string]$BasePath, [string]$TargetPath)
  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", $separator).Replace("\", "/")
}

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_EC2_DEPLOY_BUNDLE_MATRIX_$stamp.json"
}

$resolvedMatrixManifest = $RunPackageMatrixManifestFile
if (![System.IO.Path]::IsPathRooted($resolvedMatrixManifest)) {
  $resolvedMatrixManifest = Join-Path $ProjectRoot $resolvedMatrixManifest
}
$matrix = Read-JsonFile -Path $resolvedMatrixManifest
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "comfy_deploy_bundle_matrix_$stamp"
$bundleScript = Join-Path $ProjectRoot "tools\New-EC2DeployBundleMatrix.ps1"
$bundleOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $bundleScript `
  -ProjectRoot $ProjectRoot `
  -RunPackageMatrixManifestFile $resolvedMatrixManifest `
  -OutDir $tempRoot `
  -BundleName "deploy_bundle_matrix_validation_$stamp" 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "Deploy bundle matrix builder failed: $($bundleOutput | Out-String)"
}

$bundleManifestPath = Join-Path $tempRoot "DEPLOY_BUNDLE_MATRIX_MANIFEST.json"
$bundle = Read-JsonFile -Path $bundleManifestPath
$zipPath = Join-Path $tempRoot ([string]$bundle.bundle_zip)
$redactedZipPath = "[VALIDATION_TEMP_ROOT]/$($bundle.bundle_zip)"
$publishScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1"
$publishOutFile = Join-Path $tempRoot "PUBLISH_DEPLOY_BUNDLE_MATRIX_DRY_RUN.json"
$publishOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $publishScript `
  -BundleManifestFile $bundleManifestPath `
  -S3BaseUri "s3://example-bucket/deploy-bundles" `
  -OutFile $publishOutFile 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "Matrix deploy bundle S3 dry-run publish failed: $($publishOutput | Out-String)"
}
$publish = Read-JsonFile -Path $publishOutFile

$checks = @()
$checks += New-Check -Name "bundle_result_passes" -Passed ([string]$bundle.result -eq "pass_local_only") -Observed $bundle.result -Expected "pass_local_only"
$checks += New-Check -Name "bundle_matrix_matches" -Passed ([string]$bundle.matrix_id -eq [string]$matrix.matrix_id) -Observed $bundle.matrix_id -Expected $matrix.matrix_id
$checks += New-Check -Name "bundle_sample_count_matches" -Passed ([int]$bundle.sample_count -eq @($matrix.samples).Count) -Observed $bundle.sample_count -Expected @($matrix.samples).Count
$checks += New-Check -Name "bundle_zip_exists" -Passed (Test-Path -LiteralPath $zipPath) -Observed $redactedZipPath -Expected "zip exists"
$checks += New-Check -Name "bundle_zip_hash_present" -Passed (![string]::IsNullOrWhiteSpace([string]$bundle.bundle_zip_sha256)) -Observed $bundle.bundle_zip_sha256 -Expected "sha256 present"
$checks += New-Check -Name "bundle_file_count_nonzero" -Passed ([int]$bundle.file_count -gt 0) -Observed $bundle.file_count -Expected "> 0"
$checks += New-Check -Name "bundle_local_only" -Passed ([bool]$bundle.local_only -eq $true -and [bool]$bundle.aws_contacted -eq $false -and [bool]$bundle.github_api_contacted -eq $false -and [bool]$bundle.civitai_contacted -eq $false -and [bool]$bundle.comfyui_contacted -eq $false -and [bool]$bundle.ec2_started -eq $false -and [bool]$bundle.generation_executed -eq $false) -Observed ([ordered]@{ local_only = $bundle.local_only; aws = $bundle.aws_contacted; github_api = $bundle.github_api_contacted; civitai = $bundle.civitai_contacted; comfyui = $bundle.comfyui_contacted; ec2_started = $bundle.ec2_started; generation_executed = $bundle.generation_executed }) -Expected "local only; all contacts false; no EC2/generation"
$checks += New-Check -Name "bundle_contains_all_sample_manifests" -Passed (@($bundle.sample_packages | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.manifest_path) }).Count -eq 0) -Observed @($bundle.sample_packages | Select-Object -ExpandProperty manifest_path) -Expected "all sample manifest paths present"
$checks += New-Check -Name "publish_dry_run_result_passes" -Passed ([string]$publish.result -eq "dry_run_ready_to_upload") -Observed $publish.result -Expected "dry_run_ready_to_upload"
$checks += New-Check -Name "publish_preserves_matrix_manifest_name" -Passed ([string]$publish.bundle_manifest_name -eq "DEPLOY_BUNDLE_MATRIX_MANIFEST.json" -and [string]$publish.s3_manifest_uri -like "*/DEPLOY_BUNDLE_MATRIX_MANIFEST.json") -Observed ([ordered]@{ bundle_manifest_name = $publish.bundle_manifest_name; s3_manifest_uri = $publish.s3_manifest_uri }) -Expected "DEPLOY_BUNDLE_MATRIX_MANIFEST.json sidecar"
$checks += New-Check -Name "publish_records_matrix_context" -Passed ([string]$publish.bundle_type -eq "run_package_matrix_deploy_bundle" -and [string]$publish.matrix_id -eq [string]$matrix.matrix_id -and [int]$publish.sample_count -eq @($matrix.samples).Count) -Observed ([ordered]@{ bundle_type = $publish.bundle_type; matrix_id = $publish.matrix_id; sample_count = $publish.sample_count }) -Expected "matrix bundle type, matrix id, and sample count"
$checks += New-Check -Name "publish_local_only_no_aws_contact" -Passed ([bool]$publish.local_only -eq $true -and [bool]$publish.aws_contacted -eq $false -and [bool]$publish.ec2_started -eq $false -and [bool]$publish.generation_executed -eq $false) -Observed ([ordered]@{ local_only = $publish.local_only; aws_contacted = $publish.aws_contacted; ec2_started = $publish.ec2_started; generation_executed = $publish.generation_executed }) -Expected "dry-run local only; no AWS/EC2/generation"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "W66-EC2-DEPLOY-BUNDLE-MATRIX-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W63-COST-CONTROL"
  artifact_type = "ec2_deploy_bundle_matrix_validation"
  matrix_id = [string]$matrix.matrix_id
  lane_id = [string]$matrix.lane_id
  local_only = $true
  ec2_started = $false
  generation_executed = $false
  scripts = [ordered]@{
    bundle_builder = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $bundleScript
    s3_publisher = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $publishScript
    validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $PSCommandPath
  }
  matrix_manifest = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $resolvedMatrixManifest
  validation_temp_root = "[VALIDATION_TEMP_ROOT]"
  bundle_manifest = "[VALIDATION_TEMP_ROOT]/DEPLOY_BUNDLE_MATRIX_MANIFEST.json"
  bundle_zip = "[VALIDATION_TEMP_ROOT]/$($bundle.bundle_zip)"
  bundle_zip_sha256 = [string]$bundle.bundle_zip_sha256
  publish_dry_run = [ordered]@{
    result = [string]$publish.result
    bundle_manifest_name = [string]$publish.bundle_manifest_name
    s3_bundle_uri = [string]$publish.s3_bundle_uri
    s3_manifest_uri = [string]$publish.s3_manifest_uri
    local_only = [bool]$publish.local_only
    aws_contacted = [bool]$publish.aws_contacted
  }
  sample_count = [int]$bundle.sample_count
  file_count = [int]$bundle.file_count
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = "Publish a matrix deploy bundle to S3 before any future EC2 multi-sample quality run."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
$record | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath $OutFile -Encoding UTF8
$record | ConvertTo-Json -Depth 80
if ($record.result -ne "pass_local_only") { exit 1 }
