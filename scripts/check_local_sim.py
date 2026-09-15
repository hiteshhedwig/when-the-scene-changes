"""Small local MuJoCo physics/render check; no policy or robot benchmark."""
import json
import time
from pathlib import Path
import mujoco
from PIL import Image

out = Path('results/local-check')
out.mkdir(parents=True, exist_ok=True)
model = mujoco.MjModel.from_xml_string('''<mujoco>
<option timestep="0.002"/><visual><global offwidth="256" offheight="256"/></visual>
<worldbody><light pos="0 0 3"/><geom type="plane" size="2 2 .1" rgba=".3 .4 .5 1"/>
<body pos="0 0 .6"><freejoint/><geom type="box" size=".08 .08 .08" mass=".1" rgba="1 .2 .1 1"/></body>
</worldbody></mujoco>''')
data = mujoco.MjData(model)
start = time.perf_counter()
for _ in range(1000):
    mujoco.mj_step(model, data)
physics_seconds = time.perf_counter() - start
with mujoco.Renderer(model, height=256, width=256) as renderer:
    start = time.perf_counter()
    for _ in range(100):
        renderer.update_scene(data)
        pixels = renderer.render()
    render_seconds = time.perf_counter() - start
    Image.fromarray(pixels).save(out / 'render.png')
report = {'mujoco_version':mujoco.__version__, 'physics_steps':1000,
          'physics_seconds':physics_seconds, 'render_frames':100,
          'render_seconds':render_seconds, 'render_fps':100/render_seconds,
          'resolution':[256,256], 'final_box_height':float(data.qpos[2]),
          'scope':'simple box scene only; LIBERO and learned policy not tested'}
(out / 'report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
