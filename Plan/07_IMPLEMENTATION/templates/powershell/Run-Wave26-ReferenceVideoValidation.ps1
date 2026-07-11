param(
  [string]$Root = ".",
  [ValidateSet("structural", "source_video")]
  [string]$Mode = "structural",
  [string]$SourceVideo = "",
  [string]$OutputDir = "",
  [string]$ExtractionProfileId = "all_frames_short_clip",
  [string]$SourceVideoId = "",
  [string]$AudioPresent = "",
  [int]$SampleStride = 0,
  [switch]$StrictShortClipGate,
  [string]$PythonExe = "python"
)

function Resolve-PlanRoot([string]$InputRoot) {
  $direct = Join-Path $InputRoot "02_TARGET_ARCHITECTURE"
  if (Test-Path $direct) {
    return (Resolve-Path $InputRoot).Path
  }

  $nested = Join-Path $InputRoot "Plan/02_TARGET_ARCHITECTURE"
  if (Test-Path $nested) {
    return (Resolve-Path (Join-Path $InputRoot "Plan")).Path
  }

  return $null
}

$planRoot = Resolve-PlanRoot $Root
if (-not $planRoot) {
  Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: FAIL"
  Write-Host "Unable to resolve Plan root from Root=$Root"
  exit 1
}

$required = @(
  "02_TARGET_ARCHITECTURE/WAVE26_REFERENCE_VIDEO_FILE_INGESTION_ARCHITECTURE.md",
  "04_VIDEO_GIF_SYSTEM/WAVE26_REFERENCE_VIDEO_INPUT_PIPELINE.md",
  "10_REGISTRIES/wave26_reference_video_input_format_registry.json",
  "10_REGISTRIES/wave26_reference_video_extraction_profiles.json",
  "08_SCHEMAS/reference_video_manifest.schema.json",
  "08_SCHEMAS/reference_video_frame_manifest.schema.json",
  "08_SCHEMAS/wave26_reference_video_ingest_evidence.schema.json",
  "09_EXAMPLES/wave26_reference_video_manifest.example.json",
  "07_IMPLEMENTATION/scripts/ingest_wave26_reference_video.py"
)

$missing = @()
foreach ($rel in $required) {
  $p = Join-Path $planRoot $rel
  if (-not (Test-Path $p)) { $missing += $rel }
}
if ($missing.Count -gt 0) {
  Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: FAIL"
  $missing | ForEach-Object { Write-Host "Missing: $_" }
  exit 1
}

if ($Mode -eq "structural") {
  Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: PASS"
  Write-Host "Structural assets are present only; this mode does not claim decoded source-video handling."
  exit 0
}

if (-not $SourceVideo) {
  Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: FAIL"
  Write-Host "Mode=source_video requires -SourceVideo"
  exit 1
}
if (-not $OutputDir) {
  Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: FAIL"
  Write-Host "Mode=source_video requires -OutputDir"
  exit 1
}
if ($AudioPresent -notin @("true", "false")) {
  Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: FAIL"
  Write-Host "Mode=source_video requires -AudioPresent true|false"
  exit 1
}

$projectRoot = (Resolve-Path (Join-Path $planRoot "..")).Path
$scriptPath = Join-Path $projectRoot "Plan/07_IMPLEMENTATION/scripts/ingest_wave26_reference_video.py"
$args = @(
  $scriptPath,
  "--source-video", $SourceVideo,
  "--output-dir", $OutputDir,
  "--extraction-profile-id", $ExtractionProfileId,
  "--audio-present", $AudioPresent
)
if ($SourceVideoId) {
  $args += @("--source-video-id", $SourceVideoId)
}
if ($SampleStride -gt 0) {
  $args += @("--sample-stride", "$SampleStride")
}
if ($StrictShortClipGate.IsPresent) {
  $args += "--strict-short-clip-gate"
}

& $PythonExe @args
exit $LASTEXITCODE
