[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$ProjectRoot='C:\Comfy_UI_Main',
  [string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9_-]{2,80}$')][string]$TaskName,
  [Parameter(Mandatory=$true)][ValidateSet('mechanical','implementation','semantic','architecture','test_strategy','git_github_analysis','deterministic','final_authority')][string]$WorkType,
  [Parameter(Mandatory=$true)][string]$Objective,
  [Parameter(Mandatory=$true)][string[]]$CandidatePaths,
  [string[]]$AllowedPaths=@(),
  [string[]]$ValidatorCommands=@(),
  [ValidateSet('fast_low_risk','balanced_default','high_assurance')][string]$QualityProfile='balanced_default',
  [ValidateSet('low','medium','high','critical')][string]$RiskClass='medium',
  [hashtable]$AcceptanceContract=@{},
  [ValidateRange(0,100)][int]$Priority=50,
  [ValidateRange(0,600)][double]$EstimatedCodexMinutes=5,
  [string]$CodexAuthorityReason='',
  [switch]$RouteNow,
  [switch]$DeferRouting
)

$ErrorActionPreference='Stop'
if($RouteNow-and$DeferRouting){throw 'RouteNow and DeferRouting are mutually exclusive.'}
$canonicalProjectRoot=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
if($canonicalProjectRoot-eq'C:\Comfy_UI_Main'-and$WorkType-ne'final_authority'){
  $storageEvaluator=Join-Path $canonicalProjectRoot 'Plan\07_IMPLEMENTATION\scripts\evaluate_comfyui_main_local_storage_admission.py'
  $storagePolicy=Join-Path $canonicalProjectRoot 'Plan\10_REGISTRIES\comfyui_main_local_storage_admission_policy.json'
  foreach($storageControl in @($storageEvaluator,$storagePolicy)){if(-not(Test-Path -LiteralPath $storageControl -PathType Leaf)){throw "COMFYUI_LOCAL_STORAGE_ADMISSION_CONTROL_MISSING: $storageControl"}}
  $storageRaw=& python.exe -B $storageEvaluator --policy $storagePolicy --operation worker_worktree
  if($LASTEXITCODE-ne0){throw 'COMFYUI_LOCAL_STORAGE_ADMISSION_EVALUATOR_FAILED'}
  $storageAdmission=($storageRaw|Out-String)|ConvertFrom-Json
  if([string]$storageAdmission.status-ne'ADMITTED'){throw "COMFYUI_LOCAL_STORAGE_ADMISSION_DENIED: $([string]$storageAdmission.classification); free=$([long]$storageAdmission.observed_free_bytes); reasons=$(@($storageAdmission.reasons)-join',')"}
}
$authority=if($WorkType-eq'final_authority'){'codex_only'}else{'worker_eligible'}
$semanticPreflight=($WorkType-eq'implementation'-and($QualityProfile-eq'high_assurance'-or$RiskClass-in@('high','critical')))
$attempts=if($QualityProfile-eq'high_assurance'){1}else{2}
$intentParams=@{ProjectRoot=$ProjectRoot;DispatcherRoot=$DispatcherRoot;TaskName=$TaskName;WorkType=$WorkType;AuthorityClass=$authority;RiskClass=$RiskClass;QualityProfile=$QualityProfile;Objective=$Objective;CandidatePaths=$CandidatePaths;AllowedPaths=$AllowedPaths;ValidatorCommands=$ValidatorCommands;AcceptanceContract=$AcceptanceContract;Priority=$Priority;EstimatedCodexMinutes=$EstimatedCodexMinutes;CodexAuthorityReason=$CodexAuthorityReason;SemanticPreflightRequired=$semanticPreflight;MaxAttempts=$attempts}
$intent=&(Join-Path $PSScriptRoot 'New-AIWorkerTaskIntent.ps1') @intentParams|ConvertFrom-Json
$routing=$null
$routeImmediately=-not$DeferRouting
if($routeImmediately){$routing=&(Join-Path $PSScriptRoot 'Invoke-AIWorkerAdmissionRouter.ps1') -DispatcherRoot $DispatcherRoot -MaxIntents 1|ConvertFrom-Json}
[ordered]@{status='PASS';classification=$(if($routeImmediately){'AI_WORKER_DEVELOPMENT_PIPELINE_ROUTED'}else{'AI_WORKER_DEVELOPMENT_PIPELINE_ADMITTED_DEFERRED'});intent=$intent;routing=$routing;codex_final_authority_required=$true}|ConvertTo-Json -Depth 15
