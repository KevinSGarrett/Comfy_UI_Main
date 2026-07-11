param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Write-Utf8 {
  param([string]$Path, [string]$Value)
  [System.IO.Directory]::CreateDirectory((Split-Path -Path $Path -Parent)) | Out-Null
  [System.IO.File]::WriteAllText($Path, $Value, (New-Object System.Text.UTF8Encoding($false)))
}

function Write-Json {
  param([string]$Path, [object]$Value)
  Write-Utf8 -Path $Path -Value (($Value | ConvertTo-Json -Depth 40) + [Environment]::NewLine)
}

function Copy-Object {
  param([object]$Value)
  return (($Value | ConvertTo-Json -Depth 40) | ConvertFrom-Json)
}

function New-LaneResult {
  param([string]$LaneId, [string]$Result = "pass", [int]$FailedCheckCount = 0)
  return [ordered]@{
    order = 1
    lane_id = $LaneId
    role = "fixture_lane"
    checks = @(
      [ordered]@{ name = "lane_is_authored"; result = "pass"; observed = "ok"; expected = "ok" },
      [ordered]@{ name = "workflow_path_matches_lane"; result = "pass"; observed = "ok"; expected = "ok" }
    )
    failed_check_count = $FailedCheckCount
    result = $Result
  }
}

function New-RuntimeQueuePayload {
  param([bool]$GlobalPass, [string]$CoverageObserved = "flux1_dev_primary_base")

  $queueChecks = @(
    [ordered]@{ name = "queue_json_valid"; result = "pass"; observed = "valid"; expected = "valid JSON" },
    [ordered]@{ name = "queue_lanes_present"; result = "pass"; observed = "2"; expected = "one or more queued lanes" }
  )
  $laneResults = @(
    (New-LaneResult -LaneId "sdxl_realvisxl_inpaint_detail_lane" -Result "pass" -FailedCheckCount 0),
    (New-LaneResult -LaneId "flux1_dev_primary_base" -Result "pass" -FailedCheckCount 0)
  )
  if ($GlobalPass) {
    $coverageChecks = @(
      [ordered]@{ name = "coverage_result_pass_local_only"; result = "pass"; observed = "pass_local_only"; expected = "result=pass_local_only" },
      [ordered]@{ name = "coverage_failed_lane_count_zero"; result = "pass"; observed = "0"; expected = "failed_lane_count=0" },
      [ordered]@{ name = "coverage_queue_lane_results_pass"; result = "pass"; observed = "all queued lane coverage results pass"; expected = "every queued lane has coverage result=pass" }
    )
    $result = "pass_local_only"
    $failedCheckCount = 0
  } else {
    $coverageChecks = @(
      [ordered]@{ name = "coverage_result_pass_local_only"; result = "fail"; observed = "fail"; expected = "result=pass_local_only" },
      [ordered]@{ name = "coverage_failed_lane_count_zero"; result = "fail"; observed = "1"; expected = "failed_lane_count=0" },
      [ordered]@{ name = "coverage_queue_lane_results_pass"; result = "fail"; observed = $CoverageObserved; expected = "every queued lane has coverage result=pass" }
    )
    $result = "fail"
    $failedCheckCount = 3
  }
  return [ordered]@{
    result = $result
    local_only = $true
    aws_contacted = $false
    github_api_contacted = $false
    civitai_contacted = $false
    s3_contacted = $false
    comfyui_contacted = $false
    ec2_started = $false
    generation_executed = $false
    queue_checks = $queueChecks
    lane_queue_results = $laneResults
    coverage_checks = $coverageChecks
    failed_check_count = $failedCheckCount
  }
}

