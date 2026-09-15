"""Report completed paired sensor-input episodes without changing outcomes."""
import argparse
import json
import os
from pathlib import Path
import statistics

from run_clean_baseline import collect_rows
from run_sensor_pilot import compare_progress


def outcome(row):
    return ('Success' if row['success'] else 'Step limit')+' / '+str(row['steps'])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path,nargs='?',default=Path('results/sensor-perturbations-v1'))
    args=parser.parse_args()
    out=args.directory.resolve()
    manifest=json.loads((out/'manifest.json').read_text())
    baseline=Path(manifest['baseline'])
    settings=json.loads((baseline/'manifest.json').read_text())['settings']
    protocol=json.loads((out/'protocol.json').read_text())
    result=compare_progress(out,baseline,settings)
    if len(result['conditions'])!=len(protocol['conditions']) or any(s['pending'] for s in result['conditions'].values()):
        raise SystemExit('Sensor pilot incomplete; use comparison.json for explicit partial results.')
    sets={'clean':collect_rows(baseline,settings)}
    for spec in protocol['conditions']:
        folder=out/spec['name']
        condition_settings=json.loads((folder/'manifest.json').read_text())['settings']
        sets[spec['name']]=collect_rows(folder,condition_settings)
        both=[b['steps']-a['steps'] for a,b in zip(sets['clean'],sets[spec['name']]) if a['success'] and b['success']]
        summary=result['conditions'][spec['name']]
        summary['median_extra_actions_among_both_successful']=statistics.median(both) if both else None
        summary['both_successful_pairs']=len(both)
    (out/'comparison.json').write_text(json.dumps(result,indent=2))
    os.environ.setdefault('MPLCONFIGDIR',str(out/'.matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names=list(sets)
    labels=['Clean','Brightness ×0.35','Occlusion 96×96']
    colors=['#555555','#ba741d','#236d9b']
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),gridspec_kw={'width_ratios':[1,1.8]})
    wins=[sum(r['success'] for r in sets[name]) for name in names]
    axes[0].bar(labels,wins,color=colors,width=.6)
    for i,n in enumerate(wins):
        axes[0].text(i,n+.15,f'{n}/10',ha='center',fontsize=11)
    axes[0].set_ylim(0,11.5);axes[0].set_ylabel('Successful initial states')
    axes[0].tick_params(axis='x',labelsize=9)
    for name,label,color in zip(names,labels,colors):
        rows=sets[name]
        axes[1].plot([r['initial_state_id'] for r in rows],[r['steps'] for r in rows],
                     marker='o',color=color,label=label,linewidth=1.2)
        failed=[r for r in rows if not r['success']]
        if failed:
            axes[1].scatter([r['initial_state_id'] for r in failed],[r['steps'] for r in failed],
                            marker='x',color=color,s=90,linewidths=2,zorder=5)
    axes[1].axhline(220,color='#999999',linestyle='--',linewidth=1)
    axes[1].set_ylim(0,245);axes[1].set_xticks(range(10))
    axes[1].set_xlabel('Initial-state ID');axes[1].set_ylabel('Policy actions until termination')
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Transient camera faults: paired one-task pilot',x=.07,ha='left',fontsize=15)
    fig.text(.07,.015,'Fault at steps 30–59; normal input from 60 · No recovery · × denotes step-limit failure · Simulation pauses during inference',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.94])
    fig.savefig(out/'comparison.svg');fig.savefig(out/'comparison.png',dpi=160);plt.close(fig)
    # Fixed state-0 examples, selected in advance rather than for their outcome.
    fig,axes=plt.subplots(2,2,figsize=(8,8))
    for i,spec in enumerate(protocol['conditions']):
        row=sets[spec['name']][0]
        folder=out/spec['name']/row['artifacts']
        for j,(filename,title) in enumerate([('disturbance-raw.png','Original simulator image'),
                                            ('disturbance-input.png','Image sent to model')]):
            axes[i,j].imshow(plt.imread(folder/filename));axes[i,j].axis('off')
            axes[i,j].set_title(spec['name']+'\n'+title,fontsize=10)
    fig.suptitle('State 0, first disturbed policy input (step 30)',fontsize=13)
    fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(out/'input-examples.png',dpi=150);plt.close(fig)
    lines=['# Transient camera-input robustness pilot','',
           'Same bowl-to-plate task and initial-state IDs 0–9. Two camera-input faults at action indices 30–59; normal visibility returns at 60. Recovery is disabled.','',
           '![Paired comparison](comparison.svg)','',
           '| Condition | Successes | Paired loss vs clean | Median extra actions, both successful |',
           '| --- | ---: | ---: | ---: |',
           '| Clean | 10/10 | — | — |']
    for spec in protocol['conditions']:
        summary=result['conditions'][spec['name']]
        extra=summary['median_extra_actions_among_both_successful']
        lines.append(f"| {spec['name']} | {summary['successes']}/10 | {summary['lost_clean_successes']}/10 | {extra if extra is not None else '—'} |")
    lines.extend(['','Extra-action medians include only pairs that succeed in both conditions; failures exhaust the 220-action budget. Technical failures are excluded and listed in the per-condition summaries.','',
                  '![Original and perturbed model inputs](input-examples.png)','',
                  '| State | Clean: outcome / actions | Brightness: outcome / actions | Occlusion: outcome / actions |',
                  '| --- | --- | --- | --- |'])
    for clean,dark,occluded in zip(sets['clean'],sets['brightness_shift'],sets['camera_occlusion']):
        state=clean['initial_state_id']
        def link(row,name):
            return '['+outcome(row)+']('+name+'/'+row['artifacts']+'/policy-input.mp4)'
        lines.append(f"| {state} | {outcome(clean)} | {link(dark,'brightness_shift')} | {link(occluded,'camera_occlusion')} |")
    lines.extend(['',
        'Condition links above open the policy-input video. Each neighboring `episode.mp4` shows the unmodified simulator view; `actions.jsonl` records which inputs were disturbed. Videos omit network waits.','',
        '## Interpretation limits','',
        'These are transient sensor corruptions, not physical lighting or object movement. One task and ten fixed initial states do not establish broad VLA robustness. State 0 was used to choose the occlusion rectangle and the clean state-0 success was imported from an exploratory run. Severity and timing were frozen before disturbed-policy outcomes. No severity was changed to force a failure.','',
        'A task failure establishes an observed loss of completion under this protocol; inspect the action/video evidence before attributing a mechanism. A successful disturbed trial may still take longer or follow a different trajectory.','',
        'Raw data: [protocol](protocol.json), [paired comparison](comparison.json), [prefix validation](prefix-validation.json), [completed-artifact validation](artifact-validation.json). Model configuration and episode provenance are retained in the manifests.',''])
    if (out/'brightness-state-02-comparison.mp4').exists():
        lines.extend(['## Recorded counterexample', '',
                      '[Synchronized comparison video](brightness-state-02-comparison.mp4): clean raw view, brightness-fault raw view, and model input. The clean panel freezes after success; the other panels continue to the fixed step limit. Network waits are excluded.', '',
                      '![Validated target trajectories](state-02-trajectory.png)', '',
                      '[Detailed state-2 failure evidence](failure-analysis-brightness-state-02.md). This is recorded episode footage and validated local replay, not live inference.', ''])
    (out/'report.md').write_text('\n'.join(lines))
    print(json.dumps(result,indent=2))
    print('Report:',out/'report.md')


if __name__=='__main__':
    main()
