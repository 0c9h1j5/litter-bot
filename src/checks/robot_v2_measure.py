"""robot_v2 (주인 설계 배치) 실측 — logs/2026-11-24_robot_v2_measurements.md

    uv run python scripts/build_robot_v2.py
    uv run python src/checks/robot_v2_measure.py                 # 두 차체(x3, wide) 모두, 모든 항목
    uv run python src/checks/robot_v2_measure.py x3 pick -v      # 한 차체, 한 항목(pick = 한 번 자세히)

항목
  speed   : 직진·제자리 회전 (robot_v1 과 같은 방식)
  stow    : 크래들 접기 자세(허리 ±90°) — 팔 최고 높이가 가장 낮고 몸·통과 충돌 없는 자세 찾기, 차체 옆으로 나온 길이
  reach   : 바닥(손끝 z 1 cm) 앞으로 닿는 범위
  trials  : 뚜껑 모양 병(가정)의 목·뚜껑을 잡아 묻힌 통에 넣기 — 병 위치 ±2 cm 9곳, 성공 수·시간 + 집게 마찰 0.5 한 번
  tip     : 넘어짐 여유 (무게중심이 바퀴 접지 사각형 안인가) — 팔 수평 앞·옆 최대 + 통 위로 병을 넘기는 자세
"""
import sys
import time
import warnings

import mujoco
import numpy as np

sys.path.insert(0, "src/checks")
sys.path.insert(0, "scripts")
import mecanum_so101_measure as v1  # noqa: E402
from build_robot_v2 import FILE_NAMES, STOW_V2, VARIANTS, layout, wmax  # noqa: E402
from robot_v1_util import ARM, P, drive, ids, ik  # noqa: E402

warnings.filterwarnings("ignore")
DEBUG = "-v" in sys.argv
v1.DEBUG = DEBUG
OPEN, CLOSE = v1.OPEN, v1.CLOSE
FILES = {k: (f"scenes/{r}.xml", f"scenes/{g}.xml") for k, (r, g) in FILE_NAMES.items()}
CAP = dict(gp=(-0.02, 0.0, 0.016), tilt=15, zg=0.195)   # v1 에서 8/9 성공한 '목·뚜껑 손끝 쪽으로 집기' 설정 그대로
DROP_IN = 0.05            # 병 바닥을 통 테두리 아래로 넣는 깊이 m (v1 과 같음)
CLEAR = 0.03              # 통 위로 지날 때 병 바닥과 테두리 사이 m (v1 과 같음)
DZS = (-0.05, -0.03, 0.0, 0.03, 0.06, 0.10)          # 병 바닥 높이 후보 (테두리 기준 m)
COSS = (1.0, 0.97, 0.94, 0.9, 0.85, 0.8, 0.75)       # 병 축 기울기 후보 (수직과의 cos)
CACHE = {}


def own_geoms(m):
    rb, bb = m.body("robot").id, m.body("bin").id
    own = {g for g in range(m.ngeom) if m.geom_bodyid[g] in (rb, bb) and m.geom_contype[g]}
    arm = {g for g in range(m.ngeom) if m.body(m.geom_bodyid[g]).name.startswith(P) and m.geom_contype[g]}
    return own, arm


def collide(m, d, own, arm, tol=0.001):
    for c in d.contact[:d.ncon]:
        pair = {c.geom1, c.geom2}
        if pair & arm and pair & own and c.dist < -tol:
            return True
    return False


# ------------------------------------------------------------------ speed
def speed(name):
    v = VARIANTS[name]
    print(f"직진 최고 {v['vmax']} m/s (명령값 = robot_v1 실측과 같은 방식 — 시뮬은 명령을 그대로 따라감), "
          f"제자리 회전 상한 {wmax(v)} rad/s = {np.degrees(wmax(v)):.0f} °/s (운동학, 가정)")
    return dict(vmax=v["vmax"], wmax=wmax(v))


