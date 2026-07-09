<#
.SYNOPSIS
Fail-closed geometry validator for Wave70 mask rows.

.DESCRIPTION
Blocks Wave70 mask pass/candidate/accepted statuses unless the row cites a
hard geometry-gate evidence record. This validator does not run ComfyUI,
AWS, GitHub, Civitai, or visual generation. It audits current Tracker/Items
state and makes unsupported geometry-pass claims mechanically visible.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutJson = "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_LATEST.json"
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Get-RelativePathCompat {
  param([string]$BasePath, [string]$TargetPath)
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("\", "/")
}

function Convert-ToProjectPath {
  param([string]$Path)
  return (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath (Resolve-ProjectPath -Path $Path))
}

function Write-JsonNoBom {
  param([object]$Value, [string]$Path, [int]$Depth = 80)
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Test-PassLikeStatus {
  param([string]$Status)
  if ([string]::IsNullOrWhiteSpace($Status)) { return $false }
  if ($Status -match "Needs_Revision|Fail|Blocked|Unreviewed|Required_Not_Complete|Not_Visible|Too_Low") { return $false }
  return ($Status -match "Candidate_Pass|Mask_Alignment_Pass|Single_Anchor_Mask_Alignment_Pass|Matrix_Mask_Alignment_Pass|Generated_Output_Proof_Pass|Certification_Ready|Complete")
}

function Test-GeometryRequirementToken {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match "wave70_mask_geometry_gate_pass|W70_MASK_GEOMETRY_HARD_GATE|MASK_GEOMETRY_HARD_GATE")
}

function Test-ModelBackedGeometryRequirementToken {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match "model_backed_geometry_authority_pass|MODEL_BACKED_GEOMETRY_AUTHORITY|source_derived_landmark_or_segmentation_pass")
}

function Test-WholeBodyGeometryRequirementToken {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match "whole_body_geometry_authority_pass|WHOLE_BODY_GEOMETRY_AUTHORITY|pose_hand_dense_landmark_or_segmentation_pass")
}

function Test-ExplicitGeometryApprovalToken {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match "W70_MASK_GEOMETRY_ROW_GATE_PASS_TRUE")
}

function Test-ExplicitModelBackedGeometryApprovalToken {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match "W70_MODEL_BACKED_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE")
}

function Test-ExplicitWholeBodyGeometryApprovalToken {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match "W70_WHOLE_BODY_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE")
}

function Get-RowText {
  param([object]$Row)
  $parts = @()
  foreach ($name in @("Completion_Criteria", "Acceptance_Criteria", "Acceptance_Evidence", "Evidence_Path", "Evidence_Required", "Validation_Method", "QA_Gates_Required", "Visual_Review_Method", "Coverage_Audit_Status", "Status_Decision", "Notes")) {
    $prop = $Row.PSObject.Properties[$name]
    if ($prop -and $prop.Value) { $parts += [string]$prop.Value }
  }
  return ($parts -join "; ")
}

