param(
    [Parameter(Mandatory = $true)]
    [string]$RequestPath,

    [Parameter(Mandatory = $true)]
    [string]$EvidencePath,

    [Parameter(Mandatory = $true)]
    [string]$CertificationPath,

    [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
    param([Parameter(Mandatory = $true)][AllowNull()][object]$Path)
    if ($null -eq $Path) {
        return $null
    }
    $text = [string]$Path
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($text)) {
        return [System.IO.Path]::GetFullPath($text)
    }
    return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $text))
}

function Read-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
}

function Get-PropValue {
    param(
        [Parameter(Mandatory = $true)][AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )
    if ($null -eq $Object) {
        return $null
    }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) {
        return $null
    }
    return $prop.Value
}

function Convert-ToArray {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [array]) {
        return @($Value)
    }
    return @($Value)
}

function Test-PassingText {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) {
        return $false
    }
    $text = ([string]$Value).ToLowerInvariant()
    return ($text.StartsWith("pass") -or $text.Contains("pass_with_notes"))
}

function Get-EvidenceResultText {
    param([AllowNull()][object]$Doc)
    foreach ($name in @("result", "qa_result", "qa_status", "status")) {
        $value = Get-PropValue -Object $Doc -Name $name
        if ($null -ne $value -and -not [string]::IsNullOrWhiteSpace([string]$value)) {
            return [string]$value
        }
    }
    $qaDecision = Get-PropValue -Object $Doc -Name "qa_decision"
    $qaValue = Get-PropValue -Object $qaDecision -Name "result"
    if ($null -ne $qaValue) {
        return [string]$qaValue
    }
    $decision = Get-PropValue -Object $Doc -Name "decision"
    $decisionValue = Get-PropValue -Object $decision -Name "result"
    if ($null -ne $decisionValue) {
        return [string]$decisionValue
    }
    return $null
}

function Add-PathCheck {
    param(
        [System.Collections.Generic.List[string]]$Defects,
        [Parameter(Mandatory = $true)][string]$Label,
        [AllowNull()][object]$RelativePath
    )
    $resolved = Resolve-ProjectPath -Path $RelativePath
    if ($null -eq $resolved) {
        $Defects.Add("missing_path_value:$Label")
        return $null
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        $Defects.Add("missing_path:${Label}:$RelativePath")
        return $resolved
    }
    return $resolved
}

$requestPathResolved = Resolve-ProjectPath -Path $RequestPath
$evidencePathResolved = Resolve-ProjectPath -Path $EvidencePath
$certificationPathResolved = Resolve-ProjectPath -Path $CertificationPath
$request = Read-JsonFile -Path $requestPathResolved

$defects = New-Object System.Collections.Generic.List[string]
$finalBlockers = New-Object System.Collections.Generic.List[string]
$laneResults = New-Object System.Collections.Generic.List[object]

$referenceEvidencePath = Add-PathCheck -Defects $defects -Label "reference_slot_routing_evidence" -RelativePath $request.reference_slot_routing_evidence
if ($null -ne $referenceEvidencePath -and (Test-Path -LiteralPath $referenceEvidencePath -PathType Leaf)) {
    $referenceDoc = Read-JsonFile -Path $referenceEvidencePath
    $referenceResult = Get-EvidenceResultText -Doc $referenceDoc
    if ($referenceResult -ne "pass_local_reference_slot_routing_beyond_face") {
        $defects.Add("reference_slot_routing_not_pass:$referenceResult")
    }
}

$lanes = @($request.lanes)
if ($lanes.Count -lt [int]$request.minimum_required_lanes) {
    $defects.Add("minimum_required_lanes_not_met:$($lanes.Count)")
}