function New-BaseFixturePayload {
  $payload = [ordered]@{
    pre_ec2_handoff_bundle = [ordered]@{
      result = "pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked"
      lane_id = "sdxl_realvisxl_inpaint_detail_lane"
      selected_work_order_id = "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF"
      target_runtime_launch_allowed = $false
      execute_allowed_now = $false
      selected_deploy_bundle_live_commands_materialized = $false
      ready_for_s3_publish_now_local_dry_run = $false
      selected_deploy_bundle_s3_upload_execute_allowed = $false
      selected_deploy_bundle_s3_bundle_uri = ""
      selected_deploy_bundle_s3_bundle_sha256 = ""
      local_only = $true
      ec2_started = $false
      generation_executed = $false
    }
    closure_rollup = [ordered]@{
      result = "pass_local_only_final_certification_closure_rollup"
      source_work_order_count = 10
      closed_work_order_count = 2
      open_work_order_count = 8
      remaining_target_runtime_count = 8
      remaining_final_review_count = 7
      full_project_certification_allowed = $false
      local_only = $true
      aws_contacted = $false
      github_api_contacted = $false
      civitai_contacted = $false
      ec2_started = $false
      generation_executed = $false
    }
    git_checkpoint_gate = [ordered]@{
      result = "pass_git_checkpoint_ready"
      clean_worktree = $true
      local_matches_origin = $true
      commit_attempted = $false
      push_attempted = $false
      local_only = $true
      aws_contacted = $false
      github_api_contacted = $false
      civitai_contacted = $false
      ec2_started = $false
      generation_executed = $false
    }
    runtime_unblock_handoff = [ordered]@{
      result = "handoff_model_registry_blocked"
      lane_id = "sdxl_realvisxl_inpaint_detail_lane"
      failure_category = "selected_lane_model_registry_pending"
      gate_summary = [ordered]@{
        project_readiness = [ordered]@{
          result = "pass_local_ready_runtime_blocked"
        }
      }
      local_only = $true
      aws_contacted = $false
      github_api_contacted = $false
      civitai_contacted = $false
      ec2_started = $false
      generation_executed = $false
    }
    local_support_certification = [ordered]@{
      result = "pass_local_active_runtime_queue_support_certification"
      lane_count = 9
      local_only = $true
      aws_contacted = $false
      github_api_contacted = $false
      civitai_contacted = $false
      ec2_started = $false
      generation_executed = $false
    }
    runtime_lane_queue = (New-RuntimeQueuePayload -GlobalPass $false)
    model_registry_coverage = [ordered]@{
      result = "pass_local_only"
      failed_check_count = 0
      local_only = $true
      aws_contacted = $false
      github_api_contacted = $false
      civitai_contacted = $false
      ec2_started = $false
      generation_executed = $false
    }
  }
  return $payload
}

$ledgerScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\New-SelectedTargetRuntimeLocalRecheckLedger.ps1"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("selected_runtime_recheck_lane_scope_regression_" + [guid]::NewGuid().ToString("N"))
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null

