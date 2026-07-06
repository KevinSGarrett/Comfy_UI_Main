<#
.SYNOPSIS
Checks S3 runtime-transfer configuration readiness without contacting AWS.

.DESCRIPTION
Validates the safe-to-commit AWS policy templates and summarizes whether the
project has enough redacted .env/configuration to use S3 for deploy bundles,
model-cache reads, artifact writes, GitHub OIDC upload, and emergency-stop
scheduling. This is local-only by default and never prints secret values.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$EnvFile = "",
  [string]$DeployBundleS3Uri = "",
  [string]$ModelCacheS3Uri = "",
  [string]$ArtifactS3Uri = "",
  [string]$GitHubRoleArn = "",
  [string]$SchedulerRoleArn = "",
  [string]$Region = "",
  [string]$OutFile = ""
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

function Get-RelativePathCompat {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$TargetPath
  )

  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  return (Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath).Replace("\", "/")
}

function Read-EnvSummary {
  param([Parameter(Mandatory=$true)][string]$Path)

  $map = @{}
  if (!(Test-Path -LiteralPath $Path)) { return $map }
  foreach ($line in Get-Content -LiteralPath $Path) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
      $name = $matches[1]
      $value = [string]$matches[2]
      $map[$name] = $value.Trim().Trim('"').Trim("'")
    }
  }
  return $map
}

function Get-EnvValue {
  param(
    [hashtable]$Map,
    [string]$Name
  )

  if ($Map.ContainsKey($Name)) { return [string]$Map[$Name] }
  return ""
}

function New-EnvCheck {
  param(
    [hashtable]$Map,
    [string]$Name
  )

  $exists = $Map.ContainsKey($Name)
  $hasValue = $false
  if ($exists) { $hasValue = ![string]::IsNullOrWhiteSpace([string]$Map[$Name]) }
  return [ordered]@{
    name = $Name
    exists = $exists
    has_value = $hasValue
  }
}

function Test-S3UriShape {
  param([string]$Uri)
  return (![string]::IsNullOrWhiteSpace($Uri) -and $Uri -match '^s3://[^/]+/.+')
}

function Test-JsonTemplate {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    exists = Test-Path -LiteralPath $Path
    json_valid = $false
    placeholder_count = 0
    placeholders = @()
    result = "fail"
    error = $null
  }
  if (!$entry.exists) {
    $entry.error = "Template file missing."
    return $entry
  }
  try {
    $text = Get-Content -LiteralPath $Path -Raw
    $null = $text | ConvertFrom-Json
    $entry.json_valid = $true
    $entry.placeholders = @([regex]::Matches($text, '<[^>]+>') | ForEach-Object { $_.Value } | Sort-Object -Unique)
    $entry.placeholder_count = @($entry.placeholders).Count
    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }
  return $entry
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root missing: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($EnvFile)) {
  $EnvFile = Join-Path $ProjectRoot ".env"
}

$envMap = Read-EnvSummary -Path $EnvFile
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = Get-EnvValue -Map $envMap -Name "AWS_REGION"
}
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = Get-EnvValue -Map $envMap -Name "EC2_REGION"
}
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = "us-east-1"
}

$s3ModelBucket = Get-EnvValue -Map $envMap -Name "S3_MODEL_BUCKET"
$s3ModelPrefix = Get-EnvValue -Map $envMap -Name "S3_MODEL_PREFIX"
$s3RenderOutputPrefix = Get-EnvValue -Map $envMap -Name "S3_RENDER_OUTPUT_PREFIX"
$s3ManifestPrefix = Get-EnvValue -Map $envMap -Name "S3_MANIFEST_PREFIX"

if ([string]::IsNullOrWhiteSpace($DeployBundleS3Uri)) {
  $DeployBundleS3Uri = Get-EnvValue -Map $envMap -Name "COMFY_DEPLOY_BUNDLE_S3_URI"
}
if ([string]::IsNullOrWhiteSpace($ModelCacheS3Uri) -and
  ![string]::IsNullOrWhiteSpace($s3ModelBucket) -and
  ![string]::IsNullOrWhiteSpace($s3ModelPrefix)) {
  $ModelCacheS3Uri = "s3://$s3ModelBucket/$($s3ModelPrefix.Trim('/'))"
}
if ([string]::IsNullOrWhiteSpace($ArtifactS3Uri) -and
  ![string]::IsNullOrWhiteSpace($s3ModelBucket) -and
  ![string]::IsNullOrWhiteSpace($s3RenderOutputPrefix)) {
  $ArtifactS3Uri = "s3://$s3ModelBucket/$($s3RenderOutputPrefix.Trim('/'))"
}
if ([string]::IsNullOrWhiteSpace($GitHubRoleArn)) {
  $GitHubRoleArn = Get-EnvValue -Map $envMap -Name "AWS_ROLE_TO_ASSUME"
}

