"""Deterministic sensor-input perturbations. Never modify simulator observations."""
import math
import numpy as np


def validate_spec(spec):
    if not isinstance(spec, dict) or spec.get('name') not in ['brightness_shift','camera_occlusion']:
        raise ValueError('Unknown camera perturbation.')
    for key in ['start_step','duration_steps']:
        if type(spec.get(key)) is not int or spec[key] < (1 if key=='duration_steps' else 0):
            raise ValueError('Invalid '+key)
    if spec['name']=='brightness_shift':
        factor=spec.get('factor')
        if isinstance(factor,bool) or not isinstance(factor,(int,float)) or not math.isfinite(factor) or not 0 < factor <= 1:
            raise ValueError('Brightness factor must be in (0,1].')
    else:
        rectangle=spec.get('rectangle_xyxy')
        if not isinstance(rectangle,list) or len(rectangle)!=4 or any(type(x) is not int for x in rectangle):
            raise ValueError('Rectangle must be four integer pixel coordinates.')
        x0,y0,x1,y1=rectangle
        if not (0<=x0<x1<=256 and 0<=y0<y1<=256):
            raise ValueError('Rectangle must lie inside the 256x256 image.')
        fill=spec.get('fill_rgb')
        if not isinstance(fill,list) or len(fill)!=3 or any(type(x) is not int or not 0<=x<=255 for x in fill):
            raise ValueError('Fill must be three RGB bytes.')
    return spec


def is_active(step, spec):
    return spec is not None and spec['start_step'] <= step < spec['start_step']+spec['duration_steps']


def perturb_camera(rgb, step, spec=None):
    if rgb.shape!=(256,256,3) or rgb.dtype!=np.uint8:
        raise ValueError('Expected 256x256 uint8 RGB camera image.')
    result=rgb.copy()
    if not is_active(step,spec):
        return result
    if spec['name']=='brightness_shift':
        result=np.rint(result.astype(np.float32)*spec['factor']).clip(0,255).astype(np.uint8)
    else:
        x0,y0,x1,y1=spec['rectangle_xyxy']
        result[y0:y1,x0:x1]=spec['fill_rgb']
    return np.ascontiguousarray(result)
