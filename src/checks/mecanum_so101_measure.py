"""메카넘 차체 + SO-101 실측 (logs/2026-11-24_mecanum_so101_measurements.md)

    uv run python src/checks/mecanum_so101_measure.py            # 모두
    uv run python src/checks/mecanum_so101_measure.py speed reach gap pick_trials torque   (pick -v: 한 번, 자세히)

1. speed  : 직진·옆걸음·제자리 회전 최고 속도 (robot_v1, 명령 최대로 3 s, 마지막 1 s 평균)
2. reach  : SO-101 손끝이 바닥 높이(손끝 z = 1 cm)에서 닿는 범위, 차체 기준 앞·옆 (팔-차체 충돌 없는 자세만)
3. gap    : 기획안 원기둥 병(ø65)이 벌린 집게 사이에 들어가나 (틈 mm)
   pick_trials : gym_v1 에서 생수병(litter_bottle1, 빈 병 20 g) 하나를 집어 옆 바구니에 넣기 — 시간·성공
                 (기획안 원기둥 / 뚜껑 모양(가정) × 병 위치 ±2 cm 9곳 + 집게 마찰 0.5)
4. torque : 어깨(shoulder_lift) 토크 — 28차시 so101_토크.py 방식(팔을 수평으로 쭉 편 자세의 m·g·r 합)
            + pick 중 시뮬 액추에이터 힘 최대값 + 넘어짐 여유(무게중심이 바퀴 사각형 안인가)
"""
import sys
import time
import mujoco
import numpy as np

sys.path.insert(0, "src/checks")
from robot_v1_util import ARM, P, drive, ids, ik  # noqa: E402

G = 9.81
KGCM = G / 100            # 1 kg·cm = 0.0981 N·m
OMEGA = 2.0               # 팔 관절 이동 속도 상한 rad/s (가정: STS3215 무부하 약 0.19 s/60° ≈ 5.5 rad/s 의 약 1/3)
OPEN, CLOSE = 0.95, -0.17  # 집게 벌림/닫힘 명령 rad
DEBUG = "-v" in sys.argv
GP_NOW = [(0.0, 0.0, 0.034)]
DROP_IN = 0.05            # 병 바닥을 바구니 테두리 아래로 넣는 깊이 m
STOW = np.array([0.0, -1.5, 1.5, 1.0, 0.0])  # 접은 자세 (이동 중; 팔-몸 충돌 없음 확인)


def robot_geoms(m):
    rb = m.body("robot").id
    arm = {b for b in range(m.nbody) if m.body(b).name.startswith(P)}
    own = [g for g in range(m.ngeom) if m.geom_bodyid[g] in (rb, m.body("basket").id)]
    armg = [g for g in range(m.ngeom) if m.geom_bodyid[g] in arm]
    return set(own), set(armg)


# ---------------------------------------------------------------- 1. speed
def speed():
    m = mujoco.MjModel.from_xml_path("scenes/robot_v1.xml"); I = ids(m)
    out = {}
    vmax = m.actuator_ctrlrange[I["drive"][0], 1]; wmax = m.actuator_ctrlrange[I["drive"][2], 1]
    for name, cmd in (("직진", (vmax, 0, 0)), ("옆걸음", (0, vmax, 0)), ("제자리 회전", (0, 0, wmax))):
        d = mujoco.MjData(m); mujoco.mj_forward(m, d)
        hist = []
        while d.time < 3.0:
            drive(m, d, I, *cmd); mujoco.mj_step(m, d)
            hist.append((d.time, *d.qpos[I["base_q"]]))
        h = np.array(hist); k = h[:, 0] >= 2.0
        dt = h[k, 0][-1] - h[k, 0][0]
        if name == "제자리 회전":
            v = (h[k, 3][-1] - h[k, 3][0]) / dt
            out[name] = (v, np.degrees(v))
            print(f"{name}: {v:.3f} rad/s = {np.degrees(v):.0f} °/s (명령 {wmax} rad/s)")
        else:
            v = np.hypot(h[k, 1][-1] - h[k, 1][0], h[k, 2][-1] - h[k, 2][0]) / dt
            t63 = h[np.argmax(np.hypot(np.gradient(h[:, 1], h[:, 0]), np.gradient(h[:, 2], h[:, 0])) > 0.95 * vmax), 0]
            out[name] = (v, t63)
            print(f"{name}: {v:.3f} m/s (명령 {vmax} m/s), 95% 도달 {t63:.2f} s")
    return out


