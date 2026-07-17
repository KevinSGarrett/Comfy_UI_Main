<#
.SYNOPSIS
Validates batched EC2 runtime admission and caller-owned lifecycle contracts.

.DESCRIPTION
Creates temporary local-only run packages and never contacts AWS, starts EC2,
posts a prompt, or mutates Git. Negative cases run the coordinator in a child
PowerShell process because fail-closed admission returns a nonzero exit code.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$coordinator = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2BatchedRuntimeWindow.ps1"
$workOrderBuilder = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-EC2BatchedRuntimeWorkOrder.ps1"
$safetyGate = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\EC2RuntimeWindowSafetyGate.ps1"
$staticProof = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1"
$smoke = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1"
$dispositionScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Get-EC2RuntimeReadinessDisposition.ps1"
$capacityBackoff = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Set-EC2CapacityBackoffState.ps1"
$s3Infrastructure = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Initialize-S3RuntimeInfrastructure.ps1"
foreach ($path in @($coordinator,$workOrderBuilder,$safetyGate,$staticProof,$smoke,$dispositionScript,$capacityBackoff,$s3Infrastructure)) {
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required batch runtime file is missing: $path" }
}
. $safetyGate

$encoding = New-Object System.Text.UTF8Encoding($false)
$tempRoot = Join-Path $ProjectRoot "runtime_artifacts\regression\ec2_batched_runtime_$([guid]::NewGuid().ToString('N'))"
$fixtureProjectRoot = Join-Path $tempRoot "project"
$laneId = "sdxl_realvisxl_controlnet_openpose_lane"
$checks = New-Object System.Collections.ArrayList
function Add-Check([string]$Name, [bool]$Passed, $Expected, $Observed) {
  [void]$checks.Add([ordered]@{ name=$Name; result=$(if($Passed){"pass"}else{"fail"}); expected=$Expected; observed=$Observed })
}
function Write-Json([object]$Value, [string]$Path, [int]$Depth=30) {
  $directory = Split-Path -Parent $Path
  $null = New-Item -ItemType Directory -Force -Path $directory
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}
function Invoke-Coordinator([string]$ExecutionProjectRoot, [string]$WorkOrderPath, [string]$AuthPath, [string]$ReadinessPath, [string]$ResultDir) {
  $command = "& '$($coordinator -replace "'", "''")' -ProjectRoot '$($ExecutionProjectRoot -replace "'", "''")' -WorkOrderFile '$($WorkOrderPath -replace "'", "''")' -AuthGateFile '$($AuthPath -replace "'", "''")' -ReadinessFile '$($ReadinessPath -replace "'", "''")' -RuntimeWindowId 'rw-batch-regression-0001' -OutDirectory '$($ResultDir -replace "'", "''")'"
  $bytes = [System.Text.Encoding]::Unicode.GetBytes($command)
  $encoded = [Convert]::ToBase64String($bytes)
  $output = @(& powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded 2>&1)
  return [pscustomobject]@{ exit_code=$LASTEXITCODE; output=(($output | ForEach-Object {[string]$_}) -join "`n") }
}

