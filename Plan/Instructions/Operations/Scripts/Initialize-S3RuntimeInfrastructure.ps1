<#
.SYNOPSIS
Initializes S3/IAM runtime transfer infrastructure for ComfyUI.

.DESCRIPTION
Dry-run by default. With -Execute, idempotently creates or updates the runtime
S3 bucket, EC2 runtime S3 inline policy, GitHub deploy role, and EventBridge
Scheduler stop role. This never starts EC2 and never prints secret values. With
-UpdateEnv, only non-secret S3/IAM configuration keys are updated in .env.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$BucketName = "comfy-ui-main-runtime-029530099913-us-east-1",
  [string]$DeployBundlePrefix = "deploy-bundles",
  [string]$ModelCachePrefix = "model-cache",
  [string]$ArtifactPrefix = "render-outputs",
  [string]$ManifestPrefix = "manifests",
  [string]$AccountId = "029530099913",
  [string]$Region = "us-east-1",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Ec2RuntimeRoleName = "ComfyUI-SSM-Role",
  [string]$GitHubDeployRoleName = "ComfyUIGitHubDeployBundleRole",
  [string]$SchedulerStopRoleName = "ComfyUIEmergencyStopSchedulerRole",
  [string]$GitHubOwner = "KevinSGarrett",
  [string]$GitHubRepo = "Comfy_UI_Main",
  [string]$EnvFile = "",
  [string]$OutFile = "",
  [switch]$Execute,
  [switch]$UpdateEnv
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 30
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Write-TextNoBom {
  param(
    [Parameter(Mandatory=$true)][string]$Value,
    [Parameter(Mandatory=$true)][string]$Path
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Value, $encoding)
}

function Read-JsonText {
  param([Parameter(Mandatory=$true)][string]$Path)
  return Get-Content -LiteralPath $Path -Raw
}

function ConvertTo-RenderedTemplateText {
  param(
    [Parameter(Mandatory=$true)][string]$TemplatePath,
    [Parameter(Mandatory=$true)][hashtable]$Values
  )

  $text = Read-JsonText -Path $TemplatePath
  foreach ($key in $Values.Keys) {
    $text = $text.Replace($key, [string]$Values[$key])
  }
  $null = $text | ConvertFrom-Json
  $remaining = @([regex]::Matches($text, '<[^>]+>') | ForEach-Object { $_.Value } | Sort-Object -Unique)
  if (@($remaining).Count -gt 0) {
    throw "Rendered template still contains placeholders: $($remaining -join ', ')"
  }
  return $text
}

function Invoke-AwsJson {
  param([Parameter(Mandatory=$true)][string[]]$Arguments)
  $oldErrorActionPreference = $ErrorActionPreference
  $oldNativePreference = $null
  $hasNativePreference = Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue
  if ($hasNativePreference) {
    $oldNativePreference = $global:PSNativeCommandUseErrorActionPreference
    $global:PSNativeCommandUseErrorActionPreference = $false
  }
  try {
    $ErrorActionPreference = "Continue"
    $output = & aws @Arguments 2>&1
    $exit = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $oldErrorActionPreference
    if ($hasNativePreference) {
      $global:PSNativeCommandUseErrorActionPreference = $oldNativePreference
    }
  }
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  return [ordered]@{
    exit_code = $exit
    text = $text
  }
}

function Get-AwsRoleArn {
  param([Parameter(Mandatory=$true)][string]$RoleName)
  return "arn:aws:iam::${AccountId}:role/$RoleName"
}

function Update-EnvValues {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][hashtable]$Values
  )

  $lines = @()
  if (Test-Path -LiteralPath $Path) {
    $lines = @(Get-Content -LiteralPath $Path)
  }
  foreach ($key in $Values.Keys) {
    $value = [string]$Values[$key]
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
      if ($lines[$i] -match "^\s*$([regex]::Escape($key))\s*=") {
        $lines[$i] = "$key=$value"
        $found = $true
      }
    }
    if (!$found) {
      $lines += "$key=$value"
    }
  }
  Write-TextNoBom -Value (($lines -join "`r`n") + "`r`n") -Path $Path
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root missing: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($EnvFile)) {
  $EnvFile = Join-Path $ProjectRoot ".env"
}

$templateRoot = Join-Path $ProjectRoot "configs\aws"
$policyValues = @{
  "<bucket-name>" = $BucketName
  "<deploy-bundle-prefix>" = $DeployBundlePrefix.Trim("/")
  "<model-cache-prefix>" = $ModelCachePrefix.Trim("/")
  "<artifact-prefix>" = $ArtifactPrefix.Trim("/")
  "<account-id>" = $AccountId
  "<region>" = $Region
  "<instance-id>" = $InstanceId
  "<github-owner>" = $GitHubOwner
  "<github-repo>" = $GitHubRepo
}

