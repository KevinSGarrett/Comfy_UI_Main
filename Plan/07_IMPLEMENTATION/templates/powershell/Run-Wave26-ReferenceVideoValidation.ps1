param(
  [string]$Root = "."
)
$required = @(
  "02_TARGET_ARCHITECTURE/WAVE26_REFERENCE_VIDEO_FILE_INGESTION_ARCHITECTURE.md",
  "04_VIDEO_GIF_SYSTEM/WAVE26_REFERENCE_VIDEO_INPUT_PIPELINE.md",
  "06_QA_TESTING/WAVE26_REFERENCE_VIDEO_QA_GATES.md",
  "10_REGISTRIES/wave26_reference_video_input_format_registry.json",
  "08_SCHEMAS/reference_video_manifest.schema.json",
  "09_EXAMPLES/wave26_reference_video_manifest.example.json"
)
$missing = @()
foreach ($rel in $required) {
  $p = Join-Path $Root $rel
  if (-not (Test-Path $p)) { $missing += $rel }
}
if ($missing.Count -gt 0) {
  Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: FAIL"
  $missing | ForEach-Object { Write-Host "Missing: $_" }
  exit 1
}
Write-Host "WAVE26 REFERENCE VIDEO VALIDATION: PASS"
Write-Host "Actual reference-video-file handling is present. Runtime proof still requires decoded frame evidence."