function Read-CsvRows {
  param([string]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Missing CSV: $resolved" }
  return Import-Csv -LiteralPath $resolved
}

$trackerMain = "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv"
$trackerMirror = "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv"
$itemsMain = "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv"
$itemsMirror = "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv"

$trackerRows = Read-CsvRows -Path $trackerMain
$trackerMirrorRows = Read-CsvRows -Path $trackerMirror
$itemRows = Read-CsvRows -Path $itemsMain
$itemMirrorRows = Read-CsvRows -Path $itemsMirror
$coverageMatrix = Read-CsvRows -Path "Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_COVERAGE_MATRIX.csv"

$failures = @()
$warnings = @()
$checkedRows = @()

$expectedWave70RowCount = 166
$requiredTrackerIds = @()
$requiredItemIds = @()
$requiredCoverageItemIds = @()

if ($trackerRows.Count -ne $expectedWave70RowCount) {
  $failures += "Tracker row count must be $expectedWave70RowCount, found $($trackerRows.Count). Missing rows cannot be hidden behind gate evidence."
}
if ($trackerMirrorRows.Count -ne $expectedWave70RowCount) {
  $failures += "Tracker mirror row count must be $expectedWave70RowCount, found $($trackerMirrorRows.Count)."
}
if ($itemRows.Count -ne $expectedWave70RowCount) {
  $failures += "Item row count must be $expectedWave70RowCount, found $($itemRows.Count). Missing rows cannot be hidden behind gate evidence."
}
if ($itemMirrorRows.Count -ne $expectedWave70RowCount) {
  $failures += "Item mirror row count must be $expectedWave70RowCount, found $($itemMirrorRows.Count)."
}

$trackerIdSet = @{}
foreach ($row in $trackerRows) { $trackerIdSet[$row.Tracker_ID] = $true }
foreach ($id in $requiredTrackerIds) {
  if (!$trackerIdSet.ContainsKey($id)) { $failures += "Required Wave70 Tracker row missing: $id" }
}

$itemIdSet = @{}
foreach ($row in $itemRows) { $itemIdSet[$row.Item_ID] = $true }
foreach ($id in $requiredItemIds) {
  if (!$itemIdSet.ContainsKey($id)) { $failures += "Required Wave70 Item row missing: $id" }
}

if ($coverageMatrix.Count -lt 137) {
  $failures += "Coverage matrix must contain at least 137 rows after cleanup, found $($coverageMatrix.Count)."
}
$coverageItemIdSet = @{}
foreach ($row in $coverageMatrix) { $coverageItemIdSet[$row.item_id] = $true }
foreach ($id in $requiredCoverageItemIds) {
  if (!$coverageItemIdSet.ContainsKey($id)) { $failures += "Required Wave70 coverage row missing: $id" }
}

foreach ($row in $trackerRows) {
  $rowText = Get-RowText -Row $row
  $hasGeometryRequirement = Test-GeometryRequirementToken -Text $rowText
  $hasModelBackedGeometryRequirement = Test-ModelBackedGeometryRequirementToken -Text $rowText
  $hasWholeBodyGeometryRequirement = Test-WholeBodyGeometryRequirementToken -Text $rowText
  $isPassLike = Test-PassLikeStatus -Status $row.Status
  if (!$hasGeometryRequirement) {
    $failures += "Tracker row $($row.Tracker_ID) lacks wave70_mask_geometry_gate_pass requirement/evidence token."
  }
  if (!$hasModelBackedGeometryRequirement) {
    $failures += "Tracker row $($row.Tracker_ID) lacks model_backed_geometry_authority_pass requirement/evidence token."
  }
  if (!$hasWholeBodyGeometryRequirement) {
    $failures += "Tracker row $($row.Tracker_ID) lacks whole_body_geometry_authority_pass requirement/evidence token."
  }
  if ($isPassLike -and !(Test-ExplicitGeometryApprovalToken -Text $rowText)) {
    $failures += "Tracker row $($row.Tracker_ID) has pass-like status but no explicit passed geometry-gate evidence: $($row.Status)"
  }
  if ($isPassLike -and !(Test-ExplicitModelBackedGeometryApprovalToken -Text $rowText)) {
    $failures += "Tracker row $($row.Tracker_ID) has pass-like status but no explicit passed model-backed geometry authority evidence: $($row.Status)"
  }
  if ($isPassLike -and !(Test-ExplicitWholeBodyGeometryApprovalToken -Text $rowText)) {
    $failures += "Tracker row $($row.Tracker_ID) has pass-like status but no explicit passed whole-body geometry authority evidence: $($row.Status)"
  }
  $checkedRows += [ordered]@{
    row_type = "tracker"
    id = $row.Tracker_ID
    item_id = $row.Source_Item_ID
    status = $row.Status
    pass_like_status = $isPassLike
    has_geometry_requirement_token = $hasGeometryRequirement
    has_model_backed_geometry_requirement_token = $hasModelBackedGeometryRequirement
    has_whole_body_geometry_requirement_token = $hasWholeBodyGeometryRequirement
    has_explicit_geometry_approval_token = Test-ExplicitGeometryApprovalToken -Text $rowText
    has_explicit_model_backed_geometry_approval_token = Test-ExplicitModelBackedGeometryApprovalToken -Text $rowText
    has_explicit_whole_body_geometry_approval_token = Test-ExplicitWholeBodyGeometryApprovalToken -Text $rowText
    source_key = $row.Source_Key
  }
}

foreach ($row in $itemRows) {
  $rowText = Get-RowText -Row $row
  $hasGeometryRequirement = Test-GeometryRequirementToken -Text $rowText
  $hasModelBackedGeometryRequirement = Test-ModelBackedGeometryRequirementToken -Text $rowText
  $hasWholeBodyGeometryRequirement = Test-WholeBodyGeometryRequirementToken -Text $rowText
  $isPassLike = Test-PassLikeStatus -Status $row.Status
  if (!$hasGeometryRequirement) {
    $failures += "Item row $($row.Item_ID) lacks wave70_mask_geometry_gate_pass requirement/evidence token."
  }
  if (!$hasModelBackedGeometryRequirement) {
    $failures += "Item row $($row.Item_ID) lacks model_backed_geometry_authority_pass requirement/evidence token."
  }
  if (!$hasWholeBodyGeometryRequirement) {
    $failures += "Item row $($row.Item_ID) lacks whole_body_geometry_authority_pass requirement/evidence token."
  }
  if ($isPassLike -and !(Test-ExplicitGeometryApprovalToken -Text $rowText)) {
    $failures += "Item row $($row.Item_ID) has pass-like status but no explicit passed geometry-gate evidence: $($row.Status)"
  }
  if ($isPassLike -and !(Test-ExplicitModelBackedGeometryApprovalToken -Text $rowText)) {
    $failures += "Item row $($row.Item_ID) has pass-like status but no explicit passed model-backed geometry authority evidence: $($row.Status)"
  }
  if ($isPassLike -and !(Test-ExplicitWholeBodyGeometryApprovalToken -Text $rowText)) {
    $failures += "Item row $($row.Item_ID) has pass-like status but no explicit passed whole-body geometry authority evidence: $($row.Status)"
  }
  $checkedRows += [ordered]@{
    row_type = "item"
    id = $row.Item_ID
    status = $row.Status
    pass_like_status = $isPassLike
    has_geometry_requirement_token = $hasGeometryRequirement
    has_model_backed_geometry_requirement_token = $hasModelBackedGeometryRequirement
    has_whole_body_geometry_requirement_token = $hasWholeBodyGeometryRequirement
    has_explicit_geometry_approval_token = Test-ExplicitGeometryApprovalToken -Text $rowText
    has_explicit_model_backed_geometry_approval_token = Test-ExplicitModelBackedGeometryApprovalToken -Text $rowText
    has_explicit_whole_body_geometry_approval_token = Test-ExplicitWholeBodyGeometryApprovalToken -Text $rowText
    source_key = $row.Source_Key
  }
}

$trackerMirrorById = @{}
foreach ($row in $trackerMirrorRows) { $trackerMirrorById[$row.Tracker_ID] = $row }
foreach ($row in $trackerRows) {
  if (!$trackerMirrorById.ContainsKey($row.Tracker_ID)) {
    $failures += "Tracker mirror missing row $($row.Tracker_ID)."
    continue
  }
  $mirror = $trackerMirrorById[$row.Tracker_ID]
  if ($mirror.Status -ne $row.Status) {
    $failures += "Tracker mirror status mismatch for $($row.Tracker_ID): main=$($row.Status) mirror=$($mirror.Status)"
  }
}

$itemMirrorById = @{}
foreach ($row in $itemMirrorRows) { $itemMirrorById[$row.Item_ID] = $row }
foreach ($row in $itemRows) {
  if (!$itemMirrorById.ContainsKey($row.Item_ID)) {
    $failures += "Item mirror missing row $($row.Item_ID)."
    continue
  }
  $mirror = $itemMirrorById[$row.Item_ID]
  if ($mirror.Status -ne $row.Status) {
    $failures += "Item mirror status mismatch for $($row.Item_ID): main=$($row.Status) mirror=$($mirror.Status)"
  }
}

$passLikeCount = @($checkedRows | Where-Object { $_.pass_like_status }).Count
$missingGeometryRequirementCount = @($checkedRows | Where-Object { !$_.has_geometry_requirement_token }).Count
$missingModelBackedGeometryRequirementCount = @($checkedRows | Where-Object { !$_.has_model_backed_geometry_requirement_token }).Count
$missingWholeBodyGeometryRequirementCount = @($checkedRows | Where-Object { !$_.has_whole_body_geometry_requirement_token }).Count
$result = if ($failures.Count -eq 0) { "pass_wave70_mask_geometry_hard_gate" } else { "fail_wave70_mask_geometry_hard_gate" }

$outResolved = Resolve-ProjectPath -Path $OutJson
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outResolved) | Out-Null

