# Clean baseline pilot

Run one LIBERO-Spatial task on initial-state IDs 0–9. Keep environment seed 0, a 220-action budget, ten settling steps, the same model configuration, and simulation paused during remote inference. Technical errors are not classified as model task failures.

The previously successful state-0 episode is imported, with its origin recorded in the batch manifest. It is an exploratory run included in this pilot, so this is not an independent confirmatory evaluation.

## Run or resume

With `VLA_ENDPOINT` and `VLA_API_TOKEN` set in the terminal:

```bash
MUJOCO_GL=glfw .venv-libero/bin/python scripts/run_clean_baseline.py \
  --import-episode results/remote-20261115-121101-279390
```

The batch writes to `results/clean-baseline-v1/`. Completed states are skipped when the command is rerun. Incomplete or errored attempts are preserved and retried under a new attempt directory. An episode error stops the batch rather than wasting further requests on a broken endpoint. A changed endpoint URL is fine if its policy metadata is identical; changed model settings require a separate batch directory.

Files:

- `manifest.json`: settings, imported origins, batch status, active state.
- `episodes.csv`: completed and pending states, success, steps, latency, error-attempt counts, artifact locations.
- `summary.json`: completion counts, task success rate, and a descriptive binomial interval.
- `state-XX/attempt-YY/`: episode report, action trace, and video.
- `state-XX/attempt-YY.log`: setup and step-level logs.

The interval is conditional on a binomial model and does not establish generalization from ten fixed states of one task. A final success rate must state its denominator, pending states, and technical errors.

## Disturbance comparison, after this pilot

Use the identical initial states and policy settings. Freeze sensor perturbation timing and severity before evaluating them. Preserve raw camera recordings separately from perturbed policy inputs. Start with brightness and partial occlusion; label them as camera-input perturbations. Physical object displacement requires separate validation of the simulator intervention.

## Completed result

All ten fixed initial states succeeded (one prior exploratory state-0 run plus nine new states). Action counts were 76, 78, 85, 74, 76, 74, 73, 82, 86, 78. Mean request latency was 1.634 seconds and no technical errors occurred. This measures one clean task and does not establish robustness to disturbances.

Generate the completed report and chart with:

```bash
.venv-libero/bin/python scripts/report_clean_baseline.py
```

The report is in `results/clean-baseline-v1/report.md`; validation details are in the neighboring `validation.md`.
