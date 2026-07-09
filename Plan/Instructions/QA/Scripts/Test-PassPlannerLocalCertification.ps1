param(
    [Parameter(Mandatory = $true)]
    [string]$RequestPath,

    [Parameter(Mandatory = $true)]
    [string]$PlanPath,

    [Parameter(Mandatory = $true)]
    [string]$ValidationPath,

    [Parameter(Mandatory = $true)]
    [string]$EvidencePath,

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
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        throw "json_has_utf8_bom:$Path"
    }
    return ([System.Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json)
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

function Add-Defect {
    param(
        [System.Collections.Generic.List[string]]$Defects,
        [string]$Text
    )
    [void]$Defects.Add($Text)
}

$requestResolved = Resolve-ProjectPath -Path $RequestPath
$planResolved = Resolve-ProjectPath -Path $PlanPath
$validationResolved = Resolve-ProjectPath -Path $ValidationPath
$evidenceResolved = Resolve-ProjectPath -Path $EvidencePath

$defects = New-Object System.Collections.Generic.List[string]
$finalBlockers = New-Object System.Collections.Generic.List[string]

foreach ($pair in @(
        @{ label = "request"; path = $requestResolved },
        @{ label = "plan"; path = $planResolved },
        @{ label = "validation"; path = $validationResolved }
    )) {
    if ($null -eq $pair.path -or -not (Test-Path -LiteralPath $pair.path -PathType Leaf)) {
        Add-Defect -Defects $defects -Text "missing_$($pair.label)_file"
    }
}

$request = Read-JsonFile -Path $requestResolved
$plan = Read-JsonFile -Path $planResolved
$validation = Read-JsonFile -Path $validationResolved

if ($request.request_id -ne "w69_local_canny_inpaint_readiness") {
    Add-Defect -Defects $defects -Text "unexpected_request_id:$($request.request_id)"
}
if ($request.execution_mode -ne "dry_run_plan_only" -or $request.dry_run_only -ne $true) {
    Add-Defect -Defects $defects -Text "request_not_dry_run_only"
}
if ($plan.execution_mode -ne "dry_run_plan_only" -or $plan.dry_run_first -ne $true) {
    Add-Defect -Defects $defects -Text "plan_not_dry_run_first"
}
if ($validation.status -ne "PASS") {
    Add-Defect -Defects $defects -Text "validation_not_pass:$($validation.status)"
}
if (@(Convert-ToArray -Value $validation.errors).Count -ne 0) {
    Add-Defect -Defects $defects -Text "validation_errors_present"
}
if (@(Convert-ToArray -Value $validation.warnings).Count -ne 0) {
    Add-Defect -Defects $defects -Text "validation_warnings_present"
}
if ([int]$validation.checked_evidence_path_count -lt 21) {
    Add-Defect -Defects $defects -Text "checked_evidence_path_count_too_low:$($validation.checked_evidence_path_count)"
}

$expectedPassIds = @(
    "p00_preflight",
    "p01_base",
    "p03_pose_control",
    "p04_mask_factory",
    "p05_regional_detail",
    "p06_upscale_polish",
    "p99_promotion"
)
$actualPassIds = @(Convert-ToArray -Value $plan.passes | ForEach-Object { [string]$_.pass_id })
if ($actualPassIds.Count -ne $expectedPassIds.Count) {
    Add-Defect -Defects $defects -Text "unexpected_pass_count:$($actualPassIds.Count)"
}
foreach ($passId in $expectedPassIds) {
    if ($actualPassIds -notcontains $passId) {
        Add-Defect -Defects $defects -Text "missing_pass:$passId"
    }
}
foreach ($requiredPass in @("p00_preflight", "p01_base", "p06_upscale_polish", "p99_promotion")) {
    $pass = @(Convert-ToArray -Value $plan.passes | Where-Object { $_.pass_id -eq $requiredPass }) | Select-Object -First 1
    if ($null -eq $pass -or $pass.required -ne $true) {
        Add-Defect -Defects $defects -Text "required_pass_not_required:$requiredPass"
    }
}

$contract = Get-PropValue -Object $request -Name "control_map_contract"
if ((Get-PropValue -Object $contract -Name "preferred_local_candidate") -ne "canny_w69_rightedge_masked_v3_seed711570105") {
    Add-Defect -Defects $defects -Text "preferred_candidate_not_v3"
}
if ((Get-PropValue -Object $contract -Name "active_control_image") -ne "ComfyUI/input/controlnet_canny_cleaned_eye_safe_v3_rightedge_band_masked.png") {
    Add-Defect -Defects $defects -Text "active_control_image_not_v3"
}
if ((Get-PropValue -Object $contract -Name "target_runtime_required_before_final") -ne $true) {
    Add-Defect -Defects $defects -Text "target_runtime_boundary_not_required"
}

$planText = Get-Content -LiteralPath $planResolved -Raw
$requestText = Get-Content -LiteralPath $requestResolved -Raw
foreach ($staleText in @(
        "controlnet_canny_cleaned_eye_safe_v1",
        "canny_w69_eyeonly_seam_suppression",
        "W69_LOCAL_CANNY_EYEONLY_SEAM_SUPPRESSION",
        "W69_LOCAL_CANNY_EYEONLY_MULTISEED_ROBUSTNESS"
    )) {
    if ($requestText.Contains($staleText) -or $planText.Contains($staleText)) {
        Add-Defect -Defects $defects -Text "stale_canny_reference_present:$staleText"
    }
}

$requiredV3Evidence = @(
    "Plan/Instructions/QA/Evidence/Workflow_Runtime/W69_LOCAL_CANNY_RIGHTEDGE_MASKED_V3_SEED711570105_EXECUTE_20260707T132300-0500.json",
    "runtime_artifacts/run_packages/canny_w69_rightedge_masked_v3_seed711570105/RUN_PACKAGE_MANIFEST.json",
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_CANNY_RIGHTEDGE_MASKED_V3_VISUAL_QA_20260707T133500-0500.json",
    "Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W69_LOCAL_CANNY_V3_CONTROL_INPUT_STATIC_RECHECK_20260707T134500-0500.json",
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/images/codex_sdxl_realvisxl_controlnet_canny_control_map_diagnostic_00010_.png",
    "Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W69_LOCAL_REFERENCE_SLOT_ROUTING_BEYOND_FACE_V3_CANNY_20260707T134600-0500.json",
    "Plan/Instructions/QA/Evidence/Done_Certifications/W69_LOCAL_CONTROLNET_LANE_LOCAL_SUPPORT_CERTIFICATION_V3_CANNY_20260707T134800-0500.json"
)
$checkedPaths = @(Convert-ToArray -Value $validation.checked_evidence_paths)
foreach ($relativePath in $requiredV3Evidence) {
    $resolved = Resolve-ProjectPath -Path $relativePath
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        Add-Defect -Defects $defects -Text "missing_required_v3_evidence:$relativePath"
    }
    if ($checkedPaths -notcontains $resolved) {
        Add-Defect -Defects $defects -Text "validation_did_not_check_required_v3_evidence:$relativePath"
    }
}

