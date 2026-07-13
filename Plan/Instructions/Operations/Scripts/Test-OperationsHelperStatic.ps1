<#
.SYNOPSIS
Validates current Wave 60 operations helpers with local-only checks.

.DESCRIPTION
Parses every Operations/Scripts PowerShell helper, parses Operations JSON
schemas/templates, runs local-only smoke checks into a temp directory, and writes
a machine-readable evidence record. It does not contact AWS, Civitai, GitHub, or
start EC2.
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
    $tempRootProjectRelative = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $tempRootFull
    if (![string]::IsNullOrWhiteSpace($tempRootProjectRelative)) {
      $replacements += [ordered]@{ From = $tempRootProjectRelative; To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootProjectRelative.Replace("/", "\"); To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootProjectRelative.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootProjectRelative.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    }
  }
  if (![string]::IsNullOrWhiteSpace($env:TEMP)) {
    $tempFull = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempFull; To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "/"); To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "\\"); To = "[TEMP]" }
    $tempProjectRelative = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $tempFull
    if (![string]::IsNullOrWhiteSpace($tempProjectRelative)) {
      $replacements += [ordered]@{ From = $tempProjectRelative; To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempProjectRelative.Replace("/", "\"); To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempProjectRelative.Replace("\", "/"); To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempProjectRelative.Replace("\", "\\"); To = "[TEMP]" }
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

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return $null -ne ($Object.PSObject.Properties[$Name])
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

function Invoke-LocalHelper {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string[]]$Arguments = @(),
    [string]$ExpectedOutputFile = ""
  )

  $previousErrorAction = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
    $childExitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorAction
  }
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $text = ConvertTo-RedactedEvidenceText -Text $text -TempRoot $script:ValidationTempRoot
  $entry = [ordered]@{
    name = $Name
    script = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ScriptPath
    exit_code = $childExitCode
    result = $(if ($childExitCode -eq 0) { "pass" } else { "fail" })
    output_tail = $(if ($text.Length -gt 1000) { $text.Substring($text.Length - 1000) } else { $text })
    expected_output_file = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $ExpectedOutputFile -TempRoot $script:ValidationTempRoot
    expected_output_file_exists = (![string]::IsNullOrWhiteSpace($ExpectedOutputFile) -and (Test-Path -LiteralPath $ExpectedOutputFile))
    expected_output_json_valid = $false
    expected_output_error = $null
    top_level_result = $null
    top_level_failure_category = $null
    execute_gates_pass = $null
    generation_executed = $null
    ec2_started = $null
  }
  if ($entry.expected_output_file_exists) {
    try {
      $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      $entry.expected_output_json_valid = $true
      if (Has-Property -Object $payload -Name "result") {
        $entry.top_level_result = [string]$payload.result
      }
      if (Has-Property -Object $payload -Name "failure_category") {
        $entry.top_level_failure_category = $payload.failure_category
      }
      if (Has-Property -Object $payload -Name "execute_gates_pass") {
        $entry.execute_gates_pass = [bool]$payload.execute_gates_pass
      }
      if (Has-Property -Object $payload -Name "generation_executed") {
        $entry.generation_executed = [bool]$payload.generation_executed
      }
      if (Has-Property -Object $payload -Name "ec2_started") {
        $entry.ec2_started = [bool]$payload.ec2_started
      }
      if ($Name -in @("ec2_lane_static_proof_dry_run", "ec2_workflow_smoke_run_dry_run", "ec2_workflow_smoke_run_package_dry_run")) {
        foreach ($required in @("result", "failure_category", "local_git_checkpoint_gate", "execute_gates_pass", "blocked_reasons")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        foreach ($requiredGit in @("head", "origin_main", "expected_remote_head", "local_matches_origin", "clean", "result")) {
          if (-not (Has-Property -Object $payload.local_git_checkpoint_gate -Name $requiredGit)) {
            throw "$Name local_git_checkpoint_gate is missing: $requiredGit"
          }
        }
        if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
          throw "$Name output has an empty top-level result."
        }
        if (-not [bool]$payload.execute_gates_pass -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
          throw "$Name blocked output must include a top-level failure_category."
        }
      }
      if ($Name -eq "ec2_workflow_smoke_run_package_dry_run") {
        foreach ($required in @("run_package", "request_source", "smoke_request")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing package field: $required"
          }
        }
        if ([string]$payload.request_source -ne "run_package") {
          throw "$Name request_source must be run_package."
        }
        if (-not [bool]$payload.run_package.valid) {
          throw "$Name run_package.valid must be true."
        }
        if ([string]$payload.smoke_request.source -ne "run_package") {
          throw "$Name smoke_request.source must be run_package."
        }
        if ([string]::IsNullOrWhiteSpace([string]$payload.run_package.prompt_profile.profile_id)) {
          throw "$Name run package prompt profile id is missing."
        }
      }
      if ($Name -eq "github_checkpoint_dry_run") {
        foreach ($required in @("result", "failure_category", "local_only", "clean_worktree", "local_matches_origin", "porcelain_count", "tracked_porcelain_count", "untracked_porcelain_count", "commit_attempted", "push_attempted", "stage_attempted", "reset_attempted", "checkout_attempted", "checkpoint_scope_mode", "checkpoint_include_paths", "checkpoint_exclude_paths", "scope_changed_path_count", "scope_excluded_changed_path_count")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if (-not [bool]$payload.local_only) {
          throw "$Name must be local_only=true."
        }
        if ([bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.stage_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted) {
          throw "$Name dry run must not attempt stage, reset, checkout, commit, or push."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed) {
          throw "$Name must not start EC2 or run generation."
        }
        if ([string]::IsNullOrWhiteSpace([string]$payload.result)) {
          throw "$Name result must not be empty."
        }
        if ([string]$payload.checkpoint_scope_mode -ne "explicit_paths") {
          throw "$Name must validate explicit checkpoint include/exclude path support."
        }
        foreach ($requiredInclude in @("Plan", ".github", "PromptProfiles", "Workflows", "config", "PROJECT_ROOT_MANIFEST.json")) {
          if ($requiredInclude -notin @($payload.checkpoint_include_paths)) {
            throw "$Name checkpoint_include_paths is missing $requiredInclude."
          }
        }
        foreach ($requiredExclude in @("runtime_artifacts", "Ref_Image_1", "Ref_Image_2", "Ref_Image_Canonical_Body", "Reference_Images", "masks", "Jira", "Plan.zip", "_ci_w64_20260708T232900-0500")) {
          if ($requiredExclude -notin @($payload.checkpoint_exclude_paths)) {
            throw "$Name checkpoint_exclude_paths is missing $requiredExclude."
          }
        }
      }
      if ($Name -eq "scoped_git_checkpoint_manifest_smoke") {
        foreach ($required in @("result", "failure_category", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "comfyui_contacted", "s3_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "checkpoint_intent_required", "ready_for_checkpoint_execute_after_explicit_intent", "review_resolution_evidence", "checkpoint_dry_run_evidence", "review_result", "review_ready_for_guarded_checkpoint_dry_run", "dry_run_result", "dry_run_checkpoint_scope_mode", "dry_run_scope_changed_path_count", "dry_run_scope_excluded_changed_path_count", "include_paths", "exclude_paths", "missing_required_include_paths", "missing_required_exclude_paths", "blocked_include_paths", "blocked_exclude_paths", "dry_run_command", "execute_command_requires_explicit_user_intent", "checkpoint_boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "scoped_git_checkpoint_manifest_ready_pending_explicit_intent") {
          throw "$Name result must be scoped_git_checkpoint_manifest_ready_pending_explicit_intent."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.comfyui_contacted -or [bool]$payload.s3_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt) {
          throw "$Name must not stage, commit, push, reset, checkout, or rebuild deploy bundles."
        }
        if (-not [bool]$payload.checkpoint_intent_required -or -not [bool]$payload.ready_for_checkpoint_execute_after_explicit_intent) {
          throw "$Name must require explicit checkpoint intent while declaring manifest readiness."
        }
        foreach ($requiredInclude in @("Plan", ".github", "PromptProfiles", "Workflows", "config", "PROJECT_ROOT_MANIFEST.json")) {
          if ($requiredInclude -notin @($payload.include_paths)) {
            throw "$Name include_paths is missing $requiredInclude."
          }
        }
        foreach ($requiredExclude in @("runtime_artifacts", "Ref_Image_1", "Ref_Image_2", "Ref_Image_Canonical_Body", "Reference_Images", "masks", "Jira", "Plan.zip", "_ci_w64_20260708T232900-0500")) {
          if ($requiredExclude -notin @($payload.exclude_paths)) {
            throw "$Name exclude_paths is missing $requiredExclude."
          }
        }
        if (@($payload.missing_required_include_paths).Count -ne 0 -or @($payload.missing_required_exclude_paths).Count -ne 0 -or @($payload.blocked_include_paths).Count -ne 0 -or @($payload.blocked_exclude_paths).Count -ne 0) {
          throw "$Name must have no missing required or blocked include/exclude roots."
        }
        if ([string]$payload.checkpoint_boundary -notmatch "Manifest evidence only") {
          throw "$Name boundary must explicitly describe manifest-only behavior."
        }
        $manifestMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $manifestMarkdown)) {
          throw "$Name did not create the expected Markdown manifest: $manifestMarkdown"
        }
      }
      if ($Name -eq "post_checkpoint_runtime_revalidation_plan_smoke") {
        foreach ($required in @("result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "post_checkpoint_ready_to_run", "scoped_checkpoint_manifest", "manifest_checkpoint_dry_run", "package_deploy_matrix", "target_runtime_execution_plan", "selected_lane_id", "selected_package_deploy_ready", "selected_deploy_bundle_source_dirty", "manifest_ready", "manifest_checkpoint_dry_run_valid", "manifest_checkpoint_dry_run_non_mutating", "clean_git_after_checkpoint", "blocker_summary", "command_sequence", "checkpoint_boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "blocked_post_checkpoint_runtime_revalidation_waiting_for_manifest_checkpoint") {
          throw "$Name result must remain blocked until the manifest-scoped checkpoint is actually executed."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt) {
          throw "$Name must not stage, commit, push, reset, checkout, or rebuild deploy bundles."
        }
        if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated -or [bool]$payload.full_project_certification_allowed) {
          throw "$Name must not consume/promote masks, rerun Wave70, activate Wave71+, or allow final certification."
        }
        if ([bool]$payload.post_checkpoint_ready_to_run) {
          throw "$Name must not be ready while selected deploy/runtime live gates remain blocked."
        }
        foreach ($requiredBlocker in @("explicit_user_target_runtime_selection_required")) {
          if ($requiredBlocker -notin @($payload.blocker_summary)) {
            throw "$Name blocker_summary is missing $requiredBlocker."
          }
        }
        if (
          "manifest_scoped_checkpoint_not_yet_executed_clean" -notin @($payload.blocker_summary) -and
          "manifest_checkpoint_dry_run_not_valid" -notin @($payload.blocker_summary) -and
          "git_checkpoint_gate_not_clean_for_ec2_execute" -notin @($payload.blocker_summary)
        ) {
          throw "$Name blocker_summary must preserve a Git/manifest checkpoint blocker while live gates remain closed."
        }
        foreach ($requiredStep in @("manifest_scoped_checkpoint_execute", "post_checkpoint_git_gate", "active_runtime_queue_package_deploy_matrix_recheck", "selected_lane_deploy_bundle_rebuild", "target_runtime_execution_plan_recheck", "runtime_unblock_handoff_recheck", "ec2_static_proof_execute_still_blocked")) {
          if ($requiredStep -notin @($payload.command_sequence | ForEach-Object { [string]$_.name })) {
            throw "$Name command_sequence is missing $requiredStep."
          }
        }
        if ([string]$payload.checkpoint_boundary -notmatch "Post-checkpoint revalidation plan only") {
          throw "$Name boundary must explicitly describe post-checkpoint-plan-only behavior."
        }
        $postCheckpointMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $postCheckpointMarkdown)) {
          throw "$Name did not create the expected Markdown plan: $postCheckpointMarkdown"
        }
      }
      if ($Name -eq "selected_deploy_bundle_rebuild_plan_smoke") {
        foreach ($required in @("result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "selected_lane_id", "selected_work_order_id", "package_deploy_matrix", "target_runtime_execution_plan", "run_package_manifest", "run_package_exists", "run_package_pass_local_only", "existing_deploy_bundle_manifest", "existing_deploy_bundle_manifest_exists", "existing_deploy_bundle_source_git_clean", "existing_deploy_bundle_source_git_status_count", "current_git_clean", "current_git_status_count", "ready_to_rebuild_after_clean_checkpoint", "rebuild_command", "expected_manifest_after_rebuild", "expected_zip_after_rebuild", "required_post_rebuild_checks", "blockers_before_rebuild", "checkpoint_boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "selected_deploy_bundle_rebuild_plan_ready_after_clean_checkpoint") {
          throw "$Name result must be selected_deploy_bundle_rebuild_plan_ready_after_clean_checkpoint."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt) {
          throw "$Name must not stage, commit, push, reset, checkout, or rebuild deploy bundles."
        }
        if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated -or [bool]$payload.full_project_certification_allowed) {
          throw "$Name must not consume/promote masks, rerun Wave70, activate Wave71+, or allow final certification."
        }
        if ([string]$payload.selected_lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
          throw "$Name must plan the current selected inpaint lane."
        }
        if (-not [bool]$payload.run_package_exists -or -not [bool]$payload.run_package_pass_local_only) {
          throw "$Name selected run package must exist and pass local-only checks."
        }
        if ([bool]$payload.existing_deploy_bundle_source_git_clean) {
          throw "$Name should record the current selected deploy bundle source as dirty before rebuild."
        }
        if (
          -not [bool]$payload.current_git_clean -and
          "manifest_scoped_checkpoint_not_yet_executed_clean" -notin @($payload.blockers_before_rebuild)
        ) {
          throw "$Name blockers_before_rebuild must include manifest_scoped_checkpoint_not_yet_executed_clean when current Git is dirty."
        }
        if ("explicit_user_target_runtime_selection_required" -notin @($payload.blockers_before_rebuild)) {
          throw "$Name blockers_before_rebuild must preserve explicit_user_target_runtime_selection_required."
        }
        if ([string]$payload.rebuild_command -notmatch "New-EC2DeployBundle.ps1" -or [string]$payload.rebuild_command -notmatch "sdxl_realvisxl_inpaint_detail_lane" -or [string]$payload.rebuild_command -notmatch "RUN_PACKAGE_MANIFEST.json") {
          throw "$Name rebuild_command must call New-EC2DeployBundle.ps1 for the selected lane and run package."
        }
        foreach ($requiredCheck in @("source_git_clean=true", "source_git_status_count=0", "bundle_zip exists", "bundle_zip_sha256 matches actual zip hash")) {
          if ($requiredCheck -notin @($payload.required_post_rebuild_checks)) {
            throw "$Name required_post_rebuild_checks is missing $requiredCheck."
          }
        }
        if ([string]$payload.checkpoint_boundary -notmatch "Selected deploy-bundle rebuild plan only") {
          throw "$Name boundary must explicitly describe selected-rebuild-plan-only behavior."
        }
        $selectedRebuildMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $selectedRebuildMarkdown)) {
          throw "$Name did not create the expected Markdown plan: $selectedRebuildMarkdown"
        }
      }
      if ($Name -eq "selected_s3_publish_readiness_plan_smoke") {
        foreach ($required in @("result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "s3_publish_attempted", "s3_upload_execute_allowed", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "selected_lane_id", "selected_deploy_bundle_rebuild_plan", "selected_rebuild_result", "selected_rebuild_ready_after_clean_checkpoint", "selected_rebuild_current_git_clean", "selected_rebuild_command", "run_package_manifest", "expected_manifest_after_rebuild", "expected_zip_after_rebuild", "expected_manifest_exists_now", "expected_zip_exists_now", "s3_runtime_transfer_readiness", "s3_runtime_transfer_readiness_result", "s3_runtime_transfer_ready_local_only", "s3_runtime_transfer_missing_config", "region", "s3_base_uri_present", "ready_for_s3_publish_after_rebuild", "publish_dry_run_command", "publish_execute_command_requires_explicit_user_intent", "required_pre_publish_checks", "blockers_before_publish", "command_sequence", "checkpoint_boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "blocked_selected_s3_publish_readiness_waiting_for_clean_rebuild") {
          throw "$Name result must stay blocked until clean checkpoint and selected rebuild complete."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt -or [bool]$payload.s3_publish_attempted -or [bool]$payload.s3_upload_execute_allowed) {
          throw "$Name must not mutate git, rebuild deploy bundles, publish to S3, or allow S3 execute."
        }
        if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated -or [bool]$payload.full_project_certification_allowed) {
          throw "$Name must not consume/promote masks, rerun Wave70, activate Wave71+, or allow final certification."
        }
        if ([string]$payload.selected_lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
          throw "$Name must plan S3 publish readiness for the current selected inpaint lane."
        }
        if ([string]$payload.selected_rebuild_result -ne "selected_deploy_bundle_rebuild_plan_ready_after_clean_checkpoint") {
          throw "$Name must consume the selected deploy-bundle rebuild plan."
        }
        if ([bool]$payload.expected_manifest_exists_now -or [bool]$payload.expected_zip_exists_now -or [bool]$payload.ready_for_s3_publish_after_rebuild) {
          throw "$Name must remain not publish-ready before the concrete rebuilt manifest and zip exist."
        }
        foreach ($requiredBlocker in @("selected_deploy_bundle_rebuild_not_completed", "selected_deploy_bundle_manifest_missing_until_rebuild", "selected_deploy_bundle_zip_missing_until_rebuild")) {
          if ($requiredBlocker -notin @($payload.blockers_before_publish)) {
            throw "$Name blockers_before_publish is missing $requiredBlocker."
          }
        }
        if (
          "manifest_scoped_checkpoint_not_yet_executed_clean" -notin @($payload.blockers_before_publish) -and
          "deploy_bundle_source_git_dirty_rebuild_required_before_ec2" -notin @($payload.blockers_before_publish)
        ) {
          throw "$Name blockers_before_publish must include either manifest checkpoint or dirty deploy-bundle-source blocker before publish."
        }
        if ([string]$payload.publish_dry_run_command -notmatch "Publish-DeployBundleToS3.ps1" -or [string]$payload.publish_dry_run_command -notmatch "DEPLOY_BUNDLE_MANIFEST.json" -or [string]$payload.publish_dry_run_command -match "\s-Execute(\s|$)") {
          throw "$Name publish_dry_run_command must call Publish-DeployBundleToS3.ps1 without -Execute."
        }
        if ([string]$payload.publish_execute_command_requires_explicit_user_intent -notmatch "\s-Execute(\s|$)") {
          throw "$Name publish_execute_command_requires_explicit_user_intent must explicitly mark the execute-only command."
        }
        foreach ($requiredCheck in @("selected deploy-bundle rebuild completed", "DEPLOY_BUNDLE_MANIFEST.json result=pass_local_only", "bundle_zip exists", "bundle_zip_sha256 matches actual zip hash", "s3_runtime_transfer_readiness result=ready_local_only", "Publish-DeployBundleToS3.ps1 dry-run result=dry_run_ready_to_upload")) {
          if ($requiredCheck -notin @($payload.required_pre_publish_checks)) {
            throw "$Name required_pre_publish_checks is missing $requiredCheck."
          }
        }
        foreach ($requiredStep in @("manifest_scoped_checkpoint_execute", "selected_deploy_bundle_rebuild", "package_deploy_matrix_recheck", "s3_runtime_transfer_readiness_recheck", "selected_s3_publish_dry_run", "selected_s3_publish_execute_after_explicit_intent", "ec2_static_proof_execute_still_blocked")) {
          if ($requiredStep -notin @($payload.command_sequence | ForEach-Object { [string]$_.name })) {
            throw "$Name command_sequence is missing $requiredStep."
          }
        }
        if ([string]$payload.checkpoint_boundary -notmatch "Selected S3 publish readiness plan only") {
          throw "$Name boundary must explicitly describe selected-S3-publish-readiness-only behavior."
        }
        $selectedS3PublishMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $selectedS3PublishMarkdown)) {
          throw "$Name did not create the expected Markdown plan: $selectedS3PublishMarkdown"
        }
      }
      if ($Name -eq "selected_input_asset_install_readiness_plan_smoke") {
        foreach ($required in @("result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "s3_upload_attempted", "input_asset_install_attempted", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "selected_lane_id", "selected_work_order_id", "selected_package_readiness", "selected_package_readiness_result", "selected_package_ready_local_only", "selected_package_git_checkpoint_passes_for_ec2", "runtime_requirements", "required_input_asset_count", "input_asset_plans", "input_asset_local_hash_all_pass", "s3_runtime_transfer_readiness", "s3_runtime_transfer_readiness_result", "s3_runtime_transfer_ready_local_only", "input_asset_s3_base_uri_present", "region", "ready_for_input_asset_publish", "ready_for_ec2_input_asset_install_execute", "exact_blockers", "required_before_ec2_input_install", "command_sequence", "boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "blocked_selected_input_asset_install_readiness_waiting_for_s3_publish_and_live_gates") {
          throw "$Name result must stay blocked until S3 input publishing and live gates are complete."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt -or [bool]$payload.s3_upload_attempted -or [bool]$payload.input_asset_install_attempted) {
          throw "$Name must not mutate git, rebuild deploy bundles, upload to S3, or install input assets."
        }
        if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated -or [bool]$payload.full_project_certification_allowed) {
          throw "$Name must not consume/promote masks, rerun Wave70, activate Wave71+, or allow final certification."
        }
        if ([string]$payload.selected_lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
          throw "$Name must plan input-asset install readiness for the current selected inpaint lane."
        }
        if (-not [bool]$payload.selected_package_ready_local_only -or -not [bool]$payload.input_asset_local_hash_all_pass) {
          throw "$Name must consume passing selected package readiness and prove all local input asset hashes."
        }
        if ([int]$payload.required_input_asset_count -ne 2 -or @($payload.input_asset_plans).Count -ne 2) {
          throw "$Name must plan exactly the source and mask input assets for the selected inpaint lane."
        }
        foreach ($requiredFile in @("sdxl_inpaint_detail_source_canny_v1.png", "sdxl_inpaint_detail_micro_nomouth_v4.png")) {
          if ($requiredFile -notin @($payload.input_asset_plans | ForEach-Object { [string]$_.filename })) {
            throw "$Name input_asset_plans is missing $requiredFile."
          }
        }
        foreach ($assetPlan in @($payload.input_asset_plans)) {
          if (-not [bool]$assetPlan.source_file_exists -or -not [bool]$assetPlan.local_hash_match) {
            throw "$Name asset plan must have source_file_exists=true and local_hash_match=true for $($assetPlan.filename)."
          }
          if ([string]$assetPlan.publish_dry_run_command -notmatch "Publish-InputAssetToS3.ps1" -or [string]$assetPlan.publish_dry_run_command -match "\s-Execute(\s|$)") {
            throw "$Name publish_dry_run_command must call Publish-InputAssetToS3.ps1 without -Execute."
          }
          if ([string]$assetPlan.publish_execute_command_requires_explicit_user_intent -notmatch "\s-Execute(\s|$)") {
            throw "$Name publish execute command must explicitly include -Execute."
          }
          if ([string]$assetPlan.install_dry_run_command -notmatch "Install-EC2InputAssetFromS3.ps1" -or [string]$assetPlan.install_dry_run_command -match "\s-Execute(\s|$)") {
            throw "$Name install_dry_run_command must call Install-EC2InputAssetFromS3.ps1 without -Execute."
          }
          if ([string]$assetPlan.install_execute_command_requires_explicit_user_intent -notmatch "\s-Execute(\s|$)") {
            throw "$Name install execute command must explicitly include -Execute."
          }
        }
        $requiredInputAssetBlockers = @("explicit_user_target_runtime_selection_required", "input_assets_not_yet_published_to_s3_for_selected_lane", "ec2_input_asset_install_execute_requires_explicit_intent")
        if (-not [bool]$payload.selected_package_git_checkpoint_passes_for_ec2) {
          $requiredInputAssetBlockers += "git_checkpoint_gate_not_clean_for_ec2_execute"
        }
        if (-not [bool]$payload.ready_for_input_asset_publish) {
          $requiredInputAssetBlockers += "deploy_bundle_source_git_dirty_rebuild_required_before_ec2"
        }
        foreach ($requiredBlocker in $requiredInputAssetBlockers) {
          if ($requiredBlocker -notin @($payload.exact_blockers)) {
            throw "$Name exact_blockers is missing $requiredBlocker."
          }
        }
        foreach ($requiredStep in @("input_asset_publish_dry_runs", "publish_input_assets_to_s3_after_explicit_intent", "input_asset_install_dry_runs", "input_asset_install_execute_after_live_gates", "target_runtime_workflow_smoke_still_blocked")) {
          if ($requiredStep -notin @($payload.command_sequence | ForEach-Object { [string]$_.name })) {
            throw "$Name command_sequence is missing $requiredStep."
          }
        }
        if ([string]$payload.boundary -notmatch "Selected input-asset install readiness plan only") {
          throw "$Name boundary must explicitly describe selected-input-asset-install-readiness-only behavior."
        }
        $selectedInputAssetMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $selectedInputAssetMarkdown)) {
          throw "$Name did not create the expected Markdown plan: $selectedInputAssetMarkdown"
        }
      }
      if ($Name -eq "publish_input_asset_to_s3_dry_run") {
        foreach ($required in @("schema_version", "timestamp", "operation", "local_only", "aws_contacted", "s3_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "region", "asset_file", "file_name", "size_bytes", "expected_sha256", "observed_sha256", "local_hash_match", "s3_uri", "result", "failure_category", "upload", "errors", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.operation -ne "publish_input_asset_to_s3" -or [string]$payload.result -ne "dry_run_ready_to_upload_input_asset") {
          throw "$Name must produce a dry_run_ready_to_upload_input_asset publish plan."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.aws_contacted -or [bool]$payload.s3_contacted) {
          throw "$Name must remain local-only and must not contact AWS/S3."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, run generation, post prompts, or write runtime markers."
        }
        if (-not [bool]$payload.local_hash_match -or [string]$payload.s3_uri -notmatch "^s3://") {
          throw "$Name must prove the local hash and include an s3:// target URI."
        }
        if ([bool]$payload.upload.attempted) {
          throw "$Name dry run must not attempt upload."
        }
      }
      if ($Name -eq "publish_model_to_s3_dry_run") {
        foreach ($required in @("schema_version", "timestamp", "operation", "local_only", "aws_contacted", "s3_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "git_lfs_used", "region", "model_file", "file_name", "size_bytes", "expected_sha256", "observed_sha256", "local_hash_match", "s3_uri", "result", "failure_category", "upload", "errors", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.operation -ne "publish_model_to_s3" -or [string]$payload.result -ne "dry_run_ready_to_upload_model") {
          throw "$Name must produce a dry_run_ready_to_upload_model publish plan."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.aws_contacted -or [bool]$payload.s3_contacted) {
          throw "$Name must remain local-only and must not contact AWS/S3."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written -or [bool]$payload.git_lfs_used) {
          throw "$Name must not start EC2, run generation, post prompts, write runtime markers, or use Git LFS."
        }
        if (-not [bool]$payload.local_hash_match -or [string]$payload.s3_uri -notmatch "^s3://") {
          throw "$Name must prove the local hash and include an s3:// target URI."
        }
        if ([bool]$payload.upload.attempted) {
          throw "$Name dry run must not attempt upload."
        }
      }
      if ($Name -eq "selected_model_cache_readiness_plan_smoke") {
        foreach ($required in @("result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "s3_upload_attempted", "model_install_attempted", "git_lfs_used", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "full_project_certification_allowed", "selected_lane_id", "selected_work_order_id", "selected_package_readiness", "selected_package_ready_local_only", "selected_package_git_checkpoint_passes_for_ec2", "runtime_requirements", "local_object_info_evidence", "required_model_count", "model_cache_plans", "model_local_hash_all_pass_from_object_info", "s3_runtime_transfer_readiness", "s3_runtime_transfer_readiness_result", "s3_runtime_transfer_ready_local_only", "model_cache_s3_base_uri_present", "region", "ready_for_model_cache_publish", "ready_for_ec2_model_install_execute", "exact_blockers", "required_before_ec2_model_install", "command_sequence", "boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "blocked_selected_model_cache_readiness_waiting_for_s3_publish_and_live_gates") {
          throw "$Name result must stay blocked until S3 model publishing and live gates are complete."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt -or [bool]$payload.s3_upload_attempted -or [bool]$payload.model_install_attempted -or [bool]$payload.git_lfs_used) {
          throw "$Name must not mutate git, rebuild deploy bundles, upload to S3, install models, or use Git LFS."
        }
        if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated -or [bool]$payload.full_project_certification_allowed) {
          throw "$Name must not consume/promote masks, rerun Wave70, activate Wave71+, or allow final certification."
        }
        if ([string]$payload.selected_lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
          throw "$Name must plan model-cache readiness for the current selected inpaint lane."
        }
        if (-not [bool]$payload.selected_package_ready_local_only -or -not [bool]$payload.model_local_hash_all_pass_from_object_info) {
          throw "$Name must consume passing selected package readiness and object_info model hash proof."
        }
        if ([int]$payload.required_model_count -ne 1 -or @($payload.model_cache_plans).Count -ne 1) {
          throw "$Name must plan exactly the RealVisXL checkpoint for the selected inpaint lane."
        }
        $modelPlan = @($payload.model_cache_plans)[0]
        if ([string]$modelPlan.filename -ne "realvisxlV50_v50Bakedvae.safetensors" -or -not [bool]$modelPlan.local_model_exists -or -not [bool]$modelPlan.local_hash_match_from_object_info) {
          throw "$Name model_cache_plans must include a locally hash-proven RealVisXL checkpoint."
        }
        if ([string]$modelPlan.publish_dry_run_command -notmatch "Publish-ModelToS3.ps1" -or [string]$modelPlan.publish_dry_run_command -match "\s-Execute(\s|$)") {
          throw "$Name publish_dry_run_command must call Publish-ModelToS3.ps1 without -Execute."
        }
        if ([string]$modelPlan.publish_execute_command_requires_explicit_user_intent -notmatch "\s-Execute(\s|$)") {
          throw "$Name publish execute command must explicitly include -Execute."
        }
        if ([string]$modelPlan.install_dry_run_command -notmatch "Install-EC2ModelFromS3.ps1" -or [string]$modelPlan.install_dry_run_command -match "\s-Execute(\s|$)") {
          throw "$Name install_dry_run_command must call Install-EC2ModelFromS3.ps1 without -Execute."
        }
        if ([string]$modelPlan.install_execute_command_requires_explicit_user_intent -notmatch "\s-Execute(\s|$)") {
          throw "$Name install execute command must explicitly include -Execute."
        }
        $requiredModelCacheBlockers = @("explicit_user_target_runtime_selection_required", "model_not_yet_published_to_s3_for_selected_lane", "ec2_model_install_execute_requires_explicit_intent")
        if (-not [bool]$payload.selected_package_git_checkpoint_passes_for_ec2) {
          $requiredModelCacheBlockers += "git_checkpoint_gate_not_clean_for_ec2_execute"
        }
        if (-not [bool]$payload.ready_for_model_cache_publish) {
          $requiredModelCacheBlockers += "deploy_bundle_source_git_dirty_rebuild_required_before_ec2"
        }
        foreach ($requiredBlocker in $requiredModelCacheBlockers) {
          if ($requiredBlocker -notin @($payload.exact_blockers)) {
            throw "$Name exact_blockers is missing $requiredBlocker."
          }
        }
        foreach ($requiredStep in @("model_cache_publish_dry_run", "publish_model_to_s3_after_explicit_intent", "model_install_dry_run", "model_install_execute_after_live_gates", "target_runtime_workflow_smoke_still_blocked")) {
          if ($requiredStep -notin @($payload.command_sequence | ForEach-Object { [string]$_.name })) {
            throw "$Name command_sequence is missing $requiredStep."
          }
        }
        if ([string]$payload.boundary -notmatch "Selected model-cache readiness plan only") {
          throw "$Name boundary must explicitly describe selected-model-cache-readiness-only behavior."
        }
        $selectedModelCacheMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $selectedModelCacheMarkdown)) {
          throw "$Name did not create the expected Markdown plan: $selectedModelCacheMarkdown"
        }
      }
      if ($Name -eq "selected_target_runtime_live_execution_runbook_smoke") {
        foreach ($required in @("result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "s3_upload_attempted", "model_install_attempted", "input_asset_install_attempted", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "jira_mutated", "full_project_certification_allowed", "selected_lane_id", "selected_work_order_id", "selected_s3_publish_readiness", "selected_input_asset_install_readiness", "selected_model_cache_readiness", "pre_ec2_handoff_bundle", "project_readiness_snapshot", "project_readiness_result", "project_readiness_failure_category", "project_readiness_errors", "project_readiness_warnings", "project_local_ready", "git_local_matches_origin", "ready_for_live_execution", "ready_for_s3_publish_after_rebuild", "ready_for_input_asset_publish", "ready_for_ec2_input_asset_install_execute", "ready_for_model_cache_publish", "ready_for_ec2_model_install_execute", "target_runtime_launch_allowed", "execute_allowed_now", "exact_blockers", "ordered_live_execution_steps", "ordered_step_count", "checks", "failed_check_count", "boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -notin @("blocked_selected_target_runtime_live_execution_runbook_waiting_for_clean_git_and_explicit_live_intent", "blocked_selected_target_runtime_live_execution_runbook_waiting_for_explicit_live_intent")) {
          throw "$Name must remain blocked until explicit live intent, and clean Git when the Git gate has not passed."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt -or [bool]$payload.s3_upload_attempted -or [bool]$payload.model_install_attempted -or [bool]$payload.input_asset_install_attempted) {
          throw "$Name must not mutate git, rebuild deploy bundles, upload to S3, or install remote assets/models."
        }
        if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated -or [bool]$payload.jira_mutated -or [bool]$payload.full_project_certification_allowed) {
          throw "$Name must not consume/promote masks, rerun Wave70, activate Wave71+, mutate Jira, or allow final certification."
        }
        if ([string]$payload.selected_lane_id -ne "sdxl_realvisxl_inpaint_detail_lane" -or [string]$payload.selected_work_order_id -ne "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF") {
          throw "$Name must target the selected inpaint target-runtime work order."
        }
        if ([bool]$payload.ready_for_live_execution -or [bool]$payload.execute_allowed_now -or [bool]$payload.target_runtime_launch_allowed -or [bool]$payload.ready_for_ec2_input_asset_install_execute -or [bool]$payload.ready_for_ec2_model_install_execute) {
          throw "$Name must keep all live execution gates blocked."
        }
        if (-not [bool]$payload.ready_for_input_asset_publish -or -not [bool]$payload.ready_for_model_cache_publish) {
          throw "$Name must preserve the local-ready input/model evidence."
        }
        $projectReadinessAccepted = (
          ([string]$payload.project_readiness_result -eq "pass_local_ready_for_ec2_static_proof" -and [string]$payload.project_readiness_failure_category -eq "missing_ec2_static_proof") -or
          ([string]$payload.project_readiness_result -in @("pass_local_ready_runtime_blocked", "pass_local_ready_runtime_blocked_auth") -and [string]$payload.project_readiness_failure_category -eq "expired_session")
        )
        if (-not [bool]$payload.project_local_ready -or -not $projectReadinessAccepted) {
          throw "$Name must record the selected project-readiness snapshot as local-ready and either static-proof-ready or correctly fail-closed by expired auth while generation remains blocked."
        }
        if ($null -eq $payload.git_local_matches_origin) {
          throw "$Name must record the local/origin Git gate state."
        }
        if ([int]$payload.ordered_step_count -lt 17 -or @($payload.ordered_live_execution_steps).Count -ne [int]$payload.ordered_step_count) {
          throw "$Name must emit the full ordered live execution sequence."
        }
        if (@($payload.ordered_live_execution_steps | Where-Object { [bool]$_.execute_allowed_now }).Count -ne 0) {
          throw "$Name must not allow any runbook step to execute now."
        }
        foreach ($requiredStep in @("pre_ec2_handoff_recheck", "project_readiness_snapshot_recheck", "manifest_scoped_checkpoint_execute_blocked", "selected_deploy_bundle_rebuild_after_clean_checkpoint", "selected_deploy_bundle_s3_publish_dry_run", "selected_deploy_bundle_s3_publish_execute_after_explicit_intent", "ec2_static_proof_execute_blocked", "workflow_smoke_execute_blocked")) {
          if ($requiredStep -notin @($payload.ordered_live_execution_steps | ForEach-Object { [string]$_.name })) {
            throw "$Name ordered_live_execution_steps is missing $requiredStep."
          }
        }
        $projectReadinessStep = @($payload.ordered_live_execution_steps | Where-Object { [string]$_.name -eq "project_readiness_snapshot_recheck" } | Select-Object -First 1)
        if ([string]$projectReadinessStep.command -notmatch "-LaneId\s+sdxl_realvisxl_inpaint_detail_lane(\s|$)") {
          throw "$Name project_readiness_snapshot_recheck must target the selected inpaint lane."
        }
        foreach ($requiredPattern in @("input_asset_publish_dry_run:", "input_asset_publish_execute_after_explicit_intent:", "model_cache_publish_dry_run:", "model_install_execute_after_live_gates:", "input_asset_install_execute_after_live_gates:")) {
          if (@($payload.ordered_live_execution_steps | Where-Object { [string]$_.name -like "$requiredPattern*" }).Count -eq 0) {
            throw "$Name ordered_live_execution_steps is missing pattern $requiredPattern."
          }
        }
        $requiredRunbookBlockers = @("explicit_user_target_runtime_selection_required", "explicit_live_execution_intent_required", "live_s3_uploads_not_authorized", "ec2_start_not_authorized")
        if ([string]$payload.result -eq "blocked_selected_target_runtime_live_execution_runbook_waiting_for_clean_git_and_explicit_live_intent") {
          $requiredRunbookBlockers += "git_checkpoint_gate_not_clean_for_ec2_execute"
        }
        if (-not [bool]$payload.ready_for_s3_publish_after_rebuild) {
          $requiredRunbookBlockers += "deploy_bundle_source_git_dirty_rebuild_required_before_ec2"
        }
        foreach ($requiredBlocker in $requiredRunbookBlockers) {
          if ($requiredBlocker -notin @($payload.exact_blockers)) {
            throw "$Name exact_blockers is missing $requiredBlocker."
          }
        }
        if ([int]$payload.failed_check_count -ne 0) {
          throw "$Name must have failed_check_count=0."
        }
        if ([string]$payload.boundary -notmatch "Selected target-runtime live execution runbook only") {
          throw "$Name boundary must explicitly describe runbook-only behavior."
        }
        $selectedRunbookMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $selectedRunbookMarkdown)) {
          throw "$Name did not create the expected Markdown runbook: $selectedRunbookMarkdown"
        }
      }
      if ($Name -eq "selected_target_runtime_execution_readiness_snapshot_smoke") {
        foreach ($required in @("result", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "stage_attempted", "commit_attempted", "push_attempted", "reset_attempted", "checkout_attempted", "deploy_bundle_rebuilt", "s3_upload_attempted", "model_install_attempted", "input_asset_install_attempted", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "jira_mutated", "full_project_certification_allowed", "selected_lane_id", "selected_work_order_id", "live_execution_runbook", "model_install_dry_run", "source_input_install_dry_run", "mask_input_install_dry_run", "ready_for_live_execution", "execute_allowed_now", "target_runtime_launch_allowed", "local_install_dry_run_proof_count", "local_install_dry_run_proofs", "runbook_ordered_step_count", "runbook_failed_check_count", "runbook_git_local_matches_origin", "runbook_ready_for_input_asset_publish", "runbook_ready_for_model_cache_publish", "runbook_ready_for_ec2_input_asset_install_execute", "runbook_ready_for_ec2_model_install_execute", "exact_blockers", "checks", "failed_check_count", "boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "blocked_selected_target_runtime_execution_readiness_local_proofs_complete_live_gates_closed") {
          throw "$Name must report local proofs complete while live gates remain closed."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.github_api_contacted -or [bool]$payload.aws_contacted -or [bool]$payload.civitai_contacted -or [bool]$payload.s3_contacted -or [bool]$payload.comfyui_contacted) {
          throw "$Name must be local-only and must not contact external services."
        }
        if ([bool]$payload.ec2_started -or [bool]$payload.generation_executed -or [bool]$payload.prompt_posted -or [bool]$payload.active_runtime_marker_written) {
          throw "$Name must not start EC2, generate, post prompts, or write runtime markers."
        }
        if ([bool]$payload.stage_attempted -or [bool]$payload.commit_attempted -or [bool]$payload.push_attempted -or [bool]$payload.reset_attempted -or [bool]$payload.checkout_attempted -or [bool]$payload.deploy_bundle_rebuilt -or [bool]$payload.s3_upload_attempted -or [bool]$payload.model_install_attempted -or [bool]$payload.input_asset_install_attempted) {
          throw "$Name must not mutate git, rebuild deploy bundles, upload to S3, or install remote assets/models."
        }
        if ([bool]$payload.masks_consumed_as_truth -or [bool]$payload.masks_promoted -or [bool]$payload.wave70_hard_gate_rerun -or [bool]$payload.wave71_plus_activated -or [bool]$payload.jira_mutated -or [bool]$payload.full_project_certification_allowed) {
          throw "$Name must not consume/promote masks, rerun Wave70, activate Wave71+, mutate Jira, or allow final certification."
        }
        if ([string]$payload.selected_lane_id -ne "sdxl_realvisxl_inpaint_detail_lane" -or [string]$payload.selected_work_order_id -ne "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF") {
          throw "$Name must target the selected inpaint target-runtime work order."
        }
        if ([bool]$payload.ready_for_live_execution -or [bool]$payload.execute_allowed_now -or [bool]$payload.target_runtime_launch_allowed -or [bool]$payload.runbook_ready_for_ec2_input_asset_install_execute -or [bool]$payload.runbook_ready_for_ec2_model_install_execute) {
          throw "$Name must keep all live execution and EC2 install gates blocked."
        }
        if ([int]$payload.local_install_dry_run_proof_count -ne 3 -or @($payload.local_install_dry_run_proofs).Count -ne 3) {
          throw "$Name must include exactly three local install dry-run proofs."
        }
        foreach ($proof in @($payload.local_install_dry_run_proofs)) {
          if ([bool]$proof.execute -or [bool]$proof.ec2_started -or [string]$proof.command_status -ne "not_started" -or [bool]$proof.generation_executed -or [bool]$proof.git_lfs_used -or [int]$proof.error_count -ne 0) {
            throw "$Name dry-run proof $($proof.name) must remain no-execute/no-EC2/not-started/no-generation/no-Git-LFS/errors=0."
          }
        }
        foreach ($requiredProof in @("realvisxl_model_install_dry_run", "source_input_asset_install_dry_run", "mask_input_asset_install_dry_run")) {
          if ($requiredProof -notin @($payload.local_install_dry_run_proofs | ForEach-Object { [string]$_.name })) {
            throw "$Name local_install_dry_run_proofs is missing $requiredProof."
          }
        }
        if ([int]$payload.runbook_ordered_step_count -lt 17 -or [int]$payload.runbook_failed_check_count -ne 0 -or $null -eq $payload.runbook_git_local_matches_origin) {
          throw "$Name must preserve the fail-closed runbook sequence and recorded local/origin gate."
        }
        if (-not [bool]$payload.runbook_ready_for_input_asset_publish -or -not [bool]$payload.runbook_ready_for_model_cache_publish) {
          throw "$Name must preserve local publish-readiness for selected input assets and model cache."
        }
        $requiredSnapshotBlockers = @("selected_s3_publish_proof_missing_for_deploy_bundle", "selected_input_asset_s3_publish_proof_missing_for_live_install", "selected_model_s3_publish_proof_missing_for_live_install", "explicit_live_execution_intent_required", "ec2_start_not_authorized")
        if (-not [bool]$payload.runbook_ready_for_s3_publish_now_local_dry_run) {
          $requiredSnapshotBlockers += "selected_deploy_bundle_not_rebuilt_after_clean_checkpoint"
        }
        foreach ($requiredBlocker in $requiredSnapshotBlockers) {
          if ($requiredBlocker -notin @($payload.exact_blockers)) {
            throw "$Name exact_blockers is missing $requiredBlocker."
          }
        }
        if ([int]$payload.failed_check_count -ne 0) {
          throw "$Name must have failed_check_count=0."
        }
        if ([string]$payload.boundary -notmatch "Selected target-runtime execution readiness snapshot only") {
          throw "$Name boundary must explicitly describe snapshot-only behavior."
        }
        $selectedSnapshotMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $selectedSnapshotMarkdown)) {
          throw "$Name did not create the expected Markdown snapshot: $selectedSnapshotMarkdown"
        }
      }
      if ($Name -eq "selected_inpaint_pre_ec2_refresh_orchestration_smoke") {
        foreach ($required in @("result", "lane_id", "session_stamp", "local_only", "github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "jira_mutated", "execute_allowed_now", "target_runtime_launch_allowed", "child_artifact_count", "child_artifacts", "failed_child_contract_count", "boundary", "next_action")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "pass_local_only_selected_inpaint_pre_ec2_refresh_orchestrated_live_gates_closed") {
          throw "$Name must pass the local-only selected-inpaint refresh contract."
        }
        if ([string]$payload.lane_id -ne "sdxl_realvisxl_inpaint_detail_lane") {
          throw "$Name must remain scoped to the selected inpaint lane."
        }
        if (-not [bool]$payload.local_only -or [bool]$payload.execute_allowed_now -or [bool]$payload.target_runtime_launch_allowed) {
          throw "$Name must remain local-only with live execution gates closed."
        }
        foreach ($flag in @("github_api_contacted", "aws_contacted", "civitai_contacted", "s3_contacted", "comfyui_contacted", "ec2_started", "generation_executed", "prompt_posted", "active_runtime_marker_written", "masks_consumed_as_truth", "masks_promoted", "wave70_hard_gate_rerun", "wave71_plus_activated", "jira_mutated")) {
          if ([bool]$payload.$flag) {
            throw "$Name side-effect flag must remain false: $flag"
          }
        }
        if ([int]$payload.child_artifact_count -ne 4 -or @($payload.child_artifacts).Count -ne 4 -or [int]$payload.failed_child_contract_count -ne 0) {
          throw "$Name must emit exactly four passing child artifacts."
        }
        $expectedChildren = @("pre_ec2_handoff_bundle", "local_recheck_ledger", "live_execution_runbook", "execution_readiness_snapshot")
        $actualChildren = @($payload.child_artifacts | ForEach-Object { [string]$_.name })
        foreach ($expectedChild in $expectedChildren) {
          if ($expectedChild -notin $actualChildren) {
            throw "$Name child_artifacts is missing $expectedChild."
          }
        }
        foreach ($child in @($payload.child_artifacts)) {
          if (-not [bool]$child.contract_pass -or -not [bool]$child.local_only -or [bool]$child.execute_allowed_now -or [bool]$child.target_runtime_launch_allowed -or [bool]$child.live_side_effects_detected) {
            throw "$Name child contract is not local-only and fail-closed: $($child.name)"
          }
          foreach ($pathField in @("json", "markdown")) {
            $childPath = [string]$child.$pathField
            if ([string]::IsNullOrWhiteSpace($childPath) -or $childPath -notmatch [regex]::Escape([string]$payload.session_stamp)) {
              throw "$Name child $($child.name) $pathField path must include the shared session stamp."
            }
          }
        }
        $selectedOrchestrationMarkdown = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $selectedOrchestrationMarkdown)) {
          throw "$Name did not create the expected orchestration Markdown: $selectedOrchestrationMarkdown"
        }
      }
      if ($Name -eq "runtime_unblock_handoff_smoke") {
        foreach ($required in @("result", "failure_category", "next_required_action", "local_only", "aws_contacted", "ec2_started", "generation_executed", "safety_invariants", "command_sequence", "markdown_written", "gate_summary", "latest_evidence")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if (-not [bool]$payload.local_only) {
          throw "$Name must be local_only=true."
        }
        if ([bool]$payload.aws_contacted) {
          throw "$Name must not contact AWS."
        }
        if ([bool]$payload.ec2_started) {
          throw "$Name must not start EC2."
        }
        if ([bool]$payload.generation_executed) {
          throw "$Name must not execute generation."
        }
        if (-not (Has-Property -Object $payload.gate_summary -Name "run_package")) {
          throw "$Name gate_summary is missing run_package."
        }
        if (-not (Has-Property -Object $payload.gate_summary -Name "model_registry_coverage")) {
          throw "$Name gate_summary is missing model_registry_coverage."
        }
        if (-not (Has-Property -Object $payload.gate_summary -Name "git_checkpoint_gate")) {
          throw "$Name gate_summary is missing git_checkpoint_gate."
        }
        if (-not (Has-Property -Object $payload.latest_evidence -Name "git_checkpoint_gate")) {
          throw "$Name latest_evidence is missing git_checkpoint_gate."
        }
        foreach ($requiredGitGate in @("evidence", "result", "failure_category", "local_matches_origin", "clean_worktree", "commit_attempted", "push_attempted", "passes_for_ec2_execute")) {
          if (-not (Has-Property -Object $payload.gate_summary.git_checkpoint_gate -Name $requiredGitGate)) {
            throw "$Name git_checkpoint_gate is missing: $requiredGitGate"
          }
        }
        if ([bool]$payload.gate_summary.git_checkpoint_gate.commit_attempted -or [bool]$payload.gate_summary.git_checkpoint_gate.push_attempted) {
          throw "$Name git_checkpoint_gate must be sourced from a dry run with no commit or push attempt."
        }
        if (-not [bool]$payload.gate_summary.model_registry_coverage.coverage_allows_selected_lane_ec2_static_proof) {
          throw "$Name model registry coverage gate must allow selected lane EC2 static proof."
        }
        if ([bool]$payload.gate_summary.run_package.supplied) {
          if (-not [bool]$payload.gate_summary.run_package.valid) {
            throw "$Name supplied run package must be valid."
          }
          $boundedStep = @($payload.command_sequence | Where-Object { [string]$_.name -eq "bounded_workflow_smoke" } | Select-Object -First 1)
          if ($boundedStep.Count -eq 0 -or [string]$boundedStep[0].command -notmatch "-RunPackageManifestFile") {
            throw "$Name bounded_workflow_smoke command must include -RunPackageManifestFile when a run package is supplied."
          }
        }
        $modelRegistryStep = @($payload.command_sequence | Where-Object { [string]$_.name -eq "model_registry_coverage_recheck" } | Select-Object -First 1)
        if ($modelRegistryStep.Count -eq 0 -or [string]$modelRegistryStep[0].command -notmatch "Test-WorkflowModelRegistryCoverage.ps1") {
          throw "$Name command_sequence must include model_registry_coverage_recheck."
        }
        $gitCheckpointStep = @($payload.command_sequence | Where-Object { [string]$_.name -eq "git_checkpoint_recheck" } | Select-Object -First 1)
        if ($gitCheckpointStep.Count -eq 0 -or [string]$gitCheckpointStep[0].command -notmatch "Invoke-GitHubCheckpoint.ps1") {
          throw "$Name command_sequence must include git_checkpoint_recheck."
        }
        if ([string]$gitCheckpointStep[0].expected_evidence -notmatch "clean_worktree=true" -or [string]$gitCheckpointStep[0].expected_evidence -notmatch "local_matches_origin=true") {
          throw "$Name git_checkpoint_recheck expected evidence must require clean_worktree=true and local_matches_origin=true."
        }
        if (-not [bool]$payload.markdown_written) {
          throw "$Name did not write its Markdown handoff."
        }
        $expectedMarkdownFile = [System.IO.Path]::ChangeExtension($ExpectedOutputFile, ".md")
        if (-not (Test-Path -LiteralPath $expectedMarkdownFile)) {
          throw "$Name did not create the expected Markdown handoff: $expectedMarkdownFile"
        }
        $markdownBytes = [System.IO.File]::ReadAllBytes($expectedMarkdownFile)
        $allowedControlBytes = @(9, 10, 13)
        $unexpectedControlBytes = @($markdownBytes | Where-Object { ([int]$_ -lt 32) -and ($allowedControlBytes -notcontains [int]$_) })
        if ($unexpectedControlBytes.Count -gt 0) {
          throw "$Name Markdown handoff contains unexpected control characters."
        }
        $markdownText = Get-Content -LiteralPath $expectedMarkdownFile -Raw
        $tick = [string][char]96
        $markdownFence = $tick * 3
        $selectedLaneForMarkdown = [string]$payload.gate_summary.runtime_lane_queue.first_runtime_lane_id
        if ([string]::IsNullOrWhiteSpace($selectedLaneForMarkdown)) {
          $selectedLaneForMarkdown = "sdxl_low_risk_fallback_lane"
        }
        $requiredMarkdownSnippets = @(
          ("{0}powershell" -f $markdownFence),
          ("Expected AWS account is {0}029530099913{0}" -f $tick),
          ("first_runtime_lane_id={0}" -f $selectedLaneForMarkdown),
          "result=pass_local_only",
          "ready_for_ec2_static_proof=true",
          "-RunPackageManifestFile",
          "-DeployBundleS3Uri",
          "Git checkpoint gate:",
          "result=pass_git_checkpoint_ready",
          "Install-EC2ModelFromS3.ps1",
          "New-EC2EmergencyStopSchedule.ps1"
        )
        foreach ($requiredMarkdownSnippet in $requiredMarkdownSnippets) {
          if (-not $markdownText.Contains($requiredMarkdownSnippet)) {
            throw "$Name Markdown handoff is missing required text: $requiredMarkdownSnippet"
          }
        }
        if (@($payload.command_sequence).Count -lt 8) {
          throw "$Name command_sequence is missing expected post-auth steps."
        }
        foreach ($requiredSafety in @("approved_instance_id", "expected_aws_account", "do_not_start_ec2_unless_auth_safe", "do_not_start_ec2_unless_runtime_lane_queue_allows", "do_not_start_ec2_unless_git_checkpoint_clean", "do_not_start_ec2_unless_lane_ready", "prepare_deploy_bundle_before_ec2", "do_not_use_git_lfs_for_model_binaries", "install_missing_realvisxl_before_generation", "use_emergency_stop_for_live_windows", "do_not_rerun_completed_runtime_smoke", "stop_ec2_after_runtime_work")) {
          if (-not (Has-Property -Object $payload.safety_invariants -Name $requiredSafety)) {
            throw "$Name safety_invariants is missing: $requiredSafety"
          }
        }
        if (-not (Has-Property -Object $payload.safety_invariants -Name "do_not_start_ec2_unless_model_registry_coverage_passes")) {
          throw "$Name safety_invariants is missing model registry coverage gate."
        }
        if ([string]$payload.result -like "*blocked*" -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
          throw "$Name blocked result must include failure_category."
        }
      }
      if ($Name -eq "ec2_runtime_window_marker_plan_smoke") {
        foreach ($required in @("result", "local_only", "aws_contacted", "ec2_started", "generation_executed", "active_marker_written", "active_marker_path", "marker_template_path", "marker_payload", "checks", "failure_count")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if ([string]$payload.result -ne "pass_local_only_marker_plan_ready") {
          throw "$Name result must be pass_local_only_marker_plan_ready."
        }
        if (-not [bool]$payload.local_only) {
          throw "$Name must be local_only=true."
        }
        if ([bool]$payload.aws_contacted) {
          throw "$Name must not contact AWS."
        }
        if ([bool]$payload.ec2_started) {
          throw "$Name must not start EC2."
        }
        if ([bool]$payload.generation_executed) {
          throw "$Name must not execute generation."
        }
        if ([bool]$payload.active_marker_written) {
          throw "$Name must not write the active runtime marker."
        }
        if ([int]$payload.failure_count -ne 0) {
          throw "$Name failure_count must be 0."
        }
        foreach ($requiredMarker in @("schema_version", "window_id", "status", "expires_at", "instance_id", "region", "expected_account_id", "purpose", "target_lane_id", "command", "max_runtime_minutes", "emergency_stop_evidence_path", "watchdog_evidence_path_or_null", "git_head_or_bundle_sha", "owner_thread_or_automation", "allowed_stop_policy")) {
          if (-not (Has-Property -Object $payload.marker_payload -Name $requiredMarker)) {
            throw "$Name marker_payload is missing: $requiredMarker"
          }
        }
        if ([string]$payload.marker_payload.status -ne "ACTIVE") {
          throw "$Name marker_payload.status must be ACTIVE for the future marker template."
        }
        if ([string]::IsNullOrWhiteSpace([string]$payload.marker_payload.command)) {
          throw "$Name marker_payload.command must not be empty."
        }
        $templatePath = [string]$payload.marker_template_path
        if ([string]::IsNullOrWhiteSpace($templatePath)) {
          throw "$Name marker_template_path is missing."
        }
        $expectedTemplateFile = Join-Path $script:ValidationTempRoot "active_runtime_window.template.json"
        if (-not (Test-Path -LiteralPath $expectedTemplateFile)) {
          throw "$Name did not create the expected marker template: $expectedTemplateFile"
        }
        $templateJson = Get-Content -LiteralPath $expectedTemplateFile -Raw | ConvertFrom-Json
        if ([string]$templateJson.window_id -ne [string]$payload.marker_payload.window_id) {
          throw "$Name marker template window_id does not match marker_payload."
        }
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  }
  return $entry
}

function Invoke-ExpectedFailureHelper {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string[]]$Arguments = @(),
    [Parameter(Mandatory=$true)][string]$ExpectedMessagePattern,
    [string]$ForbiddenOutputFile = ""
  )

  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $text = ConvertTo-RedactedEvidenceText -Text $text -TempRoot $script:ValidationTempRoot
  $outputExists = (-not [string]::IsNullOrWhiteSpace($ForbiddenOutputFile) -and (Test-Path -LiteralPath $ForbiddenOutputFile))
  $messageMatched = $text -match $ExpectedMessagePattern
  $passed = ($exitCode -ne 0 -and $messageMatched -and -not $outputExists)

  return [ordered]@{
    name = $Name
    script = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ScriptPath
    exit_code = $exitCode
    result = $(if ($passed) { "pass" } else { "fail" })
    output_tail = $(if ($text.Length -gt 1000) { $text.Substring($text.Length - 1000) } else { $text })
    expected_output_file = $null
    expected_output_file_exists = $false
    expected_output_json_valid = $true
    expected_output_error = $(if ($passed) { $null } else { "Expected non-zero exit, matching rejection message, and no output artifact." })
    expected_failure = $true
    expected_message_matched = $messageMatched
    forbidden_output_file = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $ForbiddenOutputFile -TempRoot $script:ValidationTempRoot
    forbidden_output_file_exists = $outputExists
    top_level_result = $null
    top_level_failure_category = $null
    execute_gates_pass = $null
    generation_executed = $false
    ec2_started = $false
  }
}

