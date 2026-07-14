<#
.SYNOPSIS
Builds a local-only RealESRGAN target-runtime asset-transfer dry-run bundle.

.DESCRIPTION
Verifies the lane's local model and source-image hashes, then invokes the
existing model/input publish and EC2 install helpers without -Execute. The
result is readiness evidence only and never contacts AWS, S3, EC2, or ComfyUI.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneRuntimeRequirements = "Workflows\base_generation\sdxl_realesrgan_upscale_polish_lane\runtime_requirements.json",
  [string]$ModelProvisioningEvidence = "Plan\Instructions\QA\Evidence\Model_Registry\W69_LOCAL_REALESRGAN_UPSCALE_MODEL_PROVISIONING_20260707T110500-0500.json",
  [string]$ModelFile = "models\upscale_models\RealESRGAN_x4plus.pth",
  [string]$InputRole = "source_image",
  [string]$InputAssetFile = "Plan\Instructions\Operations\Pulled_Back_Artifacts\canny_w69_eyeonly_seam_suppression_711570105_20260707T104736-0500\images\canny_w69_eyeonly_seam_suppression_711570105_00001_.png",
  [string]$ModelS3Uri = "s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/RealESRGAN_x4plus.pth",
  [string]$InputS3Uri = "s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/input-assets/upscale_polish_source_canny_w69.png",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$ArtifactOutputDirectory = "",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = "",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $Path))
}

function ConvertTo-ProjectRelativePath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $resolved = [System.IO.Path]::GetFullPath($Path)
  if ($resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $resolved.Substring($root.Length).Replace("\", "/")
  }
  return $resolved
}

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Invoke-JsonChild {
  param(
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [Parameter(Mandatory=$true)][string[]]$Arguments,
    [Parameter(Mandatory=$true)][string]$ExpectedOutput
  )

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    $tail = @($output | Select-Object -Last 20) -join [Environment]::NewLine
    throw "Child helper failed with exit code $($exitCode): $ScriptPath$([Environment]::NewLine)$tail"
  }
  if (-not (Test-Path -LiteralPath $ExpectedOutput -PathType Leaf)) {
    throw "Child helper did not write expected output: $ExpectedOutput"
  }
  return Get-Content -LiteralPath $ExpectedOutput -Raw | ConvertFrom-Json
}

function Test-S3Uri {
  param([string]$Uri)
  return (-not [string]::IsNullOrWhiteSpace($Uri) -and $Uri -match "^s3://[^/]+/.+")
}

function Test-PropertyFalse {
  param([object]$Payload, [string]$Name)
  return ($null -ne $Payload.PSObject.Properties[$Name] -and -not [bool]$Payload.$Name)
}

if ($Execute) {
  throw "Live execution is forbidden. This bundle is local dry-run only."
}
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$requirementsPath = Resolve-ProjectPath -Path $LaneRuntimeRequirements
$provisioningPath = Resolve-ProjectPath -Path $ModelProvisioningEvidence
$modelPath = Resolve-ProjectPath -Path $ModelFile
$inputPath = Resolve-ProjectPath -Path $InputAssetFile
foreach ($requiredPath in @($requirementsPath, $provisioningPath, $modelPath, $inputPath)) {
  if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
    throw "Required local file missing: $requiredPath"
  }
}

$requirements = Get-Content -LiteralPath $requirementsPath -Raw | ConvertFrom-Json
$provisioning = Get-Content -LiteralPath $provisioningPath -Raw | ConvertFrom-Json
$laneId = [string]$requirements.lane_id
$requiredModel = @($requirements.required_models | Where-Object { [string]$_.role -eq "upscale_model" } | Select-Object -First 1)
$requiredInput = @($requirements.required_inputs | Where-Object { [string]$_.role -eq $InputRole } | Select-Object -First 1)
if ($requiredModel.Count -ne 1 -or $requiredInput.Count -ne 1) {
  throw "Runtime requirements must define one upscale_model and one required input with role '$InputRole'."
}
$requiredModel = $requiredModel[0]
$requiredInput = $requiredInput[0]

$expectedModelHash = ([string]$requiredModel.sha256).ToLowerInvariant()
$expectedInputHash = ([string]$requiredInput.source_sha256).ToLowerInvariant()
$observedModelHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $modelPath).Hash.ToLowerInvariant()
$observedInputHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputPath).Hash.ToLowerInvariant()
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")