# ------------------------------------------------------------------ stow
def arm_extent(m, d):
    """팔 몸체 충돌 형상의 x·y·z 범위 (메시는 꼭짓점, 그 밖은 rbound 구로 근사)."""
    P3 = []
    for g in range(m.ngeom):
        if m.body(m.geom_bodyid[g]).name.startswith(P) and m.geom_contype[g]:
            c = d.geom_xpos[g]; r = m.geom_rbound[g]
            if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
                mid = m.geom_dataid[g]; a, n = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
                P3.append(m.mesh_vert[a:a + n] @ d.geom_xmat[g].reshape(3, 3).T + c)
            else:
                P3.append(np.array([c - r, c + r]))
    A = np.vstack(P3)
    return A.min(0), A.max(0)


STOW_LIMITS = (0.0, 0.03, 0.06, 1.0)   # 몸통 옆면(위 몸통 반폭) 밖으로 나와도 되는 길이 m — 한도별로 가장 낮은 자세


def stow(name):
    """허리 ±90°에서 어깨·팔꿈치·손목 격자 탐색. 몸·통과 충돌 없고 팔이 차체 앞뒤 길이 안에 있는 자세 중,
    옆으로 나온 길이 한도별 '팔 최고 높이'가 가장 낮은 자세."""
    m = mujoco.MjModel.from_xml_path(FILES[name][0]); d = mujoco.MjData(m); I = ids(m)
    own, arm = own_geoms(m)
    v = VARIANTS[name]; lay = layout(v)
    hw, L = lay["up_w"] / 2, lay["L"]
    best = {k: None for k in STOW_LIMITS}
    for pan in (-np.pi / 2, np.pi / 2):
        for a in np.linspace(-1.74, 1.74, 30):
            for b in np.linspace(-1.69, 1.69, 30):
                for c in np.linspace(-1.65, 1.65, 23):
                    d.qpos[I["qadr"]] = [pan, a, b, c, 0]; mujoco.mj_forward(m, d)
                    lo, hi = arm_extent(m, d)
                    if lo[0] < -L / 2 or hi[0] > L / 2 + 0.02 or lo[2] < v["deck_z"] - 0.005:
                        continue
                    over = max(-lo[1] - hw, hi[1] - hw, 0.0)
                    z = hi[2]
                    for k in STOW_LIMITS:
                        if over <= k + 1e-9 and (best[k] is None or z < best[k][0] - 1e-4):
                            if collide(m, d, own, arm, tol=0.0005):
                                break
                            best[k] = (z, [round(float(x), 3) for x in (pan, a, b, c, 0)], over)
    out = {}
    for k, r in best.items():
        if r is None:
            print(f"옆 한도 {k * 1000:.0f} mm: 자세 없음"); continue
        z, q, over = r
        out[k] = r
        print(f"옆 한도 {k * 1000:.0f} mm: 관절 {q}, 팔 최고 높이 {z:.3f} m (윗면 위 {z - v['deck_z']:.3f} m), 옆으로 나옴 {over * 1000:.0f} mm")
    d.qpos[I["qadr"]] = STOW_V2; mujoco.mj_forward(m, d)
    lo, hi = arm_extent(m, d)
    over = max(-lo[1] - hw, hi[1] - hw, 0.0)
    print(f"   모델의 STOW_V2 {STOW_V2}: 최고 {hi[2]:.3f} m, 옆으로 나옴 {over * 1000:.0f} mm, x {lo[0]:.3f}~{hi[0]:.3f}, "
          f"충돌 {'있음' if collide(m, d, own, arm) else '없음'}")
    out["stow_v2"] = (hi[2], over)
    return out


# ------------------------------------------------------------------ reach
def reach(name):
    m = mujoco.MjModel.from_xml_path(FILES[name][0]); d = mujoco.MjData(m); mujoco.mj_forward(m, d); I = ids(m)
    own, arm = own_geoms(m); floor = m.geom("floor").id
    DOWN = ("x", np.array([0, 0, -1.0]))
    ok = [x for x in np.arange(0.10, 0.70, 0.01)
          if v1.reach_ok(m, d, I, own, arm, floor, np.array([x, 0, 0.01]))[0]
          or v1.reach_ok(m, d, I, own, arm, floor, np.array([x, 0, 0.01]), DOWN)[0]]
    L = VARIANTS[name]["length"]
    lo, hi = (round(float(min(ok)), 2), round(float(max(ok)), 2)) if ok else (None, None)
    print(f"바닥(손끝 z 1 cm) 앞: 차체 가운데에서 {lo} ~ {hi} m (앞면 {L / 2:.3f} m → 앞면에서 {lo - L / 2:.2f} ~ {hi - L / 2:.2f} m)")
    return dict(lo=lo, hi=hi, front=L / 2)


