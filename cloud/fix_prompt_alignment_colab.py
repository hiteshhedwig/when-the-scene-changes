# Run in a NEW cell in the existing model-only Colab notebook.
from pathlib import Path
import subprocess, time, json
from urllib.request import Request, urlopen

path = ROOT / 'policy_server.py'
source = path.read_text()
marker = '            action = np.asarray(self.model.predict_action('
patch = """            # Keep the mask aligned with OpenVLA's required terminal prompt token.
            if batch['input_ids'][0, -1].item() != 29871:
                ids = batch['input_ids']
                batch['input_ids'] = self.torch.cat([ids, ids.new_full((1, 1), 29871)], dim=1)
                mask = batch['attention_mask']
                batch['attention_mask'] = self.torch.cat([mask, mask.new_ones((1, 1))], dim=1)
"""
if patch not in source:
    assert source.count(marker) == 1, 'Unexpected server file; do not restart.'
    path.write_text(source.replace(marker, patch + marker))
compile(path.read_text(), str(path), 'exec')
if server.poll() is None:
    server.terminate()
    server.wait(timeout=30)
server_log = open(ROOT / 'server.log', 'w')
server = subprocess.Popen(
    [PYTHON, '-u', str(path), '--precision', '4bit'],
    env=server_env, stdout=server_log, stderr=subprocess.STDOUT)
for attempt in range(180):
    if server.poll() is not None:
        raise RuntimeError((ROOT / 'server.log').read_text()[-12000:])
    try:
        request = Request('http://127.0.0.1:8000/health',
                          headers={'Authorization': 'Bearer ' + TOKEN})
        with urlopen(request, timeout=2) as response:
            json.load(response)
        print('Ready — prompt fix applied. Existing tunnel URL stays the same.')
        break
    except OSError:
        if attempt % 15 == 0:
            print('Reloading cached model...', flush=True)
        time.sleep(2)
else:
    raise RuntimeError('Still loading. Inspect server.log.')
