<#
.SYNOPSIS
Validates current Wave 60 operations helpers with local-only checks.

.DESCRIPTION
Parses every Operations/Scripts PowerShell helper, parses Operations JSON
schemas/templates, runs local-only smoke checks into a temp directory, and writes
a machine-readable evidence record. It does not contact AWS, Civitai, GitHub, or
start EC2.
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
  }
  if (![string]::IsNullOrWhiteSpace($env:TEMP)) {
    $tempFull = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempFull; To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "/"); To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "\\"); To = "[TEMP]" }
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

function Invoke-LocalHelper {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string[]]$Arguments = @(),
    [string]$ExpectedOutputFile = ""
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
    expected_output_file_exists = (![string]::IsNullOrWhiteSpace($ExpectedOutputFile) -and (Test-Path -LiteralPath $ExpectedOutputFile))
    expected_output_json_valid = $false
    expected_output_error = $null
  }
  if ($entry.expected_output_file_exists) {
    try {
      $null = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      $entry.expected_output_json_valid = $true
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  }
  return $entry
}

function Find-LatestFile {
  param(
    [string]$Directory,
    [string]$Filter
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $file = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$operationsRoot = Join-Path $ProjectRoot "Plan\Instructions\Operations"
$scriptsRoot = Join-Path $operationsRoot "Scripts"
$schemasRoot = Join-Path $operationsRoot "Schemas"
$templatesRoot = Join-Path $operationsRoot "Templates"
$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
$workflowRuntimeDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Runtime"
$tempRoot = Join-Path $env:TEMP "comfy_ui_ops_static_validation_$stamp"
$script:ValidationTempRoot = $tempRoot
$null = New-Item -ItemType Directory -Force -Path $tempRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W60_OPERATIONS_HELPER_CURRENT_VALIDATION_$stamp.json"
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

$localSmokeResults = @()
$modelRecordFile = Join-Path $tempRoot "model_registry_smoke.json"
$localSmokeResults += Invoke-LocalHelper -Name "model_registry_record_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ModelRegistryRecord.ps1") `
  -Arguments @("-ModelName", "static-validation-placeholder", "-ModelType", "checkpoint", "-BaseModel", "SDXL", "-LocalPath", "C:\Comfy_UI_Main\__missing_static_validation_placeholder.safetensors") `
  -ExpectedOutputFile ""

$localSmokeResults += Invoke-LocalHelper -Name "github_checkpoint_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-GitHubCheckpoint.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-Message", "static validation dry run") `
  -ExpectedOutputFile ""

$staticProofDryRunFile = Join-Path $tempRoot "ec2_lane_static_proof_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_lane_static_proof_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2LaneStaticProof.ps1") `
  -Arguments @("-OutFile", $staticProofDryRunFile) `
  -ExpectedOutputFile $staticProofDryRunFile

$comfySmokeFile = Join-Path $tempRoot "comfy_workflow_smoke_dry_run.json"
$comfySmokeRequestFile = Join-Path $tempRoot "comfy_workflow_smoke_request.json"
$localSmokeResults += Invoke-LocalHelper -Name "comfy_workflow_smoke_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-ComfyWorkflowSmoke.ps1") `
  -Arguments @("-OutFile", $comfySmokeFile, "-OutRequestFile", $comfySmokeRequestFile) `
  -ExpectedOutputFile $comfySmokeFile

$pullbackDryRunFile = Join-Path $tempRoot "ec2_pullback_record_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_pullback_record_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "New-EC2PullbackRecord.ps1") `
  -Arguments @("-DryRun", "-OutFile", $pullbackDryRunFile) `
  -ExpectedOutputFile $pullbackDryRunFile

$readinessFile = Join-Path $tempRoot "lane_runtime_readiness.json"
$localSmokeResults += Invoke-LocalHelper -Name "lane_runtime_readiness_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Test-LaneRuntimeReadiness.ps1") `
  -Arguments @("-OutFile", $readinessFile) `
  -ExpectedOutputFile $readinessFile

$coordinatorFile = Join-Path $tempRoot "ec2_workflow_smoke_run_dry_run.json"
$coordinatorRequestFile = Join-Path $tempRoot "ec2_workflow_smoke_run_request.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_smoke_run_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2WorkflowSmokeRun.ps1") `
  -Arguments @("-OutFile", $coordinatorFile, "-OutRequestFile", $coordinatorRequestFile, "-ReadinessFile", $readinessFile) `
  -ExpectedOutputFile $coordinatorFile

$latestBlockedStaticProof = Find-LatestFile -Directory $workflowStaticDir -Filter "W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_*.json"
$latestCoordinatorDryRun = Find-LatestFile -Directory $workflowRuntimeDir -Filter "W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_*.json"
$latestReadiness = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W61_LANE_RUNTIME_READINESS_*.json"

$evidenceChecks = @()
foreach ($evidence in @($latestBlockedStaticProof, $latestCoordinatorDryRun, $latestReadiness)) {
  if ([string]::IsNullOrWhiteSpace($evidence)) { continue }
  $evidenceChecks += Test-JsonFile -Path $evidence
}

$scriptFailures = @($scriptParseResults | Where-Object { $_.result -ne "pass" })
$jsonFailures = @($jsonParseResults | Where-Object { $_.result -ne "pass" })
$smokeFailures = @($localSmokeResults | Where-Object { $_.result -ne "pass" -or ($_.expected_output_file -and -not $_.expected_output_json_valid) })
$evidenceFailures = @($evidenceChecks | Where-Object { $_.result -ne "pass" })

$record = [ordered]@{
  evidence_id = "EVID-W60-OPERATIONS-HELPER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W60-010"
  artifact_type = "operations_helper_current_static_validation"
  tracker_ids = @("TRK-W60-010", "TRK-W61-006", "TRK-W61-007")
  item_ids = @("W60-010", "ITEM-W61-006", "ITEM-W61-007")
  qa_protocol_used = @(
    "README_OPERATIONS_WAVE60.md",
    "OPERATIONAL_DONE_GATES.md",
    "SECRETS_ENV_HANDLING_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Instructions/Operations/Scripts/*.ps1",
    "Plan/Instructions/Operations/Schemas/*.json",
    "Plan/Instructions/Operations/Templates/*.json",
    "latest selected-lane runtime gate evidence"
  )
  validation_results = [ordered]@{
    script_count = @($scriptParseResults).Count
    script_parse_failures = @($scriptFailures).Count
    script_parse_results = $scriptParseResults
    json_file_count = @($jsonParseResults).Count
    json_parse_failures = @($jsonFailures).Count
    json_parse_results = $jsonParseResults
    local_smoke_count = @($localSmokeResults).Count
    local_smoke_failures = @($smokeFailures).Count
    local_smoke_results = $localSmokeResults
    evidence_check_count = @($evidenceChecks).Count
    evidence_check_failures = @($evidenceFailures).Count
    evidence_checks = $evidenceChecks
  }
  skipped_live_execution = @(
    [ordered]@{ script = "Invoke-CivitaiModelLookup.ps1"; reason = "Would contact Civitai API; out of scope for local static validation." },
    [ordered]@{ script = "Start-ComfyUIGpuServer.ps1"; reason = "Could start EC2/cost resources; out of scope for local static validation." },
    [ordered]@{ script = "Stop-ComfyUIGpuServer.ps1"; reason = "Would contact AWS; out of scope for local static validation." },
    [ordered]@{ script = "Test-AwsAuthGate.ps1"; reason = "Would contact AWS login/STS; existing auth evidence is inspected instead." },
    [ordered]@{ script = "Test-AwsComfyGpuIdentity.ps1"; reason = "Would contact AWS; out of scope for local static validation." }
  )
  temp_root = "[VALIDATION_TEMP_ROOT]"
  temp_root_redacted = $true
  result = $(if ($scriptFailures.Count -eq 0 -and $jsonFailures.Count -eq 0 -and $smokeFailures.Count -eq 0 -and $evidenceFailures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_issues = @(
    "Live AWS, Civitai, GitHub, EC2 start, ComfyUI runtime generation, artifact pullback, and visual QA remain separate runtime validations.",
    "AWS auth is still expired in current evidence; this validation intentionally does not refresh or require AWS credentials."
  )
  next_action = "After AWS browser login refresh, rerun auth gate and selected-lane readiness before EC2 static proof."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote operations helper static validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