if ([string]::IsNullOrWhiteSpace($ArtifactOutputDirectory)) {
  $ArtifactOutputDirectory = "Plan\Instructions\QA\Evidence\Runtime_Readiness"
}
$artifactDir = Resolve-ProjectPath -Path $ArtifactOutputDirectory
[System.IO.Directory]::CreateDirectory($artifactDir) | Out-Null

$modelPublishFile = Join-Path $artifactDir "W66_REALESRGAN_MODEL_S3_PUBLISH_DRY_RUN_$stamp.json"
$inputPublishFile = Join-Path $artifactDir "W66_REALESRGAN_INPUT_S3_PUBLISH_DRY_RUN_$stamp.json"
$modelInstallFile = Join-Path $artifactDir "W66_REALESRGAN_MODEL_EC2_INSTALL_DRY_RUN_$stamp.json"
$inputInstallFile = Join-Path $artifactDir "W66_REALESRGAN_INPUT_EC2_INSTALL_DRY_RUN_$stamp.json"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $artifactDir "W66_SDXL_REALESRGAN_UPSCALE_ASSET_TRANSFER_DRY_RUN_BUNDLE_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($outPath, ".md")
}
$markdownPath = Resolve-ProjectPath -Path $MarkdownOutFile

$checks = [System.Collections.Generic.List[object]]::new()
[void]$checks.Add((New-Check -Name "lane_is_realesrgan_upscale" -Passed ($laneId -eq "sdxl_realesrgan_upscale_polish_lane") -Observed $laneId -Expected "sdxl_realesrgan_upscale_polish_lane"))
[void]$checks.Add((New-Check -Name "model_filename_matches_requirements" -Passed ((Split-Path -Leaf $modelPath) -eq [string]$requiredModel.filename) -Observed (Split-Path -Leaf $modelPath) -Expected ([string]$requiredModel.filename)))
[void]$checks.Add((New-Check -Name "input_role_matches_requirements" -Passed (([string]$requiredInput.role) -eq $InputRole) -Observed ([string]$requiredInput.role) -Expected $InputRole))
[void]$checks.Add((New-Check -Name "input_s3_filename_matches_requirements" -Passed (($InputS3Uri -split '/')[-1] -eq [string]$requiredInput.filename) -Observed (($InputS3Uri -split '/')[-1]) -Expected ([string]$requiredInput.filename)))
[void]$checks.Add((New-Check -Name "model_hash_matches_requirements" -Passed ($observedModelHash -eq $expectedModelHash) -Observed $observedModelHash -Expected $expectedModelHash))
[void]$checks.Add((New-Check -Name "input_hash_matches_requirements" -Passed ($observedInputHash -eq $expectedInputHash) -Observed $observedInputHash -Expected $expectedInputHash))
[void]$checks.Add((New-Check -Name "provisioning_evidence_matches_model_hash" -Passed (([string]$provisioning.runtime_use.lane_id -eq $laneId) -and ([string]$provisioning.sha256).ToLowerInvariant() -eq $expectedModelHash) -Observed ([ordered]@{ lane_id = $provisioning.runtime_use.lane_id; sha256 = $provisioning.sha256 }) -Expected "matching lane and model SHA256"))
[void]$checks.Add((New-Check -Name "model_s3_uri_valid" -Passed (Test-S3Uri -Uri $ModelS3Uri) -Observed $ModelS3Uri -Expected "s3://bucket/model-cache/file"))
[void]$checks.Add((New-Check -Name "input_s3_uri_valid" -Passed (Test-S3Uri -Uri $InputS3Uri) -Observed $InputS3Uri -Expected "s3://bucket/input-prefix/file"))

$failureCategory = $null
if ($laneId -ne "sdxl_realesrgan_upscale_polish_lane") {
  $failureCategory = "lane_contract_mismatch"
} elseif ($observedModelHash -ne $expectedModelHash) {
  $failureCategory = "model_hash_mismatch"
} elseif ($observedInputHash -ne $expectedInputHash) {
  $failureCategory = "input_hash_mismatch"
} elseif (-not (Test-S3Uri -Uri $ModelS3Uri) -or -not (Test-S3Uri -Uri $InputS3Uri)) {
  $failureCategory = "missing_or_invalid_s3_uri"
}

