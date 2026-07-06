<#
.SYNOPSIS
Stops the ComfyUI EC2 GPU server and verifies stopped state.
Requires -Execute to perform the stop. Without -Execute, this is a dry-run.
#>
param(
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
. (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1") -ProjectRoot $ProjectRoot -Quiet

$identityScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-AwsComfyGpuIdentity.ps1"
& $identityScript -ProjectRoot $ProjectRoot
if ($LASTEXITCODE -ne 0) { throw "AWS/EC2 identity check failed. Stop aborted." }

$state = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
Write-Host "Current instance state: $state"

if ($state -eq "stopped") {
  Write-Host "Instance already stopped."
  exit 0
}

if (-not $Execute) {
  Write-Host "DRY RUN: would run aws ec2 stop-instances and wait instance-stopped. Re-run with -Execute to stop."
  exit 0
}

aws ec2 stop-instances --instance-ids $InstanceId
aws ec2 wait instance-stopped --instance-ids $InstanceId
$newState = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
Write-Host "New instance state: $newState"
if ($newState -ne "stopped") { exit 4 }
