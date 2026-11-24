"""robot_v2 MJCF 생성기 — 주인 설계(2026-11-24, 새싹봇 항목 83) 배치.

    uv run python scripts/build_robot_v2.py      # scenes/robot_v2*.xml, gym_v2*.xml (차체 3안)

robot_v1(build_robot_v1.py)에서 바뀐 점 (설계 페이지 '체육관 정리 로봇 설계 구상'의 ①~④):
  - 팔(SO-101): 몸통 위 앞 가운데 받침, 어깨 회전축 = 윗면 앞 모서리에서 6 cm 뒤. 안 쓸 때는 허리 90°로 돌려
    몸통 위 받침대(크래들)에 접어 눕힘(STOW_V2, 자세는 src/checks/robot_v2_measure.py stow 가 찾은 값).
  - 앞 청소: V자 가이드(충돌 있음) → 앞 모서리 옆솔 2개 판정 영역(충돌 없음, 안쪽으로 돈다고 봄).
    흡입구 = 차체 밑 가운데, 앞바퀴 바로 뒤 판정 영역. 뒤 = 마른 회전 패드 2개 판정 영역(반대 방향).
    앞 범퍼(충돌 있음)는 바닥에서 1.5 cm 띄움.
  - 쓰레기통: 왼쪽 옆에 거는 바구니 → 몸통에 묻은 통(테두리 = 윗면 높이), 팔 회전축에서 왼쪽 뒤 대각선 15~20 cm.
  - 외형: 2단(아래 청소 베이스 + 위 몸통 — 색으로만 나눔), 앞 위 짧은 기둥 깊이 카메라(높이 0.25 m, 아래로 35°),
    앞면 화면, 위 뒤 손잡이·비상정지(모두 보기용, 충돌 없음).
차체 치수는 VARIANTS 에: "x3" = Yahboom ROSMASTER X3 30 × 20 cm(지금 기준, 통은 설계대로 대각선 — 뒷바퀴 위라 얕음),
"x3b" = 같은 차체에 통을 거의 바로 뒤로(바퀴를 피해 깊게), "wide" = 설계 페이지 어림 39 × 28 × 15 cm.
값의 출처·가정 표시는 logs/2026-11-24_robot_v2_measurements.md 1절 표.
좌표: 로봇 원점 = 차체 가운데 바로 아래 바닥. x = 앞, y = 왼쪽, z = 위 (m, kg, s).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_robot_v1 import SO101_OUT, SO101_SRC, f, so101_derived  # noqa: E402

PAN_OFFSET = 0.0388   # SO-101 base 원점 → 어깨 회전(shoulder_pan) 축, 앞으로 (so101_new_calib.xml 의 shoulder body pos)

VARIANTS = {
    # ROSMASTER X3: 치수·질량·속도는 robot_v1 과 같다(커뮤니티 URDF·판매처, 확인 필요)
    "x3": dict(
        length=0.300, width=0.1994, wheel_r=0.0325, wheel_w=0.0304, wheel_x=0.08, wheel_y=0.0745,
        body_bottom=0.035, base_top=0.08, deck_z=0.14, mass=4.2, vmax=1.0,
        upper_inset=0.0,          # 위 몸통이 아래 베이스보다 좁은 만큼(한쪽). X3는 폭이 좁아 0 (색으로만 2단)
        # 통: 안쪽 0.10 × 0.10 (가정, v1 바구니와 같음). 뒷바퀴 위와 겹쳐서 바닥을 바퀴 윗면(0.065) 위 0.07 m로 (가정)
        bin=dict(inner=0.10, floor_z=0.07, dist=0.155, side=0.045),
        brush_r=0.035, pad_r=0.05,  # 옆솔·패드 반지름 (가정: 패드 2장 = 폭 0.20 m)
    ),
    # X3 + 통을 거의 바로 뒤로(옆 0.005 m): 뒷바퀴와 겹치지 않아 통 바닥을 0.045 m 까지 내릴 수 있다 (깊이 9.5 cm, 가정)
    "x3b": None,
    # 설계 페이지 어림 '길이 38~40 × 폭 26~30 × 윗면 15 cm'의 가운데. 바퀴·질량은 X3 와 같다고 둠 (가정)
    "wide": dict(
        length=0.390, width=0.280, wheel_r=0.0325, wheel_w=0.0304, wheel_x=0.13, wheel_y=0.1248,
        body_bottom=0.035, base_top=0.08, deck_z=0.15, mass=4.2, vmax=1.0,
        upper_inset=0.015,
        # 통: 설계 페이지 '시판 통 15 × 15 × 15 cm' 대신 안쪽 0.13 × 0.13 (몸통 폭에 묻으려면, 가정), 바닥 0.045
        bin=dict(inner=0.13, floor_z=0.045, dist=0.17, side=0.03),
        brush_r=0.045, pad_r=0.07,  # 패드 2장 = 폭 0.28 m (가정)
    ),
}
VARIANTS["x3b"] = dict(VARIANTS["x3"], bin=dict(inner=0.10, floor_z=0.045, dist=0.155, side=0.005))
# 설계 페이지 차체 + 병이 누울 수 있는 긴 통(안쪽 앞뒤 0.23 × 옆 0.12 m, 회전축 바로 뒤 0.19 m) — 대안 시험용 (가정)
VARIANTS["wide_long"] = dict(VARIANTS["wide"], bin=dict(inner_x=0.23, inner_y=0.12, floor_z=0.045, dist=0.19, side=0.0))
FILE_NAMES = {"x3": ("robot_v2", "gym_v2"), "x3b": ("robot_v2_x3b", "gym_v2_x3b"), "wide": ("robot_v2_wide", "gym_v2_wide"),
              "wide_long": ("robot_v2_wide_long", "gym_v2_wide_long")}
PIVOT_BACK = 0.06      # 어깨 회전축 = 윗면 앞 모서리에서 6 cm 뒤 (설계 페이지 '로봇팔' 줄)
BIN_T = 0.004          # 통 벽 두께 (가정)
SUCTION = dict(dx=0.04, dy=0.10, gap_back=0.012)  # 흡입구 판정 4 × 10 cm, 앞바퀴 뒤 끝에서 1.2 cm 뒤 (가정)
BUMPER = dict(bottom=0.015, top=0.06, thick=0.012)  # 범퍼 바닥에서 1.5 cm (설계 1~2 cm의 가운데)
CAM = dict(z=0.25, pitch_deg=35.0, fovy=58)        # 깊이 카메라: 높이 약 0.25 m, 아래로 35° (설계 페이지, 가정)
VACUUM_MASS = 0.7      # 핸디 청소기 (기획안 0.5~1 kg 가운데, 가정) — 베이스 안, 보이지 않는 질량
# 크래들 접기 자세 (new calib 관절값 rad). robot_v2_measure.py stow 가 '팔 최고 높이 최소 + 몸·통과 충돌 없음'으로 찾은 값.
STOW_V2 = [-1.5708, -1.74, 1.69, 1.24, 0.0]


def layout(v):
    """변형 v 의 주요 좌표(모델 만들기와 측정 스크립트가 같이 쓴다)."""
    L, W = v["length"], v["width"]
    body_w = W - 2 * v["wheel_w"]
    up_w = body_w - 2 * v["upper_inset"]
    pivot = (L / 2 - PIVOT_BACK, 0.0)
    b = v["bin"]
    # 통 가운데: 회전축에서 왼쪽 뒤 대각선, 회전축까지 수평 거리 dist, 옆 위치 side
    bx = pivot[0] - math.sqrt(b["dist"] ** 2 - b["side"] ** 2)
    by = b["side"]
    return dict(L=L, W=W, body_w=body_w, up_w=up_w, pivot=pivot, arm_x=pivot[0] - PAN_OFFSET, bin_c=(bx, by))


def boxes_around(x0, x1, y0, y1, z0, z1, hole):
    """[x0,x1]×[y0,y1]×[z0,z1] 상자에서 hole=(hx0,hx1,hy0,hy1) 기둥을 뺀 나머지를 상자 여러 개로."""
    hx0, hx1, hy0, hy1 = hole
    hx0, hx1 = max(hx0, x0), min(hx1, x1)
    hy0, hy1 = max(hy0, y0), min(hy1, y1)
    out = []
    for a, b_, c, d in ((x0, hx0, y0, y1), (hx1, x1, y0, y1), (hx0, hx1, y0, hy0), (hx0, hx1, hy1, y1)):
        if b_ - a > 1e-4 and d - c > 1e-4:
            out.append(((a + b_) / 2, (c + d) / 2, (z0 + z1) / 2, (b_ - a) / 2, (d - c) / 2, (z1 - z0) / 2))
    return out


def build(name="x3"):
    v = VARIANTS[name]
    lay = layout(v)
    L, W, body_w, up_w = lay["L"], lay["W"], lay["body_w"], lay["up_w"]
    r = v["wheel_r"]
    b = v["bin"]
    bx, by = lay["bin_c"]
    hix, hiy = b.get("inner_x", b.get("inner")) / 2, b.get("inner_y", b.get("inner")) / 2
    hox, hoy = hix + BIN_T, hiy + BIN_T
    hole = (bx - hox, bx + hox, by - hoy, by + hoy)
    z_floor_bot = b["floor_z"] - BIN_T

    geoms = ""
    # 아래 청소 베이스 (body_bottom ~ base_top) 와 위 몸통 (base_top ~ deck_z). 통 자리는 비운다.
    k = 0
    for (z0, z1, hw, cls) in ((v["body_bottom"], v["base_top"], body_w / 2, "base"), (v["base_top"], v["deck_z"], up_w / 2, "upper")):
        if z1 <= z_floor_bot:      # 통 바닥보다 아래 층: 통 자리도 채움
            parts = [(0.0, 0.0, (z0 + z1) / 2, L / 2, hw, (z1 - z0) / 2)]
        elif z0 >= z_floor_bot:
            parts = boxes_around(-L / 2, L / 2, -hw, hw, z0, z1, hole)
        else:                      # 통 바닥이 이 층 가운데에 있으면 두 층으로 쪼갠다
            parts = [(0.0, 0.0, (z0 + z_floor_bot) / 2, L / 2, hw, (z_floor_bot - z0) / 2)]
            parts += boxes_around(-L / 2, L / 2, -hw, hw, z_floor_bot, z1, hole)
        for (cx, cy, cz, sx, sy, sz) in parts:
            geoms += f'      <geom name="{cls}_{k}" class="{cls}" pos="{f(cx, cy, cz)}" size="{f(sx, sy, sz)}"/>\n'
            k += 1
    # 질량: 차체 질량은 가운데(가정), 핸디 청소기는 베이스 안 가운데 뒤쪽 오른편(통 반대쪽, 가정)
    geoms += (f'      <geom name="chassis_mass" class="vis" type="box" pos="{f(0.0, 0.0, (v["body_bottom"] + v["deck_z"]) / 2)}" '
              f'size="0.01 0.01 0.01" mass="{f(v["mass"])}" rgba="0 0 0 0"/>\n')
    geoms += (f'      <geom name="vacuum_mass" class="vis" type="box" pos="{f(-0.02, -body_w / 4, (v["body_bottom"] + v["base_top"]) / 2)}" '
              f'size="0.01 0.01 0.01" mass="{f(VACUUM_MASS)}" rgba="0 0 0 0"/>\n')

    # 바퀴 (보기용)
    for nm, sx, sy in (("fl", 1, 1), ("fr", 1, -1), ("rl", -1, 1), ("rr", -1, -1)):
        geoms += (f'      <geom name="wheel_{nm}" class="wheel" pos="{f(sx * v["wheel_x"], sy * v["wheel_y"], r)}" '
                  f'size="{f(r, v["wheel_w"] / 2)}"/>\n')

    # 앞 범퍼 (충돌 있음, 바닥에서 1.5 cm)
    bp = BUMPER
    geoms += (f'      <geom name="bumper" class="bumper" pos="{f(L / 2 + bp["thick"] / 2, 0.0, (bp["bottom"] + bp["top"]) / 2)}" '
              f'size="{f(bp["thick"] / 2, body_w / 2, (bp["top"] - bp["bottom"]) / 2)}"/>\n')
    # 앞 모서리 옆솔 2개 (판정 영역, 충돌 없음): 가운데가 앞 모서리 안쪽, 솔 끝이 앞·옆으로 조금 나옴
    br = v["brush_r"]
    for nm, s in (("left", 1), ("right", -1)):
        geoms += (f'      <geom name="brush_{nm}" class="zone" type="cylinder" pos="{f(L / 2 - 0.4 * br, s * (body_w / 2 - 0.4 * br), 0.004)}" '
                  f'size="{f(br, 0.004)}" rgba="0.95 0.65 0.1 0.7"/>\n')
    # 흡입구 (판정 영역): 차체 밑 가운데, 앞바퀴 뒤 끝 바로 뒤
    sx_c = v["wheel_x"] - r - SUCTION["gap_back"] - SUCTION["dx"] / 2
    sites = (f'      <site name="suction_zone" type="box" pos="{f(sx_c, 0.0, 0.015)}" '
             f'size="{f(SUCTION["dx"] / 2, SUCTION["dy"] / 2, 0.015)}" rgba="0.16 0.49 0.88 0.5"/>\n')
    # 뒤 회전 패드 2개 (판정 영역, 반대 방향으로 돈다고 봄)
    pr = v["pad_r"]
    for nm, s in (("left", 1), ("right", -1)):
        geoms += (f'      <geom name="pad_{nm}" class="zone" type="cylinder" pos="{f(-L / 2 - pr + 0.01, s * pr, 0.003)}" '
                  f'size="{f(pr, 0.003)}" rgba="0.12 0.44 0.36 0.6"/>\n')

    # 묻힌 쓰레기통 (몸통 안, 테두리 = 윗면 높이)
    rim = v["deck_z"]
    hw = (rim - b["floor_z"]) / 2
    zc = (rim + b["floor_z"]) / 2
    t = BIN_T
    bin_xml = (
        f'      <body name="bin" pos="{f(bx, by, 0.0)}">\n'
        f'        <geom name="bin_floor" class="bin" pos="0 0 {f(b["floor_z"] - t / 2)}" size="{f(hox, hoy, t / 2)}"/>\n'
        f'        <geom name="bin_wall_f" class="bin" pos="{f(hix + t / 2, 0.0, zc)}" size="{f(t / 2, hoy, hw)}"/>\n'
        f'        <geom name="bin_wall_b" class="bin" pos="{f(-hix - t / 2, 0.0, zc)}" size="{f(t / 2, hoy, hw)}"/>\n'
        f'        <geom name="bin_wall_l" class="bin" pos="{f(0.0, hiy + t / 2, zc)}" size="{f(hix, t / 2, hw)}"/>\n'
        f'        <geom name="bin_wall_r" class="bin" pos="{f(0.0, -hiy - t / 2, zc)}" size="{f(hix, t / 2, hw)}"/>\n'
        f'        <site name="bin_zone" type="box" pos="0 0 {f(zc)}" size="{f(hix, hiy, hw)}" rgba="1 1 0 0.2"/>\n'
        f'      </body>\n')

    # 보기용: 깊이 카메라 기둥(앞 오른쪽 모서리), 앞면 화면, 뒤 손잡이, 비상정지, 크래들
    cm = CAM
    cx, cy = L / 2 - 0.02, -(up_w / 2 - 0.015)
    pitch = math.radians(cm["pitch_deg"])
    vis = (f'      <geom name="cam_mast" class="vis" type="cylinder" pos="{f(cx, cy, (v["deck_z"] + cm["z"]) / 2)}" size="{f(0.006, (cm["z"] - v["deck_z"]) / 2)}" rgba="0.3 0.3 0.3 1"/>\n'
           f'      <geom name="cam_box" class="vis" type="box" pos="{f(cx, cy, cm["z"])}" euler="0 {f(pitch)} 0" size="0.0125 0.045 0.0125" rgba="0.1 0.1 0.1 1"/>\n'
           f'      <camera name="depth_cam" pos="{f(cx + 0.013, cy, cm["z"])}" fovy="{cm["fovy"]}" '
           f'xyaxes="0 -1 0 {f(math.sin(pitch), 0.0, math.cos(pitch))}"/>\n'
           f'      <geom name="screen" class="vis" type="box" pos="{f(L / 2 + 0.002, 0.0, (v["base_top"] + v["deck_z"]) / 2 + 0.005)}" '
           f'size="{f(0.002, min(0.05, up_w / 2 - 0.02), 0.02)}" rgba="0.05 0.1 0.2 1"/>\n'
           f'      <geom name="handle_bar" class="vis" type="capsule" fromto="{f(-L / 2 + 0.02, -0.04, v["deck_z"] + 0.04, -L / 2 + 0.02, 0.04, v["deck_z"] + 0.04)}" size="0.006" rgba="0.25 0.25 0.25 1"/>\n'
           f'      <geom name="handle_post_l" class="vis" type="capsule" fromto="{f(-L / 2 + 0.02, 0.04, v["deck_z"], -L / 2 + 0.02, 0.04, v["deck_z"] + 0.04)}" size="0.005" rgba="0.25 0.25 0.25 1"/>\n'
           f'      <geom name="handle_post_r" class="vis" type="capsule" fromto="{f(-L / 2 + 0.02, -0.04, v["deck_z"], -L / 2 + 0.02, -0.04, v["deck_z"] + 0.04)}" size="0.005" rgba="0.25 0.25 0.25 1"/>\n'
           f'      <geom name="estop" class="vis" type="cylinder" pos="{f(-L / 2 + 0.035, -(up_w / 2 - 0.025), v["deck_z"] + 0.01)}" size="0.015 0.01" rgba="0.85 0.1 0.1 1"/>\n'
           f'      <geom name="cradle" class="vis" type="box" pos="{f(lay["pivot"][0] - 0.005, -(up_w / 2 - 0.03), v["deck_z"] + 0.012)}" size="0.02 0.025 0.012" rgba="0.55 0.55 0.6 1"/>\n')

    xml = f"""<!--
  robot_v2 ({name}): 주인 설계(2026-11-24) 배치 — 메카넘 차체(단순화) + 옆솔·흡입·패드 판정 영역 + 묻힌 쓰레기통 + SO-101
  이 파일은 scripts/build_robot_v2.py 가 만든다. 손으로 고치지 말고 스크립트의 VARIANTS 값을 고친 뒤 다시 돌린다.
  - 차체 '{name}': 길이 {L} m, 폭 {W} m(바퀴 포함), 윗면 {v['deck_z']} m, 질량 {v['mass']} kg (+ 핸디 청소기 {VACUUM_MASS} kg)
  - 이동: robot_v1 과 같음(평면 관절 base_x/base_y/base_yaw + 속도 액추에이터, 롤러 없음)
  - 팔: so101_new_calib_litterbot.xml, 어깨 회전축 = 윗면 앞 모서리에서 {PIVOT_BACK} m 뒤, 가운데
  - 앞: 옆솔 2개(brush_left/right) · 밑 가운데 흡입구(site suction_zone) · 뒤 패드 2개(pad_left/right) — 모두 충돌 없는 판정 영역
    범퍼(bumper)만 충돌 있음, 바닥에서 {BUMPER['bottom']} m
  - 쓰레기통(body bin, site bin_zone): 몸통에 묻음, 안쪽 {2 * hix:.2f} × {2 * hiy:.2f} m, 바닥 {b['floor_z']} m, 테두리 {rim} m(= 윗면)
  치수·질량 중 출처가 없는 값은 모두 가정이다 (logs/2026-11-24_robot_v2_measurements.md 1절).