# ---------------------------------------------------------------- 2. reach
SEEDS = [np.array(s) for s in ([0, 0.8, 0.3, 0.9, 0], [0, 1.2, -0.5, 1.2, 0], [0, 0.3, 0.8, 1.0, 0],
                               [0, 1.5, -1.2, 1.5, 0], [0, 1.0, 0.6, 0.2, 0], [0, 1.6, -0.6, 0.6, 0])]


def reach_ok(m, d, I, own, armg, floor, target, down=None):
    best = None
    for s in SEEDS:
        s = s.copy(); s[0] = np.arctan2(target[1], target[0] - d.xanchor[m.joint(P + "shoulder_pan").id][0])
        s[0] = np.clip(s[0], -1.9, 1.9)
        q, e = ik(m, d, I, target, down=down, q0=s, iters=400)
        if e > 0.005:
            if best is None: best = (False, e)
            continue
        dd = mujoco.MjData(m); dd.qpos[:] = d.qpos; dd.qpos[I["qadr"]] = q; mujoco.mj_forward(m, dd)
        hit = False
        for c in dd.contact[:dd.ncon]:
            pair = {c.geom1, c.geom2}
            if pair & armg and pair & own and c.dist < -0.001:
                hit = True
            if pair & armg and floor in pair and c.dist < -0.005:
                hit = True
        if not hit:
            return True, e
        best = (False, "collide")
    return best


def reach():
    m = mujoco.MjModel.from_xml_path("scenes/robot_v1.xml"); d = mujoco.MjData(m); mujoco.mj_forward(m, d); I = ids(m)
    own, armg = robot_geoms(m); floor = m.geom("floor").id
    pan = d.xanchor[m.joint(P + "shoulder_pan").id].copy()
    res = {"pan_axis": pan}
    z = 0.01
    DOWN = ("x", np.array([0, 0, -1.0]))

    def ok(t):  # 자유 자세 또는 손끝 아래로, 둘 중 하나라도 충돌 없이 닿으면 '닿음'
        return reach_ok(m, d, I, own, armg, floor, t)[0] or reach_ok(m, d, I, own, armg, floor, t, DOWN)[0]

    def span(pts):
        v = [k for k, t in pts if ok(t)]
        return (round(float(min(v)), 2), round(float(max(v)), 2)) if v else None

    lines = {
        "앞 (y = 0)": [(x, np.array([x, 0, z])) for x in np.arange(0.10, 0.60, 0.01)],
        f"오른쪽 (x = {pan[0]:.2f}, 팔 축)": [(y, np.array([pan[0], -y, z])) for y in np.arange(0.08, 0.50, 0.01)],
        f"왼쪽 (x = {pan[0]:.2f}, 바구니 위)": [(y, np.array([pan[0], y, z])) for y in np.arange(0.08, 0.50, 0.01)],
        "왼쪽 (x = 0.25, 바구니 앞)": [(y, np.array([0.25, y, z])) for y in np.arange(0.08, 0.50, 0.01)],
        "오른쪽 (x = 0.0, 차체 가운데)": [(y, np.array([0.0, -y, z])) for y in np.arange(0.08, 0.50, 0.01)],
    }
    for lab, pts in lines.items():
        res[lab] = span(pts)
        print(f"바닥(손끝 z {z} m) {lab}: {res[lab]}  [차체 기준 m, 차체 반폭 {0.0997}, 앞면 0.15]")
    return res


# ---------------------------------------------------------------- 3. pick
def plan(m, d, I, target, axes, seed):
    best = min((ik(m, d, I, target, down=axes, q0=s, iters=600) for s in seed), key=lambda t: t[1])
    return best


def move(m, d, I, q_to, grip, log, extra=0.3, rec=None):
    """관절 공간 직선 보간으로 q_to 까지. 시간 = max|Δq|/OMEGA + extra."""
    q_from = np.array([d.ctrl[a] for a in I["act"]])
    T = float(np.max(np.abs(q_to - q_from))) / OMEGA + extra
    t0 = d.time
    g0 = d.ctrl[I["grip_act"]]
    while d.time - t0 < T:
        s = min(1.0, (d.time - t0) / max(T - extra, 1e-6))
        d.ctrl[I["act"]] = q_from + s * (q_to - q_from)
        d.ctrl[I["grip_act"]] = g0 + s * (grip - g0)
        drive(m, d, I, 0, 0, 0)
        mujoco.mj_step(m, d)
        if rec is not None:
            rec(d)
    log.append(T)
    if DEBUG:
        b = m.body("litter_bottle1").id
        from robot_v1_util import point
        print(f"   [{len(log)}] t={d.time:.2f} 병 {np.round(d.xpos[b], 3)} 집는점 {np.round(point(d, I, GP_NOW[0]), 3)} "
              f"base {np.round(d.qpos[I['base_q']], 3)} q {np.round(d.qpos[I['qadr']], 2)} 집게 {d.qpos[I['grip_q']]:.2f}")


