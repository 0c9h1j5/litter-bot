"""장면 전체 밀기 실측 — 패드 폭에 따른 줄 수·밀기 시간·커버리지 (robot_v2 기본 wide_side, gym_v2)

    uv run python scripts/build_robot_v2.py
    uv run python src/checks/sweep_measure.py            # 지금 패드(robot_params.yaml pad_radius)와 예전 0.07 m 비교
    uv run python src/checks/sweep_measure.py 0.055      # 패드 반지름 하나만

방식 (requirements ①-2 C-02·C-03·C-14·C-18과 같은 가정):
  - 줄 간격 = 패드 2장 폭 × 0.9, 줄은 x 방향(5 m), 운행 0.3 m/s. 줄 끝에서 제자리 180° 회전(시뮬 상한 225°/s) + 옆으로 한 줄.
  - 줄 앞뒤 끝은 차체(390 mm)가 바닥 5 m 안에 머무는 데까지(1 cm 여유). 옆은 벽 쪽만 차체가 벽 1 cm 앞까지.
  - 두 가지로 잰다: '줄 끝 메우기 없음'(C-03 가정 그대로)과 '줄 끝 메우기'(돈 뒤 같은 줄을 조금 갔다 옴).
  - 벤치 다리·가방·의자 다리·공은 충돌을 끄고 지나간다(우회 시간은 빠짐). 대신 그 바닥 칸은 분모에서 뺀다(C-18).
  - 커버리지 = 뒤 패드 원 안에 한 번이라도 든 5 cm 칸 / (6,000칸 − 장애물 칸). 집기(모드 1)·인식 시간은 빠짐.
  - 출발 = 충전 자리(시작 자리 -0.6, 0.2), 끝나면 같은 자리로 복귀.
"""
import sys

import mujoco
import numpy as np

sys.path.insert(0, "src/checks")
sys.path.insert(0, "scripts")
from build_robot_v2 import PARAMS, STOW_V2, VARIANTS, wmax  # noqa: E402
from robot_v1_util import ids  # noqa: E402

V = 0.3                     # 운행 속도 m/s (기획자 결정 2026-11-24)
CELL = 0.05                 # 커버리지 칸 5 cm (C-18)
FX, FY = 2.5, 1.5           # 바닥 반 크기 (gym_v0 floor)
DOCK = np.array([-0.6, 0.2])
PAINT_EVERY = 5             # 몇 스텝마다 칠할지 (0.002 s × 5 = 10 ms, 0.3 m/s면 3 mm)


def obstacle_cells(m, d, xs, ys):
    """바닥에 닿는 장애물(벤치 다리·가방·의자 다리·공)의 바닥 칸 — 분모에서 뺀다 (C-18)."""
    mask = np.zeros((len(xs), len(ys)), bool)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    for g in range(m.ngeom):
        if not m.body(m.geom_bodyid[g]).name.startswith("obstacle_"):
            continue
        c, s, t = d.geom_xpos[g], m.geom_size[g], m.geom_type[g]
        if t == mujoco.mjtGeom.mjGEOM_BOX:
            lo_z, hx, hy = c[2] - s[2], s[0], s[1]
            if lo_z < 0.02:
                mask |= (abs(X - c[0]) <= hx) & (abs(Y - c[1]) <= hy)
        elif t in (mujoco.mjtGeom.mjGEOM_CYLINDER, mujoco.mjtGeom.mjGEOM_SPHERE):
            r = s[0]
            lo_z = c[2] - (s[1] if t == mujoco.mjtGeom.mjGEOM_CYLINDER else r)
            if lo_z < 0.02:
                mask |= (X - c[0]) ** 2 + (Y - c[1]) ** 2 <= r ** 2
    return mask


