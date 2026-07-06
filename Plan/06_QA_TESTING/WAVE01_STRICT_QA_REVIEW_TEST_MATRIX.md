# Wave 01 Strict QA Review and Test Matrix

## Wave 01 objective

Prove the local/GitHub/EC2/S3 development structure is safe, reproducible, cost-aware, and ready for future image/video/audio implementation.

## Test categories

### QA-01 — Source inventory

Required proof:

```text
wave01_source_inventory.json exists
all uploaded source files are listed
each source has sha256
each source has size_bytes
tracker and Plans are marked mutable/ongoing
```

### QA-02 — Local repo structure

Required directories:

```text
docs/
workflows/
orchestration/
schemas/
configs/
scripts/
manifests/
evidence/
tests/
app_mode/
external_assets/
.github/workflows/
```

### QA-03 — Git safety

Required proof:

```text
.gitignore exists
.gitattributes exists
no model binaries in repo
no ComfyUI output folders in repo
no raw EC2 sync bundles in repo
```

Forbidden extensions:

```text
.safetensors
.ckpt
.pt
.pth
.bin
.gguf
.onnx
.engine
.trt
.mp4
.mov
.avi
.mkv
.wav
.flac
.zip
.7z
.rar
```

### QA-04 — JSON and schema parsing

Required proof:

```text
all .json files parse
all .schema.json files parse
example manifests parse
project manifest parses
```

### QA-05 — EC2 off-by-default guard

Required proof:

```text
EC2 guard script exists
script defaults to dry-run
script refuses live start without START_EC2_RUNTIME_PROOF token
script requires runtime proof request file
```

### QA-06 — S3 hydration safety

Required proof:

```text
model hydration is manifest-based
dry-run mode is default
sync all models is forbidden
hydrate exact required assets only
```

### QA-07 — Current main flow boundary

Required proof:

```text
main flow summary exists
current main flow is classified as runtime-bound source
large disabled LoRA library is not treated as active production
flow is not used as repo architecture
```

### QA-08 — No false runtime claims

Wave 01 cannot claim:

```text
runtime generation works
models load
video works
audio works
visual QA passed
EC2 proof passed
```

unless corresponding runtime evidence exists.

## Wave 01 pass/fail rule

Wave 01 passes only if:

```text
source inventory PASS
repo template PASS
JSON parse PASS
no model binary policy PASS
EC2 guard PASS
S3 hydration rule PASS
validation report written
```