def move_path(m, d, I, qs, grip, log, rec=None):
    """관절 경유점 목록을 차례로 (손끝이 직선으로 움직이게 IK로 만든 경유점). 한 구간으로 기록."""
    sub = []
    for k, q in enumerate(qs):
        move(m, d, I, q, grip, sub, extra=0.3 if k == len(qs) - 1 else 0.0, rec=rec)
    log.append(sum(sub))


def load_gym(bottle="plan", shift=(0.0, 0.0), friction=None, scene="scenes/gym_v1.xml"):
    """bottle="plan": 기획안 크기 원기둥 ø65 × 210 mm, 20 g (gym_v0 그대로).
    bottle="cap": 같은 크기 병에 어깨·목·뚜껑을 준 모양 (가정 — 시판 500 mL 병을 흉내, 실측 필요):
                  몸통 ø65 (0~150 mm), 어깨 ø48 (150~170), ø36 (170~180), 목+뚜껑 ø30 (180~210), 합 20 g.
    시험 때만 바꾸고 장면 파일은 고치지 않는다."""
    spec = mujoco.MjSpec.from_file(scene)
    if bottle == "cap":
        b = spec.body("litter_bottle1"); g = b.first_geom()
        z0 = -0.105  # 병 바닥 (body 원점 = 병 가운데)
        g.size = [0.0325, 0.075, 0]; g.pos = [0, 0, z0 + 0.075]; g.mass = 0.016
        for r, a, bz, mm, rgba in ((0.024, 0.150, 0.170, 0.002, [0, .6, 1, 1]), (0.018, 0.170, 0.180, 0.001, [0, .6, 1, 1]),
                                   (0.015, 0.180, 0.210, 0.001, [1, 1, 1, 1])):
            b.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[r, (bz - a) / 2, 0], pos=[0, 0, z0 + (a + bz) / 2], mass=mm, rgba=rgba)
    b = spec.body("litter_bottle1"); b.pos = [b.pos[0] + shift[0], b.pos[1] + shift[1], b.pos[2]]
    m = spec.compile()
    if friction is not None:   # 집게 두 면(고정 손가락·움직이는 집게) 마찰만 바꿔 본다
        for g in range(m.ngeom):
            if m.geom(g).name == "arm_fixed_finger" or m.body(m.geom_bodyid[g]).name == "arm_moving_jaw_so101_v1":
                m.geom_friction[g][0] = friction
    return m


BEST = dict(plan=dict(gp=(0.0, 0.0, 0.034), tilt=30, zg=0.12),      # 기획안 원기둥: 시도한 것 중 덜 나쁜 설정
            cap=dict(gp=(-0.02, 0.0, 0.016), tilt=15, zg=0.195))    # 뚜껑 모양: 목·뚜껑을 손끝 쪽으로 집기


