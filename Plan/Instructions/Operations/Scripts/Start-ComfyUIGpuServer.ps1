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
. (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\EC2StartFailureClassification.ps1")

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

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
  $startOutput = @(aws ec2 start-instances --instance-ids $InstanceId 2>&1)
  $startExitCode = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $previousErrorActionPreference
}
if ($startExitCode -ne 0) {
  $startText = (($startOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
  $failureCategory = Get-EC2StartFailureCategory -ExitCode $startExitCode -OutputText $startText
  Write-Error "EC2 start failed [$failureCategory] exit=$startExitCode. $startText" -ErrorAction Continue
  exit 2
}
aws ec2 wait instance-running --instance-ids $InstanceId
aws ec2 wait instance-status-ok --instance-ids $InstanceId
$newState = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
Write-Host "New instance state: $newState"
if ($newState -ne "running") { exit 3 }