# ------------------------------------------------------------------ pick into the buried bin
def load_gym(name, shift=(0.0, 0.0), friction=None):
    spec = mujoco.MjSpec.from_file(FILES[name][1])
    b = spec.body("litter_bottle1"); g = b.first_geom()   # 뚜껑 모양 병 (가정) — v1 load_gym("cap") 과 같은 치수
    z0 = -0.105
    g.size = [0.0325, 0.075, 0]; g.pos = [0, 0, z0 + 0.075]; g.mass = 0.016
    for r, a, bz, mm, rgba in ((0.024, 0.150, 0.170, 0.002, [0, .6, 1, 1]), (0.018, 0.170, 0.180, 0.001, [0, .6, 1, 1]),
                               (0.015, 0.180, 0.210, 0.001, [1, 1, 1, 1])):
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[r, (bz - a) / 2, 0], pos=[0, 0, z0 + (a + bz) / 2], mass=mm, rgba=rgba)
    b.pos = [b.pos[0] + shift[0], b.pos[1] + shift[1], b.pos[2]]
    m = spec.compile()
    if friction is not None:
        for g in range(m.ngeom):
            if m.geom(g).name == "arm_fixed_finger" or m.body(m.geom_bodyid[g]).name == "arm_moving_jaw_so101_v1":
                m.geom_friction[g][0] = friction
    return m


