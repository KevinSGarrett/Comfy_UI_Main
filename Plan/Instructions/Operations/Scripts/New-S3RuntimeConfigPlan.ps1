<#
.SYNOPSIS
Builds a local-only S3 runtime configuration plan.

.DESCRIPTION
Reads the current redacted .env shape, validates AWS policy templates, and
optionally renders safe policy previews for a supplied bucket and role set. This
does not contact AWS, GitHub APIs, Civitai, ComfyUI, or EC2, and it does not
print secret values from .env.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$EnvFile = "",
  [string]$BucketName = "",
  [string]$DeployBundlePrefix = "deploy-bundles",
  [string]$ModelCachePrefix = "",
  [string]$ArtifactPrefix = "",
  [string]$ManifestPrefix = "",
  [string]$GitHubOwner = "KevinSGarrett",
  [string]$GitHubRepo = "Comfy_UI_Main",
  [string]$AccountId = "029530099913",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "",
  [string]$GitHubRoleArn = "",
  [string]$SchedulerRoleArn = "",
  [string]$RenderedPolicyDir = "",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 30
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Read-EnvMap {
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

function New-EnvPresence {
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

function Test-JsonTemplate {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    path = $Path
    exists = Test-Path -LiteralPath $Path
    json_valid = $false
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
    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }
  return $entry
}

function ConvertTo-RenderedTemplate {
  param(
    [Parameter(Mandatory=$true)][string]$TemplatePath,
    [Parameter(Mandatory=$true)][hashtable]$Values
  )

  $text = Get-Content -LiteralPath $TemplatePath -Raw
  foreach ($key in $Values.Keys) {
    $text = $text.Replace($key, [string]$Values[$key])
  }
  return $text
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root missing: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($EnvFile)) {
  $EnvFile = Join-Path $ProjectRoot ".env"
}

$envMap = Read-EnvMap -Path $EnvFile
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = Get-EnvValue -Map $envMap -Name "AWS_REGION"
}
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = Get-EnvValue -Map $envMap -Name "EC2_REGION"
}
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = "us-east-1"
}
if ([string]::IsNullOrWhiteSpace($ModelCachePrefix)) {
  $ModelCachePrefix = Get-EnvValue -Map $envMap -Name "S3_MODEL_PREFIX"
}
if ([string]::IsNullOrWhiteSpace($ModelCachePrefix)) {
  $ModelCachePrefix = "model-cache"
}
if ([string]::IsNullOrWhiteSpace($ArtifactPrefix)) {
  $ArtifactPrefix = Get-EnvValue -Map $envMap -Name "S3_RENDER_OUTPUT_PREFIX"
}
if ([string]::IsNullOrWhiteSpace($ArtifactPrefix)) {
  $ArtifactPrefix = "render-outputs"
}
if ([string]::IsNullOrWhiteSpace($ManifestPrefix)) {
  $ManifestPrefix = Get-EnvValue -Map $envMap -Name "S3_MANIFEST_PREFIX"
}
if ([string]::IsNullOrWhiteSpace($ManifestPrefix)) {
  $ManifestPrefix = "manifests"
}
if ([string]::IsNullOrWhiteSpace($GitHubRoleArn)) {
  $GitHubRoleArn = Get-EnvValue -Map $envMap -Name "AWS_ROLE_TO_ASSUME"
}

$templateRoot = Join-Path $ProjectRoot "configs\aws"
$templateMap = [ordered]@{
  ec2_runtime_s3_policy = Join-Path $templateRoot "ec2-runtime-s3-policy.template.json"
  github_actions_oidc_deploy_bundle_policy = Join-Path $templateRoot "github-actions-oidc-deploy-bundle-policy.template.json"
  github_actions_oidc_trust_policy = Join-Path $templateRoot "github-actions-oidc-trust-policy.template.json"
  eventbridge_scheduler_stop_role_policy = Join-Path $templateRoot "eventbridge-scheduler-stop-role-policy.template.json"
  eventbridge_scheduler_stop_role_trust_policy = Join-Path $templateRoot "eventbridge-scheduler-stop-role-trust-policy.template.json"
}

