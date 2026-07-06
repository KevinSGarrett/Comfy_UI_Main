# Wave 37 Repo Cleanup and Source-Control Hardening

## Repo cleanup targets

- generated outputs
- heavy model files
- cache folders
- pycache folders
- logs
- local-only config
- private credentials
- duplicate canonical workflows
- superseded experimental files

## Recommended repo hardening

```text
.gitignore
.gitattributes
pre-commit validation
catalog refresh check
schema validation check
script compile check
release manifest check
```

## Repo rule

The repo should contain source logic and metadata, not the whole local runtime.