def pick(gp=None, tilt=None, bottle="plan", zg=None, shift=(0.0, 0.0), friction=None, quiet=False,
         scene="scenes/gym_v1.xml", zone="basket_zone", x_g=0.40, stow=None, smooth_arc=False,
         seed=0, yaw_off=0.0, roll_pref=None):
    """zg = 집는 높이(바닥에서, m). 병 바닥 높이 = zg - (병 바닥에서 집는 점까지).
    smooth_arc=True 면 호 경유점 IK 를 바로 앞 관절값에서만 시작한다(손목 돌림이 π 뒤집혀 병을 던지는 것 막기 —
    robot_v2 wide_side 에서 본 실패, v1 기본값은 그대로).
    roll_pref(rad) 를 주면 첫 IK(병 위 자세) 해 가운데 손목 돌림이 그 값에 가장 가까운 가지를 고른다 — wide_side 에서
    +1.62 가지(집게 π 뒤집힘)가 나오면 옮기는 호 후반에 병이 집게에서 빠졌다(logs/2026-11-24_pick_robust.md). 기본 None = 예전 그대로.
    seed = IK 무작위 시작점 시드, yaw_off = 다가간 차체 방향 어긋남(rad, 시험용).
    scene·zone·x_g·stow 는 다른 차체(예: robot_v2 wide_side, 통 site bin_zone)에 같은 방식을 쓸 때만 바꾼다."""
    stow = STOW if stow is None else np.asarray(stow)
    gp = BEST[bottle]["gp"] if gp is None else gp
    tilt = BEST[bottle]["tilt"] if tilt is None else tilt
    zg = BEST[bottle]["zg"] if zg is None else zg
    GP_NOW[0] = tuple(gp)
    say = (lambda *a_, **k_: None) if quiet else print
    import warnings; warnings.filterwarnings("ignore")
    m = load_gym(bottle, shift, friction, scene); d = mujoco.MjData(m); I = ids(m)
    bottle = m.body("litter_bottle1").id
    start = m.body("robot").pos.copy()  # attach frame 위치는 body pos 에 들어 있다
    d.qpos[I["qadr"]] = stow; d.ctrl[I["act"]] = stow
    mujoco.mj_forward(m, d)
    for _ in range(250): mujoco.mj_step(m, d)   # 0.5 s 안정화
    bpos = d.xpos[bottle].copy()
    out = {}

    # (a) 다가가기: 병이 차체 기준 앞 x_g 에 오게. 로봇은 +y(벤치 쪽)를 보게(yaw 90°) — 바구니가 벤치와 부딪히지 않게.
    yaw_goal = np.pi / 2 + yaw_off   # yaw_off: 병 쪽으로 다가간 차체 방향이 어긋난 경우 시험용 (기본 0)
    goal = np.array([bpos[0] - x_g * np.cos(yaw_goal), bpos[1] - x_g * np.sin(yaw_goal)])
    V_APPROACH = 0.3  # 다가가기 속도 상한 m/s (가정: 사람 옆 운행 속도, 최고 속도 아님)
    t0 = d.time
    while d.time - t0 < 15:
        x, y, yaw = (d.qpos[a] for a in I["base_q"])
        wx, wy = start[0] + x, start[1] + y
        e = goal - [wx, wy]; ey = (yaw_goal - yaw + np.pi) % (2 * np.pi) - np.pi
        if np.linalg.norm(e) < 0.005 and abs(ey) < 0.01:
            break
        v = 2.0 * e
        if np.linalg.norm(v) > V_APPROACH: v *= V_APPROACH / np.linalg.norm(v)
        c, s = np.cos(-yaw), np.sin(-yaw)
        drive(m, d, I, c * v[0] - s * v[1], s * v[0] + c * v[1], np.clip(2.0 * ey, -1.0, 1.0))
        mujoco.mj_step(m, d)
    for _ in range(100): drive(m, d, I, 0, 0, 0); mujoco.mj_step(m, d)
    if DEBUG: print("   다가간 뒤 병", np.round(d.xpos[bottle], 3))
    out["t_drive"] = d.time - t0
    dist = np.linalg.norm(goal - start[:2])
    say(f"다가가기: {dist:.2f} m 를 {out['t_drive']:.1f} s (상한 {V_APPROACH} m/s)")

    # (b) 팔 계획. SO-101은 관절이 5개라 손가락을 '수평 + 집게 수평 닫힘'으로 바닥 10 cm 높이에 둘 수 없다
    #     (어깨·손목 관절 한계 — 측정 기록 참고). 그래서 손가락을 아래로 TILT 만큼 숙이고, 집게 닫는 축(z)만 수평으로 둔다.
    #     집는 점 = gripperframe 좌표 (0, 0, +0.034): 손끝 높이, 고정 손가락 면에서 병 반지름만큼 위.
    #     병(ø65)이 이 집게에는 큰 편이라, 손가락 안쪽 깊이 넣으면 벌린 집게·손바닥과 겹친다(측정 기록의 '틈' 표).
    #     그래서 손끝 쪽으로 집고, 병 위에서 수직으로 내려와 끼운다.
    bpos = d.xpos[bottle].copy()
    ez = np.array([0, 0, 1.0])
    dots = [("x", ez, -np.sin(np.radians(tilt))), ("z", ez, 0.0)]
    GP = tuple(gp)
    pan_axis = d.xanchor[m.joint(P + "shoulder_pan").id].copy()
    u = bpos[:2] - pan_axis[:2]; u = np.r_[u / np.linalg.norm(u), 0]
    grasp = np.array([bpos[0], bpos[1], zg])
    pre = grasp + np.array([0, 0, 0.14])     # 병 위에서 내려온다
    rng = np.random.default_rng(seed)
    lo = m.jnt_range[[m.joint(P + n).id for n in ARM], 0]; hi = m.jnt_range[[m.joint(P + n).id for n in ARM], 1]

    def solve(t, seeds):
        return min((ik(m, d, I, t, q0=s, iters=400, dots=dots, offset=GP) for s in seeds), key=lambda r: r[1])

    rand = [rng.uniform(lo, hi) for _ in range(30)]
    if roll_pref is None:
        q_pre, e1 = solve(pre, rand)
    else:   # 손목 돌림(wrist_roll) 가지를 고정: IK 해 가운데 오차 2 mm 안인 것 중 roll_pref 에 가장 가까운 것
        sols = [ik(m, d, I, pre, q0=s, iters=400, dots=dots, offset=GP) for s in rand + [np.r_[0, -0.5, 0.6, 0.2, roll_pref]]]
        good = [r for r in sols if r[1] < 0.002] or [min(sols, key=lambda r: r[1])]
        q_pre, e1 = min(good, key=lambda r: abs(r[0][4] - roll_pref))

    def line(a, b, q0, n=10):   # a→b 직선 위 경유점의 관절값
        qs, q, err = [], q0, 0.0
        for k in range(1, n + 1):
            q, e = solve(a + (b - a) * k / n, [q]); qs.append(q); err = max(err, e)
        return qs, err

    down_qs, e2 = line(pre, grasp, q_pre)
    q_grasp = down_qs[-1]
    up_qs, e3 = line(grasp, grasp + np.array([0, 0, 0.20]), q_grasp)
    q_lift = up_qs[-1]
    bz = d.site_xpos[m.site(zone).id].copy()
    rim = bz[2] + m.site_size[m.site(zone).id][2]
    over = np.array([bz[0], bz[1], rim + 0.03 + zg])   # 병 바닥이 바구니 테두리 위 3 cm
    # 옮기기: 팔 축(pan) 둘레로 같은 높이의 호를 따라 (관절 직선 보간이면 병이 차체·바구니에 부딪힘)
    lift_pt = grasp + np.array([0, 0, 0.20])
    zc = max(lift_pt[2], over[2])
    r0 = lift_pt[:2] - pan_axis[:2]; r1 = over[:2] - pan_axis[:2]
    a0, a1 = np.arctan2(r0[1], r0[0]), np.arctan2(r1[1], r1[0])
    da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
    arc_qs, q, e4 = [], q_lift, 0.0
    for k in range(1, 13):
        f_ = k / 12; ang = a0 + da * f_; rad = np.linalg.norm(r0) + (np.linalg.norm(r1) - np.linalg.norm(r0)) * f_
        pt = np.r_[pan_axis[:2] + rad * np.array([np.cos(ang), np.sin(ang)]), zc]
        q, e = solve(pt, [q] if smooth_arc else [q] + rand[:5]); arc_qs.append(q); e4 = max(e4, e)
    q_over, e = solve(over, [q]); arc_qs.append(q_over); e4 = max(e4, e)
    # 내려놓기: 병 바닥이 테두리 아래 DROP_IN 까지 들어가게 수직으로 내린 뒤 벌린다
    drop_qs, e5 = line(over, over - np.array([0, 0, 0.03 + DROP_IN]), q_over, n=6)
    q_drop = drop_qs[-1]
    errs = dict(pre=e1, grasp=e2, lift=e3, over=e4, drop=e5)
    say("IK 오차(m, 자세 오차 포함):", {k: round(float(v), 4) for k, v in errs.items()}, "기울기", tilt, "°, 집는 점", GP)
    out["ik_err"] = errs
    out["q_roll"] = float(q_pre[4])

    # (c) 실행
    q_home = np.array([d.qpos[a] for a in I["qadr"]])
    d.ctrl[I["act"]] = q_home
    seg = []
    tau = {"max": 0.0}
    sl = m.actuator(P + "shoulder_lift").id

    tau["seg"] = {}

    def rec(dd):
        tau["max"] = max(tau["max"], abs(dd.actuator_force[sl]))
        k = len(seg)
        tau["seg"][k] = max(tau["seg"].get(k, 0.0), abs(dd.actuator_force[sl]))
        tau.setdefault("end", {})[k] = abs(dd.actuator_force[sl])   # 구간 끝(멈춘 뒤) 값으로 덮어씀

    t_arm0 = d.time
    move(m, d, I, q_pre, OPEN, seg, rec=rec)
    move_path(m, d, I, down_qs, OPEN, seg, rec=rec)
    move(m, d, I, q_grasp, CLOSE, seg, extra=0.6, rec=rec)
    move_path(m, d, I, up_qs, CLOSE, seg, rec=rec)
    held = d.xpos[bottle][2] > bpos[2] + 0.10
    say(f"들어 올림: 병 높이 {d.xpos[bottle][2]:.3f} m (처음 {bpos[2]:.3f}) → {'잡힘' if held else '놓침'}")
    move_path(m, d, I, arc_qs, CLOSE, seg, rec=rec)
    move(m, d, I, q_over, CLOSE, seg, extra=0.5, rec=rec)          # 흔들림 멈추기
    move_path(m, d, I, drop_qs, CLOSE, seg, rec=rec)
    move(m, d, I, q_drop, OPEN, seg, extra=0.5, rec=rec)
    move(m, d, I, q_over, OPEN, seg, rec=rec)
    t_arm = d.time - t_arm0
    move(m, d, I, q_home, OPEN, seg, rec=rec)
    for _ in range(500): drive(m, d, I, 0, 0, 0); mujoco.mj_step(m, d)
    # 판정: 병 무게중심이 바구니 안쪽 바닥 넓이 안(x·y)이고, 병이 서 있으면 무게중심이 테두리 + 6 cm 아래
    #       (병 21 cm > 바구니 깊이 10 cm 라 서 있는 병의 무게중심은 테두리보다 조금 높다), 집게는 벌린 채 떠나 있음
    sid = m.site(zone).id
    R = d.site_xmat[sid].reshape(3, 3); rel = R.T @ (d.xpos[bottle] - d.site_xpos[sid])
    hs = m.site_size[sid]
    up = d.xmat[bottle].reshape(3, 3)[:, 2] @ np.array([0, 0, 1.0])
    inside = bool(abs(rel[0]) <= hs[0] and abs(rel[1]) <= hs[1]
                  and ((up > 0.7 and rel[2] <= hs[2] + 0.06) or rel[2] <= hs[2] - 0.0325))   # 서 있거나, 누워도 테두리 아래
    drift = np.linalg.norm(d.qpos[I["base_q"][:2]] - (goal - start[:2]))
    out.update(upright=float(up), held=held, inside=inside, t_arm=t_arm, segs=seg, tau_sl=tau["max"], drift=drift,
               bottle_rel=rel, bottle_z=d.xpos[bottle][2])
    say(f"팔 동작(집기 시작 → 바구니에 놓고 손 뺄 때까지): {t_arm:.1f} s, 구간 {np.round(seg, 2).tolist()}")
    say(f"결과: {'성공' if inside else '실패'} — 병 위치(바구니 기준) {np.round(rel, 3)}, 병 z {d.xpos[bottle][2]:.3f}, 병 축 cos {up:.2f} (1 = 서 있음)")
    say("   구간별 어깨 힘 최대 N·m:", {k: round(float(v), 2) for k, v in tau["seg"].items()})
    say("   구간 끝(멈춘 뒤) 어깨 힘 N·m:", {k: round(float(v), 2) for k, v in tau["end"].items()})
    out["tau_hold"] = max(tau["end"].values())
    say(f"pick 중 어깨(shoulder_lift) 액추에이터 힘 최대 {tau['max']:.3f} N·m, 차체 밀림 {drift * 1000:.1f} mm")
    out["t_total"] = out["t_drive"] + t_arm
    return out


