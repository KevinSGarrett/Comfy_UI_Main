# Wave 35 Detailed Repository Structure

The repository should be the clean source-controlled brain of the project.

```text
repo/
├── README.md
├── CHANGELOG.md
├── docs/
│   ├── architecture/
│   ├── runbooks/
│   ├── qa/
│   ├── app_mode/
│   ├── ec2/
│   └── handoff/
├── schemas/
│   ├── workflow/
│   ├── manifests/
│   ├── registries/
│   ├── qa/
│   └── release/
├── registries/
│   ├── workflows/
│   ├── models/
│   ├── loras/
│   ├── prompts/
│   ├── app_mode/
│   ├── qa/
│   └── release/
├── workflows/
│   ├── comfyui/
│   │   ├── canonical/
│   │   ├── image/
│   │   ├── video/
│   │   ├── audio/
│   │   ├── qa/
│   │   └── archive/
│   ├── app_mode/
│   └── templates/
├── scripts/
│   ├── validation/
│   ├── cataloging/
│   ├── migration/
│   ├── release/
│   ├── local_runtime/
│   └── ec2/
├── manifests/
│   ├── examples/
│   ├── templates/
│   └── release/
├── app/
│   ├── app_mode/
│   ├── controls/
│   ├── presets/
│   └── profiles/
├── tests/
│   ├── unit/
│   ├── validation/
│   └── fixtures/
├── ec2/
│   ├── templates/
│   ├── sync/
│   └── runbooks/
└── releases/
    ├── notes/
    ├── manifests/
    └── certification/
```

## Do not store in repo

- giant checkpoint/model/LoRA files
- generated output dumps
- cache folders
- private local absolute paths except in templates/examples
- uncompressed raw evidence dumps