def pick(name="x3", shift=(0.0, 0.0), friction=None, quiet=False, want_q=False, release="low"):
    say = (lambda *a, **k: None) if quiet else print
    v1.GP_NOW[0] = CAP["gp"]
    m = load_gym(name, shift, friction); d = mujoco.MjData(m); I = ids(m)
    bottle = m.body("litter_bottle1").id
    start = m.body("robot").pos.copy()
    d.qpos[I["qadr"]] = STOW_V2; d.ctrl[I["act"]] = STOW_V2
    mujoco.mj_forward(m, d)
    for _ in range(250): mujoco.mj_step(m, d)
    bpos = d.xpos[bottle].copy()
    out = {}

    # (a) 다가가기 (v1 과 같음): 로봇은 +y(벤치 쪽)를 봄. 병이 어깨 회전축 앞 0.291 m 에 오게 (v1 과 같은 팔 거리)
    lay = layout(VARIANTS[name])
    x_g = lay["pivot"][0] + (0.40 - 0.1088)
    yaw_goal = np.pi / 2
    goal = np.array([bpos[0] - x_g * np.cos(yaw_goal), bpos[1] - x_g * np.sin(yaw_goal)])
    V_APPROACH = 0.3
    t0 = d.time
    while d.time - t0 < 15:
        x, y, yaw = (d.qpos[a] for a in I["base_q"])
        e = goal - [start[0] + x, start[1] + y]; ey = (yaw_goal - yaw + np.pi) % (2 * np.pi) - np.pi
        if np.linalg.norm(e) < 0.005 and abs(ey) < 0.01:
            break
        vv = 2.0 * e
        if np.linalg.norm(vv) > V_APPROACH: vv *= V_APPROACH / np.linalg.norm(vv)
        c, s = np.cos(-yaw), np.sin(-yaw)
        drive(m, d, I, c * vv[0] - s * vv[1], s * vv[0] + c * vv[1], np.clip(2.0 * ey, -1.0, 1.0))
        mujoco.mj_step(m, d)
    for _ in range(100): drive(m, d, I, 0, 0, 0); mujoco.mj_step(m, d)
    out["t_drive"] = d.time - t0
    out["dist"] = float(np.linalg.norm(goal - start[:2]))

    # (b) 계획
    bpos = d.xpos[bottle].copy()
    ez = np.array([0, 0, 1.0])
    dots = [("x", ez, -np.sin(np.radians(CAP["tilt"]))), ("z", ez, 0.0)]
    GP = CAP["gp"]; zg = CAP["zg"]
    pan_axis = d.xanchor[m.joint(P + "shoulder_pan").id].copy()
    grasp = np.array([bpos[0], bpos[1], zg])
    pre = grasp + np.array([0, 0, 0.14])
    rng = np.random.default_rng(0)
    lo = m.jnt_range[[m.joint(P + n).id for n in ARM], 0]; hi = m.jnt_range[[m.joint(P + n).id for n in ARM], 1]
    rand = [rng.uniform(lo, hi) for _ in range(30)]

    def solve(t, seeds):
        return min((ik(m, d, I, t, q0=s, iters=400, dots=dots, offset=GP) for s in seeds), key=lambda r: r[1])

    def line(a, b, q0, n=10):
        qs, q, err = [], q0, 0.0
        for k in range(1, n + 1):
            q, e = solve(a + (b - a) * k / n, [q]); qs.append(q); err = max(err, e)
        return qs, err

    q_pre, e1 = solve(pre, rand)
    down_qs, e2 = line(pre, grasp, q_pre)
    q_grasp = down_qs[-1]
    lift_pt = grasp + np.array([0, 0, 0.20])
    up_qs, e3 = line(grasp, lift_pt, q_grasp)
    q_lift = up_qs[-1]
    sid = m.site("bin_zone").id
    bz = d.site_xpos[sid].copy(); rim = bz[2] + m.site_size[sid][2]
    # 옮기기: 병을 목에서 매단 채 '병이 수직'으로는 통 위에 못 온다(병 바닥을 테두리 위로 올리는 자세가 없음 — 측정 기록 3절).
    # 그래서 집게가 병을 단단히 쥐고 있다고 보고(집게와 병이 같이 돈다), 병 바닥 점과 병 축 기울기로 IK를 푼다:
    #   병 바닥 = 통 가운데, 테두리 위 CLEAR · 병 축과 수직의 cos = COS (병을 COS 만큼 기울여 넣음)
    mujoco.mj_kinematics(m, d)
    dg = mujoco.MjData(m); dg.qpos[:] = d.qpos; dg.qpos[I["qadr"]] = q_grasp; mujoco.mj_kinematics(m, dg)
    Rg = dg.site_xmat[I["tip"]].reshape(3, 3)
    from robot_v1_util import point
    g0 = point(dg, I, GP)
    bottom = np.array([bpos[0], bpos[1], bpos[2] - 0.105])
    BOT = np.asarray(GP) + Rg.T @ (bottom - g0)        # 병 바닥 (gripperframe 좌표)
    AX = Rg.T @ ez                                      # 병 축 (gripperframe 좌표)
    over_b = np.array([bz[0], bz[1], rim + CLEAR])

    def solve_b(t, seeds, cos_t):
        dd_ = [(AX, ez, cos_t)]
        return min((ik(m, d, I, t, q0=s_, iters=300, dots=dd_, offset=BOT) for s_ in seeds), key=lambda r_: r_[1])

    # 통 위 자세 고르기 (차체마다 한 번 계산해 CACHE 에 둠 — 통은 차체 기준 같은 자리라 관절값을 그대로 다시 쓴다):
    #   병 바닥 높이 dz(테두리 기준)와 병 기울기 cos 의 격자에서 IK 가 3 mm 안에 맞는 칸을 찾는다.
    #   '놓는 자세' = 가장 낮은 dz(같으면 가장 똑바른 병), '위 자세' = dz ≥ CLEAR 중 가장 똑바른 병.
    if name not in CACHE:
        rand2 = rand + [rng.uniform(lo, hi) for _ in range(90)]
        table = {}
        for dz in DZS:
            for COS in COSS:
                q_, e_ = solve_b(over_b + np.array([0, 0, dz - CLEAR]), rand2, COS)
                table[(dz, COS)] = (q_, e_)
        feas = [(dz, c_) for (dz, c_), (q_, e_) in table.items() if e_ < 0.003]
        say("   통 위 IK 표 (병 바닥 dz m, cos) 가능:", sorted(feas))
        # 놓는 자세: 같은 기울기로 테두리 위 CLEAR 자세도 되는 칸 중 가장 낮은 칸(같으면 가장 똑바른 병).
        # 위 자세 = 같은 기울기, 테두리 위 CLEAR → 그 사이는 병 기울기를 그대로 두고 수직으로 내린다.
        cand = [k for k in feas if k[0] < CLEAR and (CLEAR, k[1]) in feas]
        final = min(cand, key=lambda k: (k[0], -k[1])) if cand else (CLEAR, max(c_ for dz_, c_ in feas if dz_ == CLEAR))
        above = (CLEAR, final[1])
        CACHE[name] = dict(above=above, final=final, q_above=table[above][0], q_final=table[final][0],
                           table={k: round(float(v[1]), 4) for k, v in table.items()})
    C = CACHE[name]
    q_over, e4 = solve_b(over_b + np.array([0, 0, C["above"][0] - CLEAR]), [C["q_above"]], C["above"][1])
    q_drop, e5 = solve_b(over_b + np.array([0, 0, C["final"][0] - CLEAR]), [C["q_final"]], C["final"][1])
    out["above"], out["final"] = C["above"], C["final"]
    say(f"통 위 자세: 병 바닥 테두리 {C['above'][0]:+.2f} m, 기울기 {np.degrees(np.arccos(C['above'][1])):.0f}° → "
        f"놓는 자세: {C['final'][0]:+.2f} m, {np.degrees(np.arccos(C['final'][1])):.0f}°")
    # 경로: 들어 올린 자세 → 위 자세 (관절 직선 보간 10단계) → 놓는 자세 (관절 직선 보간 6단계)
    flip_qs = [q_lift + (q_over - q_lift) * k / 10 for k in range(1, 11)]
    drop_qs, q = [], q_over
    for k in range(1, 7):
        q, e = solve_b(over_b + np.array([0, 0, (C["final"][0] - CLEAR) * k / 6]), [q], C["final"][1]); drop_qs.append(q); e5 = max(e5, e)
    q_drop = drop_qs[-1]
    errs = dict(pre=e1, grasp=e2, lift=e3, carry=e4, drop=e5)
    say("IK 오차(m, 자세 포함):", {k: round(float(x), 4) for k, x in errs.items()})
    out["ik_err"] = errs

    # (c) 실행
    q_home = np.array([d.qpos[a] for a in I["qadr"]])
    d.ctrl[I["act"]] = q_home
    seg = []
    sl = m.actuator(P + "shoulder_lift").id
    tau = {"max": 0.0}
    rb = m.body("robot").id
    wx = VARIANTS[name]["wheel_x"]; wy = VARIANTS[name]["wheel_y"]
    stab = {"min": 1.0}

    def rec(dd):
        tau["max"] = max(tau["max"], abs(dd.actuator_force[sl]))
        # 넘어짐 여유(차체 기준 무게중심, 병 포함)
        M = dd.subtree_com[rb] * m.body_subtreemass[rb] + dd.xipos[bottle] * m.body_mass[bottle]
        com = M / (m.body_subtreemass[rb] + m.body_mass[bottle])
        cb = dd.xmat[rb].reshape(3, 3).T @ (com - dd.xpos[rb])
        stab["min"] = min(stab["min"], wx - abs(cb[0]), wy - abs(cb[1]))

    t_arm0 = d.time
    v1.move(m, d, I, q_pre, OPEN, seg, rec=rec)
    v1.move_path(m, d, I, down_qs, OPEN, seg, rec=rec)
    v1.move(m, d, I, q_grasp, CLOSE, seg, extra=0.6, rec=rec)
    v1.move_path(m, d, I, up_qs, CLOSE, seg, rec=rec)
    held = d.xpos[bottle][2] > bpos[2] + 0.10
    say(f"들어 올림: 병 높이 {d.xpos[bottle][2]:.3f} m → {'잡힘' if held else '놓침'}")
    v1.move_path(m, d, I, flip_qs, CLOSE, seg, rec=rec)
    v1.move(m, d, I, q_over, CLOSE, seg, extra=0.5, rec=rec)
    held2 = d.xpos[bottle][2] > bpos[2] + 0.10
    if release == "low":     # 놓는 자세까지 내려가서 놓기
        v1.move_path(m, d, I, drop_qs, CLOSE, seg, rec=rec)
        v1.move(m, d, I, q_drop, OPEN, seg, extra=0.5, rec=rec)
        v1.move(m, d, I, q_over, OPEN, seg, rec=rec)
    else:                    # 위 자세에서 바로 놓기 (병이 통으로 떨어짐)
        v1.move(m, d, I, q_over, OPEN, seg, extra=0.5, rec=rec)
    t_arm = d.time - t_arm0
    # 접기: 통 위 → (거꾸로 넘기기) → 크래들. 시간은 따로 잰다(다음 병으로 갈 때는 접지 않아도 되므로)
    t_back0 = d.time
    for q_ in flip_qs[::-1][::4]:
        v1.move(m, d, I, q_, OPEN, [], extra=0.0, rec=rec)
    v1.move(m, d, I, np.array(STOW_V2), OPEN, seg, rec=rec)
    t_stow = d.time - t_back0
    for _ in range(500): drive(m, d, I, 0, 0, 0); mujoco.mj_step(m, d)
    R = d.site_xmat[sid].reshape(3, 3); rel = R.T @ (d.xpos[bottle] - d.site_xpos[sid])
    hs = m.site_size[sid]
    up = d.xmat[bottle].reshape(3, 3)[:, 2] @ np.array([0, 0, 1.0])
    # 판정 (두 가지를 같이 적는다):
    #   v1 기준 = 무게중심이 통 안쪽 넓이 안 + (서 있으면 테두리 + 6 cm 아래, 누우면 테두리 아래로 병 반지름만큼)
    #   묻힌 통 기준 = 무게중심이 통 안쪽 넓이 안 + 테두리(= 윗면)보다 아래, 또는 v1 기준 (기대어 걸친 병도 무게중심이 테두리 아래면 통 안)
    foot = abs(rel[0]) <= hs[0] and abs(rel[1]) <= hs[1]
    inside_v1 = bool(foot and ((up > 0.7 and rel[2] <= hs[2] + 0.06) or rel[2] <= hs[2] - 0.0325))
    inside = bool(inside_v1 or (foot and rel[2] <= hs[2]))
    out.update(held=held, held_over=held2, inside=inside, inside_v1=inside_v1, t_arm=t_arm, t_stow=t_stow, segs=seg, tau=tau["max"],
               stab_min=stab["min"], rel=rel, up=float(up))
    say(f"다가가기 {out['dist']:.2f} m {out['t_drive']:.1f} s · 팔 동작(집기 시작 → 통에 놓고 손 뺄 때까지) {t_arm:.1f} s · 크래들로 접기 {t_stow:.1f} s")
    say(f"결과: {'성공' if inside else '실패'} — 병(통 기준) {np.round(rel, 3)}, 병 축 cos {up:.2f}, 통 위에서 아직 잡힘 {held2}, "
        f"어깨 힘 최대 {tau['max']:.2f} N·m, 넘어짐 여유 최소 {stab['min'] * 1000:.0f} mm")
    if want_q:
        out["q_over"] = q_over; out["flip_qs"] = flip_qs
    return out