def run(pad_r, fill_ends=True):
    v = VARIANTS["wide_side"]
    m = mujoco.MjModel.from_xml_path("scenes/gym_v2.xml")
    d = mujoco.MjData(m)
    I = ids(m)
    rb = m.body("robot").id
    pads = [m.geom(f"pad_{s}").id for s in ("left", "right")]
    L, W = v["length"], v["width"]
    # 패드 반지름 바꾸기 (생성기와 같은 배치: 몸 뒤, 좌우로 반지름만큼)
    for g, s in zip(pads, (1, -1)):
        m.geom_size[g][0] = pad_r
        m.geom_pos[g][0] = -L / 2 - pad_r + 0.01
        m.geom_pos[g][1] = s * pad_r
    d.qpos[I["qadr"]] = STOW_V2
    d.ctrl[I["act"]] = STOW_V2
    mujoco.mj_forward(m, d)
    xs = np.arange(-FX + CELL / 2, FX, CELL)
    ys = np.arange(-FY + CELL / 2, FY, CELL)
    obst = obstacle_cells(m, d, xs, ys)
    # 로봇 밖(바닥 빼고) 충돌 끄기 — 장애물 우회는 빼고 밀기 기하만 잰다
    floor = m.geom("floor").id
    for g in range(m.ngeom):
        b = m.geom_bodyid[g]
        root = m.body_rootid[b]
        if g != floor and root != m.body_rootid[rb]:
            m.geom_contype[g] = 0
            m.geom_conaffinity[g] = 0
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    cov = np.zeros_like(obst)
    w_rot = wmax(v)
    step = [0]

    def paint():
        for g in pads:
            c = d.geom_xpos[g]
            cov[:] |= (X - c[0]) ** 2 + (Y - c[1]) ** 2 <= pad_r ** 2

    # base_x/base_y 관절값은 시작 자리(robot_start 프레임) 기준 → 월드 좌표로 바꿀 때 더한다
    q0 = np.array([d.qpos[a] for a in I["base_q"]])
    off = d.xpos[rb][:2] - q0[:2]

    def pose():
        q = np.array([d.qpos[a] for a in I["base_q"]])
        q[:2] += off
        return q

    def go(target_xy, target_yaw, paint_on):
        t0 = d.time
        while True:
            x, y, yaw = pose()
            e = np.asarray(target_xy) - [x, y]
            dist = np.hypot(*e)
            ey = (target_yaw - yaw + np.pi) % (2 * np.pi) - np.pi
            if dist < 0.002 and abs(ey) < 0.002:
                break
            vel = e / dist * min(V, dist / m.opt.timestep) if dist > 1e-9 else np.zeros(2)
            wz = np.clip(ey / m.opt.timestep, -w_rot, w_rot)
            d.ctrl[I["drive"][0]], d.ctrl[I["drive"][1]], d.ctrl[I["drive"][2]] = vel[0], vel[1], wz
            mujoco.mj_step(m, d)
            step[0] += 1
            if paint_on and step[0] % PAINT_EVERY == 0:
                paint()
            if d.time - t0 > 600:
                raise RuntimeError("멈춤")
        return d.time - t0

    width = 4 * pad_r
    gap = 0.9 * width
    x_lo, x_hi = -FX + L / 2 + 0.01, FX - L / 2 - 0.01
    # 옆: 벽 쪽(+y, wall_side)은 차체가 벽 1 cm 앞까지, 열린 쪽(-y)은 패드 끝이 장면 끝에 오게 (차체는 3 cm 밖, 코트가 이어짐)
    y_lo, y_hi = -FY + width / 2, FY - W / 2 - 0.01
    # 줄 끝 메우기: 뒤 패드는 몸 뒤에 있어서, 줄 끝에서 서면 '몸 밑 + 패드 앞' 띠(약 0.4 m)가 남는다.
    # 180° 돈 뒤 같은 줄을 back 만큼 갔다가 돌아오면 그 띠를 패드가 지나간다.
    back = L + 2 * pad_r - 0.02
    lanes = list(np.arange(y_lo, y_hi, gap))
    if y_hi - lanes[-1] > 1e-6:
        lanes.append(y_hi)
    t_to = go((x_lo, lanes[0]), 0.0, False)
    t_sweep = 0.0
    turns = 0
    for i, y in enumerate(lanes):
        fwd = i % 2 == 0
        xe, yaw_new = (x_hi, np.pi) if fwd else (x_lo, 0.0)
        t_sweep += go((xe, y), 0.0 if fwd else np.pi, True)
        if i + 1 < len(lanes) or fill_ends:
            # 줄 끝: 제자리 180° 회전
            t_sweep += go((xe, y), yaw_new, True)
            turns += 1
        if fill_ends:
            t_sweep += go((xe - back if fwd else xe + back, y), yaw_new, True)
            t_sweep += go((xe, y), yaw_new, True)
        if i + 1 < len(lanes):
            # 옆으로 한 줄
            t_sweep += go((xe, lanes[i + 1]), yaw_new, True)
    t_back = go(DOCK, 0.0, True)
    valid = ~obst
    pct = 100.0 * (cov & valid).sum() / valid.sum()
    # 못 칠한 칸이 어디에 있는지 (가장자리 띠인지)
    miss = valid & ~cov
    edge = miss & ((X < x_lo - L / 2 + 0.1) | (X > x_hi + L / 2 - 0.1) | (Y < y_lo - W / 2 + 0.1) | (Y > y_hi + W / 2 - 0.1))
    res = dict(fill_ends=fill_ends, back=back if fill_ends else 0.0, pad_r=pad_r, width=width, gap=gap, lanes=len(lanes), turns=turns, lane_len=x_hi - x_lo,
               t_to=t_to, t_sweep=t_sweep, t_back=t_back, total=t_to + t_sweep + t_back,
               cells=int(valid.sum()), obst=int(obst.sum()), covered=int((cov & valid).sum()), pct=pct,
               miss=int(miss.sum()), miss_edge=int(edge.sum()))
    return res


def show(r):
    how = f"줄 끝 메우기 {r['back']:.2f} m 왕복" if r["fill_ends"] else "줄 끝 메우기 없음 (C-03 가정 그대로)"
    print(f"패드 반지름 {r['pad_r']:.3f} m → 2장 폭 {r['width']:.2f} m, 줄 간격 {r['gap']:.3f} m, "
          f"{r['lanes']}줄 × {r['lane_len']:.2f} m, 줄 끝 회전 {r['turns']}번, {how}")
    print(f"   시간: 충전 자리 → 첫 줄 {r['t_to']:.1f} s + 밀기 {r['t_sweep']:.1f} s + 복귀 {r['t_back']:.1f} s "
          f"= {r['total']:.1f} s (집기·인식 빠짐)")
    print(f"   커버리지: {r['covered']} / {r['cells']}칸 (6,000칸 − 장애물 {r['obst']}칸) = {r['pct']:.1f} % "
          f"— 못 칠한 {r['miss']}칸 중 가장자리 띠(10 cm) {r['miss_edge']}칸")


if __name__ == "__main__":
    now = PARAMS["scale_model"]["cleaning"]["pad_radius"]["value"]
    radii = [float(a) for a in sys.argv[1:]] or [now, 0.07]
    for r in radii:
        for fill in (False, True):
            show(run(r, fill))
