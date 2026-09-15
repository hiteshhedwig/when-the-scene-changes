from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from camera_perturbations import perturb_camera, is_active, validate_spec

class CameraPerturbationTest(unittest.TestCase):
    def setUp(self):
        self.image=np.full((256,256,3),200,dtype=np.uint8)
        self.dark={'name':'brightness_shift','start_step':30,'duration_steps':30,'factor':.35}
        self.occlusion={'name':'camera_occlusion','start_step':30,'duration_steps':30,
                        'rectangle_xyxy':[40,104,136,200],'fill_rgb':[0,0,0]}

    def test_transient_boundaries_and_restoration(self):
        for step,active in [(29,False),(30,True),(59,True),(60,False)]:
            with self.subTest(step=step):
                self.assertEqual(is_active(step,self.dark),active)
                changed=perturb_camera(self.image,step,self.dark)
                self.assertTrue(np.all(changed==(70 if active else 200)))
        self.assertTrue(np.all(self.image==200))

    def test_patch_area_and_raw_image_preserved(self):
        changed=perturb_camera(self.image,30,self.occlusion)
        black=np.all(changed==0,axis=-1)
        self.assertEqual(int(black.sum()),96*96)
        self.assertTrue(np.all(changed[104:200,40:136]==0))
        self.assertTrue(np.all(changed[~black]==200))
        self.assertTrue(np.all(self.image==200))

    def test_clean_is_identical_and_independent(self):
        result=perturb_camera(self.image,30,None)
        np.testing.assert_array_equal(result,self.image)
        result[0,0]=0
        self.assertTrue(np.all(self.image==200))

    def test_invalid_severity_or_geometry_rejected(self):
        for change in [{'factor':float('nan')},{'factor':0},{'duration_steps':0}]:
            with self.assertRaises(ValueError): validate_spec(dict(self.dark,**change))
        with self.assertRaises(ValueError):
            validate_spec(dict(self.occlusion,rectangle_xyxy=[40,104,300,200]))
