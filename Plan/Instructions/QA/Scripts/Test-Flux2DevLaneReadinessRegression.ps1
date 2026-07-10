param([string]$ProjectRoot = "C:\Comfy_UI_Main", [string]$OutFile = "")
$ErrorActionPreference = "Stop"

function Write-Utf8 { param([string]$Path, [string]$Value); [System.IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null; [System.IO.File]::WriteAllText($Path, $Value, (New-Object System.Text.UTF8Encoding($false))) }
function Write-Json { param([string]$Path, [object]$Value); Write-Utf8 $Path (($Value | ConvertTo-Json -Depth 20) + [Environment]::NewLine) }
function Hash-Text { param([string]$Value); $bytes=[Text.Encoding]::UTF8.GetBytes($Value); $sha=[Security.Cryptography.SHA256]::Create(); try { (($sha.ComputeHash($bytes) | ForEach-Object {$_.ToString('x2')}) -join '') } finally {$sha.Dispose()} }

$validator = Join-Path $ProjectRoot "tools\Test-Flux2DevLaneReadiness.ps1"
$temp = Join-Path ([IO.Path]::GetTempPath()) ("flux2_readiness_regression_" + [guid]::NewGuid().ToString("N"))
$fixture = Join-Path $temp "project"
[IO.Directory]::CreateDirectory((Join-Path $fixture "Plan\10_REGISTRIES")) | Out-Null
Copy-Item (Join-Path $ProjectRoot "Plan\10_REGISTRIES\wave06_engine_registry.json") (Join-Path $fixture "Plan\10_REGISTRIES\wave06_engine_registry.json")
Copy-Item (Join-Path $ProjectRoot "Plan\10_REGISTRIES\wave15_image_base_lane_registry.json") (Join-Path $fixture "Plan\10_REGISTRIES\wave15_image_base_lane_registry.json")
Copy-Item (Join-Path $ProjectRoot "Plan\10_REGISTRIES\wave06_flux2_integration_requirements.json") (Join-Path $fixture "Plan\10_REGISTRIES\wave06_flux2_integration_requirements.json")

$content = @{ diffusion_model="diffusion`n"; text_encoder="encoder`n"; vae="vae`n" }
$hashes = @{}; foreach($role in $content.Keys){ $hashes[$role]=Hash-Text $content[$role] }
$config = Join-Path $temp "flux2.env"; $manifest = Join-Path $temp "manifest.json"; $workflow = Join-Path $temp "workflow"
$configText = @("FLUX2_ENABLED=true","FLUX2_DEV_MODEL_FILENAME=diffusion.bin","FLUX2_DEV_MODEL_SHA256=$($hashes.diffusion_model)","FLUX2_TEXT_ENCODER_FILENAME=encoder.bin","FLUX2_TEXT_ENCODER_SHA256=$($hashes.text_encoder)","FLUX2_VAE_FILENAME=vae.bin","FLUX2_VAE_SHA256=$($hashes.vae)","FLUX2_MIN_COMFYUI_VERSION=fixture-version") -join "`n"
Write-Utf8 $config ($configText+"`n")
$assets=@(); foreach($role in @("diffusion_model","text_encoder","vae")){ $name=@{diffusion_model="diffusion.bin";text_encoder="encoder.bin";vae="vae.bin"}[$role]; $path=Join-Path $temp "assets\$name"; Write-Utf8 $path $content[$role]; $assets += [ordered]@{role=$role;filename=$name;sha256=$hashes[$role];source_url="https://example.invalid/$name";license_or_access_notes="fixture only";local_cache_path=$path} }
Write-Json $manifest ([ordered]@{required_comfyui_version="fixture-version";required_node_classes=@("FixtureLoader");assets=$assets})
foreach($name in @("workflow.api.json","smoke_request.json","object_info_proof.json","smoke_output_proof.json")){ Write-Json (Join-Path $workflow $name) ([ordered]@{result="pass_fixture"}) }

function Invoke-Case {
  param([string]$Name,[scriptblock]$Mutate,[bool]$ExpectedReady)
  & $Mutate
  $out=Join-Path $temp "$Name.json"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -ProjectRoot $fixture -ConfigPath $config -AssetManifestPath $manifest -WorkflowRoot $workflow -OutFile $out *> $null
  $p=Get-Content $out -Raw | ConvertFrom-Json
  $actual=[string]$p.result -eq "pass_local_flux2_dev_candidate"
  [pscustomobject][ordered]@{name=$Name;result=$(if($actual -eq $ExpectedReady){"pass"}else{"fail"});expected_ready=$ExpectedReady;actual_ready=$actual;classification=$p.classification;failed_check_names=@($p.failed_check_names);safety_pass=([bool]$p.local_only -and -not [bool]$p.aws_contacted -and -not [bool]$p.comfyui_contacted -and -not [bool]$p.generation_executed -and -not [bool]$p.promotion_claimed)}
}

$tests=@()
$tests += Invoke-Case "complete_fixture_passes_static_candidate" {} $true
$tests += Invoke-Case "disabled_fails_closed" { (Get-Content $config -Raw).Replace("FLUX2_ENABLED=true","FLUX2_ENABLED=false") | Set-Content $config -NoNewline } $false
Write-Utf8 $config ($configText+"`n")
$tests += Invoke-Case "missing_manifest_fails_closed" { Move-Item $manifest "$manifest.hidden" } $false
Move-Item "$manifest.hidden" $manifest
$tests += Invoke-Case "hash_mismatch_fails_closed" { Write-Utf8 (Join-Path $temp "assets\diffusion.bin") "wrong`n" } $false
Write-Utf8 (Join-Path $temp "assets\diffusion.bin") $content.diffusion_model
$tests += Invoke-Case "missing_object_info_fails_closed" { Move-Item (Join-Path $workflow "object_info_proof.json") (Join-Path $workflow "object_info_proof.hidden") } $false
Move-Item (Join-Path $workflow "object_info_proof.hidden") (Join-Path $workflow "object_info_proof.json")
$tests += Invoke-Case "missing_smoke_output_fails_closed" { Move-Item (Join-Path $workflow "smoke_output_proof.json") (Join-Path $workflow "smoke_output_proof.hidden") } $false

$failed=@($tests | Where-Object {$_.result -ne "pass" -or -not $_.safety_pass})
$record=[ordered]@{schema_version="1.0";artifact_type="flux2_dev_lane_readiness_regression";created_at=(Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz");result=$(if($failed.Count -eq 0){"pass_local_only"}else{"fail"});local_only=$true;aws_contacted=$false;comfyui_contacted=$false;ec2_started=$false;generation_executed=$false;promotion_claimed=$false;test_count=$tests.Count;passing_test_count=@($tests|Where-Object{$_.result -eq "pass"}).Count;failed_test_count=$failed.Count;tests=$tests;boundary="Disposable static fixtures only; no model download, ComfyUI execution, generation, promotion, or live service access."}
if([string]::IsNullOrWhiteSpace($OutFile)){ $stamp=(Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":",""); $OutFile=Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_FLUX2_DEV_LANE_READINESS_REGRESSION_$stamp.json" } elseif(-not [IO.Path]::IsPathRooted($OutFile)){ $OutFile=Join-Path $ProjectRoot $OutFile }
Write-Json $OutFile $record
Remove-Item $temp -Recurse -Force
$record | ConvertTo-Json -Depth 20
if($failed.Count -gt 0){exit 1}