function Invoke-RegressionCase {
  param(
    [string]$Name,
    [scriptblock]$MutatePayload,
    [bool]$ExpectedPass,
    [string]$ExpectedMode = "",
    [string[]]$ExpectedCoverageFailedLanes = @(),
    [ValidateSet("", "true", "false")][string]$ExpectedLaneScopePass = ""
  )

  $caseRoot = Join-Path $tempRoot $Name
  [System.IO.Directory]::CreateDirectory($caseRoot) | Out-Null
  $payload = Copy-Object -Value (New-BaseFixturePayload)
  & $MutatePayload $payload

  $handoffPath = Join-Path $caseRoot "handoff.json"
  $closurePath = Join-Path $caseRoot "closure.json"
  $gitPath = Join-Path $caseRoot "git.json"
  $runtimeHandoffPath = Join-Path $caseRoot "runtime_handoff.json"
  $supportPath = Join-Path $caseRoot "local_support.json"
  $runtimeQueuePath = Join-Path $caseRoot "runtime_queue.json"
  $modelPath = Join-Path $caseRoot "model_coverage.json"
  $ledgerOut = Join-Path $caseRoot "ledger.json"

  Write-Json -Path $handoffPath -Value $payload.pre_ec2_handoff_bundle
  Write-Json -Path $closurePath -Value $payload.closure_rollup
  Write-Json -Path $gitPath -Value $payload.git_checkpoint_gate
  Write-Json -Path $runtimeHandoffPath -Value $payload.runtime_unblock_handoff
  Write-Json -Path $supportPath -Value $payload.local_support_certification
  Write-Json -Path $runtimeQueuePath -Value $payload.runtime_lane_queue
  Write-Json -Path $modelPath -Value $payload.model_registry_coverage

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ledgerScript `
    -ProjectRoot $ProjectRoot `
    -PreEC2HandoffBundleFile $handoffPath `
    -ClosureRollupFile $closurePath `
    -GitCheckpointGateFile $gitPath `
    -RuntimeUnblockHandoffFile $runtimeHandoffPath `
    -LocalSupportCertificationFile $supportPath `
    -RuntimeLaneQueueFile $runtimeQueuePath `
    -ModelRegistryCoverageFile $modelPath `
    -OutFile $ledgerOut 2>&1
  $exitCode = $LASTEXITCODE
  $parsed = $null
  if (Test-Path -LiteralPath $ledgerOut) {
    $parsed = Get-Content -LiteralPath $ledgerOut -Raw | ConvertFrom-Json
  }

  $laneScopePass = $null
  $laneScopeMode = $null
  $actualCoverageFailedLanes = @()
  if ($null -ne $parsed -and $null -ne $parsed.runtime_queue_lane_scope) {
    if ($parsed.runtime_queue_lane_scope.PSObject.Properties["pass"]) {
      $laneScopePass = [bool]$parsed.runtime_queue_lane_scope.pass
    }
    $laneScopeMode = [string]$parsed.runtime_queue_lane_scope.assessment_mode
    $actualCoverageFailedLanes = @($parsed.runtime_queue_lane_scope.coverage_queue_lane_results_failed_lanes | ForEach-Object { [string]$_ } | Sort-Object)
  }
  $expectedFailedLanes = @($ExpectedCoverageFailedLanes | ForEach-Object { [string]$_ } | Sort-Object)
  $failedLaneSetMatches = (
    $actualCoverageFailedLanes.Count -eq $expectedFailedLanes.Count -and
    @(Compare-Object -ReferenceObject $expectedFailedLanes -DifferenceObject $actualCoverageFailedLanes).Count -eq 0
  )
  $modeMatches = ([string]::IsNullOrWhiteSpace($ExpectedMode) -or $laneScopeMode -eq $ExpectedMode)
  $actualPass = (
    $exitCode -eq 0 -and
    $null -ne $parsed -and
    [string]$parsed.result -like "pass_*" -and
    $laneScopePass -eq $true -and
    $modeMatches -and
    $failedLaneSetMatches
  )
  $structuredFail = (
    $exitCode -eq 2 -and
    $null -ne $parsed -and
    [string]$parsed.result -eq "fail_selected_target_runtime_local_recheck_ledger" -and
    $null -ne $parsed.runtime_queue_lane_scope
  )
  $effectiveExpectedLaneScope = if ([string]::IsNullOrWhiteSpace($ExpectedLaneScopePass)) {
    if ($ExpectedPass) { "true" } else { "false" }
  } else {
    $ExpectedLaneScopePass
  }
  $laneScopeExpectationMatches = (
    ($effectiveExpectedLaneScope -eq "true" -and $laneScopePass -eq $true) -or
    ($effectiveExpectedLaneScope -eq "false" -and $laneScopePass -eq $false)
  )
  $contractPass = $(if ($ExpectedPass) { $actualPass -and $laneScopeExpectationMatches } else { $structuredFail -and $laneScopeExpectationMatches })
  $outputText = ($output | ForEach-Object { $_.ToString() }) -join "`n"
  if ($outputText.Length -gt 2000) {
    $outputText = $outputText.Substring($outputText.Length - 2000)
  }

  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($contractPass) { "pass" } else { "fail" })
    expected_pass = $ExpectedPass
    actual_pass = $actualPass
    structured_fail = $structuredFail
    exit_code = $exitCode
    ledger_result = $(if ($null -ne $parsed) { [string]$parsed.result } else { $null })
    runtime_queue_lane_scope_pass = $laneScopePass
    expected_runtime_queue_lane_scope_pass = $effectiveExpectedLaneScope
    runtime_queue_lane_scope_expectation_matches = $laneScopeExpectationMatches
    runtime_queue_lane_scope_mode = $laneScopeMode
    expected_runtime_queue_lane_scope_mode = $ExpectedMode
    coverage_failed_lanes = @($actualCoverageFailedLanes)
    expected_coverage_failed_lanes = @($expectedFailedLanes)
    coverage_failed_lane_set_matches = $failedLaneSetMatches
    runtime_queue_lane_scope_failures = $(if ($null -ne $parsed -and $null -ne $parsed.runtime_queue_lane_scope) { @($parsed.runtime_queue_lane_scope.failure_reasons) } else { @() })
    output_tail = $outputText
  }
}

