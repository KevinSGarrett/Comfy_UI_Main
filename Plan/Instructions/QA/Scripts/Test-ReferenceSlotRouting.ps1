param(
    [Parameter(Mandatory = $true)]
    [string]$RequestPath,

    [Parameter(Mandatory = $true)]
    [string]$EvidencePath,

    [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $Path))
}

function Get-ImageInfo {
    param([Parameter(Mandatory = $true)][string]$Path)
    $image = $null
    try {
        $image = [System.Drawing.Image]::FromFile($Path)
        return [ordered]@{
            width = [int]$image.Width
            height = [int]$image.Height
            pixel_format = $image.PixelFormat.ToString()
        }
    }
    finally {
        if ($null -ne $image) {
            $image.Dispose()
        }
    }
}

function Read-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
}

function Test-RequiredPatchPoint {
    param(
        [Parameter(Mandatory = $true)]$PatchPoints,
        [Parameter(Mandatory = $true)][string]$Name
    )
    foreach ($point in $PatchPoints) {
        if ($point.name -eq $Name -and $point.required -eq $true) {
            return $point
        }
    }
    return $null
}

Add-Type -AssemblyName System.Drawing

$resolvedRequestPath = Resolve-ProjectPath -Path $RequestPath
$resolvedEvidencePath = Resolve-ProjectPath -Path $EvidencePath
$request = Read-JsonFile -Path $resolvedRequestPath
$defects = New-Object System.Collections.Generic.List[string]
$bindingResults = New-Object System.Collections.Generic.List[object]

$nonFaceSlots = @($request.bindings | Where-Object { $_.semantic_slot -ne "face_reference" })
if ($nonFaceSlots.Count -lt [int]$request.minimum_required_non_face_slots) {
    $defects.Add("minimum_required_non_face_slots_not_met:$($nonFaceSlots.Count)")
}

