# Wave 11 Action Blocking and Scene Director Binding

## Scene Director Expansion

The Scene Director must now output:

- action intent;
- subject count;
- per-character role;
- blocking slot;
- camera relation;
- required body visibility;
- required hand/face visibility;
- per-character skeleton requirement;
- control map requirements;
- mask requirements;
- QA goals.

## Example Binding

A request such as "two people sitting at a table, one reaching for a cup" becomes:

- Character A seated, foreground left.
- Character B seated, midground right.
- Cup prop on table.
- DWPose skeleton for each character.
- Depth map for table/body relation.
- Canny or lineart map for table and cup edges.
- Hand mask for reaching arm.
- QA: hand reaches cup, cup stays scaled, character identities remain separated.

## Blocking Rules

- No multi-character scene is promoted without depth-layer assignment.
- No contact/intersection scene is promoted without occlusion/mask plan.
- No full-body scene is promoted if feet/hands/limbs are cut off unless the camera plan explicitly allows it.
