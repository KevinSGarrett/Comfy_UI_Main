# Wave 63 Scope

Wave 63 adds EC2 cost-control, local ComfyUI development, CI preflight packaging, and runtime no-loop guardrails.

The goal is to keep autonomous work moving while EC2 is stopped, then use the paid GPU instance only for target-runtime proof, generation, pullback, and QA.

## In Scope

- Local ComfyUI dev preflight for cheap lane/prompt iteration.
- GitHub Actions preflight/package workflow that does not require EC2 to be running.
- Deploy bundle creation from validated run packages.
- EC2 helper cost controls: explicit runtime limits and opt-in Git LFS pulls.
- Instruction updates that keep future sessions from repeating completed lane proof or housekeeping.

## Out Of Scope

- Replacing EC2 final proof with local GPU proof.
- Direct mutation of a stopped EC2 disk from GitHub Actions.
- Spot migration for final proof.
- Hibernation on the current instance.
