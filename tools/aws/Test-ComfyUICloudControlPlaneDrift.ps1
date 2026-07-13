param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RuntimeProjectRoot = "C:\Comfy_UI_Main",
  [string]$Repository = "KevinSGarrett/Comfy_UI_Main",
  [string]$Region = "us-east-1",
  [string]$AccountId = "029530099913",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Bucket = "comfy-ui-main-runtime-029530099913-us-east-1"
)

$ErrorActionPreference = "Stop"
$checks = New-Object System.Collections.Generic.List[object]
function Add-Check([string]$Name, [bool]$Passed, $Expected, $Observed, [string]$Severity = "error") {
  $checks.Add([ordered]@{
    name = $Name
    result = if ($Passed) { "pass" } else { "fail" }
    severity = $Severity
    expected = $Expected
    observed = $Observed
  })
}

function ConvertTo-CanonicalNode($Value) {
  if ($null -eq $Value) { return $null }
  if ($Value -is [System.Management.Automation.PSCustomObject]) {
    $ordered = [ordered]@{}
    foreach ($property in @($Value.PSObject.Properties | Sort-Object Name)) {
      $ordered[$property.Name] = ConvertTo-CanonicalNode $property.Value
    }
    return [pscustomobject]$ordered
  }
  if ($Value -is [System.Collections.IDictionary]) {
    $ordered = [ordered]@{}
    foreach ($key in @($Value.Keys | Sort-Object)) {
      $ordered[[string]$key] = ConvertTo-CanonicalNode $Value[$key]
    }
    return [pscustomobject]$ordered
  }
  if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
    return @($Value | ForEach-Object { ConvertTo-CanonicalNode $_ })
  }
  return $Value
}

function Get-CanonicalJson($Value) {
  return (ConvertTo-CanonicalNode $Value | ConvertTo-Json -Depth 30 -Compress)
}

function Read-CanonicalJson([string]$RelativePath) {
  $path = Join-Path $ProjectRoot $RelativePath
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Canonical cloud policy is missing: $path" }
  return (Get-Content -Raw -LiteralPath $path | ConvertFrom-Json)
}

$identity = aws sts get-caller-identity --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Routine AWS identity is unavailable." }
$expectedCaller = "arn:aws:sts::${AccountId}:assumed-role/ComfyUIMainSessionRole/comfy-ui-main-session"
Add-Check "routine_identity_is_scoped_role" ([string]$identity.Arn -eq $expectedCaller) $expectedCaller $identity.Arn

$mainTrustCanonical = Read-CanonicalJson "configs\aws\comfy-ui-main-session-role-trust-policy.json"
$mainPolicyCanonical = Read-CanonicalJson "configs\aws\comfy-ui-main-session-role-policy.json"
$githubTrustCanonical = Read-CanonicalJson "configs\aws\github-actions-oidc-trust-policy.json"
$githubPolicyCanonical = Read-CanonicalJson "configs\aws\github-actions-deploy-bundle-publisher-policy.json"
$lifecycleCanonical = Read-CanonicalJson "configs\aws\runtime-bucket-lifecycle.json"

$mainRole = aws iam get-role --role-name ComfyUIMainSessionRole --output json | ConvertFrom-Json
$mainPolicy = aws iam get-role-policy --role-name ComfyUIMainSessionRole --policy-name ComfyUIMainSessionScopedRuntimeAccess --output json | ConvertFrom-Json
$githubRole = aws iam get-role --role-name ComfyUIGitHubDeployBundlePublisherRole --output json | ConvertFrom-Json
$githubPolicy = aws iam get-role-policy --role-name ComfyUIGitHubDeployBundlePublisherRole --policy-name PublishComfyUIDeployBundlesOnly --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Unable to read the project IAM roles and inline policies." }

Add-Check "main_role_trust_matches_canonical" ((Get-CanonicalJson $mainRole.Role.AssumeRolePolicyDocument) -ceq (Get-CanonicalJson $mainTrustCanonical)) "canonical" "live"
Add-Check "main_role_policy_matches_canonical" ((Get-CanonicalJson $mainPolicy.PolicyDocument) -ceq (Get-CanonicalJson $mainPolicyCanonical)) "canonical" "live"
Add-Check "github_role_trust_matches_canonical" ((Get-CanonicalJson $githubRole.Role.AssumeRolePolicyDocument) -ceq (Get-CanonicalJson $githubTrustCanonical)) "canonical" "live"
Add-Check "github_role_policy_matches_canonical" ((Get-CanonicalJson $githubPolicy.PolicyDocument) -ceq (Get-CanonicalJson $githubPolicyCanonical)) "canonical" "live"

