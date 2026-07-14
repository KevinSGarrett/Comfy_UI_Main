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

function Test-ExcludedMediaPath([string]$path) {
  $lower = $path.ToLowerInvariant()
  return $lower -match 'agent_handoffs|synthetic|fixture|ref_image|reference_images|candidate_mask|mask_preview|diagnostic|\\masks\\|\\temp\\|\\tmp\\'
}

function Test-CandidateMedia([IO.FileInfo]$file) {
  $lower = $file.FullName.ToLowerInvariant()
  if ($file.LastWriteTime -lt $cutoff) { return $false }
  if (Test-ExcludedMediaPath $lower) { return $false }
  return [bool](Get-Modality $file.FullName)
}

function Get-EvidenceTimestamp($record) {
  foreach ($name in @("execution_timestamp", "executed_at", "completed_at", "generated_at", "created_iso", "timestamp")) {
    $property = $record.psobject.Properties[$name]
    if (!$property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) { continue }
    $parsed = [datetimeoffset]::MinValue
    if ([datetimeoffset]::TryParse([string]$property.Value, [ref]$parsed)) { return $parsed }
  }
  return $null
}

function Get-PassBasis($record) {
  $state = ""
  foreach ($name in @("result", "status", "execution_status", "qa_status", "direct_qa_state")) {
    $property = $record.psobject.Properties[$name]
    if ($property) { $state += " " + [string]$property.Value }
  }
  $state = $state.Trim().ToLowerInvariant()
  if ($state -match '(^|[ _-])(not|non|never|fail|failed|blocked|incomplete|unsuccessful|un)([ _-]|$)' -or $state -match 'dry[ _-]?run|preflight|readiness') {
    return $null
  }
  $passingState = $state -match '(^|[ _-])(pass|passed|complete|completed|success|succeeded)([ _-]|$)'
  $executionPass = $record.generation_executed -eq $true -or $record.runtime_validation_passed -eq $true -or $record.execution_passed -eq $true
  $directQaPass = $record.direct_qa_passed -eq $true -or $record.direct_review_passed -eq $true -or $record.visual_review_passed -eq $true
  if ($passingState -and $executionPass) { return "passing_execution" }
  if ($passingState -and $directQaPass) { return "passing_direct_qa" }
  return $null
}

function Get-MediaBindings($value) {
  $bindings = [Collections.Generic.List[object]]::new()
  function Visit-MediaBinding($item) {
    if ($null -eq $item) { return }
    if ($item -is [System.Collections.IEnumerable] -and !($item -is [string]) -and !($item -is [pscustomobject])) {
      foreach ($child in $item) { Visit-MediaBinding $child }
      return
    }
    if (!($item -is [pscustomobject])) { return }

    $pathValue = $null
    $pathField = $null
    foreach ($name in @("media_path", "output_path", "local_path", "display_path", "path")) {
      $property = $item.psobject.Properties[$name]
      if ($property -and $property.Value -is [string]) { $pathValue = [string]$property.Value; $pathField = $name; break }
    }
    $hashValue = if ($item.psobject.Properties["sha256"]) { [string]$item.sha256 } else { $null }
    $role = "$($item.type) $($item.role) $($item.artifact_role)".Trim().ToLowerInvariant()
    $explicitOutput = $pathField -in @("media_path", "output_path") -or $role -match '(^|[ _-])(output|generated|candidate|final)([ _-]|$)'
    if (!$pathValue -and $item.psobject.Properties["generated_image"] -and $item.generated_image -is [string]) {
      $pathValue = [string]$item.generated_image
      if ($item.psobject.Properties["generated_sha256"]) { $hashValue = [string]$item.generated_sha256 }
      $explicitOutput = $true
    }
    if ($explicitOutput -and $pathValue -and $hashValue -match '^[0-9a-fA-F]{64}$' -and (Get-Modality $pathValue)) {
      $bindings.Add([pscustomobject]@{ path = $pathValue; sha256 = $hashValue.ToLowerInvariant() })
    }
    foreach ($property in $item.psobject.Properties) { Visit-MediaBinding $property.Value }
  }
  Visit-MediaBinding $value
  return @($bindings)
}

