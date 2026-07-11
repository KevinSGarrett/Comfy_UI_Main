<#
.SYNOPSIS
Builds a local-only asset-transfer dry-run bundle for one ControlNet lane.

.DESCRIPTION
Verifies the selected lane's checkpoint, ControlNet model, active control image,
and cited source artifact. It then invokes existing publish and EC2 install
helpers without -Execute. Preflight failures create no child artifacts.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$LaneId,
  [string]$LaneRuntimeRequirements = "",
  [string]$ModelS3BaseUri = "s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache",
  [string]$InputS3BaseUri = "s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/input-assets",
  [string]$CheckpointS3UriOverride = "",
  [string]$ControlnetS3UriOverride = "",
  [string]$ControlImageS3UriOverride = "",
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

function Get-Sha256 {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
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

function Test-S3BaseUri {
  param([string]$Uri)
  return (-not [string]::IsNullOrWhiteSpace($Uri) -and $Uri -match '^s3://[^/]+/.+' -and -not $Uri.EndsWith('/'))
}

function Test-PropertyFalse {
  param([object]$Payload, [string]$Name)
  return ($null -ne $Payload.PSObject.Properties[$Name] -and -not [bool]$Payload.$Name)
}

function Test-ModelContract {
  param([object]$Row)
  return (
    $null -ne $Row -and
    -not [string]::IsNullOrWhiteSpace([string]$Row.filename) -and
    -not [string]::IsNullOrWhiteSpace([string]$Row.comfyui_model_subdir) -and
    [string]$Row.sha256 -match '^[0-9a-fA-F]{64}$'
  )
}

if ($Execute) {
  throw "Live execution is forbidden. This bundle is local dry-run only."
}
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$laneMapTypes = [ordered]@{
  sdxl_realvisxl_controlnet_depth_lane = "depth"
  sdxl_realvisxl_controlnet_lineart_lane = "lineart"
  sdxl_realvisxl_controlnet_openpose_lane = "openpose"
  sdxl_realvisxl_controlnet_normal_lane = "normal_bae"
}
$supportedLane = $laneMapTypes.Contains($LaneId)
$expectedMapType = if ($supportedLane) { [string]$laneMapTypes[$LaneId] } else { "" }
if ([string]::IsNullOrWhiteSpace($LaneRuntimeRequirements)) {
  $LaneRuntimeRequirements = "Workflows\base_generation\$LaneId\runtime_requirements.json"
}
$requirementsPath = Resolve-ProjectPath -Path $LaneRuntimeRequirements
if (-not (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
  throw "Lane runtime requirements missing: $requirementsPath"
}
$requirements = Get-Content -LiteralPath $requirementsPath -Raw | ConvertFrom-Json

$checkpointRows = @($requirements.required_models | Where-Object { [string]$_.role -eq "checkpoint" })
$controlnetRows = @($requirements.required_models | Where-Object { [string]$_.role -eq "controlnet" })
$controlImageRows = @($requirements.required_input_assets | Where-Object { [string]$_.role -eq "control_image" })
$checkpoint = if ($checkpointRows.Count -eq 1) { $checkpointRows[0] } else { $null }
$controlnet = if ($controlnetRows.Count -eq 1) { $controlnetRows[0] } else { $null }
$controlImage = if ($controlImageRows.Count -eq 1) { $controlImageRows[0] } else { $null }

$checkpointPath = if ($null -ne $checkpoint) { Resolve-ProjectPath -Path ("models\{0}\{1}" -f [string]$checkpoint.comfyui_model_subdir, [string]$checkpoint.filename) } else { "" }
$controlnetPath = if ($null -ne $controlnet) { Resolve-ProjectPath -Path ("models\{0}\{1}" -f [string]$controlnet.comfyui_model_subdir, [string]$controlnet.filename) } else { "" }
$controlImagePath = if ($null -ne $controlImage) { Resolve-ProjectPath -Path ([string]$controlImage.comfyui_input_path) } else { "" }
$sourceArtifactPath = if ($null -ne $controlImage) { Resolve-ProjectPath -Path ([string]$controlImage.source_artifact) } else { "" }

$expectedCheckpointHash = if ($null -ne $checkpoint) { ([string]$checkpoint.sha256).ToLowerInvariant() } else { "" }
$expectedControlnetHash = if ($null -ne $controlnet) { ([string]$controlnet.sha256).ToLowerInvariant() } else { "" }
$expectedInputHash = if ($null -ne $controlImage) { ([string]$controlImage.sha256).ToLowerInvariant() } else { "" }
$observedCheckpointHash = Get-Sha256 -Path $checkpointPath
$observedControlnetHash = Get-Sha256 -Path $controlnetPath
$observedInputHash = Get-Sha256 -Path $controlImagePath
$observedSourceHash = Get-Sha256 -Path $sourceArtifactPath

$modelBaseValid = Test-S3BaseUri -Uri $ModelS3BaseUri
$inputBaseValid = Test-S3BaseUri -Uri $InputS3BaseUri
$checkpointS3Uri = if (-not [string]::IsNullOrWhiteSpace($CheckpointS3UriOverride)) {
  $CheckpointS3UriOverride.TrimEnd('/')
} elseif ($modelBaseValid -and $null -ne $checkpoint) {
  "$ModelS3BaseUri/checkpoints/$([string]$checkpoint.filename)"
} else { "" }
$controlnetS3Uri = if (-not [string]::IsNullOrWhiteSpace($ControlnetS3UriOverride)) {
  $ControlnetS3UriOverride.TrimEnd('/')
} elseif ($modelBaseValid -and $null -ne $controlnet) {
  "$ModelS3BaseUri/controlnet/$([string]$controlnet.filename)"
} else { "" }
$inputS3Uri = if (-not [string]::IsNullOrWhiteSpace($ControlImageS3UriOverride)) {
  $ControlImageS3UriOverride.TrimEnd('/')
} elseif ($inputBaseValid -and $null -ne $controlImage) {
  "$InputS3BaseUri/$LaneId/$([string]$controlImage.filename)"
} else { "" }
$resolvedS3UrisValid = (
  (Test-S3BaseUri -Uri $checkpointS3Uri) -and
  (Test-S3BaseUri -Uri $controlnetS3Uri) -and
  (Test-S3BaseUri -Uri $inputS3Uri)
)

$checks = [System.Collections.Generic.List[object]]::new()
[void]$checks.Add((New-Check -Name "supported_controlnet_lane" -Passed $supportedLane -Observed $LaneId -Expected @($laneMapTypes.Keys)))
[void]$checks.Add((New-Check -Name "requirements_lane_matches" -Passed ([string]$requirements.lane_id -eq $LaneId) -Observed ([string]$requirements.lane_id) -Expected $LaneId))
[void]$checks.Add((New-Check -Name "required_asset_contracts" -Passed (
  $checkpointRows.Count -eq 1 -and $controlnetRows.Count -eq 1 -and $controlImageRows.Count -eq 1 -and
  (Test-ModelContract -Row $checkpoint) -and (Test-ModelContract -Row $controlnet) -and
  $null -ne $controlImage -and [string]$controlImage.sha256 -match '^[0-9a-fA-F]{64}$' -and
  -not [string]::IsNullOrWhiteSpace([string]$controlImage.filename) -and
  -not [string]::IsNullOrWhiteSpace([string]$controlImage.comfyui_input_path) -and
  -not [string]::IsNullOrWhiteSpace([string]$controlImage.source_artifact)
) -Observed ([ordered]@{ checkpoint_count=$checkpointRows.Count; controlnet_count=$controlnetRows.Count; control_image_count=$controlImageRows.Count }) -Expected "one hash-bound checkpoint, ControlNet, and control image"))
[void]$checks.Add((New-Check -Name "control_map_type_matches_lane" -Passed ($supportedLane -and [string]$controlImage.control_map_type -eq $expectedMapType) -Observed ([string]$controlImage.control_map_type) -Expected $expectedMapType))
[void]$checks.Add((New-Check -Name "local_asset_files_present" -Passed (
  -not [string]::IsNullOrWhiteSpace($observedCheckpointHash) -and
  -not [string]::IsNullOrWhiteSpace($observedControlnetHash) -and
  -not [string]::IsNullOrWhiteSpace($observedInputHash) -and
  -not [string]::IsNullOrWhiteSpace($observedSourceHash)
) -Observed ([ordered]@{
  checkpoint=ConvertTo-ProjectRelativePath -Path $checkpointPath
  controlnet=ConvertTo-ProjectRelativePath -Path $controlnetPath
  control_image=ConvertTo-ProjectRelativePath -Path $controlImagePath
  source_artifact=ConvertTo-ProjectRelativePath -Path $sourceArtifactPath
}) -Expected "all four selected-lane local files exist"))
[void]$checks.Add((New-Check -Name "checkpoint_hash_matches" -Passed ($observedCheckpointHash -eq $expectedCheckpointHash) -Observed $observedCheckpointHash -Expected $expectedCheckpointHash))
[void]$checks.Add((New-Check -Name "controlnet_hash_matches" -Passed ($observedControlnetHash -eq $expectedControlnetHash) -Observed $observedControlnetHash -Expected $expectedControlnetHash))
[void]$checks.Add((New-Check -Name "control_image_hash_matches" -Passed ($observedInputHash -eq $expectedInputHash) -Observed $observedInputHash -Expected $expectedInputHash))
[void]$checks.Add((New-Check -Name "source_artifact_hash_matches" -Passed ($observedSourceHash -eq $expectedInputHash) -Observed $observedSourceHash -Expected $expectedInputHash))
[void]$checks.Add((New-Check -Name "resolved_s3_uris_valid" -Passed $resolvedS3UrisValid -Observed ([ordered]@{
  checkpoint=$checkpointS3Uri
  controlnet=$controlnetS3Uri
  input=$inputS3Uri
  checkpoint_override_used=(-not [string]::IsNullOrWhiteSpace($CheckpointS3UriOverride))
  controlnet_override_used=(-not [string]::IsNullOrWhiteSpace($ControlnetS3UriOverride))
  input_override_used=(-not [string]::IsNullOrWhiteSpace($ControlImageS3UriOverride))
}) -Expected "three non-root exact s3://bucket/key URIs without trailing slash"))

$failureCategory = $null
if (-not $supportedLane) {
  $failureCategory = "unsupported_controlnet_lane"
} elseif ([string]$requirements.lane_id -ne $LaneId) {
  $failureCategory = "lane_contract_mismatch"
} elseif ($checkpointRows.Count -ne 1 -or $controlnetRows.Count -ne 1 -or $controlImageRows.Count -ne 1) {
  $failureCategory = "required_asset_contract_invalid"
} elseif ([string]$controlImage.control_map_type -ne $expectedMapType) {
  $failureCategory = "control_map_type_mismatch"
} elseif ([string]::IsNullOrWhiteSpace($observedCheckpointHash) -or [string]::IsNullOrWhiteSpace($observedControlnetHash) -or [string]::IsNullOrWhiteSpace($observedInputHash) -or [string]::IsNullOrWhiteSpace($observedSourceHash)) {
  $failureCategory = "required_local_asset_missing"
} elseif ($observedCheckpointHash -ne $expectedCheckpointHash) {
  $failureCategory = "checkpoint_hash_mismatch"
} elseif ($observedControlnetHash -ne $expectedControlnetHash) {
  $failureCategory = "controlnet_hash_mismatch"
} elseif ($observedInputHash -ne $expectedInputHash) {
  $failureCategory = "control_image_hash_mismatch"
} elseif ($observedSourceHash -ne $expectedInputHash) {
  $failureCategory = "source_artifact_hash_mismatch"
} elseif (-not $resolvedS3UrisValid) {
  $failureCategory = "missing_or_invalid_resolved_s3_uri"
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$laneTag = $expectedMapType.ToUpperInvariant().Replace("_", "-")
if ([string]::IsNullOrWhiteSpace($laneTag)) { $laneTag = "INVALID" }
if ([string]::IsNullOrWhiteSpace($ArtifactOutputDirectory)) {
  $ArtifactOutputDirectory = "Plan\Instructions\QA\Evidence\Runtime_Readiness"
}
$artifactDir = Resolve-ProjectPath -Path $ArtifactOutputDirectory
[System.IO.Directory]::CreateDirectory($artifactDir) | Out-Null

$checkpointPublishFile = Join-Path $artifactDir "W66_CONTROLNET_$($laneTag)_CHECKPOINT_S3_PUBLISH_DRY_RUN_$stamp.json"
$controlnetPublishFile = Join-Path $artifactDir "W66_CONTROLNET_$($laneTag)_MODEL_S3_PUBLISH_DRY_RUN_$stamp.json"
$inputPublishFile = Join-Path $artifactDir "W66_CONTROLNET_$($laneTag)_INPUT_S3_PUBLISH_DRY_RUN_$stamp.json"
$checkpointInstallFile = Join-Path $artifactDir "W66_CONTROLNET_$($laneTag)_CHECKPOINT_EC2_INSTALL_DRY_RUN_$stamp.json"
$controlnetInstallFile = Join-Path $artifactDir "W66_CONTROLNET_$($laneTag)_MODEL_EC2_INSTALL_DRY_RUN_$stamp.json"
$inputInstallFile = Join-Path $artifactDir "W66_CONTROLNET_$($laneTag)_INPUT_EC2_INSTALL_DRY_RUN_$stamp.json"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $artifactDir "W66_CONTROLNET_$($laneTag)_ASSET_TRANSFER_DRY_RUN_BUNDLE_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($outPath, ".md")
}
$markdownPath = Resolve-ProjectPath -Path $MarkdownOutFile

$checkpointPublish = $null
$controlnetPublish = $null
$inputPublish = $null
$checkpointInstall = $null
$controlnetInstall = $null
$inputInstall = $null
if ($null -eq $failureCategory) {
  try {
    $opsScripts = Resolve-ProjectPath -Path "Plan\Instructions\Operations\Scripts"
    $checkpointPublish = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Publish-ModelToS3.ps1") -Arguments @("-ModelFile", $checkpointPath, "-S3Uri", $checkpointS3Uri, "-ExpectedSha256", $expectedCheckpointHash, "-Region", $Region, "-OutFile", $checkpointPublishFile) -ExpectedOutput $checkpointPublishFile
    $controlnetPublish = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Publish-ModelToS3.ps1") -Arguments @("-ModelFile", $controlnetPath, "-S3Uri", $controlnetS3Uri, "-ExpectedSha256", $expectedControlnetHash, "-Region", $Region, "-OutFile", $controlnetPublishFile) -ExpectedOutput $controlnetPublishFile
    $inputPublish = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Publish-InputAssetToS3.ps1") -Arguments @("-AssetFile", $controlImagePath, "-S3Uri", $inputS3Uri, "-ExpectedSha256", $expectedInputHash, "-Region", $Region, "-OutFile", $inputPublishFile) -ExpectedOutput $inputPublishFile
    $checkpointInstall = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Install-EC2ModelFromS3.ps1") -Arguments @("-InstanceId", $InstanceId, "-Region", $Region, "-SourceS3Uri", $checkpointS3Uri, "-ModelSubdir", ([string]$checkpoint.comfyui_model_subdir), "-ModelFileName", ([string]$checkpoint.filename), "-ExpectedSha256", $expectedCheckpointHash, "-OutFile", $checkpointInstallFile) -ExpectedOutput $checkpointInstallFile
    $controlnetInstall = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Install-EC2ModelFromS3.ps1") -Arguments @("-InstanceId", $InstanceId, "-Region", $Region, "-SourceS3Uri", $controlnetS3Uri, "-ModelSubdir", ([string]$controlnet.comfyui_model_subdir), "-ModelFileName", ([string]$controlnet.filename), "-ExpectedSha256", $expectedControlnetHash, "-OutFile", $controlnetInstallFile) -ExpectedOutput $controlnetInstallFile
    $inputInstallArgs = @("-InstanceId", $InstanceId, "-Region", $Region, "-SourceS3Uri", $inputS3Uri)
    if (-not [string]::IsNullOrWhiteSpace([string]$controlImage.comfyui_input_subdir)) {
      $inputInstallArgs += @("-InputSubdir", ([string]$controlImage.comfyui_input_subdir))
    }
    $inputInstallArgs += @("-FileName", ([string]$controlImage.filename), "-ExpectedSha256", $expectedInputHash, "-OutFile", $inputInstallFile)
    $inputInstall = Invoke-JsonChild -ScriptPath (Join-Path $opsScripts "Install-EC2InputAssetFromS3.ps1") -Arguments $inputInstallArgs -ExpectedOutput $inputInstallFile
  } catch {
    $failureCategory = "child_dry_run_invocation_failed"
    [void]$checks.Add((New-Check -Name "child_dry_run_invocation" -Passed $false -Observed $_.Exception.Message -Expected "all six child helpers exit 0 and write JSON"))
  }
}

foreach ($entry in @(
  @{ name="checkpoint_publish_dry_run"; payload=$checkpointPublish; expected="dry_run_ready_to_upload_model"; kind="publish" },
  @{ name="controlnet_publish_dry_run"; payload=$controlnetPublish; expected="dry_run_ready_to_upload_model"; kind="publish" },
  @{ name="input_publish_dry_run"; payload=$inputPublish; expected="dry_run_ready_to_upload_input_asset"; kind="publish" },
  @{ name="checkpoint_install_dry_run"; payload=$checkpointInstall; expected="dry_run_model_install_plan"; kind="install" },
  @{ name="controlnet_install_dry_run"; payload=$controlnetInstall; expected="dry_run_model_install_plan"; kind="install" },
  @{ name="input_install_dry_run"; payload=$inputInstall; expected="dry_run_input_asset_install_plan"; kind="install" }
)) {
  if ($null -ne $entry.payload) {
    $passed = if ($entry.kind -eq "publish") {
      [string]$entry.payload.result -eq $entry.expected -and [bool]$entry.payload.local_only -and [bool]$entry.payload.local_hash_match -and
      (Test-PropertyFalse -Payload $entry.payload -Name "aws_contacted") -and
      (Test-PropertyFalse -Payload $entry.payload -Name "s3_contacted") -and
      (Test-PropertyFalse -Payload $entry.payload -Name "ec2_started") -and
      (Test-PropertyFalse -Payload $entry.payload -Name "generation_executed")
    } else {
      [string]$entry.payload.result -eq $entry.expected -and -not [bool]$entry.payload.execute -and
      -not [bool]$entry.payload.ec2_started -and -not [bool]$entry.payload.generation_executed -and
      [string]$entry.payload.command_status -eq "not_started"
    }
    [void]$checks.Add((New-Check -Name $entry.name -Passed $passed -Observed $entry.payload -Expected "$($entry.expected) with no external contact or execution"))
  }
}

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
if ($null -eq $failureCategory -and $failedChecks.Count -gt 0) {
  $failureCategory = "unsafe_or_unexpected_child_contract"
}
$result = if ($null -eq $failureCategory -and $failedChecks.Count -eq 0) {
  "pass_local_only_controlnet_asset_transfer_dry_run_bundle_validated"
} else {
  "fail_controlnet_asset_transfer_dry_run_bundle_validation"
}

$artifactRows = @()
foreach ($artifact in @(
  @{ name="checkpoint_s3_publish_dry_run"; path=$checkpointPublishFile; payload=$checkpointPublish },
  @{ name="controlnet_s3_publish_dry_run"; path=$controlnetPublishFile; payload=$controlnetPublish },
  @{ name="input_s3_publish_dry_run"; path=$inputPublishFile; payload=$inputPublish },
  @{ name="checkpoint_ec2_install_dry_run"; path=$checkpointInstallFile; payload=$checkpointInstall },
  @{ name="controlnet_ec2_install_dry_run"; path=$controlnetInstallFile; payload=$controlnetInstall },
  @{ name="input_ec2_install_dry_run"; path=$inputInstallFile; payload=$inputInstall }
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
  artifact_type = "controlnet_lane_asset_transfer_dry_run_bundle"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  tracker_id = "WO-W66-$($LaneId.ToUpperInvariant().Replace('_','-'))-TARGET-RUNTIME-PROOF"
  lane_id = $LaneId
  control_map_type = $expectedMapType
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
  checkpoint_file = ConvertTo-ProjectRelativePath -Path $checkpointPath
  controlnet_file = ConvertTo-ProjectRelativePath -Path $controlnetPath
  control_image_file = ConvertTo-ProjectRelativePath -Path $controlImagePath
  source_artifact_file = ConvertTo-ProjectRelativePath -Path $sourceArtifactPath
  checkpoint_s3_uri = $checkpointS3Uri
  controlnet_s3_uri = $controlnetS3Uri
  input_s3_uri = $inputS3Uri
  expected_checkpoint_sha256 = $expectedCheckpointHash
  observed_checkpoint_sha256 = $observedCheckpointHash
  expected_controlnet_sha256 = $expectedControlnetHash
  observed_controlnet_sha256 = $observedControlnetHash
  expected_input_sha256 = $expectedInputHash
  observed_input_sha256 = $observedInputHash
  observed_source_artifact_sha256 = $observedSourceHash
  child_artifact_count = @($artifactRows).Count
  artifacts = @($artifactRows)
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  exact_blockers = @(
    "explicit_live_execution_intent_required",
    "checkpoint_s3_publish_execute_proof_missing",
    "controlnet_s3_publish_execute_proof_missing",
    "control_image_s3_publish_execute_proof_missing",
    "ec2_checkpoint_install_hash_proof_missing",
    "ec2_controlnet_install_hash_proof_missing",
    "ec2_control_image_install_hash_proof_missing",
    "target_runtime_static_proof_missing",
    "bounded_target_runtime_output_and_strict_visual_qa_missing"
  )
  boundary = "Local ControlNet asset-transfer dry-run bundle only. This does not upload assets, start EC2, install remotely, contact ComfyUI, execute generation, prove target runtime, promote the lane, complete Items/Tracker rows, or claim certification."
  next_action = "Keep EC2 stopped. Use these pinned URIs and hashes only after explicit live intent, current AWS auth, clean Git/deploy gates, and bounded target-runtime authorization."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outPath -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownPath -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outPath, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$artifactLines = @($artifactRows | ForEach-Object { "- $($_.name): $($_.result) ($($_.evidence))" }) -join [Environment]::NewLine
$checkLines = @($checks | ForEach-Object { "- $($_.name): $($_.result)" }) -join [Environment]::NewLine
$markdown = @"
# ControlNet Asset Transfer Dry-Run Bundle

- created_at: $($record.created_at)
- result: $($record.result)
- lane_id: $($record.lane_id)
- control_map_type: $($record.control_map_type)
- child_artifact_count: $($record.child_artifact_count)
- failed_check_count: $($record.failed_check_count)
- target_runtime_proof: false
- certification_claimed: false
- execute_allowed_now: false

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