function Invoke-PullbackManifestVerificationSmoke {
  param(
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [Parameter(Mandatory=$true)][string]$TempRoot
  )

  $pullbackRoot = Join-Path $TempRoot "pullback_verified"
  $imageDir = Join-Path $pullbackRoot "images"
  $null = New-Item -ItemType Directory -Force -Path $imageDir

  $imagePath = Join-Path $imageDir "sample.png"
  [System.IO.File]::WriteAllBytes($imagePath, [byte[]](137,80,78,71,13,10,26,10,0,0,0,0))
  $hash = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
  $bytes = (Get-Item -LiteralPath $imagePath).Length

  $manifestPath = Join-Path $pullbackRoot "REMOTE_ARTIFACT_MANIFEST.json"
  $manifest = [ordered]@{
    run_id = "static_validation_pullback"
    files = @(
      [ordered]@{
        relative_path = "images/sample.png"
        size_bytes = [int64]$bytes
        sha256 = $hash
        artifact_type = "image"
        qa_required = $true
      }
    )
  }
  $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

  $outFile = Join-Path $pullbackRoot "PULLBACK_RECORD.json"
  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath `
    -ProjectRoot $ProjectRoot `
    -RunId "static_validation_pullback" `
    -LocalDestination $pullbackRoot `
    -RemoteManifestFile $manifestPath `
    -OutFile $outFile 2>&1
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $text = ConvertTo-RedactedEvidenceText -Text $text -TempRoot $script:ValidationTempRoot

  $entry = [ordered]@{
    name = "ec2_pullback_manifest_verification_smoke"
    script = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ScriptPath
    exit_code = $LASTEXITCODE
    result = $(if ($LASTEXITCODE -eq 0) { "pass" } else { "fail" })
    output_tail = $(if ($text.Length -gt 1000) { $text.Substring($text.Length - 1000) } else { $text })
    expected_output_file = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $outFile -TempRoot $script:ValidationTempRoot
    expected_output_file_exists = (Test-Path -LiteralPath $outFile)
    expected_output_json_valid = $false
    expected_output_error = $null
    status = $null
    hashes_verified = $false
    file_count_remote = $null
    file_count_local = $null
    qa_required_count = 0
    manifest_counted_as_artifact = $false
  }

  if ($entry.expected_output_file_exists) {
    try {
      $record = Get-Content -LiteralPath $outFile -Raw | ConvertFrom-Json
      $entry.expected_output_json_valid = $true
      $entry.status = [string]$record.status
      $entry.hashes_verified = [bool]$record.hashes_verified
      $entry.file_count_remote = $record.file_count_remote
      $entry.file_count_local = $record.file_count_local
      $entry.qa_required_count = @($record.qa_required_files).Count
      $entry.manifest_counted_as_artifact = (@($record.files | Where-Object { [string]$_.relative_path -eq "REMOTE_ARTIFACT_MANIFEST.json" }).Count -gt 0)

      if (-not $entry.hashes_verified) { $entry.result = "fail"; $entry.expected_output_error = "hashes_verified was false." }
      if ([string]$entry.status -ne "pullback_hashes_verified") { $entry.result = "fail"; $entry.expected_output_error = "Unexpected status: $($entry.status)" }
      if ([int]$entry.file_count_remote -ne 1 -or [int]$entry.file_count_local -ne 1) { $entry.result = "fail"; $entry.expected_output_error = "Unexpected file counts remote=$($entry.file_count_remote) local=$($entry.file_count_local)" }
      if ([int]$entry.qa_required_count -ne 1) { $entry.result = "fail"; $entry.expected_output_error = "Unexpected QA required count: $($entry.qa_required_count)" }
      if ($entry.manifest_counted_as_artifact) { $entry.result = "fail"; $entry.expected_output_error = "Remote manifest was counted as a pulled artifact." }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  } else {
    $entry.result = "fail"
    $entry.expected_output_error = "Expected pullback record was not created."
  }

  return $entry
}

function Find-LatestFile {
  param(
    [string]$Directory,
    [string]$Filter
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $file = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
}

function Test-AuthGateEvidenceContract {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
    top_level_result = $null
    top_level_failure_category = $null
    top_level_account_match = $null
    top_level_remote_login_status = $null
  }

  try {
    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($required in @("result", "failure_category", "account_match", "remote_login_status", "ec2_work_allowed", "safe_to_start_ec2")) {
      if (-not (Has-Property -Object $payload -Name $required)) {
        throw "Auth gate evidence is missing top-level field: $required"
      }
    }

    $entry.top_level_result = [string]$payload.result
    $entry.top_level_failure_category = $payload.failure_category
    $entry.top_level_account_match = [bool]$payload.account_match
    $entry.top_level_remote_login_status = [string]$payload.remote_login_status

    if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
      throw "Auth gate evidence has an empty top-level result."
    }
    if (-not [bool]$payload.safe_to_start_ec2 -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
      throw "Blocked auth gate evidence must include a top-level failure_category."
    }

    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

function Test-LaneReadinessEvidenceContract {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
    top_level_result = $null
    top_level_failure_category = $null
    local_pre_ec2_ready = $null
    ready_for_ec2_static_proof = $null
    ready_for_generation = $null
    auth_gate_result = $null
    auth_gate_failure_category = $null
  }

  try {
    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($required in @("result", "failure_category", "local_pre_ec2_ready", "ready_for_ec2_static_proof", "ready_for_generation", "auth_gate")) {
      if (-not (Has-Property -Object $payload -Name $required)) {
        throw "Lane readiness evidence is missing top-level field: $required"
      }
    }
    foreach ($requiredAuth in @("result", "failure_category", "account_match", "remote_login_status", "ec2_work_allowed", "safe_to_start_ec2")) {
      if (-not (Has-Property -Object $payload.auth_gate -Name $requiredAuth)) {
        throw "Lane readiness auth_gate is missing field: $requiredAuth"
      }
    }

    $entry.top_level_result = [string]$payload.result
    $entry.top_level_failure_category = $payload.failure_category
    $entry.local_pre_ec2_ready = [bool]$payload.local_pre_ec2_ready
    $entry.ready_for_ec2_static_proof = [bool]$payload.ready_for_ec2_static_proof
    $entry.ready_for_generation = [bool]$payload.ready_for_generation
    $entry.auth_gate_result = [string]$payload.auth_gate.result
    $entry.auth_gate_failure_category = $payload.auth_gate.failure_category

    if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
      throw "Lane readiness evidence has an empty top-level result."
    }
    if (-not [bool]$payload.ready_for_generation -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
      throw "Blocked lane readiness evidence must include a top-level failure_category."
    }

    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

function Test-EC2CoordinatorGateEvidenceContract {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][ValidateSet("static_proof", "workflow_smoke")][string]$Kind
  )

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    kind = $Kind
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
    top_level_result = $null
    top_level_failure_category = $null
    execute_gates_pass = $null
    blocked_reason_count = $null
    ec2_started = $null
    command_status = $null
    generation_executed = $null
    auth_gate_result = $null
    auth_gate_failure_category = $null
    readiness_gate_result = $null
    readiness_gate_failure_category = $null
  }

  try {
    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($required in @("result", "failure_category", "execute_gates_pass", "blocked_reasons", "auth_gate", "readiness_gate")) {
      if (-not (Has-Property -Object $payload -Name $required)) {
        throw "EC2 coordinator evidence is missing top-level field: $required"
      }
    }
    foreach ($requiredAuth in @("result", "failure_category", "ec2_work_allowed", "safe_to_start_ec2")) {
      if (-not (Has-Property -Object $payload.auth_gate -Name $requiredAuth)) {
        throw "EC2 coordinator auth_gate is missing field: $requiredAuth"
      }
    }
    foreach ($requiredReadiness in @("result", "failure_category", "local_pre_ec2_ready", "ready_for_ec2_static_proof", "ready_for_generation")) {
      if (-not (Has-Property -Object $payload.readiness_gate -Name $requiredReadiness)) {
        throw "EC2 coordinator readiness_gate is missing field: $requiredReadiness"
      }
    }

    $entry.top_level_result = [string]$payload.result
    $entry.top_level_failure_category = $payload.failure_category
    $entry.execute_gates_pass = [bool]$payload.execute_gates_pass
    $entry.blocked_reason_count = @($payload.blocked_reasons).Count
    $entry.auth_gate_result = [string]$payload.auth_gate.result
    $entry.auth_gate_failure_category = $payload.auth_gate.failure_category
    $entry.readiness_gate_result = [string]$payload.readiness_gate.result
    $entry.readiness_gate_failure_category = $payload.readiness_gate.failure_category

    if (Has-Property -Object $payload -Name "ec2_started") {
      $entry.ec2_started = [bool]$payload.ec2_started
    }
    if (Has-Property -Object $payload -Name "command_status") {
      $entry.command_status = [string]$payload.command_status
    }
    if (Has-Property -Object $payload -Name "generation_executed") {
      $entry.generation_executed = [bool]$payload.generation_executed
    }

    if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
      throw "EC2 coordinator evidence has an empty top-level result."
    }
    if (-not $entry.execute_gates_pass) {
      if ([string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
        throw "Blocked EC2 coordinator evidence must include a top-level failure_category."
      }
      if ($entry.blocked_reason_count -eq 0) {
        throw "Blocked EC2 coordinator evidence must include blocked_reasons."
      }
    }
    if ($entry.top_level_result -like "*blocked_before_ec2_start*") {
      if (-not (Has-Property -Object $payload -Name "ec2_started")) {
        throw "Blocked-before-start EC2 coordinator evidence must include ec2_started."
      }
      if ([bool]$payload.ec2_started) {
        throw "Blocked-before-start EC2 coordinator evidence must not start EC2."
      }
      if ((Has-Property -Object $payload -Name "command_status") -and [string]$payload.command_status -ne "not_started") {
        throw "Blocked-before-start EC2 coordinator evidence must keep command_status=not_started."
      }
    }
    if ($Kind -eq "workflow_smoke") {
      if (-not (Has-Property -Object $payload -Name "generation_executed")) {
        throw "Workflow smoke coordinator evidence is missing generation_executed."
      }
      if (-not $entry.execute_gates_pass -and [bool]$payload.generation_executed) {
        throw "Blocked workflow smoke coordinator evidence must not execute generation."
      }
    }

    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

function Test-ControlNetCannyW68GateEvidenceContract {
  param(
    [Parameter(Mandatory=$true)][string]$AuthGatePath,
    [Parameter(Mandatory=$true)][string]$ReadinessPath,
    [Parameter(Mandatory=$true)][string]$StaticProofPath,
    [Parameter(Mandatory=$true)][string]$WorkflowSmokePath
  )

  $entry = [ordered]@{
    name = "controlnet_canny_w68_gate_contract"
    path = "Plan/Instructions/QA/Evidence"
    result = "fail"
    error = $null
    auth_gate = $null
    readiness_gate = $null
    static_proof = $null
    workflow_smoke = $null
  }

  try {
    foreach ($requiredPath in @($AuthGatePath, $ReadinessPath, $StaticProofPath, $WorkflowSmokePath)) {
      if ([string]::IsNullOrWhiteSpace($requiredPath) -or !(Test-Path -LiteralPath $requiredPath)) {
        throw "Missing W68 ControlNet Canny gate evidence: $requiredPath"
      }
    }

    $authGate = Get-Content -LiteralPath $AuthGatePath -Raw | ConvertFrom-Json
    $readinessGate = Get-Content -LiteralPath $ReadinessPath -Raw | ConvertFrom-Json
    $staticProof = Get-Content -LiteralPath $StaticProofPath -Raw | ConvertFrom-Json
    $workflowSmoke = Get-Content -LiteralPath $WorkflowSmokePath -Raw | ConvertFrom-Json

    $entry.auth_gate = [ordered]@{
      file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $AuthGatePath
      result = [string]$authGate.result
      failure_category = [string]$authGate.failure_category
      remote_login_status = [string]$authGate.remote_login_status
      safe_to_start_ec2 = [bool]$authGate.safe_to_start_ec2
      generation_allowed = [bool]$authGate.generation_allowed
      auth_url_recorded = [bool]$authGate.auth_url_recorded
    }
    if ($entry.auth_gate.result -ne "blocked_expired_session") {
      throw "W68 Canny auth gate must have result=blocked_expired_session."
    }
    if ($entry.auth_gate.failure_category -ne "expired_session") {
      throw "W68 Canny auth gate must have failure_category=expired_session."
    }
    if ($entry.auth_gate.remote_login_status -ne "external_authorization_required_noninteractive") {
      throw "W68 Canny auth gate must classify remote login as external_authorization_required_noninteractive."
    }
    if ($entry.auth_gate.safe_to_start_ec2 -or $entry.auth_gate.generation_allowed -or $entry.auth_gate.auth_url_recorded) {
      throw "W68 Canny auth gate must keep EC2/generation ready and must not record the auth URL."
    }

    $entry.readiness_gate = [ordered]@{
      file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ReadinessPath
      lane_id = [string]$readinessGate.lane_id
      result = [string]$readinessGate.result
      failure_category = [string]$readinessGate.failure_category
      local_pre_ec2_ready = [bool]$readinessGate.local_pre_ec2_ready
      ready_for_ec2_static_proof = [bool]$readinessGate.ready_for_ec2_static_proof
      ready_for_generation = [bool]$readinessGate.ready_for_generation
      auth_gate_result = [string]$readinessGate.auth_gate.result
    }
    if ($entry.readiness_gate.lane_id -ne "sdxl_realvisxl_controlnet_canny_lane") {
      throw "W68 Canny readiness gate must target sdxl_realvisxl_controlnet_canny_lane."
    }
    if ($entry.readiness_gate.result -ne "local_pre_ec2_ready_runtime_blocked_auth") {
      throw "W68 Canny readiness gate must have result=local_pre_ec2_ready_runtime_blocked_auth."
    }
    if ($entry.readiness_gate.failure_category -ne "expired_session") {
      throw "W68 Canny readiness gate must have failure_category=expired_session."
    }
    if (-not $entry.readiness_gate.local_pre_ec2_ready -or $entry.readiness_gate.ready_for_ec2_static_proof -or $entry.readiness_gate.ready_for_generation) {
      throw "W68 Canny readiness gate must be locally ready while keeping EC2 static proof and generation ready."
    }
    if ($entry.readiness_gate.auth_gate_result -ne "blocked_expired_session") {
      throw "W68 Canny readiness gate must embed the blocked auth result."
    }

    $entry.static_proof = [ordered]@{
      file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $StaticProofPath
      result = [string]$staticProof.result
      failure_category = [string]$staticProof.failure_category
      execute_gates_pass = [bool]$staticProof.execute_gates_pass
      ec2_started = [bool]$staticProof.ec2_started
      generation_executed = [bool]$staticProof.generation_executed
      local_git_checkpoint_result = [string]$staticProof.local_git_checkpoint_gate.result
      auth_gate_file = [string]$staticProof.auth_gate.file
      readiness_gate_file = [string]$staticProof.readiness_gate.file
    }
    if ($entry.static_proof.result -ne "blocked_before_ec2_start" -or $entry.static_proof.failure_category -ne "expired_session") {
      throw "W68 Canny static proof must be blocked_before_ec2_start by expired_session."
    }
    if ($entry.static_proof.execute_gates_pass -or $entry.static_proof.ec2_started -or $entry.static_proof.generation_executed) {
      throw "W68 Canny static proof must not pass execute gates, start EC2, or run generation."
    }
    if ($entry.static_proof.local_git_checkpoint_result -ne "pass") {
      throw "W68 Canny static proof must include a passing local git checkpoint gate."
    }
    if ($entry.static_proof.auth_gate_file -notlike "*W68_AWS_AUTH_GATE_CONTROLNET_CANNY_STATIC_REMOTE_LOGIN_CLASSIFIED_*") {
      throw "W68 Canny static proof must select the classified W68 auth gate."
    }
    if ($entry.static_proof.readiness_gate_file -notlike "*W68_LANE_RUNTIME_READINESS_CONTROLNET_CANNY_STATIC_REMOTE_LOGIN_CLASSIFIED_*") {
      throw "W68 Canny static proof must select the classified W68 readiness gate."
    }

    $entry.workflow_smoke = [ordered]@{
      file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $WorkflowSmokePath
      result = [string]$workflowSmoke.result
      failure_category = [string]$workflowSmoke.failure_category
      execute_gates_pass = [bool]$workflowSmoke.execute_gates_pass
      ec2_started = [bool]$workflowSmoke.ec2_started
      generation_executed = [bool]$workflowSmoke.generation_executed
      run_package_valid = [bool]$workflowSmoke.run_package.valid
      run_package_lane_match = [bool]$workflowSmoke.run_package.lane_match
      smoke_request_generation_executed = [bool]$workflowSmoke.smoke_request.generation_executed
    }
    if ($entry.workflow_smoke.result -ne "blocked_before_ec2_start" -or $entry.workflow_smoke.failure_category -ne "expired_session") {
      throw "W68 Canny workflow smoke must be blocked_before_ec2_start by expired_session."
    }
    if ($entry.workflow_smoke.execute_gates_pass -or $entry.workflow_smoke.ec2_started -or $entry.workflow_smoke.generation_executed -or $entry.workflow_smoke.smoke_request_generation_executed) {
      throw "W68 Canny workflow smoke must not pass execute gates, start EC2, or run generation."
    }
    if (-not $entry.workflow_smoke.run_package_valid -or -not $entry.workflow_smoke.run_package_lane_match) {
      throw "W68 Canny workflow smoke must include a valid matching run package."
    }

    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$operationsRoot = Join-Path $ProjectRoot "Plan\Instructions\Operations"
$scriptsRoot = Join-Path $operationsRoot "Scripts"
$schemasRoot = Join-Path $operationsRoot "Schemas"
$templatesRoot = Join-Path $operationsRoot "Templates"
$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
$workflowRuntimeDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Runtime"
$tempRoot = Join-Path $env:TEMP "comfy_ui_ops_static_validation_$stamp"
$script:ValidationTempRoot = $tempRoot
$null = New-Item -ItemType Directory -Force -Path $tempRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W60_OPERATIONS_HELPER_CURRENT_VALIDATION_$stamp.json"
}

$scriptParseResults = @()
foreach ($script in Get-ChildItem -LiteralPath $scriptsRoot -Filter "*.ps1" -File | Sort-Object Name) {
  $scriptParseResults += Test-PowerShellParser -Path $script.FullName
}
$selectedInpaintRefreshScript = Join-Path $ProjectRoot "tools\Invoke-SelectedInpaintPreEC2Refresh.ps1"
$scriptParseResults += Test-PowerShellParser -Path $selectedInpaintRefreshScript
$rootProjectPreflightScript = Join-Path $ProjectRoot "tools\Test-RootProjectPreflight.ps1"
$scriptParseResults += Test-PowerShellParser -Path $rootProjectPreflightScript
$rootProjectPreflightRegressionScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-RootProjectPreflightRegression.ps1"
$scriptParseResults += Test-PowerShellParser -Path $rootProjectPreflightRegressionScript
$localComfyDevPreflightScript = Join-Path $ProjectRoot "tools\Test-LocalComfyUIDevPreflight.ps1"
$scriptParseResults += Test-PowerShellParser -Path $localComfyDevPreflightScript
$localComfyDevPreflightRegressionScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-LocalComfyUIDevPreflightRegression.ps1"
$scriptParseResults += Test-PowerShellParser -Path $localComfyDevPreflightRegressionScript
$flux2DevReadinessScript = Join-Path $ProjectRoot "tools\Test-Flux2DevLaneReadiness.ps1"
$scriptParseResults += Test-PowerShellParser -Path $flux2DevReadinessScript
$flux2DevReadinessRegressionScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-Flux2DevLaneReadinessRegression.ps1"
$scriptParseResults += Test-PowerShellParser -Path $flux2DevReadinessRegressionScript
$flux1DevWorkflowContractScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-Flux1DevWorkflowContract.ps1"
$scriptParseResults += Test-PowerShellParser -Path $flux1DevWorkflowContractScript
$runPackageDeployConsistencyScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-RunPackageDeployBundleConsistency.ps1"
$scriptParseResults += Test-PowerShellParser -Path $runPackageDeployConsistencyScript
$runPackageDeployConsistencyRegressionScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-RunPackageDeployBundleConsistencyRegression.ps1"
$scriptParseResults += Test-PowerShellParser -Path $runPackageDeployConsistencyRegressionScript
$controlNetPackageDeployConsistencyScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ControlNetSelectedLanePackageDeployConsistency.ps1"
$scriptParseResults += Test-PowerShellParser -Path $controlNetPackageDeployConsistencyScript
$controlNetAssetTransferScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ControlNetLaneAssetTransferDryRunBundle.ps1"
$scriptParseResults += Test-PowerShellParser -Path $controlNetAssetTransferScript
$controlNetPreEc2HandoffScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\New-ControlNetLanePreEC2HandoffBundle.ps1"
$scriptParseResults += Test-PowerShellParser -Path $controlNetPreEc2HandoffScript
$selectedRuntimeLocalRecheckRegressionScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-SelectedTargetRuntimeLocalRecheckLedgerRegression.ps1"
$scriptParseResults += Test-PowerShellParser -Path $selectedRuntimeLocalRecheckRegressionScript

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

$localSmokeResults = @()
$modelRecordFile = Join-Path $tempRoot "model_registry_smoke.json"
$dummyBundleDir = Join-Path $tempRoot "dummy_deploy_bundle"
$dummyBundleContentDir = Join-Path $dummyBundleDir "content"
$null = New-Item -ItemType Directory -Force -Path $dummyBundleContentDir
$dummyBundleTextFile = Join-Path $dummyBundleContentDir "dummy.txt"
Set-Content -LiteralPath $dummyBundleTextFile -Value "static validation dummy deploy bundle" -Encoding UTF8
$dummyBundleZip = Join-Path $dummyBundleDir "dummy_deploy_bundle.zip"
Compress-Archive -Path (Join-Path $dummyBundleContentDir "*") -DestinationPath $dummyBundleZip -Force
$dummyBundleHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dummyBundleZip).Hash.ToLowerInvariant()
$dummyBundleManifestFile = Join-Path $dummyBundleDir "DEPLOY_BUNDLE_MANIFEST.json"
$dummyBundleManifest = [ordered]@{
  schema_version = "1.0"
  bundle_id = "dummy_deploy_bundle"
  lane_id = "sdxl_low_risk_fallback_lane"
  bundle_zip = "dummy_deploy_bundle.zip"
  bundle_zip_sha256 = $dummyBundleHash
  result = "pass_local_only"
}
$dummyBundleManifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $dummyBundleManifestFile -Encoding UTF8

$localSmokeResults += Invoke-LocalHelper -Name "model_registry_record_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ModelRegistryRecord.ps1") `
  -Arguments @("-ModelName", "static-validation-placeholder", "-ModelType", "checkpoint", "-BaseModel", "SDXL", "-LocalPath", "C:\Comfy_UI_Main\__missing_static_validation_placeholder.safetensors") `
  -ExpectedOutputFile ""

$localSmokeResults += Invoke-LocalHelper -Name "github_checkpoint_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-GitHubCheckpoint.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-Message", "static validation dry run", "-IncludePath", "Plan,.github,PromptProfiles,Workflows,config,PROJECT_ROOT_MANIFEST.json", "-ExcludePath", "runtime_artifacts,Ref_Image_1,Ref_Image_2,Ref_Image_Canonical_Body,Reference_Images,masks,Jira,Plan.zip,_ci_w64_20260708T232900-0500", "-OutFile", (Join-Path $tempRoot "github_checkpoint_dry_run.json")) `
  -ExpectedOutputFile (Join-Path $tempRoot "github_checkpoint_dry_run.json")

$scopedGitCheckpointManifestFile = Join-Path $tempRoot "scoped_git_checkpoint_manifest.json"
$scopedGitCheckpointManifestMarkdown = Join-Path $tempRoot "scoped_git_checkpoint_manifest.md"
$localSmokeResults += Invoke-LocalHelper -Name "scoped_git_checkpoint_manifest_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ScopedGitCheckpointManifest.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-GitCheckpointDryRunFile", (Join-Path $tempRoot "github_checkpoint_dry_run.json"), "-OutFile", $scopedGitCheckpointManifestFile, "-MarkdownOutFile", $scopedGitCheckpointManifestMarkdown) `
  -ExpectedOutputFile $scopedGitCheckpointManifestFile

$postCheckpointRuntimeRevalidationPlanFile = Join-Path $tempRoot "post_checkpoint_runtime_revalidation_plan.json"
$postCheckpointRuntimeRevalidationPlanMarkdown = Join-Path $tempRoot "post_checkpoint_runtime_revalidation_plan.md"
$localSmokeResults += Invoke-LocalHelper -Name "post_checkpoint_runtime_revalidation_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-PostCheckpointRuntimeRevalidationPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-ScopedCheckpointManifestFile", $scopedGitCheckpointManifestFile, "-ManifestCheckpointDryRunFile", (Join-Path $tempRoot "github_checkpoint_dry_run.json"), "-OutFile", $postCheckpointRuntimeRevalidationPlanFile, "-MarkdownOutFile", $postCheckpointRuntimeRevalidationPlanMarkdown) `
  -ExpectedOutputFile $postCheckpointRuntimeRevalidationPlanFile