function Resolve-ProjectMediaPath([string]$path) {
  try {
    $candidate = if ([IO.Path]::IsPathRooted($path)) { [IO.Path]::GetFullPath($path) } else { [IO.Path]::GetFullPath((Join-Path $ProjectRoot $path)) }
    $rootPrefix = $ProjectRoot.TrimEnd("\") + "\"
    if (!$candidate.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) { return $null }
    if (!(Test-Path -LiteralPath $candidate -PathType Leaf)) { return $null }
    if (Test-ExcludedMediaPath $candidate) { return $null }
    return $candidate
  } catch {
    return $null
  }
}

function Test-RecoveryOnlyEvidence([IO.FileInfo]$file, $record) {
  $identity = "$($file.Name) $($record.artifact_type) $($record.classification) $($record.evidence_id)".ToLowerInvariant()
  return $identity -match 'recover(?:y|ed)|checkout|restor(?:e|ed|ation)|rollback|reconstruct|backfill|replay|runtime_input_inventory|readiness'
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
    candidate_media_latest_write_at = if ($items.Count) { $items[0].LastWriteTime.ToString("o") } else { $null }
    candidate_media_latest_write_path = if ($items.Count) { $items[0].FullName.Substring($ProjectRoot.Length).TrimStart("\").Replace("\", "/") } else { $null }
    verified_delivery_count = 0
    verified_delivery_latest_execution_at = $null
    verified_delivery_latest_path = $null
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

$verifiedByHash = @{}
foreach ($file in $recentEvidence) {
  try { $record = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop | ConvertFrom-Json } catch { continue }
  if (Test-RecoveryOnlyEvidence $file $record) { continue }
  $executionAt = Get-EvidenceTimestamp $record
  if (!$executionAt -or $executionAt.LocalDateTime -lt $cutoff) { continue }
  $passBasis = Get-PassBasis $record
  if (!$passBasis) { continue }
  foreach ($binding in @(Get-MediaBindings $record)) {
    $resolved = Resolve-ProjectMediaPath $binding.path
    if (!$resolved) { continue }
    $actualHash = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $binding.sha256) { continue }
    if ($verifiedByHash.ContainsKey($actualHash)) { continue }
    $relativePath = $resolved.Substring($ProjectRoot.Length).TrimStart("\").Replace("\", "/")
    $verifiedByHash[$actualHash] = [ordered]@{
      media_path = $relativePath
      media_sha256 = $actualHash
      modality = Get-Modality $resolved
      execution_at = $executionAt.ToString("o")
      pass_basis = $passBasis
      evidence_path = $file.FullName.Substring($ProjectRoot.Length).TrimStart("\").Replace("\", "/")
      evidence_sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
  }
}
$verifiedDelivery = @($verifiedByHash.Values | Sort-Object { [datetimeoffset]$_.execution_at } -Descending)
foreach ($modality in @("image", "video", "audio")) {
  $verifiedForModality = @($verifiedDelivery | Where-Object { $_.modality -eq $modality })
  $mediaByModality[$modality].verified_delivery_count = $verifiedForModality.Count
  if ($verifiedForModality.Count) {
    $mediaByModality[$modality].verified_delivery_latest_execution_at = $verifiedForModality[0].execution_at
    $mediaByModality[$modality].verified_delivery_latest_path = $verifiedForModality[0].media_path
  }
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
$candidateMediaLatestWriteAt = if ($latestCandidate.Count) { $latestCandidate[0].LastWriteTime.ToString("o") } else { $null }
$verifiedDeliveryLatestAt = if ($verifiedDelivery.Count) { $verifiedDelivery[0].execution_at } else { $null }
$activeModalities = @($registry.lanes | Where-Object { $_.classification -in @("required_production", "required_fallback", "required_support") } | Select-Object -ExpandProperty modality -Unique)
$starved = @()
foreach ($modality in $activeModalities) {
  $latest = $mediaByModality[$modality].verified_delivery_latest_execution_at
  if (!$latest -or ([datetime]$latest) -lt (Get-Date).AddHours(-[int]$registry.portfolio_starvation_hours)) {
    $starved += $modality
  }
}

$hasDelivery = $verifiedDelivery.Count -gt 0
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
  schema_version = "1.1"
  generated_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot.Replace("\", "/")
  window_hours = $WindowHours
  delivery_classification = $classification
  observational_warning = "Candidate media write times are observational only. DELIVERY_ADVANCING requires an exact path/SHA-256 binding to recent passing execution or direct-QA evidence."
  candidate_media_latest_write_at = $candidateMediaLatestWriteAt
  candidate_media_artifact_count = $media.Count
  verified_new_delivery_latest_execution_at = $verifiedDeliveryLatestAt
  verified_new_delivery_count = $verifiedDelivery.Count
  verified_new_delivery = $verifiedDelivery
  new_executable_capability_count = $newCapabilityCount
  runtime_claim_evidence_count = $runtimeEvidenceCount
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
