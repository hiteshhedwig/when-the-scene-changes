# First successful remote-policy episode

Task: pick up the black bowl between the plate and the ramekin and place it on the plate.

The robot simulator ran on the laptop. OpenVLA ran in the user-operated Colab GPU runtime, reached through a temporary HTTPS tunnel. No policy weights were downloaded to the laptop.

## Result

- LIBERO-Spatial task 0, initial-state ID 0, environment seed 0.
- Success: true according to LIBERO's task predicate.
- Completed policy actions: 76 of a 220-step budget, after 10 settling steps.
- Mean request latency: 1.638 seconds; median: 1.631 seconds.
- Mean server-reported inference time: 0.981 seconds.
- Total request wait: 124.48 seconds, excluding setup and simulator overhead.
- Policy-controlled simulation time: 3.8 seconds at 20 Hz. Simulation paused during each request.

The saved video excludes network waiting time and therefore plays much faster than the wall-clock run. It shows the initial scene, approach/grasp, and movement toward the plate. The success predicate is the completion criterion; the gripper partially occludes the final placement.

## Model configuration

- Checkpoint: `openvla/openvla-7b-finetuned-libero-spatial`.
- Checkpoint revision: `962318cec55ac10993ff0f5f43eda9a270b4c873`.
- 4-bit NF4 weights, FP16 compute, eager attention.
- Action statistics: `libero_spatial`.
- Rotated agent camera; JPEG/Lanczos resize to 224 pixels; 90%-area center crop.
- Gripper convention converted once on the server.
- Prompt token/mask alignment fix applied. The old action wrapper appended token 29871 without extending its provided mask, causing a 291/290 mismatch; the server now aligns them before prediction.
- The model's remote Python code resolved separately to the base-model revision shown in the Colab traceback (`47a0ec7fc4ec123775a391911046cf33cf9ed83f`); the initial checkpoint revision alone did not pin that code dependency.

## Artifacts

`results/remote-20261115-121101-279390/` contains `episode.mp4`, `report.json`, `summary.json`, `actions.jsonl`, and sampled frames. The earlier ten-step real-cloud integration run is in `results/remote-20261115-121021-47698/`.

This is one successful clean episode, not an estimate of general success rate or robustness. Next: repeat clean initial states, then evaluate paired disturbances. Numerical settings differ from upstream BF16/FlashAttention evaluation, so this is not a reproduction of their published benchmark scores.