$templateRoot = Join-Path $ProjectRoot "configs\aws"
$templateFiles = @(
  "ec2-runtime-s3-policy.template.json",
  "github-actions-oidc-deploy-bundle-policy.template.json",
  "github-actions-oidc-trust-policy.template.json",
  "eventbridge-scheduler-stop-role-policy.template.json",
  "eventbridge-scheduler-stop-role-trust-policy.template.json"
)
$templateChecks = @()
foreach ($template in $templateFiles) {
  $templateChecks += Test-JsonTemplate -Path (Join-Path $templateRoot $template)
}

$missingConfig = @()
if (!(Test-S3UriShape -Uri $DeployBundleS3Uri)) { $missingConfig += "COMFY_DEPLOY_BUNDLE_S3_URI or -DeployBundleS3Uri" }
if (!(Test-S3UriShape -Uri $ModelCacheS3Uri)) { $missingConfig += "S3_MODEL_BUCKET plus S3_MODEL_PREFIX, or -ModelCacheS3Uri" }
if (!(Test-S3UriShape -Uri $ArtifactS3Uri)) { $missingConfig += "S3_MODEL_BUCKET plus S3_RENDER_OUTPUT_PREFIX, or -ArtifactS3Uri" }
if ([string]::IsNullOrWhiteSpace($GitHubRoleArn)) { $missingConfig += "AWS_ROLE_TO_ASSUME or -GitHubRoleArn" }
if ([string]::IsNullOrWhiteSpace($SchedulerRoleArn)) { $missingConfig += "Scheduler stop role ARN for New-EC2EmergencyStopSchedule.ps1" }

$failedTemplates = @($templateChecks | Where-Object { $_.result -ne "pass" })
$result = "ready_local_only"
$failureCategory = $null
if (@($failedTemplates).Count -gt 0) {
  $result = "blocked_invalid_policy_templates"
  $failureCategory = "invalid_policy_templates"
} elseif (@($missingConfig).Count -gt 0) {
  $result = "blocked_missing_s3_runtime_config"
  $failureCategory = "missing_s3_runtime_config"
}

$record = [ordered]@{
  schema_version = "1.0"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "s3_runtime_transfer_readiness"
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  secrets_printed = $false
  project_root = $ProjectRoot
  env_file_present = Test-Path -LiteralPath $EnvFile
  region = $Region
  env_checks = @(
    New-EnvCheck -Map $envMap -Name "AWS_REGION"
    New-EnvCheck -Map $envMap -Name "EC2_REGION"
    New-EnvCheck -Map $envMap -Name "S3_MODEL_BUCKET"
    New-EnvCheck -Map $envMap -Name "S3_MODEL_PREFIX"
    New-EnvCheck -Map $envMap -Name "S3_RENDER_OUTPUT_PREFIX"
    New-EnvCheck -Map $envMap -Name "S3_MANIFEST_PREFIX"
    New-EnvCheck -Map $envMap -Name "COMFY_DEPLOY_BUNDLE_S3_URI"
    New-EnvCheck -Map $envMap -Name "AWS_ROLE_TO_ASSUME"
  )
  resolved_config = [ordered]@{
    deploy_bundle_s3_uri_present = Test-S3UriShape -Uri $DeployBundleS3Uri
    model_cache_s3_uri_present = Test-S3UriShape -Uri $ModelCacheS3Uri
    artifact_s3_uri_present = Test-S3UriShape -Uri $ArtifactS3Uri
    github_role_arn_present = ![string]::IsNullOrWhiteSpace($GitHubRoleArn)
    scheduler_role_arn_present = ![string]::IsNullOrWhiteSpace($SchedulerRoleArn)
  }
  policy_template_checks = $templateChecks
  missing_config = $missingConfig
  result = $result
  failure_category = $failureCategory
  next_action = $(if ($result -eq "ready_local_only") {
      "Apply/render the validated templates with approved bucket, prefixes, GitHub OIDC role, and scheduler stop role; then run a dry-run S3 publish before any future EC2 transfer window."
    } else {
      "Fill the missing S3/IAM configuration listed in missing_config, then rerun this local readiness helper before applying AWS policies or starting EC2."
    })
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 20
}

$record | ConvertTo-Json -Depth 20
if ($result -eq "blocked_invalid_policy_templates") { exit 2 }
