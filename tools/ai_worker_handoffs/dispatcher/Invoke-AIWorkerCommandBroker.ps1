[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$WorktreePath,[Parameter(Mandatory=$true)][string[]]$Commands,[ValidateRange(5,1800)][int]$TimeoutSeconds=300,[string]$OutputPath='')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($WorktreePath).TrimEnd('\');if(-not(Test-Path $root -PathType Container)){throw "Worktree missing: $root"}
$allowed='^(?i)\s*(python(?:3)?|py|pytest|powershell(?:\.exe)?|pwsh(?:\.exe)?|node(?:\.exe)?|npm(?:\.cmd)?|npx(?:\.cmd)?|dotnet(?:\.exe)?|Write-Output)\b'
$forbidden='(?i)(^|\s)(git|gh|aws|jira|kubectl|terraform)(\.exe)?\b|[;&|><`]|\b(Invoke-WebRequest|Invoke-RestMethod|curl|wget|Start-Process|Remove-Item|Move-Item|Copy-Item|Set-Content|Add-Content|New-Item|npm\s+(?:install|i|add|update|publish)|pip\s+install)\b'
$results=@()
foreach($command in @($Commands|Where-Object{-not[string]::IsNullOrWhiteSpace($_)})){
 if($command-notmatch$allowed-or$command-match$forbidden){throw "Validator command is outside the broker allowlist: $command"}
 if($command-match'^(?i)\s*(powershell|pwsh)' -and $command-notmatch'(?i)\s-File\s+[^\s]+\.ps1(?:\s|$)'){throw "PowerShell validators must use -File with a repository script: $command"}
 if($command-match'^(?i)\s*(python|python3|py)\b' -and $command-match'(?i)\s-(c|m)\s+' -and $command-notmatch'(?i)\s-m\s+(pytest|unittest)\b'){throw "Python inline or unapproved module execution is forbidden: $command"}
 if($command-match'^(?i)\s*node(?:\.exe)?\s+-(e|p)\b'){throw "Node inline execution is forbidden: $command"}
 if($command-match'^(?i)\s*npx(?:\.cmd)?\b' -and $command-notmatch'(?i)\s--no-install\b'){throw "npx validators require --no-install: $command"}
 if($command-match'^(?i)\s*npm(?:\.cmd)?\b' -and $command-notmatch'^(?i)\s*npm(?:\.cmd)?\s+(test|run\s+[A-Za-z0-9_.:-]+)\b'){throw "npm validators are limited to test or an existing run script: $command"}
 $psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=(Get-Command powershell.exe).Source;$psi.Arguments='-NoLogo -NoProfile -NonInteractive -Command '+('"'+($command-replace'"','\"')+'"');$psi.WorkingDirectory=$root;$psi.UseShellExecute=$false;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.CreateNoWindow=$true
 foreach($name in @($psi.EnvironmentVariables.Keys|ForEach-Object{[string]$_})){if($name-match'^(?i:AWS_|GH_|GITHUB_|ANTHROPIC_|CURSOR_|CIVITAI_|OPENAI_|HF_|HUGGINGFACE_|GIT_CONFIG_)'){[void]$psi.EnvironmentVariables.Remove($name)}}
 $p=New-Object Diagnostics.Process;$p.StartInfo=$psi;$sw=[Diagnostics.Stopwatch]::StartNew();[void]$p.Start();$outTask=$p.StandardOutput.ReadToEndAsync();$errTask=$p.StandardError.ReadToEndAsync();$timedOut=-not$p.WaitForExit($TimeoutSeconds*1000);if($timedOut){try{&taskkill.exe /PID $p.Id /T /F|Out-Null}catch{};try{[void]$p.WaitForExit(5000)}catch{}}else{$p.WaitForExit()};$sw.Stop();$stdout=$outTask.Result;$stderr=$errTask.Result
 $results+=[ordered]@{command=$command;exit_code=$(if($timedOut){-1}else{$p.ExitCode});timed_out=$timedOut;duration_ms=$sw.ElapsedMilliseconds;stdout_excerpt=$(if($stdout.Length-gt2000){$stdout.Substring(0,2000)}else{$stdout});stderr_excerpt=$(if($stderr.Length-gt2000){$stderr.Substring(0,2000)}else{$stderr});stdout_sha256=$(if($stdout){$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($stdout)))).Replace('-','').ToLower()}finally{$sha.Dispose()}}else{$null});pass=(-not$timedOut-and$p.ExitCode-eq0)}
}
$result=[ordered]@{schema_version=1;artifact_type='ai_worker_host_validation_result';status=$(if(@($results|Where-Object{-not$_.pass}).Count){'FAIL'}else{'PASS'});finalized_at=(Get-Date).ToString('o');worktree_path=$root;commands=$results}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))};$result|ConvertTo-Json -Depth 8
