<#
.SYNOPSIS
Verifies the AWS account and EC2 identity for the ComfyUI GPU server without starting or stopping anything.
#>
param(
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$ExpectedAccount = "029530099913",
  [string]$ExpectedName = "ComfyUI-LoRA-GPU-Server",
  [string]$ExpectedType = "g5.xlarge",
  [string]$ExpectedIamProfileName = "ComfyUI-SSM-Profile",
  [string]$ExpectedVolumeId = "vol-0eb9b2c6d3d2706d6",
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [switch]$Json
)

$ErrorActionPreference = "Stop"
. (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1") -ProjectRoot $ProjectRoot -Quiet

$result = [ordered]@{
  checked_at = (Get-Date).ToString("o")
  account_expected = $ExpectedAccount
  account_actual = $null
  account_match = $false
  instance_id = $InstanceId
  instance_found = $false
  instance_state = $null
  name_actual = $null
  name_match = $false
  type_actual = $null
  type_match = $false
  iam_profile_actual = $null
  iam_profile_match = $false
  volumes_actual = @()
  volume_match = $false
  public_ip = $null
  passed = $false
  errors = @()
}

try {
  $identity = aws sts get-caller-identity | ConvertFrom-Json
  $result.account_actual = $identity.Account
  $result.account_match = ($identity.Account -eq $ExpectedAccount)
} catch {
  $result.errors += "aws sts get-caller-identity failed: $($_.Exception.Message)"
}

try {
  $desc = aws ec2 describe-instances --instance-ids $InstanceId | ConvertFrom-Json
  $inst = $desc.Reservations[0].Instances[0]
  $result.instance_found = $true
  $result.instance_state = $inst.State.Name
  $result.type_actual = $inst.InstanceType
  $result.type_match = ($inst.InstanceType -eq $ExpectedType)
  $nameTag = ($inst.Tags | Where-Object { $_.Key -eq "Name" } | Select-Object -First 1).Value
  $result.name_actual = $nameTag
  $result.name_match = ($nameTag -eq $ExpectedName)
  if ($inst.IamInstanceProfile) {
    $result.iam_profile_actual = $inst.IamInstanceProfile.Arn
    $result.iam_profile_match = ($inst.IamInstanceProfile.Arn -like "*$ExpectedIamProfileName*")
  }
  $vols = @()
  foreach ($bdm in $inst.BlockDeviceMappings) {
    if ($bdm.Ebs.VolumeId) { $vols += $bdm.Ebs.VolumeId }
  }
  $result.volumes_actual = $vols
  $result.volume_match = ($vols -contains $ExpectedVolumeId)
  $result.public_ip = $inst.PublicIpAddress
} catch {
  $result.errors += "aws ec2 describe-instances failed: $($_.Exception.Message)"
}

$result.passed = $result.account_match -and $result.instance_found -and $result.name_match -and $result.type_match -and $result.iam_profile_match -and $result.volume_match

if ($Json) {
  $result | ConvertTo-Json -Depth 10
} else {
  $result.GetEnumerator() | ForEach-Object { Write-Host "$($_.Key): $($_.Value)" }
}
if (-not $result.passed) { exit 2 }
