<#
.SYNOPSIS
Creates a technical image QA record and review checklist for a generated artifact.

.DESCRIPTION
This helper prepares the evidence required by IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md.
It can run in dry-run mode before an image exists, or inspect an existing local image for
file integrity, dimensions, extension, and sha256. It does not replace visual review:
successful technical inspection still returns pending_visual_review until Codex inspects
the actual image.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ImagePath = "",
  [string]$ArtifactId = "",
  [string]$WorkflowReference = "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/sdxl_low_risk_fallback_lane/workflow.api.json",
  [string]$PromptReference = "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/sdxl_low_risk_fallback_lane/smoke_test_request.json",
  [string]$ModelContext = "sdxl_low_risk_fallback_lane / sd_xl_base_1.0.safetensors",
  [string]$TaskId = "ITEM-W61-002",
  [string]$TrackerId = "TRK-W61-002",
  [string]$OutFile = "",
  [string]$ChecklistOutFile = "",
  [int]$MinimumWidth = 512,
  [int]$MinimumHeight = 512,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

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

function Get-DisplayPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  if (Test-Path -LiteralPath $Path) {
    try {
      return (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath (Resolve-Path -LiteralPath $Path).Path).Replace("\", "/")
    } catch {
      return $Path
    }
  }
  if ([System.IO.Path]::IsPathRooted($Path)) {
    try {
      return (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $Path).Replace("\", "/")
    } catch {
      return $Path
    }
  }
  return $Path
}

function New-Checklist {
  param(
    [string]$ArtifactIdValue,
    [string]$OutputPathValue,
    [string]$WorkflowReferenceValue,
    [string]$ModelContextValue,
    [string]$DecisionValue
  )

  if ([string]::IsNullOrWhiteSpace($OutputPathValue)) {
    $OutputPathValue = "(pending)"
  }

  return @"
# Image Review Checklist

- Artifact ID: $ArtifactIdValue
- Output Path: $OutputPathValue
- Workflow / Prompt Reference: $WorkflowReferenceValue; $PromptReference
- Model / LoRA Context: $ModelContextValue

## Scores
- Face realism: pending_visual_review
- Eye quality: pending_visual_review
- Skin texture: pending_visual_review
- Hands/fingers: pending_visual_review
- Feet/toes: pending_visual_review
- Hair realism: pending_visual_review
- Teeth/mouth quality: pending_visual_review
- Body proportions: pending_visual_review
- Pose accuracy: pending_visual_review
- Clothing/fabric: pending_visual_review
- Contact points: pending_visual_review
- Object/body collisions: pending_visual_review
- Deformation realism: pending_visual_review
- Soft-body cues: pending_visual_review
- Anatomy consistency: pending_visual_review
- Lighting: pending_visual_review
- Shadows: pending_visual_review
- Reflections: pending_visual_review
- Background coherence: pending_visual_review
- Camera/lens realism: pending_visual_review
- Texture detail: pending_visual_review
- Artifacting: pending_visual_review
- Prompt compliance: pending_visual_review

## Defects
- pending_visual_review

## Decision
- $DecisionValue
"@
}

$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$evidenceId = "IMAGE-ARTIFACT-QA-" + (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$defects = New-Object System.Collections.ArrayList
$knownIssues = New-Object System.Collections.ArrayList
$scores = [ordered]@{
  technical_integrity = "not_started"
  resolution_check = "not_started"
  visual_review = "pending_artifact"
}
$imageInfo = [ordered]@{
  supplied_path = $ImagePath
  display_path = Get-DisplayPath -Path $ImagePath
  exists = $false
  bytes = $null
  sha256 = $null
  width = $null
  height = $null
  pixel_format = $null
  extension = $null
}

if ([string]::IsNullOrWhiteSpace($ArtifactId)) {
  if (![string]::IsNullOrWhiteSpace($ImagePath)) {
    $ArtifactId = [System.IO.Path]::GetFileNameWithoutExtension($ImagePath)
  } else {
    $ArtifactId = "pending_image_artifact"
  }
}

if ($DryRun) {
  [void]$knownIssues.Add("dry_run_no_image_inspected")
  $qaStatus = "pending_artifact"
  $nextAction = "Run after generated image pullback, then perform visual review with IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md."
} else {
  if ([string]::IsNullOrWhiteSpace($ImagePath)) {
    [void]$defects.Add([ordered]@{ severity = "critical"; code = "image_path_missing"; message = "ImagePath is required unless -DryRun is used." })
  } elseif (!(Test-Path -LiteralPath $ImagePath -PathType Leaf)) {
    [void]$defects.Add([ordered]@{ severity = "critical"; code = "image_missing"; message = "Image file was not found: $ImagePath" })
  } else {
    $file = Get-Item -LiteralPath $ImagePath
    $imageInfo.exists = $true
    $imageInfo.bytes = $file.Length
    $imageInfo.extension = $file.Extension.ToLowerInvariant()
    $imageInfo.sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()

    if (@(".png", ".jpg", ".jpeg", ".webp", ".bmp") -notcontains $imageInfo.extension) {
      [void]$defects.Add([ordered]@{ severity = "major"; code = "unexpected_extension"; message = "Unexpected image extension: $($imageInfo.extension)" })
    }

    try {
      Add-Type -AssemblyName System.Drawing
      $img = [System.Drawing.Image]::FromFile($file.FullName)
      try {
        $imageInfo.width = $img.Width
        $imageInfo.height = $img.Height
        $imageInfo.pixel_format = [string]$img.PixelFormat
      } finally {
        $img.Dispose()
      }
    } catch {
      [void]$defects.Add([ordered]@{ severity = "critical"; code = "image_decode_failed"; message = "Image could not be decoded: $($_.Exception.Message)" })
    }

    if ($null -ne $imageInfo.width -and $null -ne $imageInfo.height) {
      if ($imageInfo.width -lt $MinimumWidth -or $imageInfo.height -lt $MinimumHeight) {
        [void]$defects.Add([ordered]@{ severity = "major"; code = "resolution_below_minimum"; message = "Image resolution $($imageInfo.width)x$($imageInfo.height) is below minimum $MinimumWidth x $MinimumHeight." })
        $scores.resolution_check = "fail"
      } else {
        $scores.resolution_check = "pass"
      }
      $scores.technical_integrity = "pass"
    }
  }

  if ($defects.Count -gt 0) {
    $qaStatus = "blocked"
    $nextAction = "Fix technical artifact defects before visual review."
  } else {
    $qaStatus = "pending_visual_review"
    $scores.visual_review = "pending_visual_review"
    $nextAction = "Inspect the image visually and complete scores/defects/decision per IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md."
  }
}

$evidencePaths = @()
if (![string]::IsNullOrWhiteSpace($ChecklistOutFile)) {
  $evidencePaths += (Get-DisplayPath -Path $ChecklistOutFile)
}

$record = [ordered]@{
  artifact_id = $ArtifactId
  artifact_type = "image"
  task_id = $TaskId
  tracker_id = $TrackerId
  reviewer = "Codex Desktop autonomous QA"
  test_method = $(if ($DryRun) { "dry_run_checklist_generation" } else { "technical_integrity_dimensions_hash_check" })
  qa_status = $qaStatus
  scores = $scores
  defects = @($defects)
  evidence_paths = $evidencePaths
  known_issues = @($knownIssues)
  next_action = $nextAction
  timestamp = $timestamp
  evidence_id = $evidenceId
  workflow_reference = $WorkflowReference
  prompt_reference = $PromptReference
  model_context = $ModelContext
  image = $imageInfo
  visual_runtime_ready = $true
  final_decision_allowed = $false
}

if (![string]::IsNullOrWhiteSpace($ChecklistOutFile)) {
  $checklistDir = Split-Path -Parent $ChecklistOutFile
  if (![string]::IsNullOrWhiteSpace($checklistDir)) {
    $null = New-Item -ItemType Directory -Force -Path $checklistDir
  }
  $decision = $(if ($DryRun) { "Pending artifact" } elseif ($qaStatus -eq "blocked") { "Blocked before visual review" } else { "Pending visual review" })
  New-Checklist -ArtifactIdValue $ArtifactId -OutputPathValue $imageInfo.display_path -WorkflowReferenceValue $WorkflowReference -ModelContextValue $ModelContext -DecisionValue $decision |
    Set-Content -LiteralPath $ChecklistOutFile -Encoding UTF8
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote image artifact QA record: $OutFile"
}

$record | ConvertTo-Json -Depth 20
if (!$DryRun -and $qaStatus -eq "blocked") { exit 2 }
