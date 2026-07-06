# Wave 13 — Mask Factory Test Matrix

| Test ID | Scenario | Required Masks | Expected Result |
|---|---|---|---|
| MF-001 | Single character portrait | person, face, hair, body outline | valid |
| MF-002 | Two-character half-body frame | two person instances, face/hair/hands, boundary contact | valid |
| MF-003 | Full-body scene | person, limbs, feet/floor contact, macro floor/background | valid |
| MF-004 | Fabric detail repair | garment, panel, fold, seam | valid |
| MF-005 | Hand/object interaction | hand mask, object mask, contact edge | valid |
| MF-006 | Mask bleeds across two people | two person masks with shared unassigned pixels | blocked |
| MF-007 | Body-part mask without person owner | hand mask with no person ID | blocked |
| MF-008 | Nano mask used for full pose rewrite | nano mask + high denoise | blocked |
| MF-009 | Video sequence with drifting person mask | temporal drift > threshold | blocked |
| MF-010 | Missing runtime mask files | contract only | blocked from promotion |
