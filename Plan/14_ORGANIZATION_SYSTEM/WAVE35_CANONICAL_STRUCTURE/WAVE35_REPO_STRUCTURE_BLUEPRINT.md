# Wave 35 Repository Structure Blueprint

Recommended repository root:

```text
repo/
├── docs/
│   ├── architecture/
│   ├── runbooks/
│   ├── qa/
│   └── handoff/
├── schemas/
├── registries/
├── workflows/
│   ├── comfyui/
│   ├── app_mode/
│   └── templates/
├── scripts/
│   ├── validation/
│   ├── cataloging/
│   ├── migration/
│   └── release/
├── manifests/
│   ├── examples/
│   └── templates/
├── tests/
├── app/
├── ec2/
└── releases/
```

## Repo rule
The repo stores **logic, definitions, templates, and documentation**. It should not store giant model files or generated output dumps.
