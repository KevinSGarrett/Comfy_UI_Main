param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$FilesystemEvidenceFile = "",
  [double]$HeadroomMultiplier = 1.5,
  [int]$MinimumHeadroomGiB = 100,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
if ($HeadroomMultiplier -lt 1.25 -or $HeadroomMultiplier -gt 3.0) { throw "HeadroomMultiplier must be between 1.25 and 3.0." }
if ($MinimumHeadroomGiB -lt 50 -or $MinimumHeadroomGiB -gt 500) { throw "MinimumHeadroomGiB must be between 50 and 500." }

$instance = aws ec2 describe-instances --instance-ids $InstanceId --region $Region --query "Reservations[0].Instances[0]" --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Unable to read the approved instance." }
$volumeId = [string]$instance.BlockDeviceMappings[0].Ebs.VolumeId
$volume = aws ec2 describe-volumes --volume-ids $volumeId --region $Region --query "Volumes[0]" --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Unable to read the approved EBS volume." }

$filesystem = $null
if (![string]::IsNullOrWhiteSpace($FilesystemEvidenceFile) -and (Test-Path -LiteralPath $FilesystemEvidenceFile -PathType Leaf)) {
  $evidence = Get-Content -Raw -LiteralPath $FilesystemEvidenceFile | ConvertFrom-Json
  if ($null -ne $evidence.remote_result -and $null -ne $evidence.remote_result.root_filesystem) {
    $filesystem = $evidence.remote_result.root_filesystem
  } elseif ($null -ne $evidence.root_filesystem) {
    $filesystem = $evidence.root_filesystem
  }
}

$classification = "BLOCKED_EBS_USED_BYTES_PROOF_MISSING"
$recommendedGiB = $null
if ($null -ne $filesystem -and [long]$filesystem.used_bytes -gt 0) {
  $usedGiB = [math]::Ceiling([long]$filesystem.used_bytes / 1GB)
  $recommendedGiB = [int][math]::Ceiling([math]::Max($usedGiB * $HeadroomMultiplier, $usedGiB + $MinimumHeadroomGiB) / 10) * 10
  if ($recommendedGiB -ge [int]$volume.Size) {
    $classification = "EBS_RIGHT_SIZE_MIGRATION_NOT_COST_JUSTIFIED"
  } else {
    $classification = "EBS_ENCRYPTED_RIGHT_SIZE_MIGRATION_PLANNING_READY"
  }
}

$record = [ordered]@{
  schema_version = "1.0"
  created_at = [datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  result = "pass"
  classification = $classification
  instance_id = $InstanceId
  instance_state = [string]$instance.State.Name
  volume_id = $volumeId
  current_size_gib = [int]$volume.Size
  current_volume_type = [string]$volume.VolumeType
  current_encrypted = [bool]$volume.Encrypted
  filesystem_evidence_file = $FilesystemEvidenceFile
  filesystem = $filesystem
  recommended_target_size_gib = $recommendedGiB
  target_encryption_required = $true
  in_place_shrink_supported = $false
  mutation_authorized = $false
  next_action = $(if ($classification -eq "BLOCKED_EBS_USED_BYTES_PROOF_MISSING") { "Capture root_filesystem from the next already-required runtime proof; do not start EC2 only for this measurement." } else { "Create a separate rollback-tested encrypted-volume migration plan; do not modify the attached source volume in place." })
}
if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $directory = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($directory)) { $null = New-Item -ItemType Directory -Force -Path $directory }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 12), $encoding)
}
$record | ConvertTo-Json -Depth 12
