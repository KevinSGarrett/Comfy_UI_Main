# Wave 34 App Mode Release Architecture

App Mode becomes the user-facing control surface for the system.

## App Mode control groups
- scene request
- character selection
- reference assets
- camera/framing
- pose/action
- contact/interaction
- image lane
- video/GIF lane
- audio lane
- preview budget
- final render preflight
- QA/promotion status

## App Mode release requirements
- controls are mapped to schemas
- unsafe combinations are blocked by compatibility gates
- model/LoRA stacks are selected by profiles, not by enabling every library node
- preview-first workflow is enforced
- final render requires preflight pass
- output artifacts are linked to manifests