$templateChecks = @()
foreach ($key in $templateMap.Keys) {
  $templateChecks += Test-JsonTemplate -Path $templateMap[$key]
}

$bucketReady = ![string]::IsNullOrWhiteSpace($BucketName)
$githubRoleReady = ![string]::IsNullOrWhiteSpace($GitHubRoleArn)
$schedulerRoleReady = ![string]::IsNullOrWhiteSpace($SchedulerRoleArn)
$failedTemplates = @($templateChecks | Where-Object { $_.result -ne "pass" })
$missing = @()
if (!$bucketReady) { $missing += "BucketName or S3_MODEL_BUCKET/COMFY_DEPLOY_BUNDLE_S3_URI value" }
if (!$githubRoleReady) { $missing += "GitHub deploy role ARN (AWS_ROLE_TO_ASSUME or -GitHubRoleArn)" }
if (!$schedulerRoleReady) { $missing += "Scheduler stop role ARN (-SchedulerRoleArn)" }

$bucketToken = $(if ($bucketReady) { $BucketName } else { "<bucket-name>" })
$deployBundleUri = "s3://$bucketToken/$($DeployBundlePrefix.Trim('/'))"
$modelCacheUri = "s3://$bucketToken/$($ModelCachePrefix.Trim('/'))"
$artifactUri = "s3://$bucketToken/$($ArtifactPrefix.Trim('/'))"
$manifestUri = "s3://$bucketToken/$($ManifestPrefix.Trim('/'))"
$schedulerRoleToken = $(if ($schedulerRoleReady) { $SchedulerRoleArn } else { "arn:aws:iam::$AccountId:role/<scheduler-stop-role>" })
$githubRoleToken = $(if ($githubRoleReady) { $GitHubRoleArn } else { "arn:aws:iam::$AccountId:role/<github-deploy-role>" })

$envLines = @(
  "COMFY_DEPLOY_BUNDLE_S3_URI=$deployBundleUri",
  "S3_MODEL_BUCKET=$bucketToken",
  "S3_MODEL_PREFIX=$($ModelCachePrefix.Trim('/'))",
  "S3_RENDER_OUTPUT_PREFIX=$($ArtifactPrefix.Trim('/'))",
  "S3_MANIFEST_PREFIX=$($ManifestPrefix.Trim('/'))",
  "AWS_ROLE_TO_ASSUME=$githubRoleToken",
  "COMFY_SCHEDULER_STOP_ROLE_ARN=$schedulerRoleToken"
)

$renderedPolicyResults = @()
if ($bucketReady -and ![string]::IsNullOrWhiteSpace($RenderedPolicyDir)) {
  $null = New-Item -ItemType Directory -Force -Path $RenderedPolicyDir
  $placeholderValues = @{
    "<bucket-name>" = $BucketName
    "<deploy-bundle-prefix>" = $DeployBundlePrefix.Trim("/")
    "<model-cache-prefix>" = $ModelCachePrefix.Trim("/")
    "<artifact-prefix>" = $ArtifactPrefix.Trim("/")
    "<account-id>" = $AccountId
    "<region>" = $Region
    "<instance-id>" = $InstanceId
    "<github-owner>" = $GitHubOwner
    "<github-repo>" = $GitHubRepo
  }
  foreach ($key in $templateMap.Keys) {
    $renderedFile = Join-Path $RenderedPolicyDir "$key.rendered.json"
    try {
      $rendered = ConvertTo-RenderedTemplate -TemplatePath $templateMap[$key] -Values $placeholderValues
      $null = $rendered | ConvertFrom-Json
      $encoding = New-Object System.Text.UTF8Encoding($false)
      [System.IO.File]::WriteAllText($renderedFile, $rendered, $encoding)
      $remainingPlaceholders = @([regex]::Matches($rendered, '<[^>]+>') | ForEach-Object { $_.Value } | Sort-Object -Unique)
      $renderedPolicyResults += [ordered]@{
        name = $key
        path = $renderedFile
        json_valid = $true
        remaining_placeholder_count = @($remainingPlaceholders).Count
        remaining_placeholders = $remainingPlaceholders
        result = $(if (@($remainingPlaceholders).Count -eq 0) { "pass" } else { "fail_remaining_placeholders" })
      }
    } catch {
      $renderedPolicyResults += [ordered]@{
        name = $key
        path = $renderedFile
        json_valid = $false
        remaining_placeholder_count = $null
        remaining_placeholders = @()
        result = "fail"
        error = $_.Exception.Message
      }
    }
  }
}

