# Wave 20 AI PM Tasks

1. Convert user-visible hard-anatomy problems into structured repair requests.
2. Bind each repair to a character id, region id, crop box, mask id, and QA goal.
3. Decide whether the region needs face, eye, mouth/teeth, hand/finger, foot/toe, or nail lane handling.
4. Use low-denoise repair first, then bounded reruns if QA fails.
5. Preserve identity, pose, body proportions, crop boundaries, clothing/contact continuity, and environment lighting.
6. Promote only when local anatomy improvement and global continuity both pass.
