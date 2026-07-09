<#
.SYNOPSIS
Builds a local orchestrator promotion manifest from QA gate evidence.

.DESCRIPTION
Reads a QA promotion gate JSON, optionally a run manifest, and writes a concrete
promotion manifest using the Wave 14/34 promotion contract shape. This helper is
local-only: it does not run ComfyUI, contact AWS/GitHub/Civitai, start EC2, or
turn local evidence into final certification.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$QaPromotionGateFile,
  [string]$RunManifestFile = "",
  [string]$RunId = "",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$TargetPath
  )

  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("\", "/")
}

function Resolve-ProjectPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Convert-ToProjectPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  return Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $Path
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) {
    throw "JSON file not found: $resolved"
  }
  return Get-Content -Raw -LiteralPath $resolved | ConvertFrom-Json
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 40
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Test-JsonProperty {
  param([object]$Object, [string]$Name)
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

$gatePath = Resolve-ProjectPath -Path $QaPromotionGateFile
$gate = Read-JsonFile -Path $gatePath
$runManifest = $null
if (![string]::IsNullOrWhiteSpace($RunManifestFile)) {
  $runManifest = Read-JsonFile -Path $RunManifestFile
}

if ([string]::IsNullOrWhiteSpace($RunId)) {
  if ($null -ne $runManifest -and (Test-JsonProperty -Object $runManifest -Name "run_id")) {
    $RunId = [string]$runManifest.run_id
  } elseif (Test-JsonProperty -Object $gate -Name "evidence_id") {
    $RunId = [string]$gate.evidence_id
  } else {
    $RunId = "orchestrator_promotion_" + (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\manifests\generated"
  New-Item -ItemType Directory -Force -Path $outDir > $null
  $OutFile = Join-Path $outDir "ORCHESTRATOR_PROMOTION_MANIFEST_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outPath) > $null

$promotionAllowed = $false
if (Test-JsonProperty -Object $gate -Name "promotion_allowed") {
  $promotionAllowed = [bool]$gate.promotion_allowed
}

$blockingReasons = New-Object System.Collections.ArrayList
if (Test-JsonProperty -Object $gate -Name "reasons") {
  foreach ($reason in @($gate.reasons)) {
    if (![string]::IsNullOrWhiteSpace([string]$reason)) { [void]$blockingReasons.Add([string]$reason) }
  }
}
if ((Test-JsonProperty -Object $gate -Name "parse_error_count") -and [int]$gate.parse_error_count -gt 0) {
  [void]$blockingReasons.Add("qa_gate_parse_errors_present")
}
if ((Test-JsonProperty -Object $gate -Name "blocking_row_count") -and [int]$gate.blocking_row_count -gt 0) {
  [void]$blockingReasons.Add("qa_gate_blocking_rows_present")
}
if ((Test-JsonProperty -Object $gate -Name "target_runtime_block_count") -and [int]$gate.target_runtime_block_count -gt 0) {
  [void]$blockingReasons.Add("qa_gate_target_runtime_blocks_present")
}

$promotionStatus = "not_ready"
if ($promotionAllowed -and $blockingReasons.Count -eq 0) {
  $promotionStatus = "ready_for_promotion"
} elseif ((Test-JsonProperty -Object $gate -Name "promotion_decision") -and ![string]::IsNullOrWhiteSpace([string]$gate.promotion_decision)) {
  $promotionStatus = [string]$gate.promotion_decision
}

$failedPasses = New-Object System.Collections.ArrayList
if (Test-JsonProperty -Object $gate -Name "blocking_rows") {
  foreach ($row in @($gate.blocking_rows)) {
    [void]$failedPasses.Add([ordered]@{
      evidence = [string]$row
      reason = "blocking_or_failed_qa_row"
    })
  }
}
if (Test-JsonProperty -Object $gate -Name "parse_errors") {
  foreach ($err in @($gate.parse_errors)) {
    [void]$failedPasses.Add([ordered]@{
      evidence = [string]$err.path
      reason = "parse_error"
      detail = [string]$err.error
    })
  }
}

$passedPasses = New-Object System.Collections.ArrayList
if (Test-JsonProperty -Object $gate -Name "qa_sheet_csv") {
  [void]$passedPasses.Add([ordered]@{
    pass_id = "qa_sheet_export"
    status = "completed"
    evidence = [string]$gate.qa_sheet_csv
  })
}
if ((Test-JsonProperty -Object $gate -Name "parse_error_count") -and [int]$gate.parse_error_count -eq 0) {
  [void]$passedPasses.Add([ordered]@{
    pass_id = "qa_gate_parse_check"
    status = "passed"
    evidence = Convert-ToProjectPath -Path $gatePath
  })
}

$manifest = [ordered]@{
  schema_version = "1.0"
  manifest_type = "orchestrator_promotion_manifest"
  run_id = $RunId
  generated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  promotion_status = $promotionStatus
  promotion_allowed = $promotionAllowed -and $blockingReasons.Count -eq 0
  qa_promotion_gate = Convert-ToProjectPath -Path $gatePath
  run_manifest = $(if ([string]::IsNullOrWhiteSpace($RunManifestFile)) { $null } else { Convert-ToProjectPath -Path (Resolve-ProjectPath -Path $RunManifestFile) })
  passed_passes = @($passedPasses)
  failed_passes = @($failedPasses)
  promoted_outputs = @()
  blocking_reasons = @($blockingReasons)
  gate_summary = [ordered]@{
    exported_row_count = $(if (Test-JsonProperty -Object $gate -Name "exported_row_count") { $gate.exported_row_count } else { $null })
    parse_error_count = $(if (Test-JsonProperty -Object $gate -Name "parse_error_count") { $gate.parse_error_count } else { $null })
    blocking_row_count = $(if (Test-JsonProperty -Object $gate -Name "blocking_row_count") { $gate.blocking_row_count } else { $null })
    target_runtime_block_count = $(if (Test-JsonProperty -Object $gate -Name "target_runtime_block_count") { $gate.target_runtime_block_count } else { $null })
    gate_decision = $(if (Test-JsonProperty -Object $gate -Name "promotion_decision") { $gate.promotion_decision } else { $null })
  }
  boundary = "Promotion manifest generated from existing local QA gate evidence only. It blocks final promotion unless all required runtime, QA, and certification gates are independently proven."
}

Write-JsonNoBom -Value $manifest -Path $outPath -Depth 60

[pscustomobject]@{
  result = "pass_local_orchestrator_promotion_manifest"
  manifest = Convert-ToProjectPath -Path $outPath
  promotion_status = $manifest.promotion_status
  promotion_allowed = $manifest.promotion_allowed
  blocking_reason_count = @($manifest.blocking_reasons).Count
} | ConvertTo-Json -Depth 8