$seenLanes = @{}
foreach ($lane in $lanes) {
    $laneDefects = New-Object System.Collections.Generic.List[string]
    $laneFinalBlockers = New-Object System.Collections.Generic.List[string]
    $laneId = [string]$lane.lane_id
    $moduleId = [string]$lane.module_id

    if ($seenLanes.ContainsKey($laneId)) {
        $laneDefects.Add("duplicate_lane_id:$laneId")
    }
    else {
        $seenLanes[$laneId] = $true
    }

    $staticPath = Add-PathCheck -Defects $laneDefects -Label "$laneId.static_evidence" -RelativePath $lane.static_evidence
    $trackerPath = Add-PathCheck -Defects $laneDefects -Label "$laneId.tracker_evidence" -RelativePath $lane.tracker_evidence
    $visualPath = Add-PathCheck -Defects $laneDefects -Label "$laneId.visual_qa_evidence" -RelativePath $lane.visual_qa_evidence

    $staticDoc = $null
    $trackerDoc = $null
    $visualDoc = $null
    if ($null -ne $staticPath -and (Test-Path -LiteralPath $staticPath -PathType Leaf)) {
        $staticDoc = Read-JsonFile -Path $staticPath
        $staticResult = Get-EvidenceResultText -Doc $staticDoc
        if (-not (Test-PassingText -Value $staticResult)) {
            $laneDefects.Add("static_evidence_not_passing:$staticResult")
        }
        $staticLaneId = Get-PropValue -Object $staticDoc -Name "lane_id"
        if ($null -ne $staticLaneId -and $staticLaneId -ne $laneId) {
            $laneDefects.Add("static_lane_id_mismatch:$staticLaneId")
        }
        $staticDefects = @(Convert-ToArray -Value (Get-PropValue -Object $staticDoc -Name "defects"))
        if ($staticDefects.Count -gt 0) {
            $laneDefects.Add("static_defects_present:$($staticDefects.Count)")
        }
    }
    if ($null -ne $trackerPath -and (Test-Path -LiteralPath $trackerPath -PathType Leaf)) {
        $trackerDoc = Read-JsonFile -Path $trackerPath
        $trackerResult = Get-EvidenceResultText -Doc $trackerDoc
        if (-not (Test-PassingText -Value $trackerResult)) {
            $laneDefects.Add("tracker_evidence_not_passing:$trackerResult")
        }
        $trackerLaneId = Get-PropValue -Object $trackerDoc -Name "lane_id"
        if ($null -ne $trackerLaneId -and $trackerLaneId -ne $laneId) {
            $laneDefects.Add("tracker_lane_id_mismatch:$trackerLaneId")
        }
        $trackerModuleId = Get-PropValue -Object $trackerDoc -Name "module_id"
        if ($null -eq $trackerModuleId) {
            $trackerModuleId = Get-PropValue -Object $trackerDoc -Name "item_or_module"
        }
        if ($null -ne $trackerModuleId -and $trackerModuleId -ne $moduleId) {
            $laneDefects.Add("tracker_module_id_mismatch:$trackerModuleId")
        }
        if ((Get-PropValue -Object $trackerDoc -Name "local_only") -ne $true) {
            $laneDefects.Add("tracker_not_local_only")
        }
        if ((Get-PropValue -Object $trackerDoc -Name "ec2_started") -eq $true) {
            $laneDefects.Add("tracker_ec2_started_true")
        }
    }
    if ($null -ne $visualPath -and (Test-Path -LiteralPath $visualPath -PathType Leaf)) {
        $visualDoc = Read-JsonFile -Path $visualPath
        $visualResult = Get-EvidenceResultText -Doc $visualDoc
        if (-not (Test-PassingText -Value $visualResult)) {
            $laneDefects.Add("visual_qa_not_passing:$visualResult")
        }
        $visualLaneId = Get-PropValue -Object $visualDoc -Name "lane_id"
        if ($null -ne $visualLaneId -and $visualLaneId -ne $laneId) {
            $laneDefects.Add("visual_lane_id_mismatch:$visualLaneId")
        }
        $blockingDefects = @(Convert-ToArray -Value (Get-PropValue -Object $visualDoc -Name "blocking_defects"))
        if ($blockingDefects.Count -gt 0) {
            $laneDefects.Add("visual_blocking_defects_present:$($blockingDefects.Count)")
        }
    }

    $generatedArtifacts = @()
    if ($null -ne $trackerDoc) {
        $generatedArtifacts += @(Convert-ToArray -Value (Get-PropValue -Object $trackerDoc -Name "generated_images"))
        $generatedArtifacts += @(Convert-ToArray -Value (Get-PropValue -Object $trackerDoc -Name "generated_artifacts"))
    }
    if ($generatedArtifacts.Count -eq 0 -and $null -ne $visualDoc) {
        $singleImage = Get-PropValue -Object $visualDoc -Name "generated_image"
        $singlePath = Get-PropValue -Object $singleImage -Name "path"
        if ($null -ne $singlePath) {
            $generatedArtifacts += $singlePath
        }
        $artifactObjs = @(Convert-ToArray -Value (Get-PropValue -Object $visualDoc -Name "generated_artifacts"))
        foreach ($artifactObj in $artifactObjs) {
            $artifactPath = Get-PropValue -Object $artifactObj -Name "path"
            if ($null -ne $artifactPath) {
                $generatedArtifacts += $artifactPath
            }
        }
    }
    if ($generatedArtifacts.Count -eq 0) {
        $laneDefects.Add("no_generated_artifacts_listed")
    }
    $existingGeneratedArtifacts = @()
    foreach ($artifact in $generatedArtifacts) {
        $artifactPath = Resolve-ProjectPath -Path $artifact
        if ($null -eq $artifactPath -or -not (Test-Path -LiteralPath $artifactPath -PathType Leaf)) {
            $laneDefects.Add("missing_generated_artifact:$artifact")
        }
        else {
            $existingGeneratedArtifacts += [string]$artifact
        }
    }

    $targetRuntimePath = Resolve-ProjectPath -Path $lane.target_runtime_evidence
    if ($null -eq $targetRuntimePath -or -not (Test-Path -LiteralPath $targetRuntimePath -PathType Leaf)) {
        $laneFinalBlockers.Add("target_runtime_evidence_missing")
    }

    $finalCertificationStatus = if ($laneFinalBlockers.Count -eq 0 -and $laneDefects.Count -eq 0) {
        "final_certification_possible"
    }
    elseif ($laneDefects.Count -eq 0) {
        "local_support_pass_final_certification_blocked"
    }
    else {
        "local_support_failed"
    }

    foreach ($laneDefect in $laneDefects) {
        $defects.Add("${laneId}:$laneDefect")
    }
    foreach ($laneBlocker in $laneFinalBlockers) {
        $finalBlockers.Add("${laneId}:$laneBlocker")
    }

    $laneResults.Add([ordered]@{
        lane_id = $laneId
        module_id = $moduleId
        semantic_slot = $lane.semantic_slot
        static_evidence = $lane.static_evidence
        tracker_evidence = $lane.tracker_evidence
        visual_qa_evidence = $lane.visual_qa_evidence
        local_certification_scope = $lane.local_certification_scope
        generated_artifacts_checked = @($existingGeneratedArtifacts)
        local_support_result = $(if ($laneDefects.Count -eq 0) { "pass_local_support" } else { "fail_local_support" })
        final_certification_status = $finalCertificationStatus
        final_blockers = @($laneFinalBlockers.ToArray())
        defects = @($laneDefects.ToArray())
    })
}

