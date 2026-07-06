# Wave 08 — Reference Pack Test Matrix

| Test ID | Test | Local? | EC2? | Expected Result |
|---|---|---:|---:|---|
| W08-RP-001 | Character Bible JSON parses | Yes | No | PASS |
| W08-RP-002 | Identity registry JSON parses | Yes | No | PASS |
| W08-RP-003 | Reference pack manifest parses | Yes | No | PASS |
| W08-RP-004 | Required fields present | Yes | No | PASS |
| W08-RP-005 | File paths are not Git-binary paths | Yes | No | PASS |
| W08-RP-006 | SHA256 fields are populated for real assets | Yes | No | PASS for real packs |
| W08-RP-007 | Character ID/version consistency | Yes | No | PASS |
| W08-RP-008 | Scene Director binding resolves character | Yes | No | PASS |
| W08-RP-009 | Per-character mask plan exists for multi-character scenes | Yes | No | PASS |
| W08-RP-010 | ComfyUI reference node can load approved reference | No | Yes/local runtime | REQUIRED LATER |
| W08-RP-011 | Generated output matches character | No | Yes/local runtime | REQUIRED LATER |
| W08-RP-012 | Video/audio continuity matches character | No | Yes/local runtime | REQUIRED LATER |

## Local First Rule

Local validation proves file structure, schemas, manifests, and consistency. Runtime validation proves that references and models actually preserve identity in generated media.
