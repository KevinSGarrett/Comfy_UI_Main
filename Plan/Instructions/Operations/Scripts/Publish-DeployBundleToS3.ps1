<#
.SYNOPSIS
Uploads a prepared EC2 deploy bundle to S3 while EC2 remains stopped.

.DESCRIPTION
Dry-run by default. With -Execute, uploads the zip and sidecar manifest from a
New-EC2DeployBundle.ps1 output folder to an approved S3 prefix. This avoids
spending GPU-instance time on repo/LFS synchronization.
#>
param(
  [string]$BundleManifestFile,
  [string]$S3BaseUri = "",
  [string]$Region = "us-east-1",
  [string]$OutFile = "",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

if ([string]::IsNullOrWhiteSpace($BundleManifestFile)) {
  throw "BundleManifestFile is required."
}
if (!(Test-Path -LiteralPath $BundleManifestFile)) {
  throw "Bundle manifest missing: $BundleManifestFile"
}

$manifestPath = [System.IO.Path]::GetFullPath($BundleManifestFile)
$manifest = Read-JsonFile -Path $manifestPath
$bundleDir = Split-Path -Parent $manifestPath
$bundleZip = Join-Path $bundleDir ([string]$manifest.bundle_zip)
if (!(Test-Path -LiteralPath $bundleZip)) {
  throw "Bundle zip missing: $bundleZip"
}

$observedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $bundleZip).Hash.ToLowerInvariant()
$expectedHash = ([string]$manifest.bundle_zip_sha256).ToLowerInvariant()
if (![string]::IsNullOrWhiteSpace($expectedHash) -and $observedHash -ne $expectedHash) {
  throw "Bundle zip hash mismatch. expected=$expectedHash observed=$observedHash"
}

$targetPrefix = $null
if (![string]::IsNullOrWhiteSpace($S3BaseUri)) {
  $targetPrefix = "$($S3BaseUri.TrimEnd('/'))/$($manifest.bundle_id)"
}

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "publish_deploy_bundle_to_s3"
  local_only = !$Execute
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  region = $Region
  bundle_manifest_file = $manifestPath
  bundle_zip = $bundleZip
  bundle_id = [string]$manifest.bundle_id
  lane_id = [string]$manifest.lane_id
  bundle_zip_sha256 = $observedHash
  s3_base_uri = $S3BaseUri
  s3_bundle_uri = $(if ($targetPrefix) { "$targetPrefix/$($manifest.bundle_zip)" } else { $null })
  s3_manifest_uri = $(if ($targetPrefix) { "$targetPrefix/DEPLOY_BUNDLE_MANIFEST.json" } else { $null })
  result = "dry_run_ready_to_upload"
  failure_category = $null
  upload = [ordered]@{
    attempted = $false
    bundle_rc = $null
    manifest_rc = $null
  }
  next_action = "Use s3_bundle_uri and bundle_zip_sha256 with -DeployBundleS3Uri and -DeployBundleSha256 on EC2 helpers."
  errors = @()
}

if ([string]::IsNullOrWhiteSpace($S3BaseUri)) {
  $record.result = "blocked_missing_s3_base_uri"
  $record.failure_category = "missing_s3_base_uri"
  $record.next_action = "Provide an approved s3://bucket/prefix value, then rerun with -Execute if AWS auth is valid."
} elseif ($Execute) {
  $record.local_only = $false
  $record.aws_contacted = $true
  $record.upload.attempted = $true
  try {
    $bundleOutput = aws s3 cp $bundleZip $record.s3_bundle_uri --region $Region --only-show-errors 2>&1
    $record.upload.bundle_rc = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) { throw "aws s3 cp bundle failed: $bundleOutput" }
    $manifestOutput = aws s3 cp $manifestPath $record.s3_manifest_uri --region $Region --only-show-errors 2>&1
    $record.upload.manifest_rc = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) { throw "aws s3 cp manifest failed: $manifestOutput" }
    $record.result = "deploy_bundle_uploaded_to_s3"
  } catch {
    $record.result = "deploy_bundle_s3_upload_failed"
    $record.failure_category = "s3_upload_failed"
    $record.errors += $_.Exception.Message
  }
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 20
}

$record | ConvertTo-Json -Depth 20
if ($record.errors.Count -gt 0) { exit 2 }
