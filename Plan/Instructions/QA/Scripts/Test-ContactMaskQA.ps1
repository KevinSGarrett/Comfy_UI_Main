<#
.SYNOPSIS
Creates local QA evidence for a contact mask against named participant masks.

.DESCRIPTION
Validates the Wave 13 contact-mask requirements locally: named participants,
non-empty contact edge, participant overlap, bounded unrelated-region bleed, and
actual source/output/mask artifact evidence. This helper does not run ComfyUI or
perform segmentation; it audits already-prepared mask files.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$ContactMaskPath,
  [Parameter(Mandatory=$true)][string]$ParticipantAMaskPath,
  [Parameter(Mandatory=$true)][string]$ParticipantBMaskPath,
  [Parameter(Mandatory=$true)][string]$ParticipantAId,
  [Parameter(Mandatory=$true)][string]$ParticipantBId,
  [Parameter(Mandatory=$true)][string]$SourceImagePath,
  [Parameter(Mandatory=$true)][string]$OutputImagePath,
  [Parameter(Mandatory=$true)][string]$OutJson,
  [Parameter(Mandatory=$true)][string]$OutOverlayPng,
  [string]$EvidenceId = "W69-LOCAL-CONTACT-MASK-QA",
  [string]$Timestamp = "2026-07-07T12:25:00-05:00",
  [double]$MaxCoveragePercent = 8.0,
  [double]$MaxOutsideParticipantPercent = 20.0
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
  param([object]$Value, [string]$Path, [int]$Depth = 40)
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Get-FileSha256Lower {
  param([string]$Path)
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-MaskPixel {
  param([System.Drawing.Bitmap]$Bitmap, [int]$X, [int]$Y)
  if ($X -lt 0 -or $Y -lt 0 -or $X -ge $Bitmap.Width -or $Y -ge $Bitmap.Height) { return $false }
  $pixel = $Bitmap.GetPixel($X, $Y)
  return (($pixel.R + $pixel.G + $pixel.B) -gt 0)
}

function Test-ScaledMaskPixel {
  param([System.Drawing.Bitmap]$Bitmap, [int]$TargetX, [int]$TargetY, [int]$TargetWidth, [int]$TargetHeight)
  $x = [math]::Min($Bitmap.Width - 1, [math]::Floor(($TargetX / [double]$TargetWidth) * $Bitmap.Width))
  $y = [math]::Min($Bitmap.Height - 1, [math]::Floor(($TargetY / [double]$TargetHeight) * $Bitmap.Height))
  return (Test-MaskPixel -Bitmap $Bitmap -X $x -Y $y)
}

foreach ($path in @($ContactMaskPath, $ParticipantAMaskPath, $ParticipantBMaskPath, $SourceImagePath, $OutputImagePath)) {
  $resolved = Resolve-ProjectPath -Path $path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Missing required file: $resolved" }
}

Add-Type -AssemblyName System.Drawing

$contactResolved = Resolve-ProjectPath -Path $ContactMaskPath
$maskAResolved = Resolve-ProjectPath -Path $ParticipantAMaskPath
$maskBResolved = Resolve-ProjectPath -Path $ParticipantBMaskPath
$sourceResolved = Resolve-ProjectPath -Path $SourceImagePath
$outputResolved = Resolve-ProjectPath -Path $OutputImagePath
$overlayResolved = Resolve-ProjectPath -Path $OutOverlayPng
$outJsonResolved = Resolve-ProjectPath -Path $OutJson

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $overlayResolved) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outJsonResolved) | Out-Null

$contact = [System.Drawing.Bitmap]::new($contactResolved)
$maskA = [System.Drawing.Bitmap]::new($maskAResolved)
$maskB = [System.Drawing.Bitmap]::new($maskBResolved)

$contactPixels = 0
$edgePixels = 0
$overlapA = 0
$overlapB = 0
$overlapBoth = 0
$outsideParticipants = 0
$minX = $contact.Width
$minY = $contact.Height
$maxX = -1
$maxY = -1

