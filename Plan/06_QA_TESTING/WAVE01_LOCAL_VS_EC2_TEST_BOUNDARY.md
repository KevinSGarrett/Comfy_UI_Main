# Wave 01 Local vs EC2 Test Boundary

## Local tests are allowed to prove

```text
repo structure
file placement
JSON validity
schema validity
workflow JSON parse
static graph sanity
model registry shape
S3 path formatting
EC2 dry-run command construction
no forbidden model files in repo
source inventory completeness
```

## Local tests are not allowed to prove

```text
model load success unless model exists locally and ComfyUI loads it
GPU runtime performance
video generation quality
audio generation quality
soft-body realism
hand realism
multi-character visual truth
```

## EC2 tests are required to prove

```text
large model availability
GPU generation
ComfyUI runtime execution
model compatibility
node import/runtime availability
video engine execution
audio engine execution
final render proof
```

## Runtime proof promotion

A future runtime proof must produce:

```text
request manifest
workflow API JSON
model hydration manifest
ComfyUI object_info snapshot
ComfyUI /prompt response
ComfyUI /history response
output file manifest
sha256 records
QA report
cost/runtime notes
```
