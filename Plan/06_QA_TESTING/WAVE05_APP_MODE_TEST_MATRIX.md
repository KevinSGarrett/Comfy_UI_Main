# Wave 05 — App Mode Test Matrix

## Static tests

| Test ID | Test | Expected result |
|---|---|---|
| APP-001 | Parse App Mode control registry | PASS |
| APP-002 | Validate required groups exist | PASS |
| APP-003 | Verify no secret fields are visible controls | PASS |
| APP-004 | Verify camera/framing controls exist | PASS |
| APP-005 | Verify output type controls exist | PASS |
| APP-006 | Verify QA/promotion controls exist | PASS |
| APP-007 | Verify runtime target includes local static/local ComfyUI/EC2 | PASS |
| APP-008 | Verify App Mode is documented as UI only | PASS |

## Runtime tests for future waves

| Test ID | Test | Expected result |
|---|---|---|
| APP-R001 | App Mode opens without graph editing | required later |
| APP-R002 | Operator input generates structured request JSON | required later |
| APP-R003 | Invalid request is blocked before GPU run | required later |
| APP-R004 | EC2 cannot start unless runtime target and permission are explicit | required later |
| APP-R005 | App Mode submission writes run manifest | required later |
| APP-R006 | QA gate blocks final promotion by default | required later |
