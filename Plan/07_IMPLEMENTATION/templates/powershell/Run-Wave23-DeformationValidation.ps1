param(
  [string]$Root = "."
)

$ErrorActionPreference = "Stop"
python "._IMPLEMENTATION\scriptsun_wave23_local_validation.py" --root $Root
