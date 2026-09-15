# Observed failure: transient brightness fault, state 2

Clean reference: successful placement after 85 policy actions. Disturbed trial: no success within 220 actions. Brightness was multiplied by 0.35 at actions 30–59; normal input returned at action 60. The earlier technically interrupted attempt is excluded; this note concerns the fresh, fully completed attempt 2.

## Evidence

- The initial image and all 30 pre-intervention actions matched the clean pair exactly.
- All 30 scheduled input frames were darkened; saved onset pixels match the prescribed transform exactly.
- The completed disturbed trial made 220 valid model requests/actions with no transport error.
- Original-camera video shows the robot approaching the bowl and later moving toward the plate while the target remains on the table.
- Offline replay reproduced the initial image, all 220 success flags, and all 221 decoded raw-video frames exactly (maximum pixel difference 0).
- In that validated replay, the target bowl's maximum upward motion was 10.50 mm and its maximum XY displacement from the start was 3.57 mm. It was not transported to the plate.

This supports an observed grasp/transfer failure and failure to recover within the fixed budget after image restoration. It does not establish the model's internal reason for the failure, or a failure rate beyond the completed paired trials.

## Artifacts

- [Raw simulator video](brightness_shift/state-02/attempt-02/episode.mp4)
- [Model-input video](brightness_shift/state-02/attempt-02/policy-input.mp4)
- [Final simulator scene](brightness_shift/state-02/attempt-02/replay/final-scene.png)
- [Replayed state trace](brightness_shift/state-02/attempt-02/replay/trajectory.jsonl)
- [Replay validation](brightness_shift/state-02/attempt-02/replay/report.json)
- [Episode outcome](brightness_shift/state-02/attempt-02/report.json)

The replay uses recorded controls and no model inference. It supplies a reproducible local debugging artifact rather than another policy trial.

## Presentation artifacts

- [Synchronized comparison video](brightness-state-02-comparison.mp4): clean raw view, disturbed raw view, and disturbed model-input view. Clean playback freezes after its 85-action success; the other panels continue to the 220-action limit. Network waits are omitted. This is recorded episode footage, not a live model demonstration.
- [Target trajectory chart](state-02-trajectory.png): the clean pair lifted the target 108.16 mm and moved it up to 195.64 mm in XY; the brightness run reached only 10.50 mm lift and 3.57 mm XY displacement. The clean replay also matched all 86 decoded video frames exactly.