$selectedDeployBundleRebuildPlanFile = Join-Path $tempRoot "selected_deploy_bundle_rebuild_plan.json"
$selectedDeployBundleRebuildPlanMarkdown = Join-Path $tempRoot "selected_deploy_bundle_rebuild_plan.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_deploy_bundle_rebuild_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedDeployBundleRebuildPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $selectedDeployBundleRebuildPlanFile, "-MarkdownOutFile", $selectedDeployBundleRebuildPlanMarkdown) `
  -ExpectedOutputFile $selectedDeployBundleRebuildPlanFile

$publishBundleFile = Join-Path $tempRoot "publish_deploy_bundle_to_s3_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "publish_deploy_bundle_to_s3_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Publish-DeployBundleToS3.ps1") `
  -Arguments @("-BundleManifestFile", $dummyBundleManifestFile, "-S3BaseUri", "s3://example-bucket/deploy-bundles", "-OutFile", $publishBundleFile) `
  -ExpectedOutputFile $publishBundleFile

$dummyInputAssetFile = Join-Path $tempRoot "dummy_input_asset.png"
Set-Content -LiteralPath $dummyInputAssetFile -Value "static validation dummy input asset" -Encoding UTF8
$dummyInputAssetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dummyInputAssetFile).Hash.ToLowerInvariant()
$publishInputAssetFile = Join-Path $tempRoot "publish_input_asset_to_s3_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "publish_input_asset_to_s3_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Publish-InputAssetToS3.ps1") `
  -Arguments @("-AssetFile", $dummyInputAssetFile, "-S3Uri", "s3://example-bucket/model-cache/input-assets/dummy_input_asset.png", "-ExpectedSha256", $dummyInputAssetHash, "-OutFile", $publishInputAssetFile) `
  -ExpectedOutputFile $publishInputAssetFile

$dummyModelFile = Join-Path $tempRoot "dummy_model.safetensors"
Set-Content -LiteralPath $dummyModelFile -Value "static validation dummy model binary" -Encoding UTF8
$dummyModelHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dummyModelFile).Hash.ToLowerInvariant()
$publishModelFile = Join-Path $tempRoot "publish_model_to_s3_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "publish_model_to_s3_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Publish-ModelToS3.ps1") `
  -Arguments @("-ModelFile", $dummyModelFile, "-S3Uri", "s3://example-bucket/model-cache/dummy_model.safetensors", "-ExpectedSha256", $dummyModelHash, "-OutFile", $publishModelFile) `
  -ExpectedOutputFile $publishModelFile

$licensedModelInstallDryRunFile = Join-Path $tempRoot "licensed_model_install_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "licensed_model_install_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Install-LicensedModelFromHttp.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-RuntimeRequirementsFile", "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux1_dev_primary_base/runtime_requirements.json", "-DestinationModelRoot", (Join-Path $tempRoot "licensed_model_destination"), "-OutFile", $licensedModelInstallDryRunFile) `
  -ExpectedOutputFile $licensedModelInstallDryRunFile

