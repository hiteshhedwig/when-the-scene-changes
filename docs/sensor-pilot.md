# Paired transient camera-input pilot

This protocol was frozen before any disturbed-policy outcomes were observed. Reference: the completed clean pilot in `results/clean-baseline-v1` (10/10 successes, one task). State 0 is a development scene used to choose the fixed occlusion rectangle, so this is exploratory work.

## Frozen intervention

For the same task, initial-state IDs 0–9, environment seed 0, model revision/precision, ten settling steps, and a 220-policy-action budget:

- Brightness: multiply RGB pixels by 0.35, round, and retain uint8 representation.
- Occlusion: fill the fixed rectangle x=40..135, y=104..199 with black in a 256×256 camera image. It covers 96×96 pixels (14.06% of the image), chosen on the existing state-0 scene to overlap the manipulation area.
- Apply either condition before policy calls at zero-based action steps 30–59 inclusive, after the camera rotation and before cloud preprocessing. Normal camera input resumes at step 60.
- No recovery monitor or custom retry is enabled. Simulation pauses during each model request.

This evaluates transient sensor-input corruption, not physical lighting changes or an object moving. A restored image allows the base closed-loop policy to recover naturally; that recovery is part of the baseline policy behavior.

Exact machine-readable settings are in `configs/disturbances-v1.json`; a frozen copy and SHA-256 are saved in the result directory. Severity will not be changed in response to this pilot's outcomes.

## Run/resume

With the endpoint/token environment variables set:

```bash
MUJOCO_GL=glfw .venv-libero/bin/python scripts/run_sensor_pilot.py
```

The batch checks that cloud policy metadata still matches the clean pilot, skips completed initial states, preserves failed technical attempts, and stops on an endpoint/runtime error. Technical errors are not counted as model task failures.

Results: `results/sensor-perturbations-v1/`. Each condition has its own manifest, summary, CSV, and per-state attempts. `comparison.json` tracks valid paired outcomes, lost clean successes, and paired success-rate differences. Pending states remain explicit.

## Episode artifacts

- `episode.mp4`: original simulator camera, including the unmodified world during the intervention.
- `policy-input.mp4`: exact rotated RGB frames sent to the model before cloud-side resizing/cropping, one per request.
- `disturbance-raw.png` and `disturbance-input.png`: paired images at intervention onset.
- `post-disturbance-input.png`: input after normal visibility returns, when the run reaches that step.
- `actions.jsonl`: controls, task success, timings, intervention flag, and input brightness/black-pixel fraction.
- `report.json`: fixed parameters, actual number of disturbed input steps, final task outcome, and termination reason.

The two videos intentionally have different frame alignment: the raw video includes an initial frame and post-action observations; policy input is captured before each action. Align by action index rather than blindly matching frame numbers. Network waits are excluded from playback.

## Validation

The first brightness trial's initial image matched its clean pair exactly, all first 30 actions matched, and the saved brightness image matched the intended transform exactly. Four focused tests cover timing boundaries, normal-image restoration, patch area, immutability of raw observations, and invalid configurations. The clean-input path remains pixel-identical.

Do not infer robustness across tasks, physical robots, or arbitrary corruptions from this small one-task pilot. Compare success rates on matched completed states; compare action counts only with their censoring/termination status visible.

## Recorded interruption (resolved)

The first two brightness states completed successfully (76 and 80 actions, versus clean 76 and 78). State 2 reached 69 actions, then a transport error stopped it; health subsequently returned Cloudflare tunnel error 1033. At that point its outcome was pending and the attempt was preserved as a technical error; eighteen of the twenty planned episodes were still pending. The fresh state-2 retry later completed its full budget and is included as a task failure. The endpoint was replaced and the pilot resumed; completed states were preserved and state 2 was retried from its original initial state. See `results/sensor-perturbations-v1/progress.md`.

## Offline replay

Recorded actions can be replayed with no endpoint and no local model weights:

```bash
MUJOCO_GL=glfw .venv-libero/bin/python scripts/replay_episode.py results/sensor-perturbations-v1/brightness_shift/state-00/attempt-01
```

The replay writes an original-camera video, an object/end-effector state trace, and a validation report under the episode's `replay/` directory. The first completed brightness trial reproduced its initial frame and all 76 success flags exactly. This is replay of recorded controls, not live model inference. A replay that diverges fails validation and must not be used as original ground truth.

## First completed failure analysis

The fully completed state-2 brightness retry exhausted 220 actions, while its clean pair succeeded in 85. The initial image and first 30 controls matched the clean pair; its 30 disturbed frames were verified. Offline replay reproduced all 221 decoded video frames exactly and showed only 10.50 mm maximum target lift and 3.57 mm maximum XY displacement. The full evidence note is `results/sensor-perturbations-v1/failure-analysis-brightness-state-02.md`. This is an observed grasp/transfer failure, not an inference about the model's internal reasoning.

## Completed result

All twenty valid disturbed trials completed: brightness 9/10 successes; fixed occlusion 0/10; clean reference 10/10. One technical transport attempt is preserved but excluded. All twenty disturbed trials matched the corresponding clean initial image and all first thirty controls; timing and onset transformations passed validation. See `results/sensor-perturbations-v1/report.md` for the complete paired table, figures, videos, and limitations. The bounded recovery intervention has not been implemented or evaluated.
