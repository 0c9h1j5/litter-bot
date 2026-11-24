"""robot_v1 공용 도구: 차체 속도 명령, SO-101 관절 이름, 손끝 위치, 간단한 수치 IK.

다른 확인 스크립트(mecanum_so101_measure.py, render_robot.py)가 import 한다.
"""
import mujoco
import numpy as np

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
P = "arm_"   # robot_v1 에서 SO-101 이름 앞에 붙인 접두사


def ids(m):
    """자주 쓰는 id 묶음."""
    return dict(
        qadr=[m.jnt_qposadr[m.joint(P + n).id] for n in ARM],
        dadr=[m.jnt_dofadr[m.joint(P + n).id] for n in ARM],
        act=[m.actuator(P + n).id for n in ARM],
        grip_act=m.actuator(P + "gripper").id,
        grip_q=m.jnt_qposadr[m.joint(P + "gripper").id],
        tip=m.site(P + "gripperframe").id,
        base_q=[m.jnt_qposadr[m.joint(n).id] for n in ("base_x", "base_y", "base_yaw")],
        drive=[m.actuator(n).id for n in ("drive_x", "drive_y", "drive_yaw")],
        robot=m.body("robot").id,
    )


def drive(m, d, I, vx, vy, w):
    """차체 기준 속도(앞 vx, 왼 vy m/s, 회전 w rad/s)를 월드 기준 액추에이터 명령으로."""
    yaw = d.qpos[I["base_q"][2]]
    c, s = np.cos(yaw), np.sin(yaw)
    d.ctrl[I["drive"][0]] = c * vx - s * vy
    d.ctrl[I["drive"][1]] = s * vx + c * vy
    d.ctrl[I["drive"][2]] = w


def to_body(m, d, I, p_world):
    """월드 점을 차체 좌표(원점 = 차체 가운데 바닥, x 앞)로."""
    x, y, yaw = (d.qpos[a] for a in I["base_q"])
    v = np.asarray(p_world)[:2] - [x, y]
    c, s = np.cos(-yaw), np.sin(-yaw)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1], p_world[2]])


def ik(m, d, I, target, down=None, q0=None, iters=300, tol=1e-3, dots=None, offset=None):
    """손끝(gripperframe) 위치를 target(월드)로. down=(축 이름, 방향 벡터) 또는 그 목록이면 gripperframe 의 그 축(들)을 맞춘다.
    dots=[(축 이름 또는 gripperframe 벡터, 월드 벡터, 값)] 이면 gripperframe 축 · 벡터 = 값 을 맞춘다(예: 집게 닫는 축을 수평으로: ("z", ez, 0)).
    offset=(x, y, z)이면 손끝 대신 gripperframe 좌표의 그 점(예: 두 손가락 사이 집는 점)을 target 으로 보낸다.
    팔 관절 5개만 쓰는 감쇠 최소자승. 결과 관절값, 위치 오차(m)를 돌려준다. d 는 바꾸지 않는다."""
    dd = mujoco.MjData(m)
    dd.qpos[:] = d.qpos
    if q0 is not None:
        dd.qpos[I["qadr"]] = q0
    lo = m.jnt_range[[m.joint(P + n).id for n in ARM], 0]
    hi = m.jnt_range[[m.joint(P + n).id for n in ARM], 1]
    jp = np.zeros((3, m.nv)); jr = np.zeros((3, m.nv))
    for _ in range(iters):
        mujoco.mj_kinematics(m, dd); mujoco.mj_comPos(m, dd)
        pt = point(dd, I, offset)
        err = np.asarray(target) - pt
        mujoco.mj_jac(m, dd, jp, jr, pt, m.site_bodyid[I["tip"]])
        J = jp[:, I["dadr"]]; e = err
        if down is not None:
            R = dd.site_xmat[I["tip"]].reshape(3, 3)
            for axis, want in ([down] if isinstance(down[0], str) else down):
                a = R[:, "xyz".index(axis)]
                eo = np.cross(a, want)
                J = np.vstack([J, 0.3 * jr[:, I["dadr"]]]); e = np.concatenate([e, 0.3 * eo])
        if dots:
            R = dd.site_xmat[I["tip"]].reshape(3, 3)
            for axis, v, val in dots:
                a = _axis(R, axis)
                row = np.cross(a, v) @ jr[:, I["dadr"]]
                J = np.vstack([J, 0.3 * row]); e = np.concatenate([e, [0.3 * (val - a @ v)]])
        if np.linalg.norm(err) < tol and (len(e) == 3 or np.linalg.norm(e[3:]) < 0.02):
            break
        dq = J.T @ np.linalg.solve(J @ J.T + 1e-4 * np.eye(len(e)), e)
        q = np.clip(dd.qpos[I["qadr"]] + 0.5 * dq, lo, hi)
        dd.qpos[I["qadr"]] = q
    mujoco.mj_kinematics(m, dd)
    # 돌려주는 오차 = 위치 오차(m) + 자세 오차(rad·0.1 m) — 자세 조건을 못 맞추면 큰 값이 되게
    e_pos = float(np.linalg.norm(np.asarray(target) - point(dd, I, offset)))
    return dd.qpos[I["qadr"]].copy(), e_pos + 0.1 * _ori_err(dd, I, down, dots)


def _ori_err(d, I, down, dots):
    R = d.site_xmat[I["tip"]].reshape(3, 3); e = 0.0
    if down is not None:
        for axis, want in ([down] if isinstance(down[0], str) else down):
            e += float(np.linalg.norm(np.cross(R[:, "xyz".index(axis)], want)))
    for axis, v, val in (dots or []):
        e += abs(val - float(_axis(R, axis) @ v))
    return e


def _axis(R, axis):
    """gripperframe 축: 'x'·'y'·'z' 또는 gripperframe 좌표의 벡터(예: 잡은 병의 축)."""
    return R[:, "xyz".index(axis)] if isinstance(axis, str) else R @ np.asarray(axis)


def point(d, I, offset=None):
    """gripperframe 좌표의 점 offset 을 월드로 (None 이면 손끝)."""
    p = d.site_xpos[I["tip"]].copy()
    if offset is not None:
        p += d.site_xmat[I["tip"]].reshape(3, 3) @ np.asarray(offset)
    return p