if ($defects.Count -eq 0) {
    [void]$finalBlockers.Add("target_runtime_proof_missing_for_final_promotion")
}

$result = if ($defects.Count -eq 0) {
    "pass_local_pass_planner_readiness_final_blocked_target_runtime"
}
else {
    "fail_local_pass_planner_readiness"
}

$evidence = [ordered]@{
    schema_version = "1.0"
    evidence_id = "W69-LOCAL-PASS-PLANNER-CANNY-INPAINT-READINESS-CERTIFICATION-20260707T141500-0500"
    timestamp = "2026-07-07T14:15:00-05:00"
    wave = 69
    task = "Local Pass Planner readiness certification for Canny v3 plus inpaint readiness"
    request_id = $request.request_id
    run_id = $plan.run_id
    result = $result
    final_certification_result = "blocked_final_promotion_missing_target_runtime"
    local_only = $true
    ec2_started = $false
    aws_contacted = $false
    github_api_contacted = $false
    civitai_contacted = $false
    dry_run_first = $plan.dry_run_first
    execution_mode = $plan.execution_mode
    pass_count = @(Convert-ToArray -Value $plan.passes).Count
    pass_ids = $actualPassIds
    checked_evidence_path_count = [int]$validation.checked_evidence_path_count
    validation_status = $validation.status
    defects = @($defects)
    final_blockers = @($finalBlockers)
    v3_canny_candidate = "canny_w69_rightedge_masked_v3_seed711570105"
    active_control_image = "ComfyUI/input/controlnet_canny_cleaned_eye_safe_v3_rightedge_band_masked.png"
    required_v3_evidence = $requiredV3Evidence
    certification_boundary = "Local dry-run-first Pass Planner readiness only. This does not execute ComfyUI, start EC2, promote final output, or satisfy target-runtime proof."
    source_files = [ordered]@{
        request = $RequestPath
        compiled_plan = $PlanPath
        validation = $ValidationPath
    }
}

$json = $evidence | ConvertTo-Json -Depth 12
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($evidenceResolved)) | Out-Null
[System.IO.File]::WriteAllText($evidenceResolved, $json + [Environment]::NewLine, $utf8NoBom)

$evidence | ConvertTo-Json -Depth 12
if ($defects.Count -gt 0) {
    exit 2
}
exit 0