def trials(name):
    ok, ok1, times, stows, fails, stabs = 0, 0, [], [], [], []
    for dx in (-0.02, 0.0, 0.02):
        for dy in (-0.02, 0.0, 0.02):
            r = pick(name, shift=(dx, dy), quiet=True)
            ok += r["inside"]; ok1 += r["inside_v1"]; times.append(r["t_arm"]); stows.append(r["t_stow"]); stabs.append(r["stab_min"])
            if not r["inside"]:
                fails.append(((dx, dy), "놓침(집기)" if not r["held"] else ("통 위 전에 놓침" if not r["held_over"] else "통 밖/걸침"),
                              np.round(r["rel"], 3).tolist(), round(r["up"], 2)))
    f05 = pick(name, friction=0.5, quiet=True)
    res = dict(ok=ok, ok_v1=ok1, n=9, above=r["above"], final=r["final"], t_mean=float(np.mean(times)), t_min=float(np.min(times)), t_max=float(np.max(times)),
               t_stow=float(np.mean(stows)), fails=fails, f05=f05["inside"], stab=float(np.min(stabs)))
    print(f"[{name}] 통에 넣기: 9곳 중 성공 {ok} (v1 기준 {ok1}), 놓는 자세 병 바닥 {r['final'][0]:+.2f} m·기울기 {np.degrees(np.arccos(r['final'][1])):.0f}°, 팔 동작 평균 {res['t_mean']:.1f} s (최소 {res['t_min']:.1f}, 최대 {res['t_max']:.1f}), "
          f"크래들로 접기 평균 {res['t_stow']:.1f} s, 집게 마찰 0.5 {'성공' if f05['inside'] else '실패'}, pick 중 넘어짐 여유 최소 {res['stab'] * 1000:.0f} mm")
    for f_ in fails:
        print("   실패:", f_)
    return res


