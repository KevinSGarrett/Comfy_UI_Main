# Prompt and Negative Prompt QA Protocol

## Purpose

This protocol evaluates prompts, negative prompts, and prompt-control assets for clarity, controllability, contamination resistance, and outcome alignment.

## Review areas

- prompt intent clarity
- subject specificity
- composition clarity
- style control quality
- realism instruction quality
- contradiction detection
- ambiguity level
- negative prompt effectiveness
- contamination resistance
- unwanted style leakage
- compatibility with target model family
- repeatability / portability across workflow lanes

## Review flow

1. Read prompt and intended objective.
2. Identify internal contradictions or omissions.
3. Determine whether the prompt is over-constrained or under-specified.
4. Determine whether the negative prompt meaningfully addresses common failure modes.
5. Test at least one representative generation if prompt approval is required.
6. Record observed output alignment.

## Common failure patterns

- conflicting instructions
- vague realism targets
- style contamination
- too many competing modifiers
- prompt not adapted to engine family
- negative prompt suppressing desired attributes
- negative prompt ineffective against known artifact patterns

## Approval rule

Prompt assets may be marked approved only when:

- the prompt objective is clear
- the prompt is structurally usable
- representative test output aligns with intent, or pending runtime test is explicitly recorded
- known limitations are documented
