<#
.SYNOPSIS
Creates a lane-scoped final-review packet for the Canny base-generation lane.

.DESCRIPTION
Validates existing Canny lane target-runtime proof, pullback/hash evidence,
technical/visual QA, and local robustness evidence. The packet closes only the
Canny final-review work order when the evidence is sufficient. It does not run
ComfyUI, start EC2, contact external services, execute generation, promote masks,
consume candidate masks as truth, rerun Wave70 hard gates, or activate Wave71+.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_realvisxl_controlnet_canny_lane",
  [string]$WorkOrderFile = "",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return $null }
  $text = [string]$Path
  if ([string]::IsNullOrWhiteSpace($text)) { return $null }
  if ([System.IO.Path]::IsPathRooted($text)) { return [System.IO.Path]::GetFullPath($text) }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $text))
}

function ConvertTo-ProjectRelativePath {
  param([AllowNull()][object]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if ($null -eq $resolved) { return $null }
  $rootFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $targetFull = [System.IO.Path]::GetFullPath($resolved)
  if ($targetFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $targetFull.Substring($rootFull.Length).Replace("\", "/")
  }
  return $targetFull
}

function Read-JsonFile {
  param([Parameter(Mandatory = $true)][string]$Path)
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
}

function Find-LatestFile {
  param([string]$Directory, [string]$Filter)
  if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $item = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTimeUtc, Name -Descending |
    Select-Object -First 1
  if ($null -eq $item) { return $null }
  return $item.FullName
}

function Add-Text {
  param([System.Collections.Generic.List[string]]$List, [string]$Text)
  [void]$List.Add($Text)
}

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$doneCertificationsDir = Join-Path $qaRoot "Done_Certifications"
if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
  $WorkOrderFile = Find-LatestFile -Directory $doneCertificationsDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
    $WorkOrderFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  }
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_CANNY_LANE_FINAL_REVIEW_PACKET_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

$staticProofPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W68_EC2_STATIC_PROOF_CANNY_V4_RUNTIME_PASS_20260707T014700-0500.json"
$workflowSmokePath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Runtime/W68_EC2_WORKFLOW_SMOKE_CANNY_V4_AFTER_INPUT_INSTALL_20260707T020800-0500.json"
$pullbackPath = Resolve-ProjectPath -Path "Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260707T021155-0500/PULLBACK_RECORD.json"
$technicalQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W68_CANNY_V4_EC2_IMAGE_QA_TECHNICAL_20260707T021700-0500.json"
$visualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W68_CANNY_V4_EC2_IMAGE_QA_VISUAL_20260707T022300-0500.json"
$localRobustnessPath = Resolve-ProjectPath -Path "Plan/Tracker/Evidence/W69_LOCAL_CANNY_EYEONLY_MULTISEED_ROBUSTNESS_20260707T092500-0500.json"
$localRobustnessVisualPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_CANNY_EYEONLY_MULTISEED_ROBUSTNESS_VISUAL_QA_20260707T092500-0500.json"
$microControlVisualPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W72_LOCAL_CANNY_MICRO_CONTROL_MATRIX_VISUAL_QA_20260707T201500-0500.json"

$defects = New-Object System.Collections.Generic.List[string]
foreach ($required in @(
  @{ label = "work_order"; path = $workOrderResolved },
  @{ label = "static_proof"; path = $staticProofPath },
  @{ label = "workflow_smoke"; path = $workflowSmokePath },
  @{ label = "pullback"; path = $pullbackPath },
  @{ label = "technical_qa"; path = $technicalQaPath },
  @{ label = "visual_qa"; path = $visualQaPath },
  @{ label = "local_robustness"; path = $localRobustnessPath },
  @{ label = "local_robustness_visual_qa"; path = $localRobustnessVisualPath },
  @{ label = "micro_control_visual_qa"; path = $microControlVisualPath }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    Add-Text -List $defects -Text "missing_required_input:$($required.label)"
  }
}

$workOrderRecord = Read-JsonFile -Path $workOrderResolved
$staticProof = Read-JsonFile -Path $staticProofPath
$workflowSmoke = Read-JsonFile -Path $workflowSmokePath
$pullback = Read-JsonFile -Path $pullbackPath
$technicalQa = Read-JsonFile -Path $technicalQaPath
$visualQa = Read-JsonFile -Path $visualQaPath
$localRobustness = Read-JsonFile -Path $localRobustnessPath
$localRobustnessVisual = Read-JsonFile -Path $localRobustnessVisualPath
$microControlVisual = Read-JsonFile -Path $microControlVisualPath

$workOrder = @(Convert-ToArray -Value $workOrderRecord.work_orders | Where-Object { [string]$_.lane_id -eq $LaneId -and [string]$_.work_order_type -eq "final_certification_review_required" } | Select-Object -First 1)
if ($workOrder.Count -eq 0) {
  Add-Text -List $defects -Text "final_certification_review_work_order_missing:$LaneId"
}

$imagePath = Resolve-ProjectPath -Path $visualQa.image_path
$imageHash = $null
if ($null -eq $imagePath -or -not (Test-Path -LiteralPath $imagePath -PathType Leaf)) {
  Add-Text -List $defects -Text "review_image_missing"
}
else {
  $imageHash = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
}
$pullbackImage = @(Convert-ToArray -Value $pullback.files | Where-Object { [string]$_.artifact_type -eq "image" } | Select-Object -First 1)
$pullbackImageHash = if ($pullbackImage.Count -gt 0) { [string]$pullbackImage[0].sha256 } else { "" }

$technicalImageHash = [string]$technicalQa.image.sha256
$visualImageHash = [string]$visualQa.image_sha256
$localRobustnessBlockingDefects = @(Convert-ToArray -Value $localRobustnessVisual.blocking_defects)
$microControlBlockers = @(Convert-ToArray -Value $microControlVisual.final_certification_boundary.remaining_blockers)

$checks = @(
  (New-Check -Name "final_review_work_order_present" -Passed ($workOrder.Count -gt 0 -and [string]$workOrder[0].work_order_id -eq "WO-W66-SDXL_REALVISXL_CONTROLNET_CANNY_LANE-FINAL-CERTIFICATION-REVIEW") -Observed $(if ($workOrder.Count -gt 0) { [ordered]@{ work_order_id = [string]$workOrder[0].work_order_id; status = [string]$workOrder[0].status } } else { "missing" }) -Expected "Canny final-certification-review work order is present"),
  (New-Check -Name "static_proof_passed_and_stopped" -Passed ([string]$staticProof.result -eq "ec2_static_proof_recorded" -and [string]$staticProof.lane_id -eq $LaneId -and [string]$staticProof.final_state -eq "stopped" -and [bool]$staticProof.generation_executed -eq $false -and [bool]$staticProof.static_proof_summary.pass -and [bool]$staticProof.static_proof_summary.object_info_pass) -Observed ([ordered]@{ result = $staticProof.result; lane_id = $staticProof.lane_id; final_state = $staticProof.final_state; generation_executed = $staticProof.generation_executed; static_pass = $staticProof.static_proof_summary.pass; object_info_pass = $staticProof.static_proof_summary.object_info_pass }) -Expected "W68 Canny static proof pass, EC2 stopped, no generation"),
  (New-Check -Name "workflow_smoke_generated_and_stopped" -Passed ([string]$workflowSmoke.result -eq "workflow_smoke_generation_complete" -and [string]$workflowSmoke.lane_id -eq $LaneId -and [string]$workflowSmoke.final_state -eq "stopped" -and [bool]$workflowSmoke.generation_executed -eq $true -and [string]$workflowSmoke.local_pullback.status -eq "pullback_record_created") -Observed ([ordered]@{ result = $workflowSmoke.result; lane_id = $workflowSmoke.lane_id; final_state = $workflowSmoke.final_state; generation_executed = $workflowSmoke.generation_executed; local_pullback_status = $workflowSmoke.local_pullback.status }) -Expected "W68 bounded workflow smoke completed one generation, stopped, and recorded pullback"),
  (New-Check -Name "pullback_hashes_verified" -Passed ([string]$pullback.status -eq "pullback_hashes_verified" -and [bool]$pullback.hashes_verified -eq $true -and @($pullback.errors).Count -eq 0) -Observed ([ordered]@{ status = $pullback.status; hashes_verified = $pullback.hashes_verified; errors = @($pullback.errors).Count }) -Expected "pullback hashes verified with no errors"),
  (New-Check -Name "image_hash_matches_pullback_and_qa" -Passed (-not [string]::IsNullOrWhiteSpace($imageHash) -and $imageHash -eq $pullbackImageHash.ToLowerInvariant() -and $imageHash -eq $technicalImageHash.ToLowerInvariant() -and $imageHash -eq $visualImageHash.ToLowerInvariant()) -Observed ([ordered]@{ image_hash = $imageHash; pullback_hash = $pullbackImageHash; technical_qa_hash = $technicalImageHash; visual_qa_hash = $visualImageHash }) -Expected "review image hash matches pullback, technical QA, and visual QA"),
  (New-Check -Name "technical_qa_integrity_passed" -Passed ([string]$technicalQa.scores.technical_integrity -eq "pass" -and [string]$technicalQa.scores.resolution_check -eq "pass" -and @($technicalQa.defects).Count -eq 0 -and [bool]$technicalQa.image.exists) -Observed ([ordered]@{ technical_integrity = $technicalQa.scores.technical_integrity; resolution_check = $technicalQa.scores.resolution_check; defects = @($technicalQa.defects).Count; image_exists = $technicalQa.image.exists }) -Expected "technical integrity and resolution pass with no defects"),
  (New-Check -Name "target_runtime_visual_qa_passed_with_notes" -Passed ([string]$visualQa.decision -eq "pass_with_notes_for_runtime_smoke" -and [string]$visualQa.lane_id -eq $LaneId -and @($visualQa.defects).Count -eq 0 -and -not [bool]$visualQa.final_certification_allowed) -Observed ([ordered]@{ decision = $visualQa.decision; lane_id = $visualQa.lane_id; defects = @($visualQa.defects).Count; final_certification_allowed = $visualQa.final_certification_allowed }) -Expected "target-runtime visual QA pass_with_notes with no defects and no full certification claim"),
  (New-Check -Name "local_multiseed_robustness_passed_with_notes" -Passed ([string]$localRobustness.result -eq "pass_with_notes_local_canny_eyeonly_multiseed_robustness" -and [string]$localRobustness.lane_id -eq $LaneId -and [string]$localRobustnessVisual.qa_result -eq "pass_with_notes_local_canny_eyeonly_multiseed_robustness" -and $localRobustnessBlockingDefects.Count -eq 0 -and -not [bool]$localRobustnessVisual.certification_allowed) -Observed ([ordered]@{ result = $localRobustness.result; visual_qa_result = $localRobustnessVisual.qa_result; blocking_defects = $localRobustnessBlockingDefects.Count; certification_allowed = $localRobustnessVisual.certification_allowed }) -Expected "local three-sample robustness passes with notes and no blocking defects"),
  (New-Check -Name "local_micro_control_followup_recorded_not_promoted" -Passed ([string]$microControlVisual.result -eq "pass_with_notes_local_canny_micro_control_matrix_followup_neutral_not_promoted" -and [string]$microControlVisual.lane_id -eq $LaneId -and [bool]$microControlVisual.local_only -and -not [bool]$microControlVisual.final_certification_boundary.final_mod17_certification_allowed -and -not [bool]$microControlVisual.qa_decision.promote_over_retained_candidate) -Observed ([ordered]@{ result = $microControlVisual.result; lane_id = $microControlVisual.lane_id; local_only = $microControlVisual.local_only; final_mod17_certification_allowed = $microControlVisual.final_certification_boundary.final_mod17_certification_allowed; promote_over_retained_candidate = $microControlVisual.qa_decision.promote_over_retained_candidate; remaining_blockers = $microControlBlockers }) -Expected "local micro-control follow-up recorded as neutral/not promoted with final certification still disallowed")
)

foreach ($check in $checks) {
  if ([string]$check.result -ne "pass") { Add-Text -List $defects -Text "check_failed:$($check.name)" }
}

$knownIssues = @(
  "This packet closes only the Canny lane final-review work order from existing evidence; it does not certify full-project completion.",
  "W68 target-runtime proof is a single bounded smoke sample. W69/W72 add local robustness and micro-control context but do not replace broad final image-quality certification.",
  "Canny evidence is head-and-shoulders/portrait scoped. Hands, feet, full-body anatomy, contact points, body masks, and gold-mask-dependent geometry remain outside this packet.",
  "W72 retained the prior local candidate and explicitly did not promote the neutral 0.415 follow-up over the retained 0.42/0.60 candidate.",
  "Project-level final certification remains blocked by remaining lane target-runtime/final-review work orders, live gates, and manual gold-mask-dependent gates."
)

$result = if ($defects.Count -eq 0) { "pass_canny_lane_final_review_packet_ready" } else { "fail_canny_lane_final_review_packet" }
$finalDecision = if ($defects.Count -eq 0) { "done_with_non_blocking_notes" } else { "failed" }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "lane_final_review_packet"
  certification_id = "CERT-W66-SDXL-CANNY-LANE-FINAL-REVIEW-$(Get-Date -Format 'yyyyMMddTHHmmss-0500')"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  task_tracker_id = "WO-W66-SDXL_REALVISXL_CONTROLNET_CANNY_LANE-FINAL-CERTIFICATION-REVIEW"
  lane_id = $LaneId
  result = $result
  final_decision = $finalDecision
  local_only = $true
  new_ec2_started = $false
  new_generation_executed = $false
  historical_ec2_started = $true
  historical_generation_executed = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  closes_work_order = $true
  artifact_scope = "Lane-scoped final review packet for the sdxl_realvisxl_controlnet_canny_lane target-runtime smoke proof plus local Canny robustness evidence."
  implementation_summary = "Reviewed existing W68 Canny static proof, bounded target-runtime smoke, pullback/hash evidence, technical QA, visual QA, W69 local multiseed robustness, and W72 local micro-control follow-up without rerunning live runtime."
  tests_performed = @($checks)
  qa_summary = [ordered]@{
    target_runtime_visual_decision = [string]$visualQa.decision
    target_runtime_defects = @(Convert-ToArray -Value $visualQa.defects)
    local_robustness_result = [string]$localRobustness.result
    local_robustness_visual_result = [string]$localRobustnessVisual.qa_result
    local_robustness_blocking_defects = @($localRobustnessBlockingDefects)
    micro_control_result = [string]$microControlVisual.result
    retained_local_candidate = [string]$microControlVisual.qa_decision.retained_local_candidate
    micro_control_remaining_blockers = @($microControlBlockers)
  }
  evidence_paths = [ordered]@{
    work_order = ConvertTo-ProjectRelativePath -Path $workOrderResolved
    static_proof = ConvertTo-ProjectRelativePath -Path $staticProofPath
    workflow_smoke = ConvertTo-ProjectRelativePath -Path $workflowSmokePath
    pullback_record = ConvertTo-ProjectRelativePath -Path $pullbackPath
    technical_qa = ConvertTo-ProjectRelativePath -Path $technicalQaPath
    visual_qa = ConvertTo-ProjectRelativePath -Path $visualQaPath
    local_robustness = ConvertTo-ProjectRelativePath -Path $localRobustnessPath
    local_robustness_visual_qa = ConvertTo-ProjectRelativePath -Path $localRobustnessVisualPath
    local_micro_control_visual_qa = ConvertTo-ProjectRelativePath -Path $microControlVisualPath
    reviewed_image = ConvertTo-ProjectRelativePath -Path $imagePath
  }
  known_issues = $knownIssues
  defects = @($defects)
  certifier = "Codex Desktop autonomous release manager"
  certification_boundary = "Lane-scoped final review only. This does not certify full project completion, final portfolio quality, video/audio/deformation quality, body-mask readiness, Wave70 mask promotion, or Wave71+ activation."
  next_action = "Use this packet as the local review closure for the Canny lane final-review work order; continue remaining non-mask runtime/orchestration work or explicitly gated target-runtime proof only after live gates pass."
}

$outDir = Split-Path -Path $outFileResolved -Parent
$mdDir = Split-Path -Path $markdownResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($mdDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$checkLines = foreach ($check in $checks) {
  "- $($check.name): $($check.result)"
}
$evidenceLines = foreach ($prop in $record.evidence_paths.GetEnumerator()) {
  "- $($prop.Name): $($prop.Value)"
}
$knownIssueLines = foreach ($issue in $knownIssues) {
  "- $issue"
}
$markdown = @"
# Canny Lane Final Review Packet

- certification_id: $($record.certification_id)
- created_at: $($record.created_at)
- lane_id: $LaneId
- result: $result
- final_decision: $finalDecision
- full_project_certification_allowed: false

## Checks

$($checkLines -join "`n")

## Evidence

$($evidenceLines -join "`n")

## Known Issues

$($knownIssueLines -join "`n")

## Boundary

$($record.certification_boundary)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($defects.Count -gt 0) { exit 2 }
exit 0
