<#
.SYNOPSIS
Validates the current Wave 61 QA helper set with local-only checks.

.DESCRIPTION
Parses every QA/Scripts PowerShell helper, parses QA JSON schemas/templates,
checks markdown templates, runs local-only smoke checks into a temp directory,
and writes a machine-readable evidence record. It does not run ComfyUI, start
EC2, inspect real generated artifacts, or claim final visual QA.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
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

function Test-PathIsUnderRoot {
  param(
    [string]$RootPath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($RootPath) -or [string]::IsNullOrWhiteSpace($TargetPath)) { return $false }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $rootFull = [System.IO.Path]::GetFullPath($RootPath).TrimEnd("\", "/")
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  return ($targetFull.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
    $targetFull.StartsWith("$rootFull$separator", [System.StringComparison]::OrdinalIgnoreCase))
}

function ConvertTo-EvidencePath {
  param(
    [string]$BasePath,
    [string]$TargetPath,
    [string]$TempRoot = ""
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }

  if (Test-PathIsUnderRoot -RootPath $TempRoot -TargetPath $TargetPath) {
    $relativeTemp = Get-RelativePathCompat -BasePath $TempRoot -TargetPath $TargetPath
    $relativeTemp = $relativeTemp.Replace("\", "/")
    if ([string]::IsNullOrWhiteSpace($relativeTemp) -or $relativeTemp -eq ".") { return "[VALIDATION_TEMP_ROOT]" }
    return "[VALIDATION_TEMP_ROOT]/$relativeTemp"
  }

  if (![string]::IsNullOrWhiteSpace($env:TEMP) -and (Test-PathIsUnderRoot -RootPath $env:TEMP -TargetPath $TargetPath)) {
    $relativeTemp = Get-RelativePathCompat -BasePath $env:TEMP -TargetPath $TargetPath
    return ("[TEMP]/" + $relativeTemp.Replace("\", "/"))
  }

  return ConvertTo-ProjectRelativePath -BasePath $BasePath -TargetPath $TargetPath
}

function ConvertTo-RedactedEvidenceText {
  param(
    [string]$Text,
    [string]$TempRoot = ""
  )

  if ([string]::IsNullOrEmpty($Text)) { return $Text }

  $redacted = $Text
  $replacements = @()
  if (![string]::IsNullOrWhiteSpace($TempRoot)) {
    $tempRootFull = [System.IO.Path]::GetFullPath($TempRoot).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempRootFull; To = "[VALIDATION_TEMP_ROOT]" }
    $replacements += [ordered]@{ From = $tempRootFull.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
    $replacements += [ordered]@{ From = $tempRootFull.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    $tempRootRelative = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $tempRootFull
    if (![string]::IsNullOrWhiteSpace($tempRootRelative)) {
      $replacements += [ordered]@{ From = $tempRootRelative; To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootRelative.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootRelative.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    }
  }
  if (![string]::IsNullOrWhiteSpace($env:TEMP)) {
    $tempFull = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempFull; To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "/"); To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "\\"); To = "[TEMP]" }
    $tempRelative = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $tempFull
    if (![string]::IsNullOrWhiteSpace($tempRelative)) {
      $replacements += [ordered]@{ From = $tempRelative; To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempRelative.Replace("\", "/"); To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempRelative.Replace("\", "\\"); To = "[TEMP]" }
    }
  }

  foreach ($replacement in $replacements) {
    if (![string]::IsNullOrWhiteSpace($replacement.From)) {
      $redacted = $redacted.Replace($replacement.From, $replacement.To)
    }
  }
  return $redacted
}

function Test-PowerShellParser {
  param([Parameter(Mandatory=$true)][string]$Path)

  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) > $null
  return [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    parse_errors = $errors.Count
    errors = @($errors | ForEach-Object { $_.Message })
    result = $(if ($errors.Count -eq 0) { "pass" } else { "fail" })
  }
}

function Test-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
  }
  try {
    $null = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }
  return $entry
}

function Test-MarkdownTemplate {
  param([Parameter(Mandatory=$true)][string]$Path)

  $text = Get-Content -LiteralPath $Path -Raw
  return [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    bytes = (Get-Item -LiteralPath $Path).Length
    result = $(if (![string]::IsNullOrWhiteSpace($text)) { "pass" } else { "fail" })
  }
}

function Test-JsonProperty {
  param(
    [object]$Object,
    [Parameter(Mandatory=$true)][string]$Name
  )

  if ($null -eq $Object) { return $false }
  return ($null -ne $Object.PSObject.Properties[$Name])
}

function Invoke-LocalHelper {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string[]]$Arguments = @(),
    [string]$ExpectedOutputFile = "",
    [string]$ExpectedOutputType = "none"
  )

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $text = ConvertTo-RedactedEvidenceText -Text $text -TempRoot $script:ValidationTempRoot
  $entry = [ordered]@{
    name = $Name
    script = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ScriptPath
    exit_code = $LASTEXITCODE
    result = $(if ($LASTEXITCODE -eq 0) { "pass" } else { "fail" })
    output_tail = $(if ($text.Length -gt 1000) { $text.Substring($text.Length - 1000) } else { $text })
    expected_output_file = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $ExpectedOutputFile -TempRoot $script:ValidationTempRoot
    expected_output_type = $ExpectedOutputType
    expected_output_file_exists = (![string]::IsNullOrWhiteSpace($ExpectedOutputFile) -and (Test-Path -LiteralPath $ExpectedOutputFile))
    expected_output_valid = $false
    expected_output_error = $null
  }

  if ($entry.expected_output_file_exists) {
    try {
      if ($ExpectedOutputType -eq "json") {
        $null = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
        $entry.expected_output_valid = $true
      } elseif ($ExpectedOutputType -eq "markdown") {
        $content = Get-Content -LiteralPath $ExpectedOutputFile -Raw
        $entry.expected_output_valid = (![string]::IsNullOrWhiteSpace($content))
      } else {
        $entry.expected_output_valid = $true
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  } elseif ($ExpectedOutputType -ne "none") {
    $entry.result = "fail"
    $entry.expected_output_error = "Expected output file was not created."
  }
  return $entry
}

function New-ContractCheck {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][bool]$Passed,
    [string]$Expected = "",
    [string]$Observed = ""
  )

  return [ordered]@{
    name = $Name
    expected = $Expected
    observed = $Observed
    result = $(if ($Passed) { "pass" } else { "fail" })
  }
}

