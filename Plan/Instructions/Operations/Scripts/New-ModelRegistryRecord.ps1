<#
.SYNOPSIS
Creates a starter model registry JSON record from provided values.
#>
param(
  [string]$ModelName,
  [string]$ModelType,
  [string]$BaseModel,
  [string]$LocalPath,
  [string]$Source = "civitai",
  [string]$SourceModelId = "",
  [string]$SourceModelVersionId = "",
  [string]$WorkflowLane = "candidate_unverified"
)

if (-not $ModelName) { throw "ModelName is required." }
if (-not $ModelType) { throw "ModelType is required." }
if (-not $BaseModel) { throw "BaseModel is required." }

$record = [ordered]@{
  registry_schema_version = "1.0"
  record_id = [guid]::NewGuid().ToString()
  created_at = (Get-Date).ToString("o")
  updated_at = (Get-Date).ToString("o")
  source = $Source
  source_url = ""
  source_model_id = $SourceModelId
  source_model_version_id = $SourceModelVersionId
  model_name = $ModelName
  model_type = $ModelType
  base_model = $BaseModel
  version_name = ""
  file_name = if ($LocalPath) { Split-Path $LocalPath -Leaf } else { "" }
  file_extension = if ($LocalPath) { [System.IO.Path]::GetExtension($LocalPath) } else { "" }
  file_size_bytes = if ($LocalPath -and (Test-Path $LocalPath)) { (Get-Item $LocalPath).Length } else { 0 }
  sha256 = if ($LocalPath -and (Test-Path $LocalPath)) { (Get-FileHash $LocalPath -Algorithm SHA256).Hash } else { "" }
  source_hashes = @{}
  local_path = $LocalPath
  storage_location = "local"
  workflow_lane = $WorkflowLane
  compatibility_status = "needs_runtime_validation"
  compatible_engines = @()
  trigger_words = @()
  intended_use = ""
  prompt_notes = ""
  negative_prompt_notes = ""
  qa_status = "not_tested"
  runtime_validation_status = "queued"
  visual_impact = ""
  video_impact = ""
  audio_impact = ""
  known_issues = @()
  last_tested_at = ""
  evidence_paths = @()
}
$record | ConvertTo-Json -Depth 20