$ec2RuntimePolicy = ConvertTo-RenderedTemplateText -TemplatePath (Join-Path $templateRoot "ec2-runtime-s3-policy.template.json") -Values $policyValues
$githubDeployPolicy = ConvertTo-RenderedTemplateText -TemplatePath (Join-Path $templateRoot "github-actions-oidc-deploy-bundle-policy.template.json") -Values $policyValues
$githubTrustPolicy = ConvertTo-RenderedTemplateText -TemplatePath (Join-Path $templateRoot "github-actions-oidc-trust-policy.template.json") -Values $policyValues
$schedulerPolicy = ConvertTo-RenderedTemplateText -TemplatePath (Join-Path $templateRoot "eventbridge-scheduler-stop-role-policy.template.json") -Values $policyValues
$schedulerTrustPolicy = ConvertTo-RenderedTemplateText -TemplatePath (Join-Path $templateRoot "eventbridge-scheduler-stop-role-trust-policy.template.json") -Values $policyValues

$githubRoleArn = Get-AwsRoleArn -RoleName $GitHubDeployRoleName
$schedulerRoleArn = Get-AwsRoleArn -RoleName $SchedulerStopRoleName
$deployBundleUri = "s3://$BucketName/$($DeployBundlePrefix.Trim('/'))"
$modelCacheUri = "s3://$BucketName/$($ModelCachePrefix.Trim('/'))"
$artifactUri = "s3://$BucketName/$($ArtifactPrefix.Trim('/'))"
$manifestUri = "s3://$BucketName/$($ManifestPrefix.Trim('/'))"

$record = [ordered]@{
  schema_version = "1.0"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "initialize_s3_runtime_infrastructure"
  local_only = !$Execute
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  secrets_printed = $false
  account_id = $AccountId
  region = $Region
  project_root = $ProjectRoot
  bucket_name = $BucketName
  prefixes = [ordered]@{
    deploy_bundle = $DeployBundlePrefix.Trim("/")
    model_cache = $ModelCachePrefix.Trim("/")
    artifact = $ArtifactPrefix.Trim("/")
    manifest = $ManifestPrefix.Trim("/")
  }
  roles = [ordered]@{
    ec2_runtime_role = $Ec2RuntimeRoleName
    github_deploy_role = $GitHubDeployRoleName
    github_deploy_role_arn = $githubRoleArn
    scheduler_stop_role = $SchedulerStopRoleName
    scheduler_stop_role_arn = $schedulerRoleArn
  }
  s3_uris = [ordered]@{
    deploy_bundle = $deployBundleUri
    model_cache = $modelCacheUri
    artifact = $artifactUri
    manifest = $manifestUri
  }
  actions = @()
  env_update = [ordered]@{
    requested = [bool]$UpdateEnv
    attempted = $false
    file = $EnvFile
    keys = @(
      "COMFY_DEPLOY_BUNDLE_S3_URI",
      "S3_MODEL_BUCKET",
      "S3_MODEL_PREFIX",
      "S3_RENDER_OUTPUT_PREFIX",
      "S3_MANIFEST_PREFIX",
      "AWS_ROLE_TO_ASSUME",
      "COMFY_SCHEDULER_STOP_ROLE_ARN"
    )
  }
  result = "dry_run_ready"
  failure_category = $null
  errors = @()
  next_action = "Run with -Execute to create/update AWS S3/IAM resources, then rerun S3 runtime transfer readiness."
}

function Add-Action {
  param(
    [string]$Name,
    [string]$Result,
    [string]$Detail = ""
  )
  $script:record.actions += [ordered]@{
    name = $Name
    result = $Result
    detail = $Detail
  }
}

