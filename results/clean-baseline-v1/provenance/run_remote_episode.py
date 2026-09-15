"""Local LIBERO physics with model inference over HTTP(S). No local weights."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from remote_policy import RemotePolicy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=os.environ.get('VLA_ENDPOINT'))
    parser.add_argument('--steps', type=int, default=10, help='Start short; use 220 for a full spatial episode.')
    parser.add_argument('--task-id', type=int, default=0)
    parser.add_argument('--initial-state-id', type=int, default=0)
    parser.add_argument('--seed', type=int, default=0, help='Upstream uses env seed 0 with fixed initial states.')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--allow-mock', action='store_true')
    parser.add_argument('--output-dir', type=Path, help='Explicit new or empty artifact directory.')
    args = parser.parse_args()
    if not args.url or not 1 <= args.steps <= 220:
        parser.error('Set --url (or VLA_ENDPOINT), and --steps between 1 and 220.')
    policy = RemotePolicy(args.url, os.environ.get('VLA_API_TOKEN', ''), args.timeout)
    metadata = policy.health()
    if metadata['policy'] == 'mock' and not args.allow_mock:
        parser.error('Mock endpoint requires --allow-mock; it does not control the task.')
    root = Path(__file__).resolve().parents[1]
    cfg = root / '.local-libero'
    cfg.mkdir(exist_ok=True)
    (cfg / 'datasets').mkdir(exist_ok=True)
    os.environ['LIBERO_CONFIG_PATH'] = str(cfg)
    os.environ.setdefault('MUJOCO_GL', 'glfw')
    os.environ.setdefault('MPLCONFIGDIR', str(cfg / 'matplotlib'))
    import yaml
    repo = root / 'vendor/LIBERO'
    base = repo / 'libero/libero'
    (cfg / 'config.yaml').write_text(yaml.safe_dump({
        'benchmark_root':str(base), 'bddl_files':str(base/'bddl_files'),
        'init_states':str(base/'init_files'), 'datasets':str(cfg/'datasets'), 'assets':str(base/'assets')}))
    sys.path.insert(0, str(repo))
    import imageio.v2 as imageio
    import numpy as np
    import torch
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    suite = benchmark.get_benchmark_dict()['libero_spatial']()
    task = suite.get_task(args.task_id)
    states = torch.load(Path(get_libero_path('init_states')) / task.problem_folder / task.init_states_file,
                        map_location='cpu', weights_only=False)
    if not 0 <= args.initial_state_id < len(states):
        parser.error('Initial state ID is out of range.')
    out = args.output_dir or root / 'results' / ('remote-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(time.time_ns() % 1000000))
    if out.exists() and any(out.iterdir()):
        parser.error('Output directory must be new or empty; existing artifacts are preserved.')
    out.mkdir(parents=True, exist_ok=True)
    report = {'policy':metadata, 'instruction':task.language, 'task_id':args.task_id,
              'initial_state_id':args.initial_state_id, 'seed':args.seed,
              'sim_paused_during_inference':True, 'requested_steps':args.steps,
              'completed_steps':0, 'success':False, 'condition':'clean',
              'termination':'initializing', 'settling_steps':10, 'control_hz':20, 'video_fps':20,
              'video_timing':'simulation time; network waits excluded', 'latencies_seconds':[]}
    env = None
    try:
        env = OffScreenRenderEnv(bddl_file_name=str(Path(get_libero_path('bddl_files')) /
                                  task.problem_folder / task.bddl_file),
                                  camera_heights=256, camera_widths=256)
        env.seed(args.seed)
        env.reset()
        obs = env.set_init_state(states[args.initial_state_id])
        for _ in range(10):  # Match upstream settling period.
            obs, _, _, _ = env.step([0,0,0,0,0,0,-1])
        with imageio.get_writer(out/'episode.mp4', fps=20) as video, (out/'actions.jsonl').open('w') as trace:
            video.append_data(np.ascontiguousarray(obs['agentview_image'][::-1, ::-1]))
            for step in range(args.steps):
                rgb = np.ascontiguousarray(obs['agentview_image'][::-1, ::-1])
                if step == 0:
                    imageio.imwrite(out/'first-observation.png', rgb)
                start = time.perf_counter()
                response = policy.act(rgb, task.language)
                latency = time.perf_counter()-start
                # No simulator step happens until a valid action has arrived.
                obs, _, _, _ = env.step(response['action'])
                success = bool(env.check_success())
                trace.write(json.dumps({'step':step, 'action':response['action'],
                                        'request_seconds':latency, 'success':success,
                                        'inference_seconds':response.get('inference_seconds')})+'\n')
                trace.flush()
                video.append_data(np.ascontiguousarray(obs['agentview_image'][::-1, ::-1]))
                report['latencies_seconds'].append(latency)
                report['completed_steps'] += 1
                report['success'] = success
                print('Step',step+1,'request seconds',round(latency,3),'success',success,flush=True)
                if success:
                    report['termination'] = 'success'
                    break
            else:
                report['termination'] = 'step_limit'
    except Exception as exc:
        report['termination'] = 'error'
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        (out/'report.json').write_text(json.dumps(report, indent=2))
        print('Artifacts:', out, flush=True)
        if env is not None:
            env.close()


if __name__ == '__main__':
    main()
