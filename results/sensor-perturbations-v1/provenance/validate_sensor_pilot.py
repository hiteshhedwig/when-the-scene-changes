"""Validate completed perturbation artifacts, including an explicitly partial pilot."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from camera_perturbations import perturb_camera, is_active
from run_clean_baseline import collect_rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path,nargs='?',default=Path('results/sensor-perturbations-v1'))
    args=parser.parse_args()
    out=args.directory.resolve()
    overall=json.loads((out/'manifest.json').read_text())
    baseline=Path(overall['baseline'])
    clean_settings=json.loads((baseline/'manifest.json').read_text())['settings']
    clean={r['initial_state_id']:r for r in collect_rows(baseline,clean_settings)}
    checks=[]
    for spec in json.loads((out/'protocol.json').read_text())['conditions']:
        folder=out/spec['name']
        if not (folder/'manifest.json').exists():
            continue
        settings=json.loads((folder/'manifest.json').read_text())['settings']
        for row in collect_rows(folder,settings):
            if row['status']!='completed':
                continue
            state=row['initial_state_id'];episode=folder/row['artifacts']
            reference=baseline/clean[state]['artifacts']
            report=json.loads((episode/'report.json').read_text())
            trace=[json.loads(s) for s in (episode/'actions.jsonl').read_text().splitlines()]
            base_trace=[json.loads(s) for s in (reference/'actions.jsonl').read_text().splitlines()]
            assert len(trace)==report['completed_steps']
            np.testing.assert_array_equal(np.asarray(Image.open(episode/'first-observation.png')),
                                          np.asarray(Image.open(reference/'first-observation.png')))
            expected=[is_active(i,spec) for i in range(len(trace))]
            assert [r['disturbance_active'] for r in trace]==expected
            assert report['disturbed_input_steps']==sum(expected)
            if len(trace)>spec['start_step']:
                raw=np.asarray(Image.open(episode/'disturbance-raw.png'))
                sent=np.asarray(Image.open(episode/'disturbance-input.png'))
                np.testing.assert_array_equal(sent,perturb_camera(raw,spec['start_step'],spec))
            prefix=min(spec['start_step'],len(trace),len(base_trace))
            matches=sum(trace[i]['action']==base_trace[i]['action'] for i in range(prefix))
            checks.append({'condition':spec['name'],'initial_state_id':state,
                           'initial_rgb_matches_clean':True,'disturbance_schedule_exact':True,
                           'onset_transform_exact':True,'prefix_actions_compared':prefix,
                           'prefix_actions_matching':matches,'completed_steps':len(trace)})
    result={'completed_episodes_validated':len(checks),
            'scope':'Completed trials only; missing or technically interrupted trials are not outcomes.',
            'checks':checks}
    (out/'artifact-validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
