"""Render an actual LIBERO robot task locally; dummy actions, no policy."""
import argparse
import json
import os
from pathlib import Path
import time

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1] / 'vendor' / 'LIBERO')
parser.add_argument('--frames', type=int, default=60)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
repo = args.repo.resolve()
config_dir = root / '.local-libero'
config_dir.mkdir(exist_ok=True)
(config_dir / 'datasets').mkdir(exist_ok=True)
os.environ['LIBERO_CONFIG_PATH'] = str(config_dir)
os.environ.setdefault('MUJOCO_GL', 'glfw')
os.environ.setdefault('MPLCONFIGDIR', str(config_dir / 'matplotlib'))
import yaml
base = repo / 'libero' / 'libero'
(config_dir / 'config.yaml').write_text(yaml.safe_dump({
    'benchmark_root': str(base), 'bddl_files': str(base / 'bddl_files'),
    'init_states': str(base / 'init_files'), 'datasets': str(config_dir / 'datasets'),
    'assets': str(base / 'assets')}))
import sys
sys.path.insert(0, str(repo))
import numpy as np
import imageio.v2 as imageio
import torch
from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv

out = root / 'results/local-libero'
out.mkdir(parents=True, exist_ok=True)
suite = benchmark.get_benchmark_dict()['libero_spatial']()
task = suite.get_task(0)
env = OffScreenRenderEnv(
    bddl_file_name=str(Path(get_libero_path('bddl_files')) / task.problem_folder / task.bddl_file),
    camera_heights=256, camera_widths=256)
try:
    env.seed(7)
    env.reset()
    # LIBERO ships trusted NumPy initial states serialized with torch.save.
    init_path = Path(get_libero_path('init_states')) / task.problem_folder / task.init_states_file
    init_states = torch.load(init_path, map_location='cpu', weights_only=False)
    obs = env.set_init_state(init_states[0])
    frames = []
    start = time.perf_counter()
    for step in range(args.frames):
        obs, reward, done, info = env.step([0, 0, 0, 0, 0, 0, -1])
        frames.append(np.ascontiguousarray(obs['agentview_image'][::-1, ::-1]))
    elapsed = time.perf_counter() - start
    imageio.imwrite(out / 'robot-scene.png', frames[-1])
    imageio.mimsave(out / 'robot-scene.mp4', frames, fps=20)
    report = {'task':task.language, 'suite':'libero_spatial', 'task_id':0,
              'seed':7, 'initial_state_id':0, 'frames':len(frames),
              'elapsed_seconds':elapsed, 'steps_per_second':len(frames)/elapsed,
              'policy':'dummy_action', 'task_success':bool(env.check_success()),
              'scope':'Local robot simulation/render check; no learned policy',
              'observation_shapes':{k:list(v.shape) for k,v in obs.items() if hasattr(v,'shape')}}
    (out / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
finally:
    env.close()
