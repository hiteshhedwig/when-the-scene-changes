"""Regression: OpenVLA appends token 29871 without extending a provided mask."""
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from policy_server import Policy


class Batch(dict):
    def to(self, *args, **kwargs):
        return self


class PromptAlignmentTest(unittest.TestCase):
    def exercise(self, tokens, mask):
        batch = Batch(input_ids=torch.tensor([tokens]), attention_mask=torch.tensor([mask]))
        original_length = len(tokens)
        class Model:
            def predict_action(self, input_ids, attention_mask, **kwargs):
                # Reproduce the relevant contract of the upstream wrapper.
                if input_ids[0,-1] != 29871:
                    input_ids = torch.cat([input_ids, input_ids.new_full((1,1),29871)],dim=1)
                if input_ids.shape != attention_mask.shape:
                    raise RuntimeError('Attention mask length mismatch')
                self.ids, self.mask = input_ids, attention_mask
                return np.zeros(7)
        policy = Policy.__new__(Policy)
        policy.mock, policy.lock = False, threading.Lock()
        policy.torch, policy.tf = torch, None
        policy.unnorm_key = 'libero_spatial'
        policy.processor = lambda *a: batch
        policy.model = Model()
        with patch('policy_server.prepare_image', side_effect=lambda img, tf: img):
            result = policy.predict(Image.new('RGB',(256,256)), 'pick up bowl')
        self.assertEqual(len(result),7)
        self.assertEqual(policy.model.mask[0,:original_length].tolist(),mask)
        return policy.model.ids,policy.model.mask

    def test_missing_terminal_token_extends_mask(self):
        ids,mask = self.exercise([1,42,99],[1,1,1])
        self.assertEqual(ids.tolist(),[[1,42,99,29871]])
        self.assertEqual(mask.tolist(),[[1,1,1,1]])

    def test_existing_terminal_token_is_not_duplicated(self):
        ids,mask = self.exercise([1,42,29871],[1,1,1])
        self.assertEqual(ids.shape,(1,3))
        self.assertEqual(mask.shape,(1,3))

    def test_padding_mask_is_preserved(self):
        ids,mask = self.exercise([0,1,42],[0,1,1])
        self.assertEqual(mask.tolist(),[[0,1,1,1]])


if __name__=='__main__':
    unittest.main()