$evidence = [ordered]@{
  schema_version = "1.0"
  evidence_id = "W70-MASK-GEOMETRY-HARD-GATE"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  qa_type = "wave70_mask_geometry_hard_gate_validator"
  validator = Convert-ToProjectPath -Path $PSCommandPath
  result = $result
  wave70_mask_geometry_gate_validator_pass = ($failures.Count -eq 0)
  pass_like_row_count = $passLikeCount
  missing_geometry_requirement_count = $missingGeometryRequirementCount
  missing_model_backed_geometry_requirement_count = $missingModelBackedGeometryRequirementCount
  missing_whole_body_geometry_requirement_count = $missingWholeBodyGeometryRequirementCount
  checked_row_count = $checkedRows.Count
  failures = $failures
  warnings = $warnings
  checked_rows = $checkedRows
  rule = "No Wave70 mask pass/candidate/complete status is allowed without explicit model-backed geometry authority, whole-body geometry authority, and geometry-gate evidence. Every Wave70 row must carry all requirements."
}

Write-JsonNoBom -Value $evidence -Path $outResolved -Depth 90

if ($failures.Count -gt 0) {
  Write-Error "Wave70 mask geometry hard gate failed with $($failures.Count) failure(s). Evidence: $outResolved"
}

Write-Output "Wave70 mask geometry hard gate passed. Evidence: $outResolved"