# ------------------------------------------------------------------ tipping
def tip(name):
    m = mujoco.MjModel.from_xml_path(FILES[name][0]); d = mujoco.MjData(m); I = ids(m)
    mujoco.mj_forward(m, d)
    a = d.xanchor[m.joint(P + "shoulder_lift").id].copy()
    for L in np.arange(0.45, 0.25, -0.002):
        q, e = ik(m, d, I, a + [L, 0.018, 0], q0=np.array([0, 1.5, 0, 0, 0]), iters=400)
        if e < 1e-3:
            break
    wx, wy = VARIANTS[name]["wheel_x"], VARIANTS[name]["wheel_y"]
    rb = m.body("robot").id
    rows = []
    for lab, qq in (("팔 수평 앞 최대", q), ("팔 수평 왼쪽(허리 +90°)", np.r_[1.57, q[1:]]), ("팔 수평 오른쪽(허리 −90°)", np.r_[-1.57, q[1:]]),
                    ("크래들 접기", np.array(STOW_V2))):
        d.qpos[I["qadr"]] = qq; mujoco.mj_forward(m, d)
        for extra in (0.02, 0.1):
            M = d.subtree_com[rb] * m.body_subtreemass[rb] + d.site_xpos[I["tip"]] * extra
            com = M / (m.body_subtreemass[rb] + extra)
            mg = min(wx - abs(com[0]), wy - abs(com[1]))
            rows.append((lab, extra, com[:2].round(3).tolist(), mg))
            print(f"넘어짐 여유 [{lab} + 손끝 {extra} kg]: 무게중심 {np.round(com[:2], 3).tolist()} m, 바퀴 사각형 ±{wx}·±{wy} 까지 {mg * 1000:.0f} mm")
    # 가장 나쁜 옆 방향: 팔·병 외 질량이 얼마 이상이어야 하나 (v1 방식)
    arm_m = sum(m.body_mass[b] for b in range(m.nbody) if m.body(b).name.startswith(P))
    d.qpos[I["qadr"]] = np.r_[1.57, q[1:]]; mujoco.mj_forward(m, d)
    mom = abs(sum(m.body_mass[b] * d.xipos[b][1] for b in range(m.nbody) if m.body(b).name.startswith(P)) + 0.1 * d.site_xpos[I["tip"]][1])
    need = mom / wy - arm_m - 0.1
    print(f"   팔 {arm_m:.3f} kg 옆으로 쭉 펴고 0.1 kg: 넘어지지 않으려면 나머지 질량(차체 가운데) ≥ {need:.2f} kg (지금 {m.body_subtreemass[rb] - arm_m:.2f} kg)")
    return dict(rows=rows, need=need)


ALL = ["speed", "stow", "reach", "trials", "tip"]
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "-v"]
    names = [a for a in args if a in FILES] or list(FILES)
    what = [a for a in args if a not in FILES] or ALL
    t = time.time()
    for n in names:
        for w in what:
            print(f"===== [{n}] {w}")
            globals()[w](n)
    print(f"(실행 {time.time() - t:.0f} s, MuJoCo {mujoco.__version__})")
