[CmdletBinding(PositionalBinding=$false)]
param(
 [string]$ProjectRoot='C:\Comfy_UI_Main',[string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9_-]{2,80}$')][string]$TaskName,
 [Parameter(Mandatory=$true)][ValidateSet('mechanical','implementation','semantic','architecture','test_strategy','git_github_analysis','deterministic','final_authority')][string]$WorkType,
 [ValidateSet('worker_eligible','codex_only')][string]$AuthorityClass='worker_eligible',[ValidateSet('low','medium','high','critical')][string]$RiskClass='medium',
 [ValidateSet('fast_low_risk','balanced_default','high_assurance')][string]$QualityProfile='balanced_default',[Parameter(Mandatory=$true)][string]$Objective,
 [Parameter(Mandatory=$true)][string[]]$CandidatePaths,[string[]]$AllowedPaths=@(),[string[]]$ValidatorCommands=@(),[hashtable]$AcceptanceContract=@{},
 [ValidateRange(0,100)][int]$Priority=50,[ValidateRange(0,600)][double]$EstimatedCodexMinutes=5,[ValidateRange(5,10080)][int]$TtlMinutes=1440,[ValidateRange(1,3)][int]$MaxAttempts=2,
 [switch]$SemanticPreflightRequired,[string]$CodexAuthorityReason=''
)
$ErrorActionPreference='Stop';Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
if(-not(Test-Path(Get-AIWorkerKeyPath -DispatcherRoot $DispatcherRoot))){throw 'Initialize dispatcher security first.'}
if($AuthorityClass-eq'codex_only'-and[string]::IsNullOrWhiteSpace($CodexAuthorityReason)){throw 'Codex-only intent requires an authority reason.'}
$now=[DateTimeOffset]::Now;$id=('intent_{0}_{1}_{2}'-f($now.ToString('yyyyMMddTHHmmssfffzzz')-replace':',''),$TaskName,[guid]::NewGuid().ToString('N').Substring(0,8))
$intent=[ordered]@{schema_version=1;artifact_type='ai_worker_task_intent';status='READY';intent_id=$id;created_at=$now.ToString('o');project_root=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\');task_name=$TaskName;work_type=$WorkType;authority_class=$AuthorityClass;risk_class=$RiskClass;quality_profile=$QualityProfile;objective=$Objective;candidate_paths=@($CandidatePaths);allowed_paths=@($AllowedPaths);validator_commands=@($ValidatorCommands);acceptance_contract=$(if($AcceptanceContract.Count){$AcceptanceContract}else{[ordered]@{behavior=$Objective;tests='Applicable validators pass.';scope='No undeclared path changes.';regressions='Existing behavior remains covered.';evidence='Worker and validator outputs are hash-bound.';rollback='Reject and remove the isolated worker worktree.';performance='No material regression in the bounded path.';security='No credential or authority boundary is crossed.'}});priority=$Priority;estimated_codex_minutes=$EstimatedCodexMinutes;ttl_minutes=$TtlMinutes;max_attempts=$MaxAttempts;semantic_preflight_required=[bool]$SemanticPreflightRequired;codex_authority_reason=$CodexAuthorityReason}
$path=Join-Path ([IO.Path]::GetFullPath($DispatcherRoot)) "intake\$id.json";Write-AIWorkerSignedJson -Path $path -Value $intent -DispatcherRoot $DispatcherRoot|Out-Null
$intent.intent_path=$path;$intent|ConvertTo-Json -Depth 12
