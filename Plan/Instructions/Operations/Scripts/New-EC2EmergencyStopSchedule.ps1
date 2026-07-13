<#
.SYNOPSIS
Creates a one-time EventBridge Scheduler emergency stop for the GPU EC2 instance.

.DESCRIPTION
Dry-run by default. With -Execute and a scheduler execution role ARN, creates a
one-time schedule that calls EC2 StopInstances after a short TTL. Use this as a
cloud-side safety net before bounded EC2 runtime windows.
#>
param(
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$SchedulerRoleArn = "",
  [string]$RuntimeWindowId = "",
  [string]$TrackerId = "",
  [string]$ItemId = "",
  [int]$StopAfterMinutes = 60,
  [int]$VerificationAttempts = 6,
  [int]$VerificationDelaySeconds = 2,
  [string]$ScheduleName = "",
  [string]$OutFile = "",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($ScheduleName)) {
  $shortStamp = (Get-Date -Format "yyyyMMddTHHmmss")
  $ScheduleName = "cu-stop-$shortStamp" -replace "[^A-Za-z0-9_.-]", "-"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W63_EC2_EMERGENCY_STOP_SCHEDULE_$stamp.json"
}

$stopAtUtc = (Get-Date).ToUniversalTime().AddMinutes($StopAfterMinutes)
$scheduleExpression = "at($($stopAtUtc.ToString("yyyy-MM-ddTHH:mm:ss")))"
$target = [ordered]@{
  RoleArn = $SchedulerRoleArn
  Arn = "arn:aws:scheduler:::aws-sdk:ec2:stopInstances"
  Input = (@{ InstanceIds = @($InstanceId) } | ConvertTo-Json -Compress)
}

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "new_ec2_emergency_stop_schedule"
  runtime_window_id = $(if ([string]::IsNullOrWhiteSpace($RuntimeWindowId)) { $null } else { $RuntimeWindowId })
  tracker_id = $(if ([string]::IsNullOrWhiteSpace($TrackerId)) { $null } else { $TrackerId })
  item_id = $(if ([string]::IsNullOrWhiteSpace($ItemId)) { $null } else { $ItemId })
  instance_id = $InstanceId
  region = $Region
  schedule_name = $ScheduleName
  schedule_expression = $scheduleExpression
  stop_after_minutes = $StopAfterMinutes
  scheduler_role_arn_supplied = ![string]::IsNullOrWhiteSpace($SchedulerRoleArn)
  target_arn = $target.Arn
  action_after_completion = "DELETE"
  execute = [bool]$Execute
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  schedule_verified = $false
  schedule_state = $null
  verification_attempts = 0
  result = "dry_run_emergency_stop_schedule_plan"
  failure_category = $null
  errors = @()
  next_action = $(if ([string]::IsNullOrWhiteSpace($SchedulerRoleArn)) {
      "Create the scheduler execution role from configs/aws, then rerun this helper with -SchedulerRoleArn before EC2 runtime windows."
    } else {
      "Dry-run schedule plan is ready; run with -Execute only immediately before an approved bounded EC2 runtime window after AWS auth and Git cleanliness checks pass."
    })
}

if ($InstanceId -notmatch '^i-[0-9a-f]{8}([0-9a-f]{9})?$' -or $Region -notmatch '^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$') {
  $record.result = "blocked_invalid_instance_or_region"
  $record.failure_category = "invalid_instance_or_region"
  $record.errors += "-InstanceId or -Region failed the strict AWS identifier format check."
} elseif ($Execute -and $RuntimeWindowId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') {
  $record.result = "blocked_missing_or_invalid_runtime_window_id"
  $record.failure_category = "missing_or_invalid_runtime_window_id"
  $record.errors += "-RuntimeWindowId is required for live execution and must use 8-128 safe identifier characters."
} elseif ([string]::IsNullOrWhiteSpace($SchedulerRoleArn)) {
  $record.result = "blocked_missing_scheduler_role_arn"
  $record.failure_category = "missing_scheduler_role_arn"
} elseif ($Execute) {
  $record.aws_contacted = $true
  try {
    $targetPath = Join-Path $env:TEMP "codex_scheduler_target_$stamp.json"
    Write-JsonNoBom -Value $target -Path $targetPath -Depth 10
    aws scheduler create-schedule `
      --region $Region `
      --name $ScheduleName `
      --schedule-expression $scheduleExpression `
      --schedule-expression-timezone UTC `
      --flexible-time-window Mode=OFF `
      --action-after-completion DELETE `
      --target "file://$targetPath" | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "aws scheduler create-schedule failed with exit code $LASTEXITCODE"
    }

    for ($attempt = 1; $attempt -le [Math]::Max(1, $VerificationAttempts); $attempt++) {
      $record.verification_attempts = $attempt
      $liveJson = aws scheduler get-schedule --region $Region --name $ScheduleName --output json 2>$null
      if ($LASTEXITCODE -eq 0 -and ![string]::IsNullOrWhiteSpace([string]$liveJson)) {
        $live = $liveJson | ConvertFrom-Json
        $liveInput = $null
        try { $liveInput = ([string]$live.Target.Input | ConvertFrom-Json) } catch { $liveInput = $null }
        $record.schedule_state = [string]$live.State
        $record.schedule_verified = (
          [string]$live.Name -eq $ScheduleName -and
          [string]$live.ScheduleExpression -eq $scheduleExpression -and
          [string]$live.ActionAfterCompletion -eq "DELETE" -and
          [string]$live.State -eq "ENABLED" -and
          [string]$live.Target.Arn -eq [string]$target.Arn -and
          [string]$live.Target.RoleArn -eq $SchedulerRoleArn -and
          $null -ne $liveInput -and
          @($liveInput.InstanceIds).Count -eq 1 -and
          [string]$liveInput.InstanceIds[0] -eq $InstanceId
        )
        if ($record.schedule_verified) { break }
      }
      if ($attempt -lt [Math]::Max(1, $VerificationAttempts)) {
        Start-Sleep -Seconds ([Math]::Max(0, $VerificationDelaySeconds))
      }
    }
    if (!$record.schedule_verified) {
      throw "Emergency-stop schedule was created but exact live verification failed. Leave the schedule in place and block the runtime window."
    }

    $record.result = "emergency_stop_schedule_created_and_verified"
    $record.next_action = "Leave this one-time safety stop in place for the current EC2 window; it deletes itself after completion."
  } catch {
    $record.result = "emergency_stop_schedule_failed"
    $record.failure_category = "scheduler_create_failed"
    $record.errors += $_.Exception.Message
  }
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
Write-JsonNoBom -Value $record -Path $OutFile -Depth 20
$record | ConvertTo-Json -Depth 20
if ($record.errors.Count -gt 0) { exit 2 }
