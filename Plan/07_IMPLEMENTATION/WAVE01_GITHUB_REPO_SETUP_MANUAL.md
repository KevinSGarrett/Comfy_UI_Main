# Wave 01 GitHub Repository Setup Manual

## Remote

```text
https://github.com/KevinSGarrett/Comfy_UI_Main
```

## GitHub repo purpose

The GitHub repo stores:

```text
source code
workflow JSON templates
workflow UI exports
schema definitions
orchestrator code
validation scripts
QA reports
source inventories
manifests
documentation
App Mode specs
```

The GitHub repo does **not** store:

```text
model binaries
LoRA files
large checkpoints
large video outputs
large audio outputs
ComfyUI cache folders
large generated outputs
EC2 sync bundles
S3 downloads
```

## Branching strategy

```text
main
  stable, validated cumulative blueprint and implementation files

dev/wave-XX
  active work for a wave

runtime-proof/wave-XX
  optional branch for proof manifests/logs, not large generated media

hotfix/...
  urgent fixes to scripts or validation rules
```

## Commit requirements

Each commit must include:

```text
wave number
purpose
files changed
validation result
no model-binary confirmation
```

Example:

```text
Wave 01: add local repo bootstrap and EC2 guard docs

Validation:
- JSON files parse
- no forbidden model files
- pack validation passed
```

## Pull request requirements

Every PR must include:

```text
[ ] Wave number
[ ] Source files updated
[ ] Schemas valid
[ ] Workflow JSON parses
[ ] No models committed
[ ] No generated output committed
[ ] Local QA report attached
[ ] EC2 not used OR EC2 proof manifest attached
```

## GitHub Actions

A static validation workflow should run on pull requests and pushes. It must:

```text
- check JSON parse
- check no forbidden model extensions
- check required directories
- check schema files parse
- run Python syntax compile
```

## Protection rule

Do not merge to `main` unless static validation passes.
