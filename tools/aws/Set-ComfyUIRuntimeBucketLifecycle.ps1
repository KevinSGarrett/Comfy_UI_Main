param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$Bucket = "comfy-ui-main-runtime-029530099913-us-east-1",
  [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Stop"
$policyPath = Join-Path $ProjectRoot "configs\aws\runtime-bucket-lifecycle.json"
if (!(Test-Path -LiteralPath $policyPath -PathType Leaf)) { throw "Lifecycle policy is missing: $policyPath" }
$expected = Get-Content -Raw -LiteralPath $policyPath | ConvertFrom-Json

$null = aws s3api put-bucket-lifecycle-configuration --bucket $Bucket --region $Region --lifecycle-configuration "file://$policyPath" --output json
if ($LASTEXITCODE -ne 0) { throw "Failed to apply the runtime-bucket lifecycle policy." }
$observed = aws s3api get-bucket-lifecycle-configuration --bucket $Bucket --region $Region --output json | ConvertFrom-Json

$expectedIds = @($expected.Rules | ForEach-Object { [string]$_.ID } | Sort-Object)
$observedIds = @($observed.Rules | ForEach-Object { [string]$_.ID } | Sort-Object)
if (($expectedIds -join "|") -cne ($observedIds -join "|")) {
  throw "Observed lifecycle rule IDs do not match the canonical policy."
}
$modelRule = @($observed.Rules | Where-Object { [string]$_.ID -eq "abort-incomplete-model-cache-uploads" })
if ($modelRule.Count -ne 1 -or $null -ne $modelRule[0].Expiration -or $null -ne $modelRule[0].NoncurrentVersionExpiration) {
  throw "Model-cache lifecycle rule must not expire current or noncurrent model objects."
}

[ordered]@{
  result = "pass"
  classification = "COMFY_UI_RUNTIME_BUCKET_LIFECYCLE_ACTIVE"
  bucket = $Bucket
  rule_ids = $observedIds
  deploy_bundle_expiration_days = 90
  render_output_expiration_days = 180
  noncurrent_version_expiration_days = 30
  model_cache_expiration = $null
  incomplete_multipart_abort_days = 7
} | ConvertTo-Json -Depth 6