for ($y = 0; $y -lt $contact.Height; $y++) {
  for ($x = 0; $x -lt $contact.Width; $x++) {
    if (!(Test-MaskPixel -Bitmap $contact -X $x -Y $y)) { continue }
    $contactPixels++
    if ($x -lt $minX) { $minX = $x }
    if ($y -lt $minY) { $minY = $y }
    if ($x -gt $maxX) { $maxX = $x }
    if ($y -gt $maxY) { $maxY = $y }
    $inA = Test-ScaledMaskPixel -Bitmap $maskA -TargetX $x -TargetY $y -TargetWidth $contact.Width -TargetHeight $contact.Height
    $inB = Test-ScaledMaskPixel -Bitmap $maskB -TargetX $x -TargetY $y -TargetWidth $contact.Width -TargetHeight $contact.Height
    if ($inA) { $overlapA++ }
    if ($inB) { $overlapB++ }
    if ($inA -and $inB) { $overlapBoth++ }
    if (!$inA -and !$inB) { $outsideParticipants++ }
    $isEdge = $false
    foreach ($offset in @(@(-1,0), @(1,0), @(0,-1), @(0,1))) {
      if (!(Test-MaskPixel -Bitmap $contact -X ($x + $offset[0]) -Y ($y + $offset[1]))) {
        $isEdge = $true
        break
      }
    }
    if ($isEdge) { $edgePixels++ }
  }
}

$totalPixels = $contact.Width * $contact.Height
$coveragePercent = if ($totalPixels -gt 0) { [math]::Round(($contactPixels / [double]$totalPixels) * 100, 4) } else { 0 }
$outsidePercent = if ($contactPixels -gt 0) { [math]::Round(($outsideParticipants / [double]$contactPixels) * 100, 4) } else { 100 }
$overlapAPercent = if ($contactPixels -gt 0) { [math]::Round(($overlapA / [double]$contactPixels) * 100, 4) } else { 0 }
$overlapBPercent = if ($contactPixels -gt 0) { [math]::Round(($overlapB / [double]$contactPixels) * 100, 4) } else { 0 }
$overlapBothPercent = if ($contactPixels -gt 0) { [math]::Round(($overlapBoth / [double]$contactPixels) * 100, 4) } else { 0 }
$edgePercent = if ($contactPixels -gt 0) { [math]::Round(($edgePixels / [double]$contactPixels) * 100, 4) } else { 0 }

$participantsNamed = ![string]::IsNullOrWhiteSpace($ParticipantAId) -and ![string]::IsNullOrWhiteSpace($ParticipantBId)
$contactExists = $contactPixels -gt 0
$edgeExists = $edgePixels -gt 0
$bothParticipantsTouched = $overlapA -gt 0 -and $overlapB -gt 0
$coveragePlausible = $coveragePercent -gt 0 -and $coveragePercent -le $MaxCoveragePercent
$outsideBleedOk = $outsidePercent -le $MaxOutsideParticipantPercent

$checks = [ordered]@{
  participants_named = $participantsNamed
  contact_mask_nonempty = $contactExists
  contact_edge_exists = $edgeExists
  contact_overlaps_participant_a = ($overlapA -gt 0)
  contact_overlaps_participant_b = ($overlapB -gt 0)
  contact_overlaps_both_participants = $bothParticipantsTouched
  coverage_within_configured_bounds = $coveragePlausible
  outside_participant_bleed_within_bounds = $outsideBleedOk
  explicitly_labeled_as_contact_mask = $true
}

$failures = @()
foreach ($property in $checks.GetEnumerator()) {
  if ($property.Value -ne $true) { $failures += $property.Key }
}

$result = if ($failures.Count -eq 0) { "pass_local_contact_mask_qa" } else { "fail_local_contact_mask_qa" }

