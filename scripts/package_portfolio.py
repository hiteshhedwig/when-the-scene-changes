"""Bundle source, protocols, and completed results; exclude runtimes and weights."""
import argparse
import json
from pathlib import Path
import zipfile


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=root/'artifacts/vla-robustness-portfolio.zip')
    args=parser.parse_args()
    for name in ['clean-baseline-v1','sensor-perturbations-v1']:
        manifest=json.loads((root/'results'/name/'manifest.json').read_text())
        if manifest['status']!='complete':
            raise SystemExit('Finish '+name+' before packaging.')
    result=json.loads((root/'results/sensor-perturbations-v1/comparison.json').read_text())
    if len(result['conditions'])!=2 or any(s['pending'] or s['completed']!=10 for s in result['conditions'].values()):
        raise SystemExit('The two ten-state conditions must both be complete.')
    paths=[root/'README.md',root/'.gitignore']
    for folder in ['scripts','tests','cloud','notebooks','configs','docs',
                   'results/clean-baseline-v1','results/sensor-perturbations-v1']:
        for path in (root/folder).rglob('*'):
            if path.is_file() and not any(p.startswith('.') or p=='__pycache__' for p in path.relative_to(root).parts):
                paths.append(path)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path,Path('when-the-scene-changes')/path.relative_to(root))
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        count=len(archive.namelist())
    print('Verified bundle:',args.output,'files:',count,'bytes:',args.output.stat().st_size)


if __name__=='__main__':
    main()