if ($Execute) {
  $record.local_only = $false
  $record.aws_contacted = $true
  try {
    $identity = Invoke-AwsJson -Arguments @("sts", "get-caller-identity", "--output", "json")
    if ($identity.exit_code -ne 0) { throw "sts get-caller-identity failed: $($identity.text)" }
    $identityJson = $identity.text | ConvertFrom-Json
    if ([string]$identityJson.Account -ne $AccountId) {
      throw "Unexpected AWS account. expected=$AccountId observed=$($identityJson.Account)"
    }
    Add-Action -Name "aws_identity" -Result "pass" -Detail "account_match"

    $headBucket = Invoke-AwsJson -Arguments @("s3api", "head-bucket", "--bucket", $BucketName)
    if ($headBucket.exit_code -eq 0) {
      Add-Action -Name "s3_bucket" -Result "exists" -Detail $BucketName
    } else {
      if ($Region -eq "us-east-1") {
        $createBucket = Invoke-AwsJson -Arguments @("s3api", "create-bucket", "--bucket", $BucketName, "--region", $Region)
      } else {
        $createBucket = Invoke-AwsJson -Arguments @("s3api", "create-bucket", "--bucket", $BucketName, "--region", $Region, "--create-bucket-configuration", "LocationConstraint=$Region")
      }
      if ($createBucket.exit_code -ne 0) { throw "create-bucket failed: $($createBucket.text)" }
      Add-Action -Name "s3_bucket" -Result "created" -Detail $BucketName
    }

    $publicAccess = Invoke-AwsJson -Arguments @("s3api", "put-public-access-block", "--bucket", $BucketName, "--public-access-block-configuration", "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true")
    if ($publicAccess.exit_code -ne 0) { throw "put-public-access-block failed: $($publicAccess.text)" }
    Add-Action -Name "s3_public_access_block" -Result "configured" -Detail $BucketName

    $encryptionFile = Join-Path $env:TEMP "comfy_s3_encryption_$([guid]::NewGuid().ToString('N')).json"
    Write-TextNoBom -Path $encryptionFile -Value '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
    $encryption = Invoke-AwsJson -Arguments @("s3api", "put-bucket-encryption", "--bucket", $BucketName, "--server-side-encryption-configuration", "file://$encryptionFile")
    Remove-Item -LiteralPath $encryptionFile -ErrorAction SilentlyContinue
    if ($encryption.exit_code -ne 0) { throw "put-bucket-encryption failed: $($encryption.text)" }
    Add-Action -Name "s3_encryption" -Result "configured" -Detail "AES256"

    $versioning = Invoke-AwsJson -Arguments @("s3api", "put-bucket-versioning", "--bucket", $BucketName, "--versioning-configuration", "Status=Enabled")
    if ($versioning.exit_code -ne 0) { throw "put-bucket-versioning failed: $($versioning.text)" }
    Add-Action -Name "s3_versioning" -Result "enabled" -Detail $BucketName

    foreach ($rolePolicy in @(
      [ordered]@{ Role = $Ec2RuntimeRoleName; PolicyName = "ComfyUIRuntimeS3Access"; Policy = $ec2RuntimePolicy },
      [ordered]@{ Role = $GitHubDeployRoleName; PolicyName = "ComfyUIDeployBundleS3Upload"; Policy = $githubDeployPolicy },
      [ordered]@{ Role = $SchedulerStopRoleName; PolicyName = "ComfyUIEmergencyStopOnly"; Policy = $schedulerPolicy }
    )) {
      $roleCheck = Invoke-AwsJson -Arguments @("iam", "get-role", "--role-name", $rolePolicy.Role, "--output", "json")
      if ($roleCheck.exit_code -ne 0) {
        if ($rolePolicy.Role -eq $GitHubDeployRoleName) {
          $trustFile = Join-Path $env:TEMP "comfy_github_trust_$([guid]::NewGuid().ToString('N')).json"
          Write-TextNoBom -Path $trustFile -Value $githubTrustPolicy
          $createRole = Invoke-AwsJson -Arguments @("iam", "create-role", "--role-name", $rolePolicy.Role, "--assume-role-policy-document", "file://$trustFile", "--description", "Comfy UI deploy bundle upload role for GitHub Actions", "--output", "json")
          Remove-Item -LiteralPath $trustFile -ErrorAction SilentlyContinue
          if ($createRole.exit_code -ne 0) { throw "create-role $($rolePolicy.Role) failed: $($createRole.text)" }
          Add-Action -Name "iam_role_$($rolePolicy.Role)" -Result "created" -Detail "github_oidc"
        } elseif ($rolePolicy.Role -eq $SchedulerStopRoleName) {
          $trustFile = Join-Path $env:TEMP "comfy_scheduler_trust_$([guid]::NewGuid().ToString('N')).json"
          Write-TextNoBom -Path $trustFile -Value $schedulerTrustPolicy
          $createRole = Invoke-AwsJson -Arguments @("iam", "create-role", "--role-name", $rolePolicy.Role, "--assume-role-policy-document", "file://$trustFile", "--description", "Comfy UI emergency stop scheduler role", "--output", "json")
          Remove-Item -LiteralPath $trustFile -ErrorAction SilentlyContinue
          if ($createRole.exit_code -ne 0) { throw "create-role $($rolePolicy.Role) failed: $($createRole.text)" }
          Add-Action -Name "iam_role_$($rolePolicy.Role)" -Result "created" -Detail "scheduler"
        } else {
          throw "Required EC2 runtime role missing: $($rolePolicy.Role)"
        }
      } else {
        Add-Action -Name "iam_role_$($rolePolicy.Role)" -Result "exists" -Detail $rolePolicy.Role
        if ($rolePolicy.Role -eq $GitHubDeployRoleName) {
          $trustFile = Join-Path $env:TEMP "comfy_github_trust_update_$([guid]::NewGuid().ToString('N')).json"
          Write-TextNoBom -Path $trustFile -Value $githubTrustPolicy
          $trustUpdate = Invoke-AwsJson -Arguments @("iam", "update-assume-role-policy", "--role-name", $rolePolicy.Role, "--policy-document", "file://$trustFile")
          Remove-Item -LiteralPath $trustFile -ErrorAction SilentlyContinue
          if ($trustUpdate.exit_code -ne 0) { throw "update-assume-role-policy $($rolePolicy.Role) failed: $($trustUpdate.text)" }
          Add-Action -Name "iam_trust_$($rolePolicy.Role)" -Result "updated" -Detail "github_oidc"
        } elseif ($rolePolicy.Role -eq $SchedulerStopRoleName) {
          $trustFile = Join-Path $env:TEMP "comfy_scheduler_trust_update_$([guid]::NewGuid().ToString('N')).json"
          Write-TextNoBom -Path $trustFile -Value $schedulerTrustPolicy
          $trustUpdate = Invoke-AwsJson -Arguments @("iam", "update-assume-role-policy", "--role-name", $rolePolicy.Role, "--policy-document", "file://$trustFile")
          Remove-Item -LiteralPath $trustFile -ErrorAction SilentlyContinue
          if ($trustUpdate.exit_code -ne 0) { throw "update-assume-role-policy $($rolePolicy.Role) failed: $($trustUpdate.text)" }
          Add-Action -Name "iam_trust_$($rolePolicy.Role)" -Result "updated" -Detail "scheduler"
        }
      }

      $policyFile = Join-Path $env:TEMP "comfy_policy_$($rolePolicy.Role)_$([guid]::NewGuid().ToString('N')).json"
      Write-TextNoBom -Path $policyFile -Value $rolePolicy.Policy
      $putPolicy = Invoke-AwsJson -Arguments @("iam", "put-role-policy", "--role-name", $rolePolicy.Role, "--policy-name", $rolePolicy.PolicyName, "--policy-document", "file://$policyFile")
      Remove-Item -LiteralPath $policyFile -ErrorAction SilentlyContinue
      if ($putPolicy.exit_code -ne 0) { throw "put-role-policy $($rolePolicy.Role)/$($rolePolicy.PolicyName) failed: $($putPolicy.text)" }
      Add-Action -Name "iam_inline_policy_$($rolePolicy.Role)" -Result "put" -Detail $rolePolicy.PolicyName
    }

    if ($UpdateEnv) {
      $record.env_update.attempted = $true
      Update-EnvValues -Path $EnvFile -Values @{
        "COMFY_DEPLOY_BUNDLE_S3_URI" = $deployBundleUri
        "S3_MODEL_BUCKET" = $BucketName
        "S3_MODEL_PREFIX" = $ModelCachePrefix.Trim("/")
        "S3_RENDER_OUTPUT_PREFIX" = $ArtifactPrefix.Trim("/")
        "S3_MANIFEST_PREFIX" = $ManifestPrefix.Trim("/")
        "AWS_ROLE_TO_ASSUME" = $githubRoleArn
        "COMFY_SCHEDULER_STOP_ROLE_ARN" = $schedulerRoleArn
      }
      Add-Action -Name "env_non_secret_config" -Result "updated" -Detail ".env keys updated without printing values"
    }

    $record.result = "s3_runtime_infrastructure_ready"
    $record.next_action = "Rerun Test-S3RuntimeTransferReadiness.ps1, then publish the matrix deploy bundle to S3 and pass its URI/SHA to the matrix quality-run plan."
  } catch {
    $record.result = "s3_runtime_infrastructure_setup_failed"
    $record.failure_category = "aws_setup_failed"
    $record.errors += $_.Exception.Message
  }
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
}

$record | ConvertTo-Json -Depth 30
if ($record.result -eq "s3_runtime_infrastructure_setup_failed") { exit 2 }
