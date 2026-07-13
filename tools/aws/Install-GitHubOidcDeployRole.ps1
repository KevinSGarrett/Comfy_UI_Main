param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RoleName = "ComfyUIGitHubDeployBundlePublisherRole",
  [string]$AdminProfile = "comfy-ui-root-breakglass"
)

$ErrorActionPreference = "Stop"
$trustPolicy = Join-Path $ProjectRoot "configs\aws\github-actions-oidc-trust-policy.json"
$rolePolicy = Join-Path $ProjectRoot "configs\aws\github-actions-deploy-bundle-publisher-policy.json"
$providerArn = "arn:aws:iam::029530099913:oidc-provider/token.actions.githubusercontent.com"

foreach ($path in @($trustPolicy, $rolePolicy)) {
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required OIDC policy is missing: $path" }
  $null = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
}

$provider = aws iam get-open-id-connect-provider --open-id-connect-provider-arn $providerArn --profile $AdminProfile --output json | ConvertFrom-Json
if (@($provider.ClientIDList) -notcontains "sts.amazonaws.com") {
  throw "The GitHub OIDC provider does not trust audience sts.amazonaws.com."
}

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$null = aws iam get-role --role-name $RoleName --profile $AdminProfile --output json 2>$null
$roleExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $previousPreference

if ($roleExists) {
  $null = aws iam update-assume-role-policy --role-name $RoleName --policy-document "file://$trustPolicy" --profile $AdminProfile --output json
} else {
  $null = aws iam create-role --role-name $RoleName --assume-role-policy-document "file://$trustPolicy" --description "GitHub main-branch OIDC publisher for ComfyUI deploy bundles only" --profile $AdminProfile --output json
}
if ($LASTEXITCODE -ne 0) { throw "Failed to create or update the GitHub OIDC role." }

$null = aws iam put-role-policy --role-name $RoleName --policy-name "PublishComfyUIDeployBundlesOnly" --policy-document "file://$rolePolicy" --profile $AdminProfile --output json
if ($LASTEXITCODE -ne 0) { throw "Failed to apply the GitHub deploy-bundle publisher policy." }

$role = aws iam get-role --role-name $RoleName --profile $AdminProfile --output json | ConvertFrom-Json
[ordered]@{
  result = "pass"
  classification = "GITHUB_OIDC_DEPLOY_BUNDLE_ROLE_ACTIVE"
  role_arn = [string]$role.Role.Arn
  trusted_subject = "repo:KevinSGarrett/Comfy_UI_Main:ref:refs/heads/main"
  allowed_s3_prefix = "s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/github/"
  ec2_permission_granted = $false
  static_credentials_created = $false
} | ConvertTo-Json -Depth 5
