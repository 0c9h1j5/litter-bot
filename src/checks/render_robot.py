"""robot_v1 / gym_v1 / robot_v2 그림.
uv run --with pillow python src/checks/render_robot.py robot  docs/img/robot_v1.png
uv run --with pillow python src/checks/render_robot.py gym    docs/img/gym_v1.png
uv run --with pillow python src/checks/render_robot.py robot2 docs/img/robot_v2.png   # 왼쪽 X3 차체, 오른쪽 설계 어림 차체(wide) — 크래들 접기 / 앞 바닥 집기
"""
import sys
import mujoco
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "scripts")
which, out = sys.argv[1], sys.argv[2]


def shot(path, pose, lookat, dist, az, el, w=900, h=700):
    m = mujoco.MjModel.from_xml_path(path); d = mujoco.MjData(m)
    for n, v in pose.items():
        d.qpos[m.jnt_qposadr[m.joint("arm_" + n).id]] = v
        d.ctrl[m.actuator("arm_" + n).id] = v
    mujoco.mj_forward(m, d)
    for _ in range(300):
        mujoco.mj_step(m, d)
    opt = mujoco.MjvOption(); opt.sitegroup[:] = 1; opt.frame = mujoco.mjtFrame.mjFRAME_NONE
    r = mujoco.Renderer(m, h, w)
    cam = mujoco.MjvCamera(); cam.lookat[:] = lookat; cam.distance = dist; cam.azimuth = az; cam.elevation = el
    r.update_scene(d, cam, opt)
    return Image.fromarray(r.render())


if which == "robot2":
    from build_robot_v2 import STOW_V2
    names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
    stow = dict(zip(names, STOW_V2), gripper=0.0)
    reach = {"shoulder_pan": 0.0, "shoulder_lift": 0.6, "elbow_flex": 0.2, "wrist_flex": 0.9, "gripper": 0.8}
    tiles = []
    for path, lab in (("scenes/robot_v2.xml", "X3 30x20 cm"), ("scenes/robot_v2_wide.xml", "wide 39x28 cm")):
        for pose, pl in ((stow, "STOW (cradle)"), (reach, "reach floor")):
            im = shot(path, pose, [0.02, 0.0, 0.13], 0.95, 215, -30)
            ImageDraw.Draw(im).text((12, 10), f"{lab} / {pl}", fill=(255, 255, 255))
            tiles.append(im)
    W, H = tiles[0].size
    canvas = Image.new("RGB", (2 * W, 2 * H), "white")
    for k, im in enumerate(tiles):
        canvas.paste(im, ((k // 2) * W, (k % 2) * H))
    canvas.save(out); print("saved", out); sys.exit()

path = {"robot": "scenes/robot_v1.xml", "gym": "scenes/gym_v1.xml"}[which]
# 로봇 그림: 팔을 앞으로 내민 자세 / 장면 그림: 접은 자세(이동 중) — new calib 관절값, rad
pose = ({"shoulder_pan": 0.0, "shoulder_lift": 0.6, "elbow_flex": 0.2, "wrist_flex": 0.9, "gripper": 0.8} if which == "robot"
        else {"shoulder_pan": 0.0, "shoulder_lift": -1.5, "elbow_flex": 1.5, "wrist_flex": 1.0, "gripper": 0.0})
if which == "robot":
    shot(path, pose, [0.05, 0.0, 0.15], 1.05, 215, -24, 1400, 1000).save(out)
else:
    shot(path, pose, [0.0, 0.3, 0.4], 5.4, 62, -32, 1600, 1000).save(out)
print("saved", out)
