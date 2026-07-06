<#
.SYNOPSIS
Builds or executes a bounded ComfyUI API smoke request for a workflow lane.

.DESCRIPTION
Dry-run by default. In dry-run mode, this script reads workflow.api.json,
patch_points.json, and smoke_test_request.json, applies the smoke patch values,
validates that the request body can be built, and writes an evidence record.

With -Execute, it posts the patched workflow to a running ComfyUI API and polls
/history/{prompt_id}. Execution requires either smoke_test_request.json to allow
execution or a static proof file that confirms object_info and model path/hash
proof. This script does not start EC2 and does not pull back generated files by
itself.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneDir = "C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\workflow_templates\base_generation\sdxl_low_risk_fallback_lane",
  [string]$ComfyApiBaseUrl = "http://127.0.0.1:8188",
  [string]$StaticProofFile = "",
  [string]$OutFile = "",
  [string]$OutRequestFile = "",
  [string]$ClientId = "codex-desktop-smoke",
  [int]$TimeoutSeconds = 600,
  [int]$PollSeconds = 2,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) {
    throw "Required JSON file missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
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

function ConvertTo-HashtableDeep {
  param([object]$InputObject)

  if ($null -eq $InputObject) { return $null }

  if ($InputObject -is [System.Collections.IEnumerable] -and
      $InputObject -isnot [string] -and
      $InputObject -isnot [System.Collections.IDictionary] -and
      $InputObject -isnot [pscustomobject]) {
    $array = @()
    foreach ($item in $InputObject) {
      $array += ,(ConvertTo-HashtableDeep -InputObject $item)
    }
    return $array
  }

  if ($InputObject -is [pscustomobject]) {
    $hash = [ordered]@{}
    foreach ($property in $InputObject.PSObject.Properties) {
      $hash[$property.Name] = ConvertTo-HashtableDeep -InputObject $property.Value
    }
    return $hash
  }

  return $InputObject
}

function Set-WorkflowInput {
  param(
    [hashtable]$Workflow,
    [string]$NodeId,
    [string]$InputName,
    [object]$Value
  )

  if (!$Workflow.Contains($NodeId)) {
    throw "Patch references missing node: $NodeId"
  }
  if (!$Workflow[$NodeId].Contains("inputs")) {
    throw "Patch references node without inputs: $NodeId"
  }
  if (!$Workflow[$NodeId]["inputs"].Contains($InputName)) {
    throw "Patch references missing input '$InputName' on node $NodeId"
  }
  $Workflow[$NodeId]["inputs"][$InputName] = $Value
}

function Test-StaticProof {
  param([string]$Path)

  $result = [ordered]@{
    supplied = $false
    valid = $false
    errors = @()
    object_info_status = $null
    model_proof_count = 0
  }

  if ([string]::IsNullOrWhiteSpace($Path)) {
    $result.errors += "No static proof file supplied."
    return $result
  }
  if (!(Test-Path -LiteralPath $Path)) {
    $result.errors += "Static proof file not found: $Path"
    return $result
  }

  $result.supplied = $true
  $proof = Read-JsonFile -Path $Path
  $proofPayload = $proof

  if (Has-Property -Object $proof -Name "stdout") {
    if ([string]::IsNullOrWhiteSpace([string]$proof.stdout)) {
      $result.errors += "Static proof stdout is empty."
      return $result
    }
    try {
      $proofPayload = ([string]$proof.stdout | ConvertFrom-Json)
    } catch {
      $result.errors += "Static proof stdout is not valid JSON: $($_.Exception.Message)"
      return $result
    }
    if ((Has-Property -Object $proof -Name "command_status") -and [string]$proof.command_status -ne "Success") {
      $result.errors += "Static proof command_status is $($proof.command_status), not Success."
    }
  }

  if (!(Has-Property -Object $proofPayload -Name "object_info")) {
    $result.errors += "Static proof payload has no object_info."
  } else {
    $result.object_info_status = [string]$proofPayload.object_info.status
    if ([string]$proofPayload.object_info.status -ne "pass") {
      $result.errors += "Static proof object_info status is $($proofPayload.object_info.status), not pass."
    }
  }

  if (!(Has-Property -Object $proofPayload -Name "model_proofs")) {
    $result.errors += "Static proof payload has no model_proofs."
  } else {
    $models = @($proofPayload.model_proofs)
    $result.model_proof_count = $models.Count
    if ($models.Count -eq 0) {
      $result.errors += "Static proof has zero model_proofs."
    }
    foreach ($model in $models) {
      if (-not [bool]$model.exists) {
        $result.errors += "Required model missing in static proof: $($model.relative_path)"
      }
      if ([string]::IsNullOrWhiteSpace([string]$model.sha256)) {
        $result.errors += "Required model missing sha256 in static proof: $($model.relative_path)"
      }
    }
  }

  $result.valid = ($result.errors.Count -eq 0)
  return $result
}

$workflowPath = Join-Path $LaneDir "workflow.api.json"
$patchPath = Join-Path $LaneDir "patch_points.json"
$smokePath = Join-Path $LaneDir "smoke_test_request.json"

$workflow = ConvertTo-HashtableDeep -InputObject (Read-JsonFile -Path $workflowPath)
$patchPoints = Read-JsonFile -Path $patchPath
$smoke = Read-JsonFile -Path $smokePath
$patchValues = $smoke.request_patch_values
$patchedInputs = @()

foreach ($patchPoint in @($patchPoints.patch_points)) {
  $name = [string]$patchPoint.name
  if (!(Has-Property -Object $patchValues -Name $name)) {
    if ([bool]$patchPoint.required) {
      throw "Smoke request is missing required patch value: $name"
    }
    continue
  }

  $nodeId = [string]$patchPoint.node_id
  $value = $patchValues.$name
  if ([string]::IsNullOrWhiteSpace($nodeId)) { continue }

  if ((Has-Property -Object $patchPoint -Name "input") -and $null -ne $patchPoint.input -and [string]$patchPoint.input -ne "") {
    Set-WorkflowInput -Workflow $workflow -NodeId $nodeId -InputName ([string]$patchPoint.input) -Value (ConvertTo-HashtableDeep -InputObject $value)
    $patchedInputs += "$nodeId.$($patchPoint.input)"
  }

  if ((Has-Property -Object $patchPoint -Name "inputs") -and $null -ne $patchPoint.inputs) {
    foreach ($inputName in @($patchPoint.inputs)) {
      if (!(Has-Property -Object $value -Name ([string]$inputName))) {
        throw "Patch value $name is missing subvalue $inputName"
      }
      Set-WorkflowInput -Workflow $workflow -NodeId $nodeId -InputName ([string]$inputName) -Value (ConvertTo-HashtableDeep -InputObject $value.$inputName)
      $patchedInputs += "$nodeId.$inputName"
    }
  }
}

$requestBody = [ordered]@{
  prompt = $workflow
  client_id = $ClientId
}

if (![string]::IsNullOrWhiteSpace($OutRequestFile)) {
  $requestDir = Split-Path -Parent $OutRequestFile
  if (![string]::IsNullOrWhiteSpace($requestDir)) {
    $null = New-Item -ItemType Directory -Force -Path $requestDir
  }
  $requestBody | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $OutRequestFile -Encoding UTF8
}

$proofStatus = Test-StaticProof -Path $StaticProofFile
$executionAllowedByRequest = $false
if (Has-Property -Object $smoke -Name "execution_allowed") {
  $executionAllowedByRequest = [bool]$smoke.execution_allowed
}
$executionAllowed = $executionAllowedByRequest -or [bool]$proofStatus.valid

$record = [ordered]@{
  evidence_id = "COMFY-WORKFLOW-SMOKE-" + (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  mode = $(if ($Execute) { "execute" } else { "dry_run" })
  lane_id = [string]$smoke.lane_id
  workflow_path = (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $workflowPath).Replace("\", "/")
  api_base_url = $ComfyApiBaseUrl
  api_endpoint = "/prompt"
  patched_inputs = $patchedInputs
  node_count = $workflow.Keys.Count
  request_body_written = -not [string]::IsNullOrWhiteSpace($OutRequestFile)
  request_body_path = $OutRequestFile
  static_proof = $proofStatus
  execution_allowed = $executionAllowed
  generation_executed = $false
  prompt_id = $null
  output_images = @()
  history_status = "not_started"
  errors = @()
  next_action = "Run only after EC2 static proof exists; pull back output artifacts and perform image QA."
}

if ($Execute) {
  if (!$executionAllowed) {
    $record.errors += "Execution blocked: smoke_test_request execution_allowed is false and static proof is not valid."
  } else {
    try {
      $promptUri = $ComfyApiBaseUrl.TrimEnd("/") + "/prompt"
      $promptResponse = Invoke-RestMethod -Method Post -Uri $promptUri -ContentType "application/json" -Body ($requestBody | ConvertTo-Json -Depth 40)
      $record.prompt_id = [string]$promptResponse.prompt_id
      if ([string]::IsNullOrWhiteSpace($record.prompt_id)) {
        throw "ComfyUI /prompt response did not include prompt_id."
      }

      $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
      $historyUri = $ComfyApiBaseUrl.TrimEnd("/") + "/history/$($record.prompt_id)"
      while ((Get-Date) -lt $deadline) {
        $history = Invoke-RestMethod -Method Get -Uri $historyUri
        if (Has-Property -Object $history -Name $record.prompt_id) {
          $promptHistory = $history.PSObject.Properties[$record.prompt_id].Value
          if (Has-Property -Object $promptHistory -Name "outputs") {
            foreach ($outputNode in $promptHistory.outputs.PSObject.Properties) {
              if (Has-Property -Object $outputNode.Value -Name "images") {
                foreach ($image in @($outputNode.Value.images)) {
                  $record.output_images += [ordered]@{
                    node_id = $outputNode.Name
                    filename = [string]$image.filename
                    subfolder = [string]$image.subfolder
                    type = [string]$image.type
                  }
                }
              }
            }
            if ($record.output_images.Count -gt 0) {
              $record.history_status = "outputs_found"
              break
            }
          }
        }
        Start-Sleep -Seconds $PollSeconds
      }

      if ($record.output_images.Count -eq 0) {
        $record.history_status = "timeout_or_no_images"
        $record.errors += "No output images were found before timeout."
      } else {
        $record.generation_executed = $true
      }
    } catch {
      $record.errors += $_.Exception.Message
      $record.history_status = "error"
    }
  }
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote ComfyUI smoke record: $OutFile"
}

$record | ConvertTo-Json -Depth 40
if ($Execute -and ($record.errors.Count -gt 0 -or $record.output_images.Count -eq 0)) { exit 2 }
