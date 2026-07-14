[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [ValidateRange(1, 168)][int]$WindowHours = 24,
  [string]$RegistryPath = "",
  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ([string]::IsNullOrWhiteSpace($RegistryPath)) {
  $RegistryPath = Join-Path $ProjectRoot "Plan\10_REGISTRIES\comfyui_delivery_portfolio_registry.json"
}
if (!(Test-Path -LiteralPath $RegistryPath -PathType Leaf)) {
  throw "Delivery portfolio registry missing: $RegistryPath"
}

$registry = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json
$cutoff = (Get-Date).AddHours(-$WindowHours)
$runtimeRoot = Join-Path $ProjectRoot "runtime_artifacts"
$pullbackRoot = Join-Path $ProjectRoot "Plan\Instructions\Operations\Pulled_Back_Artifacts"
$evidenceRoot = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence"

function Get-Modality([string]$path) {
  $lower = $path.ToLowerInvariant()
  $ext = [IO.Path]::GetExtension($lower)
  if ($ext -in @(".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac")) { return "audio" }
  if ($ext -in @(".mp4", ".mov", ".mkv", ".webm", ".avi", ".gif")) { return "video" }
  if ($ext -eq ".webp" -and $lower -match "animatediff|video|animation|frames|loop") { return "video" }
  if ($ext -in @(".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")) { return "image" }
  return $null
}

function Test-CandidateMedia([IO.FileInfo]$file) {
  $lower = $file.FullName.ToLowerInvariant()
  if ($file.LastWriteTime -lt $cutoff) { return $false }
  if ($lower -match "agent_handoffs|synthetic|fixture|ref_image|reference_images|candidate_mask|\\masks\\|\\temp\\|\\tmp\\") { return $false }
  return [bool](Get-Modality $file.FullName)
}

$media = @()
if (Test-Path -LiteralPath $runtimeRoot -PathType Container) {
  $recentRuntimeRoots = @(Get-ChildItem -LiteralPath $runtimeRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge $cutoff -and $_.Name -notin @("agent_handoffs", "_python_deps") })
  $runtimeFiles = @(
    Get-ChildItem -LiteralPath $runtimeRoot -File -ErrorAction SilentlyContinue
    foreach ($directory in $recentRuntimeRoots) {
      Get-ChildItem -LiteralPath $directory.FullName -File -Recurse -ErrorAction SilentlyContinue
    }
  )
  $media = @($runtimeFiles |
    Where-Object { Test-CandidateMedia $_ } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1000)
}
if (Test-Path -LiteralPath $pullbackRoot -PathType Container) {
  $recentPullbacks = @(Get-ChildItem -LiteralPath $pullbackRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge $cutoff })
  $pullbackMedia = @(
    foreach ($directory in $recentPullbacks) {
      Get-ChildItem -LiteralPath $directory.FullName -File -Recurse -ErrorAction SilentlyContinue
    }
  )
  $media = @($media + @($pullbackMedia | Where-Object { Test-CandidateMedia $_ }) |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1000)
}