-->
<mujoco model="robot_v2_{name}">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.002" integrator="implicitfast"/>
  <visual>
    <headlight diffuse="0.55 0.55 0.55" ambient="0.35 0.35 0.35"/>
    <global offwidth="1600" offheight="1200"/>
  </visual>
  <default>
    <default class="base"><geom type="box" mass="0" rgba="0.82 0.84 0.86 1" friction="0.6 0.005 0.0001"/></default>
    <default class="upper"><geom type="box" mass="0" rgba="0.2 0.55 0.3 1" friction="0.6 0.005 0.0001"/></default>
    <default class="vis"><geom contype="0" conaffinity="0" mass="0"/></default>
    <default class="wheel"><geom type="cylinder" euler="1.5708 0 0" contype="0" conaffinity="0" mass="0" rgba="0.15 0.15 0.15 1"/></default>
    <default class="bumper"><geom type="box" mass="0.03" rgba="0.15 0.15 0.15 1" friction="0.3 0.005 0.0001"/></default>
    <default class="zone"><geom contype="0" conaffinity="0" mass="0"/></default>
    <default class="bin"><geom type="box" mass="0.01" rgba="0.95 0.95 0.95 1"/></default>
  </default>
  <asset>
    <model name="so101" file="assets/so101/so101_new_calib_litterbot.xml"/>
  </asset>
  <worldbody>
    <body name="robot" pos="0 0 0">
      <joint name="base_x" type="slide" axis="1 0 0" damping="0"/>
      <joint name="base_y" type="slide" axis="0 1 0" damping="0"/>
      <joint name="base_yaw" type="hinge" axis="0 0 1" damping="0"/>
      <site name="robot_origin" pos="0 0 0" size="0.01"/>
{geoms}{sites}{vis}{bin_xml}      <frame name="arm_mount" pos="{f(lay['arm_x'], 0.0, v['deck_z'])}">
        <attach model="so101" body="base" prefix="arm_"/>
      </frame>
    </body>
  </worldbody>
  <actuator>
    <velocity name="drive_x" joint="base_x" kv="400" ctrlrange="{f(-v['vmax'], v['vmax'])}"/>
    <velocity name="drive_y" joint="base_y" kv="400" ctrlrange="{f(-v['vmax'], v['vmax'])}"/>
    <velocity name="drive_yaw" joint="base_yaw" kv="20" ctrlrange="{f(-wmax(v), wmax(v))}"/>
  </actuator>