try {
  $null = New-Item -ItemType Directory -Force -Path $fixtureProjectRoot
  [System.IO.File]::WriteAllText((Join-Path $fixtureProjectRoot ".gitignore"), "runtime_artifacts/`n", $encoding)
  & git -C $fixtureProjectRoot init -b main | Out-Null
  & git -C $fixtureProjectRoot config user.email "batch-regression@example.invalid"
  & git -C $fixtureProjectRoot config user.name "EC2 Batch Regression"
  & git -C $fixtureProjectRoot add .gitignore
  & git -C $fixtureProjectRoot commit -m "Initialize clean regression fixture" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Unable to initialize clean Git regression fixture." }
  $fixtureHead = (& git -C $fixtureProjectRoot rev-parse HEAD).Trim()
  & git -C $fixtureProjectRoot update-ref refs/remotes/origin/main $fixtureHead
  if ($LASTEXITCODE -ne 0) { throw "Unable to bind fixture origin/main." }

  $unitManifestPaths = @()
  foreach ($index in 1..2) {
    $unitDir = Join-Path $fixtureProjectRoot "runtime_artifacts\unit-$index"
    $promptPath = Join-Path $unitDir "prompt_request.json"
    $prompt = [ordered]@{ client_id="batch-regression-$index"; prompt=[ordered]@{ "1"=[ordered]@{ class_type="SaveImage"; inputs=[ordered]@{ filename_prefix="batch-regression-$index"; images=@("2",0) } } } }
    Write-Json $prompt $promptPath
    $promptHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $promptPath).Hash.ToLowerInvariant()
    $relativePrompt = $promptPath.Substring($fixtureProjectRoot.Length).TrimStart("\").Replace("\","/")
    $manifestPath = Join-Path $unitDir "RUN_PACKAGE_MANIFEST.json"
    $manifest = [ordered]@{
      schema_version="1.0"; run_id="batch-regression-unit-$index"; lane_id=$laneId; result="pass_local_only"; local_only=$true
      aws_contacted=$false; ec2_started=$false; generation_executed=$false; requires_gold_masks=$false
      generated_files=@([ordered]@{ path=$relativePrompt; sha256=$promptHash; purpose="Bounded prompt request." })
      prompt_request=[ordered]@{ client_id="batch-regression-$index"; node_count=1; sha256=$promptHash }
    }
    Write-Json $manifest $manifestPath
    $unitManifestPaths += $manifestPath
  }

  $authPath = Join-Path $fixtureProjectRoot "runtime_artifacts\auth.json"
  Write-Json ([ordered]@{ result="pass"; account_actual="029530099913"; account_match=$true; ec2_work_allowed=$true; safe_to_start_ec2=$true; generation_allowed=$true }) $authPath
  $readinessPath = Join-Path $fixtureProjectRoot "runtime_artifacts\readiness.json"
  Write-Json ([ordered]@{ result="ready_for_ec2_static_proof"; lane_id=$laneId; local_pre_ec2_ready=$true; ready_for_ec2_static_proof=$true; ready_for_generation=$false }) $readinessPath
  $workOrderPath = Join-Path $fixtureProjectRoot "runtime_artifacts\READY_GPU_WORK.json"
  & $workOrderBuilder -ProjectRoot $fixtureProjectRoot -WorkOrderId "batch-regression-work-order" -LaneId $laneId -DeployBundleS3Uri "s3://example-bucket/deploy-bundles/batch.zip" -DeployBundleSha256 ("a"*64) -UnitManifestFiles $unitManifestPaths -MaxRuntimeMinutes 45 -ExpiresAfterMinutes 60 -OutFile $workOrderPath | Out-Null

  $validResultDir = Join-Path $fixtureProjectRoot "runtime_artifacts\valid-result"
  $validRun = Invoke-Coordinator -ExecutionProjectRoot $fixtureProjectRoot -WorkOrderPath $workOrderPath -AuthPath $authPath -ReadinessPath $readinessPath -ResultDir $validResultDir
  $validRecordPath = Join-Path $validResultDir "BATCH_RUNTIME_EXECUTION.json"
  $validRecord = Get-Content -Raw -LiteralPath $validRecordPath | ConvertFrom-Json
  Add-Check "valid_two_unit_batch_admitted" ($validRun.exit_code -eq 0 -and [string]$validRecord.result -eq "batch_runtime_ready_local_only" -and [int]$validRecord.unit_count -eq 2) "exit=0, ready, unit_count=2" "exit=$($validRun.exit_code), result=$($validRecord.result), units=$($validRecord.unit_count)"
  Add-Check "dry_run_has_no_external_effects" (!$validRecord.execute -and !$validRecord.aws_contacted -and !$validRecord.ec2_started -and !$validRecord.generation_executed) "all false" "execute=$($validRecord.execute), aws=$($validRecord.aws_contacted), ec2=$($validRecord.ec2_started), generation=$($validRecord.generation_executed)"

  $unit2PromptPath = Join-Path $fixtureProjectRoot "runtime_artifacts\unit-2\prompt_request.json"
  $unit2PromptOriginal = Get-Content -Raw -LiteralPath $unit2PromptPath
  Add-Content -LiteralPath $unit2PromptPath -Value " "
  $tamperResultDir = Join-Path $fixtureProjectRoot "runtime_artifacts\tamper-result"
  $tamperRun = Invoke-Coordinator -ExecutionProjectRoot $fixtureProjectRoot -WorkOrderPath $workOrderPath -AuthPath $authPath -ReadinessPath $readinessPath -ResultDir $tamperResultDir
  $tamperRecord = Get-Content -Raw -LiteralPath (Join-Path $tamperResultDir "BATCH_RUNTIME_EXECUTION.json") | ConvertFrom-Json
  Add-Check "tampered_prompt_rejected" ($tamperRun.exit_code -ne 0 -and [string]$tamperRecord.result -eq "blocked_before_ec2_start" -and (@($tamperRecord.validation_errors | Where-Object { $_ -match "prompt-request hash mismatch" }).Count -eq 1)) "blocked hash mismatch" "exit=$($tamperRun.exit_code), errors=$($tamperRecord.validation_errors -join '; ')"
  [System.IO.File]::WriteAllText($unit2PromptPath, $unit2PromptOriginal, $encoding)

  $expired = Get-Content -Raw -LiteralPath $workOrderPath | ConvertFrom-Json
  $expired.expires_at = [datetimeoffset]::UtcNow.AddMinutes(-5).ToString("yyyy-MM-ddTHH:mm:ssZ")
  $expiredPath = Join-Path $fixtureProjectRoot "runtime_artifacts\EXPIRED_GPU_WORK.json"
  Write-Json $expired $expiredPath
  $expiredResultDir = Join-Path $fixtureProjectRoot "runtime_artifacts\expired-result"
  $expiredRun = Invoke-Coordinator -ExecutionProjectRoot $fixtureProjectRoot -WorkOrderPath $expiredPath -AuthPath $authPath -ReadinessPath $readinessPath -ResultDir $expiredResultDir
  $expiredRecord = Get-Content -Raw -LiteralPath (Join-Path $expiredResultDir "BATCH_RUNTIME_EXECUTION.json") | ConvertFrom-Json
  Add-Check "expired_work_order_rejected" ($expiredRun.exit_code -ne 0 -and @($expiredRecord.validation_errors | Where-Object { $_ -eq "Work order is expired." }).Count -eq 1) "expired rejected" "exit=$($expiredRun.exit_code), errors=$($expiredRecord.validation_errors -join '; ')"

  foreach ($stateCase in @(
    [ordered]@{ status="READY_WORK_WAITING_FOR_EC2"; result="pass_local_only"; expected="READY_WORK_WAITING_FOR_EC2" },
    [ordered]@{ status="EXECUTING"; result="pass_local_only"; expected="GPU_RUNTIME_WINDOW_STARTING" },
    [ordered]@{ status="COMPLETED"; result="batch_runtime_generation_and_pullback_complete"; expected="NO_ELIGIBLE_GPU_WORK" },
    [ordered]@{ status="FAILED_CLOSED"; result="batch_runtime_failed_closed"; expected="BLOCKED_FAILED_GPU_WORK_ORDER" }
  )) {
    $stateWorkOrder = Get-Content -Raw -LiteralPath $workOrderPath | ConvertFrom-Json
    $stateWorkOrder.status = $stateCase.status
    $stateWorkOrder.result = $stateCase.result
    $statePath = Join-Path $fixtureProjectRoot ("runtime_artifacts\state-{0}.json" -f $stateCase.status)
    Write-Json $stateWorkOrder $statePath
    $disposition = & $dispositionScript -ProjectRoot $fixtureProjectRoot -WorkOrderFile $statePath | ConvertFrom-Json
    Add-Check ("dispatcher_state_{0}" -f $stateCase.status.ToLowerInvariant()) ([string]$disposition.classification -eq $stateCase.expected) $stateCase.expected $disposition.classification
  }

  $markerProject = Join-Path $tempRoot "marker-project"
  $markerDir = Join-Path $markerProject "runtime_artifacts\ec2_runtime_windows"
  $null = New-Item -ItemType Directory -Force -Path $markerDir
  $markerPath = Join-Path $markerDir "ACTIVE_EC2_RUNTIME_WINDOW.json"
  $marker = [ordered]@{ schema_version="2.0"; window_id="rw-batch-regression-0001"; status="ACTIVE"; expires_at=[datetimeoffset]::UtcNow.AddMinutes(30).ToString("o"); instance_id="i-0560bf8d143f93bb1"; region="us-east-1"; target_lane_id=$laneId; deploy_bundle_s3_uri="s3://example-bucket/deploy-bundles/batch.zip"; deploy_bundle_sha256=("a"*64) }
  Write-Json $marker $markerPath
  $markerOk = Get-ActiveRuntimeWindowStatus -ProjectRoot $markerProject -ExpectedWindowId $marker.window_id -ExpectedLaneId $laneId -ExpectedInstanceId $marker.instance_id -ExpectedRegion $marker.region -ExpectedDeployBundleS3Uri $marker.deploy_bundle_s3_uri -ExpectedDeployBundleSha256 $marker.deploy_bundle_sha256
  $markerWrongLane = Get-ActiveRuntimeWindowStatus -ProjectRoot $markerProject -ExpectedWindowId $marker.window_id -ExpectedLaneId "wrong-lane" -ExpectedInstanceId $marker.instance_id -ExpectedRegion $marker.region -ExpectedDeployBundleS3Uri $marker.deploy_bundle_s3_uri -ExpectedDeployBundleSha256 $marker.deploy_bundle_sha256
  Add-Check "active_marker_exact_match_passes" ([bool]$markerOk.verified) $true $markerOk.verified
  Add-Check "active_marker_lane_mismatch_fails" (![bool]$markerWrongLane.verified -and !$markerWrongLane.checks.lane_match) $true $markerWrongLane.verified

  $coordinatorSource = Get-Content -Raw -LiteralPath $coordinator
  $capacityBackoffSource = Get-Content -Raw -LiteralPath $capacityBackoff
  $s3InfrastructureSource = Get-Content -Raw -LiteralPath $s3Infrastructure
  $staticSource = Get-Content -Raw -LiteralPath $staticProof
  $smokeSource = Get-Content -Raw -LiteralPath $smoke
  Add-Check "coordinator_finally_stops_instance" ($coordinatorSource -match '(?s)finally\s*\{.*?aws ec2 stop-instances.*?Wait-InstanceState -DesiredState "stopped"') $true ($coordinatorSource -match 'aws ec2 stop-instances')
  Add-Check "marker_completion_requires_stopped" ($coordinatorSource -match '\$markerActivated -and \$record\.final_state -eq "stopped"') $true ($coordinatorSource -match '\$markerActivated -and \$record\.final_state -eq "stopped"')
  Add-Check "static_child_cannot_stop_caller_window" ($staticSource -match '!\$CallerManagedRuntimeWindow -and \$currentState -ne "stopped"') $true ($staticSource -match '!\$CallerManagedRuntimeWindow -and \$currentState -ne "stopped"')
  Add-Check "smoke_child_cannot_stop_caller_window" ($smokeSource -match '\$shouldStopInstance = \(!\$CallerManagedRuntimeWindow -and') $true ($smokeSource -match '\$shouldStopInstance = \(!\$CallerManagedRuntimeWindow -and')
  Add-Check "children_verify_inherited_marker" (($staticSource -match 'Get-ActiveRuntimeWindowStatus') -and ($smokeSource -match 'Get-ActiveRuntimeWindowStatus')) $true "static=$($staticSource -match 'Get-ActiveRuntimeWindowStatus'), smoke=$($smokeSource -match 'Get-ActiveRuntimeWindowStatus')"
  Add-Check "static_child_preflight_throws_to_coordinator" ($staticSource -match 'if \(\$CallerManagedRuntimeWindow\) \{ throw "Caller-managed EC2 static proof was blocked before execution') $true ($staticSource -match 'Caller-managed EC2 static proof was blocked before execution')
  Add-Check "smoke_child_preflight_throws_to_coordinator" ($smokeSource -match 'if \(\$CallerManagedRuntimeWindow\) \{ throw "Caller-managed EC2 workflow smoke was blocked before execution') $true ($smokeSource -match 'Caller-managed EC2 workflow smoke was blocked before execution')
  Add-Check "identity_helper_isolated_from_parent_host" ($coordinatorSource -match '& powershell[^\r\n]+\$identityScript') $true ($coordinatorSource -match '& powershell[^\r\n]+\$identityScript')
  $instanceTypePropagated = (
    $coordinatorSource -match '\[string\]\$ExpectedInstanceType\s*=\s*"g5\.xlarge"' -and
    $coordinatorSource -match '-ExpectedType\s+\$ExpectedInstanceType' -and
    $coordinatorSource -match 'ExpectedInstanceType=\$ExpectedInstanceType' -and
    $staticSource -match '\[string\]\$ExpectedInstanceType\s*=\s*"g5\.xlarge"' -and
    $staticSource -match '-ExpectedType\s+\$ExpectedInstanceType'
  )
  Add-Check "approved_instance_type_is_explicitly_propagated" $instanceTypePropagated $true $instanceTypePropagated
  Add-Check "post_stop_ebs_gate_wired" ($coordinatorSource -match 'Test-EC2EbsRightSizingReadiness\.ps1') $true ($coordinatorSource -match 'Test-EC2EbsRightSizingReadiness\.ps1')
  Add-Check "ebs_evidence_binds_stopped_batch_window" ($coordinatorSource -match 'EBS_FILESYSTEM_EVIDENCE\.json' -and $coordinatorSource -match 'final_state=\$record\.final_state' -and $coordinatorSource -match 'source_smoke_record_sha256') $true ($coordinatorSource -match 'EBS_FILESYSTEM_EVIDENCE\.json')
  Add-Check "work_order_state_machine_wired" (($coordinatorSource -match '"EXECUTING"') -and ($coordinatorSource -match '"COMPLETED"') -and ($coordinatorSource -match '"FAILED_CLOSED"') -and ($coordinatorSource -match '"READY_WORK_WAITING_FOR_EC2"')) $true "executing=$($coordinatorSource -match '"EXECUTING"'), completed=$($coordinatorSource -match '"COMPLETED"'), failed=$($coordinatorSource -match '"FAILED_CLOSED"')"
  $carriesForwardPullbackExclusion = (
    $coordinatorSource -match '\$runtimeGeneratedGitExcludePaths\s*=\s*@\(\$PreservedGitExcludePath\)' -and
    $coordinatorSource -match 'PreservedGitExcludePath=\$runtimeGeneratedGitExcludePaths' -and
    $coordinatorSource -match '\$pullbackPath\s*=\s*\[string\]\$smoke\.local_pullback\.local_destination' -and
    $coordinatorSource -match '\$runtimeGeneratedGitExcludePaths\s*\+=\s*\$pullbackPath'
  )
  Add-Check "completed_unit_pullback_is_preserved_for_later_git_gates" $carriesForwardPullbackExclusion $true $carriesForwardPullbackExclusion
  $requiresConcretePullbackDestination = $coordinatorSource -match '\[string\]::IsNullOrWhiteSpace\(\$pullbackPath\)'
  Add-Check "successful_pullback_requires_concrete_destination" $requiresConcretePullbackDestination $true $requiresConcretePullbackDestination
  Add-Check "capacity_backoff_binds_work_order_id" ($coordinatorSource -match 'RecordFailure[^\r\n]+RuntimeWorkOrderId \(\[string\]\$workOrder\.work_order_id\)') $true ($coordinatorSource -match 'RuntimeWorkOrderId \(\[string\]\$workOrder\.work_order_id\)')
  $coordinatorClearReason = [regex]::Match($coordinatorSource, '-Action Clear[^\r\n]+-ClearReason\s+"([^"]+)"').Groups[1].Value
  Add-Check "capacity_backoff_clear_reason_matches_helper_contract" (($coordinatorClearReason -ceq "ec2_start_succeeded") -and ($capacityBackoffSource -match '"ec2_start_succeeded"')) "ec2_start_succeeded" $coordinatorClearReason
  $coordinatorS3Prefix = [regex]::Match($coordinatorSource, '\[string\]\$S3Prefix\s*=\s*"([^"]+)"').Groups[1].Value
  $infrastructureArtifactPrefix = [regex]::Match($s3InfrastructureSource, '\[string\]\$ArtifactPrefix\s*=\s*"([^"]+)"').Groups[1].Value
  Add-Check "batch_artifact_prefix_matches_runtime_s3_contract" (($coordinatorS3Prefix -ceq "$infrastructureArtifactPrefix/batched-runtime") -and ($infrastructureArtifactPrefix -ceq "render-outputs")) "render-outputs/batched-runtime" $coordinatorS3Prefix
} finally {
  if (Test-Path -LiteralPath $tempRoot -PathType Container) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}

$failures = @($checks | Where-Object { [string]$_.result -ne "pass" })
$record = [ordered]@{
  schema_version="1.0"; created_at=[datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  result=$(if($failures.Count -eq 0){"pass_local_only"}else{"fail"}); local_only=$true; aws_contacted=$false; ec2_started=$false; generation_executed=$false
  check_count=$checks.Count; failed_check_count=$failures.Count; checks=@($checks); failures=@($failures)
}
if ([string]::IsNullOrWhiteSpace($OutFile)) { $OutFile = Join-Path $ProjectRoot "runtime_artifacts\validation\EC2_BATCHED_RUNTIME_COORDINATOR_REGRESSION.json" }
Write-Json $record $OutFile 30
$record | ConvertTo-Json -Depth 30
if ($failures.Count -gt 0) { exit 2 }
