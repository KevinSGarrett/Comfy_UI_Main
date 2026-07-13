param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$Repository = "KevinSGarrett/Comfy_UI_Main",
  [string]$RulesetName = "Protect main with required preflight"
)

$ErrorActionPreference = "Stop"
if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
  throw "Repository must use owner/name form."
}

$payloadPath = Join-Path $ProjectRoot "configs\github\main-protection-ruleset.json"
if (!(Test-Path -LiteralPath $payloadPath -PathType Leaf)) {
  throw "Canonical GitHub ruleset payload is missing: $payloadPath"
}
$canonical = Get-Content -Raw -LiteralPath $payloadPath | ConvertFrom-Json
$canonicalHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $payloadPath).Hash.ToLowerInvariant()

$rulesetsRaw = gh api "repos/$Repository/rulesets"
if ($LASTEXITCODE -ne 0) { throw "Unable to list repository rulesets." }
$rulesetsParsed = $rulesetsRaw | ConvertFrom-Json
$rulesets = @($rulesetsParsed)
$matches = @($rulesets | Where-Object { [string]$_.name -eq $RulesetName })
$checks = New-Object System.Collections.Generic.List[object]
function Add-Check([string]$Name, [bool]$Passed, $Expected, $Observed) {
  $checks.Add([ordered]@{
    name = $Name
    result = if ($Passed) { "pass" } else { "fail" }
    expected = $Expected
    observed = $Observed
  })
}

Add-Check "single_named_ruleset" ($matches.Count -eq 1) 1 $matches.Count
if ($matches.Count -eq 1) {
  $live = gh api "repos/$Repository/rulesets/$([int64]$matches[0].id)" | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0) { throw "Unable to read the live repository ruleset." }

  Add-Check "target_matches" ([string]$live.target -eq [string]$canonical.target) $canonical.target $live.target
  Add-Check "enforcement_active" ([string]$live.enforcement -eq "active") "active" $live.enforcement
  Add-Check "no_bypass_actors" (@($live.bypass_actors).Count -eq 0) 0 @($live.bypass_actors).Count
  Add-Check "current_user_cannot_bypass" ([string]$live.current_user_can_bypass -eq "never") "never" $live.current_user_can_bypass
  Add-Check "default_branch_included" (@($live.conditions.ref_name.include) -contains "~DEFAULT_BRANCH") "~DEFAULT_BRANCH" (@($live.conditions.ref_name.include) -join ",")
  Add-Check "no_ref_exclusions" (@($live.conditions.ref_name.exclude).Count -eq 0) 0 @($live.conditions.ref_name.exclude).Count

  $ruleTypes = @($live.rules | ForEach-Object { [string]$_.type })
  $expectedRuleTypes = @($canonical.rules | ForEach-Object { [string]$_.type })
  $ruleTypeSignature = (@($ruleTypes | Sort-Object) -join ",")
  $expectedRuleTypeSignature = (@($expectedRuleTypes | Sort-Object) -join ",")
  Add-Check "exact_rule_types" ($ruleTypeSignature -ceq $expectedRuleTypeSignature) $expectedRuleTypeSignature $ruleTypeSignature
  Add-Check "deletion_protected" ($ruleTypes -contains "deletion") $true ($ruleTypes -contains "deletion")
  Add-Check "non_fast_forward_protected" ($ruleTypes -contains "non_fast_forward") $true ($ruleTypes -contains "non_fast_forward")

  $pullRequestRules = @($live.rules | Where-Object { [string]$_.type -eq "pull_request" })
  Add-Check "single_pull_request_rule" ($pullRequestRules.Count -eq 1) 1 $pullRequestRules.Count
  if ($pullRequestRules.Count -eq 1) {
    $parameters = $pullRequestRules[0].parameters
    Add-Check "zero_external_approvals" ([int]$parameters.required_approving_review_count -eq 0) 0 $parameters.required_approving_review_count
    Add-Check "review_threads_resolved" ([bool]$parameters.required_review_thread_resolution) $true $parameters.required_review_thread_resolution
    Add-Check "no_last_push_approval" (![bool]$parameters.require_last_push_approval) $false $parameters.require_last_push_approval
    Add-Check "stale_review_dismissal_not_required" (![bool]$parameters.dismiss_stale_reviews_on_push) $false $parameters.dismiss_stale_reviews_on_push
    Add-Check "code_owner_review_not_required" (![bool]$parameters.require_code_owner_review) $false $parameters.require_code_owner_review
    $allowedMethods = @($parameters.allowed_merge_methods | ForEach-Object { [string]$_ } | Sort-Object)
    Add-Check "exact_allowed_merge_methods" (($allowedMethods -join ",") -ceq "merge,rebase,squash") "merge,rebase,squash" ($allowedMethods -join ",")
  }

  $statusRules = @($live.rules | Where-Object { [string]$_.type -eq "required_status_checks" })
  Add-Check "single_required_status_rule" ($statusRules.Count -eq 1) 1 $statusRules.Count
  if ($statusRules.Count -eq 1) {
    $contexts = @($statusRules[0].parameters.required_status_checks | ForEach-Object { [string]$_.context })
    Add-Check "exact_required_check" ($contexts.Count -eq 1 -and $contexts[0] -eq "Required preflight and package") "Required preflight and package" ($contexts -join ",")
    Add-Check "strict_status_policy" ([bool]$statusRules[0].parameters.strict_required_status_checks_policy) $true $statusRules[0].parameters.strict_required_status_checks_policy
    Add-Check "status_not_enforced_on_branch_create" ([bool]$statusRules[0].parameters.do_not_enforce_on_create) $true $statusRules[0].parameters.do_not_enforce_on_create
  }
}

$failed = @($checks | Where-Object { [string]$_.result -eq "fail" })
$record = [ordered]@{
  result = if ($failed.Count -eq 0) { "pass" } else { "fail" }
  classification = if ($failed.Count -eq 0) { "GITHUB_MAIN_PROTECTION_RULESET_NO_DRIFT" } else { "GITHUB_MAIN_PROTECTION_RULESET_DRIFT" }
  repository = $Repository
  canonical_payload = $payloadPath
  canonical_sha256 = $canonicalHash
  check_count = $checks.Count
  failed_check_count = $failed.Count
  checks = $checks
  mutation_performed = $false
}
$record | ConvertTo-Json -Depth 10
if ($failed.Count -gt 0) { throw "GitHub main-protection ruleset drift detected." }
