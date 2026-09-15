"""Resumable clean pilot: ten fixed initial states of one LIBERO-Spatial task."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

from remote_policy import RemotePolicy

TERMINAL = {'success', 'step_limit'}


def validate_report(report, settings, state):
    expected = {'task_id':settings['task_id'], 'seed':settings['seed'],
                'requested_steps':settings['steps'], 'condition':'clean', 'initial_state_id':state,
                'policy':settings['policy']}
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError('Incompatible episode for state %s: %s' % (state, key))
    if report.get('termination') == 'success' and report.get('success') is not True:
        raise ValueError('Success termination must agree with success predicate.')
    if report.get('termination') == 'step_limit' and report.get('completed_steps') != settings['steps']:
        raise ValueError('A completed failure must exhaust the configured step budget.')


def collect_rows(out, settings):
    rows = []
    for state in settings['initial_state_ids']:
        attempts = sorted(p for p in (out / ('state-%02d' % state)).glob('attempt-*') if p.is_dir())
        chosen = None
        errors = 0
        for attempt in attempts:
            path = attempt/'report.json'
            if not path.exists():
                errors += 1  # Interrupted process or failure before report initialization.
                continue
            report = json.loads(path.read_text())
            validate_report(report, settings, state)
            if report.get('termination') in TERMINAL:
                chosen = (attempt, report)
                break
            errors += 1
        row = {'initial_state_id':state, 'status':'pending', 'success':'', 'steps':'',
               'mean_request_seconds':'', 'technical_error_attempts':errors,
               'attempts':len(attempts), 'artifacts':''}
        if chosen:
            attempt, report = chosen
            row.update(status='completed', success=report['success'], steps=report['completed_steps'],
                       mean_request_seconds=statistics.mean(report['latencies_seconds']) if report['latencies_seconds'] else '',
                       artifacts=str(attempt.relative_to(out)))
        rows.append(row)
    return rows


def summarize(rows):
    completed = [r for r in rows if r['status'] == 'completed']
    n = len(completed)
    wins = sum(r['success'] is True for r in completed)
    result = {'planned':len(rows), 'completed':n, 'pending':len(rows)-n, 'successes':wins,
              'task_failures':n-wins, 'success_rate':wins/n if n else None,
              'technical_error_attempts':sum(r['technical_error_attempts'] for r in rows),
              'scope':'One task, fixed initial states; pilot only. Technical errors excluded from task outcomes.'}
    if n:
        z = 1.959963984540054
        p = wins/n
        center = (p + z*z/(2*n))/(1+z*z/n)
        radius = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/(1+z*z/n)
        result['wilson_95_interval'] = [center-radius,center+radius]
        result['interval_assumption'] = 'Descriptive binomial interval; fixed states of one task do not establish generalization.'
    return result


def save_progress(out, settings):
    rows = collect_rows(out, settings)
    summary = summarize(rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    with (out/'episodes.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    return rows,summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default=os.environ.get('VLA_ENDPOINT'))
    parser.add_argument('--output-dir',type=Path,default=Path('results/clean-baseline-v1'))
    parser.add_argument('--import-episode',type=Path,help='Reuse a matching prior clean pilot episode, preserving its origin.')
    args=parser.parse_args()
    if not args.url:
        parser.error('Set VLA_ENDPOINT or --url.')
    client=RemotePolicy(args.url,os.environ.get('VLA_API_TOKEN',''),timeout=45)
    metadata=client.health()
    if metadata.get('policy')=='mock':
        parser.error('Clean baseline requires a real policy.')
    settings={'task_id':0,'seed':0,'steps':220,'initial_state_ids':list(range(10)),
              'condition':'clean','policy':metadata,'settling_steps':10,
              'sim_paused_during_inference':True}
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    manifest_path=out/'manifest.json'
    manifest={'settings':settings,'created_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
              'imported_episodes':{},'status':'running'}
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        if manifest['settings'] != settings:
            parser.error('Existing batch settings or policy metadata differ. Preserve this batch and use another directory.')
    if args.import_episode:
        original=args.import_episode.resolve()
        report=json.loads((original/'report.json').read_text())
        state=report['initial_state_id']
        if state not in settings['initial_state_ids']:
            parser.error('Imported initial state is outside the pilot.')
        validate_report(report,settings,state)
        if report.get('termination') not in TERMINAL:
            parser.error('Only completed outcomes may be imported.')
        destination=out/('state-%02d'%state)/'attempt-01'
        if not destination.exists():
            shutil.copytree(original,destination)
            manifest['imported_episodes'][str(state)]=str(original)
    manifest_path.write_text(json.dumps(manifest,indent=2))
    try:
        rows,summary=save_progress(out,settings)
        for row in rows:
            if row['status']=='completed':
                continue
            if client.health()!=metadata:
                raise RuntimeError('Cloud policy metadata changed; stopping to avoid mixing baselines.')
            state=row['initial_state_id']
            parent=out/('state-%02d'%state);parent.mkdir(exist_ok=True)
            attempt=parent/('attempt-%02d'%(len([p for p in parent.glob('attempt-*') if p.is_dir()])+1))
            attempt.mkdir()
            manifest.update(status='running',active_state=state)
            manifest_path.write_text(json.dumps(manifest,indent=2))
            print('Starting initial state',state,'of 0..9',flush=True)
            command=[sys.executable,str(Path(__file__).with_name('run_remote_episode.py')),
                     '--url',args.url,'--steps','220','--seed','0',
                     '--initial-state-id',str(state),'--output-dir',str(attempt)]
            with (parent/(attempt.name+'.log')).open('w') as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
            rows,summary=save_progress(out,settings)
            print(json.dumps(summary),flush=True)
            if result.returncode:
                raise RuntimeError('Episode process failed for state %s; see %s. Resume preserves completed states.'%(state,parent))
        manifest.update(status='complete',active_state=None)
    except Exception as exc:
        manifest.update(status='stopped',error=str(exc))
        raise
    finally:
        save_progress(out,settings)
        manifest_path.write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