$s3TransferReadinessFile = Join-Path $tempRoot "s3_runtime_transfer_readiness.json"
$localSmokeResults += Invoke-LocalHelper -Name "s3_runtime_transfer_readiness_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-S3RuntimeTransferReadiness.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $s3TransferReadinessFile) `
  -ExpectedOutputFile $s3TransferReadinessFile

$selectedS3PublishReadinessPlanFile = Join-Path $tempRoot "selected_s3_publish_readiness_plan.json"
$selectedS3PublishReadinessPlanMarkdown = Join-Path $tempRoot "selected_s3_publish_readiness_plan.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_s3_publish_readiness_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedS3PublishReadinessPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-SelectedDeployBundleRebuildPlanFile", $selectedDeployBundleRebuildPlanFile, "-S3RuntimeTransferReadinessFile", $s3TransferReadinessFile, "-S3BaseUri", "s3://example-bucket/deploy-bundles", "-OutFile", $selectedS3PublishReadinessPlanFile, "-MarkdownOutFile", $selectedS3PublishReadinessPlanMarkdown) `
  -ExpectedOutputFile $selectedS3PublishReadinessPlanFile

$selectedInputAssetInstallReadinessPlanFile = Join-Path $tempRoot "selected_input_asset_install_readiness_plan.json"
$selectedInputAssetInstallReadinessPlanMarkdown = Join-Path $tempRoot "selected_input_asset_install_readiness_plan.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_input_asset_install_readiness_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedInputAssetInstallReadinessPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-S3RuntimeTransferReadinessFile", $s3TransferReadinessFile, "-InputAssetS3BaseUri", "s3://example-bucket/model-cache/input-assets", "-OutFile", $selectedInputAssetInstallReadinessPlanFile, "-MarkdownOutFile", $selectedInputAssetInstallReadinessPlanMarkdown) `
  -ExpectedOutputFile $selectedInputAssetInstallReadinessPlanFile

