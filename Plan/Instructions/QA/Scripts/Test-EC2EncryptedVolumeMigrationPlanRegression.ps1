<#
.SYNOPSIS
Validates the local-only encrypted EBS migration-plan contract.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$generator = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-EC2EncryptedVolumeMigrationPlan.ps1"
if (!(Test-Path -LiteralPath $generator -PathType Leaf)) { throw "Migration-plan generator is missing." }
$tempRoot = Join-Path $ProjectRoot "runtime_artifacts\regression\ebs_migration_plan_$([guid]::NewGuid().ToString('N'))"
$encoding = New-Object System.Text.UTF8Encoding($false)
$checks = New-Object System.Collections.ArrayList
function Write-Json([object]$Value,[string]$Path) { $null=New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path); [System.IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 20),$encoding) }
function Add-Check([string]$Name,[bool]$Pass,$Expected,$Observed) { [void]$checks.Add([ordered]@{name=$Name;result=$(if($Pass){"pass"}else{"fail"});expected=$Expected;observed=$Observed}) }

try {
  $base = [ordered]@{
    schema_version="1.0"; result="pass"; classification="EBS_ENCRYPTED_RIGHT_SIZE_MIGRATION_PLANNING_READY"
    instance_id="i-0560bf8d143f93bb1"; region="us-east-1"; instance_state="stopped"; availability_zone="us-east-1d"
    root_device_name="/dev/sda1"; volume_id="vol-0eb9b2c6d3d2706d6"; current_size_gib=1024; current_encrypted=$false
    current_iops=3000; current_throughput=125; recommended_target_size_gib=420; migration_target_size_gib=420
    filesystem_proof_valid=$true; filesystem_evidence_sha256=("a"*64); mutation_authorized=$false
  }
  $readyPath=Join-Path $tempRoot "ready.json"; Write-Json $base $readyPath
  $readyOut=Join-Path $tempRoot "ready-plan.json"
  $ready=& $generator -ProjectRoot $ProjectRoot -ReadinessEvidenceFile $readyPath -OutFile $readyOut | ConvertFrom-Json
  Add-Check "ready_plan_admitted" ([string]$ready.result -eq "encrypted_volume_migration_plan_ready_for_review" -and [int]$ready.failed_check_count -eq 0) "ready, zero failures" "$($ready.result), $($ready.failed_check_count)"
  Add-Check "ready_plan_has_eight_phases" ([int]$ready.phase_count -eq 8 -and @($ready.phases).Count -eq 8) 8 $ready.phase_count
  Add-Check "ready_plan_preserves_rollback" ([bool]$ready.rollback.source_volume_retained -and [bool]$ready.rollback.completed_snapshot_required -and [bool]$ready.rollback.rollback_boot_proof_required) $true ($ready.rollback|ConvertTo-Json -Compress)
  Add-Check "ready_plan_never_authorizes_execution" (!$ready.execution_authorized -and !$ready.aws_contacted -and !$ready.ec2_started -and !$ready.resource_mutation_performed) "all false" "execute=$($ready.execution_authorized), aws=$($ready.aws_contacted), ec2=$($ready.ec2_started), mutation=$($ready.resource_mutation_performed)"
  Add-Check "target_is_encrypted_and_sized" ([bool]$ready.target.encrypted -and [int]$ready.target.size_gib -eq 420 -and [string]$ready.target.kms_key_id -eq "alias/aws/ebs") "encrypted 420 GiB" "$($ready.target.encrypted) $($ready.target.size_gib) $($ready.target.kms_key_id)"
  Add-Check "readiness_hash_bound" ([string]$ready.readiness_evidence_sha256 -eq (Get-FileHash -Algorithm SHA256 -LiteralPath $readyPath).Hash.ToLowerInvariant()) $true $ready.readiness_evidence_sha256

  $sameSize=[ordered]@{};foreach($k in $base.Keys){$sameSize[$k]=$base[$k]};$sameSize.classification="EBS_ENCRYPTED_SAME_SIZE_MIGRATION_PLANNING_READY";$sameSize.recommended_target_size_gib=1024;$sameSize.migration_target_size_gib=1024
  $sameSizePath=Join-Path $tempRoot "same-size.json";Write-Json $sameSize $sameSizePath
  $sameSizePlan=& $generator -ProjectRoot $ProjectRoot -ReadinessEvidenceFile $sameSizePath -OutFile (Join-Path $tempRoot "same-size-plan.json") | ConvertFrom-Json
  Add-Check "same_size_encryption_plan_admitted" ([string]$sameSizePlan.result -eq "encrypted_volume_migration_plan_ready_for_review" -and [int]$sameSizePlan.target.size_gib -eq 1024) "ready 1024 GiB" "$($sameSizePlan.result) $($sameSizePlan.target.size_gib)"

  $capacity=[ordered]@{};foreach($k in $base.Keys){$capacity[$k]=$base[$k]};$capacity.classification="EBS_ENCRYPTED_CAPACITY_MIGRATION_PLANNING_READY";$capacity.recommended_target_size_gib=1200;$capacity.migration_target_size_gib=1200
  $capacityPath=Join-Path $tempRoot "capacity.json";Write-Json $capacity $capacityPath
  $capacityPlan=& $generator -ProjectRoot $ProjectRoot -ReadinessEvidenceFile $capacityPath -OutFile (Join-Path $tempRoot "capacity-plan.json") | ConvertFrom-Json
  Add-Check "capacity_encryption_plan_admitted" ([string]$capacityPlan.result -eq "encrypted_volume_migration_plan_ready_for_review" -and [int]$capacityPlan.target.size_gib -eq 1200) "ready 1200 GiB" "$($capacityPlan.result) $($capacityPlan.target.size_gib)"

  $running=[ordered]@{}; foreach($k in $base.Keys){$running[$k]=$base[$k]}; $running.instance_state="running"
  $runningPath=Join-Path $tempRoot "running.json";Write-Json $running $runningPath
  $runningPlan=& $generator -ProjectRoot $ProjectRoot -ReadinessEvidenceFile $runningPath -OutFile (Join-Path $tempRoot "running-plan.json") | ConvertFrom-Json
  Add-Check "running_instance_rejected" ([string]$runningPlan.result -eq "blocked_ebs_migration_plan" -and @($runningPlan.blockers)-contains "instance_stopped") "blocked instance_stopped" ($runningPlan.blockers -join ',')

  $undersized=[ordered]@{};foreach($k in $base.Keys){$undersized[$k]=$base[$k]};$undersized.migration_target_size_gib=300
  $undersizedPath=Join-Path $tempRoot "undersized.json";Write-Json $undersized $undersizedPath
  $undersizedPlan=& $generator -ProjectRoot $ProjectRoot -ReadinessEvidenceFile $undersizedPath -OutFile (Join-Path $tempRoot "undersized-plan.json") | ConvertFrom-Json
  Add-Check "undersized_target_rejected" ([string]$undersizedPlan.result -eq "blocked_ebs_migration_plan" -and @($undersizedPlan.blockers)-contains "target_size_valid") "blocked target_size_valid" ($undersizedPlan.blockers -join ',')

  $source=Get-Content -Raw -LiteralPath $generator
  Add-Check "plan_requires_offline_source_copy" ($source -match 'mount it read-only' -and $source -match 'offline_filesystem_copy') $true ($source -match 'offline_filesystem_copy')
  Add-Check "plan_forbids_irreversible_early_cleanup" ($source -match 'Retention cleanup is irreversible and requires separate approval') $true ($source -match 'Retention cleanup is irreversible')
} finally {
  if(Test-Path -LiteralPath $tempRoot){Remove-Item -LiteralPath $tempRoot -Recurse -Force}
}

$failures=@($checks|Where-Object{$_.result-ne"pass"})
$record=[ordered]@{schema_version="1.0";created_at=[datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");result=$(if($failures.Count-eq0){"pass_local_only"}else{"fail"});local_only=$true;aws_contacted=$false;ec2_started=$false;resource_mutation_performed=$false;check_count=$checks.Count;failed_check_count=$failures.Count;checks=@($checks);failures=@($failures)}
if([string]::IsNullOrWhiteSpace($OutFile)){$OutFile=Join-Path $ProjectRoot "runtime_artifacts\validation\EC2_ENCRYPTED_VOLUME_MIGRATION_PLAN_REGRESSION.json"}
Write-Json $record $OutFile
$record|ConvertTo-Json -Depth 20
if($failures.Count-gt0){exit 2}
