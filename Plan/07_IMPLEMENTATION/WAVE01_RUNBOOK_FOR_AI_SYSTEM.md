# Wave 01 Runbook for the AI System

## Execution order

1. Read this Wave 01 runbook.
2. Confirm source inventory exists.
3. Create local repo at `C:\Comfy_UI_Main`.
4. Install repo templates.
5. Create directory structure.
6. Initialize Git if missing.
7. Set GitHub remote if missing.
8. Run local repo validation.
9. Run no-model-binary scan.
10. Write evidence manifests.
11. Do not start EC2.
12. Do not download model binaries unless a future wave creates an approved hydration manifest.

## Required logs

The AI system must create:

```text
evidence/local/wave01_bootstrap_log.txt
evidence/local/wave01_git_remote_check.txt
evidence/local/wave01_no_model_binary_scan.txt
manifests/repo_validation/wave01_local_repo_validation.json
```

## Required decision logs

If any of these occur, write a decision log:

```text
repo root already exists
remote already exists and differs
model binaries are found inside repo
tracker rows conflict with 35-wave plan
Plans ZIP contains newer guidance than blueprint
EC2 must be started before a planned runtime-proof wave
```

## Stop conditions

Stop immediately if:

```text
Git repo path points to a model/runtime folder
.gitignore is missing
forbidden files are found
EC2 start is attempted without proof request
S3 full-bucket sync is attempted
```

## Future wave handoff

Wave 02 must inherit:

```text
repo exists
source inventory exists
models excluded
EC2 guard exists
S3 hydration policy exists
tracker and Plans are marked ongoing
```
