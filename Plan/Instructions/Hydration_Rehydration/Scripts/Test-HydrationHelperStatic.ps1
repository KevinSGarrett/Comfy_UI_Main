<#
.SYNOPSIS
Validates the current Wave 62 hydration helpers with local-only checks.

.DESCRIPTION
Parses Hydration_Rehydration scripts, validates hydration templates, smoke-runs
session-state generation into a redacted temp folder, and runs the cumulative
pack validator against the current Wave 58-62 zip if present. This does not run
EC2, ComfyUI, Civitai, model loading, generation, or artifact QA.
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

function Test-TemplateFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    type = $extension.TrimStart(".")
    result = "fail"
    row_count = $null
    error = $null
  }

  try {
    if ($extension -eq ".json") {
      $null = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
      $entry.result = "pass"
    } elseif ($extension -eq ".csv") {
      $rows = @(Import-Csv -LiteralPath $Path)
      $entry.row_count = $rows.Count
      $entry.result = "pass"
    } else {
      $text = Get-Content -LiteralPath $Path -Raw
      $entry.result = $(if (![string]::IsNullOrWhiteSpace($text)) { "pass" } else { "fail" })
    }
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

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$hydrationRoot = Join-Path $ProjectRoot "Plan\Instructions\Hydration_Rehydration"
$scriptsRoot = Join-Path $hydrationRoot "Scripts"
$templatesRoot = Join-Path $hydrationRoot "Templates"
$tempRoot = Join-Path $env:TEMP "comfy_ui_hydration_static_validation_$stamp"
$script:ValidationTempRoot = $tempRoot
$null = New-Item -ItemType Directory -Force -Path $tempRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Hydration_Helper_Static_Validation\W62_HYDRATION_HELPER_CURRENT_VALIDATION_$stamp.json"
}

$scriptParseResults = @()
foreach ($script in Get-ChildItem -LiteralPath $scriptsRoot -Filter "*.ps1" -File | Sort-Object Name) {
  $scriptParseResults += Test-PowerShellParser -Path $script.FullName
}

$templateResults = @()
foreach ($template in Get-ChildItem -LiteralPath $templatesRoot -File | Sort-Object Name) {
  $templateResults += Test-TemplateFile -Path $template.FullName
}

$sessionStateFile = Join-Path $tempRoot "sample_session_state.json"
$sessionStateSmoke = Invoke-LocalHelper -Name "session_state_generation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SessionState.ps1") `
  -Arguments @("-SessionId", "SESSION-W62-CURRENT-SAMPLE", "-OutFile", $sessionStateFile) `
  -ExpectedOutputFile $sessionStateFile `
  -ExpectedOutputType "json"

$zipFiles = @(Get-ChildItem -LiteralPath $ProjectRoot -Filter "*.zip" -File | Sort-Object LastWriteTime -Descending)
$selectedZip = $zipFiles | Select-Object -First 1
$zipValidation = [ordered]@{
  zip_count = $zipFiles.Count
  selected_zip = $null
  selected_zip_size_bytes = $null
  selected_zip_sha256 = $null
  command_exit_code = $null
  output_tail = $null
  result = "not_run"
  error = $null
}

if ($null -ne $selectedZip) {
  $zipValidation.selected_zip = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $selectedZip.FullName
  $zipValidation.selected_zip_size_bytes = $selectedZip.Length
  $zipValidation.selected_zip_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $selectedZip.FullName).Hash.ToLowerInvariant()
  $zipOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptsRoot "Test-CumulativeWavePack.ps1") -ZipPath $selectedZip.FullName 2>&1
  $zipText = (($zipOutput | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $zipValidation.command_exit_code = $LASTEXITCODE
  $zipValidation.output_tail = $(if ($zipText.Length -gt 1000) { $zipText.Substring($zipText.Length - 1000) } else { $zipText })
  $zipValidation.result = $(if ($LASTEXITCODE -eq 0) { "pass" } else { "fail" })
} else {
  $zipValidation.error = "No cumulative zip found under project root."
}

$scriptFailures = @($scriptParseResults | Where-Object { $_.result -ne "pass" })
$templateFailures = @($templateResults | Where-Object { $_.result -ne "pass" })
$smokeFailures = @($sessionStateSmoke | Where-Object { $_.result -ne "pass" -or -not $_.expected_output_valid })
$zipFailures = @()
if ($zipValidation.result -ne "pass") { $zipFailures += $zipValidation }

$record = [ordered]@{
  evidence_id = "EVID-W62-HYDRATION-HELPER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W62-003-TRK-W62-009"
  artifact_type = "hydration_helper_current_static_validation"
  tracker_ids = @("TRK-W62-003", "TRK-W62-009")
  item_ids = @("ITEM-W62-003", "ITEM-W62-009")
  qa_protocol_used = @(
    "SESSION_START_REHYDRATION_CHECKLIST.md",
    "SESSION_END_HYDRATION_CHECKLIST.md",
    "CUMULATIVE_WAVE_PACK_BUILD_PROTOCOL.md",
    "TRACKER_UPDATE_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Instructions/Hydration_Rehydration/Scripts/*.ps1",
    "Plan/Instructions/Hydration_Rehydration/Templates/*",
    "session state generation smoke",
    "current cumulative Wave 58-62 zip validation"
  )
  validation_results = [ordered]@{
    script_count = @($scriptParseResults).Count
    script_parse_failures = @($scriptFailures).Count
    script_parse_results = $scriptParseResults
    template_count = @($templateResults).Count
    template_failures = @($templateFailures).Count
    template_results = $templateResults
    session_state_smoke = $sessionStateSmoke
    cumulative_pack_validation = $zipValidation
  }
  temp_root = "[VALIDATION_TEMP_ROOT]"
  temp_root_redacted = $true
  result = $(if ($scriptFailures.Count -eq 0 -and $templateFailures.Count -eq 0 -and $smokeFailures.Count -eq 0 -and $zipFailures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_issues = @(
    "This validates hydration helpers and the current cumulative instruction pack zip only.",
    "Live AWS/EC2 execution, Civitai downloads, ComfyUI generation, model loading, artifact pullback, and media QA remain separate runtime validations."
  )
  next_action = "After AWS browser login refresh, rerun auth gate, selected-lane readiness, and EC2 static proof."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote hydration helper static validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
