[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$ProjectRoot='C:\Comfy_UI_Main',[string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9_-]{2,80}$')][string]$TaskName,
  [Parameter(Mandatory=$true)][ValidateSet('Cursor','Claude')][string]$WorkerLane,
  [Parameter(Mandatory=$true)][ValidateSet('read_only','implementation')][string]$Operation,
  [Parameter(Mandatory=$true)][string]$WorkOrderText,[Parameter(Mandatory=$true)][string[]]$CandidatePaths,
  [string[]]$AllowedPaths=@(),[string[]]$DeclaredCommands=@(),
  [ValidateSet('SonnetPrimary','OpusEscalation')][string]$ClaudeTaskTier='SonnetPrimary',
  [ValidateSet('claude-sonnet-5','claude-opus-4-8')][string]$ClaudeModel='claude-sonnet-5',
  [ValidateSet('medium','high','xhigh')][string]$ClaudeEffort='medium',[ValidateRange(60,1800)][int]$TimeoutSeconds=600,
  [ValidateRange(0,100)][int]$Priority=50,[ValidateRange(5,10080)][int]$TtlMinutes=1440,[ValidateRange(1,3)][int]$MaxAttempts=2,
  [ValidateSet('low','medium','high','critical')][string]$RiskClass='medium',
  [ValidateSet('fast_low_risk','balanced_default','high_assurance')][string]$QualityProfile='balanced_default',
  [hashtable]$AcceptanceContract=@{},[string[]]$DependsOnRequestIds=@(),[string]$SupersedesRequestId='',
  [string]$IntentId='',[string]$DecisionUnitId='',[string]$EscalationReason='',[string]$PriorSonnetRecordPath='',[switch]$ForceDuplicate
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$project=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $project '.git'))) { throw "ProjectRoot is not a Git worktree: $project" }
if (-not (Test-Path (Get-AIWorkerKeyPath -DispatcherRoot $DispatcherRoot))) { throw 'Initialize dispatcher security before queueing requests.' }
if ($WorkerLane -eq 'Claude' -and $Operation -ne 'read_only') { throw 'Claude dispatch is read-only.' }
if ($WorkerLane -eq 'Claude' -and $ClaudeTaskTier -eq 'SonnetPrimary' -and $ClaudeModel -ne 'claude-sonnet-5') { throw 'SonnetPrimary requires claude-sonnet-5.' }
if ($WorkerLane -eq 'Claude' -and $ClaudeTaskTier -eq 'OpusEscalation' -and $ClaudeModel -ne 'claude-opus-4-8') { throw 'OpusEscalation requires claude-opus-4-8.' }
$candidates=@($CandidatePaths|ForEach-Object{Normalize-AIWorkerRelativePath $_}|Sort-Object -Unique)
$allowed=@($AllowedPaths|ForEach-Object{Normalize-AIWorkerRelativePath $_}|Sort-Object -Unique)
$commands=@($DeclaredCommands|Where-Object{-not[string]::IsNullOrWhiteSpace($_)}|ForEach-Object{$_.Trim()}|Sort-Object -Unique)
if ($candidates.Count -lt 1) { throw 'At least one candidate path is required.' }
foreach($path in $candidates){
  & git.exe -C $project diff --quiet -- $path;if($LASTEXITCODE-ne 0){throw "Scope must match HEAD: $path"}
  & git.exe -C $project diff --cached --quiet -- $path;if($LASTEXITCODE-ne 0){throw "Scope has staged drift: $path"}
  & git.exe -C $project ls-files --error-unmatch -- $path 2>$null|Out-Null;if($LASTEXITCODE-ne 0){throw "Scope is not tracked: $path"}
}
$profilePath=Join-Path $project 'Plan\10_REGISTRIES\ai_worker_development_quality_profiles.json'
$profile=$null
if(Test-Path -LiteralPath $profilePath){$registry=Get-Content -LiteralPath $profilePath -Raw|ConvertFrom-Json;$profile=$registry.profiles.$QualityProfile}
if($profile-and$RiskClass-notin@($profile.risk_classes)){throw "RiskClass $RiskClass is incompatible with quality profile $QualityProfile."}
if($Operation-eq'implementation'){
  if($WorkerLane-ne'Cursor'-or$allowed.Count-lt 1-or$commands.Count-lt 1){throw 'Cursor implementation requires exact allowed paths and host validator commands.'}
  $protected=@($allowed|Where-Object{Test-AIWorkerProtectedPath $_});if($protected.Count){throw "Allowed path crosses Codex authority: $($protected-join', ')"}
  if($profile-and$commands.Count-lt[int]$profile.minimum_validators){throw "Quality profile $QualityProfile requires at least $($profile.minimum_validators) independent host validators."}
  if($profile-and$MaxAttempts-gt[int]$profile.max_cursor_attempts){throw "Quality profile $QualityProfile permits at most $($profile.max_cursor_attempts) Cursor attempts."}
}elseif($allowed.Count-or$commands.Count){throw 'Read-only work cannot declare writes or commands.'}
$forbidden='(?i)(^|[;&|]\s*)(git|gh|aws|jira|kubectl|terraform)(\.exe)?\b|\b(commit|push|pull request|merge|mask promotion|wave71|tracker status)\b'
if(@($commands|Where-Object{$_-match$forbidden}).Count){throw 'Validator command crosses a Codex-only authority boundary.'}
if($AcceptanceContract.Count-eq 0){$AcceptanceContract=[ordered]@{behavior='Complete the bounded work order without widening scope.';tests='All declared host validators pass.';scope='Only declared paths change.';regressions='Existing behavior remains covered.';evidence='Worker diff and host validation are hash-bound.';rollback='Reject the retained worker worktree.';performance='No material regression in the bounded path.';security='No authority or credential boundary is crossed.'}}
if($profile){foreach($field in @($profile.required_acceptance_fields)){if(-not$AcceptanceContract.Contains([string]$field)-or[string]::IsNullOrWhiteSpace([string]$AcceptanceContract[[string]$field])){throw "Acceptance contract is missing required $QualityProfile field: $field"}}}
$packetTool=Join-Path $project 'tools\New-AIWorkerScopePacket.ps1'
$gate=if($WorkerLane-eq'Cursor'){'CURSOR_FIRST_REQUIRED'}elseif($ClaudeTaskTier-eq'OpusEscalation'){'CLAUDE_OPUS_ESCALATION_REQUIRED'}else{'CLAUDE_SONNET_PRIMARY_REQUIRED'}
$packet=&$packetTool -ProjectRoot $project -TaskName $TaskName -Gate $gate -WorkerLane $WorkerLane -CandidatePaths $candidates|ConvertFrom-Json
$base=(&git.exe -C $project rev-parse HEAD).Trim();if($base-notmatch'^[0-9a-f]{40}$'){throw 'Unable to resolve base commit.'}
$packetHash=(Get-FileHash -LiteralPath $packet.output_path -Algorithm SHA256).Hash.ToLowerInvariant()
$identityPayload=[ordered]@{base_commit=$base;lane=$WorkerLane;operation=$Operation;task=$TaskName;candidates=$candidates;allowed=$allowed;commands=$commands;work_order=$WorkOrderText;risk=$RiskClass;quality=$QualityProfile;acceptance=$AcceptanceContract;dependencies=@($DependsOnRequestIds|Sort-Object -Unique)}|ConvertTo-Json -Depth 12 -Compress
$idempotency=Get-Sha256Text -Text $identityPayload
$indexPath=Join-Path ([IO.Path]::GetFullPath($DispatcherRoot)) "idempotency\$idempotency.json"
if((Test-Path $indexPath)-and-not$ForceDuplicate){
  try{$existing=Read-AIWorkerSignedJson -Path $indexPath -DispatcherRoot $DispatcherRoot;if($existing.state-in@('QUEUED','RUNNING','COMPLETED_AWAITING_CODEX')){[ordered]@{status='DEDUPLICATED';classification='AI_WORKER_DUPLICATE_SUPPRESSED';request_id=$existing.request_id;idempotency_key=$idempotency;request_path=$existing.request_path}|ConvertTo-Json -Depth 5;return}}catch{}
}
$now=[DateTimeOffset]::Now;$stamp=$now.ToString('yyyyMMddTHHmmssfffzzz')-replace':',''
$requestId=('p{0:D3}_{1}_{2}_{3}'-f(100-$Priority),$stamp,$TaskName,[guid]::NewGuid().ToString('N').Substring(0,8))
$queueRoot=Join-Path ([IO.Path]::GetFullPath($DispatcherRoot)) "queue\$WorkerLane";New-Item -ItemType Directory -Force -Path $queueRoot|Out-Null
$path=Join-Path $queueRoot "$requestId.json"
$request=[ordered]@{schema_version=2;artifact_type='ai_worker_dispatch_request';status='QUEUED';request_id=$requestId;intent_id=$IntentId;idempotency_key=$idempotency;created_at=$now.ToString('o');expires_at=$now.AddMinutes($TtlMinutes).ToString('o');project_root=$project;base_commit=$base;task_name=$TaskName;worker_lane=$WorkerLane;operation=$Operation;work_order_text=$WorkOrderText;scope_packet_path=[string]$packet.output_path;scope_packet_sha256=$packetHash;candidate_paths=$candidates;allowed_paths=$allowed;validator_commands=$commands;timeout_seconds=$TimeoutSeconds;priority=$Priority;attempt=1;max_attempts=$MaxAttempts;risk_class=$RiskClass;quality_profile=$QualityProfile;acceptance_contract=$AcceptanceContract;depends_on_request_ids=@($DependsOnRequestIds|Sort-Object -Unique);supersedes_request_id=$SupersedesRequestId;claude_task_tier=$ClaudeTaskTier;claude_model=$ClaudeModel;claude_effort=$ClaudeEffort;decision_unit_id=$DecisionUnitId;escalation_reason=$EscalationReason;prior_sonnet_record_path=$PriorSonnetRecordPath;final_authority='Codex Desktop'}
$signature=Write-AIWorkerSignedJson -Path $path -Value $request -DispatcherRoot $DispatcherRoot
Write-Utf8NoBom -Path ($path+'.sha256') -Text ((Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant())
$index=[ordered]@{artifact_type='ai_worker_idempotency_index';request_id=$requestId;request_path=$path;idempotency_key=$idempotency;state='QUEUED';updated_at=$now.ToString('o')};Write-AIWorkerSignedJson -Path $indexPath -Value $index -DispatcherRoot $DispatcherRoot|Out-Null
$request.request_path=$path;$request.request_hmac=$signature;$request|ConvertTo-Json -Depth 12
