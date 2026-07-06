<#
.SYNOPSIS
Validates the local-only EC2 workflow matrix quality-run plan.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RunPackageMatrixManifestFile = "runtime_artifacts\run_package_matrices\realvisxl_multisample_certification_v1\RUN_PACKAGE_MATRIX_MANIFEST.json",
  [string]$DeployBundleEvidenceFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_EC2_DEPLOY_BUNDLE_MATRIX_S3_DRY_RUN_REDACTED_20260706T171921-0500.json",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
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

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$matrixPath = Resolve-ProjectPath -Path $RunPackageMatrixManifestFile
$bundleEvidencePath = Resolve-ProjectPath -Path $DeployBundleEvidenceFile
$matrix = Read-JsonFile -Path $matrixPath
$bundleEvidence = Read-JsonFile -Path $bundleEvidencePath

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_$stamp.json"
}
$planTemp = Join-Path ([System.IO.Path]::GetTempPath()) "comfy_matrix_quality_run_plan_$stamp.json"
$plannerScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-EC2WorkflowMatrixQualityRunPlan.ps1"
$deployBundleS3Uri = [string]$bundleEvidence.publish_dry_run.s3_bundle_uri
$deployBundleSha256 = [string]$bundleEvidence.bundle_zip_sha256

$plannerOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $plannerScript `
  -ProjectRoot $ProjectRoot `
  -RunPackageMatrixManifestFile $matrixPath `
  -DeployBundleS3Uri $deployBundleS3Uri `
  -DeployBundleSha256 $deployBundleSha256 `
  -StaticProofFile "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\<static-proof>.json" `
  -ReadinessFile "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\<readiness>.json" `
  -OutFile $planTemp 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "Matrix quality run planner failed: $($plannerOutput | Out-String)"
}
$plan = Read-JsonFile -Path $planTemp

$checks = @()
$checks += New-Check -Name "plan_result_passes" -Passed ([string]$plan.result -eq "pass_local_only") -Observed $plan.result -Expected "pass_local_only"
$checks += New-Check -Name "plan_sample_count_matches_matrix" -Passed ([int]$plan.sample_count -eq @($matrix.samples).Count) -Observed $plan.sample_count -Expected @($matrix.samples).Count
$checks += New-Check -Name "plan_local_only" -Passed ([bool]$plan.local_only -eq $true -and [bool]$plan.aws_contacted -eq $false -and [bool]$plan.comfyui_contacted -eq $false -and [bool]$plan.ec2_started -eq $false -and [bool]$plan.generation_executed -eq $false) -Observed ([ordered]@{ local_only = $plan.local_only; aws = $plan.aws_contacted; comfyui = $plan.comfyui_contacted; ec2_started = $plan.ec2_started; generation_executed = $plan.generation_executed }) -Expected "local only; no contacts; no EC2/generation"
$checks += New-Check -Name "plan_uses_s3_bundle_inputs" -Passed ([bool]$plan.inputs.deploy_bundle_s3_uri_supplied -eq $true -and [bool]$plan.inputs.deploy_bundle_sha256_supplied -eq $true) -Observed ([ordered]@{ uri = $plan.inputs.deploy_bundle_s3_uri; sha256 = $plan.inputs.deploy_bundle_sha256 }) -Expected "S3 URI and SHA supplied"
$checks += New-Check -Name "all_sample_commands_include_run_package" -Passed (@($plan.planned_samples | Where-Object { [string]$_.workflow_command -notmatch "-RunPackageManifestFile" }).Count -eq 0) -Observed @($plan.planned_samples | Select-Object -ExpandProperty workflow_command) -Expected "all workflow commands include -RunPackageManifestFile"
$checks += New-Check -Name "all_sample_commands_include_s3_bundle" -Passed (@($plan.planned_samples | Where-Object { [string]$_.workflow_command -notmatch "-DeployBundleS3Uri" -or [string]$_.workflow_command -notmatch "-DeployBundleSha256" }).Count -eq 0) -Observed @($plan.planned_samples | Select-Object -ExpandProperty workflow_command) -Expected "all workflow commands include bundle URI and SHA"
$checks += New-Check -Name "all_sample_commands_include_cost_controls" -Passed (@($plan.planned_samples | Where-Object { [string]$_.workflow_command -notmatch "-SkipGitLfsPull" -or [string]$_.workflow_command -notmatch "-MaxEc2RuntimeMinutes" }).Count -eq 0) -Observed @($plan.planned_samples | Select-Object -ExpandProperty workflow_command) -Expected "all workflow commands include cost controls"
$checks += New-Check -Name "all_samples_require_pullback" -Passed (@($plan.planned_samples | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.pullback_command) }).Count -eq 0) -Observed @($plan.planned_samples | Select-Object run_id,pullback_command) -Expected "pullback command for every sample"
$checks += New-Check -Name "all_samples_require_whole_image_qa" -Passed (@($plan.planned_samples | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.whole_image_qa_command) }).Count -eq 0) -Observed @($plan.planned_samples | Select-Object run_id,whole_image_qa_command) -Expected "whole-image QA command for every sample"
$checks += New-Check -Name "all_samples_have_required_post_run_evidence" -Passed (@($plan.planned_samples | Where-Object { @($_.required_post_run_evidence).Count -lt 5 }).Count -eq 0) -Observed @($plan.planned_samples | ForEach-Object { [ordered]@{ run_id = $_.run_id; evidence_count = @($_.required_post_run_evidence).Count } }) -Expected "workflow, remote manifest, pullback, image QA JSON, QA checklist"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "W66-EC2-WORKFLOW-MATRIX-QUALITY-RUN-PLAN-VALIDATION-$stamp"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  artifact_type = "ec2_workflow_matrix_quality_run_plan_validation"
  matrix_id = [string]$matrix.matrix_id
  lane_id = [string]$matrix.lane_id
  local_only = $true
  ec2_started = $false
  generation_executed = $false
  scripts = [ordered]@{
    planner = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $plannerScript
    validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $PSCommandPath
  }
  inputs = [ordered]@{
    matrix_manifest = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $matrixPath
    deploy_bundle_evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $bundleEvidencePath
    deploy_bundle_s3_uri_present = ![string]::IsNullOrWhiteSpace($deployBundleS3Uri)
    deploy_bundle_sha256_present = ![string]::IsNullOrWhiteSpace($deployBundleSha256)
  }
  plan = [ordered]@{
    evidence_id = [string]$plan.evidence_id
    sample_count = [int]$plan.sample_count
    result = [string]$plan.result
    planned_sample_count = @($plan.planned_samples).Count
  }
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = "Use the planned commands only after S3 config, AWS auth, clean Git, static proof, and readiness gates pass; then pull back and whole-image QA every generated sample."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
$record | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath $OutFile -Encoding UTF8
$record | ConvertTo-Json -Depth 80
if ($record.result -ne "pass_local_only") { exit 1 }