$modelPublish = $null
$inputPublish = $null
$modelInstall = $null
$inputInstall = $null
if ($null -eq $failureCategory) {
  try {
    $opsScripts = Resolve-ProjectPath -Path "Plan\Instructions\Operations\Scripts"
    $modelPublish = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Publish-ModelToS3.ps1") -Arguments @("-ModelFile", $modelPath, "-S3Uri", $ModelS3Uri, "-ExpectedSha256", $expectedModelHash, "-Region", $Region, "-OutFile", $modelPublishFile) -ExpectedOutput $modelPublishFile
    $inputPublish = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Publish-InputAssetToS3.ps1") -Arguments @("-AssetFile", $inputPath, "-S3Uri", $InputS3Uri, "-ExpectedSha256", $expectedInputHash, "-Region", $Region, "-OutFile", $inputPublishFile) -ExpectedOutput $inputPublishFile
    $modelInstall = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Install-EC2ModelFromS3.ps1") -Arguments @("-InstanceId", $InstanceId, "-Region", $Region, "-SourceS3Uri", $ModelS3Uri, "-ModelSubdir", "upscale_models", "-ModelFileName", ([string]$requiredModel.filename), "-ExpectedSha256", $expectedModelHash, "-OutFile", $modelInstallFile) -ExpectedOutput $modelInstallFile
    $inputInstall = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Install-EC2InputAssetFromS3.ps1") -Arguments @("-InstanceId", $InstanceId, "-Region", $Region, "-SourceS3Uri", $InputS3Uri, "-FileName", ([string]$requiredInput.filename), "-ExpectedSha256", $expectedInputHash, "-OutFile", $inputInstallFile) -ExpectedOutput $inputInstallFile
  } catch {
    $failureCategory = "child_dry_run_invocation_failed"
    [void]$checks.Add((New-Check -Name "child_dry_run_invocation" -Passed $false -Observed $_.Exception.Message -Expected "all four child helpers exit 0 and write JSON"))
  }
}

if ($null -ne $modelPublish) {
  [void]$checks.Add((New-Check -Name "model_publish_dry_run_pass" -Passed (
    [string]$modelPublish.result -eq "dry_run_ready_to_upload_model" -and
    [bool]$modelPublish.local_only -and [bool]$modelPublish.local_hash_match -and
    (Test-PropertyFalse -Payload $modelPublish -Name "aws_contacted") -and
    (Test-PropertyFalse -Payload $modelPublish -Name "s3_contacted") -and
    (Test-PropertyFalse -Payload $modelPublish -Name "ec2_started") -and
    (Test-PropertyFalse -Payload $modelPublish -Name "generation_executed")
  ) -Observed $modelPublish -Expected "hash-matched local dry-run publish with no contact"))
}
if ($null -ne $inputPublish) {
  [void]$checks.Add((New-Check -Name "input_publish_dry_run_pass" -Passed (
    [string]$inputPublish.result -eq "dry_run_ready_to_upload_input_asset" -and
    [bool]$inputPublish.local_only -and [bool]$inputPublish.local_hash_match -and
    (Test-PropertyFalse -Payload $inputPublish -Name "aws_contacted") -and
    (Test-PropertyFalse -Payload $inputPublish -Name "s3_contacted") -and
    (Test-PropertyFalse -Payload $inputPublish -Name "ec2_started") -and
    (Test-PropertyFalse -Payload $inputPublish -Name "generation_executed")
  ) -Observed $inputPublish -Expected "hash-matched local dry-run publish with no contact"))
}
if ($null -ne $modelInstall) {
  [void]$checks.Add((New-Check -Name "model_install_dry_run_pass" -Passed (
    [string]$modelInstall.result -eq "dry_run_model_install_plan" -and
    -not [bool]$modelInstall.execute -and -not [bool]$modelInstall.ec2_started -and
    -not [bool]$modelInstall.generation_executed -and [string]$modelInstall.command_status -eq "not_started"
  ) -Observed $modelInstall -Expected "dry-run model install plan with no EC2 start"))
}
if ($null -ne $inputInstall) {
  [void]$checks.Add((New-Check -Name "input_install_dry_run_pass" -Passed (
    [string]$inputInstall.result -eq "dry_run_input_asset_install_plan" -and
    -not [bool]$inputInstall.execute -and -not [bool]$inputInstall.ec2_started -and
    -not [bool]$inputInstall.generation_executed -and [string]$inputInstall.command_status -eq "not_started"
  ) -Observed $inputInstall -Expected "dry-run input install plan with no EC2 start"))
}

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
if ($null -eq $failureCategory -and $failedChecks.Count -gt 0) {
  $failureCategory = "unsafe_or_unexpected_child_contract"
}
$result = if ($null -eq $failureCategory -and $failedChecks.Count -eq 0) {
  "pass_local_only_realesrgan_asset_transfer_dry_run_bundle_validated"
} else {
  "fail_realesrgan_asset_transfer_dry_run_bundle_validation"
}