$mediaByModality = [ordered]@{}
foreach ($modality in @("image", "video", "audio")) {
  $items = @($media | Where-Object { (Get-Modality $_.FullName) -eq $modality })
  $mediaByModality[$modality] = [ordered]@{
    candidate_count = $items.Count
    latest_candidate_at = if ($items.Count) { $items[0].LastWriteTime.ToString("o") } else { $null }
    latest_candidate_path = if ($items.Count) { $items[0].FullName.Substring($ProjectRoot.Length).TrimStart("\").Replace("\", "/") } else { $null }
  }
}

$recentEvidence = @()
if (Test-Path -LiteralPath $evidenceRoot -PathType Container) {
  $recentEvidence = @(Get-ChildItem -LiteralPath $evidenceRoot -Filter "*.json" -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge $cutoff } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 750)
}

$runtimeEvidenceCount = 0
$qualityDeltaCount = 0
$readinessCount = 0
$newCapabilityCount = 0
foreach ($file in $recentEvidence) {
  $name = $file.Name.ToLowerInvariant()
  $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
  if ($text -match '"generation_executed"\s*:\s*true|"runtime_validation_passed"\s*:\s*true|"execution_status"\s*:\s*"(?:pass|completed|success)"') { $runtimeEvidenceCount++ }
  if ($text -match '"quality_metric_delta"\s*:\s*(?!0(?:\.0+)?[,}\s])[-+]?[0-9.]+|"measured_quality_improvement"\s*:\s*true') { $qualityDeltaCount++ }
  if ($text -match '"new_executable_capability"\s*:\s*true') { $newCapabilityCount++ }
  if ($name -match "readiness|dry_run|preflight|gate|route_alignment|dependency_probe") { $readinessCount++ }
}

$changedPaths = @()
try {
  $since = $cutoff.ToString("o")
  $changedPaths = @(git -C $ProjectRoot log --since=$since --name-only --pretty=format: 2>$null |
    Where-Object { $_ -and $_.Trim() } |
    Sort-Object -Unique)
} catch {
  $changedPaths = @()
}

$bookkeepingPattern = '^(Plan/(Instructions/Hydration_Rehydration|Items|Tracker)|Jira/)|manifest|proof.log|audit|index'
$productPattern = '^(Workflows/|PromptProfiles/|config/|Plan/07_IMPLEMENTATION/|Plan/08_SCHEMAS/|Plan/10_REGISTRIES/)'
$bookkeepingChanges = @($changedPaths | Where-Object { $_ -match $bookkeepingPattern }).Count
$productChanges = @($changedPaths | Where-Object { $_ -match $productPattern }).Count
$denominator = $bookkeepingChanges + $productChanges
$bookkeepingRatio = if ($denominator -gt 0) { [Math]::Round($bookkeepingChanges / $denominator, 4) } else { 0.0 }

$latestCandidate = @($media | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
$lastGenerationAt = if ($latestCandidate.Count) { $latestCandidate[0].LastWriteTime.ToString("o") } else { $null }
$activeModalities = @($registry.lanes | Where-Object { $_.classification -in @("required_production", "required_fallback", "required_support") } | Select-Object -ExpandProperty modality -Unique)
$starved = @()
foreach ($modality in $activeModalities) {
  $latest = $mediaByModality[$modality].latest_candidate_at
  if (!$latest -or ([datetime]$latest) -lt (Get-Date).AddHours(-[int]$registry.portfolio_starvation_hours)) {
    $starved += $modality
  }
}

$hasDelivery = ($runtimeEvidenceCount -gt 0 -and $media.Count -gt 0) -or $qualityDeltaCount -gt 0 -or $newCapabilityCount -gt 0
$classification = if ($starved.Count -gt 0) {
  "PORTFOLIO_STARVATION"
} elseif ($hasDelivery) {
  "DELIVERY_ADVANCING"
} elseif ($readinessCount -gt 0 -or $bookkeepingRatio -ge 0.6) {
  "DELIVERY_STAGNATION"
} else {
  "BLOCKED_PRODUCTIVELY_REVIEW_REQUIRED"
}

$nextLane = @($registry.lanes |
  Where-Object { $_.classification -in @("required_production", "required_support") -and !$_.production_lane_certified } |
  Sort-Object recovery_priority |
  Select-Object -First 1)

$snapshot = [ordered]@{
  schema_version = "1.0"
  generated_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot.Replace("\", "/")
  window_hours = $WindowHours
  delivery_classification = $classification
  observational_warning = "Candidate media counts are not final delivery authority; direct QA and source evidence remain required."
  last_real_generation_at = $lastGenerationAt
  new_media_artifact_count = $media.Count
  new_executable_capability_count = $newCapabilityCount
  validated_runtime_evidence_count = $runtimeEvidenceCount
  quality_metric_delta = [ordered]@{ evidence_count = $qualityDeltaCount; measured_value = $null }
  repeated_readiness_or_gate_count = $readinessCount
  bookkeeping_effort_ratio = $bookkeepingRatio
  product_changed_path_count = $productChanges
  bookkeeping_changed_path_count = $bookkeepingChanges
  modalities = $mediaByModality
  starved_modalities = $starved
  next_concrete_lane = if ($nextLane.Count) { $nextLane[0].lane_id } else { $null }
  next_concrete_outcome = if ($nextLane.Count) { $nextLane[0].next_concrete_outcome } else { $null }
}

$json = $snapshot | ConvertTo-Json -Depth 8
if ($OutputPath) {
  $parent = Split-Path -Parent $OutputPath
  if ($parent -and !(Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
  [IO.File]::WriteAllText($OutputPath, $json, (New-Object Text.UTF8Encoding($false)))
}
$json
