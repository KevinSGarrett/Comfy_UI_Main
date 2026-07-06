# AWS Cost-Control Templates

These templates support the Wave 63 low-cost runtime path.

They are intentionally placeholders. Replace bracketed values such as
`<bucket-name>`, `<account-id>`, `<github-owner>`, and `<github-repo>` before
applying them in AWS.

Use these policies to keep EC2 on-time short:

- GitHub Actions prepares deploy bundles while EC2 is stopped and uploads them
  to S3.
- EC2 downloads only the selected bundle/model from S3, verifies hashes, runs
  target-runtime proof, uploads artifacts, and stops.
- EventBridge Scheduler can create a one-time emergency stop schedule before a
  runtime window.

Do not store AWS credentials, GitHub tokens, Civitai keys, model binaries, or
private keys in this directory.
