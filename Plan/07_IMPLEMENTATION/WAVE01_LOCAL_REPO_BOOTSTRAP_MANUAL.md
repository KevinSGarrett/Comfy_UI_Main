# Wave 01 Local Repository Bootstrap Manual

## Target

Create and operate the structured local repo:

```text
C:\Comfy_UI_Main
```

Remote:

```text
https://github.com/KevinSGarrett/Comfy_UI_Main
```

## Step 1 — Create root

```powershell
New-Item -ItemType Directory -Force -Path "C:\Comfy_UI_Main"
Set-Location "C:\Comfy_UI_Main"
```

## Step 2 — Initialize Git safely

```powershell
if (-not (Test-Path ".git")) {
  git init
}
```

## Step 3 — Set remote safely

```powershell
$remote = git remote get-url origin 2>$null
if (-not $remote) {
  git remote add origin "https://github.com/KevinSGarrett/Comfy_UI_Main"
}
```

If a different `origin` already exists, do not overwrite it automatically. Create a decision log entry.

## Step 4 — Create required directories

```powershell
$dirs = @(
  "docs",
  "workflows/ui/current",
  "workflows/ui/archive",
  "workflows/api/templates",
  "workflows/subgraphs",
  "workflows/modules",
  "workflows/app_mode",
  "orchestration/planner",
  "orchestration/runner",
  "orchestration/qa",
  "orchestration/repair",
  "orchestration/registries",
  "schemas",
  "configs",
  "scripts/powershell",
  "scripts/python",
  "manifests/source_inventory",
  "manifests/model_assets",
  "manifests/workflow_validation",
  "manifests/qa",
  "manifests/ec2_runtime_proof",
  "evidence/local",
  "evidence/ec2",
  "evidence/visual_qa",
  "tests/unit",
  "tests/integration",
  "tests/golden_scenes",
  "tests/no_gpu_static",
  "app_mode/specs",
  "external_assets",
  ".github/workflows"
)

foreach ($d in $dirs) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}
```

## Step 5 — Copy template files

Use templates from this blueprint:

```text
07_IMPLEMENTATION/templates/repo/.gitignore
07_IMPLEMENTATION/templates/repo/.gitattributes
07_IMPLEMENTATION/templates/repo/README.md
07_IMPLEMENTATION/templates/repo/PROJECT_MANIFEST.json
07_IMPLEMENTATION/templates/repo/.github/workflows/static-validation.yml
```

## Step 6 — Add source inventories

Create manifests for uploaded and external source packs:

```text
manifests/source_inventory/wave01_source_inventory.json
manifests/source_inventory/current_main_flow_summary.json
manifests/source_inventory/tracker_ongoing_source_summary.json
manifests/source_inventory/plans_ongoing_source_summary.json
```

## Step 7 — Commit only safe files

Before committing:

```powershell
python scripts/python/check_no_model_files_in_git.py --root "C:\Comfy_UI_Main"
```

Then:

```powershell
git status
git add .
git commit -m "Wave 01 local repo structure and geometry gates"
```

## Step 8 — Push

```powershell
git branch -M main
git push -u origin main
```

## AI PM rule

If any command fails, the AI system must stop, record the exact command, stderr/stdout, and remediation plan. It must not keep running destructive commands.
