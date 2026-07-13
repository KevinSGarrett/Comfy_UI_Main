<#
.SYNOPSIS
Validates active workflow lane coverage in the model registry.

.DESCRIPTION
Checks that every lane listed in the base-generation runtime lane queue has
checkpoint records in Plan/Registries/Models/model_registry.jsonl and rows in
the model runtime validation queue. This is local-only validation. It does not
download models, contact Civitai, contact AWS, start EC2, contact ComfyUI, or
run generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RegistryFile = "",
  [string]$RuntimeQueueFile = "",
  [string]$WorkflowQueueFile = "",
  [string]$OutFile = "",
  [switch]$AllowMissingLocalModelBinariesWithEvidence
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }

  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
  return $relativePath.Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Resolve-ProjectPath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
  return Join-Path $ProjectRoot $Path
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return $null -ne ($Object.PSObject.Properties[$Name])
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function New-Check {
  param(
    [string]$Name,
    [bool]$Passed,
    [string]$Expected,
    [string]$Observed,
    [object]$Details = $null
  )

  return [ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    expected = $Expected
    observed = $Observed
    details = $Details
  }
}

function Read-JsonLines {
  param([string]$Path)

  $entries = @()
  $lineNumber = 0
  foreach ($line in Get-Content -LiteralPath $Path) {
    $lineNumber += 1
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
      $entry = $line | ConvertFrom-Json
      $entry | Add-Member -NotePropertyName "_line_number" -NotePropertyValue $lineNumber -Force
      $entries += $entry
    } catch {
      throw "Invalid JSONL at ${Path}:${lineNumber}: $($_.Exception.Message)"
    }
  }
  return $entries
}

function Get-SourceHash {
  param(
    [object]$Entry,
    [string]$Name
  )

  if ($null -eq $Entry -or !(Has-Property -Object $Entry -Name "source_hashes")) { return "" }
  if ($null -eq $Entry.source_hashes) { return "" }
  if (Has-Property -Object $Entry.source_hashes -Name $Name) { return [string]$Entry.source_hashes.$Name }
  return ""
}

function Test-RequiredFields {
  param(
    [object]$Entry,
    [string[]]$RequiredFields
  )

  $missing = @()
  foreach ($field in $RequiredFields) {
    if (!(Has-Property -Object $Entry -Name $field)) {
      $missing += $field
      continue
    }
    $value = $Entry.$field
    if ($null -eq $value) {
      $missing += $field
      continue
    }
    if (($value -is [string]) -and [string]::IsNullOrWhiteSpace($value) -and $field -notin @("sha256")) {
      $missing += $field
    }
  }
  return $missing
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

if ([string]::IsNullOrWhiteSpace($RegistryFile)) {
  $RegistryFile = Join-Path $ProjectRoot "Plan\Registries\Models\model_registry.jsonl"
} else {
  $RegistryFile = Resolve-ProjectPath -Path $RegistryFile
}

if ([string]::IsNullOrWhiteSpace($RuntimeQueueFile)) {
  $RuntimeQueueFile = Join-Path $ProjectRoot "Plan\Registries\Models\model_runtime_validation_queue.csv"
} else {
  $RuntimeQueueFile = Resolve-ProjectPath -Path $RuntimeQueueFile
}

if ([string]::IsNullOrWhiteSpace($WorkflowQueueFile)) {
  $WorkflowQueueFile = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json"
} else {
  $WorkflowQueueFile = Resolve-ProjectPath -Path $WorkflowQueueFile
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Model_Registry\W61_MODEL_REGISTRY_COVERAGE_$stamp.json"
} else {
  $OutFile = Resolve-ProjectPath -Path $OutFile
}

$requiredRegistryFields = @(
  "registry_schema_version",
  "record_id",
  "model_name",
  "model_type",
  "base_model",
  "local_path",
  "workflow_lane",
  "compatibility_status",
  "qa_status",
  "runtime_validation_status"
)

$checks = @()
$recordChecks = @()
$laneResults = @()
$registryEntries = @()
$queueRows = @()
$workflowQueue = $null
$queueLaneObjects = @()
$activeLaneIds = @()

$workflowQueueExists = Test-Path -LiteralPath $WorkflowQueueFile
$checks += New-Check -Name "workflow_runtime_lane_queue_exists" `
  -Passed $workflowQueueExists `
  -Expected "runtime_lane_queue.json exists" `
  -Observed $(if ($workflowQueueExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $WorkflowQueueFile } else { "missing" })

if ($workflowQueueExists) {
  try {
    $workflowQueue = Read-JsonFile -Path $WorkflowQueueFile
    $queueLaneObjects = @($workflowQueue.lanes | Sort-Object order)
    $activeLaneIds = @($queueLaneObjects | ForEach-Object { [string]$_.lane_id } | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
    $checks += New-Check -Name "workflow_runtime_lane_queue_json_valid" `
      -Passed $true `
      -Expected "runtime lane queue JSON parses" `
      -Observed "valid"
    $checks += New-Check -Name "workflow_runtime_lane_queue_has_lanes" `
      -Passed (@($activeLaneIds).Count -gt 0) `
      -Expected "at least one queued runtime lane" `
      -Observed ("{0} queued lanes" -f @($activeLaneIds).Count)
    $duplicateLaneIds = @($activeLaneIds | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Name })
    $checks += New-Check -Name "workflow_runtime_lane_queue_unique_lane_ids" `
      -Passed (@($duplicateLaneIds).Count -eq 0) `
      -Expected "lane IDs are unique" `
      -Observed $(if (@($duplicateLaneIds).Count -eq 0) { "unique" } else { "duplicates: $($duplicateLaneIds -join ', ')" })
  } catch {
    $checks += New-Check -Name "workflow_runtime_lane_queue_json_valid" `
      -Passed $false `
      -Expected "runtime lane queue JSON parses" `
      -Observed $_.Exception.Message
  }
} else {
  $checks += New-Check -Name "workflow_runtime_lane_queue_json_valid" `
    -Passed $false `
    -Expected "runtime lane queue JSON parses" `
    -Observed "workflow queue missing"
}

