# Done Certification and Evidence Protocol

## Purpose

This protocol defines the final gate for declaring any item complete.

## Absolute completion requirements

Completion requires all of the following:

1. implementation complete
2. test run complete
3. QA pass or approved conditional pass
4. artifact inspection complete
5. tracker update complete
6. itemized list update complete when applicable
7. known issue review complete
8. final done certification record created

If any step above is missing, the item is not done.

## Certification record must include

- certification ID
- task / tracker ID
- title
- artifact scope
- implementation summary
- tests performed
- QA summary
- evidence paths
- known issues or none
- final decision
- certifier = Codex Desktop autonomous release manager
- timestamp

## Allowed final decisions

- done
- done_with_non_blocking_notes
- pending_runtime_validation
- failed
- blocked

## Required evidence bundle

At minimum, the done bundle must point to:

- primary artifact path(s)
- QA record(s)
- runtime log(s) or validation note
- tracker record
- itemized list record if applicable
- failure / retest notes if there were prior failures

## Prohibited shortcut

Codex must never mark an item done merely because:

- the document was written
- the script exists
- the workflow JSON exists
- a single output was generated
- a test was attempted but not reviewed
