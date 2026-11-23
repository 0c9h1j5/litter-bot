"""장면 렌더 1장: uv run --with pillow python src/checks/render_scene.py scenes/gym_v0.xml docs/img/gym_v0.png"""
import sys, mujoco, numpy as np
from PIL import Image
m = mujoco.MjModel.from_xml_path(sys.argv[1]); d = mujoco.MjData(m)
mujoco.mj_forward(m, d)
for _ in range(500): mujoco.mj_step(m, d)  # 1 s 안정화
moved = [m.body(i).name for i in range(m.nbody) if m.body(i).name.startswith("litter") and np.linalg.norm(d.xpos[i][:2]-m.body_pos[i][:2])>0.01]
print("moved after 1s:", moved)
r = mujoco.Renderer(m, 1000, 1600)
cam = mujoco.MjvCamera(); cam.lookat[:] = [0.0, 0.3, 0.4]; cam.distance = 5.4; cam.azimuth = 62; cam.elevation = -32
r.update_scene(d, cam); Image.fromarray(r.render()).save(sys.argv[2]); print("saved")