$registryExists = Test-Path -LiteralPath $RegistryFile
$checks += New-Check -Name "registry_file_exists" `
  -Passed $registryExists `
  -Expected "model_registry.jsonl exists" `
  -Observed $(if ($registryExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RegistryFile } else { "missing" })

if ($registryExists) {
  try {
    $registryEntries = @(Read-JsonLines -Path $RegistryFile)
    $checks += New-Check -Name "registry_jsonl_valid" -Passed $true -Expected "every nonblank line is valid JSON" -Observed "valid"
    $checks += New-Check -Name "registry_has_records" -Passed (@($registryEntries).Count -gt 0) -Expected "at least one registry record" -Observed ("{0} records" -f @($registryEntries).Count)
  } catch {
    $checks += New-Check -Name "registry_jsonl_valid" -Passed $false -Expected "every nonblank line is valid JSON" -Observed $_.Exception.Message
  }
} else {
  $checks += New-Check -Name "registry_jsonl_valid" -Passed $false -Expected "valid JSONL" -Observed "registry file missing"
}

foreach ($entry in @($registryEntries)) {
  $missing = @(Test-RequiredFields -Entry $entry -RequiredFields $requiredRegistryFields)
  $recordChecks += New-Check -Name ("registry_record_required_fields_{0}" -f [string]$entry.record_id) `
    -Passed (@($missing).Count -eq 0) `
    -Expected ("required fields present: {0}" -f ($requiredRegistryFields -join ", ")) `
    -Observed $(if (@($missing).Count -eq 0) { "all required fields present" } else { "missing: $($missing -join ', ')" }) `
    -Details ([ordered]@{
      line_number = $(if (Has-Property -Object $entry -Name "_line_number") { [int]$entry._line_number } else { $null })
      model_name = $(if (Has-Property -Object $entry -Name "model_name") { [string]$entry.model_name } else { $null })
      workflow_lane = $(if (Has-Property -Object $entry -Name "workflow_lane") { [string]$entry.workflow_lane } else { $null })
      file_name = $(if (Has-Property -Object $entry -Name "file_name") { [string]$entry.file_name } else { $null })
    })
}

$queueExists = Test-Path -LiteralPath $RuntimeQueueFile
$checks += New-Check -Name "runtime_validation_queue_exists" `
  -Passed $queueExists `
  -Expected "model_runtime_validation_queue.csv exists" `
  -Observed $(if ($queueExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RuntimeQueueFile } else { "missing" })

