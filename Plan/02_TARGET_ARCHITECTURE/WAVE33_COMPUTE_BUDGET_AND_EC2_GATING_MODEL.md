# Wave 33 Compute Budget and EC2 Gating Model

The compute budget controls when local, cheap, or EC2 rendering is allowed.

## Compute tiers
- local_metadata_only
- local_preview
- cheap_gpu_preview
- ec2_preview
- ec2_final
- ec2_hero_final

## EC2 block policy
EC2 final render is blocked unless:
- proxy preview plan exists
- preview output exists
- preview QA passes
- realism budget exists
- compute budget exists
- final render preflight passes
- expected final cost is accepted by policy
