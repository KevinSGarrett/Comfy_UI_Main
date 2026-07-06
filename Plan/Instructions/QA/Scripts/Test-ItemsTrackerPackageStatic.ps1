<#
.SYNOPSIS
Runs current local Items and Tracker package validators and records QA evidence.

.DESCRIPTION
This helper is local-only. It executes the existing package validators for
Plan/Tracker and Plan/Items, parses their JSON reports, and writes a combined
evidence record. It does not contact GitHub, AWS, Civitai, EC2, or ComfyUI.
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

function Invoke-ProcessCapture {
  param(
    [Parameter(Mandatory=$true)][string]$FileName,
    [Parameter(Mandatory=$true)][string[]]$Arguments,
    [int]$TimeoutSeconds = 120
  )

  $processInfo = New-Object System.Diagnostics.ProcessStartInfo
  $processInfo.FileName = $FileName
  $processInfo.UseShellExecute = $false
  $processInfo.RedirectStandardOutput = $true
  $processInfo.RedirectStandardError = $true
  $processInfo.RedirectStandardInput = $true

  $quotedArgs = @()
  foreach ($argument in $Arguments) {
    if ($argument -match '[\s"]') {
      $quotedArgs += '"' + ($argument -replace '"', '\"') + '"'
    } else {
      $quotedArgs += $argument
    }
  }
  $processInfo.Arguments = ($quotedArgs -join " ")

  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $processInfo
  $null = $process.Start()
  $process.StandardInput.Close()
  $stdout = $process.StandardOutput.ReadToEnd()
  $stderr = $process.StandardError.ReadToEnd()
  if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    try { $process.Kill() } catch {}
    return [ordered]@{
      exit_code = 124
      stdout = $stdout.Trim()
      stderr = (($stderr, "Timed out waiting for validator.") -join "`n").Trim()
    }
  }

  return [ordered]@{
    exit_code = $process.ExitCode
    stdout = $stdout.Trim()
    stderr = $stderr.Trim()
  }
}

