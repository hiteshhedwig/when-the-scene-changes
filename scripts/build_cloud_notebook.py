import json
from pathlib import Path

def md(s): return {'cell_type':'markdown','metadata':{},'source':s.splitlines(True)}
def code(s): return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(True)}
server=Path('cloud/policy_server.py').read_text()
requirements=Path('cloud/requirements.txt').read_text()
cells=[md('''# Cloud model only — local robot simulator
Upload this notebook to Colab and select a GPU runtime. The simulator stays on your laptop. This notebook runs a LIBERO-Spatial OpenVLA checkpoint and exposes an authenticated temporary endpoint.

**Status:** endpoint protocol and mock integration are tested locally; GPU loading/inference and the public tunnel are not validated yet. Free GPU availability is not guaranteed. No paid resource is provisioned.

This downloads roughly 15 GB of checkpoint weights plus dependencies into the cloud runtime. Start with a 10-step local episode after the endpoint is ready. The 4-bit FP16-compute baseline differs from upstream BF16/FlashAttention evaluation; don't claim reproduction of published scores.
'''),code('''import os, sys, subprocess, shutil, json, time, re
from pathlib import Path
import google.colab
if not Path('/content').exists():
    raise RuntimeError('Run in Colab; model weights must not be downloaded to the laptop.')
ROOT = Path('/content/vla-model')
ROOT.mkdir(exist_ok=True)
def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)
probe = run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'], capture_output=True)
print(probe.stdout)
line = probe.stdout.splitlines()[0].split(',')
if float(line[1].strip()) < 12000:
    raise RuntimeError('This first model setup targets at least 12 GB VRAM; do not download weights yet.')
free = shutil.disk_usage(ROOT).free / 2**30
print('Free disk GiB:', round(free, 1))
if free < 30:
    raise RuntimeError('Need at least 30 GiB available before installing packages and checkpoint.')
(ROOT / 'hardware.json').write_text(json.dumps({'gpu':probe.stdout, 'free_disk_gib':free}, indent=2))
'''),md('''## Isolated Python 3.10 model environment
This avoids changing the notebook kernel's Python or installed packages. Run this once per fresh runtime. Package installation can take several minutes; save the full traceback if it fails.
'''),code('''run([sys.executable, '-m', 'pip', 'install', '-q', 'uv'])
UV = shutil.which('uv')
model_env = dict(os.environ, UV_CACHE_DIR=str(ROOT/'uv-cache'), UV_PYTHON_INSTALL_DIR=str(ROOT/'python'))
PYTHON = str(ROOT/'venv/bin/python')
if not Path(PYTHON).exists():
    run([UV, 'venv', '--python', '3.10', str(ROOT/'venv')], env=model_env)
run([UV, 'pip', 'install', '--python', PYTHON, 'torch==2.2.2', 'torchvision==0.17.2',
     '--index-url', 'https://download.pytorch.org/whl/cu121'], env=model_env)
''' + '(ROOT/"requirements.txt").write_text('+repr(requirements)+')\n' + '''run([UV, 'pip', 'install', '--python', PYTHON, '-r', str(ROOT/'requirements.txt')], env=model_env)
freeze = run([UV, 'pip', 'freeze', '--python', PYTHON], env=model_env, capture_output=True).stdout
(ROOT/'requirements-resolved.txt').write_text(freeze)
run([PYTHON, '-c', 'import torch; print(torch.__version__, torch.cuda.is_available()); assert torch.cuda.is_available()'])
'''),md('''## Start the model endpoint
Enter a secret token of at least 16 ASCII letters/digits, and reuse it on the laptop. It is kept in process memory and is not printed. The server resolves and reports the model revision, loads 4-bit weights, and only becomes healthy after loading completes.

The server file is embedded below so you only need to upload this notebook. Changes to `cloud/policy_server.py` require regenerating this notebook.
'''),code('(ROOT/"policy_server.py").write_text('+repr(server)+')\n'+'''from getpass import getpass
TOKEN = getpass('Choose API token (at least 16 ASCII characters): ')
if len(TOKEN) < 16 or not TOKEN.isascii():
    raise ValueError('Use at least 16 ASCII characters.')
server_env = dict(os.environ, VLA_API_TOKEN=TOKEN, HF_HOME=str(ROOT/'hf-cache'), TF_CPP_MIN_LOG_LEVEL='2')
# Re-running this cell stops only the model server started by this notebook.
if 'server' in globals() and server.poll() is None:
    server.terminate()
    server.wait(timeout=30)
server_log = open(ROOT/'server.log', 'w')
server = subprocess.Popen([PYTHON, '-u', str(ROOT/'policy_server.py'), '--precision', '4bit'],
                          env=server_env, stdout=server_log, stderr=subprocess.STDOUT)
from urllib.request import Request, urlopen
HEALTH = None
for attempt in range(900):
    if server.poll() is not None:
        print((ROOT/'server.log').read_text()[-16000:])
        raise RuntimeError('Model server exited. Share the traceback above.')
    try:
        req = Request('http://127.0.0.1:8000/health', headers={'Authorization':'Bearer '+TOKEN})
        with urlopen(req, timeout=2) as response:
            HEALTH = json.load(response)
        break
    except OSError:
        if attempt % 10 == 0:
            print('Waiting for download/model loading...', attempt*2, 'seconds', flush=True)
        time.sleep(2)
if HEALTH is None:
    server.terminate()
    raise RuntimeError('Model did not become ready within 30 minutes. Inspect server.log.')
print(json.dumps(HEALTH, indent=2))
(ROOT/'model-metadata.json').write_text(json.dumps(HEALTH, indent=2))
'''),md('''## Open a temporary HTTPS endpoint
Cloudflare Quick Tunnels need no Cloudflare account, but have no uptime guarantee. The tunnel routes requests to the model process; all endpoint requests require your bearer token. Nothing from your laptop is uploaded until you launch the local client.
'''),code('''import urllib.request
binary = ROOT/'cloudflared'
if not binary.exists():
    urllib.request.urlretrieve('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64', binary)
    binary.chmod(0o755)
print(run([str(binary), '--version'], capture_output=True).stdout)
if 'tunnel' in globals() and tunnel.poll() is None:
    tunnel.terminate()
    tunnel.wait(timeout=30)
tunnel_log = open(ROOT/'tunnel.log', 'w')
tunnel = subprocess.Popen([str(binary), 'tunnel', '--url', 'http://127.0.0.1:8000', '--no-autoupdate'],
                          stdout=tunnel_log, stderr=subprocess.STDOUT)
ENDPOINT = None
for _ in range(60):
    if tunnel.poll() is not None:
        raise RuntimeError((ROOT/'tunnel.log').read_text()[-6000:])
    matches = re.findall(r'https://[a-z0-9-]+\\.trycloudflare\\.com', (ROOT/'tunnel.log').read_text())
    if matches:
        ENDPOINT = matches[-1]
        break
    time.sleep(1)
if ENDPOINT is None:
    raise RuntimeError('Tunnel URL not found. Inspect tunnel.log.')
print('Endpoint URL:', ENDPOINT)
print('On laptop: export VLA_ENDPOINT="'+ENDPOINT+'"')
print('Keep this runtime open. Use the same secret token on the laptop.')
'''),md('''## Run on your laptop
Open a terminal in the project folder. Copy the URL printed above into the first line:

```bash
export VLA_ENDPOINT="https://YOUR-URL.trycloudflare.com"
read -rsp 'API token: ' VLA_API_TOKEN
export VLA_API_TOKEN
MUJOCO_GL=glfw .venv-libero/bin/python scripts/run_remote_episode.py --steps 10
```

Enter the same token you chose above. This short run is an integration check, not a task-success benchmark. It saves video, actions, model metadata, and request timings in `results/remote-*`. If that works, a full LIBERO-Spatial episode uses `--steps 220`.

If you see an inference error, inspect the model log below. Never share your API token.
'''),code('''print((ROOT/'server.log').read_text()[-16000:])
'''),md('''## Stop the endpoint when finished
This stops the two processes started here. The temporary URL then stops working. Colab may also disconnect or reclaim the free runtime.
'''),code('''for name in ['tunnel', 'server']:
    process = globals().get(name)
    if process is not None and process.poll() is None:
        process.terminate()
        process.wait(timeout=30)
print('Model server and tunnel stopped.')
'''),md('''Sources: [OpenVLA](https://github.com/openvla/openvla), [LIBERO-Spatial checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial), [upstream image preprocessing](https://github.com/openvla/openvla/blob/main/experiments/robot/libero/libero_utils.py), [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
''')]
nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}
Path('notebooks/02_cloud_model_only.ipynb').write_text(json.dumps(nb,indent=2)+'\n')
