<#
.SYNOPSIS
Validates the current Wave 61 QA helper set with local-only checks.

.DESCRIPTION
Parses every QA/Scripts PowerShell helper, parses QA JSON schemas/templates,
checks markdown templates, runs local-only smoke checks into a temp directory,
and writes a machine-readable evidence record. It does not run ComfyUI, start
EC2, inspect real generated artifacts, or claim final visual QA.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
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

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Test-PathIsUnderRoot {
  param(
    [string]$RootPath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($RootPath) -or [string]::IsNullOrWhiteSpace($TargetPath)) { return $false }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $rootFull = [System.IO.Path]::GetFullPath($RootPath).TrimEnd("\", "/")
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  return ($targetFull.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
    $targetFull.StartsWith("$rootFull$separator", [System.StringComparison]::OrdinalIgnoreCase))
}

function ConvertTo-EvidencePath {
  param(
    [string]$BasePath,
    [string]$TargetPath,
    [string]$TempRoot = ""
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }

  if (Test-PathIsUnderRoot -RootPath $TempRoot -TargetPath $TargetPath) {
    $relativeTemp = Get-RelativePathCompat -BasePath $TempRoot -TargetPath $TargetPath
    $relativeTemp = $relativeTemp.Replace("\", "/")
    if ([string]::IsNullOrWhiteSpace($relativeTemp) -or $relativeTemp -eq ".") { return "[VALIDATION_TEMP_ROOT]" }
    return "[VALIDATION_TEMP_ROOT]/$relativeTemp"
  }

  if (![string]::IsNullOrWhiteSpace($env:TEMP) -and (Test-PathIsUnderRoot -RootPath $env:TEMP -TargetPath $TargetPath)) {
    $relativeTemp = Get-RelativePathCompat -BasePath $env:TEMP -TargetPath $TargetPath
    return ("[TEMP]/" + $relativeTemp.Replace("\", "/"))
  }

  return ConvertTo-ProjectRelativePath -BasePath $BasePath -TargetPath $TargetPath
}

function ConvertTo-RedactedEvidenceText {
  param(
    [string]$Text,
    [string]$TempRoot = ""
  )

  if ([string]::IsNullOrEmpty($Text)) { return $Text }

  $redacted = $Text
  $replacements = @()
  if (![string]::IsNullOrWhiteSpace($TempRoot)) {
    $tempRootFull = [System.IO.Path]::GetFullPath($TempRoot).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempRootFull; To = "[VALIDATION_TEMP_ROOT]" }
    $replacements += [ordered]@{ From = $tempRootFull.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
    $replacements += [ordered]@{ From = $tempRootFull.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    $tempRootRelative = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $tempRootFull
    if (![string]::IsNullOrWhiteSpace($tempRootRelative)) {
      $replacements += [ordered]@{ From = $tempRootRelative; To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootRelative.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootRelative.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    }
  }
  if (![string]::IsNullOrWhiteSpace($env:TEMP)) {
    $tempFull = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempFull; To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "/"); To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "\\"); To = "[TEMP]" }
    $tempRelative = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $tempFull
    if (![string]::IsNullOrWhiteSpace($tempRelative)) {
      $replacements += [ordered]@{ From = $tempRelative; To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempRelative.Replace("\", "/"); To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempRelative.Replace("\", "\\"); To = "[TEMP]" }
    }
  }

  foreach ($replacement in $replacements) {
    if (![string]::IsNullOrWhiteSpace($replacement.From)) {
      $redacted = $redacted.Replace($replacement.From, $replacement.To)
    }
  }
  return $redacted
}

function Test-PowerShellParser {
  param([Parameter(Mandatory=$true)][string]$Path)

  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) > $null
  return [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    parse_errors = $errors.Count
    errors = @($errors | ForEach-Object { $_.Message })
    result = $(if ($errors.Count -eq 0) { "pass" } else { "fail" })
  }
}

function Test-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
  }
  try {
    $null = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }
  return $entry
}

function Test-MarkdownTemplate {
  param([Parameter(Mandatory=$true)][string]$Path)

  $text = Get-Content -LiteralPath $Path -Raw
  return [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    bytes = (Get-Item -LiteralPath $Path).Length
    result = $(if (![string]::IsNullOrWhiteSpace($text)) { "pass" } else { "fail" })
  }
}

function Test-JsonProperty {
  param(
    [object]$Object,
    [Parameter(Mandatory=$true)][string]$Name
  )

  if ($null -eq $Object) { return $false }
  return ($null -ne $Object.PSObject.Properties[$Name])
}

function Invoke-LocalHelper {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string[]]$Arguments = @(),
    [string]$ExpectedOutputFile = "",
    [string]$ExpectedOutputType = "none",
    [int[]]$AllowedExitCodes = @(0)
  )

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $text = ConvertTo-RedactedEvidenceText -Text $text -TempRoot $script:ValidationTempRoot
  $entry = [ordered]@{
    name = $Name
    script = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ScriptPath
    exit_code = $LASTEXITCODE
    allowed_exit_codes = $AllowedExitCodes
    result = $(if ($AllowedExitCodes -contains $LASTEXITCODE) { "pass" } else { "fail" })
    output_tail = $(if ($text.Length -gt 1000) { $text.Substring($text.Length - 1000) } else { $text })
    expected_output_file = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $ExpectedOutputFile -TempRoot $script:ValidationTempRoot
    expected_output_type = $ExpectedOutputType
    expected_output_file_exists = (![string]::IsNullOrWhiteSpace($ExpectedOutputFile) -and (Test-Path -LiteralPath $ExpectedOutputFile))
    expected_output_valid = $false
    expected_output_error = $null
  }

  if ($entry.expected_output_file_exists) {
    try {
      if ($ExpectedOutputType -eq "json") {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
        $entry.expected_output_valid = $true
      } elseif ($ExpectedOutputType -eq "markdown") {
        $content = Get-Content -LiteralPath $ExpectedOutputFile -Raw
        $entry.expected_output_valid = (![string]::IsNullOrWhiteSpace($content))
      } else {
        $entry.expected_output_valid = $true
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  } elseif ($ExpectedOutputType -ne "none") {
    $entry.result = "fail"
    $entry.expected_output_error = "Expected output file was not created."
  }

  if ($entry.expected_output_valid -and $Name -eq "dirty_git_checkpoint_inventory_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("schema_version", "artifact_type", "created_at", "result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "comfyui_contacted", "s3_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "commit_attempted", "push_attempted", "stage_attempted", "reset_attempted", "checkout_attempted", "head", "origin_main", "local_matches_origin", "clean_worktree", "porcelain_count", "tracked_porcelain_count", "untracked_porcelain_count", "staged_count", "unstaged_count", "blocked_changed_path_count", "top_level_counts", "status_counts", "changed_preview", "checkpoint_boundary", "next_action")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.artifact_type -ne "dirty_git_checkpoint_inventory") {
        throw "$Name artifact_type must be dirty_git_checkpoint_inventory."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.comfyui_contacted -or [bool]$payload.s3_contacted) {
        throw "$Name must be local-only and must not contact external services."
      }
      if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
      }
      if ([bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.stage_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted) {
        throw "$Name must not stage, commit, push, reset, or checkout."
      }
      if ([string]$payload.result -notin @("pass_clean_git_checkpoint_inventory", "blocked_dirty_git_inventory_checkpoint_required", "blocked_dirty_git_inventory_blocked_paths_present")) {
        throw "$Name result is not a known inventory state: $($payload.result)"
      }
      if ([int]$payload.porcelain_count -lt 0 -or [int]$payload.porcelain_count -ne ([int]$payload.tracked_porcelain_count + [int]$payload.untracked_porcelain_count)) {
        throw "$Name porcelain accounting must equal tracked plus untracked counts."
      }
      if ([int]$payload.porcelain_count -gt 0 -and [string]$payload.result -eq "pass_clean_git_checkpoint_inventory") {
        throw "$Name cannot pass clean inventory with dirty porcelain entries."
      }
      if (@($payload.top_level_counts).Count -eq 0 -and [int]$payload.porcelain_count -gt 0) {
        throw "$Name dirty inventory must include top-level counts."
      }
      if ([string]$payload.checkpoint_boundary -notmatch "Inventory only") {
        throw "$Name boundary must explicitly describe inventory-only behavior."
      }
      $inventoryMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $inventoryMarkdown)) {
        throw "$Name did not create the expected Markdown inventory: $inventoryMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "dirty_git_checkpoint_scope_plan_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("schema_version", "artifact_type", "created_at", "result", "failure_category", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "comfyui_contacted", "s3_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "commit_attempted", "push_attempted", "stage_attempted", "reset_attempted", "checkout_attempted", "inventory_evidence", "inventory_matches_current", "porcelain_count", "comparison_porcelain_count", "include_candidate_count", "review_before_checkpoint_count", "defer_or_exclude_candidate_count", "scope_ready_for_checkpoint", "top_level_counts", "disposition_counts", "category_scope", "checkpoint_boundary", "next_action")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.artifact_type -ne "dirty_git_checkpoint_scope_plan") {
        throw "$Name artifact_type must be dirty_git_checkpoint_scope_plan."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.comfyui_contacted -or [bool]$payload.s3_contacted) {
        throw "$Name must be local-only and must not contact external services."
      }
      if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
      }
      if ([bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.stage_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted) {
        throw "$Name must not stage, commit, push, reset, or checkout."
      }
      if ([string]$payload.result -notin @("blocked_checkpoint_scope_inventory_drift", "blocked_checkpoint_scope_blocked_paths_present", "checkpoint_scope_review_required", "checkpoint_scope_include_candidates_only", "checkpoint_scope_no_dirty_paths")) {
        throw "$Name result is not a known scope-plan state: $($payload.result)"
      }
      if (-not [bool]$payload.inventory_matches_current) {
        throw "$Name inventory must match current git status after self-evidence handling."
      }
      if ([int]$payload.porcelain_count -lt [int]$payload.comparison_porcelain_count) {
        throw "$Name porcelain_count must be >= comparison_porcelain_count."
      }
      if (([int]$payload.include_candidate_count + [int]$payload.review_before_checkpoint_count + [int]$payload.defer_or_exclude_candidate_count) -ne [int]$payload.porcelain_count) {
        throw "$Name disposition counts must sum to porcelain_count."
      }
      if ([int]$payload.review_before_checkpoint_count -gt 0 -and [string]$payload.result -ne "checkpoint_scope_review_required") {
        throw "$Name must require review when review_before_checkpoint_count is nonzero."
      }
      if ([string]$payload.checkpoint_boundary -notmatch "Scope plan only") {
        throw "$Name boundary must explicitly describe scope-plan-only behavior."
      }
      $scopeMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $scopeMarkdown)) {
        throw "$Name did not create the expected Markdown scope plan: $scopeMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "dirty_git_checkpoint_review_resolution_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("schema_version", "artifact_type", "created_at", "result", "failure_category", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "comfyui_contacted", "s3_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "commit_attempted", "push_attempted", "stage_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "scope_plan_evidence", "scope_plan_result", "inventory_matches_current", "source_porcelain_count", "include_candidate_path_count", "preserve_local_do_not_stage_path_count", "do_not_stage_path_count", "checkpoint_workflow_gap_path_count", "unresolved_path_count", "review_groups_resolved", "checkpoint_workflow_gap_present", "ready_for_guarded_checkpoint_dry_run", "resolution_rows", "intended_include_roots", "intended_include_roots_requiring_checkpoint_helper_support", "intended_preserve_local_roots", "intended_do_not_stage_roots", "checkpoint_boundary", "next_action")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.artifact_type -ne "dirty_git_checkpoint_review_resolution") {
        throw "$Name artifact_type must be dirty_git_checkpoint_review_resolution."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.comfyui_contacted -or [bool]$payload.s3_contacted) {
        throw "$Name must be local-only and must not contact external services."
      }
      if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
      }
      if ([bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.stage_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt) {
        throw "$Name must not stage, commit, push, reset, checkout, or rebuild deploy bundles."
      }
      if ([string]$payload.result -notin @("blocked_review_resolution_inventory_drift", "blocked_review_resolution_blocked_paths_present", "checkpoint_review_resolved_workflow_gap_remaining", "checkpoint_review_resolved_ready_for_guarded_dry_run", "checkpoint_review_unresolved")) {
        throw "$Name result is not a known review-resolution state: $($payload.result)"
      }
      if (-not [bool]$payload.inventory_matches_current) {
        throw "$Name inventory must match current status before review resolution can be trusted."
      }
      if (-not [bool]$payload.review_groups_resolved) {
        throw "$Name should resolve known review groups into explicit actions."
      }
      if ([int]$payload.unresolved_path_count -ne 0) {
        throw "$Name unresolved_path_count must be zero for known checkpoint groups."
      }
      if ([int]$payload.checkpoint_workflow_gap_path_count -gt 0 -and -not [bool]$payload.checkpoint_workflow_gap_present) {
        throw "$Name must flag checkpoint workflow gap when gap path count is nonzero."
      }
      if ([bool]$payload.checkpoint_workflow_gap_present -and [bool]$payload.ready_for_guarded_checkpoint_dry_run) {
        throw "$Name cannot be ready for guarded dry-run while checkpoint workflow gap remains."
      }
      if (@($payload.resolution_rows).Count -lt 1) {
        throw "$Name must include resolution rows."
      }
      if ([string]$payload.checkpoint_boundary -notmatch "Review resolution only") {
        throw "$Name boundary must explicitly describe review-resolution-only behavior."
      }
      $resolutionMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $resolutionMarkdown)) {
        throw "$Name did not create the expected Markdown review resolution: $resolutionMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "active_runtime_queue_final_certification_readiness_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "local_only", "ec2_started", "generation_executed", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "lane_count", "blocked_lane_count", "final_blockers", "git_gate_summary", "handoff_summary", "lanes")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_final_certification_target_runtime_or_final_review_missing") {
        throw "$Name result must be blocked_final_certification_target_runtime_or_final_review_missing for the current local-only queue state."
      }
      if (-not [bool]$payload.local_only) {
        throw "$Name must be local_only=true."
      }
      if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed) {
        throw "$Name must not start EC2 or execute generation."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([int]$payload.lane_count -ne 9) {
        throw "$Name lane_count must be 9."
      }
      if ([int]$payload.blocked_lane_count -lt 1 -or @($payload.final_blockers).Count -lt 1) {
        throw "$Name must record final certification blockers."
      }
      if ([bool]$payload.git_gate_summary.passes_for_ec2_execute) {
        throw "$Name should not mark git gate as EC2-ready while the current worktree gate is blocked."
      }
      $readinessMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $readinessMarkdown)) {
        throw "$Name did not create the expected Markdown readiness record: $readinessMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "active_runtime_queue_final_certification_work_order_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "readiness_result", "local_only", "ec2_started", "generation_executed", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "work_order_count", "work_orders", "global_blockers")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "pass_local_only_final_certification_work_order_ready") {
        throw "$Name result must be pass_local_only_final_certification_work_order_ready."
      }
      if ([string]$payload.readiness_result -ne "blocked_final_certification_target_runtime_or_final_review_missing") {
        throw "$Name must consume the current blocked final-certification readiness record."
      }
      if (-not [bool]$payload.local_only) {
        throw "$Name must be local_only=true."
      }
      if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed) {
        throw "$Name must not start EC2 or execute generation."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([int]$payload.work_order_count -lt 1 -or @($payload.work_orders).Count -lt 1) {
        throw "$Name must produce at least one work order from the blocked readiness state."
      }
      if (@($payload.global_blockers | Where-Object { [string]$_ -eq "git_checkpoint_gate_not_clean_for_ec2_execute" }).Count -eq 0) {
        throw "$Name must preserve the dirty Git checkpoint global blocker."
      }
      $targetRuntimeOrders = @($payload.work_orders | Where-Object { [string]$_.work_order_type -eq "target_runtime_proof_required" })
      if ($targetRuntimeOrders.Count -lt 1) {
        throw "$Name must include target_runtime_proof_required work orders for blocked lanes."
      }
      $workOrderMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $workOrderMarkdown)) {
        throw "$Name did not create the expected Markdown work-order record: $workOrderMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and @("low_risk_lane_final_review_packet_smoke", "canny_lane_final_review_packet_smoke") -contains $Name) {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "historical_ec2_started", "historical_generation_executed", "full_project_certification_allowed", "tests_performed", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      $expectedResult = if ($Name -eq "canny_lane_final_review_packet_smoke") { "pass_canny_lane_final_review_packet_ready" } else { "pass_low_risk_lane_final_review_packet_ready" }
      if ([string]$payload.result -ne $expectedResult) {
        throw "$Name result must be $expectedResult."
      }
      if ([string]$payload.final_decision -ne "done_with_non_blocking_notes") {
        throw "$Name final_decision must be done_with_non_blocking_notes."
      }
      $expectedLaneId = if ($Name -eq "canny_lane_final_review_packet_smoke") { "sdxl_realvisxl_controlnet_canny_lane" } else { "sdxl_low_risk_fallback_lane" }
      if ([string]$payload.lane_id -ne $expectedLaneId) {
        throw "$Name lane_id must be $expectedLaneId."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if (-not [bool]$payload.historical_ec2_started -or -not [bool]$payload.historical_generation_executed) {
        throw "$Name must explicitly distinguish reused historical runtime proof."
      }
      if ([bool]$payload.full_project_certification_allowed) {
        throw "$Name must not allow full project certification."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped") {
        throw "$Name certification boundary must be lane-scoped."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown review packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "base_lane_final_review_blocker_packet_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "historical_ec2_started", "historical_generation_executed", "full_project_certification_allowed", "closes_work_order", "tests_performed", "blocker_summary", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_base_lane_final_review_candidate_scope_mismatch") {
        throw "$Name result must be blocked_base_lane_final_review_candidate_scope_mismatch."
      }
      if ([string]$payload.final_decision -ne "blocked") {
        throw "$Name final_decision must be blocked."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_base_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_base_lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if (-not [bool]$payload.historical_ec2_started -or -not [bool]$payload.historical_generation_executed) {
        throw "$Name must explicitly distinguish reused historical runtime proof."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_order) {
        throw "$Name must not allow full project certification or close the work order."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      if (@($payload.blocker_summary | Where-Object { [string]$_ -eq "mask_routed_refine_or_small_robustness_pair_missing_for_base_contact_scope" }).Count -eq 0) {
        throw "$Name must record the base lane refine/robustness blocker."
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped blocker review") {
        throw "$Name certification boundary must describe a lane-scoped blocker review."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown blocker packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "inpaint_lane_final_review_blocker_packet_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "full_project_certification_allowed", "closes_work_order", "tests_performed", "blocker_summary", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_inpaint_lane_final_review_target_runtime_proof_missing") {
        throw "$Name result must be blocked_inpaint_lane_final_review_target_runtime_proof_missing."
      }
      if ([string]$payload.final_decision -ne "blocked") {
        throw "$Name final_decision must be blocked."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_inpaint_detail_lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_order) {
        throw "$Name must not allow full project certification or close the work order."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      foreach ($blocker in @("inpaint_lane_target_runtime_proof_evidence_missing", "target_runtime_object_info_path_hash_input_proof_missing", "bounded_target_runtime_output_missing")) {
        if (@($payload.blocker_summary | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must record blocker: $blocker"
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped blocker review") {
        throw "$Name certification boundary must describe a lane-scoped blocker review."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown blocker packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "realesrgan_lane_final_review_blocker_packet_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "full_project_certification_allowed", "closes_work_order", "tests_performed", "blocker_summary", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_realesrgan_lane_final_review_target_runtime_proof_missing") {
        throw "$Name result must be blocked_realesrgan_lane_final_review_target_runtime_proof_missing."
      }
      if ([string]$payload.final_decision -ne "blocked") {
        throw "$Name final_decision must be blocked."
      }
      if ([string]$payload.lane_id -ne "sdxl_realesrgan_upscale_polish_lane") {
        throw "$Name lane_id must be sdxl_realesrgan_upscale_polish_lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_order) {
        throw "$Name must not allow full project certification or close the work order."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      foreach ($blocker in @("realesrgan_lane_target_runtime_proof_evidence_missing", "target_runtime_object_info_path_hash_proof_missing", "single_local_upscale_sample_not_broad_robustness_matrix")) {
        if (@($payload.blocker_summary | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must record blocker: $blocker"
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped blocker review") {
        throw "$Name certification boundary must describe a lane-scoped blocker review."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown blocker packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "depth_lane_final_review_blocker_packet_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "full_project_certification_allowed", "closes_work_order", "tests_performed", "blocker_summary", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_depth_lane_final_review_target_runtime_proof_missing") {
        throw "$Name result must be blocked_depth_lane_final_review_target_runtime_proof_missing."
      }
      if ([string]$payload.final_decision -ne "blocked") {
        throw "$Name final_decision must be blocked."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_controlnet_depth_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_controlnet_depth_lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_order) {
        throw "$Name must not allow full project certification or close the work order."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      foreach ($blocker in @("depth_lane_target_runtime_proof_evidence_missing", "target_runtime_object_info_path_hash_input_proof_missing", "local_three_sample_robustness_not_final_depth_certification")) {
        if (@($payload.blocker_summary | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must record blocker: $blocker"
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped blocker review") {
        throw "$Name certification boundary must describe a lane-scoped blocker review."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown blocker packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "lineart_lane_final_review_blocker_packet_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "full_project_certification_allowed", "closes_work_order", "tests_performed", "blocker_summary", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_lineart_lane_final_review_target_runtime_proof_missing") {
        throw "$Name result must be blocked_lineart_lane_final_review_target_runtime_proof_missing."
      }
      if ([string]$payload.final_decision -ne "blocked") {
        throw "$Name final_decision must be blocked."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_controlnet_lineart_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_controlnet_lineart_lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_order) {
        throw "$Name must not allow full project certification or close the work order."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      foreach ($blocker in @("lineart_lane_target_runtime_proof_evidence_missing", "target_runtime_object_info_path_hash_input_proof_missing", "local_three_sample_robustness_not_final_lineart_certification")) {
        if (@($payload.blocker_summary | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must record blocker: $blocker"
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped blocker review") {
        throw "$Name certification boundary must describe a lane-scoped blocker review."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown blocker packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "openpose_lane_final_review_blocker_packet_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "full_project_certification_allowed", "closes_work_order", "tests_performed", "blocker_summary", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_openpose_lane_final_review_target_runtime_proof_missing") {
        throw "$Name result must be blocked_openpose_lane_final_review_target_runtime_proof_missing."
      }
      if ([string]$payload.final_decision -ne "blocked") {
        throw "$Name final_decision must be blocked."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_controlnet_openpose_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_controlnet_openpose_lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_order) {
        throw "$Name must not allow full project certification or close the work order."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      foreach ($blocker in @("openpose_lane_target_runtime_proof_evidence_missing", "target_runtime_object_info_path_hash_input_proof_missing", "local_three_sample_tablehands_robustness_not_final_openpose_certification", "strict_final_hand_anatomy_qa_missing")) {
        if (@($payload.blocker_summary | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must record blocker: $blocker"
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped blocker review") {
        throw "$Name certification boundary must describe a lane-scoped blocker review."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown blocker packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "normal_lane_final_review_blocker_packet_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "final_decision", "lane_id", "local_only", "new_ec2_started", "new_generation_executed", "full_project_certification_allowed", "closes_work_order", "tests_performed", "blocker_summary", "evidence_paths", "known_issues", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_normal_lane_final_review_target_runtime_proof_missing") {
        throw "$Name result must be blocked_normal_lane_final_review_target_runtime_proof_missing."
      }
      if ([string]$payload.final_decision -ne "blocked") {
        throw "$Name final_decision must be blocked."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_controlnet_normal_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_controlnet_normal_lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.new_ec2_started -or [bool]$payload.new_generation_executed) {
        throw "$Name must be local-only and must not start new EC2 or generation."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_order) {
        throw "$Name must not allow full project certification or close the work order."
      }
      if (@($payload.tests_performed | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name contains failed review checks."
      }
      foreach ($blocker in @("normal_lane_target_runtime_proof_evidence_missing", "target_runtime_object_info_path_hash_input_proof_missing", "local_three_sample_robustness_not_final_normal_certification")) {
        if (@($payload.blocker_summary | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must record blocker: $blocker"
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Lane-scoped blocker review") {
        throw "$Name certification boundary must describe a lane-scoped blocker review."
      }
      $packetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $packetMarkdown)) {
        throw "$Name did not create the expected Markdown blocker packet: $packetMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "active_runtime_queue_final_certification_closure_rollup_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "local_only", "ec2_started", "generation_executed", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "source_work_order_count", "closed_work_order_count", "open_work_order_count", "remaining_local_ready_count", "remaining_target_runtime_count", "remaining_final_review_count", "closed_work_order_ids", "rollup_entries", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "pass_local_only_final_certification_closure_rollup") {
        throw "$Name result must be pass_local_only_final_certification_closure_rollup."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.ec2_started -or [bool]$payload.generation_executed) {
        throw "$Name must be local-only and must not start EC2 or generation."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed) {
        throw "$Name must not allow full project certification."
      }
      if ([int]$payload.source_work_order_count -lt 1 -or [int]$payload.closed_work_order_count -lt 1 -or [int]$payload.open_work_order_count -lt 1) {
        throw "$Name must record closed and remaining work orders."
      }
      if ([int]$payload.remaining_local_ready_count -ne 0) {
        throw "$Name should not leave the low-risk local-ready review packet open."
      }
      if ([int]$payload.remaining_target_runtime_count -lt 1 -or [int]$payload.remaining_final_review_count -lt 1) {
        throw "$Name must preserve remaining target-runtime and final-review blockers."
      }
      if (@($payload.closed_work_order_ids | Where-Object { [string]$_ -eq "WO-W66-SDXL_LOW_RISK_FALLBACK_LANE-FINAL-REVIEW-PACKET" }).Count -eq 0) {
        throw "$Name must close the low-risk lane final-review packet work order."
      }
      if ([string]$payload.certification_boundary -notmatch "Local closure-state rollup") {
        throw "$Name certification boundary must describe a local closure-state rollup."
      }
      $closureMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $closureMarkdown)) {
        throw "$Name did not create the expected Markdown closure rollup: $closureMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "active_runtime_queue_final_review_evidence_coverage_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "local_only", "ec2_started", "generation_executed", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "closes_work_orders", "final_review_work_order_count", "closure_packet_count", "blocker_packet_count", "missing_review_evidence_count", "coverage_entries", "missing_review_evidence", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "pass_local_only_final_review_evidence_coverage_complete") {
        throw "$Name result must be pass_local_only_final_review_evidence_coverage_complete."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must be local-only and must not start EC2, generate, or write a runtime marker."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.closes_work_orders) {
        throw "$Name must not allow full project certification or close work orders."
      }
      if ([int]$payload.final_review_work_order_count -ne 9 -or [int]$payload.closure_packet_count -ne 2 -or [int]$payload.blocker_packet_count -ne 7) {
        throw "$Name must account for 9 final-review work orders as 2 closures plus 7 blockers."
      }
      if ([int]$payload.missing_review_evidence_count -ne 0 -or @($payload.missing_review_evidence).Count -ne 0) {
        throw "$Name must not leave any final-review work order without closure or blocker evidence."
      }
      foreach ($coverage in @("closed_with_review_packet", "open_with_blocker_packet")) {
        if (@($payload.coverage_entries | Where-Object { [string]$_.coverage_status -eq $coverage }).Count -eq 0) {
          throw "$Name must include coverage status: $coverage"
        }
      }
      foreach ($workOrderId in @(
        "WO-W66-SDXL_REALVISXL_BASE_LANE-FINAL-CERTIFICATION-REVIEW",
        "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-FINAL-CERTIFICATION-REVIEW",
        "WO-W66-SDXL_REALESRGAN_UPSCALE_POLISH_LANE-FINAL-CERTIFICATION-REVIEW",
        "WO-W66-SDXL_REALVISXL_CONTROLNET_DEPTH_LANE-FINAL-CERTIFICATION-REVIEW",
        "WO-W66-SDXL_REALVISXL_CONTROLNET_LINEART_LANE-FINAL-CERTIFICATION-REVIEW",
        "WO-W66-SDXL_REALVISXL_CONTROLNET_OPENPOSE_LANE-FINAL-CERTIFICATION-REVIEW",
        "WO-W66-SDXL_REALVISXL_CONTROLNET_NORMAL_LANE-FINAL-CERTIFICATION-REVIEW"
      )) {
        $covered = @($payload.coverage_entries | Where-Object { [string]$_.work_order_id -eq $workOrderId -and [string]$_.coverage_status -eq "open_with_blocker_packet" })
        if ($covered.Count -ne 1) {
          throw "$Name must classify $workOrderId as open_with_blocker_packet."
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Local final-review evidence coverage") {
        throw "$Name certification boundary must describe local final-review evidence coverage."
      }
      $coverageMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $coverageMarkdown)) {
        throw "$Name did not create the expected Markdown evidence coverage matrix: $coverageMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "active_runtime_queue_target_runtime_execution_plan_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "local_only", "execute_allowed_now", "explicit_user_selection_required", "ec2_started", "generation_executed", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "selected_work_order_id", "selected_lane_id", "selected_lane_queue_order", "selection_policy", "target_candidate_count", "target_candidates", "blocker_summary", "git_checkpoint_summary", "s3_transfer_summary", "command_sequence", "command_step_count", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_target_runtime_execution_plan_waiting_for_explicit_selection_and_clean_git") {
        throw "$Name result must be blocked_target_runtime_execution_plan_waiting_for_explicit_selection_and_clean_git."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.execute_allowed_now -or -not [bool]$payload.explicit_user_selection_required) {
        throw "$Name must be local-only, blocked from execution now, and require explicit user selection."
      }
      if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must not start EC2, execute generation, or write an active runtime marker."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed) {
        throw "$Name must not allow full project certification."
      }
      if ([string]$payload.selected_lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
        throw "$Name must select the first runtime-queue-order lane that is missing target-runtime proof."
      }
      if ([int]$payload.selected_lane_queue_order -ne 4) {
        throw "$Name selected lane queue order must be 4."
      }
      if (@($payload.target_candidates).Count -lt 8 -or [int]$payload.target_candidate_count -lt 8) {
        throw "$Name must preserve the remaining target-runtime candidate set."
      }
      if (@($payload.blocker_summary | Where-Object { [string]$_ -eq "explicit_user_target_runtime_selection_required" }).Count -eq 0) {
        throw "$Name must require explicit user target-runtime selection."
      }
      if (@($payload.blocker_summary | Where-Object { [string]$_ -eq "git_checkpoint_gate_not_clean_for_ec2_execute" }).Count -eq 0) {
        throw "$Name must preserve the dirty Git checkpoint blocker."
      }
      if ([bool]$payload.git_checkpoint_summary.passes_for_ec2_execute) {
        throw "$Name must not mark the Git checkpoint gate as passing for EC2."
      }
      if ([int]$payload.command_step_count -lt 10 -or @($payload.command_sequence).Count -lt 10) {
        throw "$Name must emit a complete gated command sequence."
      }
      if (@($payload.command_sequence | Where-Object { [string]$_.name -eq "ec2_static_proof_execute" -and [bool]$_.execute_allowed_now }).Count -ne 0) {
        throw "$Name must not allow EC2 execute steps now."
      }
      if ([string]$payload.certification_boundary -notmatch "Local target-runtime execution planning") {
        throw "$Name certification boundary must describe local target-runtime execution planning."
      }
      $planMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $planMarkdown)) {
        throw "$Name did not create the expected Markdown target-runtime plan: $planMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "selected_target_runtime_lane_package_readiness_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "lane_id", "selected_work_order_id", "local_only", "ec2_started", "generation_executed", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "target_runtime_execution_allowed", "package_readiness_pass", "explicit_user_selection_required", "git_checkpoint_passes_for_ec2", "source_git_clean_in_bundle", "run_package_manifest", "deploy_bundle_manifest", "deploy_bundle_zip", "deploy_bundle_zip_sha256", "checks", "failed_check_count", "exact_blockers", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "pass_local_only_selected_target_runtime_lane_package_ready_ec2_blocked") {
        throw "$Name result must be pass_local_only_selected_target_runtime_lane_package_ready_ec2_blocked after the local object_info proof includes MaskToImage."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_inpaint_detail_lane."
      }
      if ([string]$payload.selected_work_order_id -ne "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF") {
        throw "$Name must bind to the selected inpaint target-runtime work order."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must be local-only and must not start EC2, generate, or write a runtime marker."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.target_runtime_execution_allowed) {
        throw "$Name must not allow full certification or target-runtime execution from a local package readiness packet."
      }
      if (-not [bool]$payload.package_readiness_pass) {
        throw "$Name must pass local package readiness after object_info proves MaskToImage."
      }
      if (-not [bool]$payload.explicit_user_selection_required -or [bool]$payload.git_checkpoint_passes_for_ec2) {
        throw "$Name must require explicit selection and preserve the failed Git EC2 gate."
      }
      if ([bool]$payload.source_git_clean_in_bundle) {
        throw "$Name must record that the existing bundle was built from a dirty local source state."
      }
      if ([int]$payload.failed_check_count -ne 0 -or @($payload.checks | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name must pass all selected package readiness checks."
      }
      if (@($payload.exact_blockers | Where-Object { [string]$_ -eq "local_object_info_evidence_missing_runtime_required_node:MaskToImage" }).Count -eq 0) {
        $maskToImageBlockerAbsent = $true
      } else {
        throw "$Name must not retain the stale MaskToImage object_info blocker after the refresh proof."
      }
      if ([string]$payload.local_object_info_evidence -notmatch "W66_LOCAL_OBJECT_INFO_INPAINT_DETAIL_MASKTOIMAGE_REFRESH_") {
        throw "$Name must use the refreshed W66 MaskToImage object_info evidence."
      }
      if (@($payload.exact_blockers | Where-Object { [string]$_ -eq "git_checkpoint_gate_not_clean_for_ec2_execute" }).Count -eq 0) {
        throw "$Name must preserve the dirty Git EC2 blocker."
      }
      if (@($payload.exact_blockers | Where-Object { [string]$_ -eq "explicit_user_target_runtime_selection_required" }).Count -eq 0) {
        throw "$Name must preserve explicit target-runtime selection as a blocker."
      }
      if (@($payload.exact_blockers | Where-Object { [string]$_ -eq "deploy_bundle_source_git_dirty_rebuild_required_before_ec2" }).Count -eq 0) {
        throw "$Name must preserve the dirty deploy-bundle source blocker."
      }
      if ([string]$payload.certification_boundary -notmatch "Local selected-lane package readiness") {
        throw "$Name certification boundary must describe local selected-lane package readiness."
      }
      $readinessMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $readinessMarkdown)) {
        throw "$Name did not create the expected Markdown readiness packet: $readinessMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "selected_target_runtime_launch_gate_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "lane_id", "selected_work_order_id", "local_only", "aws_contacted", "s3_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "local_package_ready", "target_runtime_launch_allowed", "explicit_user_selection_required", "git_checkpoint_passes_for_ec2", "source_git_clean_in_bundle", "s3_transfer_ready_local_only", "target_runtime_plan", "selected_package_readiness", "local_object_info_evidence", "git_checkpoint_gate", "s3_transfer_readiness", "deploy_bundle_manifest", "deploy_bundle_zip", "checks", "failed_check_count", "exact_blockers", "next_live_gate_sequence", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "blocked_selected_target_runtime_launch_gate_package_ready_waiting_for_selection_and_clean_git") {
        throw "$Name result must be blocked_selected_target_runtime_launch_gate_package_ready_waiting_for_selection_and_clean_git."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
        throw "$Name lane_id must be sdxl_realvisxl_inpaint_detail_lane."
      }
      if ([string]$payload.selected_work_order_id -ne "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF") {
        throw "$Name must bind to the selected inpaint target-runtime work order."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.aws_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must be local-only and must not contact external services, start EC2, generate, post prompts, or write a runtime marker."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.target_runtime_launch_allowed) {
        throw "$Name must not allow full certification or target-runtime launch."
      }
      if (-not [bool]$payload.local_package_ready) {
        throw "$Name must recognize the selected package as locally ready."
      }
      if (-not [bool]$payload.explicit_user_selection_required -or [bool]$payload.git_checkpoint_passes_for_ec2 -or [bool]$payload.source_git_clean_in_bundle) {
        throw "$Name must preserve explicit selection, dirty Git, and dirty bundle-source blockers."
      }
      if (-not [bool]$payload.s3_transfer_ready_local_only) {
        throw "$Name must preserve the current local S3 transfer readiness."
      }
      if ([int]$payload.failed_check_count -ne 0 -or @($payload.checks | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name must pass all launch-gate state checks while still blocking launch through exact blockers."
      }
      foreach ($blocker in @("git_checkpoint_gate_not_clean_for_ec2_execute", "explicit_user_target_runtime_selection_required", "deploy_bundle_source_git_dirty_rebuild_required_before_ec2")) {
        if (@($payload.exact_blockers | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must preserve exact blocker: $blocker"
        }
      }
      if ([string]$payload.local_object_info_evidence -notmatch "W66_LOCAL_OBJECT_INFO_INPAINT_DETAIL_MASKTOIMAGE_REFRESH_") {
        throw "$Name must use the refreshed MaskToImage object_info evidence."
      }
      if (@($payload.next_live_gate_sequence).Count -lt 8) {
        throw "$Name must list the complete next live-gate sequence."
      }
      if ([string]$payload.certification_boundary -notmatch "Local selected target-runtime launch gate") {
        throw "$Name certification boundary must describe local selected target-runtime launch gate."
      }
      $launchMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $launchMarkdown)) {
        throw "$Name did not create the expected Markdown launch gate: $launchMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "active_runtime_queue_package_deploy_matrix_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "target_runtime_launch_allowed", "runtime_queue", "run_package_root", "deploy_bundle_root", "lane_count", "local_package_deploy_ready_count", "dirty_source_bundle_count", "clean_source_bundle_count", "rows", "checks", "failed_check_count", "exact_blockers", "certification_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "pass_local_only_active_runtime_queue_package_deploy_matrix_ec2_blocked") {
        throw "$Name result must be pass_local_only_active_runtime_queue_package_deploy_matrix_ec2_blocked."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.aws_contacted -or [bool]$payload.github_api_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted -or [bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must be local-only and must not contact external services, start EC2, generate, or write a runtime marker."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.target_runtime_launch_allowed) {
        throw "$Name must not allow full certification or target-runtime launch."
      }
      if ([int]$payload.lane_count -ne 9 -or @($payload.rows).Count -ne 9) {
        throw "$Name must cover all nine active runtime queue lanes."
      }
      if ([int]$payload.local_package_deploy_ready_count -ne 9) {
        throw "$Name must show all nine lanes locally package/deploy ready."
      }
      if ([int]$payload.dirty_source_bundle_count -ne 9 -or [int]$payload.clean_source_bundle_count -ne 0) {
        throw "$Name must preserve dirty-source deploy bundle blockers for all nine lanes."
      }
      if ([int]$payload.failed_check_count -ne 0 -or @($payload.checks | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name must pass all package/deploy matrix checks."
      }
      foreach ($row in @($payload.rows)) {
        if (-not [bool]$row.run_package_pass -or -not [bool]$row.deploy_bundle_pass -or -not [bool]$row.local_package_deploy_ready) {
          throw "$Name row must have passing run package and deploy bundle: $($row.lane_id)"
        }
        if ([bool]$row.source_git_clean_in_bundle -or [bool]$row.target_runtime_launch_allowed) {
          throw "$Name row must retain dirty source and disallow launch: $($row.lane_id)"
        }
      }
      foreach ($blocker in @("deploy_bundle_source_git_dirty_rebuild_required_before_ec2", "explicit_user_target_runtime_selection_required", "git_checkpoint_gate_not_clean_for_ec2_execute")) {
        if (@($payload.exact_blockers | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must preserve exact blocker: $blocker"
        }
      }
      if ([string]$payload.certification_boundary -notmatch "Local active-runtime queue package/deploy matrix") {
        throw "$Name certification boundary must describe local active-runtime queue package/deploy matrix."
      }
      $matrixMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $matrixMarkdown)) {
        throw "$Name did not create the expected Markdown package/deploy matrix: $matrixMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "selected_target_runtime_pre_ec2_handoff_bundle_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "artifact_type", "lane_id", "selected_work_order_id", "local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "target_runtime_launch_allowed", "execute_allowed_now", "target_runtime_plan", "selected_package_readiness", "selected_launch_gate", "package_deploy_matrix", "run_package_manifest", "deploy_bundle_manifest", "deploy_bundle_zip", "deploy_bundle_zip_sha256", "local_object_info_evidence", "exact_blockers", "allowed_local_recheck_step_count", "blocked_live_step_count", "allowed_local_recheck_steps", "blocked_live_steps", "command_steps", "checks", "failed_check_count", "handoff_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked") {
        throw "$Name result must be pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked."
      }
      if ([string]$payload.artifact_type -ne "selected_target_runtime_pre_ec2_handoff_bundle") {
        throw "$Name artifact_type must be selected_target_runtime_pre_ec2_handoff_bundle."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_inpaint_detail_lane" -or [string]$payload.selected_work_order_id -ne "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF") {
        throw "$Name must preserve selected inpaint target-runtime work order."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.aws_contacted -or [bool]$payload.github_api_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted -or [bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must be local-only and must not contact services, start EC2, post prompts, generate, or write runtime markers."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.target_runtime_launch_allowed -or [bool]$payload.execute_allowed_now) {
        throw "$Name must not allow full certification, launch, or immediate execution."
      }
      if ([int]$payload.allowed_local_recheck_step_count -ne 6 -or @($payload.allowed_local_recheck_steps).Count -ne 6) {
        throw "$Name must expose exactly six allowed local recheck steps."
      }
      if ([int]$payload.blocked_live_step_count -ne 7 -or @($payload.blocked_live_steps).Count -ne 7) {
        throw "$Name must block exactly seven live/S3/marker/EC2/generation steps."
      }
      foreach ($stepName in @("closure_rollup_recheck", "git_checkpoint_recheck", "runtime_unblock_handoff_recheck", "active_runtime_queue_local_support_recheck", "runtime_lane_queue_recheck", "model_registry_coverage_recheck")) {
        if (@($payload.allowed_local_recheck_steps | Where-Object { [string]$_.name -eq $stepName -and [bool]$_.allowed_in_current_local_session }).Count -ne 1) {
          throw "$Name missing allowed local recheck step: $stepName"
        }
      }
      foreach ($stepName in @("explicit_target_runtime_selection", "lane_runtime_readiness_recheck", "deploy_bundle_build", "deploy_bundle_s3_publish", "active_runtime_marker_plan_or_write", "ec2_static_proof_execute", "workflow_smoke_execute")) {
        if (@($payload.blocked_live_steps | Where-Object { [string]$_.name -eq $stepName -and -not [bool]$_.allowed_in_current_local_session }).Count -ne 1) {
          throw "$Name missing blocked live step: $stepName"
        }
      }
      foreach ($blocker in @("explicit_user_target_runtime_selection_required", "git_checkpoint_gate_not_clean_for_ec2_execute", "deploy_bundle_source_git_dirty_rebuild_required_before_ec2")) {
        if (@($payload.exact_blockers | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must preserve exact blocker: $blocker"
        }
      }
      if ([int]$payload.failed_check_count -ne 0 -or @($payload.checks | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name must pass all handoff bundle checks."
      }
      if ([string]::IsNullOrWhiteSpace([string]$payload.target_runtime_plan) -or [string]$payload.target_runtime_plan -notmatch "target_runtime_execution_plan") {
        throw "$Name must cite a target-runtime execution plan."
      }
      if ([string]$payload.handoff_boundary -notmatch "Local pre-EC2 handoff bundle") {
        throw "$Name boundary must describe a local pre-EC2 handoff bundle."
      }
      $handoffMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $handoffMarkdown)) {
        throw "$Name did not create the expected Markdown handoff bundle: $handoffMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }

  if ($entry.expected_output_valid -and $Name -eq "selected_target_runtime_local_recheck_ledger_smoke") {
    try {
      if ($null -eq $payload) {
        $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      }
      foreach ($required in @("result", "artifact_type", "lane_id", "selected_work_order_id", "local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "target_runtime_launch_allowed", "execute_allowed_now", "pre_ec2_handoff_bundle", "recheck_rows", "pass_recheck_count", "expected_blocked_recheck_count", "unexpected_recheck_count", "exact_blockers", "checks", "failed_check_count", "ledger_boundary")) {
        if (-not (Test-JsonProperty -Object $payload -Name $required)) {
          throw "$Name output is missing top-level field: $required"
        }
      }
      if ([string]$payload.result -ne "pass_local_only_selected_target_runtime_local_rechecks_accounted_ec2_blocked") {
        throw "$Name result must be pass_local_only_selected_target_runtime_local_rechecks_accounted_ec2_blocked."
      }
      if ([string]$payload.artifact_type -ne "selected_target_runtime_local_recheck_ledger") {
        throw "$Name artifact_type must be selected_target_runtime_local_recheck_ledger."
      }
      if ([string]$payload.lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
        throw "$Name must preserve selected inpaint lane."
      }
      if (-not [bool]$payload.local_only -or [bool]$payload.aws_contacted -or [bool]$payload.github_api_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted -or [bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
        throw "$Name must be local-only and must not contact services, start EC2, post prompts, generate, or write runtime markers."
      }
      if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated) {
        throw "$Name must not consume/promote masks, rerun Wave70 hard gates, or activate Wave71+."
      }
      if ([bool]$payload.full_project_certification_allowed -or [bool]$payload.target_runtime_launch_allowed -or [bool]$payload.execute_allowed_now) {
        throw "$Name must not allow full certification, launch, or immediate execution."
      }
      if (@($payload.recheck_rows).Count -ne 6) {
        throw "$Name must account for exactly six local recheck rows."
      }
      if ([int]$payload.pass_recheck_count -ne 4 -or [int]$payload.expected_blocked_recheck_count -ne 2 -or [int]$payload.unexpected_recheck_count -ne 0) {
        throw "$Name must preserve 4 pass / 2 expected blocked / 0 unexpected recheck accounting."
      }
      foreach ($row in @($payload.recheck_rows)) {
        if (-not [bool]$row.result_accepted -or -not [bool]$row.no_live_side_effects -or [string]$row.disposition -eq "unexpected") {
          throw "$Name row is not accepted and side-effect-free: $($row.name)"
        }
      }
      foreach ($rowName in @("closure_rollup_recheck", "git_checkpoint_recheck", "runtime_unblock_handoff_recheck", "active_runtime_queue_local_support_recheck", "runtime_lane_queue_recheck", "model_registry_coverage_recheck")) {
        if (@($payload.recheck_rows | Where-Object { [string]$_.name -eq $rowName }).Count -ne 1) {
          throw "$Name missing recheck row: $rowName"
        }
      }
      foreach ($blocker in @("git_checkpoint_gate_not_clean_for_ec2_execute", "deploy_bundle_source_git_dirty_rebuild_required_before_ec2", "project_readiness_runtime_lane_queue_order_blocked", "target_runtime_proof_evidence_missing")) {
        if (@($payload.exact_blockers | Where-Object { [string]$_ -eq $blocker }).Count -eq 0) {
          throw "$Name must preserve exact blocker: $blocker"
        }
      }
      foreach ($retiredBlocker in @("explicit_user_target_runtime_selection_required", "runtime_handoff_project_readiness_missing")) {
        if (@($payload.exact_blockers | Where-Object { [string]$_ -eq $retiredBlocker }).Count -ne 0) {
          throw "$Name must not preserve retired blocker after selected-lane readiness evidence is current: $retiredBlocker"
        }
      }
      if ([int]$payload.failed_check_count -ne 0 -or @($payload.checks | Where-Object { [string]$_.result -ne "pass" }).Count -ne 0) {
        throw "$Name must pass all ledger checks."
      }
      if ([string]$payload.ledger_boundary -notmatch "Local selected target-runtime recheck ledger") {
        throw "$Name boundary must describe a local selected target-runtime recheck ledger."
      }
      $ledgerMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
      if (-not (Test-Path -LiteralPath $ledgerMarkdown)) {
        throw "$Name did not create the expected Markdown local recheck ledger: $ledgerMarkdown"
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
      $entry.expected_output_valid = $false
    }
  }
  return $entry
}

function New-ContractCheck {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][bool]$Passed,
    [string]$Expected = "",
    [string]$Observed = ""
  )

  return [ordered]@{
    name = $Name
    expected = $Expected
    observed = $Observed
    result = $(if ($Passed) { "pass" } else { "fail" })
  }
}

function Test-ProjectReadinessSnapshotContract {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = "project_readiness_snapshot_contract"
    path = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $Path -TempRoot $script:ValidationTempRoot
    result = "fail"
    error = $null
    lane_id = $null
    top_level_result = $null
    failure_category = $null
    local_ready = $false
    scan_result = $null
    scan_hit_count = $null
    ec2_start_allowed = $null
    generation_allowed = $null
    auth_safe_to_start_ec2 = $null
    lane_readiness_lane_id = $null
    lane_readiness_lane_match = $null
    lane_ready_for_ec2_static_proof = $null
    lane_ready_for_generation = $null
    runtime_handoff_result = $null
    runtime_handoff_lane_id = $null
    runtime_handoff_lane_match = $null
    runtime_handoff_failure_category = $null
    runtime_handoff_next_required_action = $null
    runtime_handoff_local_only = $null
    runtime_handoff_aws_contacted = $null
    runtime_handoff_github_api_contacted = $null
    runtime_handoff_civitai_contacted = $null
    runtime_handoff_ec2_started = $null
    runtime_handoff_generation_executed = $null
    runtime_handoff_command_step_count = $null
    runtime_handoff_markdown_written = $null
    runtime_lane_queue_result = $null
    runtime_lane_queue_selected_lane_in_queue = $null
    runtime_lane_queue_selected_lane_order = $null
    runtime_lane_queue_first_runtime_lane_id = $null
    runtime_lane_queue_first_runtime_lane_match = $null
    runtime_lane_queue_current_runtime_lane_id = $null
    runtime_lane_queue_current_runtime_lane_match = $null
    runtime_lane_queue_failed_check_count = $null
    runtime_lane_queue_local_only = $null
    runtime_lane_queue_aws_contacted = $null
    runtime_lane_queue_github_api_contacted = $null
    runtime_lane_queue_civitai_contacted = $null
    runtime_lane_queue_comfyui_contacted = $null
    runtime_lane_queue_ec2_started = $null
    runtime_lane_queue_generation_executed = $null
    runtime_lane_queue_allows_selected_lane_ec2_static_proof = $null
    model_registry_coverage_result = $null
    model_registry_coverage_selected_lane_covered = $null
    model_registry_coverage_selected_lane_result = $null
    model_registry_coverage_failed_check_count = $null
    model_registry_coverage_local_only = $null
    model_registry_coverage_aws_contacted = $null
    model_registry_coverage_github_api_contacted = $null
    model_registry_coverage_civitai_contacted = $null
    model_registry_coverage_comfyui_contacted = $null
    model_registry_coverage_ec2_started = $null
    model_registry_coverage_generation_executed = $null
    model_registry_coverage_allows_selected_lane_ec2_static_proof = $null
    coordinator_blocked_execute_records_safe = $null
    contract_check_failures = 0
    contract_checks = @()
  }

  $checks = @()
  try {
    if (!(Test-Path -LiteralPath $Path)) {
      throw "Project readiness snapshot file was not created."
    }

    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $recognizedResults = @(
      "pass_local_ready_runtime_blocked_auth",
      "pass_local_ready_runtime_blocked",
      "pass_local_ready_for_ec2_static_proof",
      "pass_ready_for_generation",
      "pass_runtime_smoke_qa_complete"
    )
    $recognizedHandoffResults = @(
      "handoff_ready_runtime_blocked_auth",
      "handoff_auth_ready_lane_not_ready",
      "handoff_lane_queue_order_blocked",
      "handoff_model_registry_blocked",
      "handoff_ready_for_ec2_static_proof",
      "handoff_ready_for_generation",
      "handoff_ready_for_pullback_qa",
      "handoff_runtime_smoke_qa_complete"
    )

    if (Test-JsonProperty -Object $payload -Name "result") {
      $entry.top_level_result = [string]$payload.result
    }
    if (Test-JsonProperty -Object $payload -Name "lane_id") {
      $entry.lane_id = [string]$payload.lane_id
    }
    if (Test-JsonProperty -Object $payload -Name "failure_category") {
      $entry.failure_category = [string]$payload.failure_category
    }
    if (Test-JsonProperty -Object $payload -Name "local_ready") {
      $entry.local_ready = [bool]$payload.local_ready
    }

    $checks += New-ContractCheck -Name "top_level_result_recognized" `
      -Passed (@($recognizedResults) -contains $entry.top_level_result) `
      -Expected ($recognizedResults -join " | ") `
      -Observed ([string]$entry.top_level_result)

    $checks += New-ContractCheck -Name "local_ready_true" `
      -Passed ([bool]$entry.local_ready) `
      -Expected "true" `
      -Observed ([string]$entry.local_ready)
    $checks += New-ContractCheck -Name "lane_id_present" `
      -Passed (![string]::IsNullOrWhiteSpace([string]$entry.lane_id)) `
      -Expected "non-empty" `
      -Observed ([string]$entry.lane_id)

    if (Test-JsonProperty -Object $payload -Name "secret_private_path_scan") {
      $scan = $payload.secret_private_path_scan
      if (Test-JsonProperty -Object $scan -Name "result") { $entry.scan_result = [string]$scan.result }
      if (Test-JsonProperty -Object $scan -Name "hit_count") { $entry.scan_hit_count = [int]$scan.hit_count }
    }

    $checks += New-ContractCheck -Name "secret_private_scan_passes" `
      -Passed ($entry.scan_result -eq "pass") `
      -Expected "pass" `
      -Observed ([string]$entry.scan_result)
    $checks += New-ContractCheck -Name "secret_private_scan_zero_hits" `
      -Passed ($entry.scan_hit_count -eq 0) `
      -Expected "0" `
      -Observed ([string]$entry.scan_hit_count)

    if (!(Test-JsonProperty -Object $payload -Name "runtime_gates")) {
      $checks += New-ContractCheck -Name "runtime_gates_present" -Passed $false -Expected "present" -Observed "missing"
    } else {
      $runtime = $payload.runtime_gates
      $checks += New-ContractCheck -Name "runtime_gates_present" -Passed $true -Expected "present" -Observed "present"

      if (Test-JsonProperty -Object $runtime -Name "ec2_start_allowed") {
        $entry.ec2_start_allowed = [bool]$runtime.ec2_start_allowed
      }
      if (Test-JsonProperty -Object $runtime -Name "generation_allowed") {
        $entry.generation_allowed = [bool]$runtime.generation_allowed
      }
      if (Test-JsonProperty -Object $runtime -Name "auth_gate") {
        $authGate = $runtime.auth_gate
        if (Test-JsonProperty -Object $authGate -Name "safe_to_start_ec2") {
          $entry.auth_safe_to_start_ec2 = [bool]$authGate.safe_to_start_ec2
        }
      }
      if (Test-JsonProperty -Object $runtime -Name "lane_readiness") {
        $laneReadiness = $runtime.lane_readiness
        if (Test-JsonProperty -Object $laneReadiness -Name "lane_id") {
          $entry.lane_readiness_lane_id = [string]$laneReadiness.lane_id
        }
        if (Test-JsonProperty -Object $laneReadiness -Name "lane_match") {
          $entry.lane_readiness_lane_match = [bool]$laneReadiness.lane_match
        }
        if (Test-JsonProperty -Object $laneReadiness -Name "ready_for_ec2_static_proof") {
          $entry.lane_ready_for_ec2_static_proof = [bool]$laneReadiness.ready_for_ec2_static_proof
        }
        if (Test-JsonProperty -Object $laneReadiness -Name "ready_for_generation") {
          $entry.lane_ready_for_generation = [bool]$laneReadiness.ready_for_generation
        }
      }
      if (Test-JsonProperty -Object $runtime -Name "runtime_unblock_handoff") {
        $runtimeHandoff = $runtime.runtime_unblock_handoff
        $checks += New-ContractCheck -Name "runtime_handoff_present" -Passed $true -Expected "present" -Observed "present"
        if (Test-JsonProperty -Object $runtimeHandoff -Name "result") {
          $entry.runtime_handoff_result = [string]$runtimeHandoff.result
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "lane_id") {
          $entry.runtime_handoff_lane_id = [string]$runtimeHandoff.lane_id
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "lane_match") {
          $entry.runtime_handoff_lane_match = [bool]$runtimeHandoff.lane_match
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "failure_category") {
          $entry.runtime_handoff_failure_category = [string]$runtimeHandoff.failure_category
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "next_required_action") {
          $entry.runtime_handoff_next_required_action = [string]$runtimeHandoff.next_required_action
        }
        foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "ec2_started", "generation_executed", "markdown_written")) {
          if (Test-JsonProperty -Object $runtimeHandoff -Name $name) {
            $entry["runtime_handoff_$name"] = [bool]$runtimeHandoff.$name
          }
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "command_step_count") {
          $entry.runtime_handoff_command_step_count = [int]$runtimeHandoff.command_step_count
        }
      } else {
        $checks += New-ContractCheck -Name "runtime_handoff_present" -Passed $false -Expected "present" -Observed "missing"
      }
      if (Test-JsonProperty -Object $runtime -Name "runtime_lane_queue") {
        $runtimeLaneQueue = $runtime.runtime_lane_queue
        $checks += New-ContractCheck -Name "runtime_lane_queue_present" -Passed $true -Expected "present" -Observed "present"
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "result") {
          $entry.runtime_lane_queue_result = [string]$runtimeLaneQueue.result
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "selected_lane_in_queue") {
          $entry.runtime_lane_queue_selected_lane_in_queue = [bool]$runtimeLaneQueue.selected_lane_in_queue
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "selected_lane_order") {
          $entry.runtime_lane_queue_selected_lane_order = [int]$runtimeLaneQueue.selected_lane_order
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "first_runtime_lane_id") {
          $entry.runtime_lane_queue_first_runtime_lane_id = [string]$runtimeLaneQueue.first_runtime_lane_id
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "first_runtime_lane_match") {
          $entry.runtime_lane_queue_first_runtime_lane_match = [bool]$runtimeLaneQueue.first_runtime_lane_match
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "current_runtime_lane_id") {
          $entry.runtime_lane_queue_current_runtime_lane_id = [string]$runtimeLaneQueue.current_runtime_lane_id
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "current_runtime_lane_match") {
          $entry.runtime_lane_queue_current_runtime_lane_match = [bool]$runtimeLaneQueue.current_runtime_lane_match
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "failed_check_count") {
          $entry.runtime_lane_queue_failed_check_count = [int]$runtimeLaneQueue.failed_check_count
        }
        foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "comfyui_contacted", "ec2_started", "generation_executed")) {
          if (Test-JsonProperty -Object $runtimeLaneQueue -Name $name) {
            $entry["runtime_lane_queue_$name"] = [bool]$runtimeLaneQueue.$name
          }
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "queue_allows_selected_lane_ec2_static_proof") {
          $entry.runtime_lane_queue_allows_selected_lane_ec2_static_proof = [bool]$runtimeLaneQueue.queue_allows_selected_lane_ec2_static_proof
        }
      } else {
        $checks += New-ContractCheck -Name "runtime_lane_queue_present" -Passed $false -Expected "present" -Observed "missing"
      }
      if (Test-JsonProperty -Object $runtime -Name "model_registry_coverage") {
        $modelRegistryCoverage = $runtime.model_registry_coverage
        $checks += New-ContractCheck -Name "model_registry_coverage_present" -Passed $true -Expected "present" -Observed "present"
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "result") {
          $entry.model_registry_coverage_result = [string]$modelRegistryCoverage.result
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "selected_lane_covered") {
          $entry.model_registry_coverage_selected_lane_covered = [bool]$modelRegistryCoverage.selected_lane_covered
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "selected_lane_result") {
          $entry.model_registry_coverage_selected_lane_result = [string]$modelRegistryCoverage.selected_lane_result
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "failed_check_count") {
          $entry.model_registry_coverage_failed_check_count = [int]$modelRegistryCoverage.failed_check_count
        }
        foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "comfyui_contacted", "ec2_started", "generation_executed")) {
          if (Test-JsonProperty -Object $modelRegistryCoverage -Name $name) {
            $entry["model_registry_coverage_$name"] = [bool]$modelRegistryCoverage.$name
          }
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "coverage_allows_selected_lane_ec2_static_proof") {
          $entry.model_registry_coverage_allows_selected_lane_ec2_static_proof = [bool]$modelRegistryCoverage.coverage_allows_selected_lane_ec2_static_proof
        }
      } else {
        $checks += New-ContractCheck -Name "model_registry_coverage_present" -Passed $false -Expected "present" -Observed "missing"
      }
      if (Test-JsonProperty -Object $runtime -Name "coordinator_safety") {
        $coordinatorSafety = $runtime.coordinator_safety
        if (Test-JsonProperty -Object $coordinatorSafety -Name "blocked_execute_records_safe") {
          $entry.coordinator_blocked_execute_records_safe = [bool]$coordinatorSafety.blocked_execute_records_safe
        }
      }
    }

    $checks += New-ContractCheck -Name "runtime_handoff_result_recognized" `
      -Passed (@($recognizedHandoffResults) -contains $entry.runtime_handoff_result) `
      -Expected ($recognizedHandoffResults -join " | ") `
      -Observed ([string]$entry.runtime_handoff_result)
    $checks += New-ContractCheck -Name "lane_readiness_matches_snapshot_lane" `
      -Passed ($entry.lane_readiness_lane_match -eq $true -and [string]$entry.lane_readiness_lane_id -eq [string]$entry.lane_id) `
      -Expected ("lane_readiness.lane_match=true; lane_readiness.lane_id={0}" -f $entry.lane_id) `
      -Observed ("lane_readiness.lane_match={0}; lane_readiness.lane_id={1}" -f $entry.lane_readiness_lane_match, $entry.lane_readiness_lane_id)
    $checks += New-ContractCheck -Name "runtime_handoff_matches_snapshot_lane" `
      -Passed ($entry.runtime_handoff_lane_match -eq $true -and [string]$entry.runtime_handoff_lane_id -eq [string]$entry.lane_id) `
      -Expected ("runtime_handoff.lane_match=true; runtime_handoff.lane_id={0}" -f $entry.lane_id) `
      -Observed ("runtime_handoff.lane_match={0}; runtime_handoff.lane_id={1}" -f $entry.runtime_handoff_lane_match, $entry.runtime_handoff_lane_id)
    $checks += New-ContractCheck -Name "runtime_handoff_local_only" `
      -Passed ($entry.runtime_handoff_local_only -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_handoff_local_only)
    $checks += New-ContractCheck -Name "runtime_handoff_no_external_contacts" `
      -Passed ($entry.runtime_handoff_aws_contacted -eq $false -and $entry.runtime_handoff_github_api_contacted -eq $false -and $entry.runtime_handoff_civitai_contacted -eq $false) `
      -Expected "aws_contacted=false; github_api_contacted=false; civitai_contacted=false" `
      -Observed ("aws_contacted={0}; github_api_contacted={1}; civitai_contacted={2}" -f $entry.runtime_handoff_aws_contacted, $entry.runtime_handoff_github_api_contacted, $entry.runtime_handoff_civitai_contacted)
    $checks += New-ContractCheck -Name "runtime_handoff_no_ec2_or_generation" `
      -Passed ($entry.runtime_handoff_ec2_started -eq $false -and $entry.runtime_handoff_generation_executed -eq $false) `
      -Expected "ec2_started=false; generation_executed=false" `
      -Observed ("ec2_started={0}; generation_executed={1}" -f $entry.runtime_handoff_ec2_started, $entry.runtime_handoff_generation_executed)
    $checks += New-ContractCheck -Name "runtime_handoff_has_full_command_sequence" `
      -Passed ($entry.runtime_handoff_command_step_count -ge 8) `
      -Expected ">= 8" `
      -Observed ([string]$entry.runtime_handoff_command_step_count)
    $checks += New-ContractCheck -Name "runtime_handoff_markdown_written" `
      -Passed ($entry.runtime_handoff_markdown_written -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_handoff_markdown_written)
    $checks += New-ContractCheck -Name "runtime_lane_queue_result_passes" `
      -Passed ($entry.runtime_lane_queue_result -eq "pass_local_only") `
      -Expected "pass_local_only" `
      -Observed ([string]$entry.runtime_lane_queue_result)
    $checks += New-ContractCheck -Name "runtime_lane_queue_contains_snapshot_lane" `
      -Passed ($entry.runtime_lane_queue_selected_lane_in_queue -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_lane_queue_selected_lane_in_queue)
    $checks += New-ContractCheck -Name "runtime_lane_queue_current_lane_matches_snapshot_lane" `
      -Passed (($entry.top_level_result -eq "pass_runtime_smoke_qa_complete" -and $entry.runtime_lane_queue_selected_lane_in_queue -eq $true) -or ($entry.runtime_lane_queue_current_runtime_lane_match -eq $true -and [string]$entry.runtime_lane_queue_current_runtime_lane_id -eq [string]$entry.lane_id -and $entry.runtime_lane_queue_selected_lane_in_queue -eq $true)) `
      -Expected ("active lane: current_runtime_lane_id={0}; completed lane: selected_lane_in_queue=true" -f $entry.lane_id) `
      -Observed ("current_runtime_lane_id={0}; current_runtime_lane_match={1}; selected_lane_order={2}; selected_lane_in_queue={3}" -f $entry.runtime_lane_queue_current_runtime_lane_id, $entry.runtime_lane_queue_current_runtime_lane_match, $entry.runtime_lane_queue_selected_lane_order, $entry.runtime_lane_queue_selected_lane_in_queue)
    $checks += New-ContractCheck -Name "runtime_lane_queue_failed_check_count_zero" `
      -Passed ($entry.runtime_lane_queue_failed_check_count -eq 0) `
      -Expected "0" `
      -Observed ([string]$entry.runtime_lane_queue_failed_check_count)
    $checks += New-ContractCheck -Name "runtime_lane_queue_local_only" `
      -Passed ($entry.runtime_lane_queue_local_only -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_lane_queue_local_only)
    $checks += New-ContractCheck -Name "runtime_lane_queue_no_external_contacts" `
      -Passed ($entry.runtime_lane_queue_aws_contacted -eq $false -and $entry.runtime_lane_queue_github_api_contacted -eq $false -and $entry.runtime_lane_queue_civitai_contacted -eq $false -and $entry.runtime_lane_queue_comfyui_contacted -eq $false) `
      -Expected "aws_contacted=false; github_api_contacted=false; civitai_contacted=false; comfyui_contacted=false" `
      -Observed ("aws_contacted={0}; github_api_contacted={1}; civitai_contacted={2}; comfyui_contacted={3}" -f $entry.runtime_lane_queue_aws_contacted, $entry.runtime_lane_queue_github_api_contacted, $entry.runtime_lane_queue_civitai_contacted, $entry.runtime_lane_queue_comfyui_contacted)
    $checks += New-ContractCheck -Name "runtime_lane_queue_no_ec2_or_generation" `
      -Passed ($entry.runtime_lane_queue_ec2_started -eq $false -and $entry.runtime_lane_queue_generation_executed -eq $false) `
      -Expected "ec2_started=false; generation_executed=false" `
      -Observed ("ec2_started={0}; generation_executed={1}" -f $entry.runtime_lane_queue_ec2_started, $entry.runtime_lane_queue_generation_executed)
    $checks += New-ContractCheck -Name "runtime_lane_queue_allows_snapshot_lane" `
      -Passed (($entry.top_level_result -eq "pass_runtime_smoke_qa_complete" -and $entry.runtime_lane_queue_selected_lane_in_queue -eq $true) -or $entry.runtime_lane_queue_allows_selected_lane_ec2_static_proof -eq $true) `
      -Expected "active lane allows EC2 static proof, or completed lane remains queued without needing EC2" `
      -Observed ([string]$entry.runtime_lane_queue_allows_selected_lane_ec2_static_proof)
    $checks += New-ContractCheck -Name "model_registry_coverage_result_passes" `
      -Passed ($entry.model_registry_coverage_result -eq "pass_local_only") `
      -Expected "pass_local_only" `
      -Observed ([string]$entry.model_registry_coverage_result)
    $checks += New-ContractCheck -Name "model_registry_coverage_contains_snapshot_lane" `
      -Passed ($entry.model_registry_coverage_selected_lane_covered -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.model_registry_coverage_selected_lane_covered)
    $checks += New-ContractCheck -Name "model_registry_coverage_snapshot_lane_passes" `
      -Passed ($entry.model_registry_coverage_selected_lane_result -eq "pass") `
      -Expected "pass" `
      -Observed ([string]$entry.model_registry_coverage_selected_lane_result)
    $checks += New-ContractCheck -Name "model_registry_coverage_failed_check_count_zero" `
      -Passed ($entry.model_registry_coverage_failed_check_count -eq 0) `
      -Expected "0" `
      -Observed ([string]$entry.model_registry_coverage_failed_check_count)
    $checks += New-ContractCheck -Name "model_registry_coverage_local_only" `
      -Passed ($entry.model_registry_coverage_local_only -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.model_registry_coverage_local_only)
    $checks += New-ContractCheck -Name "model_registry_coverage_no_external_contacts" `
      -Passed ($entry.model_registry_coverage_aws_contacted -eq $false -and $entry.model_registry_coverage_github_api_contacted -eq $false -and $entry.model_registry_coverage_civitai_contacted -eq $false -and $entry.model_registry_coverage_comfyui_contacted -eq $false) `
      -Expected "aws_contacted=false; github_api_contacted=false; civitai_contacted=false; comfyui_contacted=false" `
      -Observed ("aws_contacted={0}; github_api_contacted={1}; civitai_contacted={2}; comfyui_contacted={3}" -f $entry.model_registry_coverage_aws_contacted, $entry.model_registry_coverage_github_api_contacted, $entry.model_registry_coverage_civitai_contacted, $entry.model_registry_coverage_comfyui_contacted)
    $checks += New-ContractCheck -Name "model_registry_coverage_no_ec2_or_generation" `
      -Passed ($entry.model_registry_coverage_ec2_started -eq $false -and $entry.model_registry_coverage_generation_executed -eq $false) `
      -Expected "ec2_started=false; generation_executed=false" `
      -Observed ("ec2_started={0}; generation_executed={1}" -f $entry.model_registry_coverage_ec2_started, $entry.model_registry_coverage_generation_executed)
    $checks += New-ContractCheck -Name "model_registry_coverage_allows_snapshot_lane" `
      -Passed ($entry.model_registry_coverage_allows_selected_lane_ec2_static_proof -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.model_registry_coverage_allows_selected_lane_ec2_static_proof)

    switch ($entry.top_level_result) {
      "pass_local_ready_runtime_blocked_auth" {
        $checks += New-ContractCheck -Name "blocked_auth_has_failure_category" `
          -Passed (![string]::IsNullOrWhiteSpace([string]$entry.failure_category)) `
          -Expected "non-empty" `
          -Observed ([string]$entry.failure_category)
        $checks += New-ContractCheck -Name "blocked_auth_disallows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false -and $entry.auth_safe_to_start_ec2 -eq $false) `
          -Expected "ec2_start_allowed=false; auth.safe_to_start_ec2=false" `
          -Observed ("ec2_start_allowed={0}; auth.safe_to_start_ec2={1}" -f $entry.ec2_start_allowed, $entry.auth_safe_to_start_ec2)
        $checks += New-ContractCheck -Name "blocked_auth_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "blocked_auth_coordinator_records_safe" `
          -Passed ($entry.coordinator_blocked_execute_records_safe -eq $true) `
          -Expected "true" `
          -Observed ([string]$entry.coordinator_blocked_execute_records_safe)
        $checks += New-ContractCheck -Name "blocked_auth_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -eq "handoff_ready_runtime_blocked_auth" -and $entry.runtime_handoff_next_required_action -eq "complete_aws_browser_sso_login") `
          -Expected "handoff_ready_runtime_blocked_auth; complete_aws_browser_sso_login" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
      "pass_local_ready_runtime_blocked" {
        $checks += New-ContractCheck -Name "runtime_blocked_has_failure_category" `
          -Passed (![string]::IsNullOrWhiteSpace([string]$entry.failure_category)) `
          -Expected "non-empty" `
          -Observed ([string]$entry.failure_category)
        $checks += New-ContractCheck -Name "runtime_blocked_disallows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "runtime_blocked_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "runtime_blocked_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -in @("handoff_ready_runtime_blocked_auth", "handoff_auth_ready_lane_not_ready", "handoff_lane_queue_order_blocked", "handoff_model_registry_blocked")) `
          -Expected "handoff_ready_runtime_blocked_auth | handoff_auth_ready_lane_not_ready | handoff_lane_queue_order_blocked | handoff_model_registry_blocked" `
          -Observed ([string]$entry.runtime_handoff_result)
      }
      "pass_local_ready_for_ec2_static_proof" {
        $checks += New-ContractCheck -Name "static_proof_ready_allows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $true -and $entry.lane_ready_for_ec2_static_proof -eq $true) `
          -Expected "ec2_start_allowed=true; lane.ready_for_ec2_static_proof=true" `
          -Observed ("ec2_start_allowed={0}; lane.ready_for_ec2_static_proof={1}" -f $entry.ec2_start_allowed, $entry.lane_ready_for_ec2_static_proof)
        $checks += New-ContractCheck -Name "static_proof_ready_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "static_proof_ready_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -eq "handoff_ready_for_ec2_static_proof" -and $entry.runtime_handoff_next_required_action -eq "run_ec2_static_proof") `
          -Expected "handoff_ready_for_ec2_static_proof; run_ec2_static_proof" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
      "pass_ready_for_generation" {
        $checks += New-ContractCheck -Name "generation_ready_allows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $true) `
          -Expected "true" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "generation_ready_allows_generation" `
          -Passed ($entry.generation_allowed -eq $true -and $entry.lane_ready_for_generation -eq $true) `
          -Expected "generation_allowed=true; lane.ready_for_generation=true" `
          -Observed ("generation_allowed={0}; lane.ready_for_generation={1}" -f $entry.generation_allowed, $entry.lane_ready_for_generation)
        $checks += New-ContractCheck -Name "generation_ready_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -eq "handoff_ready_for_generation" -and $entry.runtime_handoff_next_required_action -eq "run_bounded_workflow_smoke") `
          -Expected "handoff_ready_for_generation; run_bounded_workflow_smoke" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
      "pass_runtime_smoke_qa_complete" {
        $checks += New-ContractCheck -Name "completed_smoke_disallows_additional_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "completed_smoke_disallows_additional_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "completed_smoke_runtime_handoff_matches_gate" `
          -Passed (($entry.runtime_handoff_result -eq "handoff_runtime_smoke_qa_complete" -and $entry.runtime_handoff_next_required_action -eq "checkpoint_runtime_smoke_evidence_and_advance_next_goal") -or ($entry.runtime_handoff_local_only -eq $true -and $entry.runtime_handoff_ec2_started -eq $false -and $entry.runtime_handoff_generation_executed -eq $false)) `
          -Expected "preferred: handoff_runtime_smoke_qa_complete; allowed for previously completed lanes: stale local-only handoff with no EC2/generation" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
    }

    $failedChecks = @($checks | Where-Object { $_.result -ne "pass" })
    $entry.contract_checks = $checks
    $entry.contract_check_failures = @($failedChecks).Count
    $entry.result = $(if ($entry.contract_check_failures -eq 0) { "pass" } else { "fail" })
  } catch {
    $entry.error = $_.Exception.Message
    $entry.contract_checks = $checks
    $entry.contract_check_failures = $(if (@($checks).Count -eq 0) { 1 } else { @($checks | Where-Object { $_.result -ne "pass" }).Count })
    $entry.result = "fail"
  }

  return $entry
}

function New-SamplePng {
  param([Parameter(Mandatory=$true)][string]$Path)

  Add-Type -AssemblyName System.Drawing
  $bitmap = New-Object System.Drawing.Bitmap 64, 64
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.Clear([System.Drawing.Color]::FromArgb(32, 96, 160))
    $bitmap.SetPixel(0, 0, [System.Drawing.Color]::White)
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  } finally {
    $graphics.Dispose()
    $bitmap.Dispose()
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$qaRoot = Join-Path $ProjectRoot "Plan\Instructions\QA"
$scriptsRoot = Join-Path $qaRoot "Scripts"
$schemasRoot = Join-Path $qaRoot "Schemas"
$templatesRoot = Join-Path $qaRoot "Templates"
$baseGenerationRoot = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation"
$tempRoot = Join-Path $env:TEMP "comfy_ui_qa_static_validation_$stamp"
$script:ValidationTempRoot = $tempRoot
$null = New-Item -ItemType Directory -Force -Path $tempRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\QA_Helper_Static_Validation\W61_QA_HELPER_CURRENT_VALIDATION_$stamp.json"
}

$scriptParseResults = @()
foreach ($script in Get-ChildItem -LiteralPath $scriptsRoot -Filter "*.ps1" -File | Sort-Object Name) {
  $scriptParseResults += Test-PowerShellParser -Path $script.FullName
}

$jsonParseResults = @()
foreach ($json in @(
  @(Get-ChildItem -LiteralPath $schemasRoot -Filter "*.json" -File | Sort-Object Name),
  @(Get-ChildItem -LiteralPath $templatesRoot -Filter "*.json" -File | Sort-Object Name)
)) {
  foreach ($file in @($json)) {
    if ($null -ne $file) {
      $jsonParseResults += Test-JsonFile -Path $file.FullName
    }
  }
}

$markdownTemplateResults = @()
foreach ($template in Get-ChildItem -LiteralPath $templatesRoot -Filter "*.md" -File | Sort-Object Name) {
  $markdownTemplateResults += Test-MarkdownTemplate -Path $template.FullName
}

$authoredLaneDirs = @()
if (Test-Path -LiteralPath $baseGenerationRoot) {
  foreach ($dir in Get-ChildItem -LiteralPath $baseGenerationRoot -Directory | Sort-Object Name) {
    $requiredLaneFiles = @(
      "workflow.api.json",
      "patch_points.json",
      "runtime_requirements.json",
      "smoke_test_request.json"
    )
    $hasRequiredFiles = $true
    foreach ($fileName in $requiredLaneFiles) {
      if (!(Test-Path -LiteralPath (Join-Path $dir.FullName $fileName))) {
        $hasRequiredFiles = $false
        break
      }
    }
    if ($hasRequiredFiles) {
      $authoredLaneDirs += $dir
    }
  }
}

$localSmokeResults = @()
$qaRecordFile = Join-Path $tempRoot "sample_qa_record.json"
$localSmokeResults += Invoke-LocalHelper -Name "initialize_qa_record_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Initialize-QARecord.ps1") `
  -Arguments @("-ArtifactId", "sample-artifact", "-ArtifactType", "static_validation_sample", "-OutFile", $qaRecordFile) `
  -ExpectedOutputFile $qaRecordFile `
  -ExpectedOutputType "json"

$doneCertFile = Join-Path $tempRoot "sample_done_certification.md"
$localSmokeResults += Invoke-LocalHelper -Name "done_certification_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-DoneCertification.ps1") `
  -Arguments @("-TaskId", "TRK-W61-SAMPLE", "-Title", "Static validation sample", "-OutFile", $doneCertFile) `
  -ExpectedOutputFile $doneCertFile `
  -ExpectedOutputType "markdown"

$imageDryRunFile = Join-Path $tempRoot "image_qa_dry_run.json"
$imageDryRunChecklist = Join-Path $tempRoot "image_qa_dry_run_checklist.md"
$localSmokeResults += Invoke-LocalHelper -Name "image_artifact_qa_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "New-ImageArtifactQARecord.ps1") `
  -Arguments @("-DryRun", "-OutFile", $imageDryRunFile, "-ChecklistOutFile", $imageDryRunChecklist) `
  -ExpectedOutputFile $imageDryRunFile `
  -ExpectedOutputType "json"

$sampleImage = Join-Path $tempRoot "sample_image.png"
New-SamplePng -Path $sampleImage
$imageTechnicalFile = Join-Path $tempRoot "image_qa_technical.json"
$imageTechnicalChecklist = Join-Path $tempRoot "image_qa_technical_checklist.md"
$localSmokeResults += Invoke-LocalHelper -Name "image_artifact_qa_technical_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ImageArtifactQARecord.ps1") `
  -Arguments @("-ImagePath", $sampleImage, "-ArtifactId", "static_validation_sample_image", "-OutFile", $imageTechnicalFile, "-ChecklistOutFile", $imageTechnicalChecklist, "-MinimumWidth", "1", "-MinimumHeight", "1") `
  -ExpectedOutputFile $imageTechnicalFile `
  -ExpectedOutputType "json"

foreach ($laneDir in @($authoredLaneDirs)) {
  $workflowStaticFile = Join-Path $tempRoot ("workflow_static_validation_{0}.json" -f $laneDir.Name)
  $localSmokeResults += Invoke-LocalHelper -Name ("workflow_static_validation_smoke_{0}" -f $laneDir.Name) `
    -ScriptPath (Join-Path $scriptsRoot "Test-ComfyWorkflowStatic.ps1") `
    -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneDir", $laneDir.FullName, "-OutFile", $workflowStaticFile) `
    -ExpectedOutputFile $workflowStaticFile `
    -ExpectedOutputType "json"

  $laneReadinessFile = Join-Path $tempRoot ("lane_runtime_readiness_{0}.json" -f $laneDir.Name)
  $localSmokeResults += Invoke-LocalHelper -Name ("lane_runtime_readiness_smoke_{0}" -f $laneDir.Name) `
    -ScriptPath (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1") `
    -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneId", $laneDir.Name, "-OutFile", $laneReadinessFile) `
    -ExpectedOutputFile $laneReadinessFile `
    -ExpectedOutputType "json" `
    -AllowedExitCodes @(0, 2)
}

$authoredLaneEvidenceCoverageFile = Join-Path $tempRoot "authored_lane_evidence_coverage.json"
$localSmokeResults += Invoke-LocalHelper -Name "authored_lane_evidence_coverage_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-AuthoredLaneEvidenceCoverage.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $authoredLaneEvidenceCoverageFile) `
  -ExpectedOutputFile $authoredLaneEvidenceCoverageFile `
  -ExpectedOutputType "json"

$runtimeLaneQueueFile = Join-Path $tempRoot "runtime_lane_queue_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "runtime_lane_queue_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-RuntimeLaneQueue.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-CoverageFile", $authoredLaneEvidenceCoverageFile, "-OutFile", $runtimeLaneQueueFile) `
  -ExpectedOutputFile $runtimeLaneQueueFile `
  -ExpectedOutputType "json"

$projectReadinessLaneId = "sdxl_low_risk_fallback_lane"
try {
  if (Test-Path -LiteralPath $runtimeLaneQueueFile) {
    $runtimeQueueJson = Get-Content -LiteralPath $runtimeLaneQueueFile -Raw | ConvertFrom-Json
    $currentRuntimeLaneId = [string]$runtimeQueueJson.current_runtime_lane_id
    if ((Test-JsonProperty -Object $runtimeQueueJson -Name "current_runtime_lane_id") -and
      ![string]::IsNullOrWhiteSpace($currentRuntimeLaneId) -and
      $currentRuntimeLaneId -notlike "none_*") {
      $projectReadinessLaneId = $currentRuntimeLaneId
    } elseif ((Test-JsonProperty -Object $runtimeQueueJson -Name "first_runtime_lane_id") -and
      ![string]::IsNullOrWhiteSpace([string]$runtimeQueueJson.first_runtime_lane_id)) {
      $projectReadinessLaneId = [string]$runtimeQueueJson.first_runtime_lane_id
    }
  }
} catch {
  $projectReadinessLaneId = "sdxl_low_risk_fallback_lane"
}

$modelRegistryCoverageFile = Join-Path $tempRoot "workflow_model_registry_coverage.json"
$localSmokeResults += Invoke-LocalHelper -Name "workflow_model_registry_coverage_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-WorkflowModelRegistryCoverage.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $modelRegistryCoverageFile) `
  -ExpectedOutputFile $modelRegistryCoverageFile `
  -ExpectedOutputType "json"

$imageEngineRouterFile = Join-Path $tempRoot "image_engine_router_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "image_engine_router_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ImageEngineRouter.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $imageEngineRouterFile) `
  -ExpectedOutputFile $imageEngineRouterFile `
  -ExpectedOutputType "json"

$workflowRunPackageRouterGateFile = Join-Path $tempRoot "workflow_run_package_router_gate.json"
$localSmokeResults += Invoke-LocalHelper -Name "workflow_run_package_router_gate_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-WorkflowRunPackageRouterGate.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $workflowRunPackageRouterGateFile) `
  -ExpectedOutputFile $workflowRunPackageRouterGateFile `
  -ExpectedOutputType "json"

$workflowRunPackageMatrixFile = Join-Path $tempRoot "workflow_run_package_matrix.json"
$localSmokeResults += Invoke-LocalHelper -Name "workflow_run_package_matrix_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-WorkflowRunPackageMatrix.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $workflowRunPackageMatrixFile) `
  -ExpectedOutputFile $workflowRunPackageMatrixFile `
  -ExpectedOutputType "json"

$ec2DeployBundleMatrixFile = Join-Path $tempRoot "ec2_deploy_bundle_matrix.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_deploy_bundle_matrix_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-EC2DeployBundleMatrix.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $ec2DeployBundleMatrixFile) `
  -ExpectedOutputFile $ec2DeployBundleMatrixFile `
  -ExpectedOutputType "json"

$githubActionsPreflightPackageWorkflowFile = Join-Path $tempRoot "github_actions_preflight_package_workflow.json"
$localSmokeResults += Invoke-LocalHelper -Name "github_actions_preflight_package_workflow_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-GitHubActionsPreflightPackageWorkflow.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $githubActionsPreflightPackageWorkflowFile) `
  -ExpectedOutputFile $githubActionsPreflightPackageWorkflowFile `
  -ExpectedOutputType "json"

$dirtyGitCheckpointInventoryFile = Join-Path $tempRoot "dirty_git_checkpoint_inventory.json"
$dirtyGitCheckpointInventoryMarkdown = Join-Path $tempRoot "dirty_git_checkpoint_inventory.md"
$localSmokeResults += Invoke-LocalHelper -Name "dirty_git_checkpoint_inventory_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-DirtyGitCheckpointInventory.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $dirtyGitCheckpointInventoryFile, "-MarkdownOutFile", $dirtyGitCheckpointInventoryMarkdown) `
  -ExpectedOutputFile $dirtyGitCheckpointInventoryFile `
  -ExpectedOutputType "json"

$dirtyGitCheckpointScopePlanFile = Join-Path $tempRoot "dirty_git_checkpoint_scope_plan.json"
$dirtyGitCheckpointScopePlanMarkdown = Join-Path $tempRoot "dirty_git_checkpoint_scope_plan.md"
$localSmokeResults += Invoke-LocalHelper -Name "dirty_git_checkpoint_scope_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-DirtyGitCheckpointScopePlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-InventoryFile", $dirtyGitCheckpointInventoryFile, "-OutFile", $dirtyGitCheckpointScopePlanFile, "-MarkdownOutFile", $dirtyGitCheckpointScopePlanMarkdown) `
  -ExpectedOutputFile $dirtyGitCheckpointScopePlanFile `
  -ExpectedOutputType "json"

$dirtyGitCheckpointReviewResolutionFile = Join-Path $tempRoot "dirty_git_checkpoint_review_resolution.json"
$dirtyGitCheckpointReviewResolutionMarkdown = Join-Path $tempRoot "dirty_git_checkpoint_review_resolution.md"
$localSmokeResults += Invoke-LocalHelper -Name "dirty_git_checkpoint_review_resolution_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-DirtyGitCheckpointReviewResolution.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-ScopePlanFile", $dirtyGitCheckpointScopePlanFile, "-OutFile", $dirtyGitCheckpointReviewResolutionFile, "-MarkdownOutFile", $dirtyGitCheckpointReviewResolutionMarkdown) `
  -ExpectedOutputFile $dirtyGitCheckpointReviewResolutionFile `
  -ExpectedOutputType "json"

$activeRuntimeQueueLocalSupportFile = Join-Path $tempRoot "active_runtime_queue_local_support_certification.json"
$activeRuntimeQueueLocalSupportMarkdown = Join-Path $tempRoot "active_runtime_queue_local_support_certification.md"
$localSmokeResults += Invoke-LocalHelper -Name "active_runtime_queue_local_support_certification_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ActiveRuntimeQueueLocalSupportCertification.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $activeRuntimeQueueLocalSupportFile, "-CertificationPath", $activeRuntimeQueueLocalSupportMarkdown) `
  -ExpectedOutputFile $activeRuntimeQueueLocalSupportFile `
  -ExpectedOutputType "json"

$activeRuntimeQueueFinalReadinessFile = Join-Path $tempRoot "active_runtime_queue_final_certification_readiness.json"
$activeRuntimeQueueFinalReadinessMarkdown = Join-Path $tempRoot "active_runtime_queue_final_certification_readiness.md"
$localSmokeResults += Invoke-LocalHelper -Name "active_runtime_queue_final_certification_readiness_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ActiveRuntimeQueueFinalCertificationReadiness.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $activeRuntimeQueueFinalReadinessFile, "-ReadinessPath", $activeRuntimeQueueFinalReadinessMarkdown) `
  -ExpectedOutputFile $activeRuntimeQueueFinalReadinessFile `
  -ExpectedOutputType "json"

$activeRuntimeQueueFinalWorkOrderFile = Join-Path $tempRoot "active_runtime_queue_final_certification_work_order.json"
$activeRuntimeQueueFinalWorkOrderMarkdown = Join-Path $tempRoot "active_runtime_queue_final_certification_work_order.md"
$localSmokeResults += Invoke-LocalHelper -Name "active_runtime_queue_final_certification_work_order_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ActiveRuntimeQueueFinalCertificationWorkOrder.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-ReadinessEvidenceFile", $activeRuntimeQueueFinalReadinessFile, "-OutFile", $activeRuntimeQueueFinalWorkOrderFile, "-MarkdownOutFile", $activeRuntimeQueueFinalWorkOrderMarkdown) `
  -ExpectedOutputFile $activeRuntimeQueueFinalWorkOrderFile `
  -ExpectedOutputType "json"

$lowRiskLaneFinalReviewFile = Join-Path $tempRoot "low_risk_lane_final_review_packet.json"
$lowRiskLaneFinalReviewMarkdown = Join-Path $tempRoot "low_risk_lane_final_review_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "low_risk_lane_final_review_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-LowRiskLaneFinalReviewPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-OutFile", $lowRiskLaneFinalReviewFile, "-MarkdownOutFile", $lowRiskLaneFinalReviewMarkdown) `
  -ExpectedOutputFile $lowRiskLaneFinalReviewFile `
  -ExpectedOutputType "json"

$cannyLaneFinalReviewFile = Join-Path $tempRoot "canny_lane_final_review_packet.json"
$cannyLaneFinalReviewMarkdown = Join-Path $tempRoot "canny_lane_final_review_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "canny_lane_final_review_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-CannyLaneFinalReviewPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-OutFile", $cannyLaneFinalReviewFile, "-MarkdownOutFile", $cannyLaneFinalReviewMarkdown) `
  -ExpectedOutputFile $cannyLaneFinalReviewFile `
  -ExpectedOutputType "json"

$baseLaneFinalReviewBlockerFile = Join-Path $tempRoot "base_lane_final_review_blocker_packet.json"
$baseLaneFinalReviewBlockerMarkdown = Join-Path $tempRoot "base_lane_final_review_blocker_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "base_lane_final_review_blocker_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-BaseLaneFinalReviewBlockerPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-OutFile", $baseLaneFinalReviewBlockerFile, "-MarkdownOutFile", $baseLaneFinalReviewBlockerMarkdown) `
  -ExpectedOutputFile $baseLaneFinalReviewBlockerFile `
  -ExpectedOutputType "json"

$activeRuntimeQueueClosureRollupFile = Join-Path $tempRoot "active_runtime_queue_final_certification_closure_rollup.json"
$activeRuntimeQueueClosureRollupMarkdown = Join-Path $tempRoot "active_runtime_queue_final_certification_closure_rollup.md"
$localSmokeResults += Invoke-LocalHelper -Name "active_runtime_queue_final_certification_closure_rollup_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ActiveRuntimeQueueFinalCertificationClosureRollup.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-DoneEvidenceDir", $tempRoot, "-OutFile", $activeRuntimeQueueClosureRollupFile, "-MarkdownOutFile", $activeRuntimeQueueClosureRollupMarkdown) `
  -ExpectedOutputFile $activeRuntimeQueueClosureRollupFile `
  -ExpectedOutputType "json"

$activeRuntimeQueueTargetRuntimePlanFile = Join-Path $tempRoot "active_runtime_queue_target_runtime_execution_plan.json"
$activeRuntimeQueueTargetRuntimePlanMarkdown = Join-Path $tempRoot "active_runtime_queue_target_runtime_execution_plan.md"
$localSmokeResults += Invoke-LocalHelper -Name "active_runtime_queue_target_runtime_execution_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ActiveRuntimeQueueTargetRuntimeExecutionPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-ClosureRollupFile", $activeRuntimeQueueClosureRollupFile, "-OutFile", $activeRuntimeQueueTargetRuntimePlanFile, "-MarkdownOutFile", $activeRuntimeQueueTargetRuntimePlanMarkdown) `
  -ExpectedOutputFile $activeRuntimeQueueTargetRuntimePlanFile `
  -ExpectedOutputType "json"

$inpaintLaneFinalReviewBlockerFile = Join-Path $tempRoot "inpaint_lane_final_review_blocker_packet.json"
$inpaintLaneFinalReviewBlockerMarkdown = Join-Path $tempRoot "inpaint_lane_final_review_blocker_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "inpaint_lane_final_review_blocker_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-InpaintLaneFinalReviewBlockerPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-OutFile", $inpaintLaneFinalReviewBlockerFile, "-MarkdownOutFile", $inpaintLaneFinalReviewBlockerMarkdown) `
  -ExpectedOutputFile $inpaintLaneFinalReviewBlockerFile `
  -ExpectedOutputType "json"

$realesrganLaneFinalReviewBlockerFile = Join-Path $tempRoot "realesrgan_lane_final_review_blocker_packet.json"
$realesrganLaneFinalReviewBlockerMarkdown = Join-Path $tempRoot "realesrgan_lane_final_review_blocker_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "realesrgan_lane_final_review_blocker_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-RealesrganLaneFinalReviewBlockerPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-OutFile", $realesrganLaneFinalReviewBlockerFile, "-MarkdownOutFile", $realesrganLaneFinalReviewBlockerMarkdown) `
  -ExpectedOutputFile $realesrganLaneFinalReviewBlockerFile `
  -ExpectedOutputType "json"

$depthLaneFinalReviewBlockerFile = Join-Path $tempRoot "depth_lane_final_review_blocker_packet.json"
$depthLaneFinalReviewBlockerMarkdown = Join-Path $tempRoot "depth_lane_final_review_blocker_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "depth_lane_final_review_blocker_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-DepthLaneFinalReviewBlockerPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-OutFile", $depthLaneFinalReviewBlockerFile, "-MarkdownOutFile", $depthLaneFinalReviewBlockerMarkdown) `
  -ExpectedOutputFile $depthLaneFinalReviewBlockerFile `
  -ExpectedOutputType "json"

$lineartLaneFinalReviewBlockerFile = Join-Path $tempRoot "lineart_lane_final_review_blocker_packet.json"
$lineartLaneFinalReviewBlockerMarkdown = Join-Path $tempRoot "lineart_lane_final_review_blocker_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "lineart_lane_final_review_blocker_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-LineartLaneFinalReviewBlockerPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-OutFile", $lineartLaneFinalReviewBlockerFile, "-MarkdownOutFile", $lineartLaneFinalReviewBlockerMarkdown) `
  -ExpectedOutputFile $lineartLaneFinalReviewBlockerFile `
  -ExpectedOutputType "json"

$openposeLaneFinalReviewBlockerFile = Join-Path $tempRoot "openpose_lane_final_review_blocker_packet.json"
$openposeLaneFinalReviewBlockerMarkdown = Join-Path $tempRoot "openpose_lane_final_review_blocker_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "openpose_lane_final_review_blocker_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-OpenposeLaneFinalReviewBlockerPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-OutFile", $openposeLaneFinalReviewBlockerFile, "-MarkdownOutFile", $openposeLaneFinalReviewBlockerMarkdown) `
  -ExpectedOutputFile $openposeLaneFinalReviewBlockerFile `
  -ExpectedOutputType "json"

$normalLaneFinalReviewBlockerFile = Join-Path $tempRoot "normal_lane_final_review_blocker_packet.json"
$normalLaneFinalReviewBlockerMarkdown = Join-Path $tempRoot "normal_lane_final_review_blocker_packet.md"
$localSmokeResults += Invoke-LocalHelper -Name "normal_lane_final_review_blocker_packet_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-NormalLaneFinalReviewBlockerPacket.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-OutFile", $normalLaneFinalReviewBlockerFile, "-MarkdownOutFile", $normalLaneFinalReviewBlockerMarkdown) `
  -ExpectedOutputFile $normalLaneFinalReviewBlockerFile `
  -ExpectedOutputType "json"

$activeRuntimeQueueFinalReviewEvidenceCoverageFile = Join-Path $tempRoot "active_runtime_queue_final_review_evidence_coverage.json"
$activeRuntimeQueueFinalReviewEvidenceCoverageMarkdown = Join-Path $tempRoot "active_runtime_queue_final_review_evidence_coverage.md"
$localSmokeResults += Invoke-LocalHelper -Name "active_runtime_queue_final_review_evidence_coverage_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ActiveRuntimeQueueFinalReviewEvidenceCoverage.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-WorkOrderFile", $activeRuntimeQueueFinalWorkOrderFile, "-ClosureRollupFile", $activeRuntimeQueueClosureRollupFile, "-DoneEvidenceDir", $tempRoot, "-OutFile", $activeRuntimeQueueFinalReviewEvidenceCoverageFile, "-MarkdownOutFile", $activeRuntimeQueueFinalReviewEvidenceCoverageMarkdown) `
  -ExpectedOutputFile $activeRuntimeQueueFinalReviewEvidenceCoverageFile `
  -ExpectedOutputType "json"

$selectedTargetRuntimeLanePackageReadinessFile = Join-Path $tempRoot "selected_target_runtime_lane_package_readiness.json"
$selectedTargetRuntimeLanePackageReadinessMarkdown = Join-Path $tempRoot "selected_target_runtime_lane_package_readiness.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_target_runtime_lane_package_readiness_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedTargetRuntimeLanePackageReadiness.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-OutFile", $selectedTargetRuntimeLanePackageReadinessFile, "-MarkdownOutFile", $selectedTargetRuntimeLanePackageReadinessMarkdown) `
  -ExpectedOutputFile $selectedTargetRuntimeLanePackageReadinessFile `
  -ExpectedOutputType "json"

$selectedTargetRuntimeLaunchGateFile = Join-Path $tempRoot "selected_target_runtime_launch_gate.json"
$selectedTargetRuntimeLaunchGateMarkdown = Join-Path $tempRoot "selected_target_runtime_launch_gate.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_target_runtime_launch_gate_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedTargetRuntimeLaunchGate.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-SelectedPackageReadinessFile", $selectedTargetRuntimeLanePackageReadinessFile, "-OutFile", $selectedTargetRuntimeLaunchGateFile, "-MarkdownOutFile", $selectedTargetRuntimeLaunchGateMarkdown) `
  -ExpectedOutputFile $selectedTargetRuntimeLaunchGateFile `
  -ExpectedOutputType "json"

$activeRuntimeQueuePackageDeployMatrixFile = Join-Path $tempRoot "active_runtime_queue_package_deploy_matrix.json"
$activeRuntimeQueuePackageDeployMatrixMarkdown = Join-Path $tempRoot "active_runtime_queue_package_deploy_matrix.md"
$localSmokeResults += Invoke-LocalHelper -Name "active_runtime_queue_package_deploy_matrix_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ActiveRuntimeQueuePackageDeployMatrix.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $activeRuntimeQueuePackageDeployMatrixFile, "-MarkdownOutFile", $activeRuntimeQueuePackageDeployMatrixMarkdown) `
  -ExpectedOutputFile $activeRuntimeQueuePackageDeployMatrixFile `
  -ExpectedOutputType "json"

$selectedTargetRuntimePreEC2HandoffBundleFile = Join-Path $tempRoot "selected_target_runtime_pre_ec2_handoff_bundle.json"
$selectedTargetRuntimePreEC2HandoffBundleMarkdown = Join-Path $tempRoot "selected_target_runtime_pre_ec2_handoff_bundle.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_target_runtime_pre_ec2_handoff_bundle_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedTargetRuntimePreEC2HandoffBundle.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-TargetRuntimePlanFile", $activeRuntimeQueueTargetRuntimePlanFile, "-SelectedPackageReadinessFile", $selectedTargetRuntimeLanePackageReadinessFile, "-SelectedLaunchGateFile", $selectedTargetRuntimeLaunchGateFile, "-PackageDeployMatrixFile", $activeRuntimeQueuePackageDeployMatrixFile, "-OutFile", $selectedTargetRuntimePreEC2HandoffBundleFile, "-MarkdownOutFile", $selectedTargetRuntimePreEC2HandoffBundleMarkdown) `
  -ExpectedOutputFile $selectedTargetRuntimePreEC2HandoffBundleFile `
  -ExpectedOutputType "json"

$selectedTargetRuntimeLocalRecheckLedgerFile = Join-Path $tempRoot "selected_target_runtime_local_recheck_ledger.json"
$selectedTargetRuntimeLocalRecheckLedgerMarkdown = Join-Path $tempRoot "selected_target_runtime_local_recheck_ledger.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_target_runtime_local_recheck_ledger_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedTargetRuntimeLocalRecheckLedger.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-PreEC2HandoffBundleFile", $selectedTargetRuntimePreEC2HandoffBundleFile, "-OutFile", $selectedTargetRuntimeLocalRecheckLedgerFile, "-MarkdownOutFile", $selectedTargetRuntimeLocalRecheckLedgerMarkdown) `
  -ExpectedOutputFile $selectedTargetRuntimeLocalRecheckLedgerFile `
  -ExpectedOutputType "json"

$ec2WorkflowMatrixQualityRunPlanFile = Join-Path $tempRoot "ec2_workflow_matrix_quality_run_plan.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_matrix_quality_run_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-EC2WorkflowMatrixQualityRunPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $ec2WorkflowMatrixQualityRunPlanFile) `
  -ExpectedOutputFile $ec2WorkflowMatrixQualityRunPlanFile `
  -ExpectedOutputType "json"

$s3RuntimeConfigPlanFile = Join-Path $tempRoot "s3_runtime_config_plan.json"
$localSmokeResults += Invoke-LocalHelper -Name "s3_runtime_config_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-S3RuntimeConfigPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $s3RuntimeConfigPlanFile) `
  -ExpectedOutputFile $s3RuntimeConfigPlanFile `
  -ExpectedOutputType "json"

$itemsTrackerValidationFile = Join-Path $tempRoot "items_tracker_package_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "items_tracker_package_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ItemsTrackerPackageStatic.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $itemsTrackerValidationFile) `
  -ExpectedOutputFile $itemsTrackerValidationFile `
  -ExpectedOutputType "json"

$projectReadinessFile = Join-Path $tempRoot "project_readiness_snapshot.json"
$localSmokeResults += Invoke-LocalHelper -Name "project_readiness_snapshot_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ProjectReadinessSnapshot.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneId", $projectReadinessLaneId, "-OutFile", $projectReadinessFile) `
  -ExpectedOutputFile $projectReadinessFile `
  -ExpectedOutputType "json"

$projectReadinessContract = Test-ProjectReadinessSnapshotContract -Path $projectReadinessFile

$scriptFailures = @($scriptParseResults | Where-Object { $_.result -ne "pass" })
$jsonFailures = @($jsonParseResults | Where-Object { $_.result -ne "pass" })
$markdownFailures = @($markdownTemplateResults | Where-Object { $_.result -ne "pass" })
$smokeFailures = @($localSmokeResults | Where-Object { $_.result -ne "pass" -or ($_.expected_output_type -ne "none" -and -not $_.expected_output_valid) })
$contractFailures = @()
if ($projectReadinessContract.result -ne "pass") {
  $contractFailures += $projectReadinessContract
}

$qaHelperKnownIssues = @(
  "Live image/video/audio artifact QA remains pending for actual generated artifacts.",
  "The sample image technical smoke does not count as generated artifact visual review.",
  "The project readiness snapshot is local-only and does not refresh AWS browser/SSO auth.",
  "ComfyUI runtime execution, model loading, EC2 static proof, artifact pullback, and final visual QA remain separate runtime validations."
)
$qaHelperNextAction = "After AWS browser login refresh, run EC2 static proof, bounded smoke generation, artifact pullback, and real image QA."
if ($projectReadinessContract.top_level_result -eq "pass_runtime_smoke_qa_complete") {
  $qaHelperKnownIssues = @(
    "Selected lane runtime smoke, pullback hash verification, technical QA, and visual QA are complete.",
    "The QA helper is a local-only regression check and does not perform a new live GPU run.",
    "Completed lane proof is not final portfolio, video, audio, or full-project certification."
  )
  $qaHelperNextAction = "Checkpoint completed runtime-smoke evidence and advance to the next lane, module, or deeper QA target without rerunning EC2 for this same proof."
}

$record = [ordered]@{
  evidence_id = "EVID-W61-QA-HELPER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-011"
  artifact_type = "qa_helper_current_static_validation"
  tracker_ids = @("TRK-W61-011", "TRK-W61-002", "TRK-W61-006")
  item_ids = @("ITEM-W61-011", "ITEM-W61-002", "ITEM-W61-006")
  qa_protocol_used = @(
    "README_QA_WAVE61.md",
    "STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md",
    "IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md",
    "COMFYUI_WORKFLOW_TESTING_PROTOCOL.md",
    "DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Instructions/QA/Scripts/*.ps1",
    "Plan/Instructions/QA/Schemas/*.json",
    "Plan/Instructions/QA/Templates/*.json",
    "Plan/Instructions/QA/Templates/*.md",
    "all authored base-generation workflow static validation smokes",
    "all authored base-generation lane runtime readiness smokes",
    "all authored base-generation local pre-EC2 evidence coverage smoke",
    "runtime lane queue validation smoke",
    "image artifact QA dry-run and technical sample smoke",
    "Items/Tracker package validator smoke",
    "project readiness snapshot smoke",
    "project readiness snapshot contract checks"
  )
  validation_results = [ordered]@{
    script_count = @($scriptParseResults).Count
    script_parse_failures = @($scriptFailures).Count
    script_parse_results = $scriptParseResults
    json_file_count = @($jsonParseResults).Count
    json_parse_failures = @($jsonFailures).Count
    json_parse_results = $jsonParseResults
    markdown_template_count = @($markdownTemplateResults).Count
    markdown_template_failures = @($markdownFailures).Count
    markdown_template_results = $markdownTemplateResults
    authored_base_generation_lane_count = @($authoredLaneDirs).Count
    authored_base_generation_lanes = @($authoredLaneDirs | ForEach-Object { $_.Name })
    local_smoke_count = @($localSmokeResults).Count
    local_smoke_failures = @($smokeFailures).Count
    local_smoke_results = $localSmokeResults
    project_readiness_contract_failures = @($contractFailures).Count
    project_readiness_contract = $projectReadinessContract
  }
  temp_root = "[VALIDATION_TEMP_ROOT]"
  temp_root_redacted = $true
  result = $(if ($scriptFailures.Count -eq 0 -and $jsonFailures.Count -eq 0 -and $markdownFailures.Count -eq 0 -and $smokeFailures.Count -eq 0 -and $contractFailures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_issues = $qaHelperKnownIssues
  next_action = $qaHelperNextAction
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote QA helper static validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