def gap():
    """기획안 원기둥 병(ø65)을 손가락 사이에 둔 자세에서, 집게 벌림 각도별 '집게·손바닥과 병 사이 최소 틈'(mm, 음수 = 겹침)."""
    import warnings; warnings.filterwarnings("ignore")
    m = load_gym("plan"); d = mujoco.MjData(m); I = ids(m)
    d.qpos[I["base_q"]] = [0.7, 0.2, np.pi / 2]; mujoco.mj_forward(m, d)
    b = m.body("litter_bottle1").id; bg = [g for g in range(m.ngeom) if m.geom_bodyid[g] == b][0]
    armg = [g for g in range(m.ngeom) if m.body(m.geom_bodyid[g]).name.startswith(P) and m.geom_contype[g]]
    ez = np.array([0, 0, 1.0]); rng = np.random.default_rng(1)
    lo = m.jnt_range[[m.joint(P + n).id for n in ARM], 0]; hi = m.jnt_range[[m.joint(P + n).id for n in ARM], 1]
    bpos = d.xpos[b].copy(); phis = [0.3, 0.5, 0.7, 0.9, 1.2]
    print("기울기°  집는점x  " + "  ".join(f"벌림{p_}" for p_ in phis))
    for tilt in (0, 30, 60):
        for xc in (0.0, -0.01, -0.02, -0.03):
            dots = [("x", ez, -np.sin(np.radians(tilt))), ("z", ez, 0.0)]
            q, e = min((ik(m, d, I, np.array([bpos[0], bpos[1], 0.12]), q0=rng.uniform(lo, hi), iters=300, dots=dots,
                           offset=(xc, 0, 0.034)) for _ in range(15)), key=lambda r: r[1])
            if e > 0.003:
                print(f"{tilt:5d}  {xc:6.2f}   IK 못 맞춤 ({e:.3f})"); continue
            d.qpos[I["qadr"]] = q; row = []
            for phi in phis:
                d.qpos[I["grip_q"]] = phi; mujoco.mj_forward(m, d)
                row.append(min(mujoco.mj_geomDistance(m, d, g, bg, 0.2, np.zeros(6)) for g in armg) * 1000)
            print(f"{tilt:5d}  {xc:6.2f}   " + "  ".join(f"{v:7.1f}" for v in row))


