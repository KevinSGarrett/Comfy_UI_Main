<#
.SYNOPSIS
Runs the selected-inpaint local pre-EC2 evidence chain under one session stamp.

.DESCRIPTION
Invokes four existing local-only generators in dependency order, pins each
new downstream artifact explicitly, and validates their shared fail-closed
contract. This helper never contacts external services or authorizes live
execution.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_realvisxl_inpaint_detail_lane",
  [string]$SessionStamp = "",
  [string]$TargetRuntimePlanFile = "",
  [string]$SelectedPackageReadinessFile = "",
  [string]$SelectedLaunchGateFile = "",
  [string]$PackageDeployMatrixFile = "",
  [string]$SelectedS3PublishReadinessFile = "",
  [string]$SelectedInputAssetInstallReadinessFile = "",
  [string]$SelectedModelCacheReadinessFile = "",
  [string]$SelectedModelS3PublishDryRunFile = "",
  [string]$SelectedInputAssetSourceS3PublishDryRunFile = "",
  [string]$SelectedInputAssetMaskS3PublishDryRunFile = "",
  [string]$ClosureRollupFile = "",
  [string]$GitCheckpointGateFile = "",
  [string]$RuntimeUnblockHandoffFile = "",
  [string]$LocalSupportCertificationFile = "",
  [string]$RuntimeLaneQueueFile = "",
  [string]$ModelRegistryCoverageFile = "",
  [string]$ProjectReadinessSnapshotFile = "",
  [string]$ModelInstallDryRunFile = "",
  [string]$SourceInputInstallDryRunFile = "",
  [string]$MaskInputInstallDryRunFile = "",
  [string]$ArtifactOutputDirectory = "",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([Parameter(Mandatory = $true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $Path))
}

function ConvertTo-ProjectRelativePath {
  param([Parameter(Mandatory = $true)][string]$Path)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $resolved = [System.IO.Path]::GetFullPath($Path)
  if ($resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $resolved.Substring($root.Length).Replace("\", "/")
  }
  return $resolved
}

function Add-OptionalArgument {
  param(
    [Parameter(Mandatory = $true)][System.Collections.Generic.List[string]]$Arguments,
    [Parameter(Mandatory = $true)][string]$Name,
    [AllowEmptyString()][string]$Value
  )
  if (-not [string]::IsNullOrWhiteSpace($Value)) {
    [void]$Arguments.Add("-$Name")
    [void]$Arguments.Add($Value)
  }
}

function Invoke-JsonGenerator {
  param(
    [Parameter(Mandatory = $true)][string]$ScriptPath,
    [Parameter(Mandatory = $true)][System.Collections.Generic.List[string]]$GeneratorArguments,
    [Parameter(Mandatory = $true)][string]$JsonOutFile
  )

  if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
    throw "Generator script not found: $ScriptPath"
  }

  $commandArguments = [System.Collections.Generic.List[string]]::new()
  foreach ($value in @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath)) {
    [void]$commandArguments.Add($value)
  }
  foreach ($value in $GeneratorArguments) {
    [void]$commandArguments.Add($value)
  }

  $output = & powershell @commandArguments 2>&1
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    $tail = @($output | Select-Object -Last 20) -join [Environment]::NewLine
    throw "Generator failed with exit code $exitCode`: $ScriptPath$([Environment]::NewLine)$tail"
  }
  if (-not (Test-Path -LiteralPath $JsonOutFile -PathType Leaf)) {
    throw "Generator did not create expected JSON: $JsonOutFile"
  }
  return Get-Content -LiteralPath $JsonOutFile -Raw | ConvertFrom-Json
}

function Test-Property {
  param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string]$Name)
  return ($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name])
}

