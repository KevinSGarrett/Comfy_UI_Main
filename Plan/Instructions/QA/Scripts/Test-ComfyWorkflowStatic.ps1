<#
.SYNOPSIS
Validates a ComfyUI API workflow lane without launching ComfyUI.

.DESCRIPTION
Checks workflow graph shape, required node classes, link references, patch points,
runtime requirements, and smoke request coverage. This is static validation only;
it does not prove ComfyUI object_info compatibility, model hash/path resolution,
model loading, generated output, or artifact QA.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneDir = "C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\workflow_templates\base_generation\sdxl_low_risk_fallback_lane",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) {
    throw "Required JSON file missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Add-Defect {
  param(
    [System.Collections.ArrayList]$List,
    [string]$Severity,
    [string]$Code,
    [string]$Message
  )
  [void]$List.Add([ordered]@{
    severity = $Severity
    code = $Code
    message = $Message
  })
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

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

$workflowPath = Join-Path $LaneDir "workflow.api.json"
$patchPath = Join-Path $LaneDir "patch_points.json"
$runtimePath = Join-Path $LaneDir "runtime_requirements.json"
$smokePath = Join-Path $LaneDir "smoke_test_request.json"
$requiredFiles = @($workflowPath, $patchPath, $runtimePath, $smokePath)

$defects = New-Object System.Collections.ArrayList
$warnings = New-Object System.Collections.ArrayList

foreach ($file in $requiredFiles) {
  if (!(Test-Path -LiteralPath $file)) {
    Add-Defect -List $defects -Severity "critical" -Code "missing_file" -Message "Required lane file missing: $file"
  }
}

$workflow = Read-JsonFile -Path $workflowPath
$patchPoints = Read-JsonFile -Path $patchPath
$runtime = Read-JsonFile -Path $runtimePath
$smoke = Read-JsonFile -Path $smokePath

$nodeMap = @{}
$classCounts = @{}
$links = New-Object System.Collections.ArrayList

foreach ($property in $workflow.PSObject.Properties) {
  $nodeId = [string]$property.Name
  $node = $property.Value

  if (!(Has-Property -Object $node -Name "class_type")) {
    Add-Defect -List $defects -Severity "critical" -Code "missing_class_type" -Message "Node $nodeId is missing class_type."
    continue
  }
  if (!(Has-Property -Object $node -Name "inputs")) {
    Add-Defect -List $defects -Severity "critical" -Code "missing_inputs" -Message "Node $nodeId is missing inputs."
    continue
  }

  $nodeMap[$nodeId] = $node
  $classType = [string]$node.class_type
  if (!$classCounts.ContainsKey($classType)) { $classCounts[$classType] = 0 }
  $classCounts[$classType] = $classCounts[$classType] + 1
}

foreach ($nodeId in $nodeMap.Keys) {
  $node = $nodeMap[$nodeId]
  foreach ($inputProperty in $node.inputs.PSObject.Properties) {
    $value = $inputProperty.Value
    if ($value -is [System.Array] -and $value.Count -eq 2) {
      $fromNode = [string]$value[0]
      $outputIndex = $value[1]
      [void]$links.Add([ordered]@{
        to_node = $nodeId
        input = $inputProperty.Name
        from_node = $fromNode
        output_index = $outputIndex
      })
      if (!$nodeMap.ContainsKey($fromNode)) {
        Add-Defect -List $defects -Severity "critical" -Code "broken_node_reference" -Message "Node $nodeId input $($inputProperty.Name) references missing node $fromNode."
      }
      if (!($outputIndex -is [int] -or $outputIndex -is [long])) {
        Add-Defect -List $defects -Severity "major" -Code "invalid_output_index" -Message "Node $nodeId input $($inputProperty.Name) has non-integer output index."
      } elseif ([int]$outputIndex -lt 0) {
        Add-Defect -List $defects -Severity "major" -Code "negative_output_index" -Message "Node $nodeId input $($inputProperty.Name) has negative output index."
      }
    }
  }
}

foreach ($requiredNode in @($runtime.required_nodes)) {
  if (!$classCounts.ContainsKey([string]$requiredNode)) {
    Add-Defect -List $defects -Severity "critical" -Code "missing_required_node_class" -Message "Workflow is missing required node class $requiredNode."
  }
}

foreach ($patchPoint in @($patchPoints.patch_points)) {
  $name = [string]$patchPoint.name
  $required = [bool]$patchPoint.required
  $nodeId = $patchPoint.node_id

  if ($required -and [string]::IsNullOrWhiteSpace([string]$nodeId)) {
    Add-Defect -List $defects -Severity "critical" -Code "patch_point_missing_node" -Message "Required patch point $name has no node_id."
    continue
  }
  if ([string]::IsNullOrWhiteSpace([string]$nodeId)) {
    continue
  }

  $nodeKey = [string]$nodeId
  if (!$nodeMap.ContainsKey($nodeKey)) {
    Add-Defect -List $defects -Severity "critical" -Code "patch_point_node_missing" -Message "Patch point $name references missing node $nodeKey."
    continue
  }

  $node = $nodeMap[$nodeKey]
  if ((Has-Property -Object $patchPoint -Name "node_type") -and [string]$patchPoint.node_type -ne [string]$node.class_type) {
    Add-Defect -List $defects -Severity "major" -Code "patch_point_node_type_mismatch" -Message "Patch point $name expected $($patchPoint.node_type) but node $nodeKey is $($node.class_type)."
  }

  if ((Has-Property -Object $patchPoint -Name "input") -and $null -ne $patchPoint.input -and [string]$patchPoint.input -ne "") {
    if (!(Has-Property -Object $node.inputs -Name ([string]$patchPoint.input))) {
      Add-Defect -List $defects -Severity "major" -Code "patch_point_input_missing" -Message "Patch point $name input $($patchPoint.input) is not present on node $nodeKey."
    }
  }

  if ((Has-Property -Object $patchPoint -Name "inputs") -and $null -ne $patchPoint.inputs) {
    foreach ($inputName in @($patchPoint.inputs)) {
      if (!(Has-Property -Object $node.inputs -Name ([string]$inputName))) {
        Add-Defect -List $defects -Severity "major" -Code "patch_point_input_missing" -Message "Patch point $name input $inputName is not present on node $nodeKey."
      }
    }
  }
}

$checkpointNodes = @()
$modelReferenceChecks = New-Object System.Collections.ArrayList
foreach ($nodeId in $nodeMap.Keys) {
  $node = $nodeMap[$nodeId]
  if ([string]$node.class_type -eq "CheckpointLoaderSimple") {
    $checkpointNodes += [ordered]@{
      node_id = $nodeId
      ckpt_name = [string]$node.inputs.ckpt_name
    }
  }
}

foreach ($model in @($runtime.required_models)) {
  $role = [string]$model.role
  $expectedName = [string]$model.filename
  $explicitNodeId = $(if (Has-Property -Object $model -Name "node_id") { [string]$model.node_id } else { "" })
  $expectedNodeClass = $(if (Has-Property -Object $model -Name "node_class") { [string]$model.node_class } elseif (Has-Property -Object $model -Name "node_type") { [string]$model.node_type } else { "" })
  $inputName = $(if (Has-Property -Object $model -Name "input") { [string]$model.input } elseif (Has-Property -Object $model -Name "input_name") { [string]$model.input_name } else { "" })
  $matched = $false
  $observed = @()

  if (![string]::IsNullOrWhiteSpace($explicitNodeId) -or ![string]::IsNullOrWhiteSpace($expectedNodeClass)) {
    if ([string]::IsNullOrWhiteSpace($inputName)) {
      Add-Defect -List $defects -Severity "major" -Code "model_requirement_missing_input" -Message "Runtime model requirement $expectedName declares node mapping but no input/input_name."
    } else {
      foreach ($nodeId in $nodeMap.Keys) {
        $node = $nodeMap[$nodeId]
        $classMatches = ([string]::IsNullOrWhiteSpace($expectedNodeClass) -or [string]$node.class_type -eq $expectedNodeClass)
        $idMatches = ([string]::IsNullOrWhiteSpace($explicitNodeId) -or [string]$nodeId -eq $explicitNodeId)
        if ($classMatches -and $idMatches -and (Has-Property -Object $node.inputs -Name $inputName)) {
          $value = [string]$node.inputs.$inputName
          $observed += ("{0}.{1}={2}" -f $nodeId, $inputName, $value)
          if ($value -eq $expectedName) { $matched = $true }
        }
      }
      if (!$matched) {
        Add-Defect -List $defects -Severity "critical" -Code "model_requirement_not_referenced" -Message "Runtime model requirement $expectedName is not referenced by node mapping node_id='$explicitNodeId' node_class='$expectedNodeClass' input='$inputName'."
      }
    }
  } elseif ($role -eq "checkpoint") {
    foreach ($checkpointNode in $checkpointNodes) {
      $observed += ("{0}.ckpt_name={1}" -f $checkpointNode.node_id, $checkpointNode.ckpt_name)
      if ([string]$checkpointNode.ckpt_name -eq $expectedName) { $matched = $true }
    }
    if (!$matched) {
      Add-Defect -List $defects -Severity "critical" -Code "checkpoint_requirement_not_referenced" -Message "Runtime checkpoint requirement $expectedName is not referenced by any CheckpointLoaderSimple node."
    }
  } else {
    Add-Defect -List $defects -Severity "major" -Code "model_requirement_missing_node_mapping" -Message "Runtime non-checkpoint model requirement $expectedName must declare node_id/input or node_class/input for static workflow validation."
  }

  [void]$modelReferenceChecks.Add([ordered]@{
    role = $role
    filename = $expectedName
    node_id = $explicitNodeId
    node_class = $expectedNodeClass
    input = $inputName
    observed = $observed
    matched = $matched
  })
}

if ([string]$patchPoints.lane_id -ne [string]$runtime.lane_id -or [string]$smoke.lane_id -ne [string]$runtime.lane_id) {
  Add-Defect -List $defects -Severity "major" -Code "lane_id_mismatch" -Message "Lane IDs differ between patch_points, runtime_requirements, or smoke_test_request."
}

foreach ($patchPoint in @($patchPoints.patch_points)) {
  if ([bool]$patchPoint.required) {
    $name = [string]$patchPoint.name
    if (!(Has-Property -Object $smoke.request_patch_values -Name $name)) {
      Add-Defect -List $defects -Severity "major" -Code "smoke_request_patch_missing" -Message "Smoke request is missing required patch value $name."
    }
  }
}

if ((Has-Property -Object $smoke -Name "execution_allowed") -and [bool]$smoke.execution_allowed) {
  Add-Defect -List $defects -Severity "major" -Code "execution_allowed_before_runtime_proof" -Message "Smoke request execution_allowed is true before object-info/path/hash proof."
}

$dependencies = @{}
foreach ($nodeId in $nodeMap.Keys) { $dependencies[$nodeId] = @() }
foreach ($link in $links) {
  if ($nodeMap.ContainsKey([string]$link.from_node)) {
    $dependencies[[string]$link.to_node] += [string]$link.from_node
  }
}

$visitState = @{}
function Test-NodeCycle {
  param([string]$NodeId)
  if ($visitState.ContainsKey($NodeId)) {
    if ($visitState[$NodeId] -eq 1) { return $true }
    if ($visitState[$NodeId] -eq 2) { return $false }
  }
  $visitState[$NodeId] = 1
  foreach ($dep in @($dependencies[$NodeId])) {
    if (Test-NodeCycle -NodeId $dep) { return $true }
  }
  $visitState[$NodeId] = 2
  return $false
}

foreach ($nodeId in $nodeMap.Keys) {
  if (Test-NodeCycle -NodeId $nodeId) {
    Add-Defect -List $defects -Severity "critical" -Code "workflow_cycle_detected" -Message "Workflow graph contains a cycle involving node $nodeId."
    break
  }
}

$relativeLaneDir = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $LaneDir
$status = "pass"
if ($defects.Count -gt 0) { $status = "fail" }

$record = [ordered]@{
  evidence_id = "LOCAL-COMFY-WORKFLOW-STATIC-" + (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  lane_dir = $relativeLaneDir.Replace("\", "/")
  workflow_path = (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $workflowPath).Replace("\", "/")
  lane_id = [string]$runtime.lane_id
  qa_status = $status
  node_count = $nodeMap.Count
  link_count = $links.Count
  class_counts = $classCounts
  checkpoint_nodes = $checkpointNodes
  model_reference_checks = @($modelReferenceChecks)
  defects = @($defects)
  warnings = @($warnings)
  runtime_gates_not_proven_by_static_validation = @(
    "ComfyUI object_info node compatibility",
    "model path resolution",
    "model sha256/hash proof",
    "model load validation",
    "runtime execution output",
    "generated artifact QA"
  )
  next_action = "Refresh AWS auth, run EC2 static proof for object_info/path/hash, then run bounded smoke execution."
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote workflow static validation record: $OutFile"
}

$record | ConvertTo-Json -Depth 20
if ($status -ne "pass") { exit 2 }