</mujoco>
"""
    return xml


def wmax(v):
    """제자리 회전 상한: 메카넘 운동학 ω = v / (lx + ly) (가정: 바퀴가 최고 속도일 때)."""
    return round(v["vmax"] / (v["wheel_x"] + v["wheel_y"]), 2)


def standalone(xml):
    floor = ('    <light pos="0 0 3" dir="0 0 -1" diffuse="0.7 0.7 0.7"/>\n'
             '    <geom name="floor" type="plane" size="2 2 0.1" rgba="0.8 0.62 0.4 1"/>\n')
    return xml.replace("  <worldbody>\n", "  <worldbody>\n" + floor, 1)


GYM = """<!--
  {gym}: gym_v0(체육관 코트 일부 5 m x 3 m, 그대로) + {robot}(주인 설계 배치, 차체 '{name}') — 2026-11-24
  scripts/build_robot_v2.py 가 만든다. 시작 자리 (-0.6, 0.2), 앞(+x)을 봄 — gym_v1 과 같음.
-->
<mujoco model="{gym}">
  <include file="gym_v0.xml"/>
  <option integrator="implicitfast"/>
  <asset>
    <model name="robot" file="{robot}.xml"/>
  </asset>
  <worldbody>
    <frame name="robot_start" pos="-0.6 0.2 0">
      <attach model="robot" body="robot" prefix=""/>
    </frame>
  </worldbody>
</mujoco>
"""

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    (root / SO101_OUT).write_text(so101_derived((root / SO101_SRC).read_text(encoding="utf-8")), encoding="utf-8")
    for name, (robot, gym) in FILE_NAMES.items():
        (root / "scenes" / f"{robot}.xml").write_text(standalone(build(name)), encoding="utf-8")
        (root / "scenes" / f"{gym}.xml").write_text(GYM.format(gym=gym, robot=robot, name=name), encoding="utf-8")
        print("wrote", robot, gym, layout(VARIANTS[name]))
