# Connect the local robot to a cloud VLA

## What is ready

- Local LIBERO-Spatial robot environment has been rendered successfully.
- The remote client and server protocol passed five tests for camera upload, authentication, action validation, and transport restrictions.
- A real local LIBERO episode completed five steps using an HTTP mock policy and saved video/action traces. This tests plumbing only; it does not demonstrate learned behavior or internet performance.
- GPU model loading and a public cloud tunnel were confirmed through the user-operated Colab runtime. After the prompt-mask fix, ten real remote action requests completed successfully with the simulator running locally; mean request latency was 1.90 seconds. The following full clean attempt succeeded after 76 policy actions (mean request latency 1.638 seconds); see `docs/first-success.md`.

## Start the model in Colab

Upload `notebooks/02_cloud_model_only.ipynb` to https://colab.research.google.com/ and select a GPU runtime. Run cells in order. This notebook is self-contained: it embeds `cloud/policy_server.py`, checks resources, and installs the model in an isolated Python environment. The simulator stays on the laptop.

Use the **02** notebook, not the older **01** cloud-simulator notebook.

It targets a GPU with at least 12 GB VRAM and 30 GiB available disk before setup. Those are provisioning gates, not guarantees of successful model loading. The initial configuration uses 4-bit NF4 weights, FP16 computation, and eager attention to accommodate a possible T4 GPU. This changes the numerical baseline compared with upstream BF16/FlashAttention runs.

Model: `openvla/openvla-7b-finetuned-libero-spatial`. The server records its resolved Hugging Face revision, normalization key, precision, and preprocessing. It accepts the rotated 256×256 RGB camera image, applies JPEG/resizing/center cropping, predicts a single action, and converts the gripper convention once. This checkpoint does not use robot state or the wrist camera as model input.

Enter a token in the notebook when prompted, and retain it to enter on your laptop. Do not share the token. After loading, the next cell opens a temporary Cloudflare HTTPS tunnel without a Cloudflare account. Free GPU access and tunnel uptime are not guaranteed; the runtime must remain running.

## Run the local client

Open a terminal in this project folder. Replace the URL with the notebook's printed endpoint:

```bash
export VLA_ENDPOINT="https://YOUR-URL.trycloudflare.com"
read -rsp 'API token: ' VLA_API_TOKEN
export VLA_API_TOKEN
MUJOCO_GL=glfw .venv-libero/bin/python scripts/run_remote_episode.py --steps 10
```

Enter the same token as in the notebook. Start with 10 steps to establish integration, then use `--steps 220` for a full attempt. The client uses a 10-step settling period before querying the policy. Task 0 and initial-state 0 are the defaults; the environment seed is 0 to follow upstream evaluation. The earlier dummy-action render test used seed 7, so it is not a paired baseline for these runs.

Simulation time pauses during each network request. A timeout or invalid action aborts the episode without another physics step. Videos use simulated time, excluding network waits; network and inference latencies are recorded separately.

Artifacts in `results/remote-*`: `report.json`, `actions.jsonl`, `episode.mp4`, and `first-observation.png`. Endpoint errors also appear in the notebook's server log. Mock runs require an explicit `--allow-mock` and are identified as mock in their report.

A short integration run or one successful episode is not enough to establish robustness. First validate repeated clean success before adding disturbances.

## Maintenance and tests

```bash
.venv-libero/bin/python -m unittest discover -s tests -v
python3 scripts/build_cloud_notebook.py
```

Regenerate the notebook after changing the cloud server or cloud requirements; the server code is embedded in the notebook so the user need not upload multiple files. No real cloud endpoint has been provisioned automatically.

## Sources

- Model and evaluation: https://github.com/openvla/openvla
- Checkpoint: https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial
- Image preprocessing: https://github.com/openvla/openvla/blob/main/experiments/robot/libero/libero_utils.py
- Temporary tunnels: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/

## Prompt-mask compatibility fix

A real cloud inference request reached the loaded model but failed with a 291/290 attention-mask length mismatch. The upstream action wrapper appends token 29871 without extending a supplied attention mask. The server now appends the token and its mask together before calling the wrapper. Three CPU regression cases pass (missing token, existing token, preserved padding). Real cloud inference with the fix succeeded for ten local simulator steps. For an already-running old notebook, paste `cloud/fix_prompt_alignment_colab.py` into a new cell; this restarts only the model server using cached weights and preserves the tunnel. Do not rerun the old embedded server cell, which would overwrite the fix.