$selectedModelCacheReadinessPlanFile = Join-Path $tempRoot "selected_model_cache_readiness_plan.json"
$selectedModelCacheReadinessPlanMarkdown = Join-Path $tempRoot "selected_model_cache_readiness_plan.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_model_cache_readiness_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedModelCacheReadinessPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-S3RuntimeTransferReadinessFile", $s3TransferReadinessFile, "-ModelCacheS3BaseUri", "s3://example-bucket/model-cache", "-OutFile", $selectedModelCacheReadinessPlanFile, "-MarkdownOutFile", $selectedModelCacheReadinessPlanMarkdown) `
  -ExpectedOutputFile $selectedModelCacheReadinessPlanFile

$selectedTargetRuntimeLiveExecutionRunbookFile = Join-Path $tempRoot "selected_target_runtime_live_execution_runbook.json"
$selectedTargetRuntimeLiveExecutionRunbookMarkdown = Join-Path $tempRoot "selected_target_runtime_live_execution_runbook.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_target_runtime_live_execution_runbook_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedTargetRuntimeLiveExecutionRunbook.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $selectedTargetRuntimeLiveExecutionRunbookFile, "-MarkdownOutFile", $selectedTargetRuntimeLiveExecutionRunbookMarkdown) `
  -ExpectedOutputFile $selectedTargetRuntimeLiveExecutionRunbookFile

