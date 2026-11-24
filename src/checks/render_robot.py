"""robot_v1 / gym_v1 그림.
uv run --with pillow python src/checks/render_robot.py robot docs/img/robot_v1.png
uv run --with pillow python src/checks/render_robot.py gym   docs/img/gym_v1.png
"""
import sys
import mujoco
from PIL import Image

which, out = sys.argv[1], sys.argv[2]
path = {"robot": "scenes/robot_v1.xml", "gym": "scenes/gym_v1.xml"}[which]
m = mujoco.MjModel.from_xml_path(path); d = mujoco.MjData(m)
# 로봇 그림: 팔을 앞으로 내민 자세 / 장면 그림: 접은 자세(이동 중) — new calib 관절값, rad
pose = ({"shoulder_pan": 0.0, "shoulder_lift": 0.6, "elbow_flex": 0.2, "wrist_flex": 0.9, "gripper": 0.8} if which == "robot"
        else {"shoulder_pan": 0.0, "shoulder_lift": -1.5, "elbow_flex": 1.5, "wrist_flex": 1.0, "gripper": 0.0})
for n, v in pose.items():
    d.qpos[m.jnt_qposadr[m.joint("arm_" + n).id]] = v
    d.ctrl[m.actuator("arm_" + n).id] = v
mujoco.mj_forward(m, d)
for _ in range(300):
    mujoco.mj_step(m, d)
opt = mujoco.MjvOption()
opt.sitegroup[:] = 1          # 흡입구·바구니 판정 영역(반투명)도 보이게
opt.frame = mujoco.mjtFrame.mjFRAME_NONE
if which == "robot":
    r = mujoco.Renderer(m, 1000, 1400)
    cam = mujoco.MjvCamera(); cam.lookat[:] = [0.05, 0.0, 0.15]; cam.distance = 1.05; cam.azimuth = 215; cam.elevation = -24
else:
    r = mujoco.Renderer(m, 1000, 1600)
    cam = mujoco.MjvCamera(); cam.lookat[:] = [0.0, 0.3, 0.4]; cam.distance = 5.4; cam.azimuth = 62; cam.elevation = -32
r.update_scene(d, cam, opt)
Image.fromarray(r.render()).save(out)
print("saved", out)
