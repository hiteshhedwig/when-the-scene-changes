"""Small synchronous client: simulator time does not advance during requests."""
import base64
import io
import json
import math
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image

CONTRACT = 'libero_osc_pose_v1'


def validate_action(response):
    if response.get('contract') != CONTRACT:
        raise ValueError('Endpoint uses the wrong action contract.')
    action = response.get('action')
    if not isinstance(action, list) or len(action) != 7:
        raise ValueError('Expected exactly seven action values.')
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
           not math.isfinite(x) or abs(x) > 1.000001 for x in action):
        raise ValueError('Action values must be finite numbers within [-1,1].')
    return action


class RemotePolicy:
    def __init__(self, url, token, timeout=120):
        parsed = urlparse(url)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ['127.0.0.1', 'localhost']):
            raise ValueError('Use HTTPS for cloud endpoints; HTTP is only allowed on loopback.')
        if not token:
            raise ValueError('VLA_API_TOKEN is missing.')
        self.url, self.token, self.timeout = url.rstrip('/'), token, timeout

    def request(self, path, payload=None):
        body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
        req = Request(self.url + path, data=body, headers={
            'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        with urlopen(req, timeout=self.timeout) as response:
            return json.load(response)

    def health(self):
        info = self.request('/health')
        if info.get('contract') != CONTRACT or info.get('suite') != 'libero_spatial':
            raise ValueError('Endpoint is not compatible with this LIBERO-Spatial runner.')
        return info

    def act(self, rgb_rotated, instruction):
        if rgb_rotated.shape != (256, 256, 3) or str(rgb_rotated.dtype) != 'uint8':
            raise ValueError('Expected uint8 RGB image with shape (256,256,3).')
        image = io.BytesIO()
        Image.fromarray(rgb_rotated).save(image, format='PNG')
        result = self.request('/act', {'contract': CONTRACT, 'instruction': instruction,
                                      'image_png': base64.b64encode(image.getvalue()).decode('ascii')})
        result['action'] = validate_action(result)
        return result
