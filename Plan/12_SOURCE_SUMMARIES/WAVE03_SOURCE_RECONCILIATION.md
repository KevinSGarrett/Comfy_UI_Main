# Wave 03 Source Reconciliation

## Current Wave42 main flow

The current attached main flow is treated as the active runtime-bound source for image-generation validation. Static inventory extracted:

```text
nodes: 356
links: 91
node types: 28
terminal outputs: 16
asset/model references: 287
```

## Wave42 tracker CSV

The tracker is treated as ongoing/mutable upstream project state.

```text
rows: 12887
columns: 73
top statuses: [('Not Started', 12870), ('Package Marked Complete; Verify Local', 16), ('Package Received', 1)]
```

## Plans ZIP

The Plans ZIP is treated as ongoing/mutable upstream planning and implementation material.

```text
entries: 6307
files: 4870
directories: 1437
```

## Advanced Additions ZIP

The Advanced Additions ZIP continues to feed later waves. Wave 03 does not implement those features; it ensures their future workflow modules can be validated through the same runtime harness.

```text
entries: 21
files: 20
```

## Assistant replies ZIP

The assistant replies ZIP remains conversation-context source material for project requirements.

```text
entries: 4
files: 4
```

## Boundary

Wave 03 does not freeze any of these inputs. Future waves must re-ingest updated versions when provided.
