# Wave 35 Environment, Config, and Secrets Structure

## Config belongs in templates

Repo can store:

```text
.env.example
config.template.json
paths.template.json
ec2_sync.template.json
```

## Secrets do not belong in repo

Local secret locations:

```text
00_ADMIN/secrets_local_notes/
02_COMFYUI_RUNTIME/runtime_config/local_only/
```

## Rule

Never place real API keys, cloud credentials, or private absolute secrets into release packs.
