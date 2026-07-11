<#
.SYNOPSIS
Validates the mirrored Flux1 Dev API workflow and its fail-closed asset boundary.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param([object]$Value, [string]$Path, [int]$Depth = 24)
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) { [IO.Directory]::CreateDirectory($parent) | Out-Null }
  [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))
}

function Add-Check {
  param([Collections.ArrayList]$Checks, [string]$Name, [bool]$Passed, [object]$Observed = $null)
  [void]$Checks.Add([ordered]@{ name = $Name; passed = $Passed; result = $(if ($Passed) { "pass" } else { "fail" }); observed = $Observed })
}

function Read-Json {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  try { return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json } catch { return $null }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "Project root not found: $ProjectRoot" }
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$planLane = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\flux1_dev_primary_base"
$runtimeLane = Join-Path $ProjectRoot "Workflows\base_generation\flux1_dev_primary_base"
$staticValidator = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1"
$objectInfoPath = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\BASE_GENERATION_RUN_PACKAGE_OBJECT_INFO_SNAPSHOT_20260709T005603-0500.json"
$assetEvidencePath = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_FLUX1_DEV_ASSET_AUTHORITY_20260710T222500-0500.json"
$installDryRunPath = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_FLUX1_DEV_LICENSED_INSTALL_DRY_RUN_20260710T224500-0500.json"
$installRegressionPath = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_LICENSED_MODEL_INSTALL_REGRESSION_20260710T224500-0500.json"
$installerScriptPath = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Install-LicensedModelFromHttp.ps1"
$installerRegressionScriptPath = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-LicensedModelInstallRegression.ps1"
$acceptanceTemplatePath = Join-Path $ProjectRoot "Plan\Instructions\Operations\Templates\flux1_dev_license_acceptance.template.json"
$activePath = Join-Path $ProjectRoot "Workflows\base_generation\ACTIVE_LANES.json"
$queuePath = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json"
$registryPath = Join-Path $ProjectRoot "Plan\10_REGISTRIES\wave15_image_base_lane_registry.json"
$files = @("workflow.api.json", "patch_points.json", "runtime_requirements.json", "smoke_test_request.json")
$checks = New-Object Collections.ArrayList

foreach ($name in $files) {
  $planPath = Join-Path $planLane $name
  $runtimePath = Join-Path $runtimeLane $name
  $planExists = Test-Path -LiteralPath $planPath -PathType Leaf
  $runtimeExists = Test-Path -LiteralPath $runtimePath -PathType Leaf
  Add-Check $checks "${name}_both_mirrors_exist" ($planExists -and $runtimeExists) ([ordered]@{ plan = $planExists; workflows = $runtimeExists })
  $hashMatch = $planExists -and $runtimeExists -and (Get-FileHash $planPath -Algorithm SHA256).Hash -eq (Get-FileHash $runtimePath -Algorithm SHA256).Hash
  Add-Check $checks "${name}_mirror_hash_matches" $hashMatch
}

$temp = Join-Path ([IO.Path]::GetTempPath()) ("flux1_dev_contract_" + [guid]::NewGuid().ToString("N"))
[IO.Directory]::CreateDirectory($temp) | Out-Null
try {
  $staticResults = @()
  foreach ($entry in @([ordered]@{ name = "plan"; path = $planLane }, [ordered]@{ name = "workflows"; path = $runtimeLane })) {
    $staticOut = Join-Path $temp "$($entry.name)_static.json"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $staticValidator -ProjectRoot $ProjectRoot -LaneDir $entry.path -OutFile $staticOut *> $null
    $payload = Read-Json $staticOut
    $staticResults += [ordered]@{ mirror = $entry.name; exit_code = $LASTEXITCODE; qa_status = $payload.qa_status; defect_count = @($payload.defects).Count; node_count = $payload.node_count }
  }
  Add-Check $checks "both_mirrors_pass_workflow_static" (@($staticResults | Where-Object { $_.exit_code -ne 0 -or $_.qa_status -ne "pass" -or $_.defect_count -ne 0 }).Count -eq 0) $staticResults
} finally {
  if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}