$localResult = if ($defects.Count -eq 0) { "pass_local_controlnet_lane_support_certification" } else { "fail_local_controlnet_lane_support_certification" }
$finalResult = if ($finalBlockers.Count -eq 0 -and $defects.Count -eq 0) { "final_certification_possible" } else { "blocked_final_controlnet_lane_certification_missing_target_runtime" }

$evidence = [ordered]@{
    schema_version = "1.0"
    evidence_id = "W69-LOCAL-CONTROLNET-LANE-LOCAL-SUPPORT-CERTIFICATION-20260707T125500-0500"
    created_at = "2026-07-07T12:55:00-05:00"
    artifact_type = "done_certification_gate"
    work_type = $request.work_type
    request_path = $RequestPath
    local_only = $true
    ec2_started = $false
    aws_contacted = $false
    github_api_contacted = $false
    civitai_contacted = $false
    comfyui_contacted = $false
    generation_executed = $false
    lanes_checked = $lanes.Count
    local_support_result = $localResult
    final_certification_result = $finalResult
    lane_results = @($laneResults.ToArray())
    defects = @($defects.ToArray())
    final_blockers = @($finalBlockers.ToArray())
    promotion_boundary = $request.promotion_boundary
}

$evidenceDir = Split-Path -Path $evidencePathResolved -Parent
if (-not (Test-Path -LiteralPath $evidenceDir -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
}
$certDir = Split-Path -Path $certificationPathResolved -Parent
if (-not (Test-Path -LiteralPath $certDir -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $certDir | Out-Null
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($evidencePathResolved, ($evidence | ConvertTo-Json -Depth 20), $utf8NoBom)

$laneLines = foreach ($laneResult in $laneResults) {
    $laneIdText = [string]$laneResult["lane_id"]
    $moduleIdText = [string]$laneResult["module_id"]
    $localSupportText = [string]$laneResult["local_support_result"]
    $finalStatusText = [string]$laneResult["final_certification_status"]
    $blockerText = ([array]$laneResult["final_blockers"]) -join ", "
    "- " + $laneIdText + " / " + $moduleIdText + ": " + $localSupportText + "; final status " + $finalStatusText + "; blockers: " + $blockerText
}
$referenceSlotPath = [string]$request.reference_slot_routing_evidence
$certMarkdown = @"
# ControlNet Lane Local Support Certification

- certification_id: CERT-W69-LOCAL-CONTROLNET-LANE-SUPPORT-20260707T125500-0500
- created_at: 2026-07-07T12:55:00-05:00
- artifact_scope: MOD-17 through MOD-21 SDXL RealVisXL ControlNet lanes
- local_support_result: $localResult
- final_certification_result: $finalResult

## Certification

The local support layer for the five active ControlNet lanes was checked against static workflow evidence, tracker evidence, strict visual QA evidence, generated artifact existence, and the reference-slot routing proof. Local support passes only for the bounded local evidence named in the request.

## Lane Results

$($laneLines -join "`n")

## Evidence

- $RequestPath
- $EvidencePath
- $referenceSlotPath

## Runtime Boundary

$($request.promotion_boundary)

No EC2, AWS, GitHub API, Civitai, S3 publishing, Wave65 refresh, or broad helper evidence loop was used for this certification gate.
"@
[System.IO.File]::WriteAllText($certificationPathResolved, $certMarkdown, $utf8NoBom)

if ($defects.Count -gt 0) {
    Write-Error "ControlNet lane local certification failed: $($defects -join '; ')"
}

Write-Output "ControlNet lane local support certification: $localResult; final certification: $finalResult; lanes checked: $($lanes.Count)."
