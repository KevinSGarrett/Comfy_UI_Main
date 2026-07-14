param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$FilesystemEvidenceFile = "",
  [double]$HeadroomMultiplier = 1.5,
  [int]$MinimumHeadroomGiB = 100,
  [int]$MaxEvidenceAgeHours = 168,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
if ($HeadroomMultiplier -lt 1.25 -or $HeadroomMultiplier -gt 3.0) { throw "HeadroomMultiplier must be between 1.25 and 3.0." }
if ($MinimumHeadroomGiB -lt 50 -or $MinimumHeadroomGiB -gt 500) { throw "MinimumHeadroomGiB must be between 50 and 500." }
if ($MaxEvidenceAgeHours -lt 1 -or $MaxEvidenceAgeHours -gt 720) { throw "MaxEvidenceAgeHours must be between 1 and 720." }

$instance = aws ec2 describe-instances --instance-ids $InstanceId --region $Region --query "Reservations[0].Instances[0]" --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Unable to read the approved instance." }
$rootMapping = @($instance.BlockDeviceMappings | Where-Object { [string]$_.DeviceName -ceq [string]$instance.RootDeviceName } | Select-Object -First 1)
if ($rootMapping.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$rootMapping[0].Ebs.VolumeId)) { throw "Unable to resolve the approved instance root volume mapping." }
$volumeId = [string]$rootMapping[0].Ebs.VolumeId
$volume = aws ec2 describe-volumes --volume-ids $volumeId --region $Region --query "Volumes[0]" --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Unable to read the approved EBS volume." }

$filesystem = $null
$filesystemEvidenceSha256 = $null
$filesystemEvidenceCreatedAt = $null
$filesystemEvidenceAgeHours = $null
$filesystemEvidenceInstanceMatch = $false
$filesystemEvidenceRegionMatch = $false
$filesystemEvidenceFinalStateStopped = $false
$filesystemEvidenceFresh = $false
if (![string]::IsNullOrWhiteSpace($FilesystemEvidenceFile) -and (Test-Path -LiteralPath $FilesystemEvidenceFile -PathType Leaf)) {
  $evidence = Get-Content -Raw -LiteralPath $FilesystemEvidenceFile | ConvertFrom-Json
  $filesystemEvidenceSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $FilesystemEvidenceFile).Hash.ToLowerInvariant()
  if ($null -ne $evidence.remote_result -and $null -ne $evidence.remote_result.root_filesystem) {
    $filesystem = $evidence.remote_result.root_filesystem
  } elseif ($null -ne $evidence.root_filesystem) {
    $filesystem = $evidence.root_filesystem
  }
  $filesystemEvidenceInstanceMatch = ([string]$evidence.instance_id -ceq $InstanceId)
  $filesystemEvidenceRegionMatch = ([string]$evidence.region -ceq $Region)
  $filesystemEvidenceFinalStateStopped = ([string]$evidence.final_state -ceq "stopped")
  try {
    $filesystemEvidenceCreatedAt = [datetimeoffset]::Parse([string]$evidence.created_at)
    $filesystemEvidenceAgeHours = [math]::Round(([datetimeoffset]::UtcNow - $filesystemEvidenceCreatedAt).TotalHours, 3)
    $filesystemEvidenceFresh = ($filesystemEvidenceAgeHours -ge 0 -and $filesystemEvidenceAgeHours -le $MaxEvidenceAgeHours)
  } catch {
    $filesystemEvidenceCreatedAt = $null
  }
}

