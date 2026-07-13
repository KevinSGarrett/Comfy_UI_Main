param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$windowId = "rw-normal-regression-20260713"
$instanceId = "i-0560bf8d143f93bb1"
$region = "us-east-1"
$helper = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\EC2RuntimeWindowSafetyGate.ps1"
$staticExecutor = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1"
$smokeExecutor = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1"
$queueFile = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json"
. $helper

function Write-JsonNoBom {
  param([object]$Value, [string]$Path)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 20), [System.Text.UTF8Encoding]::new($false))
}

function New-Test {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Test-ExecutorOrdering {
  param([string]$Path, [string]$PayloadMarker)
  $text = Get-Content -LiteralPath $Path -Raw
  $startIndex = $text.IndexOf("aws ec2 start-instances")
  $ssmIndex = $text.IndexOf("SSM did not become Online")
  $watchdogIndex = $text.IndexOf("Invoke-VerifiedInstanceWatchdog")
  $payloadIndex = $text.IndexOf($PayloadMarker)
  return [pscustomobject]@{
    emergency_gate_before_start = ($text.IndexOf("Get-EmergencyStopScheduleStatus") -ge 0 -and $text.IndexOf("Get-EmergencyStopScheduleStatus") -lt $startIndex)
    ssm_before_watchdog = ($ssmIndex -ge 0 -and $ssmIndex -lt $watchdogIndex)
    watchdog_before_payload = ($watchdogIndex -ge 0 -and $watchdogIndex -lt $payloadIndex)
    indexes = [ordered]@{ start=$startIndex; ssm=$ssmIndex; watchdog=$watchdogIndex; payload=$payloadIndex }
  }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ec2_runtime_safety_regression_" + [guid]::NewGuid().ToString("N"))
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null
try {
  $validSchedulePath = Join-Path $tempRoot "valid_schedule.json"
  $validSchedule = [ordered]@{
    result = "emergency_stop_schedule_created_and_verified"
    runtime_window_id = $windowId
    instance_id = $instanceId
    region = $region
    execute = $true
    aws_contacted = $true
    schedule_verified = $true
    ec2_started = $false
    generation_executed = $false
  }
  Write-JsonNoBom $validSchedule $validSchedulePath

  $drySchedulePath = Join-Path $tempRoot "dry_schedule.json"
  $drySchedule = [ordered]@{} + $validSchedule
  $drySchedule.result = "dry_run_emergency_stop_schedule_plan"
  $drySchedule.execute = $false
  $drySchedule.aws_contacted = $false
  $drySchedule.schedule_verified = $false
  Write-JsonNoBom $drySchedule $drySchedulePath

  $mismatchSchedulePath = Join-Path $tempRoot "mismatch_schedule.json"
  $mismatchSchedule = [ordered]@{} + $validSchedule
  $mismatchSchedule.runtime_window_id = "rw-different-regression-window"
  Write-JsonNoBom $mismatchSchedule $mismatchSchedulePath

  $incompleteSchedulePath = Join-Path $tempRoot "incomplete_schedule.json"
  $incompleteSchedule = [ordered]@{} + $validSchedule
  $incompleteSchedule.Remove("generation_executed")
  Write-JsonNoBom $incompleteSchedule $incompleteSchedulePath

  $validWatchdogPath = Join-Path $tempRoot "valid_watchdog.json"
  $validWatchdog = [ordered]@{
    result = "instance_stop_watchdog_started_and_capability_verified"
    runtime_window_id = $windowId
    instance_id = $instanceId
    region = $region
    execute = $true
    aws_contacted = $true
    command_status = "Success"
    command_id = "regression-command-id"
    stop_capability_verified = $true
    watchdog_pid = "4242"
    generation_executed = $false
  }
  Write-JsonNoBom $validWatchdog $validWatchdogPath

  $dryWatchdogPath = Join-Path $tempRoot "dry_watchdog.json"
  $dryWatchdog = [ordered]@{} + $validWatchdog
  $dryWatchdog.result = "dry_run_instance_watchdog_plan"
  $dryWatchdog.execute = $false
  $dryWatchdog.aws_contacted = $false
  $dryWatchdog.command_status = "not_started"
  $dryWatchdog.stop_capability_verified = $false
  $dryWatchdog.watchdog_pid = $null
  Write-JsonNoBom $dryWatchdog $dryWatchdogPath

  $validScheduleStatus = Get-EmergencyStopScheduleStatus $validSchedulePath $windowId $instanceId $region
  $dryScheduleStatus = Get-EmergencyStopScheduleStatus $drySchedulePath $windowId $instanceId $region
  $mismatchScheduleStatus = Get-EmergencyStopScheduleStatus $mismatchSchedulePath $windowId $instanceId $region
  $incompleteScheduleStatus = Get-EmergencyStopScheduleStatus $incompleteSchedulePath $windowId $instanceId $region
  $validWatchdogStatus = Get-InstanceStopWatchdogStatus $validWatchdogPath $windowId $instanceId $region
  $dryWatchdogStatus = Get-InstanceStopWatchdogStatus $dryWatchdogPath $windowId $instanceId $region
  $missingScheduleStatus = Get-EmergencyStopScheduleStatus (Join-Path $tempRoot "missing.json") $windowId $instanceId $region
  $staticOrdering = Test-ExecutorOrdering $staticExecutor '$payloadPath = Join-Path $env:TEMP ("codex_ec2_lane_static_proof_'
  $smokeOrdering = Test-ExecutorOrdering $smokeExecutor '$payloadPath = Join-Path $env:TEMP ("codex_ec2_workflow_smoke_'
  $queue = Get-Content -LiteralPath $queueFile -Raw | ConvertFrom-Json
  $gitEmpty = Resolve-GitCheckpointCleanliness -PorcelainLines @() -PreservedExcludePath @()
  $gitDirtyNoExclude = Resolve-GitCheckpointCleanliness -PorcelainLines @(" M Plan/a.json") -PreservedExcludePath @()
  $gitExactExclude = Resolve-GitCheckpointCleanliness -PorcelainLines @(" M Plan/a.json") -PreservedExcludePath @("Plan/a.json")
  $gitPrefixPartial = Resolve-GitCheckpointCleanliness -PorcelainLines @(" M Plan/a.json", "?? tools/new.ps1") -PreservedExcludePath @("Plan")
  $gitStagedExcluded = Resolve-GitCheckpointCleanliness -PorcelainLines @("M  Plan/a.json") -PreservedExcludePath @("Plan/a.json")
  $gitNormalizedExclude = Resolve-GitCheckpointCleanliness -PorcelainLines @("?? tools/new.ps1") -PreservedExcludePath @(".\tools\")
  $gitTypoExclude = Resolve-GitCheckpointCleanliness -PorcelainLines @("?? tools/new.ps1") -PreservedExcludePath @("tool")
  $helperText = Get-Content -LiteralPath $helper -Raw

  $tests = @(
    (New-Test "valid_live_schedule_accepted" $validScheduleStatus.verified $validScheduleStatus.status "pass"),
    (New-Test "dry_run_schedule_rejected" (-not $dryScheduleStatus.verified) $dryScheduleStatus.failure_category "live_emergency_stop_schedule_not_verified"),
    (New-Test "mismatched_window_rejected" (-not $mismatchScheduleStatus.verified) $mismatchScheduleStatus.checks.runtime_window_match $false),
    (New-Test "missing_safety_field_rejected" (-not $incompleteScheduleStatus.verified) $incompleteScheduleStatus.checks.generation_not_executed $false),
    (New-Test "missing_schedule_rejected" (-not $missingScheduleStatus.verified) $missingScheduleStatus.found $false),
    (New-Test "valid_live_watchdog_accepted" $validWatchdogStatus.verified $validWatchdogStatus.status "pass"),
    (New-Test "dry_run_watchdog_rejected" (-not $dryWatchdogStatus.verified) $dryWatchdogStatus.failure_category "instance_stop_watchdog_not_verified"),
    (New-Test "static_emergency_gate_before_start" $staticOrdering.emergency_gate_before_start $staticOrdering.indexes "gate before start"),
    (New-Test "static_watchdog_after_ssm_before_payload" ($staticOrdering.ssm_before_watchdog -and $staticOrdering.watchdog_before_payload) $staticOrdering.indexes "ssm < watchdog < payload"),
    (New-Test "smoke_emergency_gate_before_start" $smokeOrdering.emergency_gate_before_start $smokeOrdering.indexes "gate before start"),
    (New-Test "smoke_watchdog_after_ssm_before_payload" ($smokeOrdering.ssm_before_watchdog -and $smokeOrdering.watchdog_before_payload) $smokeOrdering.indexes "ssm < watchdog < payload"),
    (New-Test "queue_boundary_remains_fail_closed" (-not [bool]$queue.runtime_boundary.ec2_start_allowed_by_queue_file -and -not [bool]$queue.runtime_boundary.generation_allowed_by_queue_file) $queue.runtime_boundary "both flags false"),
    (New-Test "git_no_excludes_empty_is_clean" ($gitEmpty.actual_clean -and $gitEmpty.effective_clean) $gitEmpty "actual and effective clean"),
    (New-Test "git_no_excludes_dirty_blocks" (-not $gitDirtyNoExclude.effective_clean -and $gitDirtyNoExclude.unexpected_dirty_count -eq 1) $gitDirtyNoExclude "one unexpected dirty path"),
    (New-Test "git_exact_exclude_is_effectively_clean" (-not $gitExactExclude.actual_clean -and $gitExactExclude.effective_clean -and $gitExactExclude.excluded_dirty_count -eq 1) $gitExactExclude "actual dirty, effective clean"),
    (New-Test "git_prefix_exclude_does_not_hide_uncovered_path" (-not $gitPrefixPartial.effective_clean -and $gitPrefixPartial.excluded_dirty_count -eq 1 -and $gitPrefixPartial.unexpected_dirty_count -eq 1) $gitPrefixPartial "one excluded and one unexpected"),
    (New-Test "git_staged_path_blocks_even_when_excluded" (-not $gitStagedExcluded.effective_clean -and $gitStagedExcluded.staged_count -eq 1 -and $gitStagedExcluded.excluded_dirty_count -eq 0) $gitStagedExcluded "staged always blocks"),
    (New-Test "git_exclude_normalization_matches" ($gitNormalizedExclude.effective_clean -and $gitNormalizedExclude.excluded_dirty_count -eq 1) $gitNormalizedExclude "normalized prefix match"),
    (New-Test "git_typo_exclude_fails_closed" (-not $gitTypoExclude.effective_clean -and $gitTypoExclude.unexpected_dirty_count -eq 1) $gitTypoExclude "typo does not match"),
    (New-Test "git_origin_match_remains_required" ($helperText -match '\$result\.local_matches_origin\s+-and\s+\$result\.effective_clean') "source contract present" "origin and effective cleanliness required")
  )

  $failed = @($tests | Where-Object result -ne "pass")
  $record = [ordered]@{
    schema_version = "1.0"
    artifact_type = "ec2_runtime_window_safety_gate_regression"
    created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
    failure_category = $(if ($failed.Count -eq 0) { $null } else { "regression_case_failed" })
    local_only = $true
    aws_contacted = $false
    ec2_started = $false
    generation_executed = $false
    test_count = $tests.Count
    passing_test_count = @($tests | Where-Object result -eq "pass").Count
    failed_test_count = $failed.Count
    tests = $tests
    boundary = "Local evidence-parser and source-order regression only. No AWS, SSM, EC2, ComfyUI, or generation action occurred."
  }
  if ([string]::IsNullOrWhiteSpace($OutFile)) {
    $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
    $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W64_EC2_RUNTIME_WINDOW_SAFETY_GATE_REGRESSION_$stamp.json"
  }
  [System.IO.Directory]::CreateDirectory((Split-Path -Parent $OutFile)) | Out-Null
  Write-JsonNoBom $record $OutFile
  $record | ConvertTo-Json -Depth 20
  if ($failed.Count -gt 0) { exit 1 }
  exit 0
} finally {
  if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
