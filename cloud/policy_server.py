"""Model-only JSON endpoint. Run --mock for transport testing without weights."""
import argparse
import base64
import hmac
import io
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
from PIL import Image

CONTRACT = 'libero_osc_pose_v1'
CHECKPOINT = 'openvla/openvla-7b-finetuned-libero-spatial'


def prepare_image(image, tf):
    """Match the upstream LIBERO JPEG/Lanczos resize and 90%-area crop."""
    encoded = tf.io.encode_jpeg(np.asarray(image, dtype=np.uint8))
    decoded = tf.io.decode_jpeg(encoded, channels=3)
    resized = tf.image.resize(decoded, [224, 224], method='lanczos3', antialias=True)
    quantized = tf.cast(tf.clip_by_value(tf.round(resized), 0, 255), tf.uint8)
    offset = (1.0 - np.sqrt(0.9)) / 2.0
    floating = tf.image.convert_image_dtype(quantized, tf.float32)[None]
    cropped = tf.image.crop_and_resize(
        floating, [[offset, offset, 1-offset, 1-offset]], [0], [224, 224])[0]
    rgb = tf.image.convert_image_dtype(tf.clip_by_value(cropped, 0, 1), tf.uint8, saturate=True)
    return Image.fromarray(rgb.numpy())


class Policy:
    def __init__(self, mock=False, revision='main', precision='4bit'):
        self.mock = mock
        self.lock = threading.Lock()
        self.metadata = {'contract': CONTRACT, 'suite': 'libero_spatial',
                         'policy': 'mock' if mock else CHECKPOINT,
                         'precision': 'none' if mock else precision,
                         'compute_dtype': 'none' if mock else 'float16',
                         'quantization_type': 'nf4' if precision == '4bit' and not mock else None,
                         'attention': 'none' if mock else 'eager',
                         'revision': None, 'preprocessing': 'none' if mock else 'jpeg_lanczos224_crop_area0.9',
                         'action_postprocessing': 'gripper_binarize_and_invert'}
        if mock:
            return
        import torch
        import tensorflow as tf
        from huggingface_hub import model_info
        from transformers import AutoProcessor, AutoModelForVision2Seq, BitsAndBytesConfig
        if not torch.cuda.is_available():
            raise RuntimeError('Cloud model needs an NVIDIA GPU. No CPU fallback or local weights.')
        tf.config.set_visible_devices([], 'GPU')
        resolved = model_info(CHECKPOINT, revision=revision).sha
        self.metadata['revision'] = resolved
        options = dict(revision=resolved, trust_remote_code=True,
                       torch_dtype=torch.float16, attn_implementation='eager',
                       low_cpu_mem_usage=True, device_map={'': 0})
        if precision == '4bit':
            options['quantization_config'] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type='nf4',
                bnb_4bit_compute_dtype=torch.float16)
        self.model = AutoModelForVision2Seq.from_pretrained(CHECKPOINT, **options).eval()
        self.processor = AutoProcessor.from_pretrained(
            CHECKPOINT, revision=resolved, trust_remote_code=True)
        keys = self.model.norm_stats
        self.unnorm_key = next((k for k in ['libero_spatial', 'libero_spatial_no_noops'] if k in keys), None)
        if self.unnorm_key is None:
            raise RuntimeError('Checkpoint lacks LIBERO-Spatial action statistics.')
        self.metadata['unnorm_key'] = self.unnorm_key
        self.torch, self.tf = torch, tf

    def predict(self, image, instruction):
        if self.mock:
            return [0, 0, 0, 0, 0, 0, -1]
        with self.lock, self.torch.inference_mode():
            image = prepare_image(image, self.tf)
            prompt = 'In: What action should the robot take to ' + instruction.lower() + '?\nOut:'
            batch = self.processor(prompt, image).to('cuda:0', dtype=self.torch.float16)
            # Keep the mask aligned with OpenVLA's required terminal prompt token.
            if batch['input_ids'][0, -1].item() != 29871:
                ids = batch['input_ids']
                batch['input_ids'] = self.torch.cat([ids, ids.new_full((1, 1), 29871)], dim=1)
                mask = batch['attention_mask']
                batch['attention_mask'] = self.torch.cat([mask, mask.new_ones((1, 1))], dim=1)
            action = np.asarray(self.model.predict_action(
                **batch, unnorm_key=self.unnorm_key, do_sample=False), dtype=float).copy()
            # Convert OpenVLA's [0,1] gripper convention to LIBERO's signed control.
            action[-1] = -float(np.sign(2 * action[-1] - 1))
            return action.tolist()


def make_server(policy, token, host='127.0.0.1', port=8000):
    if not token:
        raise ValueError('Set VLA_API_TOKEN before starting the endpoint.')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # Do not write tokens or observation payloads to access logs.

        def send_json(self, status, payload):
            body = json.dumps(payload, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                self.send_json(401, {'error': 'unauthorized'})
                return False
            return True

        def do_GET(self):
            if self.authorized():
                self.send_json(200 if self.path == '/health' else 404,
                               policy.metadata if self.path == '/health' else {'error': 'not_found'})

        def do_POST(self):
            if not self.authorized():
                return
            if self.path != '/act':
                self.send_json(404, {'error': 'not_found'})
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 2_000_000:
                    raise ValueError('Request must be at most 2 MB.')
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError('Expected a JSON object.')
                if request.get('contract') != CONTRACT:
                    raise ValueError('Wrong action contract.')
                instruction = request['instruction']
                if not isinstance(instruction, str) or not 1 <= len(instruction) <= 2000:
                    raise ValueError('Invalid instruction.')
                raw = base64.b64decode(request['image_png'], validate=True)
                with Image.open(io.BytesIO(raw)) as source:
                    if source.size != (256, 256):
                        raise ValueError('Expected rotated 256x256 RGB camera image.')
                    image = source.convert('RGB')
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.send_json(400, {'error': str(exc)})
                return
            try:
                start = time.perf_counter()
                action = policy.predict(image, instruction)
                values = np.asarray(action, dtype=float)
                if values.shape != (7,) or not np.isfinite(values).all() or (np.abs(values) > 1.000001).any():
                    raise ValueError('Policy returned invalid LIBERO control values.')
                self.send_json(200, {'contract': CONTRACT, 'action': action,
                                    'inference_seconds': time.perf_counter()-start})
            except Exception:
                import traceback
                traceback.print_exc()
                self.send_json(500, {'error': 'Policy inference failed; inspect cloud server log.'})

    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--revision', default='main')
    parser.add_argument('--precision', choices=['4bit', 'fp16'], default='4bit')
    args = parser.parse_args()
    token = os.environ.get('VLA_API_TOKEN', '')
    if not token:
        parser.error('Set VLA_API_TOKEN.')
    policy = Policy(args.mock, args.revision, args.precision)
    print(json.dumps(policy.metadata), flush=True)
    make_server(policy, token, port=args.port).serve_forever()
