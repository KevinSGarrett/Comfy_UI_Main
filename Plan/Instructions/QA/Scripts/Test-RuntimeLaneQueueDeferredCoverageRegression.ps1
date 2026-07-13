<#
.SYNOPSIS
Exercises fail-closed runtime queue validation around explicitly deferred coverage.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"

$validatorPath = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-RuntimeLaneQueue.ps1"
$queuePath = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json"
$coveragePath = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W66_AUTHORED_LANE_EVIDENCE_COVERAGE_POST_FLUX1_ASSET_AUTHORITY_20260710T223000-0500.json"
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$runRoot = Join-Path $ProjectRoot "runtime_artifacts\regression_temp\runtime_lane_queue_deferred_coverage_$stamp"
$normalLaneId = "sdxl_realvisxl_controlnet_normal_lane"
$fluxLaneId = "flux1_dev_primary_base"
$deferredStatus = "existing_external_model_hash_verified_license_and_live_runtime_proof_pending"
$enginePath = (Get-Process -Id $PID).Path

$null = New-Item -ItemType Directory -Force -Path $runRoot

function Read-JsonClone {
  param([string]$Path)
  return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
}

function Write-JsonFile {
  param(
    [string]$Path,
    [object]$Payload
  )
  [System.IO.File]::WriteAllText($Path, ($Payload | ConvertTo-Json -Depth 40), (New-Object System.Text.UTF8Encoding($false)))
}

function Get-FailedCheckNames {
  param([object]$Record)
  $names = @($Record.queue_checks | Where-Object { $_.result -ne "pass" } | ForEach-Object { [string]$_.name })
  $names += @($Record.coverage_checks | Where-Object { $_.result -ne "pass" } | ForEach-Object { [string]$_.name })
  foreach ($laneResult in @($Record.lane_queue_results)) {
    $names += @($laneResult.checks | Where-Object { $_.result -ne "pass" } | ForEach-Object { [string]$_.name })
  }
  return @($names | Sort-Object -Unique)
}

$cases = @(
  [ordered]@{
    name = "normal_selected_flux_explicitly_deferred"
    expected_result = "pass_local_only"
    expected_failed_check = $null
    expected_deferred_output = $true
    mutate = { param($queue, $coverage) }
  },
  [ordered]@{
    name = "local_prefixed_regressed_completed_status_rejected"
    expected_result = "fail"
    expected_failed_check = "lane_status_expected"
    expected_deferred_output = $true
    mutate = {
      param($queue, $coverage)
      ($queue.lanes | Where-Object { $_.lane_id -eq "sdxl_low_risk_fallback_lane" }).status = "local_regressed_awaiting_rework"
    }
  },
  [ordered]@{
    name = "completed_status_cannot_be_swapped_between_lanes"
    expected_result = "fail"
    expected_failed_check = "lane_status_expected"
    expected_deferred_output = $true
    mutate = {
      param($queue, $coverage)
      $normalStatus = ($queue.lanes | Where-Object { $_.lane_id -eq $normalLaneId }).status
      ($queue.lanes | Where-Object { $_.lane_id -eq "sdxl_low_risk_fallback_lane" }).status = $normalStatus
    }
  },
  [ordered]@{
    name = "deferred_lane_not_listed_rejected"
    expected_result = "fail"
    expected_failed_check = "coverage_queue_lane_results_pass"
    expected_deferred_output = $false
    mutate = {
      param($queue, $coverage)
      $queue.selection_policy.runtime_not_started_lane_ids = @()
    }
  },
  [ordered]@{
    name = "current_lane_cannot_be_deferred"
    expected_result = "fail"
    expected_failed_check = "current_runtime_lane_not_deferred"
    expected_deferred_output = $false
    mutate = {
      param($queue, $coverage)
      $queue.selection_policy.current_runtime_lane_id = $fluxLaneId
    }
  },
  [ordered]@{
    name = "selected_normal_coverage_failure_rejected"
    expected_result = "fail"
    expected_failed_check = "coverage_queue_lane_results_pass"
    expected_deferred_output = $true
    mutate = {
      param($queue, $coverage)
      ($coverage.lane_results | Where-Object { $_.lane_id -eq $normalLaneId }).result = "fail"
      $coverage.failed_lane_count = 2
      $coverage.result = "fail"
    }
  },
  [ordered]@{
    name = "lying_coverage_aggregate_rejected"
    expected_result = "fail"
    expected_failed_check = "coverage_result_pass_local_only"
    expected_deferred_output = $true
    mutate = {
      param($queue, $coverage)
      ($coverage.lane_results | Where-Object { $_.lane_id -eq $normalLaneId }).result = "fail"
      $coverage.failed_lane_count = 1
      $coverage.result = "pass_local_only"
    }
  },
  [ordered]@{
    name = "non_flux_lane_cannot_be_deferred"
    expected_result = "fail"
    expected_failed_check = "runtime_not_started_lane_ids_exact"
    expected_deferred_output = $true
    mutate = {
      param($queue, $coverage)
      $otherLaneId = "sdxl_realvisxl_controlnet_openpose_lane"
      $queue.selection_policy.runtime_not_started_lane_ids = @($fluxLaneId, $otherLaneId)
      ($queue.lanes | Where-Object { $_.lane_id -eq $otherLaneId }).status = $deferredStatus
    }
  },
  [ordered]@{
    name = "deferred_status_must_match_exactly"
    expected_result = "fail"
    expected_failed_check = "runtime_not_started_lane_statuses_exact"
    expected_deferred_output = $false
    mutate = {
      param($queue, $coverage)
      ($queue.lanes | Where-Object { $_.lane_id -eq $fluxLaneId }).status = "queued"
    }
  },
  [ordered]@{
    name = "queue_runtime_permissions_must_remain_false"
    expected_result = "fail"
    expected_failed_check = "runtime_boundary_no_generation"
    expected_deferred_output = $true
    mutate = {
      param($queue, $coverage)
      $queue.runtime_boundary.ec2_start_allowed_by_queue_file = $true
      $queue.runtime_boundary.generation_allowed_by_queue_file = $true
    }
  }
)

