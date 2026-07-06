# Wave 24 Instance Layout Scene Director Binding

The Scene Director must convert a plain request into an instance layout plan before routing multi-character scenes.

## Required output
- character_count_target
- instance list
- frame placement target for each instance
- depth ordering
- skeleton/control map assignment
- mask ownership assignment
- contact graph participation
- per-instance QA goals

## Example normalized request
"two people, one sitting behind the other" becomes:
- instance_A: foreground / lower frame / depth 0
- instance_B: background / upper frame / depth 1
- B behind A
- no merge allowed
- overlap only at declared contact/occlusion boundaries
