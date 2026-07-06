<#
.SYNOPSIS
Builds a local-only EC2 execution plan for a run-package matrix.

.DESCRIPTION
Validates a run-package matrix and emits the bounded command sequence needed
for a future multi-sample EC2 quality pass. This does not contact AWS, GitHub
APIs, Civitai, ComfyUI, or EC2, and it does not execute generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RunPackageMatrixManifestFile = "runtime_artifacts\run_package_matrices\realvisxl_multisample_certification_v1\RUN_PACKAGE_MATRIX_MANIFEST.json",
  [string]$DeployBundleS3Uri = "",
  [string]$DeployBundleSha256 = "",
  [string]$StaticProofFile = "<static-proof-json>",
  [string]$ReadinessFile = "<readiness-json>",
  [int]$MaxEc2RuntimeMinutes = 45,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 40
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
  param([string]$BasePath, [string]$TargetPath)
  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  if (![System.IO.Path]::IsPathRooted($TargetPath)) { return $TargetPath.Replace("\", "/") }
  return (Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath).Replace("\", "/")
}

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Assert-UnderProject {
  param([Parameter(Mandatory=$true)][string]$Path)
  $projectFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $targetFull = [System.IO.Path]::GetFullPath($Path)
  if (!$targetFull.StartsWith($projectFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing path outside ProjectRoot: $Path"
  }
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

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root missing: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$matrixPath = Resolve-ProjectPath -Path $RunPackageMatrixManifestFile
Assert-UnderProject -Path $matrixPath
$matrix = Read-JsonFile -Path $matrixPath

if ([string]$matrix.result -ne "pass_local_only") {
  throw "Matrix manifest must be pass_local_only: $matrixPath"
}

$laneId = [string]$matrix.lane_id
if ([string]::IsNullOrWhiteSpace($laneId)) {
  throw "Matrix manifest is missing lane_id."
}
$samples = @($matrix.samples)
if ($samples.Count -eq 0) {
  throw "Matrix manifest has no samples."
}

$workflowRunner = "C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1"
$pullbackHelper = "C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1"
$imageQaHelper = "C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1"
$deployBundleArgs = ""
if (![string]::IsNullOrWhiteSpace($DeployBundleS3Uri)) {
  $deployBundleArgs += " -DeployBundleS3Uri $DeployBundleS3Uri"
}
if (![string]::IsNullOrWhiteSpace($DeployBundleSha256)) {
  $deployBundleArgs += " -DeployBundleSha256 $DeployBundleSha256"
}

$plannedSamples = @()
$checks = @()
$seenRunIds = New-Object System.Collections.Generic.HashSet[string]
$seenPromptHashes = New-Object System.Collections.Generic.HashSet[string]

foreach ($sample in $samples) {
  $manifestPath = Resolve-ProjectPath -Path ([string]$sample.manifest_path)
  Assert-UnderProject -Path $manifestPath
  $package = Read-JsonFile -Path $manifestPath
  $runId = [string]$sample.run_id
  $profileId = [string]$sample.profile_id
  $promptHash = [string]$package.prompt_request.sha256
  [void]$seenRunIds.Add($runId)
  if (![string]::IsNullOrWhiteSpace($promptHash)) { [void]$seenPromptHashes.Add($promptHash) }

  $workflowOut = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_EC2_WORKFLOW_MATRIX_$runId`_<timestamp>.json"
  $pullbackRoot = "C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\$runId"
  $pullbackRecord = "$pullbackRoot\PULLBACK_RECORD.json"
  $imageQaRecord = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W66_IMAGE_QA_MATRIX_$runId`_<timestamp>.json"
  $imageQaChecklist = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W66_IMAGE_QA_MATRIX_$runId`_<timestamp>.md"

  $workflowCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File $workflowRunner -ProjectRoot C:\Comfy_UI_Main -LaneId $laneId -Execute -SkipGitLfsPull$deployBundleArgs -MaxEc2RuntimeMinutes $MaxEc2RuntimeMinutes -StaticProofFile $StaticProofFile -ReadinessFile $ReadinessFile -RunPackageManifestFile $manifestPath -OutFile $workflowOut"
  $pullbackCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File $pullbackHelper -ProjectRoot C:\Comfy_UI_Main -RunId $runId -LocalDestination $pullbackRoot -RemoteManifestFile $pullbackRoot\REMOTE_ARTIFACT_MANIFEST.json -OutFile $pullbackRecord"
  $imageQaCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File $imageQaHelper -ImagePath <pulled-back-image-for-$runId> -OutFile $imageQaRecord -ChecklistOutFile $imageQaChecklist"

  $plannedSamples += [ordered]@{
    profile_id = $profileId
    certification_focus = [string]$sample.certification_focus
    run_id = $runId
    run_package_manifest = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $manifestPath
    package_result = [string]$package.result
    route_result = [string]$package.route_gate.result
    route_selected_lane_id = [string]$package.route_gate.selected_lane_id
    prompt_profile_applied = [bool]$package.prompt_profile.applied
    prompt_request_sha256 = $promptHash
    expected_output_prefix = [string]$sample.output_prefix
    workflow_command = $workflowCommand
    pullback_command = $pullbackCommand
    whole_image_qa_command = $imageQaCommand
    required_post_run_evidence = @(
      $workflowOut,
      "$pullbackRoot\REMOTE_ARTIFACT_MANIFEST.json",
      $pullbackRecord,
      $imageQaRecord,
      $imageQaChecklist
    )
  }
}

$checks += New-Check -Name "sample_count_matches_matrix" -Passed ($plannedSamples.Count -eq $samples.Count) -Observed $plannedSamples.Count -Expected $samples.Count
$checks += New-Check -Name "all_sample_run_ids_unique" -Passed ($seenRunIds.Count -eq $samples.Count) -Observed $seenRunIds.Count -Expected $samples.Count
$checks += New-Check -Name "all_prompt_hashes_unique" -Passed ($seenPromptHashes.Count -eq $samples.Count) -Observed $seenPromptHashes.Count -Expected $samples.Count
$workflowCommands = @($plannedSamples | ForEach-Object { [string]$_["workflow_command"] })
$checks += New-Check -Name "all_packages_pass" -Passed (@($plannedSamples | Where-Object { [string]$_["package_result"] -ne "pass_local_only" }).Count -eq 0) -Observed @($plannedSamples | ForEach-Object { $_["package_result"] }) -Expected "all pass_local_only"
$checks += New-Check -Name "all_route_gates_pass" -Passed (@($plannedSamples | Where-Object { [string]$_["route_result"] -ne "pass_local_only" }).Count -eq 0) -Observed @($plannedSamples | ForEach-Object { $_["route_result"] }) -Expected "all pass_local_only"
$checks += New-Check -Name "all_routes_match_lane" -Passed (@($plannedSamples | Where-Object { [string]$_["route_selected_lane_id"] -ne $laneId }).Count -eq 0) -Observed @($plannedSamples | ForEach-Object { $_["route_selected_lane_id"] }) -Expected $laneId
$checks += New-Check -Name "all_workflow_commands_use_run_packages" -Passed (@($workflowCommands | Where-Object { $_ -notmatch "-RunPackageManifestFile" }).Count -eq 0) -Observed $workflowCommands -Expected "-RunPackageManifestFile on every sample"
$checks += New-Check -Name "all_workflow_commands_use_cost_controls" -Passed (@($workflowCommands | Where-Object { $_ -notmatch "-SkipGitLfsPull" -or $_ -notmatch "-MaxEc2RuntimeMinutes" }).Count -eq 0) -Observed $workflowCommands -Expected "-SkipGitLfsPull and -MaxEc2RuntimeMinutes"
$checks += New-Check -Name "deploy_bundle_args_present_when_supplied" -Passed (([string]::IsNullOrWhiteSpace($DeployBundleS3Uri) -or @($workflowCommands | Where-Object { $_ -notmatch "-DeployBundleS3Uri" }).Count -eq 0) -and ([string]::IsNullOrWhiteSpace($DeployBundleSha256) -or @($workflowCommands | Where-Object { $_ -notmatch "-DeployBundleSha256" }).Count -eq 0)) -Observed $workflowCommands -Expected "S3 bundle URI/SHA args present when supplied"
$checks += New-Check -Name "all_samples_require_pullback_and_whole_image_qa" -Passed (@($plannedSamples | Where-Object { [string]::IsNullOrWhiteSpace([string]$_["pullback_command"]) -or [string]::IsNullOrWhiteSpace([string]$_["whole_image_qa_command"]) }).Count -eq 0) -Observed @($plannedSamples | ForEach-Object { [ordered]@{ run_id = $_["run_id"]; pullback = $_["pullback_command"]; qa = $_["whole_image_qa_command"] } }) -Expected "pullback and whole-image QA command for every sample"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$record = [ordered]@{
  evidence_id = "W66-EC2-WORKFLOW-MATRIX-QUALITY-RUN-PLAN-$stamp"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  artifact_type = "ec2_workflow_matrix_quality_run_plan"
  matrix_id = [string]$matrix.matrix_id
  lane_id = $laneId
  sample_count = $samples.Count
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  execution_ready = $false
  execution_ready_reason = "This record is a local-only plan. Live execution still requires AWS auth, clean pushed Git, S3 bundle publish, static proof/readiness gates, artifact pullback, and whole-image QA."
  inputs = [ordered]@{
    matrix_manifest = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $matrixPath
    deploy_bundle_s3_uri_supplied = ![string]::IsNullOrWhiteSpace($DeployBundleS3Uri)
    deploy_bundle_sha256_supplied = ![string]::IsNullOrWhiteSpace($DeployBundleSha256)
    deploy_bundle_s3_uri = $DeployBundleS3Uri
    deploy_bundle_sha256 = $DeployBundleSha256
    static_proof_file = $StaticProofFile
    readiness_file = $ReadinessFile
    max_ec2_runtime_minutes = $MaxEc2RuntimeMinutes
  }
  planned_samples = $plannedSamples
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = "After S3 config and auth gates pass, publish the matrix bundle, run each planned workflow command, pull back all artifacts, and complete whole-image QA for every sample."
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 60
}

$record | ConvertTo-Json -Depth 60
if ($record.result -ne "pass_local_only") { exit 1 }
