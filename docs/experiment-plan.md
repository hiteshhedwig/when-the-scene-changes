# Experiment specification

Question: How does a pretrained instruction-conditioned manipulation policy respond to changes during execution, and can a bounded recovery mechanism improve completion?

## Baseline gate

Use LIBERO-Spatial with a checkpoint specifically fine-tuned for that suite. Confirm camera preprocessing, action normalization, robot embodiment, and checkpoint settings against upstream evaluation. Record checkpoint revision, simulator revision, dependency versions, hardware, precision/quantization, seed, task, and initial-state ID. First obtain a successful episode; then run repeated clean episodes. Do not attribute baseline integration failures to robustness.

The chosen architecture runs simulation locally and model inference remotely. Both the basic MuJoCo check and a full local LIBERO-Spatial robot rendering check passed. Model integration remains unverified. Pause simulated time while waiting for remote actions and log request latency separately. The earlier cloud notebook is optional and is not the chosen simulator deployment.

## Pilot

Choose one task after inspecting its objects and success condition. Use 10 fixed initial-state IDs, paired across conditions. Treat this as a pilot, not a statistically conclusive benchmark. Expand to at least three tasks before making broad claims.

Conditions:

1. Clean baseline.
2. Camera-image brightness shift at a recorded control step. Label this as a sensor perturbation, not a physical lighting change.
3. Partial camera occlusion at a recorded control step. Preserve the raw observation separately.
4. Target displacement before contact. Implement only after identifying the task's free object joint and verifying valid collision-free placement. Update physics consistently, record the before/after pose, and exclude invalid interventions with stated reasons. Never teleport a grasped object.

Use two severity levels for each disturbance, calibrated on development scenes and frozen before evaluation. Separate episode-start shifts from mid-episode interventions. Keep task semantics and success predicates unchanged.

## Recovery comparison

First use a privileged simulator-state progress monitor as a diagnostic baseline. It can request reobservation, a bounded retry, or stop. A policy already replans from observations; merely calling it again is not a new recovery method. Specify exactly what a retry changes and count interventions. A reset is a new attempt, never a successful continuation of the original episode.

Later replace privileged state with a camera-based monitor and measure the additional error. Report those results separately.

Compare clean/disturbed conditions with and without recovery using identical initial states, policy settings, and horizons. Fix the total step budget, and report recovery overhead and false interventions on clean runs.

## Artifacts and metrics

Per episode: task instruction, seed, initial-state ID, condition, severity, disturbance step, policy revision, precision, final success, steps, wall time, intervention count, termination reason, raw video, policy-input video, and action trace.

Report task success and paired changes in success, recovery success, false intervention rate, and completion time. Include confidence intervals once the run count supports them. Simulator success predicates are the primary outcome; monitor predictions are not ground truth. Any safety metric requires a concrete constraint definition.

## Portfolio deliverable

A short side-by-side video, reproducible run configuration, results table, representative failures, and an honest limitations section. Simulation-only results do not establish real-robot safety or sim-to-real transfer.
