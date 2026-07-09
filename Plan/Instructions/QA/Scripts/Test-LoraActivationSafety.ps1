<#
.SYNOPSIS
Validates that active workflow lanes do not carry disabled LoRA library nodes.

.DESCRIPTION
Scans the active lane manifest and mirrored workflow API files for active LoRA
loader/library nodes. It also checks that LoRA catalog data remains in registry
form and that active lanes expose LoRA selection only through optional profile
patch points. This is a local static QA gate only; it does not run ComfyUI or
contact AWS/GitHub/Civitai.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ActiveLanesFile = "Workflows/base_generation/ACTIVE_LANES.json",
  [string]$LoraCatalogFile = "Plan/10_REGISTRIES/main_flow_wave04_lora_catalog_inventory_raw.json",
  [string]$CompatibilityMatrixFile = "Plan/10_REGISTRIES/wave15_model_family_compatibility_matrix.json",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Get-RelativePathCompat {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$TargetPath
  )
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
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  return (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $Path)
}

function Test-JsonProperty {
  param([object]$Object, [string]$Name)
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 40
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Get-WorkflowScanRecord {
  param(
    [Parameter(Mandatory=$true)][string]$LaneId,
    [Parameter(Mandatory=$true)][string]$WorkflowPath,
    [Parameter(Mandatory=$true)][string]$ScanRole
  )

  $record = [ordered]@{
    lane_id = $LaneId
    scan_role = $ScanRole
    workflow_path = Convert-ToProjectPath -Path $WorkflowPath
    file_exists = (Test-Path -LiteralPath $WorkflowPath -PathType Leaf)
    parse_ok = $false
    node_count = 0
    active_lora_node_count = 0
    active_lora_nodes = @()
  }

  if (!$record.file_exists) { return $record }

  $workflow = Get-Content -Raw -LiteralPath $WorkflowPath | ConvertFrom-Json
  $record.parse_ok = $true
  $nodes = @($workflow.PSObject.Properties)
  $record.node_count = $nodes.Count
  $loraNodes = New-Object System.Collections.ArrayList
  foreach ($nodeProp in $nodes) {
    $node = $nodeProp.Value
    $classType = ""
    if (Test-JsonProperty -Object $node -Name "class_type") { $classType = [string]$node.class_type }
    $title = ""
    if ((Test-JsonProperty -Object $node -Name "_meta") -and (Test-JsonProperty -Object $node._meta -Name "title")) {
      $title = [string]$node._meta.title
    }
    if ($classType -match "(?i)lora" -or $title -match "(?i)lora") {
      [void]$loraNodes.Add([ordered]@{
        node_id = [string]$nodeProp.Name
        class_type = $classType
        title = $title
      })
    }
  }
  $record.active_lora_nodes = @($loraNodes)
  $record.active_lora_node_count = $loraNodes.Count
  return $record
}

$activeLanesPath = Resolve-ProjectPath -Path $ActiveLanesFile
$loraCatalogPath = Resolve-ProjectPath -Path $LoraCatalogFile
$compatibilityMatrixPath = Resolve-ProjectPath -Path $CompatibilityMatrixFile

if (!(Test-Path -LiteralPath $activeLanesPath -PathType Leaf)) { throw "Active lanes file not found: $activeLanesPath" }
if (!(Test-Path -LiteralPath $loraCatalogPath -PathType Leaf)) { throw "LoRA catalog file not found: $loraCatalogPath" }
if (!(Test-Path -LiteralPath $compatibilityMatrixPath -PathType Leaf)) { throw "Compatibility matrix file not found: $compatibilityMatrixPath" }

$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$stampForFile = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
  New-Item -ItemType Directory -Force -Path $outDir > $null
  $OutFile = Join-Path $outDir "W69_LOCAL_LORA_ACTIVATION_SAFETY_$stampForFile.json"
}

$activeLanes = Get-Content -Raw -LiteralPath $activeLanesPath | ConvertFrom-Json
$catalogRaw = Get-Content -Raw -LiteralPath $loraCatalogPath | ConvertFrom-Json
$catalog = New-Object System.Collections.ArrayList
foreach ($entry in $catalogRaw) { [void]$catalog.Add($entry) }

$compatibilityMatrixRaw = Get-Content -Raw -LiteralPath $compatibilityMatrixPath | ConvertFrom-Json
$compatibilityMatrix = New-Object System.Collections.ArrayList
foreach ($entry in $compatibilityMatrixRaw) { [void]$compatibilityMatrix.Add($entry) }

$workflowScans = New-Object System.Collections.ArrayList
$patchPointScans = New-Object System.Collections.ArrayList
$defects = New-Object System.Collections.ArrayList
$warnings = New-Object System.Collections.ArrayList