$seenSlots = @{}
foreach ($binding in $request.bindings) {
    $slotDefects = New-Object System.Collections.Generic.List[string]
    if ([string]::IsNullOrWhiteSpace($binding.semantic_slot)) {
        $slotDefects.Add("missing_semantic_slot")
    }
    elseif ($seenSlots.ContainsKey($binding.semantic_slot)) {
        $slotDefects.Add("duplicate_semantic_slot:$($binding.semantic_slot)")
    }
    else {
        $seenSlots[$binding.semantic_slot] = $true
    }

    if ($binding.semantic_slot -eq "face_reference") {
        $slotDefects.Add("face_reference_slot_not_allowed_for_beyond_face_contract")
    }

    $patchPointsPath = Resolve-ProjectPath -Path $binding.patch_points_path
    $workflowPath = Resolve-ProjectPath -Path $binding.workflow_path
    $controlImagePath = Resolve-ProjectPath -Path $binding.control_image_path

    if (-not (Test-Path -LiteralPath $patchPointsPath -PathType Leaf)) {
        $slotDefects.Add("missing_patch_points_path:$($binding.patch_points_path)")
    }
    if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
        $slotDefects.Add("missing_workflow_path:$($binding.workflow_path)")
    }
    if (-not (Test-Path -LiteralPath $controlImagePath -PathType Leaf)) {
        $slotDefects.Add("missing_control_image_path:$($binding.control_image_path)")
    }

    $patchPointFindings = @()
    if (Test-Path -LiteralPath $patchPointsPath -PathType Leaf) {
        $patchDoc = Read-JsonFile -Path $patchPointsPath
        if ($patchDoc.lane_id -ne $binding.lane_id) {
            $slotDefects.Add("lane_id_mismatch_patch_points:$($binding.lane_id)")
        }
        if ($patchDoc.module_id -ne $binding.module_id) {
            $slotDefects.Add("module_id_mismatch_patch_points:$($binding.module_id)")
        }
        foreach ($requiredPatchPoint in $binding.required_patch_points) {
            $point = Test-RequiredPatchPoint -PatchPoints $patchDoc.patch_points -Name $requiredPatchPoint
            if ($null -eq $point) {
                $slotDefects.Add("missing_required_patch_point:$requiredPatchPoint")
            }
            else {
                $pointInput = $null
                $pointInputs = $null
                if ($null -ne $point.PSObject.Properties["input"]) {
                    $pointInput = $point.input
                }
                if ($null -ne $point.PSObject.Properties["inputs"]) {
                    $pointInputs = $point.inputs
                }
                $patchPointFindings += [ordered]@{
                    name = $point.name
                    node_id = $point.node_id
                    node_type = $point.node_type
                    input = $pointInput
                    inputs = $pointInputs
                }
            }
        }
        $controlImagePoint = Test-RequiredPatchPoint -PatchPoints $patchDoc.patch_points -Name "control_image"
        if ($null -ne $controlImagePoint) {
            if ($controlImagePoint.node_type -ne "LoadImage") {
                $slotDefects.Add("control_image_not_loadimage:$($controlImagePoint.node_type)")
            }
            if ($controlImagePoint.input -ne "image") {
                $slotDefects.Add("control_image_input_not_image:$($controlImagePoint.input)")
            }
        }
    }

    $imageInfo = $null
    $sha256 = $null
    $sizeBytes = $null
    if (Test-Path -LiteralPath $controlImagePath -PathType Leaf) {
        $sha256 = (Get-FileHash -LiteralPath $controlImagePath -Algorithm SHA256).Hash.ToLowerInvariant()
        $sizeBytes = (Get-Item -LiteralPath $controlImagePath).Length
        $imageInfo = Get-ImageInfo -Path $controlImagePath
        if ($imageInfo.width -lt 512 -or $imageInfo.height -lt 512) {
            $slotDefects.Add("control_image_dimension_below_512:$($imageInfo.width)x$($imageInfo.height)")
        }
    }

    foreach ($evidencePath in $binding.runtime_or_qa_evidence) {
        $resolvedEvidence = Resolve-ProjectPath -Path $evidencePath
        if (-not (Test-Path -LiteralPath $resolvedEvidence -PathType Leaf)) {
            $slotDefects.Add("missing_runtime_or_qa_evidence:$evidencePath")
        }
    }

    foreach ($slotDefect in $slotDefects) {
        $defects.Add("$($binding.semantic_slot):$slotDefect")
    }

    $bindingResults.Add([ordered]@{
        semantic_slot = $binding.semantic_slot
        slot_family = $binding.slot_family
        lane_id = $binding.lane_id
        module_id = $binding.module_id
        patch_points_path = $binding.patch_points_path
        workflow_path = $binding.workflow_path
        control_image_path = $binding.control_image_path
        control_image_sha256 = $sha256
        control_image_size_bytes = $sizeBytes
        control_image_dimensions = $imageInfo
        required_patch_points_verified = $patchPointFindings
        runtime_or_qa_evidence = $binding.runtime_or_qa_evidence
        result = $(if ($slotDefects.Count -eq 0) { "pass" } else { "fail" })
        defects = @($slotDefects)
    })
}

$result = if ($defects.Count -eq 0) { "pass_local_reference_slot_routing_beyond_face" } else { "fail_local_reference_slot_routing_beyond_face" }
$sourceRequirements = @($request.source_requirements)
$bindingsChecked = @($bindingResults.ToArray())
$defectsChecked = @($defects.ToArray())
$evidence = [ordered]@{
    schema_version = "1.0"
    evidence_id = "W69-LOCAL-REFERENCE-SLOT-ROUTING-BEYOND-FACE-20260707T124000-0500"
    created_at = "2026-07-07T12:40:00-05:00"
    artifact_type = "workflow_prerequisite_matching"
    work_type = $request.work_type
    request_path = $RequestPath
    local_only = $true
    ec2_started = $false
    aws_contacted = $false
    github_api_contacted = $false
    civitai_contacted = $false
    comfyui_contacted = $false
    generation_executed = $false
    minimum_required_non_face_slots = [int]$request.minimum_required_non_face_slots
    non_face_slots_verified = $nonFaceSlots.Count
    source_requirements = $sourceRequirements
    bindings_checked = $bindingsChecked
    result = $result
    defects = $defectsChecked
    promotion_boundary = $request.promotion_boundary
}

$evidenceDir = Split-Path -Path $resolvedEvidencePath -Parent
if (-not (Test-Path -LiteralPath $evidenceDir -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
}

$json = $evidence | ConvertTo-Json -Depth 20
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($resolvedEvidencePath, $json, $utf8NoBom)
if ($defects.Count -gt 0) {
    Write-Error "Reference slot routing validation failed: $($defects -join '; ')"
}

Write-Output "Reference slot routing validation passed: $($bindingResults.Count) bindings checked, $($nonFaceSlots.Count) non-face slots."