$base = [System.Drawing.Bitmap]::new($outputResolved)
$overlay = [System.Drawing.Bitmap]::new($base.Width, $base.Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$graphics = [System.Drawing.Graphics]::FromImage($overlay)
$graphics.DrawImage($base, 0, 0, $overlay.Width, $overlay.Height)
for ($y = 0; $y -lt $overlay.Height; $y++) {
  for ($x = 0; $x -lt $overlay.Width; $x++) {
    $inContact = Test-ScaledMaskPixel -Bitmap $contact -TargetX $x -TargetY $y -TargetWidth $overlay.Width -TargetHeight $overlay.Height
    if (!$inContact) { continue }
    $pixel = $overlay.GetPixel($x, $y)
    $red = [math]::Min(255, [int]($pixel.R * 0.55 + 255 * 0.45))
    $green = [int]($pixel.G * 0.55)
    $blue = [int]($pixel.B * 0.55)
    $overlay.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($red, $green, $blue))
  }
}
$pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::Yellow), 3
if ($maxX -ge $minX -and $maxY -ge $minY) {
  $scaleX = $overlay.Width / [double]$contact.Width
  $scaleY = $overlay.Height / [double]$contact.Height
  $rect = New-Object System.Drawing.Rectangle ([int]($minX * $scaleX)), ([int]($minY * $scaleY)), ([int](($maxX - $minX + 1) * $scaleX)), ([int](($maxY - $minY + 1) * $scaleY))
  $graphics.DrawRectangle($pen, $rect)
}
$font = New-Object System.Drawing.Font "Arial", 16
$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::Yellow)
$graphics.DrawString("contact mask overlay", $font, $brush, 12, 12)
$overlay.Save($overlayResolved, [System.Drawing.Imaging.ImageFormat]::Png)
$font.Dispose()
$brush.Dispose()
$pen.Dispose()
$graphics.Dispose()
$base.Dispose()
$overlay.Dispose()

$overlayHash = Get-FileSha256Lower -Path $overlayResolved

$evidence = [ordered]@{
  schema_version = "1.0"
  evidence_id = $EvidenceId
  timestamp = $Timestamp
  project_root = $ProjectRoot
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  generation_executed = $false
  source_requirements = @(
    "Plan/06_QA_TESTING/WAVE13_CONTACT_MASK_TESTS.md",
    "Plan/06_QA_TESTING/WAVE13_MASK_BLEED_AND_OVERLAP_QA.md",
    "Plan/06_QA_TESTING/WAVE13_MASK_FACTORY_QA_GATES.md"
  )
  contact_mask = [ordered]@{
    path = Convert-ToProjectPath -Path $ContactMaskPath
    sha256 = Get-FileSha256Lower -Path $contactResolved
    width = $contact.Width
    height = $contact.Height
    contact_pixel_count = $contactPixels
    coverage_percent = $coveragePercent
    edge_pixel_count = $edgePixels
    edge_percent_of_contact = $edgePercent
    bbox = [ordered]@{
      x_min = if ($contactPixels -gt 0) { $minX } else { $null }
      y_min = if ($contactPixels -gt 0) { $minY } else { $null }
      x_max = if ($contactPixels -gt 0) { $maxX } else { $null }
      y_max = if ($contactPixels -gt 0) { $maxY } else { $null }
    }
  }
  participants = @(
    [ordered]@{
      participant_id = $ParticipantAId
      mask_path = Convert-ToProjectPath -Path $ParticipantAMaskPath
      mask_sha256 = Get-FileSha256Lower -Path $maskAResolved
      contact_overlap_pixels = $overlapA
      contact_overlap_percent = $overlapAPercent
    },
    [ordered]@{
      participant_id = $ParticipantBId
      mask_path = Convert-ToProjectPath -Path $ParticipantBMaskPath
      mask_sha256 = Get-FileSha256Lower -Path $maskBResolved
      contact_overlap_pixels = $overlapB
      contact_overlap_percent = $overlapBPercent
    }
  )
  overlap = [ordered]@{
    both_participants_overlap_pixels = $overlapBoth
    both_participants_overlap_percent = $overlapBothPercent
    outside_participant_pixels = $outsideParticipants
    outside_participant_percent = $outsidePercent
    max_outside_participant_percent = $MaxOutsideParticipantPercent
  }
  source_image = [ordered]@{
    path = Convert-ToProjectPath -Path $SourceImagePath
    sha256 = Get-FileSha256Lower -Path $sourceResolved
  }
  output_image = [ordered]@{
    path = Convert-ToProjectPath -Path $OutputImagePath
    sha256 = Get-FileSha256Lower -Path $outputResolved
  }
  overlay = [ordered]@{
    path = Convert-ToProjectPath -Path $OutOverlayPng
    sha256 = $overlayHash
  }
  checks = $checks
  failures = $failures
  result = $result
  certification_boundary = "Local mask QA only; does not replace strict whole-image visual QA or target-runtime proof."
}

Write-JsonNoBom -Value $evidence -Path $outJsonResolved

$contact.Dispose()
$maskA.Dispose()
$maskB.Dispose()

$evidence | ConvertTo-Json -Depth 40
