param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$Repository = "KevinSGarrett/Comfy_UI_Main",
  [string]$RulesetName = "Protect main with required preflight",
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
  throw "Repository must use owner/name form."
}

$payloadPath = Join-Path $ProjectRoot "configs\github\main-protection-ruleset.json"
if (!(Test-Path -LiteralPath $payloadPath -PathType Leaf)) {
  throw "Canonical GitHub ruleset payload is missing: $payloadPath"
}
$payload = Get-Content -Raw -LiteralPath $payloadPath | ConvertFrom-Json
if ([string]$payload.name -ne $RulesetName -or [string]$payload.target -ne "branch") {
  throw "Canonical payload does not match the requested branch ruleset."
}

$rulesetsRaw = gh api "repos/$Repository/rulesets"
if ($LASTEXITCODE -ne 0) { throw "Unable to list repository rulesets." }
$rulesetsParsed = $rulesetsRaw | ConvertFrom-Json
$rulesets = @($rulesetsParsed)
$matches = @($rulesets | Where-Object { [string]$_.name -eq $RulesetName })
if ($matches.Count -gt 1) { throw "More than one ruleset has the canonical name." }

$operation = if ($matches.Count -eq 1) { "update" } else { "create" }
if (!$Apply) {
  [ordered]@{
    result = "planned"
    classification = "GITHUB_MAIN_PROTECTION_RULESET_APPLY_REQUIRED"
    repository = $Repository
    operation = $operation
    ruleset_id = if ($matches.Count -eq 1) { [int64]$matches[0].id } else { $null }
    payload_path = $payloadPath
    mutation_performed = $false
  } | ConvertTo-Json -Depth 5
  return
}

$tempPath = Join-Path $env:TEMP ("comfy_main_ruleset_" + [guid]::NewGuid().ToString("N") + ".json")
try {
  [System.IO.File]::WriteAllText(
    $tempPath,
    ($payload | ConvertTo-Json -Depth 20),
    [System.Text.UTF8Encoding]::new($false)
  )
  if ($operation -eq "update") {
    $response = gh api --method PUT "repos/$Repository/rulesets/$([int64]$matches[0].id)" --input $tempPath | ConvertFrom-Json
  } else {
    $response = gh api --method POST "repos/$Repository/rulesets" --input $tempPath | ConvertFrom-Json
  }
  if ($LASTEXITCODE -ne 0) { throw "GitHub ruleset mutation failed." }
} finally {
  if (Test-Path -LiteralPath $tempPath) { Remove-Item -LiteralPath $tempPath -Force }
}

if ([string]$response.enforcement -ne "active" -or
    @($response.bypass_actors).Count -ne 0 -or
    [string]$response.current_user_can_bypass -ne "never") {
  throw "GitHub accepted the ruleset but its no-bypass enforcement is not active."
}

[ordered]@{
  result = "pass"
  classification = "GITHUB_MAIN_PROTECTION_RULESET_ACTIVE_NO_BYPASS"
  repository = $Repository
  operation = $operation
  ruleset_id = [int64]$response.id
  required_check = "Required preflight and package"
  pull_request_required = $true
  owner_bypass_allowed = $false
  mutation_performed = $true
} | ConvertTo-Json -Depth 5
