[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$WrapperPath,
  [Parameter(Mandatory=$true)][string]$ParametersPath,
  [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference='Stop'
if(-not(Test-Path $WrapperPath -PathType Leaf)){throw "Worker wrapper missing: $WrapperPath"}
$source=Get-Content -LiteralPath $ParametersPath -Raw|ConvertFrom-Json;$parameters=@{}
foreach($property in $source.PSObject.Properties){
  if($property.Value-is[System.Array]){$parameters[$property.Name]=@($property.Value)}else{$parameters[$property.Name]=$property.Value}
}
$output=&$WrapperPath @parameters
$text=($output|Out-String).Trim()
[IO.File]::WriteAllText($OutputPath,$text,(New-Object Text.UTF8Encoding($false)))
$text