$results = @()
foreach ($case in $cases) {
  $caseRoot = Join-Path $runRoot $case.name
  $null = New-Item -ItemType Directory -Force -Path $caseRoot
  $queue = Read-JsonClone -Path $queuePath
  $coverage = Read-JsonClone -Path $coveragePath
  $queue.selection_policy.current_runtime_lane_id = $normalLaneId
  $queue.selection_policy.runtime_not_started_lane_ids = @($fluxLaneId)
  ($queue.lanes | Where-Object { $_.lane_id -eq $fluxLaneId }).status = $deferredStatus
  & $case.mutate $queue $coverage

  $caseQueuePath = Join-Path $caseRoot "queue.json"
  $caseCoveragePath = Join-Path $caseRoot "coverage.json"
  $caseOutPath = Join-Path $caseRoot "validation.json"
  Write-JsonFile -Path $caseQueuePath -Payload $queue
  Write-JsonFile -Path $caseCoveragePath -Payload $coverage

  & $enginePath -NoProfile -File $validatorPath -ProjectRoot $ProjectRoot -QueueFile $caseQueuePath -CoverageFile $caseCoveragePath -OutFile $caseOutPath *> $null
  $exitCode = $LASTEXITCODE
  $record = Read-JsonClone -Path $caseOutPath
  $failedCheckNames = @(Get-FailedCheckNames -Record $record)
  $resultMatched = ([string]$record.result -eq [string]$case.expected_result)
  $exitMatched = (($case.expected_result -eq "pass_local_only" -and $exitCode -eq 0) -or ($case.expected_result -eq "fail" -and $exitCode -eq 2))
  $failureMatched = ($null -eq $case.expected_failed_check -or $failedCheckNames -contains [string]$case.expected_failed_check)
  $deferredOutputMatched = (($record.deferred_coverage_lane_ids -contains $fluxLaneId) -eq [bool]$case.expected_deferred_output)
  $normalRequiredMatched = ($record.required_coverage_lane_ids -contains $normalLaneId)
  $passed = ($resultMatched -and $exitMatched -and $failureMatched -and $deferredOutputMatched -and $normalRequiredMatched)

  $results += [ordered]@{
    name = $case.name
    result = $(if ($passed) { "pass" } else { "fail" })
    observed_validator_result = [string]$record.result
    observed_exit_code = $exitCode
    expected_failed_check = $case.expected_failed_check
    failed_check_names = $failedCheckNames
    deferred_output_matched = $deferredOutputMatched
    normal_required_matched = $normalRequiredMatched
  }
}

$failed = @($results | Where-Object { $_.result -ne "pass" })
$summary = [ordered]@{
  classification = $(if (@($failed).Count -eq 0) { "RUNTIME_LANE_QUEUE_DEFERRED_COVERAGE_REGRESSION_PASS" } else { "RUNTIME_LANE_QUEUE_DEFERRED_COVERAGE_REGRESSION_FAIL" })
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  local_only = $true
  ec2_started = $false
  generation_executed = $false
  case_count = @($results).Count
  passed_case_count = @($results | Where-Object { $_.result -eq "pass" }).Count
  failed_case_count = @($failed).Count
  run_root = $runRoot
  cases = $results
}

$summary | ConvertTo-Json -Depth 20
if (@($failed).Count -gt 0) { exit 1 }
exit 0
