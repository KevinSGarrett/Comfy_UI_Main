<#
.SYNOPSIS
Uploads one prepared ComfyUI model binary to S3 model-cache while EC2 remains stopped.

.DESCRIPTION
Dry-run by default. With -Execute, verifies the local model SHA256, uploads it
to the approved S3 model-cache URI, and writes an evidence record. This helper
is for model/checkpoint binaries, not deploy bundles or LoadImage inputs.
#>
param(
  [string]$ModelFile,
  [string]$S3Uri = "",
  [string]$S3BaseUri = "",
  [string]$FileName = "",
  [string]$ExpectedSha256 = "",
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

function Test-S3UriShape {
  param([string]$Uri)
  return (![string]::IsNullOrWhiteSpace($Uri) -and $Uri -match '^s3://[^/]+/.+')
}

if ([string]::IsNullOrWhiteSpace($ModelFile)) {
  throw "ModelFile is required."
}
if (!(Test-Path -LiteralPath $ModelFile -PathType Leaf)) {
  throw "Model file missing: $ModelFile"
}

$modelPath = [System.IO.Path]::GetFullPath($ModelFile)
if ([string]::IsNullOrWhiteSpace($FileName)) {
  $FileName = Split-Path -Leaf $modelPath
}
if ([string]::IsNullOrWhiteSpace($S3Uri) -and ![string]::IsNullOrWhiteSpace($S3BaseUri)) {
  $S3Uri = "$($S3BaseUri.TrimEnd('/'))/$FileName"
}

$observedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $modelPath).Hash.ToLowerInvariant()
$expectedHash = ([string]$ExpectedSha256).ToLowerInvariant()
$hashMatches = ([string]::IsNullOrWhiteSpace($expectedHash) -or $observedHash -eq $expectedHash)

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "publish_model_to_s3"
  local_only = !$Execute
  aws_contacted = $false
  s3_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  active_runtime_marker_written = $false
  git_lfs_used = $false
  region = $Region
  model_file = $modelPath
  file_name = $FileName
  size_bytes = (Get-Item -LiteralPath $modelPath).Length
  expected_sha256 = $(if ([string]::IsNullOrWhiteSpace($expectedHash)) { $null } else { $expectedHash })
  observed_sha256 = $observedHash
  local_hash_match = $hashMatches
  s3_uri = $S3Uri
  result = "dry_run_ready_to_upload_model"
  failure_category = $null
  upload = [ordered]@{
    attempted = $false
    rc = $null
  }
  errors = @()
  next_action = "Use Install-EC2ModelFromS3.ps1 with this s3_uri and observed_sha256 after live gates pass."
}

if (-not $hashMatches) {
  $record.result = "blocked_model_hash_mismatch"
  $record.failure_category = "model_hash_mismatch"
  $record.next_action = "Fix the local model binary or expected hash before upload."
} elseif (-not (Test-S3UriShape -Uri $S3Uri)) {
  $record.result = "blocked_missing_or_invalid_s3_uri"
  $record.failure_category = "missing_or_invalid_s3_uri"
  $record.next_action = "Provide an approved s3://bucket/model-cache/file target before upload."
} elseif ($Execute) {
  $record.local_only = $false
  $record.aws_contacted = $true
  $record.s3_contacted = $true
  $record.upload.attempted = $true
  try {
    $metadata = "sha256=$observedHash"
    $output = aws s3 cp $modelPath $S3Uri --region $Region --metadata $metadata --only-show-errors 2>&1
    $record.upload.rc = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) { throw "aws s3 cp model failed: $output" }
    $record.result = "model_uploaded_to_s3"
  } catch {
    $record.result = "model_s3_upload_failed"
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
if ($record.errors.Count -gt 0 -or $record.failure_category -eq "model_hash_mismatch") { exit 2 }