$workflow = Read-Json (Join-Path $planLane "workflow.api.json")
$runtime = Read-Json (Join-Path $planLane "runtime_requirements.json")
$smoke = Read-Json (Join-Path $planLane "smoke_test_request.json")
$active = Read-Json $activePath
$queue = Read-Json $queuePath
$registry = Read-Json $registryPath
$objectInfoRecord = Read-Json $objectInfoPath
$assetEvidence = Read-Json $assetEvidencePath
$installDryRun = Read-Json $installDryRunPath
$installRegression = Read-Json $installRegressionPath
$acceptanceTemplate = Read-Json $acceptanceTemplatePath
$requiredNodes = @($runtime.required_nodes)
$workflowNodeClasses = @($workflow.PSObject.Properties | ForEach-Object { [string]$_.Value.class_type })
$missingWorkflowNodes = @($requiredNodes | Where-Object { $_ -notin $workflowNodeClasses })
Add-Check $checks "required_nodes_present_in_workflow" ($missingWorkflowNodes.Count -eq 0) $missingWorkflowNodes

$objectInfo = $objectInfoRecord.object_info
$missingObjectInfoNodes = @($requiredNodes | Where-Object { $null -eq $objectInfo.PSObject.Properties[[string]$_] })
Add-Check $checks "required_nodes_present_in_saved_object_info" ($missingObjectInfoNodes.Count -eq 0) $missingObjectInfoNodes

$inputCompatibility = @()
foreach ($nodeProperty in $workflow.PSObject.Properties) {
  $nodeId = [string]$nodeProperty.Name
  $node = $nodeProperty.Value
  $nodeClass = [string]$node.class_type
  $schema = if ($null -ne $objectInfo.PSObject.Properties[$nodeClass]) { $objectInfo.$nodeClass } else { $null }
  $requiredSchema = if ($null -ne $schema -and $null -ne $schema.input) { $schema.input.required } else { $null }
  $optionalSchema = if ($null -ne $schema -and $null -ne $schema.input) { $schema.input.optional } else { $null }
  foreach ($inputProperty in $node.inputs.PSObject.Properties) {
    $inputName = [string]$inputProperty.Name
    $descriptor = $null
    if ($null -ne $requiredSchema -and $null -ne $requiredSchema.PSObject.Properties[$inputName]) {
      $descriptor = $requiredSchema.$inputName
    } elseif ($null -ne $optionalSchema -and $null -ne $optionalSchema.PSObject.Properties[$inputName]) {
      $descriptor = $optionalSchema.$inputName
    }
    $inputDeclared = $null -ne $descriptor
    $enumValid = $true
    $value = $inputProperty.Value
    if ($inputDeclared -and -not ($value -is [array])) {
      $typeSpec = @($descriptor)[0]
      if ($typeSpec -is [array]) {
        $enumValid = $value -in @($typeSpec)
      }
    }
    $inputCompatibility += [ordered]@{
      node_id = $nodeId
      node_class = $nodeClass
      input = $inputName
      declared_in_object_info = $inputDeclared
      enum_value_valid = $enumValid
    }
  }
}
$incompatibleInputs = @($inputCompatibility | Where-Object { -not $_.declared_in_object_info -or -not $_.enum_value_valid })
Add-Check $checks "workflow_inputs_match_saved_object_info" ($incompatibleInputs.Count -eq 0) $incompatibleInputs