$providerArn = "arn:aws:iam::${AccountId}:oidc-provider/token.actions.githubusercontent.com"
$providerRaw = aws iam get-open-id-connect-provider --open-id-connect-provider-arn $providerArn --output json
if ($LASTEXITCODE -ne 0) { throw "Unable to read the GitHub OIDC provider." }
$provider = $providerRaw | ConvertFrom-Json
Add-Check "github_oidc_audience_present" (@($provider.ClientIDList) -contains "sts.amazonaws.com") "sts.amazonaws.com" (@($provider.ClientIDList) -join ",")

$variablesRaw = gh variable list --repo $Repository --json name,value
if ($LASTEXITCODE -ne 0) { throw "Unable to read GitHub repository variables." }
$variablesParsed = $variablesRaw | ConvertFrom-Json
$variables = @($variablesParsed)
$variableMap = @{}
foreach ($variable in $variables) { $variableMap[[string]$variable.name] = [string]$variable.value }
Add-Check "github_region_variable" ($variableMap.AWS_REGION -eq $Region) $Region $variableMap.AWS_REGION
Add-Check "github_role_variable" ($variableMap.AWS_ROLE_TO_ASSUME -eq "arn:aws:iam::${AccountId}:role/ComfyUIGitHubDeployBundlePublisherRole") "arn:aws:iam::${AccountId}:role/ComfyUIGitHubDeployBundlePublisherRole" $variableMap.AWS_ROLE_TO_ASSUME
Add-Check "github_s3_variable" ($variableMap.COMFY_DEPLOY_BUNDLE_S3_URI -eq "s3://$Bucket/deploy-bundles/github") "s3://$Bucket/deploy-bundles/github" $variableMap.COMFY_DEPLOY_BUNDLE_S3_URI

$lifecycleLive = aws s3api get-bucket-lifecycle-configuration --bucket $Bucket --output json | ConvertFrom-Json
$canonicalRules = @($lifecycleCanonical.Rules | Sort-Object ID)
$liveRules = @($lifecycleLive.Rules | Sort-Object ID)
Add-Check "runtime_bucket_lifecycle_matches_canonical" ((Get-CanonicalJson $liveRules) -ceq (Get-CanonicalJson $canonicalRules)) "canonical rules" "live rules"

$instance = aws ec2 describe-instances --region $Region --instance-ids $InstanceId --output json --query 'Reservations[0].Instances[0]' | ConvertFrom-Json
$volumeId = [string](@($instance.BlockDeviceMappings | Where-Object { [string]$_.DeviceName -eq [string]$instance.RootDeviceName })[0].Ebs.VolumeId)
$volume = aws ec2 describe-volumes --region $Region --volume-ids $volumeId --output json --query 'Volumes[0]' | ConvertFrom-Json
Add-Check "approved_instance_stopped" ([string]$instance.State.Name -eq "stopped") "stopped" $instance.State.Name
$marker = Join-Path $RuntimeProjectRoot "runtime_artifacts\ec2_runtime_windows\ACTIVE_EC2_RUNTIME_WINDOW.json"
Add-Check "no_active_marker_while_stopped" (!(Test-Path -LiteralPath $marker)) $false (Test-Path -LiteralPath $marker)

$failed = @($checks | Where-Object { [string]$_.result -eq "fail" -and [string]$_.severity -eq "error" })
$record = [ordered]@{
  result = if ($failed.Count -eq 0) { "pass_with_known_ebs_blocker" } else { "fail" }
  classification = if ($failed.Count -eq 0) { "COMFYUI_CLOUD_CONTROL_PLANE_NO_DRIFT" } else { "COMFYUI_CLOUD_CONTROL_PLANE_DRIFT" }
  check_count = $checks.Count
  failed_check_count = $failed.Count
  checks = $checks
  instance = [ordered]@{
    instance_id = $InstanceId
    state = [string]$instance.State.Name
    volume_id = $volumeId
  }
  ebs_followup = [ordered]@{
    classification = if (![bool]$volume.Encrypted -or [int]$volume.Size -eq 1024) { "BLOCKED_EBS_USED_BYTES_PROOF_MISSING" } else { "EBS_ENCRYPTED_RIGHT_SIZING_COMPLETE" }
    size_gib = [int]$volume.Size
    volume_type = [string]$volume.VolumeType
    encrypted = [bool]$volume.Encrypted
    mutation_authorized = $false
  }
  aws_mutation_performed = $false
  github_mutation_performed = $false
}
$record | ConvertTo-Json -Depth 12
if ($failed.Count -gt 0) { throw "ComfyUI cloud control-plane drift detected." }
