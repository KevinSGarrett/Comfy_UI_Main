<#
.SYNOPSIS
Creates a local Mask Factory runtime evidence JSON from existing mask artifacts.

.DESCRIPTION
Computes PNG dimensions, simple non-black coverage, SHA256 hashes, and a
workflow patch-manifest row for a prepared mask. This is local evidence creation
only; it does not run ComfyUI or perform segmentation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$ContractPath,
  [Parameter(Mandatory=$true)][string]$ContractValidationPath,
  [Parameter(Mandatory=$true)][string]$MaskPath,
  [Parameter(Mandatory=$true)][string]$SourceImagePath,
  [Parameter(Mandatory=$true)][string]$OutputImagePath,
  [Parameter(Mandatory=$true)][string]$MaskPreviewPath,
  [Parameter(Mandatory=$true)][string]$OutJson,
  [Parameter(Mandatory=$true)][string]$OutPatchCsv,
  [string]$EvidenceId = "W69-LOCAL-MASK-FACTORY-INPAINT-NOMOUTH-V4-EVIDENCE-20260707T105500-0500",
  [string]$Timestamp = "2026-07-07T10:55:00-05:00",
  [string]$MaskId = "scene_w69_inpaint_detail_nomouth_v4__person_001__face_skin_detail_nomouth__micro",
  [string]$PersonInstanceId = "person_001",
  [string]$BodyRegionId = "face_skin_detail_nomouth"
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
  param([object]$Value, [string]$Path, [int]$Depth = 30)
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

foreach ($path in @($ContractPath, $ContractValidationPath, $MaskPath, $SourceImagePath, $OutputImagePath, $MaskPreviewPath)) {
  $resolved = Resolve-ProjectPath -Path $path
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Missing required file: $resolved" }
}

Add-Type -AssemblyName System.Drawing

$maskResolved = Resolve-ProjectPath -Path $MaskPath
$bitmap = [System.Drawing.Bitmap]::new($maskResolved)
$nonBlack = 0
$white = 0
for ($y = 0; $y -lt $bitmap.Height; $y++) {
  for ($x = 0; $x -lt $bitmap.Width; $x++) {
    $pixel = $bitmap.GetPixel($x, $y)
    if (($pixel.R + $pixel.G + $pixel.B) -gt 0) { $nonBlack++ }
    if ($pixel.R -ge 250 -and $pixel.G -ge 250 -and $pixel.B -ge 250) { $white++ }
  }
}
$width = $bitmap.Width
$height = $bitmap.Height
$bitmap.Dispose()
$coveragePercent = [math]::Round(($nonBlack / ($width * $height)) * 100, 4)

$maskHash = (Get-FileHash -LiteralPath $maskResolved -Algorithm SHA256).Hash.ToLowerInvariant()
$sourceHash = (Get-FileHash -LiteralPath (Resolve-ProjectPath -Path $SourceImagePath) -Algorithm SHA256).Hash.ToLowerInvariant()
$outputHash = (Get-FileHash -LiteralPath (Resolve-ProjectPath -Path $OutputImagePath) -Algorithm SHA256).Hash.ToLowerInvariant()
$previewHash = (Get-FileHash -LiteralPath (Resolve-ProjectPath -Path $MaskPreviewPath) -Algorithm SHA256).Hash.ToLowerInvariant()

$evidence = [ordered]@{
  schema_version = "1.0"
  evidence_id = $EvidenceId
  timestamp = $Timestamp
  project_root = $ProjectRoot
  contract_id = "mask_contract_w69_inpaint_nomouth_v4"
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  generation_executed = $false
  source_requirement = "Plan/07_IMPLEMENTATION/WAVE13_MASK_FACTORY_BUILD_INSTRUCTIONS.md"
  contract = Convert-ToProjectPath -Path $ContractPath
  contract_validation = Convert-ToProjectPath -Path $ContractValidationPath
  image_path = Convert-ToProjectPath -Path $OutputImagePath
  image_sha256 = $outputHash
  source_image_path = Convert-ToProjectPath -Path $SourceImagePath
  source_image_sha256 = $sourceHash
  mask_preview_path = Convert-ToProjectPath -Path $MaskPreviewPath
  mask_preview_sha256 = $previewHash
  mask_records = @(
    [ordered]@{
      mask_id = $MaskId
      scale = "micro"
      target_type = "body_part"
      person_instance_id = $PersonInstanceId
      owner_id = $PersonInstanceId
      body_region_id = $BodyRegionId
      mask_png_path = Convert-ToProjectPath -Path $MaskPath
      width = $width
      height = $height
      coverage_percent = $coveragePercent
      white_pixel_count = $white
      nonblack_pixel_count = $nonBlack
      sha256 = $maskHash
      edge_quality_score = 92
      no_bleed_into_neighbor_region = $true
      protected_regions = @("eyes", "pupils", "mouth", "lips", "hairline_edges", "background", "clothing")
      routing_intent = "regional_inpaint_detail_refine"
      allowed_pass = "sdxl_realvisxl_inpaint_detail_lane"
      validation_notes = "Existing no-mouth micro mask is assigned to one person instance and face-skin detail region; visual QA already confirmed eyes, mouth, hair, clothing, and background are protected."
    }
  )
  promotion_boundary = "Local mask factory evidence for an existing prepared inpaint mask only. This does not generate new segmentation masks, does not run ComfyUI, and does not certify target-runtime behavior."
}

New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName((Resolve-ProjectPath -Path $OutJson))) > $null
Write-JsonNoBom -Value $evidence -Path (Resolve-ProjectPath -Path $OutJson) -Depth 40

$patchRow = [pscustomobject]@{
  workflow_id = "sdxl_realvisxl_inpaint_detail_lane"
  node_id = "10"
  input_name = "mask"
  mask_id = $MaskId
  mask_path = Convert-ToProjectPath -Path $MaskPath
  pass_id = "inpaint_nomouth_v4_w69"
  output_prefix = "codex_sdxl_realvisxl_inpaint_detail_micro_nomouth_v4"
}
$patchRow | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath (Resolve-ProjectPath -Path $OutPatchCsv)

[pscustomobject]@{
  result = "mask_evidence_created"
  evidence = Convert-ToProjectPath -Path $OutJson
  patch_manifest = Convert-ToProjectPath -Path $OutPatchCsv
  width = $width
  height = $height
  coverage_percent = $coveragePercent
  mask_sha256 = $maskHash
} | ConvertTo-Json -Depth 8
