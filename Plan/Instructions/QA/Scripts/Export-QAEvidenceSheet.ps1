<#
.SYNOPSIS
Exports image QA evidence into a review sheet and local promotion-gate record.

.DESCRIPTION
Scans structured Image_Artifact_QA JSON evidence, writes a compact CSV sheet for
review, and writes a machine-readable promotion-gate summary. This is a local-only
QA utility: it does not inspect pixels, run ComfyUI, contact AWS/GitHub/Civitai, or
certify final release by itself.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$EvidenceRoot = "Plan/Instructions/QA/Evidence/Image_Artifact_QA",
  [string]$IncludePattern = "W69_LOCAL_*.json",
  [string]$SupersessionFile = "",
  [string]$OutCsv = "",
  [string]$OutGateJson = "",
  [switch]$RequireTargetRuntimeForPromotion
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
  return (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $Path)
}

function Test-JsonProperty {
  param([object]$Object, [string]$Name)
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

function Get-FirstValue {
  param([object]$Object, [string[]]$Names)
  foreach ($name in $Names) {
    if (Test-JsonProperty -Object $Object -Name $name) {
      $value = $Object.$name
      if ($null -ne $value -and ![string]::IsNullOrWhiteSpace([string]$value)) { return $value }
    }
  }
  return $null
}

function Convert-ToBooleanText {
  param([object]$Value)
  if ($null -eq $Value) { return "unknown" }
  if ($Value -is [bool]) { return $Value.ToString().ToLowerInvariant() }
  return [string]$Value
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 30
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Normalize-ProjectRelativeKey {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  return $Path.Replace("\", "/").Trim().ToLowerInvariant()
}

$evidenceRootPath = Resolve-ProjectPath -Path $EvidenceRoot
if (!(Test-Path -LiteralPath $evidenceRootPath -PathType Container)) {
  throw "Evidence root not found: $evidenceRootPath"
}

$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$stampForFile = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$defaultOutDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\QA_Sheets"
New-Item -ItemType Directory -Force -Path $defaultOutDir > $null

if ([string]::IsNullOrWhiteSpace($OutCsv)) {
  $OutCsv = Join-Path $defaultOutDir "W69_LOCAL_IMAGE_QA_SHEET_$stampForFile.csv"
}
if ([string]::IsNullOrWhiteSpace($OutGateJson)) {
  $OutGateJson = Join-Path $defaultOutDir "W69_LOCAL_IMAGE_QA_PROMOTION_GATE_$stampForFile.json"
}

$supersessionMapPath = $null
$supersessionRecord = $null
$supersededBySource = @{}
$supersededByEvidenceId = @{}
$supersessionParseError = $null

if (![string]::IsNullOrWhiteSpace($SupersessionFile)) {
  $supersessionMapPath = Resolve-ProjectPath -Path $SupersessionFile
  try {
    $supersessionRecord = Get-Content -Raw -LiteralPath $supersessionMapPath | ConvertFrom-Json
    foreach ($entry in @($supersessionRecord.supersessions)) {
      if ($null -eq $entry) { continue }
      $entryResult = [string](Get-FirstValue -Object $entry -Names @("supersession_result", "result", "status"))
      if ($entryResult -notmatch "accepted|pass|superseded") { continue }
      $sourceKey = Normalize-ProjectRelativeKey -Path ([string]$entry.superseded_source_file)
      $evidenceKey = ([string]$entry.superseded_evidence_id).Trim().ToLowerInvariant()
      if (![string]::IsNullOrWhiteSpace($sourceKey)) { $supersededBySource[$sourceKey] = $entry }
      if (![string]::IsNullOrWhiteSpace($evidenceKey)) { $supersededByEvidenceId[$evidenceKey] = $entry }
    }
  } catch {
    $supersessionParseError = $_.Exception.Message
  }
}

$files = @(Get-ChildItem -LiteralPath $evidenceRootPath -File -Filter $IncludePattern | Sort-Object Name)
$rows = New-Object System.Collections.ArrayList
$parseErrors = New-Object System.Collections.ArrayList
$blockingRows = New-Object System.Collections.ArrayList
$targetRuntimeBlocks = New-Object System.Collections.ArrayList
$supersededRows = New-Object System.Collections.ArrayList

foreach ($file in $files) {
  try {
    $qa = Get-Content -Raw -LiteralPath $file.FullName | ConvertFrom-Json
  } catch {
    [void]$parseErrors.Add([ordered]@{
      path = Convert-ToProjectPath -Path $file.FullName
      error = $_.Exception.Message
    })
    continue
  }

  $evidenceId = [string](Get-FirstValue -Object $qa -Names @("evidence_id"))
  $sourceFileRel = Convert-ToProjectPath -Path $file.FullName
  $result = [string](Get-FirstValue -Object $qa -Names @("overall_result", "qa_result", "strict_qa_result", "result", "qa_status"))
  if ([string]::IsNullOrWhiteSpace($result) -and (Test-JsonProperty -Object $qa -Name "decision") -and (Test-JsonProperty -Object $qa.decision -Name "result")) {
    $result = [string]$qa.decision.result
  }
  if ([string]::IsNullOrWhiteSpace($result) -and (Test-JsonProperty -Object $qa -Name "scores")) {
    if ($qa.scores.technical_integrity -eq "pass" -and $qa.scores.resolution_check -eq "pass" -and $qa.scores.visual_review -eq "pending_visual_review") {
      $result = "technical_pass_pending_visual_review"
    } elseif ($qa.scores.visual_review -eq "pending_visual_review") {
      $result = "visual_review_pending"
    }
  }
  $certStatus = [string](Get-FirstValue -Object $qa -Names @("certification_status", "certification_scope"))
  $laneId = [string](Get-FirstValue -Object $qa -Names @("lane_id"))
  $moduleId = [string](Get-FirstValue -Object $qa -Names @("module_id"))
  $artifactPath = $null
  $artifactSha = $null
  $artifactWidth = $null
  $artifactHeight = $null

  if ((Test-JsonProperty -Object $qa -Name "sample") -and (Test-JsonProperty -Object $qa.sample -Name "output_path")) {
    $artifactPath = $qa.sample.output_path
  } elseif (Test-JsonProperty -Object $qa -Name "generated_artifacts") {
    $firstArtifact = @($qa.generated_artifacts)[0]
    if ($null -ne $firstArtifact -and (Test-JsonProperty -Object $firstArtifact -Name "path")) { $artifactPath = $firstArtifact.path }
  }

  if (Test-JsonProperty -Object $qa -Name "technical_checks") {
    $artifactSha = $qa.technical_checks.sha256
    $artifactWidth = $qa.technical_checks.width
    $artifactHeight = $qa.technical_checks.height
  } elseif (Test-JsonProperty -Object $qa -Name "image") {
    if ([string]::IsNullOrWhiteSpace($artifactPath)) { $artifactPath = $qa.image.display_path }
    $artifactSha = $qa.image.sha256
    $artifactWidth = $qa.image.width
    $artifactHeight = $qa.image.height
  } elseif (Test-JsonProperty -Object $qa -Name "generated_image") {
    if ([string]::IsNullOrWhiteSpace($artifactPath)) { $artifactPath = $qa.generated_image.path }
    $artifactSha = $qa.generated_image.sha256
    if (Test-JsonProperty -Object $qa.generated_image -Name "dimensions") {
      $dims = ([string]$qa.generated_image.dimensions).Split("x")
      if ($dims.Count -eq 2) {
        $artifactWidth = $dims[0]
        $artifactHeight = $dims[1]
      }
    }
  } elseif (Test-JsonProperty -Object $qa -Name "generated_artifacts") {
    $firstArtifact = @($qa.generated_artifacts)[0]
    if ($null -ne $firstArtifact) {
      $artifactSha = $firstArtifact.sha256
      $artifactWidth = $firstArtifact.width
      $artifactHeight = $firstArtifact.height
    }
  }

  $runtime = $qa.runtime_boundaries
  $localOnly = $qa.local_only
  if ($null -eq $localOnly -and $null -ne $runtime) { $localOnly = $runtime.local_comfyui_used -and !$runtime.ec2_started }
  $ec2Started = $null
  if ($null -ne $runtime) { $ec2Started = $runtime.ec2_started }
  if ($null -eq $ec2Started -and (Test-JsonProperty -Object $qa -Name "ec2_started")) { $ec2Started = $qa.ec2_started }

  $promotionAllowed = $null
  if ((Test-JsonProperty -Object $qa -Name "qa_decision") -and (Test-JsonProperty -Object $qa.qa_decision -Name "promotion_allowed")) {
    $promotionAllowed = $qa.qa_decision.promotion_allowed
  } elseif (Test-JsonProperty -Object $qa -Name "certification_allowed") {
    $promotionAllowed = $qa.certification_allowed
  } elseif (Test-JsonProperty -Object $qa -Name "final_decision_allowed") {
    $promotionAllowed = $qa.final_decision_allowed
  }

  $isFailure = $false
  if ($result -match "fail|failed|blocked|reject") { $isFailure = $true }
  $blockingDefectCount = 0
  if (Test-JsonProperty -Object $qa -Name "blocking_defects") { $blockingDefectCount = @($qa.blocking_defects).Count }
  if ($blockingDefectCount -gt 0) { $isFailure = $true }

  $supersessionEntry = $null
  $sourceKey = Normalize-ProjectRelativeKey -Path $sourceFileRel
  $evidenceKey = $evidenceId.Trim().ToLowerInvariant()
  if ($supersededBySource.ContainsKey($sourceKey)) {
    $supersessionEntry = $supersededBySource[$sourceKey]
  } elseif ($supersededByEvidenceId.ContainsKey($evidenceKey)) {
    $supersessionEntry = $supersededByEvidenceId[$evidenceKey]
  }
  $isSuperseded = ($null -ne $supersessionEntry)
  $supersessionStatus = "active"
  $supersededBy = ""
  if ($isSuperseded) {
    $supersessionStatus = "superseded"
    $supersededBy = [string](Get-FirstValue -Object $supersessionEntry -Names @("superseded_by_evidence_id", "superseded_by_source_file"))
  }

  $row = [pscustomobject]@{
    evidence_id = $evidenceId
    timestamp = [string](Get-FirstValue -Object $qa -Names @("timestamp"))
    lane_id = $laneId
    module_id = $moduleId
    result = $result
    supersession_status = $supersessionStatus
    superseded_by = $supersededBy
    certification_status = $certStatus
    promotion_allowed = Convert-ToBooleanText -Value $promotionAllowed
    local_only_or_local_runtime = Convert-ToBooleanText -Value $localOnly
    ec2_started = Convert-ToBooleanText -Value $ec2Started
    output_path = [string]$artifactPath
    sha256 = [string]$artifactSha
    width = $artifactWidth
    height = $artifactHeight
    blocking_defect_count = $blockingDefectCount
    source_file = $sourceFileRel
  }
  [void]$rows.Add($row)

  if ($isSuperseded) {
    [void]$supersededRows.Add($row)
  }
  if ($isFailure -and !$isSuperseded) {
    [void]$blockingRows.Add($row)
  }
  if ($RequireTargetRuntimeForPromotion -and ($ec2Started -ne $true) -and !$isSuperseded) {
    [void]$targetRuntimeBlocks.Add($row)
  }
}

$rows | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $OutCsv

$decision = "local_evidence_sheet_pass_with_boundaries"
$reasons = New-Object System.Collections.ArrayList
if ($parseErrors.Count -gt 0) {
  $decision = "block_promotion_parse_errors"
  [void]$reasons.Add("One or more QA evidence JSON files failed to parse.")
}
if (![string]::IsNullOrWhiteSpace($supersessionParseError)) {
  $decision = "block_promotion_supersession_parse_error"
  [void]$reasons.Add("The supplied QA supersession map failed to parse.")
}
if ($blockingRows.Count -gt 0) {
  $decision = "block_promotion_failed_or_blocked_evidence"
  [void]$reasons.Add("One or more QA evidence rows has a failed, blocked, rejected, or blocking-defect result.")
}
if ($targetRuntimeBlocks.Count -gt 0) {
  $decision = "block_final_promotion_missing_target_runtime"
  [void]$reasons.Add("Target-runtime proof was required for promotion, but one or more rows lack EC2/target-runtime evidence.")
}
if ($rows.Count -eq 0) {
  $decision = "block_promotion_no_matching_evidence"
  [void]$reasons.Add("No matching QA evidence rows were found.")
}
if ($reasons.Count -eq 0) {
  [void]$reasons.Add("Matching local QA evidence parsed and exported. Final promotion remains blocked unless required runtime/certification gates are separately proven.")
}

$gate = [ordered]@{
  schema_version = "1.0"
  evidence_id = "QA-EVIDENCE-SHEET-PROMOTION-GATE-$stampForFile"
  timestamp = $timestamp
  project_root = $ProjectRoot
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  evidence_root = Convert-ToProjectPath -Path $evidenceRootPath
  include_pattern = $IncludePattern
  qa_sheet_csv = Convert-ToProjectPath -Path $OutCsv
  supersession_file = if ($null -ne $supersessionMapPath) { Convert-ToProjectPath -Path $supersessionMapPath } else { $null }
  matching_file_count = $files.Count
  exported_row_count = $rows.Count
  parse_error_count = $parseErrors.Count
  supersession_parse_error = $supersessionParseError
  superseded_row_count = $supersededRows.Count
  blocking_row_count = $blockingRows.Count
  target_runtime_block_count = $targetRuntimeBlocks.Count
  require_target_runtime_for_promotion = [bool]$RequireTargetRuntimeForPromotion
  promotion_decision = $decision
  promotion_allowed = $false
  reasons = @($reasons)
  parse_errors = @($parseErrors)
  superseded_rows = @($supersededRows | ForEach-Object { $_.source_file })
  blocking_rows = @($blockingRows | ForEach-Object { $_.source_file })
  target_runtime_blocks = @($targetRuntimeBlocks | ForEach-Object { $_.source_file })
  boundary = "This exporter creates a review sheet and local gate summary only. It never certifies final release without independent runtime, artifact, and QA proof."
}

Write-JsonNoBom -Value $gate -Path $OutGateJson -Depth 40

[pscustomobject]@{
  result = "pass_local_qa_sheet_export"
  csv = Convert-ToProjectPath -Path $OutCsv
  gate = Convert-ToProjectPath -Path $OutGateJson
  rows = $rows.Count
  promotion_decision = $decision
} | ConvertTo-Json -Depth 8