$classification = "BLOCKED_EBS_USED_BYTES_PROOF_MISSING"
$recommendedGiB = $null
$migrationTargetGiB = $null
$filesystemProofValid = (
  $null -ne $filesystem -and
  [long]$filesystem.total_bytes -gt 0 -and
  [long]$filesystem.used_bytes -gt 0 -and
  [long]$filesystem.free_bytes -ge 0 -and
  [long]$filesystem.used_bytes -lt [long]$filesystem.total_bytes -and
  $filesystemEvidenceInstanceMatch -and
  $filesystemEvidenceRegionMatch -and
  $filesystemEvidenceFinalStateStopped -and
  $filesystemEvidenceFresh
)
if ([string]$instance.State.Name -ne "stopped") {
  $classification = "BLOCKED_EBS_INSTANCE_NOT_STOPPED"
} elseif ($filesystemProofValid) {
  $usedGiB = [math]::Ceiling([long]$filesystem.used_bytes / 1GB)
  $recommendedGiB = [int][math]::Ceiling([math]::Max($usedGiB * $HeadroomMultiplier, $usedGiB + $MinimumHeadroomGiB) / 10) * 10
  if ($recommendedGiB -gt [int]$volume.Size) {
    $migrationTargetGiB = $recommendedGiB
    $classification = $(if ([bool]$volume.Encrypted) { "EBS_IN_PLACE_CAPACITY_EXPANSION_REVIEW_REQUIRED" } else { "EBS_ENCRYPTED_CAPACITY_MIGRATION_PLANNING_READY" })
  } elseif ($recommendedGiB -eq [int]$volume.Size) {
    $migrationTargetGiB = [int]$volume.Size
    $classification = $(if ([bool]$volume.Encrypted) { "EBS_ENCRYPTED_RIGHT_SIZING_COMPLETE" } else { "EBS_ENCRYPTED_SAME_SIZE_MIGRATION_PLANNING_READY" })
  } else {
    $migrationTargetGiB = $recommendedGiB
    $classification = $(if ([bool]$volume.Encrypted -and [int]$volume.Size -eq $recommendedGiB) { "EBS_ENCRYPTED_RIGHT_SIZING_COMPLETE" } else { "EBS_ENCRYPTED_RIGHT_SIZE_MIGRATION_PLANNING_READY" })
  }
}

$record = [ordered]@{
  schema_version = "1.0"
  created_at = [datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  result = "pass"
  classification = $classification
  instance_id = $InstanceId
  instance_state = [string]$instance.State.Name
  availability_zone = [string]$instance.Placement.AvailabilityZone
  root_device_name = [string]$instance.RootDeviceName
  volume_id = $volumeId
  current_size_gib = [int]$volume.Size
  current_volume_type = [string]$volume.VolumeType
  current_encrypted = [bool]$volume.Encrypted
  current_iops = [int]$volume.Iops
  current_throughput = [int]$volume.Throughput
  current_delete_on_termination = [bool]$rootMapping[0].Ebs.DeleteOnTermination
  filesystem_evidence_file = $FilesystemEvidenceFile
  filesystem_evidence_sha256 = $filesystemEvidenceSha256
  filesystem_evidence_created_at = $(if ($null -ne $filesystemEvidenceCreatedAt) { $filesystemEvidenceCreatedAt.ToString("yyyy-MM-ddTHH:mm:ssZ") } else { $null })
  filesystem_evidence_age_hours = $filesystemEvidenceAgeHours
  filesystem_evidence_max_age_hours = $MaxEvidenceAgeHours
  filesystem_evidence_instance_match = $filesystemEvidenceInstanceMatch
  filesystem_evidence_region_match = $filesystemEvidenceRegionMatch
  filesystem_evidence_final_state_stopped = $filesystemEvidenceFinalStateStopped
  filesystem_evidence_fresh = $filesystemEvidenceFresh
  filesystem_proof_valid = $filesystemProofValid
  filesystem = $filesystem
  recommended_target_size_gib = $recommendedGiB
  migration_target_size_gib = $migrationTargetGiB
  target_encryption_required = $true
  in_place_shrink_supported = $false
  mutation_authorized = $false
  next_action = $(if ($classification -eq "BLOCKED_EBS_INSTANCE_NOT_STOPPED") { "Wait for the owned runtime window to stop and complete before evaluating migration readiness." } elseif ($classification -eq "BLOCKED_EBS_USED_BYTES_PROOF_MISSING") { "Capture hash-bound root_filesystem evidence from the next already-required runtime proof; do not start EC2 only for this measurement." } else { "Create a separate rollback-tested encrypted-volume migration plan; do not modify the attached source volume in place." })
}
if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $directory = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($directory)) { $null = New-Item -ItemType Directory -Force -Path $directory }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 12), $encoding)
}
$record | ConvertTo-Json -Depth 12