$result = "ready_to_apply_local_plan"
$failureCategory = $null
if (@($failedTemplates).Count -gt 0) {
  $result = "blocked_invalid_policy_templates"
  $failureCategory = "invalid_policy_templates"
} elseif (@($missing).Count -gt 0) {
  $result = "blocked_missing_s3_runtime_config"
  $failureCategory = "missing_s3_runtime_config"
}
if (@($renderedPolicyResults | Where-Object { $_.result -ne "pass" }).Count -gt 0) {
  $result = "blocked_rendered_policy_validation"
  $failureCategory = "rendered_policy_validation_failed"
}

$record = [ordered]@{
  schema_version = "1.0"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "s3_runtime_config_plan"
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
  env_presence = @(
    New-EnvPresence -Map $envMap -Name "COMFY_DEPLOY_BUNDLE_S3_URI"
    New-EnvPresence -Map $envMap -Name "S3_MODEL_BUCKET"
    New-EnvPresence -Map $envMap -Name "S3_MODEL_PREFIX"
    New-EnvPresence -Map $envMap -Name "S3_RENDER_OUTPUT_PREFIX"
    New-EnvPresence -Map $envMap -Name "S3_MANIFEST_PREFIX"
    New-EnvPresence -Map $envMap -Name "AWS_ROLE_TO_ASSUME"
    New-EnvPresence -Map $envMap -Name "COMFY_SCHEDULER_STOP_ROLE_ARN"
  )
  planned_config = [ordered]@{
    bucket_configured = $bucketReady
    deploy_bundle_s3_uri = $deployBundleUri
    model_cache_s3_uri = $modelCacheUri
    artifact_s3_uri = $artifactUri
    manifest_s3_uri = $manifestUri
    github_role_arn_configured = $githubRoleReady
    scheduler_role_arn_configured = $schedulerRoleReady
  }
  env_lines_to_add_or_update = $envLines
  policy_template_checks = $templateChecks
  rendered_policy_dir = $RenderedPolicyDir
  rendered_policy_results = $renderedPolicyResults
  command_plan = @(
    "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-S3RuntimeTransferReadiness.ps1 -ProjectRoot C:\Comfy_UI_Main -DeployBundleS3Uri $deployBundleUri -ModelCacheS3Uri $modelCacheUri -ArtifactS3Uri $artifactUri -GitHubRoleArn $githubRoleToken -SchedulerRoleArn $schedulerRoleToken -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_RUNTIME_TRANSFER_READINESS_<timestamp>.json",
    "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <matrix-deploy-bundle-manifest> -S3BaseUri $deployBundleUri -Region $Region -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_MATRIX_DEPLOY_BUNDLE_S3_UPLOAD_<timestamp>.json -Execute",
    "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1 -SchedulerRoleArn $schedulerRoleToken -StopAfterMinutes 60 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_EC2_EMERGENCY_STOP_SCHEDULE_<timestamp>.json",
    "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2WorkflowMatrixQualityRunPlan.ps1 -ProjectRoot C:\Comfy_UI_Main -DeployBundleS3Uri <uploaded-matrix-bundle-s3-uri> -DeployBundleSha256 <uploaded-matrix-bundle-sha256> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_<timestamp>.json"
  )
  missing_config = $missing
  result = $result
  failure_category = $failureCategory
  next_action = $(if ($result -eq "ready_to_apply_local_plan") { "Rerun Test-S3RuntimeTransferReadiness.ps1 with the planned values, then publish the matrix deploy bundle to S3 only after AWS auth and Git cleanliness pass." } else { "Fill missing_config, rerun this planner, then rerun S3 runtime transfer readiness before any live upload or EC2 execution." })
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
}

$record | ConvertTo-Json -Depth 30