if ($queueExists) {
  $queueRows = @(Import-Csv -LiteralPath $RuntimeQueueFile)
  $checks += New-Check -Name "runtime_validation_queue_has_rows" `
    -Passed (@($queueRows).Count -gt 0) `
    -Expected "at least one runtime validation queue row" `
    -Observed ("{0} rows" -f @($queueRows).Count)
}

foreach ($laneId in $activeLaneIds) {
  $laneChecks = @()
  $workflowLaneMatches = @($queueLaneObjects | Where-Object { [string]$_.lane_id -eq $laneId })
  $workflowLane = $(if (@($workflowLaneMatches).Count -gt 0) { $workflowLaneMatches[0] } else { $null })
  $workflowLaneStatus = $(if ($null -ne $workflowLane -and (Has-Property -Object $workflowLane -Name "status")) { [string]$workflowLane.status } else { "" })
  $workflowLaneProofEvidence = @()
  if ($null -ne $workflowLane -and (Has-Property -Object $workflowLane -Name "proof_evidence")) {
    $workflowLaneProofEvidence = @($workflowLane.proof_evidence | ForEach-Object { [string]$_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
  }
  $workflowLaneLocalEvidence = @()
  if ($null -ne $workflowLane -and (Has-Property -Object $workflowLane -Name "local_pre_ec2_evidence")) {
    $workflowLaneLocalEvidence = @($workflowLane.local_pre_ec2_evidence | ForEach-Object { [string]$_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
  }
  $laneExplicitlyBlocked = $workflowLaneStatus -match "^blocked|asset_authority_recorded_blocked|pending_install_and_runtime_proof"
  $lanePartialTargetRuntime = $workflowLaneStatus -match "single_sample_smoke_certified.*full_lane_not_certified"
  $laneRuntimeProven = (
    -not $laneExplicitlyBlocked -and -not $lanePartialTargetRuntime -and (
      $workflowLaneStatus -in @("runtime_smoke_proven", "runtime_smoke_qa_complete") -or
      $workflowLaneStatus -match "runtime_smoke_proven|runtime_smoke_qa_complete|first_runtime_smoke.*complete|target_runtime.*certified|target_runtime_scope.*complete" -or
      (($workflowLaneStatus -match "target_runtime") -and @($workflowLaneProofEvidence).Count -gt 0)
    )
  )
  $targetRuntimeProofLaneIds = @()
  if ($null -ne $workflowQueue -and (Has-Property -Object $workflowQueue -Name "selection_policy") -and (Has-Property -Object $workflowQueue.selection_policy -Name "target_runtime_proof_present_lane_ids")) {
    $targetRuntimeProofLaneIds = @($workflowQueue.selection_policy.target_runtime_proof_present_lane_ids | ForEach-Object { [string]$_ })
  }
  $laneBoundedModelRuntimeProven = $lanePartialTargetRuntime -and ($targetRuntimeProofLaneIds -contains $laneId)
  $laneModelRuntimeProven = $laneRuntimeProven -or $laneBoundedModelRuntimeProven
  $laneLocalPreEc2Validated = (
    -not $laneModelRuntimeProven -and
    ($workflowLaneStatus -match "local_") -and
    @($workflowLaneLocalEvidence).Count -gt 0
  )
  $requirementsPath = Join-Path $ProjectRoot ("Plan\07_IMPLEMENTATION\workflow_templates\base_generation\{0}\runtime_requirements.json" -f $laneId)
  $requirementsExists = Test-Path -LiteralPath $requirementsPath
  $laneChecks += New-Check -Name "runtime_requirements_exists" `
    -Passed $requirementsExists `
    -Expected "runtime_requirements.json exists for lane" `
    -Observed $(if ($requirementsExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $requirementsPath } else { "missing" })

  $requirements = $null
  if ($requirementsExists) {
    $requirements = Read-JsonFile -Path $requirementsPath
    $laneChecks += New-Check -Name "requirements_lane_id_matches" `
      -Passed ((Has-Property -Object $requirements -Name "lane_id") -and [string]$requirements.lane_id -eq $laneId) `
      -Expected $laneId `
      -Observed $(if (Has-Property -Object $requirements -Name "lane_id") { [string]$requirements.lane_id } else { "missing" })
  }

  $requiredModels = @()
  if ($null -ne $requirements -and (Has-Property -Object $requirements -Name "required_models")) {
    $requiredModels = @($requirements.required_models)
  }
  $laneChecks += New-Check -Name "requirements_have_required_models" `
    -Passed (@($requiredModels).Count -gt 0) `
    -Expected "at least one required model" `
    -Observed ("{0} required models" -f @($requiredModels).Count)

  foreach ($model in @($requiredModels)) {
    $filename = $(if (Has-Property -Object $model -Name "filename") { [string]$model.filename } else { "" })
    $subdir = $(if (Has-Property -Object $model -Name "comfyui_model_subdir") { [string]$model.comfyui_model_subdir } else { "" })
    $role = $(if (Has-Property -Object $model -Name "role") { [string]$model.role } else { "" })
    $expectedModelType = $(if (Has-Property -Object $model -Name "model_type") { [string]$model.model_type } elseif ($role -eq "checkpoint") { "Checkpoint" } else { "" })
    $expectedLocalPath = ("models/{0}/{1}" -f $subdir, $filename).Replace("\", "/")
    $matches = @($registryEntries | Where-Object {
      (Has-Property -Object $_ -Name "workflow_lane") -and
      (Has-Property -Object $_ -Name "file_name") -and
      [string]$_.workflow_lane -eq $laneId -and
      [string]$_.file_name -eq $filename
    })
    $entry = $(if (@($matches).Count -gt 0) { $matches[0] } else { $null })

    $laneChecks += New-Check -Name "registry_record_found_for_required_model" `
      -Passed ($null -ne $entry) `
      -Expected ("registry record for {0}" -f $filename) `
      -Observed $(if ($null -ne $entry) { [string]$entry.record_id } else { "missing" })
    $laneChecks += New-Check -Name "single_registry_record_for_required_model" `
      -Passed (@($matches).Count -eq 1) `
      -Expected "exactly one matching registry record" `
      -Observed ("{0} matching records" -f @($matches).Count)

    if ($null -ne $entry) {
      $localPath = $(if (Has-Property -Object $entry -Name "local_path") { ([string]$entry.local_path).Replace("\", "/") } else { "" })
      $compatibleEngines = @()
      if (Has-Property -Object $entry -Name "compatible_engines") {
        $compatibleEngines = @($entry.compatible_engines | ForEach-Object { [string]$_ })
      }
      $engineFamily = $(if (Has-Property -Object $requirements -Name "engine_family") { [string]$requirements.engine_family } else { "" })
      $binaryPath = Resolve-ProjectPath -Path $expectedLocalPath
      $binaryExists = Test-Path -LiteralPath $binaryPath
      $runtimeValidationStatus = $(if (Has-Property -Object $entry -Name "runtime_validation_status") { [string]$entry.runtime_validation_status } else { "" })
      $compatibilityStatus = $(if (Has-Property -Object $entry -Name "compatibility_status") { [string]$entry.compatibility_status } else { "" })
      $qaStatus = $(if (Has-Property -Object $entry -Name "qa_status") { [string]$entry.qa_status } else { "" })
      $storageLocation = $(if (Has-Property -Object $entry -Name "storage_location") { [string]$entry.storage_location } else { "" })
      $hashStatus = $(if (Has-Property -Object $model -Name "hash_status") { [string]$model.hash_status } else { "" })
      $pathStatus = $(if (Has-Property -Object $model -Name "path_status") { [string]$model.path_status } else { "" })
      $runtimeQueued = ($runtimeValidationStatus -eq "queued")
      $runtimeComplete = ($runtimeValidationStatus -in @("runtime_smoke_complete", "runtime_validated"))
      if ($laneModelRuntimeProven) {
        $expectedCompatibilityStatuses = @("runtime_validated", "runtime_smoke_validated", "bounded_target_runtime_smoke_validated")
        $expectedRuntimeStatuses = @("runtime_smoke_complete", "runtime_validated")
        $expectedQaStatuses = @("pass_with_notes_for_runtime_smoke", "target_runtime_smoke_pass_with_notes", "pass")
      } elseif ($laneLocalPreEc2Validated) {
        $expectedCompatibilityStatuses = @("needs_runtime_validation", "local_runtime_smoke_validated_with_notes", "local_runtime_followup_validated_with_notes")
        $expectedRuntimeStatuses = @("queued", "local_generation_smoke_complete", "local_generation_followup_complete")
        $expectedQaStatuses = @("not_tested")
      } else {
        $expectedCompatibilityStatuses = @("needs_runtime_validation")
        $expectedRuntimeStatuses = @("queued")
        $expectedQaStatuses = @("not_tested")
      }
      $evidencePaths = @()
      if (Has-Property -Object $entry -Name "evidence_paths") {
        $evidencePaths = @($entry.evidence_paths | ForEach-Object { [string]$_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
      }
      $existingEvidencePaths = @($evidencePaths | Where-Object { Test-Path -LiteralPath (Resolve-ProjectPath -Path $_) })
      $missingEvidencePaths = @($evidencePaths | Where-Object { !(Test-Path -LiteralPath (Resolve-ProjectPath -Path $_)) })
      $missingEvidenceIsSupplementalRuntimeOnly = @($missingEvidencePaths | Where-Object { $_.Replace("\", "/") -notlike "runtime_artifacts/*" }).Count -eq 0
      $cleanEnvironmentEvidenceCoverage = (
        $AllowMissingLocalModelBinariesWithEvidence -and
        @($existingEvidencePaths).Count -gt 0 -and
        $missingEvidenceIsSupplementalRuntimeOnly
      )
      $verifiedHashStatuses = @("local_sha256_verified", "observed_external_local_sha256_verified", "ec2_static_match_verified", "verified_ec2_static_match")
      $verifiedPathStatuses = @("local_model_present", "present_via_configured_external_model_path", "ec2_static_match_verified", "verified_ec2_static_match")
      $verifiedHashAndPathAuthority = ($verifiedHashStatuses -contains $hashStatus -and $verifiedPathStatuses -contains $pathStatus)
      $boundedLocalPreEc2Authority = ($laneLocalPreEc2Validated -and $hashStatus -eq "pending_ec2_static_match" -and $pathStatus -eq "pending_ec2_static_match")
      $cleanEnvironmentEvidenceSubstitution = (
        $AllowMissingLocalModelBinariesWithEvidence -and
        !$binaryExists -and
        ($verifiedHashAndPathAuthority -or $boundedLocalPreEc2Authority) -and
        $cleanEnvironmentEvidenceCoverage
      )

      $laneChecks += New-Check -Name "registry_local_path_matches_requirement" `
        -Passed ($localPath -eq $expectedLocalPath) `
        -Expected $expectedLocalPath `
        -Observed $localPath
      $laneChecks += New-Check -Name "registry_model_type_matches_requirement" `
        -Passed (([string]::IsNullOrWhiteSpace($expectedModelType) -and (Has-Property -Object $entry -Name "model_type") -and ![string]::IsNullOrWhiteSpace([string]$entry.model_type)) -or ((Has-Property -Object $entry -Name "model_type") -and [string]$entry.model_type -eq $expectedModelType)) `
        -Expected $(if ([string]::IsNullOrWhiteSpace($expectedModelType)) { "nonblank model_type for non-checkpoint role $role" } else { $expectedModelType }) `
        -Observed $(if (Has-Property -Object $entry -Name "model_type") { [string]$entry.model_type } else { "missing" })
      $laneChecks += New-Check -Name "registry_base_model_matches_engine_family" `
        -Passed ((Has-Property -Object $entry -Name "base_model") -and [string]$entry.base_model -eq $engineFamily) `
        -Expected $engineFamily `
        -Observed $(if (Has-Property -Object $entry -Name "base_model") { [string]$entry.base_model } else { "missing" })
      $laneChecks += New-Check -Name "registry_compatible_engine_includes_lane_engine" `
        -Passed ($compatibleEngines -contains $engineFamily) `
        -Expected ("compatible_engines contains {0}" -f $engineFamily) `
        -Observed ($compatibleEngines -join ", ")
      $laneChecks += New-Check -Name "registry_compatibility_status_matches_lane_state" `
        -Passed ($expectedCompatibilityStatuses -contains $compatibilityStatus) `
        -Expected ($expectedCompatibilityStatuses -join " | ") `
        -Observed $(if ([string]::IsNullOrWhiteSpace($compatibilityStatus)) { "missing" } else { $compatibilityStatus })
      $laneChecks += New-Check -Name "registry_runtime_validation_status_matches_lane_state" `
        -Passed ($expectedRuntimeStatuses -contains $runtimeValidationStatus) `
        -Expected ($expectedRuntimeStatuses -join " | ") `
        -Observed $(if ([string]::IsNullOrWhiteSpace($runtimeValidationStatus)) { "missing" } else { $runtimeValidationStatus })
      $laneChecks += New-Check -Name "registry_qa_status_matches_lane_state" `
        -Passed (($expectedQaStatuses -contains $qaStatus) -or ($laneLocalPreEc2Validated -and $qaStatus -like "pass_with_notes_for_local_*")) `
        -Expected ($expectedQaStatuses -join " | ") `
        -Observed $(if ([string]::IsNullOrWhiteSpace($qaStatus)) { "missing" } else { $qaStatus })
      $laneChecks += New-Check -Name "registry_completed_lane_has_evidence_paths" `
        -Passed (!$laneModelRuntimeProven -or (@($evidencePaths).Count -gt 0 -and (@($existingEvidencePaths).Count -eq @($evidencePaths).Count -or $cleanEnvironmentEvidenceCoverage))) `
        -Expected $(if ($laneModelRuntimeProven) { "model runtime-smoke-complete lane has complete evidence, or clean CI is missing only supplemental runtime_artifacts paths while tracked evidence remains" } else { "not required for pending lane" }) `
        -Observed ("lane_status={0}; evidence_paths={1}; existing={2}; missing_supplemental_runtime_only={3}" -f $workflowLaneStatus, @($evidencePaths).Count, @($existingEvidencePaths).Count, $missingEvidenceIsSupplementalRuntimeOnly)
      $laneChecks += New-Check -Name "local_model_binary_boundary_respected" `
        -Passed ($binaryExists -or $runtimeQueued -or $cleanEnvironmentEvidenceSubstitution -or ($laneModelRuntimeProven -and $runtimeComplete -and $storageLocation -in @("ec2", "local_and_target_runtime_validated") -and @($existingEvidencePaths).Count -gt 0)) `
        -Expected "binary is present, queued, target-runtime proven, or explicitly substituted in a clean environment by verified hash/path state and complete evidence" `
        -Observed $(if ($binaryExists) { "local binary present" } elseif ($cleanEnvironmentEvidenceSubstitution) { "local binary absent; explicit clean-environment evidence substitution passed" } elseif ($laneModelRuntimeProven -and $runtimeComplete) { "local binary absent; bounded runtime evidence recorded" } else { "local binary absent; registry remains queued" }) `
        -Details ([ordered]@{ expected_local_path = $expectedLocalPath; local_file_exists = $binaryExists; storage_location = $storageLocation; lane_status = $workflowLaneStatus; hash_status = $hashStatus; path_status = $pathStatus; verified_hash_and_path_authority = $verifiedHashAndPathAuthority; bounded_local_pre_ec2_authority = $boundedLocalPreEc2Authority; clean_environment_evidence_substitution = $cleanEnvironmentEvidenceSubstitution; missing_evidence_paths = $missingEvidencePaths; missing_evidence_is_supplemental_runtime_only = $missingEvidenceIsSupplementalRuntimeOnly })
    }

    if ($null -ne $requirements) {
      $hashStatus = $(if (Has-Property -Object $model -Name "hash_status") { [string]$model.hash_status } else { "" })
      $pathStatus = $(if (Has-Property -Object $model -Name "path_status") { [string]$model.path_status } else { "" })
      $laneBlockedPreinstall = $workflowLaneStatus -eq "asset_authority_recorded_blocked_local_install_and_runtime_proof"
      $laneExternalModelHashVerified = $workflowLaneStatus -match "existing_external_model_hash_verified"
      $expectedHashStatuses = $(if ($laneRuntimeProven) { @("ec2_static_match_verified", "verified_ec2_static_match", "verified_ec2_static_and_target_runtime") } elseif ($laneLocalPreEc2Validated) { @("pending_ec2_static_match", "local_sha256_verified") } elseif ($laneExternalModelHashVerified) { @("observed_external_local_sha256_verified") } elseif ($laneBlockedPreinstall) { @("authoritative_remote_sha256_recorded_local_verification_pending") } else { @("pending_ec2_static_match") })
      $expectedPathStatuses = $(if ($laneRuntimeProven) { @("ec2_static_match_verified", "verified_ec2_static_match", "verified_ec2_static_and_target_runtime") } elseif ($laneLocalPreEc2Validated) { @("pending_ec2_static_match", "local_model_present") } elseif ($laneExternalModelHashVerified) { @("present_via_configured_external_model_path") } elseif ($laneBlockedPreinstall) { @("blocked_model_not_present_locally") } else { @("pending_ec2_static_match") })
      $laneChecks += New-Check -Name "requirements_hash_status_matches_lane_state" `
        -Passed ($expectedHashStatuses -contains $hashStatus) `
        -Expected ($expectedHashStatuses -join " | ") `
        -Observed $hashStatus
      $laneChecks += New-Check -Name "requirements_path_status_matches_lane_state" `
        -Passed ($expectedPathStatuses -contains $pathStatus) `
        -Expected ($expectedPathStatuses -join " | ") `
        -Observed $pathStatus
      $laneChecks += New-Check -Name "requirements_block_promotion_without_evidence" `
        -Passed ((Has-Property -Object $requirements -Name "promotion_allowed_without_evidence") -and -not [bool]$requirements.promotion_allowed_without_evidence) `
        -Expected "promotion_allowed_without_evidence=false" `
        -Observed $(if (Has-Property -Object $requirements -Name "promotion_allowed_without_evidence") { [string]$requirements.promotion_allowed_without_evidence } else { "missing" })
    }

    $queueMatches = @($queueRows | Where-Object {
      [string]$_.workflow_lane -eq $laneId -and
      ([string]$_.local_path).Replace("\", "/") -eq $expectedLocalPath
    })
    $laneChecks += New-Check -Name "runtime_validation_queue_row_found" `
      -Passed (@($queueMatches).Count -eq 1) `
      -Expected "one queue row for required model" `
      -Observed ("{0} matching rows" -f @($queueMatches).Count)
    if (@($queueMatches).Count -gt 0) {
      if ($laneModelRuntimeProven) {
        $expectedQueueStatuses = @("runtime_smoke_complete", "runtime_validated")
      } elseif ($laneLocalPreEc2Validated) {
        $expectedQueueStatuses = @("queued", "local_generation_smoke_complete", "local_generation_followup_complete")
      } else {
        $expectedQueueStatuses = @("queued")
      }
      $laneChecks += New-Check -Name "runtime_validation_queue_status_matches_lane_state" `
        -Passed ($expectedQueueStatuses -contains [string]$queueMatches[0].status) `
        -Expected ($expectedQueueStatuses -join " | ") `
        -Observed ([string]$queueMatches[0].status)
      $laneChecks += New-Check -Name "runtime_validation_queue_completed_lane_has_evidence" `
        -Passed (!$laneModelRuntimeProven -or ![string]::IsNullOrWhiteSpace([string]$queueMatches[0].evidence_path)) `
        -Expected $(if ($laneModelRuntimeProven) { "model runtime-smoke-complete queue row has evidence_path" } else { "not required for pending lane" }) `
        -Observed $(if ([string]::IsNullOrWhiteSpace([string]$queueMatches[0].evidence_path)) { "missing" } else { [string]$queueMatches[0].evidence_path })
    }

    if ($laneId -eq "sdxl_realvisxl_base_lane" -and $null -ne $entry) {
      $sourceModelId = $(if (Has-Property -Object $entry -Name "source_model_id") { [string]$entry.source_model_id } else { "" })
      $sourceVersionId = $(if (Has-Property -Object $entry -Name "source_model_version_id") { [string]$entry.source_model_version_id } else { "" })
      $sourceSha = Get-SourceHash -Entry $entry -Name "SHA256"
      $laneChecks += New-Check -Name "realvisxl_civitai_model_id_matches_requirement" `
        -Passed ($sourceModelId -eq "139562") `
        -Expected "139562" `
        -Observed $sourceModelId
      $laneChecks += New-Check -Name "realvisxl_civitai_version_id_selected" `
        -Passed ($sourceVersionId -eq "789646") `
        -Expected "789646 for V5.0 (BakedVAE), SDXL 1.0" `
        -Observed $sourceVersionId
      $laneChecks += New-Check -Name "realvisxl_source_sha256_captured" `
        -Passed ($sourceSha -eq "6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80") `
        -Expected "Civitai source SHA256 for realvisxlV50_v50Bakedvae.safetensors" `
        -Observed $(if ([string]::IsNullOrWhiteSpace($sourceSha)) { "missing" } else { $sourceSha })
    }
  }

  $laneFailures = @($laneChecks | Where-Object { $_.result -ne "pass" })
  $laneResults += [ordered]@{
    lane_id = $laneId
    requirements_path = $(if ($requirementsExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $requirementsPath } else { $null })
    required_model_count = @($requiredModels).Count
    checks = $laneChecks
    failed_check_count = @($laneFailures).Count
    result = $(if (@($laneFailures).Count -eq 0) { "pass" } else { "fail" })
  }
}

$failedChecks = @($checks | Where-Object { $_.result -ne "pass" })
$failedRecordChecks = @($recordChecks | Where-Object { $_.result -ne "pass" })
$failedLaneResults = @($laneResults | Where-Object { $_.result -ne "pass" })
$allFailures = @($failedChecks) + @($failedRecordChecks) + @($failedLaneResults)

$record = [ordered]@{
  evidence_id = "EVID-W61-MODEL-REGISTRY-COVERAGE-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-MODEL-REGISTRY-COVERAGE"
  artifact_type = "workflow_model_registry_coverage"
  tracker_ids = @("TRK-W61-006", "TRK-W61-011")
  item_ids = @("ITEM-W61-006", "ITEM-W61-011")
  qa_protocol_used = @(
    "README_QA_WAVE61.md",
    "MODEL_DOWNLOAD_AND_REGISTRY_UPDATE_PROTOCOL.md",
    "MODEL_METADATA_LOOKUP_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Registries/Models/model_registry.jsonl",
    "Plan/Registries/Models/model_runtime_validation_queue.csv",
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json",
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/<queued-lane>/runtime_requirements.json"
  )
  local_only = $true
  missing_local_model_binary_evidence_substitution_enabled = [bool]$AllowMissingLocalModelBinariesWithEvidence
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  registry_file = $(if ($registryExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RegistryFile } else { $RegistryFile })
  runtime_validation_queue_file = $(if ($queueExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RuntimeQueueFile } else { $RuntimeQueueFile })
  workflow_runtime_lane_queue_file = $(if ($workflowQueueExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $WorkflowQueueFile } else { $WorkflowQueueFile })
  registry_record_count = @($registryEntries).Count
  runtime_validation_queue_row_count = @($queueRows).Count
  workflow_runtime_lane_count = @($activeLaneIds).Count
  active_lane_ids = $activeLaneIds
  checks = $checks
  registry_record_checks = $recordChecks
  lane_results = $laneResults
  failed_check_count = @($allFailures).Count
  result = $(if (@($allFailures).Count -eq 0) { "pass_local_only" } else { "fail" })
  known_limits = @(
    "Does not download checkpoint binaries.",
    "Does not create new local or EC2 checkpoint hash proof; completed-lane statuses must point to existing proof evidence.",
    "Does not refresh AWS browser/SSO auth.",
    "Does not start EC2 or contact ComfyUI.",
    "Does not execute generation or perform new generated artifact visual QA."
  )
  next_action = "Before adding or promoting any queued lane, keep runtime_lane_queue.json, runtime_requirements.json, model_registry.jsonl, and model_runtime_validation_queue.csv aligned; then run EC2 proof only after auth, Git, queue, registry, and lane-readiness gates pass."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
[System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 40), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Wrote workflow model registry coverage record: $OutFile"
$record | ConvertTo-Json -Depth 40

if ($record.result -ne "pass_local_only") { exit 2 }
