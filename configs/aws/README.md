# AWS Cost-Control Templates

These templates and canonical account policies support the low-cost runtime path.

Files ending in `.template.json` remain placeholders. Files without that suffix
are the canonical policies for this project/account and contain no secrets.

Use these policies to keep EC2 on-time short:

- GitHub Actions prepares deploy bundles while EC2 is stopped and uploads them
  to S3.
- EC2 downloads only the selected bundle/model from S3, verifies hashes, runs
  target-runtime proof, uploads artifacts, and stops.
- EventBridge Scheduler can create a one-time emergency stop schedule before a
  runtime window.
- The local main session uses a DPAPI-protected bootstrap key that can assume
  only `ComfyUIMainSessionRole`; routine AWS commands use short-lived STS
  credentials and root remains a named break-glass profile.
- GitHub OIDC trusts only the repository main branch and writes only to
  `deploy-bundles/github/`; it has no EC2 authority.
- Runtime-bucket lifecycle expires replaceable bundles and old output copies
  while preserving the model cache.
- `tools/aws/Test-ComfyUICloudControlPlaneDrift.ps1` performs a read-only
  comparison of the routine role, GitHub OIDC role, repository variables,
  runtime-bucket lifecycle, stopped-instance state, and marker state against
  these canonical controls. It reports the known EBS encryption/right-sizing
  blocker without starting EC2 or authorizing a migration.

Do not store AWS credentials, GitHub tokens, Civitai keys, model binaries, or
private keys in this directory.
