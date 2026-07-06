param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python .\07_IMPLEMENTATION\scripts\run_wave22_local_validation.py --root $Root