function Assert-ChildContract {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][object]$Payload,
    [Parameter(Mandatory = $true)][string[]]$ExpectedResults,
    [Parameter(Mandatory = $true)][string]$LaneProperty,
    [Parameter(Mandatory = $true)][string]$JsonPath,
    [Parameter(Mandatory = $true)][string]$MarkdownPath
  )

  $failures = [System.Collections.Generic.List[string]]::new()
  if (@($ExpectedResults) -notcontains [string]$Payload.result) {
    [void]$failures.Add("unexpected_result:$($Payload.result)")
  }
  if (-not (Test-Property -Object $Payload -Name $LaneProperty) -or [string]$Payload.$LaneProperty -ne $LaneId) {
    [void]$failures.Add("lane_mismatch:$([string]$Payload.$LaneProperty)")
  }
  if (-not (Test-Property -Object $Payload -Name "local_only") -or -not [bool]$Payload.local_only) {
    [void]$failures.Add("local_only_not_true")
  }
  if (-not (Test-Property -Object $Payload -Name "failed_check_count") -or [int]$Payload.failed_check_count -ne 0) {
    [void]$failures.Add("failed_check_count_not_zero:$([int]$Payload.failed_check_count)")
  }
  foreach ($flag in @("target_runtime_launch_allowed", "execute_allowed_now")) {
    if (-not (Test-Property -Object $Payload -Name $flag) -or [bool]$Payload.$flag) {
      [void]$failures.Add("fail_closed_flag_invalid:$flag")
    }
  }
  foreach ($flag in @("aws_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "active_runtime_marker_written")) {
    if (-not (Test-Property -Object $Payload -Name $flag) -or [bool]$Payload.$flag) {
      [void]$failures.Add("live_side_effect_flag_invalid:$flag")
    }
  }
  foreach ($path in @($JsonPath, $MarkdownPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      [void]$failures.Add("missing_output:$path")
    }
  }

  if ($failures.Count -gt 0) {
    throw "$Name contract failed: $($failures -join ', ')"
  }

  return [pscustomobject][ordered]@{
    name = $Name
    result = [string]$Payload.result
    lane_id = [string]$Payload.$LaneProperty
    failed_check_count = [int]$Payload.failed_check_count
    json = ConvertTo-ProjectRelativePath -Path $JsonPath
    markdown = ConvertTo-ProjectRelativePath -Path $MarkdownPath
    contract_pass = $true
    local_only = $true
    execute_allowed_now = $false
    target_runtime_launch_allowed = $false
    live_side_effects_detected = $false
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

if ([string]::IsNullOrWhiteSpace($SessionStamp)) {
  $SessionStamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
}
if ($SessionStamp -notmatch "^\d{8}T\d{6}-\d{4}$") {
  throw "SessionStamp must use yyyyMMddTHHmmss-zzzz without a colon: $SessionStamp"
}
if ($LaneId -ne "sdxl_realvisxl_inpaint_detail_lane") {
  throw "This wrapper is scoped to sdxl_realvisxl_inpaint_detail_lane; received: $LaneId"
}

$runtimeEvidenceDir = if ([string]::IsNullOrWhiteSpace($ArtifactOutputDirectory)) {
  Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence\Runtime_Readiness"
} else {
  Resolve-ProjectPath -Path $ArtifactOutputDirectory
}
$preJson = Join-Path $runtimeEvidenceDir "W66_SELECTED_TARGET_RUNTIME_PRE_EC2_HANDOFF_BUNDLE_$SessionStamp.json"
$preMarkdown = [System.IO.Path]::ChangeExtension($preJson, ".md")
$ledgerJson = Join-Path $runtimeEvidenceDir "W66_SELECTED_TARGET_RUNTIME_LOCAL_RECHECK_LEDGER_$SessionStamp.json"
$ledgerMarkdown = [System.IO.Path]::ChangeExtension($ledgerJson, ".md")
$runbookJson = Join-Path $runtimeEvidenceDir "W66_SELECTED_TARGET_RUNTIME_LIVE_EXECUTION_RUNBOOK_$SessionStamp.json"
$runbookMarkdown = [System.IO.Path]::ChangeExtension($runbookJson, ".md")
$snapshotJson = Join-Path $runtimeEvidenceDir "W66_SELECTED_TARGET_RUNTIME_EXECUTION_READINESS_SNAPSHOT_$SessionStamp.json"
$snapshotMarkdown = [System.IO.Path]::ChangeExtension($snapshotJson, ".md")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $runtimeEvidenceDir "W66_SELECTED_INPAINT_PRE_EC2_REFRESH_ORCHESTRATION_$SessionStamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}
$orchestrationJson = Resolve-ProjectPath -Path $OutFile
$orchestrationMarkdown = Resolve-ProjectPath -Path $MarkdownOutFile

$preArguments = [System.Collections.Generic.List[string]]::new()
foreach ($value in @("-ProjectRoot", $ProjectRoot, "-OutFile", $preJson, "-MarkdownOutFile", $preMarkdown)) {
  [void]$preArguments.Add($value)
}
Add-OptionalArgument -Arguments $preArguments -Name "TargetRuntimePlanFile" -Value $TargetRuntimePlanFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedPackageReadinessFile" -Value $SelectedPackageReadinessFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedLaunchGateFile" -Value $SelectedLaunchGateFile
Add-OptionalArgument -Arguments $preArguments -Name "PackageDeployMatrixFile" -Value $PackageDeployMatrixFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedS3PublishReadinessFile" -Value $SelectedS3PublishReadinessFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedInputAssetInstallReadinessFile" -Value $SelectedInputAssetInstallReadinessFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedModelCacheReadinessFile" -Value $SelectedModelCacheReadinessFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedModelS3PublishDryRunFile" -Value $SelectedModelS3PublishDryRunFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedInputAssetSourceS3PublishDryRunFile" -Value $SelectedInputAssetSourceS3PublishDryRunFile
Add-OptionalArgument -Arguments $preArguments -Name "SelectedInputAssetMaskS3PublishDryRunFile" -Value $SelectedInputAssetMaskS3PublishDryRunFile
$prePayload = Invoke-JsonGenerator -ScriptPath (Resolve-ProjectPath -Path "Plan\Instructions\QA\Scripts\New-SelectedTargetRuntimePreEC2HandoffBundle.ps1") -GeneratorArguments $preArguments -JsonOutFile $preJson
$preRow = Assert-ChildContract -Name "pre_ec2_handoff_bundle" -Payload $prePayload -ExpectedResults @("pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked") -LaneProperty "lane_id" -JsonPath $preJson -MarkdownPath $preMarkdown

$ledgerArguments = [System.Collections.Generic.List[string]]::new()
foreach ($value in @("-ProjectRoot", $ProjectRoot, "-PreEC2HandoffBundleFile", $preJson, "-OutFile", $ledgerJson, "-MarkdownOutFile", $ledgerMarkdown)) {
  [void]$ledgerArguments.Add($value)
}
Add-OptionalArgument -Arguments $ledgerArguments -Name "ClosureRollupFile" -Value $ClosureRollupFile
Add-OptionalArgument -Arguments $ledgerArguments -Name "GitCheckpointGateFile" -Value $GitCheckpointGateFile
Add-OptionalArgument -Arguments $ledgerArguments -Name "RuntimeUnblockHandoffFile" -Value $RuntimeUnblockHandoffFile
Add-OptionalArgument -Arguments $ledgerArguments -Name "LocalSupportCertificationFile" -Value $LocalSupportCertificationFile
Add-OptionalArgument -Arguments $ledgerArguments -Name "RuntimeLaneQueueFile" -Value $RuntimeLaneQueueFile
Add-OptionalArgument -Arguments $ledgerArguments -Name "ModelRegistryCoverageFile" -Value $ModelRegistryCoverageFile
$ledgerPayload = Invoke-JsonGenerator -ScriptPath (Resolve-ProjectPath -Path "Plan\Instructions\QA\Scripts\New-SelectedTargetRuntimeLocalRecheckLedger.ps1") -GeneratorArguments $ledgerArguments -JsonOutFile $ledgerJson
$ledgerRow = Assert-ChildContract -Name "local_recheck_ledger" -Payload $ledgerPayload -ExpectedResults @("pass_local_only_selected_target_runtime_local_rechecks_accounted_ec2_blocked") -LaneProperty "lane_id" -JsonPath $ledgerJson -MarkdownPath $ledgerMarkdown

$runbookArguments = [System.Collections.Generic.List[string]]::new()
foreach ($value in @("-ProjectRoot", $ProjectRoot, "-PreEC2HandoffBundleFile", $preJson, "-OutFile", $runbookJson, "-MarkdownOutFile", $runbookMarkdown)) {
  [void]$runbookArguments.Add($value)
}
Add-OptionalArgument -Arguments $runbookArguments -Name "SelectedS3PublishReadinessFile" -Value $SelectedS3PublishReadinessFile
Add-OptionalArgument -Arguments $runbookArguments -Name "SelectedInputAssetInstallReadinessFile" -Value $SelectedInputAssetInstallReadinessFile
Add-OptionalArgument -Arguments $runbookArguments -Name "SelectedModelCacheReadinessFile" -Value $SelectedModelCacheReadinessFile
Add-OptionalArgument -Arguments $runbookArguments -Name "ProjectReadinessSnapshotFile" -Value $ProjectReadinessSnapshotFile
$runbookPayload = Invoke-JsonGenerator -ScriptPath (Resolve-ProjectPath -Path "Plan\Instructions\Operations\Scripts\New-SelectedTargetRuntimeLiveExecutionRunbook.ps1") -GeneratorArguments $runbookArguments -JsonOutFile $runbookJson
$runbookRow = Assert-ChildContract -Name "live_execution_runbook" -Payload $runbookPayload -ExpectedResults @("blocked_selected_target_runtime_live_execution_runbook_waiting_for_clean_git_and_explicit_live_intent", "blocked_selected_target_runtime_live_execution_runbook_waiting_for_explicit_live_intent") -LaneProperty "selected_lane_id" -JsonPath $runbookJson -MarkdownPath $runbookMarkdown

$snapshotArguments = [System.Collections.Generic.List[string]]::new()
foreach ($value in @("-ProjectRoot", $ProjectRoot, "-LiveExecutionRunbookFile", $runbookJson, "-OutFile", $snapshotJson, "-MarkdownOutFile", $snapshotMarkdown)) {
  [void]$snapshotArguments.Add($value)
}
Add-OptionalArgument -Arguments $snapshotArguments -Name "ModelInstallDryRunFile" -Value $ModelInstallDryRunFile
Add-OptionalArgument -Arguments $snapshotArguments -Name "SourceInputInstallDryRunFile" -Value $SourceInputInstallDryRunFile
Add-OptionalArgument -Arguments $snapshotArguments -Name "MaskInputInstallDryRunFile" -Value $MaskInputInstallDryRunFile
$snapshotPayload = Invoke-JsonGenerator -ScriptPath (Resolve-ProjectPath -Path "Plan\Instructions\Operations\Scripts\New-SelectedTargetRuntimeExecutionReadinessSnapshot.ps1") -GeneratorArguments $snapshotArguments -JsonOutFile $snapshotJson
$snapshotRow = Assert-ChildContract -Name "execution_readiness_snapshot" -Payload $snapshotPayload -ExpectedResults @("blocked_selected_target_runtime_execution_readiness_local_proofs_complete_live_gates_closed") -LaneProperty "selected_lane_id" -JsonPath $snapshotJson -MarkdownPath $snapshotMarkdown

$childRows = @($preRow, $ledgerRow, $runbookRow, $snapshotRow)
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_inpaint_pre_ec2_refresh_orchestration"
  created_at = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
  result = "pass_local_only_selected_inpaint_pre_ec2_refresh_orchestrated_live_gates_closed"
  lane_id = $LaneId
  session_stamp = $SessionStamp
  local_only = $true
  github_api_contacted = $false
  aws_contacted = $false
  civitai_contacted = $false
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
  execute_allowed_now = $false
  target_runtime_launch_allowed = $false
  child_artifact_count = $childRows.Count
  child_artifacts = $childRows
  failed_child_contract_count = 0
  boundary = "Local selected-inpaint pre-EC2 refresh only. No AWS, S3, EC2, ComfyUI, GitHub, Jira, mask promotion, Wave70 hard-gate, or Wave71+ action is authorized or performed."
  next_action = "Keep EC2 stopped. Use the synchronized artifacts as one fail-closed handoff snapshot; live upload and target-runtime proof still require explicit live intent and all external gates."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $orchestrationJson -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $orchestrationMarkdown -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($orchestrationJson, ($record | ConvertTo-Json -Depth 20) + [Environment]::NewLine, $utf8NoBom)

$childLines = @($childRows | ForEach-Object {
  "- $($_.name): $($_.result) ($($_.json))"
}) -join [Environment]::NewLine
$markdown = @"
# Selected Inpaint Pre-EC2 Refresh Orchestration

- created_at: $($record.created_at)
- result: $($record.result)
- lane_id: $($record.lane_id)
- session_stamp: $($record.session_stamp)
- child_artifact_count: $($record.child_artifact_count)
- failed_child_contract_count: 0
- execute_allowed_now: false
- target_runtime_launch_allowed: false

## Child Artifacts

$childLines

## Boundary

$($record.boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($orchestrationMarkdown, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 20
exit 0
