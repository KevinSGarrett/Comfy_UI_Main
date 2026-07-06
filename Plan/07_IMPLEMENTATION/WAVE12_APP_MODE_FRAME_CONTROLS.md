# Wave 12 App Mode Frame Controls

Expose frame composition as clean controls instead of raw node graph edits.

## Controls

- Expected character count.
- Shot size.
- Body visibility profile.
- Require full head visibility.
- Require hands visible.
- Require feet visible.
- Safe margin amount.
- Prevent merged bodies.
- Allow intentional occlusion.
- Allow background people.
- Auto-repair cropped outputs.

## Operator rule

The operator should not have to know which detector, pose, or mask node enforces a rule. App Mode should expose the intent; the orchestrator should compile it into the correct contract and QA gates.
