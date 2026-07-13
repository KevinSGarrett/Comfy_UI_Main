<#
.SYNOPSIS
Starts an instance-side EC2 stop watchdog through SSM.

.DESCRIPTION
Dry-run by default. With -Execute, sends a short SSM command that launches a
background watchdog. When -AllowOsShutdownFallback is supplied, the watchdog
uses verified OS shutdown directly so the restricted instance role does not
generate an expected-but-noisy ec2:StopInstances authorization failure.
#>
param(
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$RuntimeWindowId = "",
  [string]$TrackerId = "",
  [string]$ItemId = "",
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
# AWS-RunShellScript executes this outer payload with /bin/sh.
set -eu
if [ '$fallback' = 'true' ]; then
  sudo -n shutdown --help >/dev/null
  echo 'STOP_CAPABILITY=os_shutdown_direct_verified'
else
  set +e
  dry_run_output=`$(aws ec2 stop-instances --dry-run --region '$Region' --instance-ids '$InstanceId' 2>&1)
  dry_run_rc=`$?
  set -e
  if echo "`$dry_run_output" | grep -q 'DryRunOperation'; then
    echo 'STOP_CAPABILITY=ec2_api_dry_run_verified'
  else
    echo "STOP_CAPABILITY=unavailable rc=`$dry_run_rc" >&2
    exit 42
  fi
fi

cat >/tmp/codex_ec2_stop_watchdog.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
sleep $seconds
if [ '$fallback' = 'true' ]; then
  sudo -n shutdown -h now
else
  aws ec2 stop-instances --region '$Region' --instance-ids '$InstanceId' --output json >/tmp/codex_ec2_stop_watchdog_stop.json 2>/tmp/codex_ec2_stop_watchdog_stop.err
fi
SH
chmod 700 /tmp/codex_ec2_stop_watchdog.sh
nohup /tmp/codex_ec2_stop_watchdog.sh >/tmp/codex_ec2_stop_watchdog.log 2>&1 &
watchdog_pid=`$!
echo `$watchdog_pid >/tmp/codex_ec2_stop_watchdog.pid
echo "WATCHDOG_PID=`$watchdog_pid"
"@

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "start_ec2_instance_stop_watchdog"
  runtime_window_id = $(if ([string]::IsNullOrWhiteSpace($RuntimeWindowId)) { $null } else { $RuntimeWindowId })
  tracker_id = $(if ([string]::IsNullOrWhiteSpace($TrackerId)) { $null } else { $TrackerId })
  item_id = $(if ([string]::IsNullOrWhiteSpace($ItemId)) { $null } else { $ItemId })
  instance_id = $InstanceId
  region = $Region
  stop_after_minutes = $StopAfterMinutes
  allow_os_shutdown_fallback = [bool]$AllowOsShutdownFallback
  effective_stop_method = $(if ($AllowOsShutdownFallback) { "os_shutdown_direct" } else { "ec2_api" })
  avoids_expected_ec2_api_authorization_failure = [bool]$AllowOsShutdownFallback
  execute = [bool]$Execute
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  command_id = $null
  command_status = "not_started"
  watchdog_pid = $null
  stop_capability_verified = $false
  stop_capability_method = $null
  result = "dry_run_instance_watchdog_plan"
  failure_category = $null
  errors = @()
  next_action = "Run with -Execute only after the instance is already running and SSM is online."
}

if ($InstanceId -notmatch '^i-[0-9a-f]{8}([0-9a-f]{9})?$' -or $Region -notmatch '^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$') {
  $record.result = "blocked_invalid_instance_or_region"
  $record.failure_category = "invalid_instance_or_region"
  $record.errors += "-InstanceId or -Region failed the strict AWS identifier format check."
} elseif ($Execute -and $RuntimeWindowId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') {
  $record.result = "blocked_missing_or_invalid_runtime_window_id"
  $record.failure_category = "missing_or_invalid_runtime_window_id"
  $record.errors += "-RuntimeWindowId is required for live execution and must use 8-128 safe identifier characters."
} elseif ($Execute) {
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
    $invocation = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --output json 2>$null | ConvertFrom-Json
    $stdout = [string]$invocation.StandardOutputContent
    $stderr = [string]$invocation.StandardErrorContent
    $stdoutLines = @(([string]$stdout -split "`r?`n") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $capabilityLine = @($stdoutLines | Where-Object { $_ -like "STOP_CAPABILITY=*" } | Select-Object -Last 1)
    $pidLine = @($stdoutLines | Where-Object { $_ -like "WATCHDOG_PID=*" } | Select-Object -Last 1)
    if ($capabilityLine.Count -eq 1) {
      $record.stop_capability_method = ([string]$capabilityLine[0]).Substring("STOP_CAPABILITY=".Length)
      $record.stop_capability_verified = @("ec2_api_dry_run_verified", "os_shutdown_direct_verified").Contains($record.stop_capability_method)
    }
    if ($pidLine.Count -eq 1) {
      $record.watchdog_pid = ([string]$pidLine[0]).Substring("WATCHDOG_PID=".Length)
    }
    if ($record.command_status -eq "Success" -and $record.stop_capability_verified -and [string]$record.watchdog_pid -match '^[0-9]+$') {
      $record.result = "instance_stop_watchdog_started_and_capability_verified"
      $record.next_action = "Continue the bounded EC2 runtime window; the watchdog is a last-resort stop only."
    } else {
      $record.result = "instance_stop_watchdog_failed"
      $record.failure_category = "ssm_watchdog_command_failed"
      if (![string]::IsNullOrWhiteSpace($stderr)) {
        $record.errors += $stderr.Trim()
      }
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
if ($record.errors.Count -gt 0 -or ($Execute -and $record.result -ne "instance_stop_watchdog_started_and_capability_verified")) { exit 2 }
