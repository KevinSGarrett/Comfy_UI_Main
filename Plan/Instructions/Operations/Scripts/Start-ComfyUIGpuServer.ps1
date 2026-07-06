<#
.SYNOPSIS
Starts the ComfyUI EC2 GPU server only after identity verification.
Requires -Execute to perform the start. Without -Execute, this is a dry-run.
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
if ($LASTEXITCODE -ne 0) { throw "AWS/EC2 identity check failed. Start aborted." }

$state = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
Write-Host "Current instance state: $state"

if ($state -eq "running") {
  Write-Host "Instance already running. Verifying instance-status-ok..."
  if ($Execute) { aws ec2 wait instance-status-ok --instance-ids $InstanceId }
  exit 0
}

if ($state -ne "stopped") {
  throw "Instance is in state '$state'. Start only allowed from stopped or running."
}

if (-not $Execute) {
  Write-Host "DRY RUN: would run aws ec2 start-instances and waiters. Re-run with -Execute to start."
  exit 0
}

aws ec2 start-instances --instance-ids $InstanceId
aws ec2 wait instance-running --instance-ids $InstanceId
aws ec2 wait instance-status-ok --instance-ids $InstanceId
$newState = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
Write-Host "New instance state: $newState"
if ($newState -ne "running") { exit 3 }
