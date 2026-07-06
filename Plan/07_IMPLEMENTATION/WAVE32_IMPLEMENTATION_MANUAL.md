# Wave 32 Implementation Manual

## Local workflow
1. Generate or collect planned_state.
2. Generate or collect generated_state.
3. Run the state-diff compiler.
4. Score state-diff QA.
5. Decide the smallest rerun scope.
6. Create or update revision/take/variant ledgers.
7. Promote only when state diff and QA pass.
8. Record successful-run learning only with evidence.

## Required artifacts
- planned state manifest
- generated state manifest
- state diff report
- revision/take/variant ledger
- targeted rerun plan
- learning record
