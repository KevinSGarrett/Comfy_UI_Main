<#
.SYNOPSIS
Builds a local-only, rollback-first plan for replacing the approved EC2 root EBS volume.

.DESCRIPTION
Consumes hash-bound right-sizing readiness evidence. It never contacts AWS and
never creates, attaches, detaches, snapshots, starts, stops, or deletes a
resource. A ready plan still requires a separate reviewed execution procedure.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$ReadinessEvidenceFile,
  [string]$KmsKeyId = "alias/aws/ebs",
  [int]$SourceRetentionDays = 14,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
if ($SourceRetentionDays -lt 7 -or $SourceRetentionDays -gt 90) { throw "SourceRetentionDays must be between 7 and 90." }
if ($KmsKeyId -notmatch '^(alias/[A-Za-z0-9/_-]+|arn:aws[-a-z]*:kms:[a-z0-9-]+:[0-9]{12}:key/[A-Fa-f0-9-]+)$') { throw "KmsKeyId must be an AWS KMS alias or key ARN." }

function Resolve-ProjectFile {
  param([Parameter(Mandatory=$true)][string]$Path, [switch]$MustExist)
  $resolved = if ([System.IO.Path]::IsPathRooted($Path)) { [System.IO.Path]::GetFullPath($Path) } else { [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path)) }
  if (!$resolved.StartsWith($ProjectRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Path must remain inside ProjectRoot: $Path" }
  if ($MustExist -and !(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Required file is missing: $resolved" }
  return $resolved
}

function Relative-Path {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  return ([System.IO.Path]::GetFullPath($Path)).Substring($ProjectRoot.Length).TrimStart("\", "/").Replace("\", "/")
}

function Add-Check {
  param([string]$Name, [bool]$Passed, $Expected, $Observed)
  [void]$checks.Add([ordered]@{ name=$Name; result=$(if($Passed){"pass"}else{"fail"}); expected=$Expected; observed=$Observed })
}

$readinessPath = Resolve-ProjectFile -Path $ReadinessEvidenceFile -MustExist
$readiness = Get-Content -Raw -LiteralPath $readinessPath | ConvertFrom-Json
$readinessSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $readinessPath).Hash.ToLowerInvariant()
$readyClassifications = @("EBS_ENCRYPTED_RIGHT_SIZE_MIGRATION_PLANNING_READY", "EBS_ENCRYPTED_SAME_SIZE_MIGRATION_PLANNING_READY", "EBS_ENCRYPTED_CAPACITY_MIGRATION_PLANNING_READY")
$checks = New-Object System.Collections.ArrayList
Add-Check "readiness_result_pass" ([string]$readiness.result -ceq "pass") "pass" $readiness.result
Add-Check "readiness_classification_allows_planning" ($readyClassifications -contains [string]$readiness.classification) ($readyClassifications -join ",") $readiness.classification
Add-Check "approved_instance" ([string]$readiness.instance_id -ceq "i-0560bf8d143f93bb1") "i-0560bf8d143f93bb1" $readiness.instance_id
Add-Check "approved_region" ([string]$readiness.region -ceq "us-east-1") "us-east-1" $readiness.region
Add-Check "instance_stopped" ([string]$readiness.instance_state -ceq "stopped") "stopped" $readiness.instance_state
Add-Check "root_volume_identified" ([string]$readiness.volume_id -match '^vol-[0-9a-f]+$' -and [string]$readiness.root_device_name -match '^/dev/') "root volume and device" "$($readiness.volume_id) $($readiness.root_device_name)"
Add-Check "availability_zone_identified" ([string]$readiness.availability_zone -match '^us-east-1[a-z]$') "us-east-1 AZ" $readiness.availability_zone
Add-Check "filesystem_proof_valid" ([bool]$readiness.filesystem_proof_valid -and [string]$readiness.filesystem_evidence_sha256 -match '^[0-9a-f]{64}$') $true $readiness.filesystem_proof_valid
$targetRelationValid = switch ([string]$readiness.classification) {
  "EBS_ENCRYPTED_RIGHT_SIZE_MIGRATION_PLANNING_READY" { [int]$readiness.migration_target_size_gib -lt [int]$readiness.current_size_gib }
  "EBS_ENCRYPTED_SAME_SIZE_MIGRATION_PLANNING_READY" { [int]$readiness.migration_target_size_gib -eq [int]$readiness.current_size_gib }
  "EBS_ENCRYPTED_CAPACITY_MIGRATION_PLANNING_READY" { [int]$readiness.migration_target_size_gib -gt [int]$readiness.current_size_gib }
  default { $false }
}
Add-Check "target_size_valid" ([int]$readiness.migration_target_size_gib -gt 0 -and [int]$readiness.migration_target_size_gib -ge [int]$readiness.recommended_target_size_gib -and $targetRelationValid) "target satisfies recommendation and classification relation" $readiness.migration_target_size_gib
Add-Check "source_mutation_not_authorized" (![bool]$readiness.mutation_authorized) $false $readiness.mutation_authorized

$failures = @($checks | Where-Object { [string]$_.result -ne "pass" })
$planningReady = ($failures.Count -eq 0)
$targetSizeGiB = $(if ($planningReady) { [int]$readiness.migration_target_size_gib } else { $null })
$phases = @(
  [ordered]@{ order=1; name="freeze_source_identity"; action="Recheck the approved instance is stopped, the active runtime marker is absent, and the root volume ID still matches this hash-bound readiness record."; rollback="Abort without mutation on any drift." },
  [ordered]@{ order=2; name="create_rollback_snapshot"; action="Create and wait for a completed snapshot of the unmodified source root volume; record snapshot ID, source volume ID, tags, and hashes before proceeding."; rollback="Keep the source volume attached and abort if snapshot completion is not verified." },
  [ordered]@{ order=3; name="prepare_offline_copy_helper"; action="Use a separately approved same-AZ maintenance helper. Keep the approved GPU instance stopped; attach the source root to the helper and mount it read-only."; rollback="Detach the source from the helper and reattach it to the approved root device." },
  [ordered]@{ order=4; name="create_encrypted_target"; action="Create a blank gp3 target in the same AZ at the planned size with explicit KMS encryption, matching required IOPS and throughput; partition and format it on the helper."; rollback="Delete only the newly created target after confirming the source and snapshot remain intact." },
  [ordered]@{ order=5; name="offline_filesystem_copy"; action="Copy the stopped source filesystem to the target with ownership, ACLs, xattrs, hardlinks, sparse files, and boot metadata preserved; verify byte counts and a bounded integrity manifest."; rollback="Do not detach or delete the source when copy or integrity verification fails." },
  [ordered]@{ order=6; name="swap_root_volume"; action="Detach both helper volumes, attach the encrypted target to the approved instance at the original root device, preserve source volume and rollback snapshot, and keep delete-on-termination disabled during validation."; rollback="Stop the approved instance, detach the target, and restore the original source volume at the original root device." },
  [ordered]@{ order=7; name="bounded_boot_validation"; action="Start one bounded validation window; verify boot, SSM, filesystem size, encryption, ComfyUI paths, model hashes, and a non-generating service health check, then stop and verify stopped."; rollback="On any failed check, stop immediately and restore the original source root." },
  [ordered]@{ order=8; name="retention_and_cleanup"; action="Retain the detached source volume and completed snapshot for the declared rollback period. Delete them only after explicit acceptance and a second stopped-state verification."; rollback="Retention cleanup is irreversible and requires separate approval." }
)

$record = [ordered]@{
  schema_version="1.0"
  created_at=[datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  result=$(if($planningReady){"encrypted_volume_migration_plan_ready_for_review"}else{"blocked_ebs_migration_plan"})
  classification=$(if($planningReady){"EBS_ENCRYPTED_VOLUME_MIGRATION_PLAN_READY_FOR_REVIEW"}else{"BLOCKED_EBS_MIGRATION_READINESS_NOT_PROVEN"})
  local_only=$true
  aws_contacted=$false
  ec2_started=$false
  resource_mutation_performed=$false
  execution_authorized=$false
  readiness_evidence=Relative-Path $readinessPath
  readiness_evidence_sha256=$readinessSha256
  source=[ordered]@{ instance_id=$readiness.instance_id; region=$readiness.region; availability_zone=$readiness.availability_zone; root_device_name=$readiness.root_device_name; volume_id=$readiness.volume_id; size_gib=$readiness.current_size_gib; encrypted=$readiness.current_encrypted }
  target=[ordered]@{ size_gib=$targetSizeGiB; volume_type="gp3"; iops=$readiness.current_iops; throughput=$readiness.current_throughput; encrypted=$true; kms_key_id=$KmsKeyId }
  rollback=[ordered]@{ source_volume_retained=$true; completed_snapshot_required=$true; retention_days=$SourceRetentionDays; delete_on_termination_during_validation=$false; rollback_boot_proof_required=$true }
  checks=@($checks)
  failed_check_count=$failures.Count
  blockers=@($failures | ForEach-Object { $_.name })
  phases=$phases
  phase_count=$phases.Count
  next_action=$(if($planningReady){"Review and separately implement the bounded migration executor. Do not execute from this plan artifact alone."}else{"Resolve the failed readiness checks; do not create, attach, detach, snapshot, start, stop, or delete EBS resources."})
}

if ([string]::IsNullOrWhiteSpace($OutFile)) { $OutFile = Join-Path $ProjectRoot "runtime_artifacts\ebs_migration\EBS_ENCRYPTED_VOLUME_MIGRATION_PLAN.json" }
$OutFile = Resolve-ProjectFile -Path $OutFile
$directory = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($directory)) { $null = New-Item -ItemType Directory -Force -Path $directory }
[System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))
$record | ConvertTo-Json -Depth 20