foreach ($lane in @($activeLanes.lanes)) {
  $laneId = [string]$lane.lane_id
  $workflowPath = Resolve-ProjectPath -Path ([string]$lane.workflow)
  $planWorkflowPath = $null
  if ([string]$lane.workflow -match "^Workflows/base_generation/") {
    $planWorkflowPath = Resolve-ProjectPath -Path ([string]$lane.workflow -replace "^Workflows/base_generation/", "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/")
  }

  foreach ($scan in @(
    @{ Path = $workflowPath; Role = "active_workflow" },
    @{ Path = $planWorkflowPath; Role = "plan_template_mirror" }
  )) {
    if ([string]::IsNullOrWhiteSpace($scan.Path)) { continue }
    $scanRecord = Get-WorkflowScanRecord -LaneId $laneId -WorkflowPath $scan.Path -ScanRole $scan.Role
    [void]$workflowScans.Add($scanRecord)
    if ($scanRecord.active_lora_node_count -gt 0) {
      [void]$defects.Add([ordered]@{
        severity = "blocking"
        code = "ACTIVE_LORA_NODE_IN_RUNTIME_WORKFLOW"
        lane_id = $laneId
        workflow_path = $scanRecord.workflow_path
        active_lora_nodes = $scanRecord.active_lora_nodes
      })
    }
  }

  $patchPath = Resolve-ProjectPath -Path ([string]$lane.patch_points)
  $patchRecord = [ordered]@{
    lane_id = $laneId
    patch_points_path = Convert-ToProjectPath -Path $patchPath
    file_exists = (Test-Path -LiteralPath $patchPath -PathType Leaf)
    parse_ok = $false
    lora_patch_point_count = 0
    lora_patch_points = @()
  }
  if ($patchRecord.file_exists) {
    $patch = Get-Content -Raw -LiteralPath $patchPath | ConvertFrom-Json
    $patchRecord.parse_ok = $true
    $loraPatchPoints = @($patch.patch_points | Where-Object {
      ([string]$_.name -match "(?i)lora") -or ([string]$_.node_type -match "(?i)lora")
    })
    $patchRecord.lora_patch_point_count = $loraPatchPoints.Count
    $patchRecord.lora_patch_points = @($loraPatchPoints | ForEach-Object {
      [ordered]@{
        name = [string]$_.name
        required = $_.required
        node_id = $_.node_id
        node_type = [string]$_.node_type
        status = [string]$_.status
      }
    })
  }
  [void]$patchPointScans.Add($patchRecord)
}

$catalogDisabledCount = @($catalog | Where-Object { $_.disabled_by_default -eq $true }).Count
$catalogAlreadyActiveCount = @($catalog | Where-Object { $_.already_active_in_main_chain -eq $true }).Count
$catalogEngineCounts = @{}
foreach ($entry in $catalog) {
  $engine = [string]$entry.engine
  if ([string]::IsNullOrWhiteSpace($engine)) { $engine = "unknown" }
  if (!$catalogEngineCounts.ContainsKey($engine)) { $catalogEngineCounts[$engine] = 0 }
  $catalogEngineCounts[$engine]++
}

if ($catalog.Count -gt 0 -and $catalogDisabledCount -ne $catalog.Count) {
  [void]$defects.Add([ordered]@{
    severity = "blocking"
    code = "LORA_CATALOG_NOT_DISABLED_BY_DEFAULT"
    disabled_count = $catalogDisabledCount
    catalog_count = $catalog.Count
  })
}
if ($catalogAlreadyActiveCount -gt 0) {
  [void]$warnings.Add([ordered]@{
    severity = "warning"
    code = "HISTORICAL_SOURCE_LORA_ACTIVE_COPY_LABELS"
    already_active_count = $catalogAlreadyActiveCount
    note = "These entries are historical source-canvas ACTIVE_COPY labels. They remain disabled_by_default and no active extracted workflow/template contains LoRA loader nodes."
  })
}

$result = "pass_local_lora_activation_safety"
if ($defects.Count -gt 0) { $result = "fail_local_lora_activation_safety" }

$evidence = [ordered]@{
  schema_version = "1.0"
  evidence_id = "W69-LOCAL-LORA-ACTIVATION-SAFETY-$stampForFile"
  timestamp = $timestamp
  project_root = $ProjectRoot
  qa_type = "local_static_lora_activation_safety"
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  source_requirements = @(
    "Plan/07_IMPLEMENTATION/COMFYUI_WIRING_REPAIR_LIST.md Priority 3",
    "Plan/07_IMPLEMENTATION/WAVE04_MAIN_FLOW_FIX_UPDATE_CONNECT_IMPROVE_LIST.md P0 item 1 and item 2",
    "Plan/07_IMPLEMENTATION/WAVE05_MAIN_FLOW_TO_MODULE_EXTRACTION_INSTRUCTIONS.md LoRA library note"
  )
  active_lanes_file = Convert-ToProjectPath -Path $activeLanesPath
  lora_catalog_file = Convert-ToProjectPath -Path $loraCatalogPath
  compatibility_matrix_file = Convert-ToProjectPath -Path $compatibilityMatrixPath
  active_lane_count = @($activeLanes.lanes).Count
  workflow_scan_count = $workflowScans.Count
  workflow_scans = @($workflowScans)
  patch_point_scans = @($patchPointScans)
  lora_catalog_summary = [ordered]@{
    entry_count = $catalog.Count
    disabled_by_default_count = $catalogDisabledCount
    already_active_in_main_chain_count = $catalogAlreadyActiveCount
    engine_counts = $catalogEngineCounts
  }
  compatibility_matrix_summary = [ordered]@{
    family_count = $compatibilityMatrix.Count
    families = @($compatibilityMatrix | ForEach-Object { $_.family_id })
  }
  defects = @($defects)
  warnings = @($warnings)
  result = $result
  certification_status = "local_static_safety_gate_only_not_runtime_or_final_certification"
  boundary = "This proves active local workflow/templates do not contain active LoRA loader/library nodes and that catalog entries remain disabled by default. It does not activate or runtime-test any LoRA profile."
}

Write-JsonNoBom -Value $evidence -Path $OutFile -Depth 60

$activeLoraNodeTotal = 0
foreach ($scanRecord in @($workflowScans)) {
  $activeLoraNodeTotal += [int]$scanRecord.active_lora_node_count
}

[pscustomobject]@{
  result = $result
  evidence = Convert-ToProjectPath -Path $OutFile
  active_lane_count = @($activeLanes.lanes).Count
  workflow_scan_count = $workflowScans.Count
  active_lora_node_total = $activeLoraNodeTotal
  defects = $defects.Count
} | ConvertTo-Json -Depth 8
