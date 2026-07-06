param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python ".\07_IMPLEMENTATION\scripts\run_wave30_local_validation.py" --root $Root
