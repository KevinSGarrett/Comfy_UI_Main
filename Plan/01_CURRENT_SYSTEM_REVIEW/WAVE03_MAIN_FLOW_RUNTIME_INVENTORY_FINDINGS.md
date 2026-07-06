# Wave 03 Current Main Flow Runtime Findings

## Static validation result

```text
PASS
```

No missing source/target nodes or broken link references were found in the static graph check.

## Main structure

The flow contains:

```text
356 nodes
91 links
28 unique node types
7 KSampler nodes
8 SaveImage nodes
8 PreviewImage nodes
287 model/asset references
```

## Active/staged split

Only `69` nodes are upstream of enabled terminal outputs. `287` nodes are not upstream of enabled terminal outputs.

This confirms the current canvas should be treated as:

```text
runtime-bound source canvas
+ staged reference lanes
+ disabled/catalog LoRA library
+ partial QA/export notes
```

not as a finished autonomous production pipeline.

## LoRA/library status

The main flow includes a large library of disabled model nodes. This is not inherently wrong. It is correct if those nodes remain catalog/selector entries.

However, Wave 03 requires future production modules to prove:

```text
selected engine
selected model/checkpoint
selected LoRA stack
selected pass scope
selected mask scope
selected output proof
```

before any of those library assets become production-active.

## Runtime proof not completed in Wave 03 pack generation

The generated pack did not contact a live local or EC2 ComfyUI runtime. Therefore:

```text
static graph = checked
object_info = not checked
model loader proof = not checked
GPU render proof = not checked
creative QA = not checked
```

This is intentional. Wave 03 gives the AI project manager the tools to run those checks in the local repo.
