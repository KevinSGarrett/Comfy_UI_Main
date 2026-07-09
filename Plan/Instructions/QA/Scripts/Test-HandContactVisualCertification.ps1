<#
.SYNOPSIS
Evaluates stricter hand/contact visual certification from existing QA evidence.

.DESCRIPTION
Consumes a certification request JSON that names source requirements, runtime
evidence, strict visual QA, contact-mask QA, generated images, and visual review
findings. It produces a promotion decision that separates local pass/support
from final certification. No ComfyUI, AWS, GitHub, or Civitai calls are made.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$RequestJson,
  [Parameter(Mandatory=$true)][string]$OutJson
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
  param([object]$Value, [string]$Path, [int]$Depth = 60)
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Read-JsonFile {
  param([string]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Missing JSON file: $resolved" }
  return Get-Content -Raw -LiteralPath $resolved | ConvertFrom-Json
}

function Get-FileSha256Lower {
  param([string]$Path)
  return (Get-FileHash -LiteralPath (Resolve-ProjectPath -Path $Path) -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-Truth {
  param([object]$Object, [string]$Name)
  if ($null -eq $Object) { return $false }
  $property = $Object.PSObject.Properties[$Name]
  if ($null -eq $property) { return $false }
  return ($property.Value -eq $true)
}

$request = Read-JsonFile -Path $RequestJson
$outResolved = Resolve-ProjectPath -Path $OutJson
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outResolved) | Out-Null

Add-Type -AssemblyName System.Drawing

$errors = @()
$warnings = @()
$checkedEvidence = @()

foreach ($path in @($request.source_requirements)) {
  $resolved = Resolve-ProjectPath -Path $path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { $errors += "Missing source requirement: $path" }
  else { $checkedEvidence += Convert-ToProjectPath -Path $path }
}

foreach ($path in @($request.required_evidence_paths)) {
  $resolved = Resolve-ProjectPath -Path $path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { $errors += "Missing required evidence: $path" }
  else { $checkedEvidence += Convert-ToProjectPath -Path $path }
}

foreach ($image in @($request.images)) {
  $resolved = Resolve-ProjectPath -Path $image.path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) {
    $errors += "Missing image: $($image.path)"
    continue
  }
  $actualHash = Get-FileSha256Lower -Path $image.path
  if (![string]::IsNullOrWhiteSpace($image.sha256) -and $actualHash -ne $image.sha256.ToLowerInvariant()) {
    $errors += "Image hash mismatch for $($image.path): $actualHash"
  }
  $bitmap = [System.Drawing.Image]::FromFile($resolved)
  try {
    if ($image.width -and $bitmap.Width -ne [int]$image.width) { $errors += "Image width mismatch for $($image.path): $($bitmap.Width)" }
    if ($image.height -and $bitmap.Height -ne [int]$image.height) { $errors += "Image height mismatch for $($image.path): $($bitmap.Height)" }
  } finally {
    $bitmap.Dispose()
  }
  $checkedEvidence += Convert-ToProjectPath -Path $image.path
}

$contactMaskQa = if ($request.contact_mask_qa_evidence) { Read-JsonFile -Path $request.contact_mask_qa_evidence } else { $null }
$robustnessQa = if ($request.robustness_visual_qa_evidence) { Read-JsonFile -Path $request.robustness_visual_qa_evidence } else { $null }

if ($contactMaskQa -and $contactMaskQa.result -ne "pass_local_contact_mask_qa") {
  $errors += "Contact mask QA result is not pass_local_contact_mask_qa: $($contactMaskQa.result)"
}
if ($robustnessQa -and $robustnessQa.whole_image_visual_qa.result -notmatch "^pass_with_notes") {
  $errors += "Robustness visual QA did not pass with notes: $($robustnessQa.whole_image_visual_qa.result)"
}

$review = $request.visual_review
$localPassChecks = [ordered]@{
  participants_distinct = Test-Truth -Object $review -Name "participants_distinct"
  source_target_ownership_correct = Test-Truth -Object $review -Name "source_target_ownership_correct"
  open_hand_contact_visible = Test-Truth -Object $review -Name "open_hand_contact_visible"
  hand_anatomy_acceptable = Test-Truth -Object $review -Name "hand_anatomy_acceptable"
  no_body_merge = Test-Truth -Object $review -Name "no_body_merge"
  no_duplicate_or_missing_hand = Test-Truth -Object $review -Name "no_duplicate_or_missing_hand"
  no_visible_mask_edge = Test-Truth -Object $review -Name "no_visible_mask_edge"
  robustness_pair_stable = Test-Truth -Object $review -Name "robustness_pair_stable"
  contact_mask_qa_passed = ($contactMaskQa -and $contactMaskQa.result -eq "pass_local_contact_mask_qa")
}

foreach ($check in $localPassChecks.GetEnumerator()) {
  if ($check.Value -ne $true) { $errors += "Local pass check failed: $($check.Key)" }
}

$finalBlockers = @()
if ($review.contact_shadow_strength -ne "clear") {
  $finalBlockers += "contact_shadow_not_clear:$($review.contact_shadow_strength)"
}
if ($review.contact_placement_precision -ne "target_upper_arm") {
  $finalBlockers += "contact_placement_not_exact_target:$($review.contact_placement_precision)"
}
if ($request.target_runtime_proof_available -ne $true) {
  $finalBlockers += "target_runtime_proof_missing"
}
if ($request.multi_seed_final_certification_available -ne $true) {
  $finalBlockers += "final_certification_review_missing"
}

$localSupport = ($errors.Count -eq 0)
$finalAllowed = ($localSupport -and $finalBlockers.Count -eq 0)
$result = if ($finalAllowed) {
  "pass_final_hand_contact_visual_certification"
} elseif ($localSupport) {
  "pass_local_support_block_final_hand_contact_certification"
} else {
  "fail_hand_contact_visual_certification"
}

$evidence = [ordered]@{
  schema_version = "1.0"
  evidence_id = $request.evidence_id
  timestamp = $request.timestamp
  project_root = $ProjectRoot
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  generation_executed = $false
  certification_subject = $request.certification_subject
  source_requirements = @($request.source_requirements)
  checked_evidence_paths = $checkedEvidence
  visual_review = $review
  local_pass_checks = $localPassChecks
  final_certification_blockers = $finalBlockers
  warnings = $warnings
  errors = $errors
  local_support_passed = $localSupport
  final_certification_allowed = $finalAllowed
  result = $result
  certification_boundary = "This is a local visual certification gate. Final project certification still requires target-runtime proof and all broader done gates."
}

Write-JsonNoBom -Value $evidence -Path $outResolved
$evidence | ConvertTo-Json -Depth 60
