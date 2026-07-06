<#
.SYNOPSIS
Starts an instance-side EC2 stop watchdog through SSM.

.DESCRIPTION
Dry-run by default. With -Execute, sends a short SSM command that launches a
background watchdog. The watchdog first tries AWS CLI StopInstances from inside
the instance and can optionally fall back to OS shutdown.
#>
param(
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [int]$StopAfterMinutes = 60,
  [string]$OutFile = "",
  [switch]$AllowOsShutdownFallback,
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
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W63_EC2_INSTANCE_WATCHDOG_$stamp.json"
}

$seconds = [Math]::Max(60, $StopAfterMinutes * 60)
$fallback = $(if ($AllowOsShutdownFallback) { "true" } else { "false" })
$remoteScript = @"
cat >/tmp/codex_ec2_stop_watchdog.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
sleep $seconds
aws ec2 stop-instances --region '$Region' --instance-ids '$InstanceId' --output json >/tmp/codex_ec2_stop_watchdog_stop.json 2>/tmp/codex_ec2_stop_watchdog_stop.err || {
  if [ '$fallback' = 'true' ]; then
    sudo shutdown -h now
  else
    exit 1
  fi
}
SH
chmod 700 /tmp/codex_ec2_stop_watchdog.sh
nohup /tmp/codex_ec2_stop_watchdog.sh >/tmp/codex_ec2_stop_watchdog.log 2>&1 &
echo `$! >/tmp/codex_ec2_stop_watchdog.pid
cat /tmp/codex_ec2_stop_watchdog.pid
"@

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "start_ec2_instance_stop_watchdog"
  instance_id = $InstanceId
  region = $Region
  stop_after_minutes = $StopAfterMinutes
  allow_os_shutdown_fallback = [bool]$AllowOsShutdownFallback
  execute = [bool]$Execute
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  command_id = $null
  command_status = "not_started"
  watchdog_pid = $null
  result = "dry_run_instance_watchdog_plan"
  failure_category = $null
  errors = @()
  next_action = "Run with -Execute only after the instance is already running and SSM is online."
}

if ($Execute) {
  $record.aws_contacted = $true
  try {
    $payload = @{
      DocumentName = "AWS-RunShellScript"
      InstanceIds = @($InstanceId)
      TimeoutSeconds = 120
      Parameters = @{ commands = @($remoteScript); executionTimeout = @("120") }
    }
    $payloadPath = Join-Path $env:TEMP "codex_instance_watchdog_payload_$stamp.json"
    Write-JsonNoBom -Value $payload -Path $payloadPath -Depth 10
    $record.command_id = (aws ssm send-command --region $Region --cli-input-json "file://$payloadPath" --query "Command.CommandId" --output text).Trim()
    for ($i = 1; $i -le 24; $i++) {
      $record.command_status = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "Status" --output text 2>$null).Trim()
      if (@("Success","Failed","Cancelled","TimedOut").Contains($record.command_status)) { break }
      Start-Sleep -Seconds 5
    }
    $stdout = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "StandardOutputContent" --output text 2>$null)
    $record.watchdog_pid = ([string]$stdout).Trim()
    if ($record.command_status -eq "Success") {
      $record.result = "instance_stop_watchdog_started"
      $record.next_action = "Continue the bounded EC2 runtime window; the watchdog is a last-resort stop only."
    } else {
      $record.result = "instance_stop_watchdog_failed"
      $record.failure_category = "ssm_watchdog_command_failed"
    }
  } catch {
    $record.result = "instance_stop_watchdog_failed"
    $record.failure_category = "ssm_watchdog_command_failed"
    $record.errors += $_.Exception.Message
  }
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
Write-JsonNoBom -Value $record -Path $OutFile -Depth 20
$record | ConvertTo-Json -Depth 20
if ($record.errors.Count -gt 0 -or ($Execute -and $record.result -ne "instance_stop_watchdog_started")) { exit 2 }