$tests = @()
$tests += Invoke-RegressionCase -Name "global_pass_passes" -ExpectedPass $true -ExpectedMode "global_pass" -ExpectedCoverageFailedLanes @() -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue = New-RuntimeQueuePayload -GlobalPass $true
}
$tests += Invoke-RegressionCase -Name "flux_only_coverage_failure_passes" -ExpectedPass $true -ExpectedMode "global_fail_lane_scoped" -ExpectedCoverageFailedLanes @("flux1_dev_primary_base") -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue = New-RuntimeQueuePayload -GlobalPass $false -CoverageObserved "flux1_dev_primary_base"
}
$tests += Invoke-RegressionCase -Name "global_pass_selected_lane_failure_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue = New-RuntimeQueuePayload -GlobalPass $true
  $selectedLane = @($payload.runtime_lane_queue.lane_queue_results | Where-Object { [string]$_.lane_id -eq "sdxl_realvisxl_inpaint_detail_lane" } | Select-Object -First 1)
  if ($selectedLane.Count -eq 1) {
    $selectedLane[0].result = "fail"
    $selectedLane[0].failed_check_count = 1
    $selectedLane[0].checks[0].result = "fail"
  }
}
$tests += Invoke-RegressionCase -Name "global_pass_empty_selected_lane_checks_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue = New-RuntimeQueuePayload -GlobalPass $true
  $selectedLane = @($payload.runtime_lane_queue.lane_queue_results | Where-Object { [string]$_.lane_id -eq "sdxl_realvisxl_inpaint_detail_lane" } | Select-Object -First 1)
  if ($selectedLane.Count -eq 1) {
    $selectedLane[0].checks = @()
  }
}
$tests += Invoke-RegressionCase -Name "selected_lane_failure_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $selectedLane = @($payload.runtime_lane_queue.lane_queue_results | Where-Object { [string]$_.lane_id -eq "sdxl_realvisxl_inpaint_detail_lane" } | Select-Object -First 1)
  if ($selectedLane.Count -eq 1) {
    $selectedLane[0].result = "fail"
    $selectedLane[0].failed_check_count = 1
    $selectedLane[0].checks[0].result = "fail"
  }
}
$tests += Invoke-RegressionCase -Name "selected_lane_named_in_coverage_failure_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $coverageCheck = @($payload.runtime_lane_queue.coverage_checks | Where-Object { [string]$_.name -eq "coverage_queue_lane_results_pass" } | Select-Object -First 1)
  if ($coverageCheck.Count -eq 1) {
    $coverageCheck[0].observed = "sdxl_realvisxl_inpaint_detail_lane, flux1_dev_primary_base"
  }
}
$tests += Invoke-RegressionCase -Name "queue_structural_failure_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue.PSObject.Properties.Remove("lane_queue_results")
}
$tests += Invoke-RegressionCase -Name "unaccounted_failed_check_count_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue.failed_check_count = 4
}
$tests += Invoke-RegressionCase -Name "global_fail_without_failed_coverage_check_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue.result = "fail"
  $payload.runtime_lane_queue.failed_check_count = 0
  foreach ($check in @($payload.runtime_lane_queue.coverage_checks)) {
    $check.result = "pass"
  }
  $coverageLaneCheck = @($payload.runtime_lane_queue.coverage_checks | Where-Object { [string]$_.name -eq "coverage_queue_lane_results_pass" } | Select-Object -First 1)
  if ($coverageLaneCheck.Count -eq 1) {
    $coverageLaneCheck[0].observed = "all queued lane coverage results pass"
  }
}
$tests += Invoke-RegressionCase -Name "live_side_effect_flag_fails" -ExpectedPass $false -MutatePayload {
  param($payload)
  $payload.runtime_lane_queue.ec2_started = $true
}
$tests += Invoke-RegressionCase -Name "missing_required_side_effect_field_fails" -ExpectedPass $false -ExpectedLaneScopePass "true" -MutatePayload {
  param($payload)
  $payload.model_registry_coverage.PSObject.Properties.Remove("aws_contacted")
}

$failedTests = @($tests | Where-Object { [string]$_.result -ne "pass" })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_target_runtime_local_recheck_ledger_regression"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failedTests.Count -eq 0) { "pass_local_only" } else { "fail" })
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  test_count = @($tests).Count
  passing_test_count = @($tests | Where-Object { [string]$_.result -eq "pass" }).Count
  failed_test_count = @($failedTests).Count
  tests = @($tests)
  boundary = "Disposable local fixtures only. No canonical evidence mutation, no live upload, no EC2 start, and no generation."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_SELECTED_TARGET_RUNTIME_LOCAL_RECHECK_LEDGER_REGRESSION_$stamp.json"
} elseif (-not [System.IO.Path]::IsPathRooted($OutFile)) {
  $OutFile = Join-Path $ProjectRoot $OutFile
}

Write-Json -Path $OutFile -Value $record
Remove-Item -LiteralPath $tempRoot -Recurse -Force
$record | ConvertTo-Json -Depth 40
if ($failedTests.Count -gt 0) { exit 1 }
exit 0
