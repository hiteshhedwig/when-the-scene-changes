# Validation and experiment status

The full pilot is complete: ten clean reference episodes, ten brightness episodes, and ten occlusion episodes. Valid outcomes are 10/10, 9/10, and 0/10 successes respectively.

## Completed-episode checks

- All twenty disturbed trials have a completed success or step-limit outcome; there are no pending cases.
- Every initial RGB image matches its clean reference exactly.
- All 600 pre-intervention controls (30 per disturbed trial) match their clean references exactly.
- Perturbations are active at precisely zero-based policy steps 30–59. All completed trials reach the end of that window; normal images return at 60.
- Saved intervention-onset images match the frozen pixel transforms exactly, including the 96×96 occlusion geometry.
- Action-trace lengths match reported completed steps. All step-limit failures exhaust 220 actions. Episode and policy-input recordings are saved for every valid trial.
- One earlier brightness state-2 attempt ended after 69 controls because the tunnel stopped. It is preserved as a technical error. Its fresh, fully completed retry supplies the state-2 outcome; the interrupted attempt is not counted as a task failure.
- The batch stopped on the transport error and resumed with compatible policy metadata using the replacement endpoint. Completed states were skipped and source settings remained unchanged.

Machine-readable checks: `artifact-validation.json`, `comparison.json`, each condition's CSV/summary, and per-episode reports/action logs.

## Software checks

Thirteen focused tests passed: four camera-perturbation tests, five aggregation/settings-validation tests, one paired-comparison test, and three prompt/mask regression tests. They cover exact timing boundaries, image restoration, patch area, raw-image immutability, invalid parameters, compatible pairing, correct treatment of technical interruptions, and the terminal-token alignment fix.

Five HTTP protocol tests passed earlier with a local mock server, and an actual mock-policy LIBERO rollout passed. A later rerun of the socket-based tests was blocked by the execution sandbox's socket permissions; this is separate from robot trial outcomes. Actual cloud-model rollouts exercised the client/server path for all valid episodes.

The complete comparison chart, intervention-image figure, and sample comparison videos were generated from recorded data. The brightness counterexample and its clean pair were replayed locally: all 221 and 86 decoded raw-video frames matched their originals respectively. Their state trajectories therefore support the recorded object-motion comparison. The occlusion state-0 replay reproduced its initial frame and all 220 success flags; no stronger pixel-equivalence claim is made for that replay.

## Limits

This is a developmental pilot using one manipulation task and ten fixed initial states. State 0 informed patch placement and its exploratory clean success was reused. These results do not establish broad VLA robustness, real-time physical deployment, or real-robot safety. Quantization/attention settings differ from upstream published benchmark settings. No custom recovery intervention has been evaluated.