$selectedTargetRuntimeExecutionReadinessSnapshotFile = Join-Path $tempRoot "selected_target_runtime_execution_readiness_snapshot.json"
$selectedTargetRuntimeExecutionReadinessSnapshotMarkdown = Join-Path $tempRoot "selected_target_runtime_execution_readiness_snapshot.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_target_runtime_execution_readiness_snapshot_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-SelectedTargetRuntimeExecutionReadinessSnapshot.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-LiveExecutionRunbookFile", $selectedTargetRuntimeLiveExecutionRunbookFile, "-OutFile", $selectedTargetRuntimeExecutionReadinessSnapshotFile, "-MarkdownOutFile", $selectedTargetRuntimeExecutionReadinessSnapshotMarkdown) `
  -ExpectedOutputFile $selectedTargetRuntimeExecutionReadinessSnapshotFile

$selectedInpaintRefreshStamp = "20990101T000000-0500"
$selectedInpaintRefreshFile = Join-Path $tempRoot "selected_inpaint_pre_ec2_refresh_orchestration.json"
$selectedInpaintRefreshMarkdown = Join-Path $tempRoot "selected_inpaint_pre_ec2_refresh_orchestration.md"
$localSmokeResults += Invoke-LocalHelper -Name "selected_inpaint_pre_ec2_refresh_orchestration_smoke" `
  -ScriptPath $selectedInpaintRefreshScript `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-SessionStamp", $selectedInpaintRefreshStamp, "-ArtifactOutputDirectory", $tempRoot, "-OutFile", $selectedInpaintRefreshFile, "-MarkdownOutFile", $selectedInpaintRefreshMarkdown) `
  -ExpectedOutputFile $selectedInpaintRefreshFile

