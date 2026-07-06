<#
.SYNOPSIS
Validates the local-only S3 runtime configuration planner.

.DESCRIPTION
Runs New-S3RuntimeConfigPlan.ps1 with sample bucket and role inputs, validates
rendered policy previews, verifies no external services or EC2 were contacted,
and writes machine-readable QA evidence.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
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

function New-Check {
  param(
    [string]$Name,
    [bool]$Passed,
    [object]$Observed,
    [object]$Expected
  )

  return [ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return $null -ne $Object.PSObject.Properties[$Name]
}

function ConvertTo-RedactedTempPath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $Path }
  $fullPath = [System.IO.Path]::GetFullPath($Path)
  $tempFull = [System.IO.Path]::GetFullPath($tempRoot).TrimEnd("\", "/")
  if ($fullPath.StartsWith($tempFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    $relative = $fullPath.Substring($tempFull.Length).TrimStart("\", "/").Replace("\", "/")
    if ([string]::IsNullOrWhiteSpace($relative)) { return "[VALIDATION_TEMP_ROOT]" }
    return "[VALIDATION_TEMP_ROOT]/$relative"
  }
  return $Path
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root missing: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

$plannerScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-S3RuntimeConfigPlan.ps1"
if (!(Test-Path -LiteralPath $plannerScript)) {
  throw "Planner script missing: $plannerScript"
}

$stamp = (Get-Date).ToString("yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_RUNTIME_CONFIG_PLAN_$stamp.json"
}

$tempRoot = Join-Path $env:TEMP "comfy_s3_runtime_config_plan_$stamp"
$renderedDir = Join-Path $tempRoot "rendered_policies"
$plannerOut = Join-Path $tempRoot "s3_runtime_config_plan.json"
$null = New-Item -ItemType Directory -Force -Path $tempRoot

& powershell -NoProfile -ExecutionPolicy Bypass -File $plannerScript `
  -ProjectRoot $ProjectRoot `
  -BucketName "example-comfy-runtime-bucket" `
  -DeployBundlePrefix "deploy-bundles" `
  -ModelCachePrefix "model-cache" `
  -ArtifactPrefix "render-outputs" `
  -ManifestPrefix "manifests" `
  -GitHubRoleArn "arn:aws:iam::029530099913:role/example-github-deploy-role" `
  -SchedulerRoleArn "arn:aws:iam::029530099913:role/example-scheduler-stop-role" `
  -RenderedPolicyDir $renderedDir `
  -OutFile $plannerOut | Out-Null

if ($LASTEXITCODE -ne 0) {
  throw "New-S3RuntimeConfigPlan.ps1 exited with code $LASTEXITCODE"
}
if (!(Test-Path -LiteralPath $plannerOut)) {
  throw "Planner output missing: $plannerOut"
}

$plan = Get-Content -Raw -LiteralPath $plannerOut | ConvertFrom-Json
$renderedPolicies = @($plan.rendered_policy_results)
$commandPlan = @($plan.command_plan)
$envLines = @($plan.env_lines_to_add_or_update)

$renderedPolicyJsonFailures = @()
foreach ($policy in $renderedPolicies) {
  if (!(Test-Path -LiteralPath $policy.path)) {
    $renderedPolicyJsonFailures += "$($policy.name): missing rendered file"
    continue
  }
  try {
    $null = Get-Content -Raw -LiteralPath $policy.path | ConvertFrom-Json
  } catch {
    $renderedPolicyJsonFailures += "$($policy.name): $($_.Exception.Message)"
  }
}
$sanitizedRenderedPolicies = @($renderedPolicies | ForEach-Object {
  [ordered]@{
    name = $_.name
    path = ConvertTo-RedactedTempPath -Path ([string]$_.path)
    json_valid = $_.json_valid
    remaining_placeholder_count = $_.remaining_placeholder_count
    remaining_placeholders = @($_.remaining_placeholders)
    result = $_.result
  }
})

$checks = @()
$checks += New-Check -Name "planner_result_ready" -Passed ([string]$plan.result -eq "ready_to_apply_local_plan") -Observed $plan.result -Expected "ready_to_apply_local_plan"
$checks += New-Check -Name "planner_local_only" -Passed ([bool]$plan.local_only -and -not [bool]$plan.aws_contacted -and -not [bool]$plan.ec2_started -and -not [bool]$plan.generation_executed) -Observed ([ordered]@{ local_only = $plan.local_only; aws = $plan.aws_contacted; ec2_started = $plan.ec2_started; generation_executed = $plan.generation_executed }) -Expected "local only; no AWS/EC2/generation"
$checks += New-Check -Name "planner_does_not_print_secrets" -Passed ([bool]$plan.secrets_printed -eq $false) -Observed $plan.secrets_printed -Expected $false
$checks += New-Check -Name "planned_s3_uris_present" -Passed (([string]$plan.planned_config.deploy_bundle_s3_uri -match '^s3://example-comfy-runtime-bucket/deploy-bundles') -and ([string]$plan.planned_config.model_cache_s3_uri -match '^s3://example-comfy-runtime-bucket/model-cache') -and ([string]$plan.planned_config.artifact_s3_uri -match '^s3://example-comfy-runtime-bucket/render-outputs')) -Observed $plan.planned_config -Expected "deploy, model-cache, and artifact S3 URIs"
$checks += New-Check -Name "env_lines_include_required_keys" -Passed ((@($envLines | Where-Object { $_ -match '^COMFY_DEPLOY_BUNDLE_S3_URI=' }).Count -eq 1) -and (@($envLines | Where-Object { $_ -match '^S3_MODEL_BUCKET=' }).Count -eq 1) -and (@($envLines | Where-Object { $_ -match '^AWS_ROLE_TO_ASSUME=' }).Count -eq 1) -and (@($envLines | Where-Object { $_ -match '^COMFY_SCHEDULER_STOP_ROLE_ARN=' }).Count -eq 1)) -Observed $envLines -Expected "required S3/IAM env lines"
$checks += New-Check -Name "all_policy_templates_parse" -Passed (@($plan.policy_template_checks | Where-Object { $_.result -ne "pass" }).Count -eq 0) -Observed $plan.policy_template_checks -Expected "all template checks pass"
$checks += New-Check -Name "rendered_policies_exist_and_parse" -Passed ((@($renderedPolicies).Count -eq 5) -and (@($renderedPolicies | Where-Object { $_.result -ne "pass" }).Count -eq 0) -and (@($renderedPolicyJsonFailures).Count -eq 0)) -Observed ([ordered]@{ rendered_count = @($renderedPolicies).Count; failures = $renderedPolicyJsonFailures; results = $sanitizedRenderedPolicies }) -Expected "5 rendered valid JSON policies with no placeholders"
$checks += New-Check -Name "command_plan_has_required_followups" -Passed ((@($commandPlan | Where-Object { $_ -match "Test-S3RuntimeTransferReadiness.ps1" }).Count -ge 1) -and (@($commandPlan | Where-Object { $_ -match "Publish-DeployBundleToS3.ps1" }).Count -ge 1) -and (@($commandPlan | Where-Object { $_ -match "New-EC2WorkflowMatrixQualityRunPlan.ps1" }).Count -ge 1)) -Observed $commandPlan -Expected "readiness, publish, and matrix plan commands"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "W66-S3-RUNTIME-CONFIG-PLAN-VALIDATION-$stamp"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  artifact_type = "s3_runtime_config_plan_validation"
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  scripts = [ordered]@{
    planner = "Plan/Instructions/Operations/Scripts/New-S3RuntimeConfigPlan.ps1"
    validator = "Plan/Instructions/QA/Scripts/Test-S3RuntimeConfigPlan.ps1"
  }
  planner_result = [ordered]@{
    result = $plan.result
    rendered_policy_count = @($renderedPolicies).Count
    command_count = @($commandPlan).Count
  }
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = "Use real bucket and role values, rerun S3 readiness, then publish the matrix deploy bundle only after auth/Git gates pass."
}

Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
$record | ConvertTo-Json -Depth 30
if (@($failures).Count -gt 0) { exit 1 }
