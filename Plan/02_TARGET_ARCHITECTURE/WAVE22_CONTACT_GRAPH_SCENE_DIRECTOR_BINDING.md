# Wave 22 Contact Graph Scene Director Binding

The Scene Director must convert plain user intent into a contact graph before the orchestrator creates passes.

## Scene Director output
- contact graph id
- contact edge list
- source/target ownership
- pressure/intensity profile
- occlusion profile
- duration class
- mask requirements
- soft-body profile references
- audio force events
- QA goals

## Planning rule
The Scene Director may propose contact, but the orchestrator must verify masks, ownership, and expected visual/audio evidence before running or promoting a pass.
