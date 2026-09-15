"""Write a readable partial report without treating pending trials as failures."""
import json
from pathlib import Path

from run_clean_baseline import collect_rows


def write_progress(out):
    out=Path(out)
    manifest=json.loads((out/'manifest.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text())
    baseline=Path(manifest['baseline'])
    baseline_settings=json.loads((baseline/'manifest.json').read_text())['settings']
    clean={r['initial_state_id']:r for r in collect_rows(baseline,baseline_settings)}
    planned=len(protocol['conditions'])*len(protocol['initial_state_ids'])
    completed=[];counts=[];errors=[]
    for spec in protocol['conditions']:
        folder=out/spec['name']
        if not (folder/'manifest.json').exists():
            counts.append((spec['name'],0,0,len(protocol['initial_state_ids'])))
            continue
        settings=json.loads((folder/'manifest.json').read_text())['settings']
        rows=collect_rows(folder,settings)
        done=[r for r in rows if r['status']=='completed']
        counts.append((spec['name'],len(done),sum(r['success'] for r in done),len(rows)-len(done)))
        for row in done:
            completed.append((spec['name'],row))
        for path in sorted(folder.glob('state-*/attempt-*/report.json')):
            r=json.loads(path.read_text())
            if r.get('termination')=='error':
                errors.append((spec['name'],r['initial_state_id'],r['completed_steps'],r.get('error',''),str(path.relative_to(out))))
    lines=['# Sensor-input pilot progress','',
           f"Status: **{manifest['status']}**. **{len(completed)}/{planned}** planned disturbed episodes completed. Technical interruptions are preserved and are not model task failures.",'',
           '| Condition | Completed | Successful completed trials | Pending |',
           '| --- | ---: | ---: | ---: |']
    for name,n,wins,pending in counts:
        lines.append(f'| {name} | {n}/10 | {wins}/{n} | {pending} |')
    if manifest.get('active_condition'):
        lines.extend(['',f"Last/current active trial: {manifest['active_condition']}, initial state {manifest['active_state']}."])
    lines.extend(['','| Condition | State | Clean actions | Disturbed outcome / actions | Model-input video |',
                  '| --- | ---: | ---: | --- | --- |'])
    for name,row in completed:
        label='Success' if row['success'] else 'Step limit'
        lines.append(f"| {name} | {row['initial_state_id']} | {clean[row['initial_state_id']]['steps']} | {label} / {row['steps']} | [Watch]({name}/{row['artifacts']}/policy-input.mp4) |")
    if errors:
        lines.extend(['','## Technical interruptions',''])
        for name,state,steps,message,path in errors:
            lines.append(f'- {name}, state {state}: {steps} completed actions before {message}. [Preserved attempt]({path}).')
    lines.extend(['','Protocol: darken RGB pixels to 35% intensity, or mask a fixed 96×96 rectangle, at zero-based policy steps 30–59. Normal input returns at 60. No recovery is enabled. These are camera-input corruptions, not physical lighting or object movement.','',
                  'Partial success counts do not estimate the final ten-state condition result. Severity/timing remain frozen. All videos omit network waiting; raw simulator videos are saved beside model-input videos.','',
                  '[Frozen protocol](protocol.json) · [Paired outcome progress](comparison.json) · [Artifact validation](artifact-validation.json)',''])
    (out/'progress.md').write_text('\n'.join(lines))


if __name__=='__main__':
    write_progress(Path('results/sensor-perturbations-v1'))
