# Wave 07 LLM Scene Director QA Gates

## Static QA gates

Wave07 must pass static QA before use:

1. JSON registries parse.
2. Scene Director schemas exist.
3. Example request exists.
4. Example plan exists.
5. Example plan includes required top-level fields.
6. Director profiles exist.
7. Intent taxonomy exists.
8. Pass compiler rules exist.
9. QA goal catalog exists.
10. Main Flow source summary exists.
11. Scripts compile.
12. Validation report exists.

## Plan QA gates

Every generated plan must include:

- plan ID
- request ID
- director profile
- normalized request
- intent classification
- ambiguity resolution
- scene graph
- camera plan
- mask plan
- model-selection plan
- engine route
- pass plan
- QA goal plan
- promotion requirements
- evidence requirements

## Engine/model QA gates

Before execution:

- selected engine IDs must exist in Wave06 registry
- selected models must exist in model registry or be marked pending/proof-required
- wrong-engine LoRAs must be blocked
- rejected/superseded assets must be blocked
- cross-engine bridge must be image-file based

## Mask QA gates

For regional passes:

- mask IDs must exist
- target region must be defined
- protect regions must be defined when needed
- overlay evidence must be required
- no-bleed check must be required

## Runtime QA gates

Runtime proof is not part of static Wave07 packaging, but future runtime must prove:

- ComfyUI object_info contains required nodes
- selected model loaders can load
- outputs are produced
- outputs decode
- output SHA256 recorded
- QA evidence exists
- promotion decision is explicit

## Promotion rule

A Scene Director plan alone can never promote an output.

Promotion requires actual runtime evidence and QA pass.
