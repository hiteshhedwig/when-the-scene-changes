"""Replay recorded controls locally for physics validation; no model or endpoint."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('episode',type=Path)
    args=parser.parse_args()
    episode=args.episode.resolve()
    report=json.loads((episode/'report.json').read_text())
    trace=[json.loads(s) for s in (episode/'actions.jsonl').read_text().splitlines()]
    root=Path(__file__).resolve().parents[1]
    cfg=root/'.local-libero';cfg.mkdir(exist_ok=True);(cfg/'datasets').mkdir(exist_ok=True)
    os.environ['LIBERO_CONFIG_PATH']=str(cfg)
    os.environ.setdefault('MUJOCO_GL','glfw')
    os.environ.setdefault('MPLCONFIGDIR',str(cfg/'matplotlib'))
    import yaml
    repo=root/'vendor/LIBERO';base=repo/'libero/libero'
    (cfg/'config.yaml').write_text(yaml.safe_dump({
        'benchmark_root':str(base),'bddl_files':str(base/'bddl_files'),
        'init_states':str(base/'init_files'),'datasets':str(cfg/'datasets'),'assets':str(base/'assets')}))
    sys.path.insert(0,str(repo))
    import imageio.v2 as imageio
    import numpy as np
    import torch
    from libero.libero import benchmark,get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    from remote_policy import validate_action,CONTRACT
    np.random.seed(report['seed']);torch.manual_seed(report['seed'])
    suite=benchmark.get_benchmark_dict()['libero_spatial']()
    task=suite.get_task(report['task_id'])
    states=torch.load(Path(get_libero_path('init_states'))/task.problem_folder/task.init_states_file,
                      map_location='cpu',weights_only=False)
    out=episode/'replay';out.mkdir(exist_ok=True)
    env=OffScreenRenderEnv(bddl_file_name=str(Path(get_libero_path('bddl_files'))/task.problem_folder/task.bddl_file),
                           camera_heights=256,camera_widths=256)
    try:
        env.seed(report['seed']);env.reset();obs=env.set_init_state(states[report['initial_state_id']])
        for _ in range(report.get('settling_steps',10)):
            obs,_,_,_=env.step([0,0,0,0,0,0,-1])
        def rgb(observation):
            return np.ascontiguousarray(observation['agentview_image'][::-1,::-1])
        original=imageio.imread(episode/'first-observation.png')
        identical=bool(np.array_equal(rgb(obs),original))
        matched=0
        initial_positions={k:np.asarray(v).tolist() for k,v in obs.items()
                           if k.endswith('_pos') and '_to_robot' not in k}
        with (out/'trajectory.jsonl').open('w') as positions, imageio.get_writer(out/'recorded-actions.mp4',fps=20) as video:
            video.append_data(rgb(obs))
            for row in trace:
                action=validate_action({'contract':CONTRACT,'action':row['action']})
                obs,_,_,_=env.step(action)
                success=bool(env.check_success())
                matched += int(success==row['success'])
                record={'step':row['step'],'success':success,'positions':{
                    k:np.asarray(v).tolist() for k,v in obs.items()
                    if k.endswith('_pos') and '_to_robot' not in k}}
                positions.write(json.dumps(record)+'\n')
                video.append_data(rgb(obs))
        imageio.imwrite(out/'final-scene.png',rgb(obs))
        result={'source_episode':str(episode),'policy':'recorded_controls_only_no_live_inference',
                'steps_replayed':len(trace),'initial_frame_exact_match':identical,
                'success_flags_matching':matched,'success_flags_compared':len(trace),
                'final_success':bool(env.check_success()),'initial_positions':initial_positions}
        (out/'report.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
        if not identical or matched!=len(trace):
            raise RuntimeError('Replay differs from source; do not use its state trace as original ground truth.')
    finally:
        env.close()


if __name__=='__main__':
    main()
