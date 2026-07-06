# Wave 13 — Person-Instance and Body-Part Masks

## Person-instance mask

A person-instance mask is the first mask every multi-character scene needs.

It answers:

```text
Which pixels belong to Character A?
Which pixels belong to Character B?
Where do they overlap?
Which person is in front?
Which person owns each body part?
```

## Body-part masks

Body-part masks are subordinate to person-instance masks. A hand mask, face mask, or torso mask is invalid if it is not assigned to a person instance.

## Required identity protection

Face, hair, body outline, and locked outfit regions should be protected during local edits unless the Scene Director explicitly requests a revision.

## Multi-character prevention

This wave blocks masks that bleed across two characters, merge bodies, swap limbs, or leave body parts unassigned.