$selectedInpaintInvalidLaneFile = Join-Path $tempRoot "selected_inpaint_pre_ec2_refresh_invalid_lane.json"
$localSmokeResults += Invoke-ExpectedFailureHelper -Name "selected_inpaint_pre_ec2_refresh_invalid_lane_rejection" `
  -ScriptPath $selectedInpaintRefreshScript `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneId", "sdxl_realvisxl_base_lane", "-SessionStamp", $selectedInpaintRefreshStamp, "-ArtifactOutputDirectory", $tempRoot, "-OutFile", $selectedInpaintInvalidLaneFile) `
  -ExpectedMessagePattern "This wrapper is scoped to sdxl_realvisxl_inpaint_detail_lane" `
  -ForbiddenOutputFile $selectedInpaintInvalidLaneFile

$s3RuntimeConfigPlanFile = Join-Path $tempRoot "s3_runtime_config_plan.json"
$s3RuntimeConfigPolicyDir = Join-Path $tempRoot "s3_runtime_config_plan_policies"
$localSmokeResults += Invoke-LocalHelper -Name "s3_runtime_config_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-S3RuntimeConfigPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-BucketName", "example-comfy-runtime-bucket", "-GitHubRoleArn", "arn:aws:iam::029530099913:role/example-github-deploy-role", "-SchedulerRoleArn", "arn:aws:iam::029530099913:role/example-scheduler-stop-role", "-RenderedPolicyDir", $s3RuntimeConfigPolicyDir, "-OutFile", $s3RuntimeConfigPlanFile) `
  -ExpectedOutputFile $s3RuntimeConfigPlanFile

$s3RuntimeInfraDryRunFile = Join-Path $tempRoot "s3_runtime_infrastructure_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "s3_runtime_infrastructure_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Initialize-S3RuntimeInfrastructure.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $s3RuntimeInfraDryRunFile) `
  -ExpectedOutputFile $s3RuntimeInfraDryRunFile

$installModelFile = Join-Path $tempRoot "install_ec2_model_from_s3_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "install_ec2_model_from_s3_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Install-EC2ModelFromS3.ps1") `
  -Arguments @("-SourceS3Uri", "s3://example-bucket/model-cache/realvisxlV50_v50Bakedvae.safetensors", "-ExpectedSha256", "6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80", "-OutFile", $installModelFile) `
  -ExpectedOutputFile $installModelFile

$emergencyStopFile = Join-Path $tempRoot "ec2_emergency_stop_schedule_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_emergency_stop_schedule_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "New-EC2EmergencyStopSchedule.ps1") `
  -Arguments @("-SchedulerRoleArn", "arn:aws:iam::029530099913:role/example-scheduler-stop-role", "-RuntimeWindowId", "validation-window", "-OutFile", $emergencyStopFile) `
  -ExpectedOutputFile $emergencyStopFile

$watchdogFile = Join-Path $tempRoot "ec2_instance_watchdog_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_instance_watchdog_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Start-EC2InstanceStopWatchdog.ps1") `
  -Arguments @("-RuntimeWindowId", "validation-window", "-OutFile", $watchdogFile) `
  -ExpectedOutputFile $watchdogFile

$runtimeWindowMarkerPlanFile = Join-Path $tempRoot "ec2_runtime_window_marker_plan.json"
$runtimeWindowMarkerTemplateFile = Join-Path $tempRoot "active_runtime_window.template.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_runtime_window_marker_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-EC2RuntimeWindowMarkerPlan.ps1") `
  -Arguments @(
    "-ProjectRoot", $ProjectRoot,
    "-WindowId", "validation-window",
    "-LaneId", "sdxl_realvisxl_base_lane",
    "-Purpose", "validation_runtime_window_marker_plan",
    "-Command", "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 25",
    "-DeployBundleS3Uri", "s3://example-bucket/deploy-bundles/example.zip",
    "-DeployBundleSha256", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "-EmergencyStopEvidencePath", $emergencyStopFile,
    "-WatchdogEvidencePath", $watchdogFile,
    "-MaxRuntimeMinutes", "60",
    "-OutFile", $runtimeWindowMarkerPlanFile,
    "-MarkerTemplateOutFile", $runtimeWindowMarkerTemplateFile
  ) `
  -ExpectedOutputFile $runtimeWindowMarkerPlanFile

$staticProofDryRunFile = Join-Path $tempRoot "ec2_lane_static_proof_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_lane_static_proof_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2LaneStaticProof.ps1") `
  -Arguments @("-OutFile", $staticProofDryRunFile) `
  -ExpectedOutputFile $staticProofDryRunFile

$comfySmokeFile = Join-Path $tempRoot "comfy_workflow_smoke_dry_run.json"
$comfySmokeRequestFile = Join-Path $tempRoot "comfy_workflow_smoke_request.json"
$localSmokeResults += Invoke-LocalHelper -Name "comfy_workflow_smoke_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-ComfyWorkflowSmoke.ps1") `
  -Arguments @("-OutFile", $comfySmokeFile, "-OutRequestFile", $comfySmokeRequestFile) `
  -ExpectedOutputFile $comfySmokeFile

$pullbackDryRunFile = Join-Path $tempRoot "ec2_pullback_record_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_pullback_record_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "New-EC2PullbackRecord.ps1") `
  -Arguments @("-DryRun", "-OutFile", $pullbackDryRunFile) `
  -ExpectedOutputFile $pullbackDryRunFile

$localSmokeResults += Invoke-PullbackManifestVerificationSmoke `
  -ScriptPath (Join-Path $scriptsRoot "New-EC2PullbackRecord.ps1") `
  -TempRoot $tempRoot

$readinessFile = Join-Path $tempRoot "lane_runtime_readiness.json"
$localSmokeResults += Invoke-LocalHelper -Name "lane_runtime_readiness_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Test-LaneRuntimeReadiness.ps1") `
  -Arguments @("-OutFile", $readinessFile) `
  -ExpectedOutputFile $readinessFile

$coordinatorFile = Join-Path $tempRoot "ec2_workflow_smoke_run_dry_run.json"
$coordinatorRequestFile = Join-Path $tempRoot "ec2_workflow_smoke_run_request.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_smoke_run_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2WorkflowSmokeRun.ps1") `
  -Arguments @("-OutFile", $coordinatorFile, "-OutRequestFile", $coordinatorRequestFile, "-ReadinessFile", $readinessFile) `
  -ExpectedOutputFile $coordinatorFile

$startFailureRegressionFile = Join-Path $tempRoot "ec2_workflow_smoke_start_failure_regression.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_smoke_start_failure_regression" `
  -ScriptPath (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-EC2WorkflowSmokeStartFailureRegression.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $startFailureRegressionFile) `
  -ExpectedOutputFile $startFailureRegressionFile

$stopFailureRegressionFile = Join-Path $tempRoot "ec2_stop_failure_regression.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_stop_failure_regression" `
  -ScriptPath (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-EC2StopFailureRegression.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $stopFailureRegressionFile) `
  -ExpectedOutputFile $stopFailureRegressionFile

$packageCoordinatorFile = Join-Path $tempRoot "ec2_workflow_smoke_run_package_dry_run.json"
$packageCoordinatorRequestFile = Join-Path $tempRoot "ec2_workflow_smoke_run_package_request.json"
$hyperrealPackageManifest = Join-Path $ProjectRoot "runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_smoke_run_package_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2WorkflowSmokeRun.ps1") `
  -Arguments @("-OutFile", $packageCoordinatorFile, "-OutRequestFile", $packageCoordinatorRequestFile, "-ReadinessFile", $readinessFile, "-RunPackageManifestFile", $hyperrealPackageManifest) `
  -ExpectedOutputFile $packageCoordinatorFile

$runtimeUnblockHandoffFile = Join-Path $tempRoot "runtime_unblock_handoff.json"
$runtimeUnblockHandoffMarkdown = Join-Path $tempRoot "runtime_unblock_handoff.md"
$localSmokeResults += Invoke-LocalHelper -Name "runtime_unblock_handoff_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-RuntimeUnblockHandoff.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $runtimeUnblockHandoffFile, "-MarkdownOutFile", $runtimeUnblockHandoffMarkdown, "-RunPackageManifestFile", $hyperrealPackageManifest) `
  -ExpectedOutputFile $runtimeUnblockHandoffFile

