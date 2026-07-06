# Wave 32 Revision and Take Ledger Model

## Revision ledger
Tracks intentional changes:
- revision_id
- parent_revision_id
- change_reason
- changed_domains
- changed_fields
- expected impact
- approval/promotion status

## Take ledger
Tracks generated candidates:
- take_id
- parent_revision_id
- seed/config reference
- output artifact paths
- QA summary
- state diff summary
- rerun decision
- promotion decision

## Difference
A revision is a planned change. A take is a generated attempt.
