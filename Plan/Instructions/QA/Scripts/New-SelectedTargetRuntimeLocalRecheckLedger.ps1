<#
.SYNOPSIS
Creates a local-only ledger for selected target-runtime pre-EC2 rechecks.

.DESCRIPTION
Reads the selected pre-EC2 handoff bundle plus the six allowed local recheck
evidence files: closure rollup, Git checkpoint dry-run, runtime unblock
handoff, active runtime queue local support, runtime lane queue, and model
registry coverage. The ledger accounts for expected blockers without
authorizing live upload, marker writes, EC2 start, prompt posting, or
generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$PreEC2HandoffBundleFile = "",
  [string]$ClosureRollupFile = "",
  [string]$GitCheckpointGateFile = "",
  [string]$RuntimeUnblockHandoffFile = "",
  [string]$LocalSupportCertificationFile = "",
  [string]$RuntimeLaneQueueFile = "",
  [string]$ModelRegistryCoverageFile = "",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return $null }
  $text = [string]$Path
  if ([string]::IsNullOrWhiteSpace($text)) { return $null }
  if ([System.IO.Path]::IsPathRooted($text)) { return [System.IO.Path]::GetFullPath($text) }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $text))
}

function ConvertTo-ProjectRelativePath {
  param([AllowNull()][object]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if ($null -eq $resolved) { return $null }
  $rootFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $targetFull = [System.IO.Path]::GetFullPath($resolved)
  if ($targetFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $targetFull.Substring($rootFull.Length).Replace("\", "/")
  }
  return $targetFull
}

function Read-JsonFile {
  param([Parameter(Mandatory = $true)][string]$Path)
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Find-LatestFile {
  param([string]$Directory, [string]$Filter)
  if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $item = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTimeUtc, Name -Descending |
    Select-Object -First 1
  if ($null -eq $item) { return $null }
  return $item.FullName
}

function Has-Property {
  param([AllowNull()][object]$Object, [string]$Name)
  return ($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name])
}

function Get-BoolValue {
  param([AllowNull()][object]$Object, [string]$Name, [bool]$Default = $false)
  if (Has-Property -Object $Object -Name $Name) { return [bool]$Object.$Name }
  return $Default
}

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
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

function Test-NoLiveSideEffects {
  param([object]$Payload)
  foreach ($required in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "ec2_started", "generation_executed")) {
    if (-not (Has-Property -Object $Payload -Name $required)) { return $false }
  }
  if (-not [bool]$Payload.local_only) { return $false }
  foreach ($name in @("aws_contacted", "github_api_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated")) {
    if ((Has-Property -Object $Payload -Name $name) -and [bool]$Payload.$name) { return $false }
  }
  return $true
}

function New-RecheckRow {
  param(
    [string]$Name,
    [string]$Path,
    [object]$Payload,
    [string[]]$AcceptedResults,
    [string]$ExpectedDisposition
  )

  $result = if (Has-Property -Object $Payload -Name "result") { [string]$Payload.result } else { "" }
  $sideEffectsPass = Test-NoLiveSideEffects -Payload $Payload
  $resultAccepted = @($AcceptedResults) -contains $result
  return [pscustomobject][ordered]@{
    name = $Name
    evidence = ConvertTo-ProjectRelativePath -Path $Path
    result = $result
    disposition = $(if ($resultAccepted -and $sideEffectsPass) { $ExpectedDisposition } else { "unexpected" })
    result_accepted = $resultAccepted
    no_live_side_effects = $sideEffectsPass
  }
}

function Parse-FailedLaneList {
  param([AllowNull()][object]$Observed)
  $text = [string]$Observed
  if ([string]::IsNullOrWhiteSpace($text)) { return @() }
  if ($text -match "(?i)^\s*all queued lane coverage results pass\s*$") { return @() }
  return @($text -split "[,;\r\n]+" | ForEach-Object { [string]$_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
}

function Test-RuntimeQueueLaneScope {
  param(
    [AllowNull()][object]$RuntimeQueue,
    [Parameter(Mandatory = $true)][string]$SelectedLaneId
  )

  $allowedCoverageFailureNames = @("coverage_result_pass_local_only", "coverage_failed_lane_count_zero", "coverage_queue_lane_results_pass")
  $structuralFailures = New-Object System.Collections.Generic.List[string]
  $failureReasons = New-Object System.Collections.Generic.List[string]

  $scope = [ordered]@{
    selected_lane_id = $SelectedLaneId
    assessment_mode = "unassessed"
    pass = $false
    runtime_queue_result = $null
    runtime_queue_failed_check_count = $null
    local_no_side_effects = $false
    structure_valid = $false
    queue_check_count = 0
    queue_checks_all_pass = $false
    lane_queue_result_count = 0
    lane_queue_results_all_pass = $false
    selected_lane_row_count = 0
    selected_lane_row_pass = $false
    selected_lane_check_count = 0
    selected_lane_checks_all_pass = $false
    coverage_check_count = 0
    coverage_checks_all_pass = $false
    coverage_failed_check_count = 0
    coverage_failed_check_names = @()
    coverage_failed_check_names_allowed = $false
    coverage_queue_lane_results_pass_check_count = 0
    coverage_queue_lane_results_pass_check_failed = $false
    coverage_queue_lane_results_failed_lanes = @()
    coverage_queue_lane_results_failed_lane_count = 0
    coverage_queue_lane_results_excludes_selected_lane = $false
    failed_check_count_accounts_for_coverage_only = $false
    structural_failures = @()
    failure_reasons = @()
  }

  if ($null -eq $RuntimeQueue) {
    [void]$structuralFailures.Add("runtime_queue_missing")
    $scope.structural_failures = @($structuralFailures)
    $scope.failure_reasons = @("structural_failure")
    return [pscustomobject]$scope
  }

  $scope.runtime_queue_result = if (Has-Property -Object $RuntimeQueue -Name "result") { [string]$RuntimeQueue.result } else { $null }
  $scope.local_no_side_effects = Test-NoLiveSideEffects -Payload $RuntimeQueue
  if (-not $scope.local_no_side_effects) {
    [void]$failureReasons.Add("runtime_queue_not_local_only")
  }

  foreach ($required in @("result", "failed_check_count", "local_only", "queue_checks", "lane_queue_results", "coverage_checks")) {
    if (-not (Has-Property -Object $RuntimeQueue -Name $required)) {
      [void]$structuralFailures.Add("missing_$required")
    }
  }
  if ($structuralFailures.Count -gt 0) {
    $scope.structural_failures = @($structuralFailures)
    [void]$failureReasons.Add("structural_failure")
    $scope.failure_reasons = @($failureReasons)
    return [pscustomobject]$scope
  }

  $runtimeFailedCount = $null
  try {
    $runtimeFailedCount = [int]$RuntimeQueue.failed_check_count
  } catch {
    [void]$structuralFailures.Add("failed_check_count_not_int")
  }
  if ($structuralFailures.Count -gt 0) {
    $scope.structural_failures = @($structuralFailures)
    [void]$failureReasons.Add("structural_failure")
    $scope.failure_reasons = @($failureReasons)
    return [pscustomobject]$scope
  }
  $scope.runtime_queue_failed_check_count = $runtimeFailedCount

  $queueChecks = Convert-ToArray -Value $RuntimeQueue.queue_checks
  $laneQueueResults = Convert-ToArray -Value $RuntimeQueue.lane_queue_results
  $coverageChecks = Convert-ToArray -Value $RuntimeQueue.coverage_checks
  $scope.queue_check_count = $queueChecks.Count
  $scope.lane_queue_result_count = $laneQueueResults.Count
  $scope.coverage_check_count = $coverageChecks.Count
  if (
    $RuntimeQueue.queue_checks -is [string] -or
    $RuntimeQueue.lane_queue_results -is [string] -or
    $RuntimeQueue.coverage_checks -is [string] -or
    $queueChecks.Count -eq 0 -or
    $laneQueueResults.Count -eq 0 -or
    $coverageChecks.Count -eq 0
  ) {
    [void]$structuralFailures.Add("check_collections_malformed")
  }
  if ($structuralFailures.Count -gt 0) {
    $scope.structural_failures = @($structuralFailures)
    [void]$failureReasons.Add("structural_failure")
    $scope.failure_reasons = @($failureReasons)
    return [pscustomobject]$scope
  }

  $scope.structure_valid = $true
  $scope.structural_failures = @()

  $queueCheckShapeFailures = @($queueChecks | Where-Object {
    -not (Has-Property -Object $_ -Name "name") -or
    [string]::IsNullOrWhiteSpace([string]$_.name) -or
    -not (Has-Property -Object $_ -Name "result")
  })
  if ($queueCheckShapeFailures.Count -gt 0) {
    $scope.structure_valid = $false
    [void]$structuralFailures.Add("queue_check_shape_invalid")
    [void]$failureReasons.Add("structural_failure")
  }
  $queueCheckFailures = @($queueChecks | Where-Object { -not (Has-Property -Object $_ -Name "result") -or [string]$_.result -ne "pass" })
  $scope.queue_checks_all_pass = ($queueCheckFailures.Count -eq 0)
  if (-not $scope.queue_checks_all_pass) {
    [void]$failureReasons.Add("queue_checks_have_failures")
  }

  $laneQueueFailures = @()
  foreach ($laneRow in @($laneQueueResults)) {
    $laneIdValid = (
      (Has-Property -Object $laneRow -Name "lane_id") -and
      -not [string]::IsNullOrWhiteSpace([string]$laneRow.lane_id)
    )
    $laneChecks = if (Has-Property -Object $laneRow -Name "checks") { Convert-ToArray -Value $laneRow.checks } else { @() }
    $laneCheckShapeFailures = @($laneChecks | Where-Object {
      -not (Has-Property -Object $_ -Name "name") -or
      [string]::IsNullOrWhiteSpace([string]$_.name) -or
      -not (Has-Property -Object $_ -Name "result")
    })
    $laneChecksValid = ($laneChecks.Count -gt 0 -and $laneCheckShapeFailures.Count -eq 0)
    $laneCheckFailures = @($laneChecks | Where-Object { -not (Has-Property -Object $_ -Name "result") -or [string]$_.result -ne "pass" })
    $laneFailedCount = $null
    $laneFailedCountValid = $true
    if (-not (Has-Property -Object $laneRow -Name "failed_check_count")) {
      $laneFailedCountValid = $false
    } else {
      try {
        $laneFailedCount = [int]$laneRow.failed_check_count
      } catch {
        $laneFailedCountValid = $false
      }
    }
    if (
      -not $laneIdValid -or
      -not $laneChecksValid -or
      $laneCheckFailures.Count -gt 0 -or
      -not (Has-Property -Object $laneRow -Name "result") -or
      [string]$laneRow.result -ne "pass" -or
      -not $laneFailedCountValid -or
      $laneFailedCount -ne 0
    ) {
      $laneQueueFailures += $laneRow
    }
  }
  $scope.lane_queue_results_all_pass = ($laneQueueFailures.Count -eq 0)
  if (-not $scope.lane_queue_results_all_pass) {
    [void]$failureReasons.Add("lane_queue_results_have_failures")
  }

  $selectedRows = @($laneQueueResults | Where-Object { (Has-Property -Object $_ -Name "lane_id") -and [string]$_.lane_id -eq $SelectedLaneId })
  $scope.selected_lane_row_count = $selectedRows.Count
  if ($selectedRows.Count -ne 1) {
    [void]$failureReasons.Add("selected_lane_row_count_invalid")
  } else {
    $selectedRow = $selectedRows[0]
    $selectedRowChecks = if (Has-Property -Object $selectedRow -Name "checks") { Convert-ToArray -Value $selectedRow.checks } else { @() }
    $scope.selected_lane_check_count = $selectedRowChecks.Count
    $selectedRowCheckShapeFailures = @($selectedRowChecks | Where-Object {
      -not (Has-Property -Object $_ -Name "name") -or
      [string]::IsNullOrWhiteSpace([string]$_.name) -or
      -not (Has-Property -Object $_ -Name "result")
    })
    $selectedRowCheckFailures = @($selectedRowChecks | Where-Object { -not (Has-Property -Object $_ -Name "result") -or [string]$_.result -ne "pass" })
    $scope.selected_lane_checks_all_pass = (
      $selectedRowChecks.Count -gt 0 -and
      $selectedRowCheckShapeFailures.Count -eq 0 -and
      $selectedRowCheckFailures.Count -eq 0
    )
    $selectedRowFailedCount = $null
    $selectedRowFailedCountValid = $true
    if (-not (Has-Property -Object $selectedRow -Name "failed_check_count")) {
      $selectedRowFailedCountValid = $false
    } else {
      try {
        $selectedRowFailedCount = [int]$selectedRow.failed_check_count
      } catch {
        $selectedRowFailedCountValid = $false
      }
    }
    $scope.selected_lane_row_pass = (
      (Has-Property -Object $selectedRow -Name "result") -and [string]$selectedRow.result -eq "pass" -and
      $selectedRowFailedCountValid -and $selectedRowFailedCount -eq 0
    )
    if (-not $scope.selected_lane_row_pass) {
      [void]$failureReasons.Add("selected_lane_row_failed")
    }
    if (-not $scope.selected_lane_checks_all_pass) {
      [void]$failureReasons.Add("selected_lane_check_failed")
    }
  }

  $coverageCheckShapeFailures = @($coverageChecks | Where-Object {
    -not (Has-Property -Object $_ -Name "name") -or
    [string]::IsNullOrWhiteSpace([string]$_.name) -or
    -not (Has-Property -Object $_ -Name "result")
  })
  if ($coverageCheckShapeFailures.Count -gt 0) {
    $scope.structure_valid = $false
    [void]$structuralFailures.Add("coverage_check_shape_invalid")
    [void]$failureReasons.Add("structural_failure")
  }
  $failedCoverageChecks = @($coverageChecks | Where-Object { -not (Has-Property -Object $_ -Name "result") -or [string]$_.result -ne "pass" })
  $scope.coverage_checks_all_pass = ($failedCoverageChecks.Count -eq 0)
  $scope.coverage_failed_check_count = $failedCoverageChecks.Count
  $scope.coverage_failed_check_names = @($failedCoverageChecks | ForEach-Object { if (Has-Property -Object $_ -Name "name") { [string]$_.name } else { "missing_name" } })
  $scope.coverage_failed_check_names_allowed = (@($scope.coverage_failed_check_names | Where-Object { $allowedCoverageFailureNames -notcontains [string]$_ }).Count -eq 0)
  if (-not $scope.coverage_failed_check_names_allowed) {
    [void]$failureReasons.Add("coverage_failure_name_not_allowed")
  }

  $coverageQueueLaneResultsChecks = @($coverageChecks | Where-Object { (Has-Property -Object $_ -Name "name") -and [string]$_.name -eq "coverage_queue_lane_results_pass" })
  $scope.coverage_queue_lane_results_pass_check_count = $coverageQueueLaneResultsChecks.Count
  if ($coverageQueueLaneResultsChecks.Count -ne 1) {
    [void]$failureReasons.Add("coverage_queue_lane_results_pass_check_count_invalid")
  } else {
    $scope.coverage_queue_lane_results_pass_check_failed = ([string]$coverageQueueLaneResultsChecks[0].result -eq "fail")
    $failedLanes = Parse-FailedLaneList -Observed $coverageQueueLaneResultsChecks[0].observed
    $scope.coverage_queue_lane_results_failed_lanes = @($failedLanes)
    $scope.coverage_queue_lane_results_failed_lane_count = $failedLanes.Count
    $scope.coverage_queue_lane_results_excludes_selected_lane = (@($failedLanes | Where-Object { [string]$_ -eq $SelectedLaneId }).Count -eq 0)
    if (-not $scope.coverage_queue_lane_results_excludes_selected_lane) {
      [void]$failureReasons.Add("selected_lane_listed_in_coverage_failure")
    }
  }

  $scope.failed_check_count_accounts_for_coverage_only = ($runtimeFailedCount -eq $failedCoverageChecks.Count)
  if (-not $scope.failed_check_count_accounts_for_coverage_only) {
    [void]$failureReasons.Add("failed_check_count_not_coverage_only")
  }

  $commonSelectedLaneContract = (
    $scope.structure_valid -and
    $scope.queue_checks_all_pass -and
    $scope.lane_queue_results_all_pass -and
    $scope.selected_lane_row_count -eq 1 -and
    $scope.selected_lane_row_pass -and
    $scope.selected_lane_checks_all_pass -and
    $scope.coverage_queue_lane_results_pass_check_count -eq 1 -and
    $scope.failed_check_count_accounts_for_coverage_only
  )
  $globalPass = (
    [string]$scope.runtime_queue_result -eq "pass_local_only" -and
    $runtimeFailedCount -eq 0 -and
    $commonSelectedLaneContract -and
    $scope.coverage_checks_all_pass -and
    $scope.coverage_queue_lane_results_failed_lane_count -eq 0
  )
  $globalFailLaneScoped = (
    [string]$scope.runtime_queue_result -eq "fail" -and
    $commonSelectedLaneContract -and
    $scope.coverage_failed_check_count -gt 0 -and
    $scope.coverage_failed_check_names_allowed -and
    $scope.coverage_queue_lane_results_pass_check_failed -and
    $scope.coverage_queue_lane_results_failed_lane_count -gt 0 -and
    $scope.coverage_queue_lane_results_excludes_selected_lane
  )

  if ($globalPass) {
    $scope.assessment_mode = "global_pass"
    if ($scope.local_no_side_effects) {
      $scope.pass = $true
    }
  } elseif ($globalFailLaneScoped) {
    $scope.assessment_mode = "global_fail_lane_scoped"
    if ($scope.local_no_side_effects) {
      $scope.pass = $true
    }
  } else {
    $scope.assessment_mode = "global_fail_closed"
    [void]$failureReasons.Add("runtime_queue_result_not_accepted")
  }

  $scope.structural_failures = @($structuralFailures | Select-Object -Unique)
  $scope.failure_reasons = @($failureReasons | Select-Object -Unique)
  return [pscustomobject]$scope
}

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$gitVerificationDir = Join-Path $qaRoot "Git_Verification"
$doneDir = Join-Path $qaRoot "Done_Certifications"
$queueDir = Join-Path $qaRoot "Workflow_Prerequisite_Matching"
$modelDir = Join-Path $qaRoot "Model_Registry"

if ([string]::IsNullOrWhiteSpace($PreEC2HandoffBundleFile)) {
  $PreEC2HandoffBundleFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_TARGET_RUNTIME_PRE_EC2_HANDOFF_BUNDLE_*.json"
}
if ([string]::IsNullOrWhiteSpace($ClosureRollupFile)) {
  $ClosureRollupFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_*.json"
}
if ([string]::IsNullOrWhiteSpace($GitCheckpointGateFile)) {
  $GitCheckpointGateFile = Find-LatestFile -Directory $gitVerificationDir -Filter "W66_GITHUB_CHECKPOINT_DRY_RUN_JSON_GATE_*.json"
}
if ([string]::IsNullOrWhiteSpace($RuntimeUnblockHandoffFile)) {
  $RuntimeUnblockHandoffFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_RUNTIME_UNBLOCK_HANDOFF_sdxl_realvisxl_inpaint_detail_lane_*.json"
}
if ([string]::IsNullOrWhiteSpace($LocalSupportCertificationFile)) {
  $LocalSupportCertificationFile = Find-LatestFile -Directory $doneDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_LOCAL_SUPPORT_CERTIFICATION_*.json"
}
if ([string]::IsNullOrWhiteSpace($RuntimeLaneQueueFile)) {
  $RuntimeLaneQueueFile = Find-LatestFile -Directory $queueDir -Filter "W66_RUNTIME_LANE_QUEUE_*.json"
}
if ([string]::IsNullOrWhiteSpace($ModelRegistryCoverageFile)) {
  $ModelRegistryCoverageFile = Find-LatestFile -Directory $modelDir -Filter "W66_MODEL_REGISTRY_COVERAGE_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_TARGET_RUNTIME_LOCAL_RECHECK_LEDGER_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$paths = [ordered]@{
  pre_ec2_handoff_bundle = Resolve-ProjectPath -Path $PreEC2HandoffBundleFile
  closure_rollup = Resolve-ProjectPath -Path $ClosureRollupFile
  git_checkpoint_gate = Resolve-ProjectPath -Path $GitCheckpointGateFile
  runtime_unblock_handoff = Resolve-ProjectPath -Path $RuntimeUnblockHandoffFile
  local_support_certification = Resolve-ProjectPath -Path $LocalSupportCertificationFile
  runtime_lane_queue = Resolve-ProjectPath -Path $RuntimeLaneQueueFile
  model_registry_coverage = Resolve-ProjectPath -Path $ModelRegistryCoverageFile
}
foreach ($entry in $paths.GetEnumerator()) {
  if ([string]::IsNullOrWhiteSpace([string]$entry.Value) -or -not (Test-Path -LiteralPath $entry.Value -PathType Leaf)) {
    throw "Required evidence missing: $($entry.Key)"
  }
}

$handoffBundle = Read-JsonFile -Path $paths.pre_ec2_handoff_bundle
$closure = Read-JsonFile -Path $paths.closure_rollup
$gitGate = Read-JsonFile -Path $paths.git_checkpoint_gate
$runtimeHandoff = Read-JsonFile -Path $paths.runtime_unblock_handoff
$localSupport = Read-JsonFile -Path $paths.local_support_certification
$runtimeQueue = Read-JsonFile -Path $paths.runtime_lane_queue
$modelCoverage = Read-JsonFile -Path $paths.model_registry_coverage

$selectedLaneId = "sdxl_realvisxl_inpaint_detail_lane"
$laneId = [string]$handoffBundle.lane_id
$workOrderId = [string]$handoffBundle.selected_work_order_id
$handoffMaterializedBundle = (
  (Get-BoolValue -Object $handoffBundle -Name "selected_deploy_bundle_live_commands_materialized") -and
  (Get-BoolValue -Object $handoffBundle -Name "ready_for_s3_publish_now_local_dry_run") -and
  -not (Get-BoolValue -Object $handoffBundle -Name "selected_deploy_bundle_s3_upload_execute_allowed")
)

$runtimeQueueLaneScope = Test-RuntimeQueueLaneScope -RuntimeQueue $runtimeQueue -SelectedLaneId $selectedLaneId
$runtimeLaneQueueRow = New-RecheckRow -Name "runtime_lane_queue_recheck" -Path $paths.runtime_lane_queue -Payload $runtimeQueue -AcceptedResults @("pass_local_only", "fail") -ExpectedDisposition "pass_local_recheck"
$runtimeLaneQueueRow.result_accepted = [bool]$runtimeQueueLaneScope.pass
$runtimeLaneQueueRow.disposition = $(if ([bool]$runtimeLaneQueueRow.result_accepted -and [bool]$runtimeLaneQueueRow.no_live_side_effects) { "pass_local_recheck" } else { "unexpected" })
$runtimeLaneQueueRow | Add-Member -NotePropertyName "runtime_queue_lane_scope" -NotePropertyValue $runtimeQueueLaneScope

$rows = @(
  (New-RecheckRow -Name "closure_rollup_recheck" -Path $paths.closure_rollup -Payload $closure -AcceptedResults @("pass_local_only_final_certification_closure_rollup") -ExpectedDisposition "pass_local_recheck"),
  (New-RecheckRow -Name "git_checkpoint_recheck" -Path $paths.git_checkpoint_gate -Payload $gitGate -AcceptedResults @("blocked_git_checkpoint_dirty_worktree", "pass_git_checkpoint_ready") -ExpectedDisposition $(if ([string]$gitGate.result -eq "pass_git_checkpoint_ready") { "pass_local_recheck" } else { "blocked_expected_dirty_git" })),
  (New-RecheckRow -Name "runtime_unblock_handoff_recheck" -Path $paths.runtime_unblock_handoff -Payload $runtimeHandoff -AcceptedResults @("handoff_failed_local_readiness", "handoff_git_checkpoint_blocked", "handoff_ready_for_ec2_static_proof", "handoff_ready_runtime_blocked_auth", "handoff_auth_ready_lane_not_ready", "handoff_lane_queue_order_blocked", "handoff_model_registry_blocked") -ExpectedDisposition $(if ([string]$runtimeHandoff.result -eq "handoff_failed_local_readiness") { "blocked_expected_missing_project_readiness" } elseif ([string]$runtimeHandoff.result -eq "handoff_git_checkpoint_blocked") { "blocked_expected_dirty_git" } else { "pass_or_blocked_local_handoff" })),
  (New-RecheckRow -Name "active_runtime_queue_local_support_recheck" -Path $paths.local_support_certification -Payload $localSupport -AcceptedResults @("pass_local_active_runtime_queue_support_certification") -ExpectedDisposition "pass_local_recheck"),
  $runtimeLaneQueueRow,
  (New-RecheckRow -Name "model_registry_coverage_recheck" -Path $paths.model_registry_coverage -Payload $modelCoverage -AcceptedResults @("pass_local_only") -ExpectedDisposition "pass_local_recheck")
)

$unexpectedRows = @($rows | Where-Object { [string]$_.disposition -eq "unexpected" })
$passRows = @($rows | Where-Object { [string]$_.disposition -eq "pass_local_recheck" })
$expectedBlockedRows = @($rows | Where-Object { [string]$_.disposition -like "blocked_expected*" })
$allRowsSideEffectFree = (@($rows | Where-Object { -not [bool]$_.no_live_side_effects }).Count -eq 0)
$allRowsAccepted = (@($rows | Where-Object { -not [bool]$_.result_accepted }).Count -eq 0)

$runtimeHandoffProjectReadiness = $null
if ((Has-Property -Object $runtimeHandoff -Name "gate_summary") -and (Has-Property -Object $runtimeHandoff.gate_summary -Name "project_readiness")) {
  $runtimeHandoffProjectReadiness = $runtimeHandoff.gate_summary.project_readiness
}

$gitGatePasses = (
  [string]$gitGate.result -eq "pass_git_checkpoint_ready" -and
  [bool]$gitGate.clean_worktree -and
  [bool]$gitGate.local_matches_origin -and
  -not [bool]$gitGate.commit_attempted -and
  -not [bool]$gitGate.push_attempted
)
$gitGateDirtyBlocker = (
  [string]$gitGate.result -eq "blocked_git_checkpoint_dirty_worktree" -and
  -not [bool]$gitGate.clean_worktree -and
  -not [bool]$gitGate.commit_attempted -and
  -not [bool]$gitGate.push_attempted
)
$expectedOpenWorkOrderCount = [int]$closure.source_work_order_count - [int]$closure.closed_work_order_count

$exactBlockers = New-Object System.Collections.Generic.List[string]
if ($gitGateDirtyBlocker) {
  [void]$exactBlockers.Add("git_checkpoint_gate_not_clean_for_ec2_execute")
}
if ([string]$runtimeHandoff.failure_category -eq "local_git_worktree_dirty" -and -not $handoffMaterializedBundle) {
  [void]$exactBlockers.Add("deploy_bundle_source_git_dirty_rebuild_required_before_ec2")
}
if ([string]$runtimeHandoff.result -eq "handoff_ready_runtime_blocked_auth") {
  $authBlocker = if (![string]::IsNullOrWhiteSpace([string]$runtimeHandoff.failure_category)) { "aws_auth_$([string]$runtimeHandoff.failure_category)" } else { "aws_auth_blocked" }
  [void]$exactBlockers.Add($authBlocker)
}
if ($null -eq $runtimeHandoffProjectReadiness -or [string]$runtimeHandoffProjectReadiness.result -eq "missing_project_readiness") {
  [void]$exactBlockers.Add("runtime_handoff_project_readiness_missing")
} elseif ([string]$runtimeHandoffProjectReadiness.failure_category -and [string]$runtimeHandoffProjectReadiness.result -ne "pass_local_ready_for_ec2_static_proof") {
  [void]$exactBlockers.Add("project_readiness_$([string]$runtimeHandoffProjectReadiness.failure_category)")
}
if ((Has-Property -Object $runtimeHandoff -Name "gate_summary") -and
    (Has-Property -Object $runtimeHandoff.gate_summary -Name "workflow_smoke") -and
    [string]$runtimeHandoff.gate_summary.workflow_smoke.result -eq "missing_workflow_smoke") {
  [void]$exactBlockers.Add("target_runtime_proof_evidence_missing")
}

$checks = @(
  (New-Check -Name "pre_ec2_handoff_bundle_still_fail_closed" -Passed ([string]$handoffBundle.result -eq "pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked" -and $laneId -eq $selectedLaneId -and -not [bool]$handoffBundle.target_runtime_launch_allowed -and -not [bool]$handoffBundle.execute_allowed_now) -Observed ([ordered]@{ result = $handoffBundle.result; lane_id = $laneId; launch_allowed = $handoffBundle.target_runtime_launch_allowed; execute_allowed_now = $handoffBundle.execute_allowed_now }) -Expected "selected inpaint pre-EC2 handoff bundle remains fail-closed"),
  (New-Check -Name "materialized_bundle_commands_preserved_when_available" -Passed ((-not $handoffMaterializedBundle) -or (-not [string]::IsNullOrWhiteSpace([string]$handoffBundle.selected_deploy_bundle_s3_bundle_uri) -and -not [string]::IsNullOrWhiteSpace([string]$handoffBundle.selected_deploy_bundle_s3_bundle_sha256))) -Observed ([ordered]@{ materialized = $handoffMaterializedBundle; uri = [string]$handoffBundle.selected_deploy_bundle_s3_bundle_uri; sha = [string]$handoffBundle.selected_deploy_bundle_s3_bundle_sha256; s3_upload_execute_allowed = $handoffBundle.selected_deploy_bundle_s3_upload_execute_allowed }) -Expected "materialized selected bundle evidence carries URI/SHA while upload execute remains blocked"),
  (New-Check -Name "six_recheck_rows_accounted" -Passed (@($rows).Count -eq 6 -and $allRowsAccepted -and $allRowsSideEffectFree -and $unexpectedRows.Count -eq 0) -Observed ([ordered]@{ row_count = @($rows).Count; accepted = $allRowsAccepted; side_effect_free = $allRowsSideEffectFree; unexpected_count = $unexpectedRows.Count }) -Expected "six accepted local-only recheck rows with no live side effects"),
  (New-Check -Name "closure_rollup_keeps_final_certification_blocked" -Passed ([int]$closure.closed_work_order_count -eq 2 -and [int]$closure.open_work_order_count -eq $expectedOpenWorkOrderCount -and [int]$closure.remaining_target_runtime_count -eq 8 -and [int]$closure.remaining_final_review_count -eq 7 -and -not [bool]$closure.full_project_certification_allowed) -Observed ([ordered]@{ source_work_orders = $closure.source_work_order_count; closed = $closure.closed_work_order_count; open = $closure.open_work_order_count; expected_open = $expectedOpenWorkOrderCount; target_runtime = $closure.remaining_target_runtime_count; final_review = $closure.remaining_final_review_count; full_project_certification_allowed = $closure.full_project_certification_allowed }) -Expected "closure rollup keeps two local review closures, all target-runtime/final-review blockers open, and full certification blocked"),
  (New-Check -Name "git_checkpoint_dry_run_accounted_without_commit_or_push" -Passed ($gitGatePasses -or $gitGateDirtyBlocker) -Observed ([ordered]@{ result = $gitGate.result; clean_worktree = $gitGate.clean_worktree; local_matches_origin = $gitGate.local_matches_origin; porcelain_count = $gitGate.porcelain_count; commit_attempted = $gitGate.commit_attempted; push_attempted = $gitGate.push_attempted; passes_for_ec2_execute = $gitGatePasses; dirty_blocker = $gitGateDirtyBlocker }) -Expected "clean/synced pass gate or dirty Git blocker, always with no commit or push"),
  (New-Check -Name "runtime_unblock_handoff_records_expected_blocker" -Passed ([string]$runtimeHandoff.lane_id -eq $laneId -and (@("handoff_failed_local_readiness", "handoff_git_checkpoint_blocked", "handoff_ready_runtime_blocked_auth", "handoff_auth_ready_lane_not_ready", "handoff_lane_queue_order_blocked", "handoff_model_registry_blocked", "handoff_ready_for_ec2_static_proof") -contains [string]$runtimeHandoff.result) -and $null -ne $runtimeHandoffProjectReadiness -and (@("missing_project_readiness", "pass_local_ready_runtime_blocked", "pass_local_ready_for_ec2_static_proof") -contains [string]$runtimeHandoffProjectReadiness.result)) -Observed ([ordered]@{ result = $runtimeHandoff.result; failure_category = $runtimeHandoff.failure_category; project_readiness = $(if ($null -ne $runtimeHandoffProjectReadiness) { $runtimeHandoffProjectReadiness.result } else { $null }) }) -Expected "selected inpaint runtime handoff fail-closes on an expected local blocker or remains ready for the next gated runtime step"),
  (New-Check -Name "local_support_queue_and_model_rechecks_pass" -Passed ([string]$localSupport.result -eq "pass_local_active_runtime_queue_support_certification" -and [int]$localSupport.lane_count -eq 9 -and [bool]$runtimeQueueLaneScope.pass -and [string]$modelCoverage.result -eq "pass_local_only" -and [int]$modelCoverage.failed_check_count -eq 0) -Observed ([ordered]@{ local_support = $localSupport.result; lane_count = $localSupport.lane_count; runtime_queue = $runtimeQueue.result; runtime_queue_failed = $runtimeQueue.failed_check_count; runtime_queue_lane_scope_pass = $runtimeQueueLaneScope.pass; runtime_queue_lane_scope_mode = $runtimeQueueLaneScope.assessment_mode; runtime_queue_lane_scope_failures = @($runtimeQueueLaneScope.failure_reasons); model_coverage = $modelCoverage.result; model_coverage_failed = $modelCoverage.failed_check_count }) -Expected "local support passes, runtime queue is accepted by selected-lane fail-closed scope, and model registry recheck passes locally")
)
$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })

$result = if ($failedChecks.Count -eq 0) {
  "pass_local_only_selected_target_runtime_local_rechecks_accounted_ec2_blocked"
} else {
  "fail_selected_target_runtime_local_recheck_ledger"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_target_runtime_local_recheck_ledger"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  lane_id = $laneId
  selected_work_order_id = $workOrderId
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
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
  full_project_certification_allowed = $false
  target_runtime_launch_allowed = $false
  execute_allowed_now = $false
  pre_ec2_handoff_bundle = ConvertTo-ProjectRelativePath -Path $paths.pre_ec2_handoff_bundle
  ready_for_s3_publish_now_local_dry_run = [bool]$handoffBundle.ready_for_s3_publish_now_local_dry_run
  selected_deploy_bundle_live_commands_materialized = $handoffMaterializedBundle
  selected_deploy_bundle_s3_bundle_uri = [string]$handoffBundle.selected_deploy_bundle_s3_bundle_uri
  selected_deploy_bundle_s3_bundle_sha256 = [string]$handoffBundle.selected_deploy_bundle_s3_bundle_sha256
  runtime_queue_lane_scope = $runtimeQueueLaneScope
  recheck_rows = @($rows)
  pass_recheck_count = $passRows.Count
  expected_blocked_recheck_count = $expectedBlockedRows.Count
  unexpected_recheck_count = $unexpectedRows.Count
  exact_blockers = @($exactBlockers)
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  ledger_boundary = "Local selected target-runtime recheck ledger only. This accounts for dry-run/local evidence and expected blockers; it does not authorize live upload, S3 publish with Execute, marker write, EC2 start, prompt post, generation, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, or Wave71+ activation."
  next_action = $(if ($handoffMaterializedBundle) { "Keep EC2 stopped. The selected deploy bundle URI/SHA are materialized for future live proof, but Git/live intent/S3 Execute/input/model publish/install/static-proof gates remain blocked." } else { "Keep EC2 stopped. Resolve or intentionally checkpoint the dirty Git state, then rebuild/revalidate the deploy bundle from a clean checkpoint before any explicit live target-runtime window." })
}

$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$rowLines = foreach ($row in $rows) {
  "- $($row.name): $($row.disposition) (`$($row.result)`)"
}
$checkLines = foreach ($check in $checks) {
  "- $($check.name): $($check.result)"
}
$markdown = @"
# Selected Target Runtime Local Recheck Ledger

- created_at: $($record.created_at)
- result: $result
- lane_id: $laneId
- selected_work_order_id: $workOrderId
- pass_recheck_count: $($record.pass_recheck_count)
- expected_blocked_recheck_count: $($record.expected_blocked_recheck_count)
- unexpected_recheck_count: $($record.unexpected_recheck_count)
- target_runtime_launch_allowed: false
- execute_allowed_now: false
- ready_for_s3_publish_now_local_dry_run: $($record.ready_for_s3_publish_now_local_dry_run)
- selected_deploy_bundle_live_commands_materialized: $($record.selected_deploy_bundle_live_commands_materialized)

## Rechecks

$($rowLines -join "`n")

## Checks

$($checkLines -join "`n")

## Boundary

$($record.ledger_boundary)

## Evidence

- $($record.pre_ec2_handoff_bundle)
$(@($rows | ForEach-Object { "- $($_.evidence)" }) -join "`n")
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($result -like "fail_*") { exit 2 }
exit 0
