# When the Scene Changes

A VLA robustness pilot: can a robot finish an instruction after its camera input temporarily degrades?

OpenVLA controls a local LIBERO/MuJoCo Panda robot, with model inference on a cloud GPU. The task is to pick up the black bowl between the plate and ramekin and place it on the plate. No model weights are installed on the laptop.

## Measured result

Thirty valid episodes: ten fixed initial states under each of three conditions, with the same task, model settings, environment seed, and 220-action budget.

| Condition | Successful initial states |
| --- | ---: |
| Clean reference | 10/10 |
| Brightness ×0.35, actions 30–59 | 9/10 |
| Fixed 96×96 black patch, actions 30–59 | 0/10 |

Normal camera input returns at action 60. No custom recovery is enabled. The patch covers 14.06% of the 256×256 camera image and was chosen on the state-0 development scene to overlap the manipulation area. These are sensor-input corruptions, not physical lighting changes or object displacement.

- [Full report, per-state results, and videos](results/sensor-perturbations-v1/report.md)
- [Comparison chart](results/sensor-perturbations-v1/comparison.png)
- [Brightness counterexample video](results/sensor-perturbations-v1/brightness-state-02-comparison.mp4)
- [Occlusion counterexample video](results/sensor-perturbations-v1/occlusion-state-00-comparison.mp4)
- [Validated grasp/transfer failure analysis](results/sensor-perturbations-v1/failure-analysis-brightness-state-02.md)
- [Clean baseline report](results/clean-baseline-v1/report.md)

All twenty disturbed trials matched their clean pair's initial image and first thirty controls exactly. Perturbation timing and onset pixel transformations were verified. One interrupted transport attempt was preserved and retried from its initial state; it is excluded from model task outcomes.

## What this project implements

- A model-only authenticated cloud endpoint and a synchronous local robot client with action validation.
- Frozen, deterministic camera faults, paired trials, separate original-scene/model-input recordings, and per-action logs.
- Resumable batches that preserve technical errors and reject incompatible policy metadata or trial settings.
- A prompt-token/attention-mask compatibility fix, covered by regression tests.
- Offline replay of recorded controls with object/end-effector trajectories. The illustrated brightness counterexample reproduced every decoded video frame exactly.
- Portable reports, figures, source snapshots, and a source/data bundle.

This is integration, evaluation, and failure analysis of an existing pretrained policy; no new policy is trained here.

## Architecture

The laptop runs physics, camera rendering, fault injection, recording, and analysis. The cloud runs `openvla/openvla-7b-finetuned-libero-spatial` with 4-bit NF4 weights, FP16 computation, and eager attention. The checkpoint takes the agent camera and task instruction; it does not consume robot state or the wrist camera.

For each control step, the laptop sends a rotated RGB image and instruction, waits for one seven-dimensional action, validates it, and steps physics. **Simulation time pauses during inference.** Videos omit network waiting and therefore play faster than the wall-clock run. This is not a real-time physical-robot deployment.

## Run locally with a cloud model

The tested laptop uses a Ryzen 7 6800HS, about 14 GiB usable RAM, and working AMD OpenGL graphics. NVIDIA drivers were not required for local simulation. The isolated robot environment occupies about 2.3 GB, plus roughly 641 MB of LIBERO source/assets; some package-cache storage is shared. No policy weights or training datasets were downloaded locally.

For a fresh setup, install `uv` and Git, then run:

```bash
bash scripts/setup_local_libero.sh
```

Upload **`notebooks/02_cloud_model_only.ipynb`** to Colab, select a GPU runtime, and run the model and tunnel cells. Keep the runtime open. Follow [the remote setup guide](docs/remote-setup.md). The older `01_cloud_smoke.ipynb` is an optional cloud-simulator diagnostic and is not the chosen architecture.

On the laptop, enter the generated endpoint URL and the token you chose in Colab:

```bash
export VLA_ENDPOINT="https://YOUR-ENDPOINT.trycloudflare.com"
read -rsp 'API token: ' VLA_API_TOKEN
export VLA_API_TOKEN
MUJOCO_GL=glfw .venv-libero/bin/python scripts/run_remote_episode.py --steps 10
```

For a new clean/sensor experiment, use new output directories so existing results remain intact:

```bash
MUJOCO_GL=glfw .venv-libero/bin/python scripts/run_clean_baseline.py --output-dir results/new-clean-baseline
MUJOCO_GL=glfw .venv-libero/bin/python scripts/run_sensor_pilot.py --baseline results/new-clean-baseline --output-dir results/new-sensor-pilot
```

The batch commands resume completed work if rerun with matching settings. The [clean guide](docs/clean-baseline.md) and [sensor protocol](docs/sensor-pilot.md) explain artifacts and denominators. Package versions and simulator revision are recorded in `configs/`; cloud model revisions and precision are recorded in each episode report.

## Inspect results without the cloud

Videos, figures, reports, and recorded-action replay work locally. For example:

```bash
MUJOCO_GL=glfw .venv-libero/bin/python scripts/replay_episode.py results/sensor-perturbations-v1/brightness_shift/state-02/attempt-02
```

Replay runs recorded controls, not live inference. It checks the initial image and success flags against the original episode and records privileged simulator trajectories for analysis.

## Limits and next experiment

This is a developmental pilot on one task and ten fixed initial states, not a general robustness estimate. The clean state-0 success was reused from the exploratory integration run, and that scene informed patch placement. Camera-fault severity/timing were frozen before disturbed-policy outcomes. Quantized inference differs from upstream BF16/FlashAttention evaluation; no reproduction of published benchmark scores is claimed.

A bounded image-quality monitor and recovery intervention remain to be implemented and evaluated. Physical object displacement and real-robot validation are also outside these results.

Thirteen focused tests for fault timing, image preservation, outcome aggregation, and prompt alignment passed. Five HTTP protocol tests passed earlier; their later rerun was blocked by sandbox socket permissions. Real cloud-policy integration and all recorded experiment episodes provide separate end-to-end evidence. See [validation details](results/sensor-perturbations-v1/validation.md).

## Sources

- [OpenVLA model and evaluation code](https://github.com/openvla/openvla)
- [LIBERO-Spatial checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial)
- [LIBERO benchmark](https://github.com/Lifelong-Robot-Learning/LIBERO)
- [Cloudflare temporary tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