function Get-OutputTail {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  if ($Text.Length -gt 1000) { return $Text.Substring($Text.Length - 1000) }
  return $Text
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Test-ValidatorReport {
  param(
    [Parameter(Mandatory=$true)][object]$Report
  )

  $errors = @()
  if ([string]$Report.promotion_decision -ne "pass") { $errors += "promotion_decision_not_pass" }
  if ([int]$Report.row_count -le 0) { $errors += "row_count_not_positive" }
  if ([int]$Report.missing_ultra_source_keys -ne 0) { $errors += "missing_ultra_source_keys" }
  if ([int]$Report.bad_human_flag_rows -ne 0) { $errors += "bad_human_flag_rows" }
  if ([int]$Report.bad_citation_rows -ne 0) { $errors += "bad_citation_rows" }
  if ([int]$Report.bad_line_rows -ne 0) { $errors += "bad_line_rows" }
  if (@($Report.errors).Count -ne 0) { $errors += "report_errors_present" }
  return [ordered]@{
    result = $(if ($errors.Count -eq 0) { "pass" } else { "fail" })
    errors = $errors
  }
}

function Test-Wave64Report {
  param(
    [Parameter(Mandatory=$true)][object]$Report
  )

  $errors = @()
  if ([string]$Report.result -ne "pass") { $errors += "wave64_result_not_pass" }
  if ([int]$Report.row_count_items -lt 60) { $errors += "wave64_items_row_count_below_60" }
  if ([int]$Report.row_count_tracker -lt 60) { $errors += "wave64_tracker_row_count_below_60" }
  if (@($Report.required_domains_missing).Count -ne 0) { $errors += "wave64_required_domains_missing" }
  if (@($Report.errors).Count -ne 0) { $errors += "wave64_errors_present" }

  foreach ($property in $Report.legacy_items_master_citation_integrity.missing_counts.PSObject.Properties) {
    if ([int]$property.Value -ne 0) { $errors += "legacy_items_missing_$($property.Name)" }
  }
  foreach ($property in $Report.legacy_tracker_master_citation_integrity.missing_counts.PSObject.Properties) {
    if ([int]$property.Value -ne 0) { $errors += "legacy_tracker_missing_$($property.Name)" }
  }

  return [ordered]@{
    result = $(if ($errors.Count -eq 0) { "pass" } else { "fail" })
    errors = $errors
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
  throw "Python executable not found; cannot run Items/Tracker validators."
}

$trackerRoot = Join-Path $ProjectRoot "Plan\Tracker"
$itemsRoot = Join-Path $ProjectRoot "Plan\Items"
$trackerValidator = Join-Path $trackerRoot "Scripts\validate_tracker_package.py"
$itemsValidator = Join-Path $itemsRoot "Scripts\validate_items_package.py"
$wave64Validator = Join-Path $itemsRoot "Scripts\generate_wave64_end_to_end_ai_coverage.py"
$trackerReportPath = Join-Path $trackerRoot "Reports\tracker_validation_report.json"
$itemsReportPath = Join-Path $itemsRoot "Reports\items_validation_report.json"
$wave64ItemsReportPath = Join-Path $itemsRoot "Reports\wave64_end_to_end_strict_ai_coverage_report.json"
$wave64TrackerReportPath = Join-Path $trackerRoot "Reports\wave64_end_to_end_strict_ai_coverage_report.json"

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Items_Tracker_Validation\W59_W60_ITEMS_TRACKER_CURRENT_VALIDATION_$stamp.json"
}

$trackerRun = Invoke-ProcessCapture -FileName $pythonCommand.Source -Arguments @($trackerValidator, $trackerRoot)
$itemsRun = Invoke-ProcessCapture -FileName $pythonCommand.Source -Arguments @($itemsValidator, $itemsRoot)
$wave64Run = Invoke-ProcessCapture -FileName $pythonCommand.Source -Arguments @($wave64Validator)
$trackerReport = Read-JsonFile -Path $trackerReportPath
$itemsReport = Read-JsonFile -Path $itemsReportPath
$wave64Report = Read-JsonFile -Path $wave64ItemsReportPath
$trackerReportCheck = Test-ValidatorReport -Report $trackerReport
$itemsReportCheck = Test-ValidatorReport -Report $itemsReport
$wave64ReportCheck = Test-Wave64Report -Report $wave64Report

$failures = @()
if ($trackerRun.exit_code -ne 0) { $failures += "tracker_validator_exit_$($trackerRun.exit_code)" }
if ($itemsRun.exit_code -ne 0) { $failures += "items_validator_exit_$($itemsRun.exit_code)" }
if ($wave64Run.exit_code -ne 0) { $failures += "wave64_validator_exit_$($wave64Run.exit_code)" }
if ($trackerReportCheck.result -ne "pass") { $failures += "tracker_report_failed" }
if ($itemsReportCheck.result -ne "pass") { $failures += "items_report_failed" }
if ($wave64ReportCheck.result -ne "pass") { $failures += "wave64_report_failed" }

$record = [ordered]@{
  evidence_id = "EVID-W59-W60-ITEMS-TRACKER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W59-002-TRK-W59-003"
  artifact_type = "items_tracker_package_current_validation"
  tracker_ids = @("TRK-W59-002", "TRK-W59-003", "TRK-W60-010")
  qa_protocol_used = @(
    "TRACKER_UPDATE_PROTOCOL.md",
    "ITEMIZED_LIST_UPDATE_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  python = [ordered]@{
    executable = $pythonCommand.Source
    version_command = "python --version"
  }
  validations = [ordered]@{
    tracker = [ordered]@{
      validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $trackerValidator
      root = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $trackerRoot
      exit_code = $trackerRun.exit_code
      stdout_tail = Get-OutputTail -Text $trackerRun.stdout
      stderr_tail = Get-OutputTail -Text $trackerRun.stderr
      report_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $trackerReportPath
      report = $trackerReport
      report_check = $trackerReportCheck
    }
    items = [ordered]@{
      validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $itemsValidator
      root = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $itemsRoot
      exit_code = $itemsRun.exit_code
      stdout_tail = Get-OutputTail -Text $itemsRun.stdout
      stderr_tail = Get-OutputTail -Text $itemsRun.stderr
      report_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $itemsReportPath
      report = $itemsReport
      report_check = $itemsReportCheck
    }
    wave64_strict_ai_coverage = [ordered]@{
      validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $wave64Validator
      exit_code = $wave64Run.exit_code
      stdout_tail = Get-OutputTail -Text $wave64Run.stdout
      stderr_tail = Get-OutputTail -Text $wave64Run.stderr
      items_report_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $wave64ItemsReportPath
      tracker_report_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $wave64TrackerReportPath
      report = $wave64Report
      report_check = $wave64ReportCheck
    }
  }
  result = $(if ($failures.Count -eq 0) { "pass_local_only" } else { "fail" })
  failures = $failures
  known_issues = @(
    "This validates package ledger structure and Wave64 strict AI coverage only. It does not claim EC2 runtime proof, ComfyUI generation, model load, artifact pullback, or completed media QA.",
    "Wave64 rows define required visual/audio/whole-artifact QA gates; each generated artifact still needs its own evidence record before completion."
  )
  next_action = "Use Wave64 Items/Tracker rows as the strict AI execution and QA map; continue local validations where possible and only use EC2 for target-runtime proof."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote Items/Tracker validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