function Test-ProjectReadinessSnapshotContract {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = "project_readiness_snapshot_contract"
    path = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $Path -TempRoot $script:ValidationTempRoot
    result = "fail"
    error = $null
    top_level_result = $null
    failure_category = $null
    local_ready = $false
    scan_result = $null
    scan_hit_count = $null
    ec2_start_allowed = $null
    generation_allowed = $null
    auth_safe_to_start_ec2 = $null
    lane_ready_for_ec2_static_proof = $null
    lane_ready_for_generation = $null
    coordinator_blocked_execute_records_safe = $null
    contract_check_failures = 0
    contract_checks = @()
  }

  $checks = @()
  try {
    if (!(Test-Path -LiteralPath $Path)) {
      throw "Project readiness snapshot file was not created."
    }

    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $recognizedResults = @(
      "pass_local_ready_runtime_blocked_auth",
      "pass_local_ready_runtime_blocked",
      "pass_local_ready_for_ec2_static_proof",
      "pass_ready_for_generation"
    )

    if (Test-JsonProperty -Object $payload -Name "result") {
      $entry.top_level_result = [string]$payload.result
    }
    if (Test-JsonProperty -Object $payload -Name "failure_category") {
      $entry.failure_category = [string]$payload.failure_category
    }
    if (Test-JsonProperty -Object $payload -Name "local_ready") {
      $entry.local_ready = [bool]$payload.local_ready
    }

    $checks += New-ContractCheck -Name "top_level_result_recognized" `
      -Passed (@($recognizedResults) -contains $entry.top_level_result) `
      -Expected ($recognizedResults -join " | ") `
      -Observed ([string]$entry.top_level_result)

    $checks += New-ContractCheck -Name "local_ready_true" `
      -Passed ([bool]$entry.local_ready) `
      -Expected "true" `
      -Observed ([string]$entry.local_ready)

    if (Test-JsonProperty -Object $payload -Name "secret_private_path_scan") {
      $scan = $payload.secret_private_path_scan
      if (Test-JsonProperty -Object $scan -Name "result") { $entry.scan_result = [string]$scan.result }
      if (Test-JsonProperty -Object $scan -Name "hit_count") { $entry.scan_hit_count = [int]$scan.hit_count }
    }

    $checks += New-ContractCheck -Name "secret_private_scan_passes" `
      -Passed ($entry.scan_result -eq "pass") `
      -Expected "pass" `
      -Observed ([string]$entry.scan_result)
    $checks += New-ContractCheck -Name "secret_private_scan_zero_hits" `
      -Passed ($entry.scan_hit_count -eq 0) `
      -Expected "0" `
      -Observed ([string]$entry.scan_hit_count)

    if (!(Test-JsonProperty -Object $payload -Name "runtime_gates")) {
      $checks += New-ContractCheck -Name "runtime_gates_present" -Passed $false -Expected "present" -Observed "missing"
    } else {
      $runtime = $payload.runtime_gates
      $checks += New-ContractCheck -Name "runtime_gates_present" -Passed $true -Expected "present" -Observed "present"

      if (Test-JsonProperty -Object $runtime -Name "ec2_start_allowed") {
        $entry.ec2_start_allowed = [bool]$runtime.ec2_start_allowed
      }
      if (Test-JsonProperty -Object $runtime -Name "generation_allowed") {
        $entry.generation_allowed = [bool]$runtime.generation_allowed
      }
      if (Test-JsonProperty -Object $runtime -Name "auth_gate") {
        $authGate = $runtime.auth_gate
        if (Test-JsonProperty -Object $authGate -Name "safe_to_start_ec2") {
          $entry.auth_safe_to_start_ec2 = [bool]$authGate.safe_to_start_ec2
        }
      }
      if (Test-JsonProperty -Object $runtime -Name "lane_readiness") {
        $laneReadiness = $runtime.lane_readiness
        if (Test-JsonProperty -Object $laneReadiness -Name "ready_for_ec2_static_proof") {
          $entry.lane_ready_for_ec2_static_proof = [bool]$laneReadiness.ready_for_ec2_static_proof
        }
        if (Test-JsonProperty -Object $laneReadiness -Name "ready_for_generation") {
          $entry.lane_ready_for_generation = [bool]$laneReadiness.ready_for_generation
        }
      }
      if (Test-JsonProperty -Object $runtime -Name "coordinator_safety") {
        $coordinatorSafety = $runtime.coordinator_safety
        if (Test-JsonProperty -Object $coordinatorSafety -Name "blocked_execute_records_safe") {
          $entry.coordinator_blocked_execute_records_safe = [bool]$coordinatorSafety.blocked_execute_records_safe
        }
      }
    }

    switch ($entry.top_level_result) {
      "pass_local_ready_runtime_blocked_auth" {
        $checks += New-ContractCheck -Name "blocked_auth_has_failure_category" `
          -Passed (![string]::IsNullOrWhiteSpace([string]$entry.failure_category)) `
          -Expected "non-empty" `
          -Observed ([string]$entry.failure_category)
        $checks += New-ContractCheck -Name "blocked_auth_disallows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false -and $entry.auth_safe_to_start_ec2 -eq $false) `
          -Expected "ec2_start_allowed=false; auth.safe_to_start_ec2=false" `
          -Observed ("ec2_start_allowed={0}; auth.safe_to_start_ec2={1}" -f $entry.ec2_start_allowed, $entry.auth_safe_to_start_ec2)
        $checks += New-ContractCheck -Name "blocked_auth_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "blocked_auth_coordinator_records_safe" `
          -Passed ($entry.coordinator_blocked_execute_records_safe -eq $true) `
          -Expected "true" `
          -Observed ([string]$entry.coordinator_blocked_execute_records_safe)
      }
      "pass_local_ready_runtime_blocked" {
        $checks += New-ContractCheck -Name "runtime_blocked_has_failure_category" `
          -Passed (![string]::IsNullOrWhiteSpace([string]$entry.failure_category)) `
          -Expected "non-empty" `
          -Observed ([string]$entry.failure_category)
        $checks += New-ContractCheck -Name "runtime_blocked_disallows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "runtime_blocked_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
      }
      "pass_local_ready_for_ec2_static_proof" {
        $checks += New-ContractCheck -Name "static_proof_ready_allows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $true -and $entry.lane_ready_for_ec2_static_proof -eq $true) `
          -Expected "ec2_start_allowed=true; lane.ready_for_ec2_static_proof=true" `
          -Observed ("ec2_start_allowed={0}; lane.ready_for_ec2_static_proof={1}" -f $entry.ec2_start_allowed, $entry.lane_ready_for_ec2_static_proof)
        $checks += New-ContractCheck -Name "static_proof_ready_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
      }
      "pass_ready_for_generation" {
        $checks += New-ContractCheck -Name "generation_ready_allows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $true) `
          -Expected "true" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "generation_ready_allows_generation" `
          -Passed ($entry.generation_allowed -eq $true -and $entry.lane_ready_for_generation -eq $true) `
          -Expected "generation_allowed=true; lane.ready_for_generation=true" `
          -Observed ("generation_allowed={0}; lane.ready_for_generation={1}" -f $entry.generation_allowed, $entry.lane_ready_for_generation)
      }
    }

    $failedChecks = @($checks | Where-Object { $_.result -ne "pass" })
    $entry.contract_checks = $checks
    $entry.contract_check_failures = @($failedChecks).Count
    $entry.result = $(if ($entry.contract_check_failures -eq 0) { "pass" } else { "fail" })
  } catch {
    $entry.error = $_.Exception.Message
    $entry.contract_checks = $checks
    $entry.contract_check_failures = $(if (@($checks).Count -eq 0) { 1 } else { @($checks | Where-Object { $_.result -ne "pass" }).Count })
    $entry.result = "fail"
  }

  return $entry
}

function New-SamplePng {
  param([Parameter(Mandatory=$true)][string]$Path)

  Add-Type -AssemblyName System.Drawing
  $bitmap = New-Object System.Drawing.Bitmap 64, 64
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.Clear([System.Drawing.Color]::FromArgb(32, 96, 160))
    $bitmap.SetPixel(0, 0, [System.Drawing.Color]::White)
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  } finally {
    $graphics.Dispose()
    $bitmap.Dispose()
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$qaRoot = Join-Path $ProjectRoot "Plan\Instructions\QA"
$scriptsRoot = Join-Path $qaRoot "Scripts"
$schemasRoot = Join-Path $qaRoot "Schemas"
$templatesRoot = Join-Path $qaRoot "Templates"
$laneDir = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\sdxl_low_risk_fallback_lane"
$tempRoot = Join-Path $env:TEMP "comfy_ui_qa_static_validation_$stamp"
$script:ValidationTempRoot = $tempRoot
$null = New-Item -ItemType Directory -Force -Path $tempRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\QA_Helper_Static_Validation\W61_QA_HELPER_CURRENT_VALIDATION_$stamp.json"
}

$scriptParseResults = @()
foreach ($script in Get-ChildItem -LiteralPath $scriptsRoot -Filter "*.ps1" -File | Sort-Object Name) {
  $scriptParseResults += Test-PowerShellParser -Path $script.FullName
}

$jsonParseResults = @()
foreach ($json in @(
  @(Get-ChildItem -LiteralPath $schemasRoot -Filter "*.json" -File | Sort-Object Name),
  @(Get-ChildItem -LiteralPath $templatesRoot -Filter "*.json" -File | Sort-Object Name)
)) {
  foreach ($file in @($json)) {
    if ($null -ne $file) {
      $jsonParseResults += Test-JsonFile -Path $file.FullName
    }
  }
}

$markdownTemplateResults = @()
foreach ($template in Get-ChildItem -LiteralPath $templatesRoot -Filter "*.md" -File | Sort-Object Name) {
  $markdownTemplateResults += Test-MarkdownTemplate -Path $template.FullName
}

$localSmokeResults = @()
$qaRecordFile = Join-Path $tempRoot "sample_qa_record.json"
$localSmokeResults += Invoke-LocalHelper -Name "initialize_qa_record_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Initialize-QARecord.ps1") `
  -Arguments @("-ArtifactId", "sample-artifact", "-ArtifactType", "static_validation_sample", "-OutFile", $qaRecordFile) `
  -ExpectedOutputFile $qaRecordFile `
  -ExpectedOutputType "json"

$doneCertFile = Join-Path $tempRoot "sample_done_certification.md"
$localSmokeResults += Invoke-LocalHelper -Name "done_certification_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-DoneCertification.ps1") `
  -Arguments @("-TaskId", "TRK-W61-SAMPLE", "-Title", "Static validation sample", "-OutFile", $doneCertFile) `
  -ExpectedOutputFile $doneCertFile `
  -ExpectedOutputType "markdown"

$imageDryRunFile = Join-Path $tempRoot "image_qa_dry_run.json"
$imageDryRunChecklist = Join-Path $tempRoot "image_qa_dry_run_checklist.md"
$localSmokeResults += Invoke-LocalHelper -Name "image_artifact_qa_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "New-ImageArtifactQARecord.ps1") `
  -Arguments @("-DryRun", "-OutFile", $imageDryRunFile, "-ChecklistOutFile", $imageDryRunChecklist) `
  -ExpectedOutputFile $imageDryRunFile `
  -ExpectedOutputType "json"

$sampleImage = Join-Path $tempRoot "sample_image.png"
New-SamplePng -Path $sampleImage
$imageTechnicalFile = Join-Path $tempRoot "image_qa_technical.json"
$imageTechnicalChecklist = Join-Path $tempRoot "image_qa_technical_checklist.md"
$localSmokeResults += Invoke-LocalHelper -Name "image_artifact_qa_technical_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ImageArtifactQARecord.ps1") `
  -Arguments @("-ImagePath", $sampleImage, "-ArtifactId", "static_validation_sample_image", "-OutFile", $imageTechnicalFile, "-ChecklistOutFile", $imageTechnicalChecklist, "-MinimumWidth", "1", "-MinimumHeight", "1") `
  -ExpectedOutputFile $imageTechnicalFile `
  -ExpectedOutputType "json"

$workflowStaticFile = Join-Path $tempRoot "workflow_static_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "workflow_static_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ComfyWorkflowStatic.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneDir", $laneDir, "-OutFile", $workflowStaticFile) `
  -ExpectedOutputFile $workflowStaticFile `
  -ExpectedOutputType "json"

$itemsTrackerValidationFile = Join-Path $tempRoot "items_tracker_package_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "items_tracker_package_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ItemsTrackerPackageStatic.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $itemsTrackerValidationFile) `
  -ExpectedOutputFile $itemsTrackerValidationFile `
  -ExpectedOutputType "json"

$projectReadinessFile = Join-Path $tempRoot "project_readiness_snapshot.json"
$localSmokeResults += Invoke-LocalHelper -Name "project_readiness_snapshot_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ProjectReadinessSnapshot.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $projectReadinessFile) `
  -ExpectedOutputFile $projectReadinessFile `
  -ExpectedOutputType "json"

$projectReadinessContract = Test-ProjectReadinessSnapshotContract -Path $projectReadinessFile

$scriptFailures = @($scriptParseResults | Where-Object { $_.result -ne "pass" })
$jsonFailures = @($jsonParseResults | Where-Object { $_.result -ne "pass" })
$markdownFailures = @($markdownTemplateResults | Where-Object { $_.result -ne "pass" })
$smokeFailures = @($localSmokeResults | Where-Object { $_.result -ne "pass" -or ($_.expected_output_type -ne "none" -and -not $_.expected_output_valid) })
$contractFailures = @()
if ($projectReadinessContract.result -ne "pass") {
  $contractFailures += $projectReadinessContract
}

$record = [ordered]@{
  evidence_id = "EVID-W61-QA-HELPER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-011"
  artifact_type = "qa_helper_current_static_validation"
  tracker_ids = @("TRK-W61-011", "TRK-W61-002", "TRK-W61-006")
  item_ids = @("ITEM-W61-011", "ITEM-W61-002", "ITEM-W61-006")
  qa_protocol_used = @(
    "README_QA_WAVE61.md",
    "STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md",
    "IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md",
    "COMFYUI_WORKFLOW_TESTING_PROTOCOL.md",
    "DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Instructions/QA/Scripts/*.ps1",
    "Plan/Instructions/QA/Schemas/*.json",
    "Plan/Instructions/QA/Templates/*.json",
    "Plan/Instructions/QA/Templates/*.md",
    "selected-lane workflow static validation smoke",
    "image artifact QA dry-run and technical sample smoke",
    "Items/Tracker package validator smoke",
    "project readiness snapshot smoke",
    "project readiness snapshot contract checks"
  )
  validation_results = [ordered]@{
    script_count = @($scriptParseResults).Count
    script_parse_failures = @($scriptFailures).Count
    script_parse_results = $scriptParseResults
    json_file_count = @($jsonParseResults).Count
    json_parse_failures = @($jsonFailures).Count
    json_parse_results = $jsonParseResults
    markdown_template_count = @($markdownTemplateResults).Count
    markdown_template_failures = @($markdownFailures).Count
    markdown_template_results = $markdownTemplateResults
    local_smoke_count = @($localSmokeResults).Count
    local_smoke_failures = @($smokeFailures).Count
    local_smoke_results = $localSmokeResults
    project_readiness_contract_failures = @($contractFailures).Count
    project_readiness_contract = $projectReadinessContract
  }
  temp_root = "[VALIDATION_TEMP_ROOT]"
  temp_root_redacted = $true
  result = $(if ($scriptFailures.Count -eq 0 -and $jsonFailures.Count -eq 0 -and $markdownFailures.Count -eq 0 -and $smokeFailures.Count -eq 0 -and $contractFailures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_issues = @(
    "Live image/video/audio artifact QA remains pending for actual generated artifacts.",
    "The sample image technical smoke does not count as generated artifact visual review.",
    "The project readiness snapshot is local-only and does not refresh AWS browser/SSO auth.",
    "ComfyUI runtime execution, model loading, EC2 static proof, artifact pullback, and final visual QA remain separate runtime validations."
  )
  next_action = "After AWS browser login refresh, run EC2 static proof, bounded smoke generation, artifact pullback, and real image QA."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote QA helper static validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
