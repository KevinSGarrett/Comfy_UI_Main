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
  [int]$StopAfterMinutes = 60,
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
  result = "dry_run_emergency_stop_schedule_plan"
  failure_category = $null
  errors = @()
  next_action = $(if ([string]::IsNullOrWhiteSpace($SchedulerRoleArn)) {
      "Create the scheduler execution role from configs/aws, then rerun this helper with -SchedulerRoleArn before EC2 runtime windows."
    } else {
      "Dry-run schedule plan is ready; run with -Execute only immediately before an approved bounded EC2 runtime window after AWS auth and Git cleanliness checks pass."
    })
}

if ([string]::IsNullOrWhiteSpace($SchedulerRoleArn)) {
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
    $record.result = "emergency_stop_schedule_created"
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
