"""Resume the two frozen camera perturbations, paired with a clean pilot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from camera_perturbations import validate_spec
from remote_policy import RemotePolicy
from run_clean_baseline import collect_rows, save_progress, summarize


def compare_progress(out, baseline, settings):
    clean=collect_rows(baseline,settings)
    result={'scope':'Paired fixed states of one task; developmental sensor-input pilot, no recovery.',
            'clean':summarize(clean), 'conditions':{}}
    for spec in json.loads((out/'protocol.json').read_text())['conditions']:
        folder=out/spec['name']
        if not (folder/'manifest.json').exists():
            continue
        condition_settings=json.loads((folder/'manifest.json').read_text())['settings']
        rows,summary=save_progress(folder,condition_settings)
        pairs=[(a,b) for a,b in zip(clean,rows) if a['status']==b['status']=='completed']
        summary['paired_completed']=len(pairs)
        summary['lost_clean_successes']=sum(a['success'] and not b['success'] for a,b in pairs)
        summary['gained_successes']=sum(not a['success'] and b['success'] for a,b in pairs)
        summary['paired_success_rate_difference']=sum(int(b['success'])-int(a['success']) for a,b in pairs)/len(pairs) if pairs else None
        result['conditions'][spec['name']]=summary
    (out/'comparison.json').write_text(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default=os.environ.get('VLA_ENDPOINT'))
    parser.add_argument('--baseline',type=Path,default=Path('results/clean-baseline-v1'))
    parser.add_argument('--protocol',type=Path,default=Path('configs/disturbances-v1.json'))
    parser.add_argument('--output-dir',type=Path,default=Path('results/sensor-perturbations-v1'))
    args=parser.parse_args()
    if not args.url:
        parser.error('Set VLA_ENDPOINT.')
    baseline=args.baseline.resolve()
    base_manifest=json.loads((baseline/'manifest.json').read_text())
    if base_manifest['status']!='complete':
        parser.error('The clean reference must be complete.')
    base_settings=base_manifest['settings']
    base_rows=collect_rows(baseline,base_settings)
    if any(r['status']!='completed' for r in base_rows):
        parser.error('Clean reference has pending states.')
    protocol=json.loads(args.protocol.read_text())
    for key in ['task_id','seed','steps','initial_state_ids']:
        if protocol[key]!=base_settings[key]:
            parser.error('Protocol does not match clean reference: '+key)
    if protocol['recovery']!='disabled':
        parser.error('This pilot must have recovery disabled.')
    names=[validate_spec(s)['name'] for s in protocol['conditions']]
    if len(names)!=len(set(names)):
        parser.error('Condition names must be unique.')
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    frozen=out/'protocol.json'
    if frozen.exists() and json.loads(frozen.read_text())!=protocol:
        parser.error('Existing frozen protocol differs; use a new output directory.')
    if not frozen.exists():
        frozen.write_text(args.protocol.read_text())
    (out/'protocol-sha256.txt').write_text(hashlib.sha256(frozen.read_bytes()).hexdigest()+'\n')
    client=RemotePolicy(args.url,os.environ.get('VLA_API_TOKEN',''),timeout=45)
    if client.health()!=base_settings['policy']:
        parser.error('Cloud policy metadata differs from the clean baseline.')
    overall=out/'manifest.json'
    manifest={'protocol_version':protocol['protocol_version'],'baseline':str(baseline),
              'baseline_manifest_sha256':hashlib.sha256((baseline/'manifest.json').read_bytes()).hexdigest(),
              'created_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'status':'running'}
    if overall.exists():
        old=json.loads(overall.read_text())
        for key in ['protocol_version','baseline','baseline_manifest_sha256']:
            if old[key]!=manifest[key]:
                parser.error('Existing pilot reference changed: '+key)
        manifest=old
        manifest.pop('error',None)
        manifest['status']='running'
    overall.write_text(json.dumps(manifest,indent=2))
    try:
        for spec in protocol['conditions']:
            folder=out/spec['name'];folder.mkdir(exist_ok=True)
            settings=dict(base_settings,condition=spec['name'],disturbance=spec,recovery='disabled')
            cm=folder/'manifest.json'
            condition_manifest={'settings':settings,'status':'running'}
            if cm.exists() and json.loads(cm.read_text())['settings']!=settings:
                raise ValueError('Existing condition settings differ: '+spec['name'])
            cm.write_text(json.dumps(condition_manifest,indent=2))
            spec_path=folder/'condition.json'
            spec_path.write_text(json.dumps(spec,indent=2))
            rows,_=save_progress(folder,settings)
            for row in rows:
                if row['status']=='completed':
                    continue
                if client.health()!=base_settings['policy']:
                    raise RuntimeError('Cloud policy changed; stopping.')
                state=row['initial_state_id']
                parent=folder/('state-%02d'%state);parent.mkdir(exist_ok=True)
                number=len([p for p in parent.glob('attempt-*') if p.is_dir()])+1
                attempt=parent/('attempt-%02d'%number);attempt.mkdir()
                manifest.update(active_condition=spec['name'],active_state=state)
                overall.write_text(json.dumps(manifest,indent=2))
                print('Starting',spec['name'],'state',state,flush=True)
                command=[sys.executable,str(Path(__file__).with_name('run_remote_episode.py')),
                         '--url',args.url,'--steps',str(settings['steps']),'--seed',str(settings['seed']),
                         '--task-id',str(settings['task_id']),'--initial-state-id',str(state),
                         '--condition-config',str(spec_path),'--output-dir',str(attempt)]
                with (parent/(attempt.name+'.log')).open('w') as log:
                    process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
                result=compare_progress(out,baseline,base_settings)
                print(json.dumps(result['conditions'][spec['name']]),flush=True)
                if process.returncode:
                    raise RuntimeError('Technical error; see '+str(parent/(attempt.name+'.log')))
            condition_manifest['status']='complete'
            cm.write_text(json.dumps(condition_manifest,indent=2))
        manifest.update(status='complete',active_condition=None,active_state=None)
    except Exception as exc:
        manifest.update(status='stopped',error=str(exc))
        raise
    finally:
        compare_progress(out,baseline,base_settings)
        overall.write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
