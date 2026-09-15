"""Create a portable chart and Markdown report from a completed clean pilot."""
import argparse
import json
import os
from pathlib import Path
import statistics

from run_clean_baseline import save_progress


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',nargs='?',type=Path,default=Path('results/clean-baseline-v1'))
    args=parser.parse_args()
    out=args.directory.resolve()
    manifest=json.loads((out/'manifest.json').read_text())
    rows,summary=save_progress(out,manifest['settings'])
    if summary['pending']:
        raise SystemExit('Pilot is incomplete; keep pending states explicit in summary.json.')
    os.environ.setdefault('MPLCONFIGDIR', str(out/'.matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    successes=summary['successes'];total=summary['completed']
    fig,ax=plt.subplots(figsize=(10,4.5))
    xs=list(range(len(rows)))
    values=[r['steps'] for r in rows]
    colors=['#257955' if r['success'] else '#be593c' for r in rows]
    ax.bar(xs,values,color=colors,width=.65)
    for x,row in zip(xs,rows):
        ax.text(x,row['steps']+4,str(row['steps']),ha='center',fontsize=10)
    ax.axhline(manifest['settings']['steps'],color='#666666',linestyle='--',linewidth=1)
    ax.set_ylim(0,245)
    ax.set_xticks(xs,[str(r['initial_state_id']) for r in rows])
    ax.set_xlabel('Initial-state ID')
    ax.set_ylabel('Policy actions until termination')
    ax.set_title('Clean baseline: %s/%s successful initial states'%(successes,total),loc='left',pad=18)
    ax.spines[['top','right']].set_visible(False)
    fig.text(.12,.015,'One LIBERO-Spatial task · OpenVLA 4-bit NF4 · No recovery · Dashed line: 220-action limit',fontsize=9,color='#444444')
    fig.tight_layout(rect=[0,.06,1,1])
    fig.savefig(out/'baseline-actions.svg')
    fig.savefig(out/'baseline-actions.png',dpi=160)
    plt.close(fig)
    latencies=[]
    for row in rows:
        r=json.loads((out/row['artifacts']/'report.json').read_text())
        latencies.extend(r['latencies_seconds'])
    summary.update(mean_request_seconds=statistics.mean(latencies),
                   total_request_seconds=sum(latencies),
                   action_count_range=[min(values),max(values)],
                   median_action_count=statistics.median(values))
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    low,high=summary['wilson_95_interval']
    lines=['# Clean baseline pilot','',
        '**%s/%s successful initial states (%.0f%%).**'%(successes,total,100*summary['success_rate']), '',
        'One LIBERO-Spatial bowl-to-plate task, seed 0, initial-state IDs 0–9, ten settling steps, 220-action limit, no recovery.', '',
        'The simulator ran on the laptop; OpenVLA inference ran in the user-operated Colab runtime. Simulation paused during network requests.', '',
        '![Policy actions by initial state](baseline-actions.svg)', '',
        '| Initial state | Outcome | Actions | Mean request time | Video |',
        '| --- | --- | ---: | ---: | --- |']
    for row in rows:
        lines.append('| %s | %s | %s | %.2f s | [Watch](%s/episode.mp4) |'%(
            row['initial_state_id'],'Success' if row['success'] else 'Step limit',row['steps'],
            row['mean_request_seconds'],row['artifacts']))
    lines.extend(['',
        'Overall mean request time: %.2f seconds. Technical-error attempts: %s.'%(
            statistics.mean(latencies),summary['technical_error_attempts']), '',
        'Videos use simulation time and exclude network waiting. Request timings include network/server overhead.', '',
        'The descriptive Wilson 95%% interval is %.1f–%.1f%% under a binomial model. These are fixed initial states of one task, so this does not establish generalization or robustness.'%(100*low,100*high), '',
        'State 0 reuses the earlier exploratory success; its origin is recorded in manifest.json. This pilot is not an independent confirmatory evaluation. Brightness, occlusion, and physical displacement have not been evaluated here.', '',
        'Model: `%s`, revision `%s`, %s weights, %s compute, %s attention.'%(
            manifest['settings']['policy']['policy'],manifest['settings']['policy']['revision'],
            manifest['settings']['policy']['precision'],manifest['settings']['policy']['compute_dtype'],
            manifest['settings']['policy']['attention']), '',
        'Raw data: [episodes.csv](episodes.csv), [summary.json](summary.json), [manifest.json](manifest.json).',''])
    (out/'report.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2))
    print('Report:',out/'report.md')


if __name__=='__main__':
    main()