def pick_trials():
    """두 병 모양 × 병 위치 9곳(±2 cm 격자) + 집게 마찰 0.5 한 번. 성공 수와 평균 시간."""
    res = {}
    for bottle in ("plan", "cap"):
        print(f"--- 병 모양 {bottle}: 자세히 1회")
        one = pick(bottle=bottle)
        ok, times = 0, []
        for dx in (-0.02, 0.0, 0.02):
            for dy in (-0.02, 0.0, 0.02):
                r = pick(bottle=bottle, shift=(dx, dy), quiet=True)
                ok += r["inside"]; times.append(r["t_arm"])
        f05 = pick(bottle=bottle, friction=0.5, quiet=True)
        res[bottle] = dict(one=one, ok=ok, n=9, t_mean=float(np.mean(times)), f05=f05["inside"])
        print(f"--- {bottle}: 위치 9곳 중 성공 {ok}, 팔 동작 평균 {np.mean(times):.1f} s, 집게 마찰 0.5 일 때 {'성공' if f05['inside'] else '실패'}")
    return res


# ---------------------------------------------------------------- 4. torque + stability
def torque():
    m = mujoco.MjModel.from_xml_path("scenes/robot_v1.xml"); d = mujoco.MjData(m); I = ids(m)
    # 수평으로 쭉 편 자세 찾기: 손끝을 어깨 lift 축 높이에서 앞으로 최대한 멀리
    mujoco.mj_forward(m, d)
    a = d.xanchor[m.joint(P + "shoulder_lift").id].copy()
    best = None
    for L in np.arange(0.45, 0.25, -0.002):
        q, e = ik(m, d, I, a + [L, 0.018, 0], q0=np.array([0, 1.5, 0, 0, 0]), iters=400)
        if e < 1e-3:
            best = (L, q); break
    L, q = best
    d.qpos[I["qadr"]] = q; mujoco.mj_forward(m, d)
    jid = m.joint(P + "shoulder_lift").id
    b0 = m.jnt_bodyid[jid]
    tau = 0.0
    rows = []
    for b in range(b0, m.nbody):
        if not m.body(b).name.startswith(P):
            continue
        r = abs(d.xipos[b][0] - d.xanchor[jid][0])
        tau += m.body_mass[b] * G * r
        rows.append((m.body(b).name, m.body_mass[b], r))
    rt = abs(d.site_xpos[I["tip"]][0] - d.xanchor[jid][0])
    print(f"수평 쭉 편 자세: 손끝까지 {rt:.3f} m, 관절 {np.round(q, 2).tolist()}")
    for n, mm, r in rows:
        print(f"   {n:28s} m={mm:.3f} kg r={r:.3f} m  m·g·r={mm * G * r:.4f} N·m")
    print(f"   제 무게 토크 {tau:.3f} N·m = {tau / KGCM:.1f} kg·cm")
    specs = [("STS3215 7.4V 정지 토크 19.5 kg·cm (28차시 코드 값)", 19.5 * KGCM),
             ("STS3215 12V 정지 토크 30 kg·cm (판매처 표기, 확인 필요)", 30 * KGCM),
             ("모델 forcerange 3.35 N·m (SO101 MJCF)", 3.35)]
    out = dict(reach=rt, self=tau, rows=rows, specs=[])
    for name, T in specs:
        extra = (T - tau) / (G * rt)
        out["specs"].append((name, T, extra))
        print(f"   {name}: {T:.2f} N·m → 손끝에 더 들 수 있는 무게 {extra * 1000:.0f} g (빈 병 20 g, 물 남은 병 기준 100 g)")
    # 넘어짐 여유: 로봇 전체 무게중심 vs 바퀴 접지 사각형
    wx = abs(m.geom_pos[m.geom("wheel_fl").id][0]); wy = abs(m.geom_pos[m.geom("wheel_fl").id][1])
    stab = []
    for lab, qq, extra_m in (("팔 수평으로 앞 최대 + 물 남은 병 0.1 kg", q, 0.1),
                             ("팔 수평 옆(pan +90°) 최대 + 0.1 kg", np.r_[1.57, q[1:]], 0.1),
                             ("팔 수평 옆(pan -90°) 최대 + 0.1 kg", np.r_[-1.57, q[1:]], 0.1)):
        d.qpos[I["qadr"]] = qq; mujoco.mj_forward(m, d)
        if abs(d.site_xpos[I["tip"]][1]) > 0.05:
            lab += " → 손끝 " + ("왼쪽" if d.site_xpos[I["tip"]][1] > 0 else "오른쪽")
        rb = m.body("robot").id
        M = d.subtree_com[rb] * m.body_subtreemass[rb] + d.site_xpos[I["tip"]] * extra_m
        com = M / (m.body_subtreemass[rb] + extra_m)
        margin = min(wx - abs(com[0]), wy - abs(com[1]))
        stab.append((lab, com, margin))
        print(f"   넘어짐 여유 [{lab}]: 무게중심 ({com[0]:.3f}, {com[1]:.3f}) m, 바퀴 사각형 ±{wx}·±{wy} 까지 여유 {margin * 1000:.0f} mm")
    # 차체가 가벼우면? 같은 팔·자세에서 차체 질량을 바꿔 여유가 0 이 되는 질량
    arm_m = sum(m.body_mass[b] for b in range(m.nbody) if m.body(b).name.startswith(P))
    d.qpos[I["qadr"]] = np.r_[1.57, q[1:]]; mujoco.mj_forward(m, d)
    arm_mom = abs(sum(m.body_mass[b] * d.xipos[b][1] for b in range(m.nbody) if m.body(b).name.startswith(P)) + 0.1 * d.site_xpos[I["tip"]][1])
    # 손끝 최고 높이 (팔 관절 격자 탐색, 창문틀 1.0 m 비교용)
    zmax = 0.0
    for a_ in np.linspace(-1.75, 1.75, 36):
        for b_ in np.linspace(-1.69, 1.69, 36):
            for c_ in np.linspace(-1.66, 1.66, 24):
                d.qpos[I["qadr"]] = [0, a_, b_, c_, 0]; mujoco.mj_kinematics(m, d)
                zmax = max(zmax, d.site_xpos[I["tip"]][2])
    print(f"   손끝 최고 높이(바닥 기준) {zmax:.2f} m")
    out.update(zmax=zmax, stab=stab, arm_mass=arm_m, min_mass_side=(arm_mom / wy) - arm_m - 0.1)
    print(f"   팔 질량 {arm_m:.3f} kg. 팔을 옆으로 쭉 펴고 0.1 kg 들 때, 넘어지지 않으려면 팔·병 외 질량(차체 가운데에 있다고 가정) ≥ {out['min_mass_side']:.2f} kg")
    return out


if __name__ == "__main__":
    what = [a for a in sys.argv[1:] if a != "-v"] or ["speed", "reach", "gap", "pick_trials", "torque"]
    t = time.time()
    for w in what:
        print(f"===== {w}")
        globals()[w]()
    print(f"(실행 {time.time() - t:.0f} s, MuJoCo {mujoco.__version__})")