$artifactRows = @()
foreach ($artifact in @(
  @{ name = "model_s3_publish_dry_run"; path = $modelPublishFile; payload = $modelPublish },
  @{ name = "input_s3_publish_dry_run"; path = $inputPublishFile; payload = $inputPublish },
  @{ name = "model_ec2_install_dry_run"; path = $modelInstallFile; payload = $modelInstall },
  @{ name = "input_ec2_install_dry_run"; path = $inputInstallFile; payload = $inputInstall }
)) {
  if ($null -ne $artifact.payload) {
    $artifactRows += [pscustomobject][ordered]@{
      name = $artifact.name
      result = [string]$artifact.payload.result
      evidence = ConvertTo-ProjectRelativePath -Path $artifact.path
    }
  }
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "realesrgan_lane_asset_transfer_dry_run_bundle"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  tracker_id = "WO-W66-SDXL_REALESRGAN_UPSCALE_POLISH_LANE-TARGET-RUNTIME-PROOF"
  lane_id = $laneId
  result = $result
  failure_category = $failureCategory
  local_only = $true
  aws_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  active_runtime_marker_written = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  jira_mutated = $false
  target_runtime_proof = $false
  certification_claimed = $false
  promotion_allowed = $false
  execute_allowed_now = $false
  lane_runtime_requirements = ConvertTo-ProjectRelativePath -Path $requirementsPath
  model_provisioning_evidence = ConvertTo-ProjectRelativePath -Path $provisioningPath
  model_file = ConvertTo-ProjectRelativePath -Path $modelPath
  input_role = $InputRole
  input_asset_file = ConvertTo-ProjectRelativePath -Path $inputPath
  model_s3_uri = $ModelS3Uri
  input_s3_uri = $InputS3Uri
  expected_model_sha256 = $expectedModelHash
  observed_model_sha256 = $observedModelHash
  expected_input_sha256 = $expectedInputHash
  observed_input_sha256 = $observedInputHash
  child_artifact_count = @($artifactRows).Count
  artifacts = @($artifactRows)
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  exact_blockers = @(
    "explicit_live_execution_intent_required",
    "model_s3_publish_execute_proof_missing",
    "input_s3_publish_execute_proof_missing",
    "ec2_model_install_hash_proof_missing",
    "ec2_input_install_hash_proof_missing",
    "target_runtime_static_proof_missing",
    "bounded_target_runtime_output_and_strict_visual_qa_missing"
  )
  boundary = "Local RealESRGAN asset-transfer dry-run bundle only. This does not upload assets, start EC2, install remotely, contact ComfyUI, execute generation, prove target runtime, promote the lane, or claim certification."
  next_action = "Keep EC2 stopped. Use these pinned model/input URIs and hashes only after explicit live intent, current AWS auth, clean Git/deploy gates, and bounded target-runtime authorization."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outPath -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownPath -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outPath, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$artifactLines = @($artifactRows | ForEach-Object { "- $($_.name): $($_.result) ($($_.evidence))" }) -join [Environment]::NewLine
$checkLines = @($checks | ForEach-Object { "- $($_.name): $($_.result)" }) -join [Environment]::NewLine
$markdown = @"
# RealESRGAN Asset Transfer Dry-Run Bundle

- created_at: $($record.created_at)
- result: $($record.result)
- lane_id: $($record.lane_id)
- target_runtime_proof: false
- certification_claimed: false
- execute_allowed_now: false
- failed_check_count: $($record.failed_check_count)

## Child Artifacts

$artifactLines

## Checks

$checkLines

## Boundary

$($record.boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownPath, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($result -like "fail_*") { exit 2 }
exit 0
