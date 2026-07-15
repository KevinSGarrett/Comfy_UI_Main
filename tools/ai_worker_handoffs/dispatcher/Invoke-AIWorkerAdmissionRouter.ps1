[CmdletBinding()]
param([string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',[ValidateRange(1,100)][int]$MaxIntents=10)
$ErrorActionPreference='Stop';Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$root=[IO.Path]::GetFullPath($DispatcherRoot);foreach($d in @('intake','admission\processed','admission\failed','admission\events')){New-Item -ItemType Directory -Force -Path(Join-Path $root $d)|Out-Null}
$lock=Join-Path $root 'admission.lock';if(-not(Enter-AIWorkerFileLock -Path $lock)){[ordered]@{status='IDLE';classification='AI_WORKER_ADMISSION_ALREADY_RUNNING';processed=0}|ConvertTo-Json;return}
$results=@();try{
 foreach($file in @(Get-ChildItem (Join-Path $root 'intake') -Filter *.json -File|Sort-Object Name|Select-Object -First $MaxIntents)){
  $intent=$null;$decision=$null
  try{
   $intent=Read-AIWorkerSignedJson -Path $file.FullName -DispatcherRoot $root
   if($intent.artifact_type-ne'ai_worker_task_intent'-or$intent.status-ne'READY'){throw 'Invalid intent contract.'}
   $acceptance=@{};foreach($property in $intent.acceptance_contract.PSObject.Properties){$acceptance[$property.Name]=$property.Value}
   $route=if($intent.authority_class-eq'codex_only'-or$intent.work_type-eq'final_authority'){'CODEX_ONLY_AUTHORITY'}elseif($intent.work_type-eq'deterministic'-and[double]$intent.estimated_codex_minutes-le2){'DETERMINISTIC_FAST_PATH'}elseif($intent.work_type-in@('semantic','architecture','test_strategy')){'CLAUDE_SONNET_PRIMARY_REQUIRED'}elseif($intent.work_type-eq'git_github_analysis'){'GIT_GITHUB_WORKER_ANALYSIS_REQUIRED'}else{'CURSOR_FIRST_REQUIRED'}
   $requests=@()
   if($route-eq'CURSOR_FIRST_REQUIRED'-and($intent.semantic_preflight_required-eq$true-or$intent.risk_class-in@('high','critical'))){
    $pre=&(Join-Path $PSScriptRoot 'New-AIWorkerDispatchRequest.ps1') -ProjectRoot $intent.project_root -DispatcherRoot $root -TaskName ($intent.task_name+'_sonnet_preflight') -WorkerLane Claude -Operation read_only -WorkOrderText ("Produce the architecture, risk, and test contract before implementation. Objective: "+$intent.objective) -CandidatePaths @($intent.candidate_paths) -Priority ([math]::Min(100,[int]$intent.priority+5)) -TtlMinutes $intent.ttl_minutes -MaxAttempts $intent.max_attempts -RiskClass $intent.risk_class -QualityProfile $intent.quality_profile -AcceptanceContract $acceptance -IntentId $intent.intent_id|ConvertFrom-Json
    $requests+=$pre
    $impl=&(Join-Path $PSScriptRoot 'New-AIWorkerDispatchRequest.ps1') -ProjectRoot $intent.project_root -DispatcherRoot $root -TaskName $intent.task_name -WorkerLane Cursor -Operation implementation -WorkOrderText $intent.objective -CandidatePaths @($intent.candidate_paths) -AllowedPaths @($intent.allowed_paths) -DeclaredCommands @($intent.validator_commands) -Priority $intent.priority -TtlMinutes $intent.ttl_minutes -MaxAttempts $intent.max_attempts -RiskClass $intent.risk_class -QualityProfile $intent.quality_profile -AcceptanceContract $acceptance -DependsOnRequestIds @($pre.request_id) -IntentId $intent.intent_id|ConvertFrom-Json
    $requests+=$impl
    if($intent.quality_profile-eq'high_assurance'){
      $post=&(Join-Path $PSScriptRoot 'New-AIWorkerDispatchRequest.ps1') -ProjectRoot $intent.project_root -DispatcherRoot $root -TaskName ($intent.task_name+'_sonnet_review') -WorkerLane Claude -Operation read_only -WorkOrderText ('Review the hash-bound implementation diff, validator result, acceptance contract, and residual risk. Do not repeat architecture work. Objective: '+$intent.objective) -CandidatePaths @($intent.candidate_paths) -Priority ([math]::Max(0,[int]$intent.priority-1)) -TtlMinutes $intent.ttl_minutes -MaxAttempts $intent.max_attempts -RiskClass $intent.risk_class -QualityProfile $intent.quality_profile -AcceptanceContract $acceptance -DependsOnRequestIds @($impl.request_id) -IntentId $intent.intent_id|ConvertFrom-Json
      $requests+=$post
    }
   }elseif($route-in@('CURSOR_FIRST_REQUIRED','GIT_GITHUB_WORKER_ANALYSIS_REQUIRED')){
    $operation=if($intent.work_type-eq'implementation'){'implementation'}else{'read_only'}
    $args=@{ProjectRoot=$intent.project_root;DispatcherRoot=$root;TaskName=$intent.task_name;WorkerLane='Cursor';Operation=$operation;WorkOrderText=$intent.objective;CandidatePaths=@($intent.candidate_paths);Priority=$intent.priority;TtlMinutes=$intent.ttl_minutes;MaxAttempts=$intent.max_attempts;RiskClass=$intent.risk_class;QualityProfile=$intent.quality_profile;AcceptanceContract=$acceptance;IntentId=$intent.intent_id}
    if($operation-eq'implementation'){$args.AllowedPaths=@($intent.allowed_paths);$args.DeclaredCommands=@($intent.validator_commands)}
    $requests+=(&(Join-Path $PSScriptRoot 'New-AIWorkerDispatchRequest.ps1') @args|ConvertFrom-Json)
   }elseif($route-eq'CLAUDE_SONNET_PRIMARY_REQUIRED'){$requests+=(&(Join-Path $PSScriptRoot 'New-AIWorkerDispatchRequest.ps1') -ProjectRoot $intent.project_root -DispatcherRoot $root -TaskName $intent.task_name -WorkerLane Claude -Operation read_only -WorkOrderText $intent.objective -CandidatePaths @($intent.candidate_paths) -Priority $intent.priority -TtlMinutes $intent.ttl_minutes -MaxAttempts $intent.max_attempts -RiskClass $intent.risk_class -QualityProfile $intent.quality_profile -AcceptanceContract $acceptance -IntentId $intent.intent_id|ConvertFrom-Json)}
   $decision=[ordered]@{schema_version=1;artifact_type='ai_worker_admission_decision';status='FINALIZED';finalized_at=(Get-Date).ToString('o');intent_id=$intent.intent_id;task_name=$intent.task_name;route=$route;authority_reason=$intent.codex_authority_reason;eligible_for_worker=($route-notin@('CODEX_ONLY_AUTHORITY','DETERMINISTIC_FAST_PATH'));estimated_codex_minutes=$intent.estimated_codex_minutes;request_ids=@($requests|ForEach-Object{$_.request_id});quality_profile=$intent.quality_profile;risk_class=$intent.risk_class}
   $event=Join-Path $root "admission\events\$($intent.intent_id).json";Write-AIWorkerSignedJson -Path $event -Value $decision -DispatcherRoot $root|Out-Null
   Move-Item $file.FullName (Join-Path $root "admission\processed\$($file.Name)") -Force;Move-Item ($file.FullName+'.sig') (Join-Path $root "admission\processed\$($file.Name).sig") -Force
   $results+=[ordered]@{intent_id=$intent.intent_id;status='PASS';route=$route;request_ids=$decision.request_ids}
  }catch{$dest=Join-Path $root "admission\failed\$($file.Name)";Move-Item $file.FullName $dest -Force;if(Test-Path($file.FullName+'.sig')){Move-Item($file.FullName+'.sig')($dest+'.sig')-Force};$results+=[ordered]@{intent_id=$(if($intent){$intent.intent_id}else{$file.BaseName});status='FAIL';issue=$_.Exception.Message}}
 }
}finally{Remove-Item $lock -Force -ErrorAction SilentlyContinue}
[ordered]@{status=$(if(@($results|Where-Object{$_.status-eq'FAIL'}).Count){'FAIL'}else{'PASS'});classification='AI_WORKER_ADMISSION_ROUTED';processed=$results.Count;results=$results}|ConvertTo-Json -Depth 8