$model = @($runtime.required_models | Select-Object -First 1)
$loaderMatches = $null -ne $workflow.'1' -and [string]$workflow.'1'.class_type -eq "CheckpointLoaderSimple" -and [string]$workflow.'1'.inputs.ckpt_name -eq "flux1-dev-fp8.safetensors"
Add-Check $checks "flux1_dev_loader_is_canonical" $loaderMatches $workflow.'1'
$expectedSha256 = "8e91b68084b53a7fc44ed2a3756d821e355ac1a7b6fe29be760c1db532f3d88a"
$expectedRevision = "0f6b956e6e2e041fb73d079b72ec0e761506f601"
$assetBoundary = $model.Count -eq 1 -and [string]$model[0].filename -eq "flux1-dev-fp8.safetensors" -and [string]$model[0].sha256 -eq $expectedSha256 -and [int64]$model[0].bytes -eq 17246524772 -and [bool]$runtime.asset_authority_complete -and -not [bool]$runtime.asset_contract_complete -and [string]$runtime.current_status -eq "asset_authority_recorded_blocked_local_install_and_runtime_proof"
Add-Check $checks "asset_contract_fails_closed" $assetBoundary $model
$sourceAuthorityPass = [string]$runtime.licensed_source.repository -eq "Comfy-Org/flux1-dev" -and [string]$runtime.licensed_source.revision -eq $expectedRevision -and [string]$runtime.licensed_source.license_id -eq "flux-1-dev-non-commercial-license"
Add-Check $checks "licensed_source_authority_is_immutable" $sourceAuthorityPass $runtime.licensed_source
$evidenceBindingPass = $null -ne $assetEvidence -and [string]$assetEvidence.authority.revision -eq $expectedRevision -and [string]$assetEvidence.authority.sha256 -eq $expectedSha256 -and -not [bool]$assetEvidence.local_inventory.present -and -not [bool]$assetEvidence.s3_inventory.present
Add-Check $checks "asset_authority_evidence_matches_requirements" $evidenceBindingPass $assetEvidence
$installContractPass = [string]$runtime.local_install_contract.installer -eq "Plan/Instructions/Operations/Scripts/Install-LicensedModelFromHttp.ps1" -and [string]$runtime.local_install_contract.status -eq "ready_dry_run_license_acceptance_pending" -and [string]$runtime.licensed_source.download_url -like "*$expectedRevision*"
Add-Check $checks "licensed_local_install_contract_declared" $installContractPass $runtime.local_install_contract
$acceptanceTemplatePass = $null -ne $acceptanceTemplate -and -not [bool]$acceptanceTemplate.accepted -and [string]$acceptanceTemplate.license_id -eq "flux-1-dev-non-commercial-license" -and [string]$acceptanceTemplate.repository -eq "Comfy-Org/flux1-dev" -and [string]$acceptanceTemplate.revision -eq $expectedRevision -and [string]$acceptanceTemplate.filename -eq "flux1-dev-fp8.safetensors" -and [string]$acceptanceTemplate.use_scope -eq "noncommercial" -and [string]::IsNullOrWhiteSpace([string]$acceptanceTemplate.accepted_by) -and [string]::IsNullOrWhiteSpace([string]$acceptanceTemplate.accepted_at)
Add-Check $checks "license_acceptance_template_remains_unaccepted" $acceptanceTemplatePass $acceptanceTemplate
$installerHash = if (Test-Path -LiteralPath $installerScriptPath -PathType Leaf) { (Get-FileHash -LiteralPath $installerScriptPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "" }
$requirementsHash = (Get-FileHash -LiteralPath (Join-Path $planLane "runtime_requirements.json") -Algorithm SHA256).Hash.ToLowerInvariant()
$dryRunPass = $null -ne $installDryRun -and [string]$installDryRun.result -eq "ready_dry_run" -and -not [bool]$installDryRun.network_contacted -and -not [bool]$installDryRun.download_attempted -and [string]$installDryRun.installer_script_sha256 -eq $installerHash -and [string]$installDryRun.runtime_requirements_sha256 -eq $requirementsHash
Add-Check $checks "licensed_installer_dry_run_hash_bound_no_network" $dryRunPass ([ordered]@{
  path = "Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_FLUX1_DEV_LICENSED_INSTALL_DRY_RUN_20260710T224500-0500.json"
  result = $installDryRun.result
  network_contacted = $installDryRun.network_contacted
  download_attempted = $installDryRun.download_attempted
  installer_script_sha256 = $installDryRun.installer_script_sha256
  runtime_requirements_sha256 = $installDryRun.runtime_requirements_sha256
})
$regressionScriptHash = if (Test-Path -LiteralPath $installerRegressionScriptPath -PathType Leaf) { (Get-FileHash -LiteralPath $installerRegressionScriptPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "" }
$regressionPass = $null -ne $installRegression -and [string]$installRegression.result -eq "pass_local_only" -and [int]$installRegression.failed_check_count -eq 0 -and [int]$installRegression.check_count -ge 14 -and [string]$installRegression.installer_script_sha256 -eq $installerHash -and [string]$installRegression.regression_script_sha256 -eq $regressionScriptHash
Add-Check $checks "licensed_installer_regression_passes" $regressionPass ([ordered]@{
  path = "Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LICENSED_MODEL_INSTALL_REGRESSION_20260710T224500-0500.json"
  result = $installRegression.result
  check_count = $installRegression.check_count
  failed_check_count = $installRegression.failed_check_count
  installer_script_sha256 = $installRegression.installer_script_sha256
  regression_script_sha256 = $installRegression.regression_script_sha256
})
$canonicalWorkflowPath = "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux1_dev_primary_base/workflow.api.json"
$canonicalPathPolicy = "canonical_plan_authority_with_byte_identical_runtime_mirror"
$pathPolicyPass = @($runtime, $smoke, (Read-Json (Join-Path $planLane "patch_points.json"))) | Where-Object { [string]$_.workflow_path -ne $canonicalWorkflowPath -or [string]$_.workflow_path_policy -ne $canonicalPathPolicy }
Add-Check $checks "canonical_plan_path_policy_explicit" (@($pathPolicyPass).Count -eq 0) $pathPolicyPass
$candidateModelPaths = @(
  (Join-Path $ProjectRoot "models\checkpoints\flux1-dev-fp8.safetensors"),
  (Join-Path $ProjectRoot "ComfyUI\models\checkpoints\flux1-dev-fp8.safetensors")
)
$presentModels = @($candidateModelPaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
Add-Check $checks "model_absence_matches_blocker" ($presentModels.Count -eq 0) $presentModels
Add-Check $checks "smoke_execution_remains_disabled" ($null -ne $smoke -and -not [bool]$smoke.execution_allowed) $smoke.execution_allowed

$activeRows = @($active.lanes | Where-Object { [string]$_.lane_id -eq "flux1_dev_primary_base" })
$queueRows = @($queue.lanes | Where-Object { [string]$_.lane_id -eq "flux1_dev_primary_base" })
$manifestStatePass = $activeRows.Count -eq 1 -and $queueRows.Count -eq 1 -and [string]$queue.selection_policy.current_runtime_lane_id -eq "flux1_dev_primary_base" -and [string]$activeRows[0].status -eq [string]$runtime.current_status -and [string]$queueRows[0].status -eq [string]$runtime.current_status
Add-Check $checks "active_and_queue_state_aligned" $manifestStatePass ([ordered]@{ active_count = $activeRows.Count; queue_count = $queueRows.Count; current_lane = $queue.selection_policy.current_runtime_lane_id })
$registryRows = @($registry | Where-Object { [string]$_.lane_id -eq "flux1_dev_primary_base" })
Add-Check $checks "registry_remains_not_promoted" ($registryRows.Count -eq 1 -and [string]$registryRows[0].promotion_state -eq "not_promoted") $registryRows

$failed = @($checks | Where-Object { -not $_.passed })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "flux1_dev_workflow_contract_validation"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failed.Count -eq 0) { "pass_asset_authority_recorded_local_model_blocked" } else { "fail" })
  classification = $(if ($failed.Count -eq 0) { "FLUX1_DEV_ASSET_AUTHORITY_RECORDED_LOCAL_MODEL_BLOCKED" } else { "FLUX1_DEV_WORKFLOW_CONTRACT_INVALID" })
  lane_id = "flux1_dev_primary_base"
  local_only = $true
  aws_contacted = $false
  s3_contacted = $false
  github_api_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  mask_consumed_as_truth = $false
  target_runtime_proof = $false
  certification_claimed = $false
  promotion_claimed = $false
  check_count = $checks.Count
  failed_check_count = $failed.Count
  failed_check_names = @($failed | ForEach-Object { $_.name })
  checks = @($checks)
  blocker = "The authoritative source and SHA256 are recorded, but the licensed checkpoint is not installed locally and automation does not assert license acceptance."
  next_action = "After explicit license-authorized installation, verify observed SHA256, then run lane object_info, output, technical QA, and visual QA gates."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W66_FLUX1_DEV_WORKFLOW_CONTRACT_$stamp.json"
} elseif (-not [IO.Path]::IsPathRooted($OutFile)) { $OutFile = Join-Path $ProjectRoot $OutFile }
Write-JsonNoBom $record $OutFile
$record | ConvertTo-Json -Depth 24
if ($failed.Count -gt 0) { exit 1 }