$latestBlockedStaticProof = Find-LatestFile -Directory $workflowStaticDir -Filter "W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_*.json"
$latestCoordinatorDryRun = Find-LatestFile -Directory $workflowRuntimeDir -Filter "W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_*.json"
$latestCoordinatorBlockedRun = Find-LatestFile -Directory $workflowRuntimeDir -Filter "W61_EC2_WORKFLOW_SMOKE_RUN_BLOCKED_EXECUTE_*.json"
$latestReadiness = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W61_LANE_RUNTIME_READINESS_*.json"
$latestAuthGate = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_AUTH_GATE*.json"
$latestCannyW68AuthGate = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W68_AWS_AUTH_GATE_CONTROLNET_CANNY_STATIC_REMOTE_LOGIN_CLASSIFIED_*.json"
$latestCannyW68Readiness = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W68_LANE_RUNTIME_READINESS_CONTROLNET_CANNY_STATIC_REMOTE_LOGIN_CLASSIFIED_*.json"
$latestCannyW68StaticProof = Find-LatestFile -Directory $workflowStaticDir -Filter "W68_EC2_STATIC_PROOF_CONTROLNET_CANNY_BLOCKED_AUTH_*.json"
$latestCannyW68WorkflowSmoke = Find-LatestFile -Directory $workflowRuntimeDir -Filter "W68_EC2_WORKFLOW_SMOKE_CONTROLNET_CANNY_BLOCKED_AUTH_*.json"

$evidenceChecks = @()
foreach ($evidence in @(
  $latestBlockedStaticProof,
  $latestCoordinatorDryRun,
  $latestCoordinatorBlockedRun,
  $latestReadiness,
  $latestCannyW68AuthGate,
  $latestCannyW68Readiness,
  $latestCannyW68StaticProof,
  $latestCannyW68WorkflowSmoke
)) {
  if ([string]::IsNullOrWhiteSpace($evidence)) { continue }
  $evidenceChecks += Test-JsonFile -Path $evidence
}

$evidenceContractChecks = @()
if (![string]::IsNullOrWhiteSpace($latestAuthGate)) {
  $evidenceContractChecks += Test-AuthGateEvidenceContract -Path $latestAuthGate
}
if (![string]::IsNullOrWhiteSpace($latestReadiness)) {
  $evidenceContractChecks += Test-LaneReadinessEvidenceContract -Path $latestReadiness
}
if (![string]::IsNullOrWhiteSpace($latestBlockedStaticProof)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestBlockedStaticProof -Kind "static_proof"
}
if (![string]::IsNullOrWhiteSpace($latestCoordinatorDryRun)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestCoordinatorDryRun -Kind "workflow_smoke"
}
if (![string]::IsNullOrWhiteSpace($latestCoordinatorBlockedRun)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestCoordinatorBlockedRun -Kind "workflow_smoke"
}
if (![string]::IsNullOrWhiteSpace($latestCannyW68AuthGate)) {
  $evidenceContractChecks += Test-AuthGateEvidenceContract -Path $latestCannyW68AuthGate
}
if (![string]::IsNullOrWhiteSpace($latestCannyW68Readiness)) {
  $evidenceContractChecks += Test-LaneReadinessEvidenceContract -Path $latestCannyW68Readiness
}
if (![string]::IsNullOrWhiteSpace($latestCannyW68StaticProof)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestCannyW68StaticProof -Kind "static_proof"
}
if (![string]::IsNullOrWhiteSpace($latestCannyW68WorkflowSmoke)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestCannyW68WorkflowSmoke -Kind "workflow_smoke"
}
if (
  ![string]::IsNullOrWhiteSpace($latestCannyW68AuthGate) -and
  ![string]::IsNullOrWhiteSpace($latestCannyW68Readiness) -and
  ![string]::IsNullOrWhiteSpace($latestCannyW68StaticProof) -and
  ![string]::IsNullOrWhiteSpace($latestCannyW68WorkflowSmoke)
) {
  $evidenceContractChecks += Test-ControlNetCannyW68GateEvidenceContract `
    -AuthGatePath $latestCannyW68AuthGate `
    -ReadinessPath $latestCannyW68Readiness `
    -StaticProofPath $latestCannyW68StaticProof `
    -WorkflowSmokePath $latestCannyW68WorkflowSmoke
}

$scriptFailures = @($scriptParseResults | Where-Object { $_.result -ne "pass" })
$jsonFailures = @($jsonParseResults | Where-Object { $_.result -ne "pass" })
$smokeFailures = @($localSmokeResults | Where-Object { $_.result -ne "pass" -or ($_.expected_output_file -and -not $_.expected_output_json_valid) })
$evidenceFailures = @($evidenceChecks | Where-Object { $_.result -ne "pass" })
$evidenceContractFailures = @($evidenceContractChecks | Where-Object { $_.result -ne "pass" })

$operationsKnownIssues = @(
  "Live AWS, Civitai, GitHub, EC2 start, ComfyUI runtime generation, artifact pullback, and visual QA remain separate runtime validations.",
  "This validation intentionally does not refresh or require AWS credentials."
)
$operationsNextAction = "If the selected lane is not already runtime-smoke proven, rerun auth gate and selected-lane readiness before EC2 static proof."
$runtimeUnblockHandoffSmoke = @($localSmokeResults | Where-Object { $_.name -eq "runtime_unblock_handoff_smoke" } | Select-Object -First 1)
if ($runtimeUnblockHandoffSmoke -and $runtimeUnblockHandoffSmoke.top_level_result -eq "handoff_runtime_smoke_qa_complete") {
  $operationsKnownIssues = @(
    "Selected lane runtime smoke, artifact pullback, and QA are complete; this local validation does not perform a new live GPU run.",
    "Completed runtime smoke proof does not certify final portfolio quality, video QA, audio QA, or full-project release completion."
  )
  $operationsNextAction = "Checkpoint completed runtime-smoke evidence and advance to the next lane, module, or deeper QA target without rerunning EC2 for this same proof."
}

$record = [ordered]@{
  evidence_id = "EVID-W60-OPERATIONS-HELPER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W60-010"
  artifact_type = "operations_helper_current_static_validation"
  tracker_ids = @("TRK-W60-010", "TRK-W61-006", "TRK-W61-007", "TRK-W66-RUNTIME-ORCHESTRATION")
  item_ids = @("W60-010", "ITEM-W61-006", "ITEM-W61-007", "ITEM-W66-RUNTIME-ORCHESTRATION")
  qa_protocol_used = @(
    "README_OPERATIONS_WAVE60.md",
    "OPERATIONAL_DONE_GATES.md",
    "SECRETS_ENV_HANDLING_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Instructions/Operations/Scripts/*.ps1",
    "Plan/Instructions/Operations/Schemas/*.json",
    "Plan/Instructions/Operations/Templates/*.json",
    "tools/Invoke-SelectedInpaintPreEC2Refresh.ps1",
    "tools/Test-RootProjectPreflight.ps1",
    "Plan/Instructions/QA/Scripts/Test-RootProjectPreflightRegression.ps1",
    "tools/Test-LocalComfyUIDevPreflight.ps1",
    "Plan/Instructions/QA/Scripts/Test-LocalComfyUIDevPreflightRegression.ps1",
    "tools/Test-Flux2DevLaneReadiness.ps1",
    "Plan/Instructions/QA/Scripts/Test-Flux2DevLaneReadinessRegression.ps1",
    "Plan/Instructions/QA/Scripts/Test-Flux1DevWorkflowContract.ps1",
    "Plan/Instructions/Operations/Scripts/Install-LicensedModelFromHttp.ps1",
    "Plan/Instructions/QA/Scripts/Test-LicensedModelInstallRegression.ps1",
    "Plan/Instructions/QA/Scripts/Test-RunPackageDeployBundleConsistency.ps1",
    "Plan/Instructions/QA/Scripts/Test-RunPackageDeployBundleConsistencyRegression.ps1",
    "Plan/Instructions/QA/Scripts/Test-SelectedTargetRuntimeLocalRecheckLedgerRegression.ps1",
    "Plan/Instructions/QA/Scripts/Test-ControlNetSelectedLanePackageDeployConsistency.ps1",
    "Plan/Instructions/QA/Scripts/Test-ControlNetLaneAssetTransferDryRunBundle.ps1",
    "Plan/Instructions/QA/Scripts/Test-EC2WorkflowSmokeStartFailureRegression.ps1",
    "Plan/Instructions/QA/Scripts/Test-EC2StopFailureRegression.ps1",
    "Plan/Instructions/QA/Scripts/New-ControlNetLanePreEC2HandoffBundle.ps1",
    "latest selected-lane runtime gate evidence",
    "runtime unblock handoff smoke"
  )
  validation_results = [ordered]@{
    script_count = @($scriptParseResults).Count
    script_parse_failures = @($scriptFailures).Count
    script_parse_results = $scriptParseResults
    json_file_count = @($jsonParseResults).Count
    json_parse_failures = @($jsonFailures).Count
    json_parse_results = $jsonParseResults
    local_smoke_count = @($localSmokeResults).Count
    local_smoke_failures = @($smokeFailures).Count
    local_smoke_results = $localSmokeResults
    evidence_check_count = @($evidenceChecks).Count
    evidence_check_failures = @($evidenceFailures).Count
    evidence_checks = $evidenceChecks
    evidence_contract_check_count = @($evidenceContractChecks).Count
    evidence_contract_check_failures = @($evidenceContractFailures).Count
    evidence_contract_checks = $evidenceContractChecks
  }
  skipped_live_execution = @(
    [ordered]@{ script = "Invoke-CivitaiModelLookup.ps1"; reason = "Would contact Civitai API; out of scope for local static validation." },
    [ordered]@{ script = "Start-ComfyUIGpuServer.ps1"; reason = "Could start EC2/cost resources; out of scope for local static validation." },
    [ordered]@{ script = "Stop-ComfyUIGpuServer.ps1"; reason = "Would contact AWS; out of scope for local static validation." },
    [ordered]@{ script = "Test-AwsAuthGate.ps1"; reason = "Would contact AWS login/STS; existing auth evidence is inspected instead." },
    [ordered]@{ script = "Test-AwsProfileAuthMatrix.ps1"; reason = "Would contact AWS STS for every configured profile; out of scope for local static validation." },
    [ordered]@{ script = "Test-AwsComfyGpuIdentity.ps1"; reason = "Would contact AWS; out of scope for local static validation." }
  )
  temp_root = "[VALIDATION_TEMP_ROOT]"
  temp_root_redacted = $true
  result = $(if ($scriptFailures.Count -eq 0 -and $jsonFailures.Count -eq 0 -and $smokeFailures.Count -eq 0 -and $evidenceFailures.Count -eq 0 -and $evidenceContractFailures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_issues = $operationsKnownIssues
  next_action = $operationsNextAction
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote operations helper static validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
