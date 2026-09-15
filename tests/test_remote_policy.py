import base64
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'cloud'))
from remote_policy import CONTRACT, RemotePolicy, validate_action
from policy_server import Policy, make_server


class RemoteProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(Policy(mock=True), 'test-token', port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)
        cls.client = RemotePolicy(cls.url, 'test-token')

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_camera_to_mock_action(self):
        self.assertEqual(self.client.health()['policy'], 'mock')
        result = self.client.act(np.zeros((256,256,3), dtype=np.uint8), 'place the bowl')
        self.assertEqual(result['action'], [0,0,0,0,0,0,-1])
        self.assertGreaterEqual(result['inference_seconds'], 0)

    def test_bad_token_rejected(self):
        with self.assertRaises(HTTPError) as error:
            RemotePolicy(self.url, 'wrong').health()
        self.assertEqual(error.exception.code, 401)

    def test_bad_image_rejected_by_server(self):
        image = io.BytesIO()
        Image.new('RGB', (32,32)).save(image, 'PNG')
        with self.assertRaises(HTTPError) as error:
            self.client.request('/act', {'contract':CONTRACT, 'instruction':'test',
                'image_png':base64.b64encode(image.getvalue()).decode()})
        self.assertEqual(error.exception.code, 400)

    def test_action_contract_rejects_bad_controls(self):
        for action in [[0]*6, [0]*6+[float('nan')], [0]*6+[2], [0]*6+[True]]:
            with self.subTest(action=action), self.assertRaises(ValueError):
                validate_action({'contract':CONTRACT, 'action':action})
        with self.assertRaises(ValueError):
            validate_action({'contract':'other', 'action':[0]*7})

    def test_cloud_requires_tls(self):
        with self.assertRaises(ValueError):
            RemotePolicy('http://example.com', 'test-token')


if __name__ == '__main__':
    unittest.main()
