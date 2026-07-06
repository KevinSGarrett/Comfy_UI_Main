# Bug / Issue / Fix Log Protocol

## Purpose

This protocol ensures failures, fixes, and retests are never lost between autonomous sessions.

## When to create an issue record

Create or update an issue record when Codex encounters:

- failed test
- broken path
- missing file
- model mismatch
- workflow runtime crash
- EC2/AWS access issue
- GitHub sync issue
- Civitai lookup/download issue
- QA defect
- incomplete evidence
- contradiction between tracker and files

## Required issue fields

- issue_id
- date/time
- severity
- category
- affected item / tracker ID
- affected file(s)
- observed behavior
- expected behavior
- suspected root cause
- fix attempted
- retest result
- current status
- next action

## Issue categories

- local_file_system
- github
- aws_ec2
- civitai
- model_registry
- comfyui_workflow
- image_quality
- video_quality
- audio_quality
- prompt_quality
- qa_evidence
- tracker_state
- unknown

## Fix record rule

Every fix must be tied to an issue ID.

## Retest rule

Every fix must have one of these retest statuses:

- retest_passed
- retest_failed
- retest_blocked
- retest_not_run_yet

## No-loop rule

If the same issue fails twice with the same fix attempt, Codex must not keep retrying the same action. It must change strategy, inspect deeper, or mark blocked with a new next action.
