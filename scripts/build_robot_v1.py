"""robot_v1 MJCF 생성기: 메카넘 차체(단순화) + 청소 모듈 A + SO-101 팔 + 바구니 + 깊이 카메라 자리.

    uv run python scripts/build_robot_v1.py        # scenes/robot_v1.xml 을 다시 쓴다

차체 치수는 아래 CHASSIS 딕셔너리 하나에 모았다. 차체 후보가 바뀌면 여기만 고치고 다시 돌린다.
값의 출처·가정 표시는 logs/2026-11-24_mecanum_so101_measurements.md 1절 표에 있다.

좌표: 로봇 원점 = 차체 가운데 바로 아래 바닥. x = 앞, y = 왼쪽, z = 위 (m, kg, s).
"""
import math
from pathlib import Path

# ---- 차체: Yahboom ROSMASTER X3 기준 (치수는 커뮤니티 URDF automaticaddison/yahboom_rosmaster, BSD-3) ----
CHASSIS = dict(
    length=0.300,        # URDF base_length 0.300
    width=0.1994,        # URDF total_width 0.19940 (바퀴 포함)
    wheel_r=0.0325,      # URDF wheel_radius
    wheel_w=0.0304,      # URDF wheel_width
    wheel_x=0.08,        # URDF wheel_xoff (앞뒤 바퀴 축 = ±0.08)
    wheel_y=0.0745,      # URDF wheel_separation/2 + wheel_yoff = 0.0845 - 0.01
    body_bottom=0.035,   # 차체 바닥판 높이 (가정: 바퀴 반지름 약간 위)
    deck_z=0.14,         # 윗판 높이 (추정: URDF 메시의 판 2장 간격에서, 확인 필요)
    mass=4.2,            # 판매처 표기 4.23 kg (포장 포함 여부 확인 필요)
    vmax=1.0,            # 최고 속도 m/s (판매처 Q&A 1.0 m/s, 확인 필요)
)
# 제자리 회전 상한: 메카넘 운동학 ω = v / (lx + ly)  (바퀴 속도가 vmax일 때)
CHASSIS["wmax"] = round(CHASSIS["vmax"] / (CHASSIS["wheel_x"] + CHASSIS["wheel_y"]), 2)

ARM_X = 0.07          # SO-101 받침 원점: 차체 가운데에서 앞으로 0.07 m (가정 — 주인 장착 디자인 전)
GUIDE = dict(theta_deg=40.0, mouth=0.20, neck=0.04, height=0.03, gap=0.002, thick=0.006)  # 기획안 6-10·9장 (가정)
PAD_R = 0.05          # 뒤 회전 패드 반지름 (가정: 차체 폭 0.2 m에 원판 2장)
# 작은 바구니: 차체 왼쪽 옆에 거는 통 (가정). 윗판 뒤쪽에 두면 SO-101이 병(21 cm)을 세워 넣을 수 없다
# (어깨가 바닥에서 0.26 m라 손끝을 아래로 향하면 병 바닥이 윗판보다 높아지지 않음 — 측정 기록 참고).
BASKET = dict(x=0.109, y=0.157, inner_x=0.10, inner_y=0.10, floor_z=0.045, rim_z=0.145, t=0.004)
VACUUM = dict(x=-0.06, size=(0.05, 0.045, 0.035), mass=0.7)  # 핸디 청소기 자리 (기획안 0.5~1 kg 가운데, 가정)
CAM = dict(x=0.135, z=0.30, pitch_deg=40.0, fovy=58)          # 깊이 카메라 자리 (가정)


SO101_SRC = "scenes/assets/so101/so101_new_calib.xml"            # 원본 (고치지 않음)
SO101_OUT = "scenes/assets/so101/so101_new_calib_litterbot.xml"  # 이 저장소에서 바꾼 사본 (아래 so101_derived)
FINGER_FRICTION = 1.0   # 집게 마찰 계수 (MuJoCo 기본값. 실물 PLA 집게는 더 낮을 수 있음 — 확인 필요)


def so101_derived(src: str) -> str:
    """SO-101 원본 MJCF에서 바꾸는 것: 고정 집게(wrist_roll_follower)의 충돌 형상, 그리고 두 집게 면의 condim·마찰.
    MuJoCo는 메시 충돌을 볼록 껍질로 계산하는데, 이 부품은 서보 몸통과 고정 손가락이 한 메시라
    껍질이 두 손가락 사이를 메워 병(ø65 mm)이 들어갈 자리가 없다. 그래서 그 메시 충돌을 끄고
    상자 2개(손가락, 손바닥)로 바꾼다. 상자 치수는 메시 꼭짓점을 gripperframe 좌표로 옮겨 잰 값이다.
    그 밖의 관절·질량·액추에이터는 원본 그대로다 (Apache-2.0 §4: 바꾼 파일에 바꾼 사실을 적는다)."""
    old = ('<geom type="mesh" class="collision" pos="8.32667e-17 -0.000218214 0.000949706" quat="0 1 0 0" '
           'mesh="wrist_roll_follower_so101_v1" material="wrist_roll_follower_so101_v1_material"/>')
    assert old in src, "원본 SO-101 파일이 예상과 다르다"
    new = (f'<!-- litter-bot 변경: 볼록 껍질 대신 상자 2개 (gripperframe 좌표, 손끝 = x 0) -->\n'
           f'                <frame pos="-0.0079 -0.000218121 -0.0981274" quat="0.707107 0 0.707107 0">\n'
           f'                  <geom name="fixed_finger" type="box" group="3" pos="-0.027 0 -0.0115" size="0.033 0.009 0.0115" '
           f'condim="4" friction="{FINGER_FRICTION} 0.01 0.0001"/>\n'
           f'                  <geom name="fixed_palm" type="box" group="3" pos="-0.082 0 0.0055" size="0.017 0.026 0.0325"/>\n'
           f'                </frame>')
    out = src.replace(old, new)
    out = out.replace('<mujoco model="so101_new_calib">',
                      '<!-- litter-bot 변경본 (2026-11-24): 원본 so101_new_calib.xml 에서 고정 집게 충돌 형상만 상자로 바꿈. '
                      'scripts/build_robot_v1.py 가 만든다. 원본: TheRobotStudio/SO-ARM100 (Apache-2.0) -->\n'
                      '<mujoco model="so101_new_calib_litterbot">')
    # 움직이는 집게도 condim 4 로 (병이 돌며 빠지는 것을 줄임)
    out = out.replace('mesh="moving_jaw_so101_v1" material="moving_jaw_so101_v1_material"/>\n                </body>',
                      f'mesh="moving_jaw_so101_v1" material="moving_jaw_so101_v1_material" condim="4" friction="{FINGER_FRICTION} 0.01 0.0001"/>\n                </body>', 1)
    return out


def f(*v):
    return " ".join(f"{x:.4f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x) for x in v)


def build() -> str:
    c = CHASSIS
    L, W, r = c["length"], c["width"], c["wheel_r"]
    body_w = W - 2 * c["wheel_w"]
    zc = (c["body_bottom"] + c["deck_z"]) / 2
    hz = (c["deck_z"] - c["body_bottom"]) / 2

    # V자 가이드: 앞쪽 끝 = 입(mouth), 뒤쪽 끝 = 목(neck). 진행 방향과 θ.
    g = GUIDE
    th = math.radians(g["theta_deg"])
    dy = (g["mouth"] - g["neck"]) / 2
    glen = dy / math.sin(th)              # 날 한 장 길이
    dx = dy / math.tan(th)                # 앞뒤 길이
    x_neck = L / 2 + 0.01                 # 차체 앞면 바로 앞
    x_mid = x_neck + dx / 2
    y_mid = g["neck"] / 2 + dy / 2
    gz = g["gap"] + g["height"] / 2
    guides = ""
    for side, s in (("left", 1), ("right", -1)):  # 날이 앞으로 갈수록 바깥으로 벌어짐(진행 방향과 θ)
        guides += (f'      <geom name="guide_{side}" class="guide" pos="{f(x_mid, s * y_mid, gz)}" '
                   f'euler="0 0 {f(s * th)}" size="{f(glen / 2, g["thick"] / 2, g["height"] / 2)}"/>\n')
    # 흡입구 판정 영역: 목 뒤 4 × 4 cm (기획안 8장, 가정). 충돌 없음.
    suction = f'      <site name="suction_zone" type="box" pos="{f(x_neck, 0.0, 0.02)}" size="0.02 0.02 0.02" rgba="0.16 0.49 0.88 0.35"/>\n'

    wheels = ""
    for nm, sx, sy in (("fl", 1, 1), ("fr", 1, -1), ("rl", -1, 1), ("rr", -1, -1)):
        wheels += (f'      <geom name="wheel_{nm}" class="wheel" pos="{f(sx * c["wheel_x"], sy * c["wheel_y"], r)}" '
                   f'size="{f(r, c["wheel_w"] / 2)}"/>\n')

    pads = ""
    for nm, sy in (("left", 1), ("right", -1)):
        pads += (f'      <geom name="pad_{nm}" class="zone" type="cylinder" pos="{f(-L / 2 - PAD_R + 0.01, sy * PAD_R, 0.003)}" '
                 f'size="{f(PAD_R, 0.003)}" rgba="0.12 0.44 0.36 0.6"/>\n')

    b = BASKET
    hx, hy, t = b["inner_x"] / 2, b["inner_y"] / 2, b["t"]
    hw = (b["rim_z"] - b["floor_z"]) / 2
    zc_b = (b["rim_z"] + b["floor_z"]) / 2
    basket = (
        f'      <body name="basket" pos="{f(b["x"], b["y"], 0.0)}">\n'
        f'        <geom name="basket_floor" class="basket" pos="0 0 {f(b["floor_z"] - t / 2)}" size="{f(hx + t, hy + t, t / 2)}"/>\n'
        f'        <geom name="basket_wall_f" class="basket" pos="{f(hx + t / 2, 0.0, zc_b)}" size="{f(t / 2, hy + t, hw)}"/>\n'
        f'        <geom name="basket_wall_b" class="basket" pos="{f(-hx - t / 2, 0.0, zc_b)}" size="{f(t / 2, hy + t, hw)}"/>\n'
        f'        <geom name="basket_wall_l" class="basket" pos="{f(0.0, hy + t / 2, zc_b)}" size="{f(hx, t / 2, hw)}"/>\n'
        f'        <geom name="basket_wall_r" class="basket" pos="{f(0.0, -hy - t / 2, zc_b)}" size="{f(hx, t / 2, hw)}"/>\n'
        f'        <site name="basket_zone" type="box" pos="0 0 {f(zc_b)}" size="{f(hx, hy, hw)}" rgba="1 1 0 0.15"/>\n'
        f'      </body>\n')

    v = VACUUM
    vac = (f'      <geom name="vacuum" class="body" pos="{f(v["x"], 0.0, c["deck_z"] + v["size"][2])}" '
           f'size="{f(*v["size"])}" mass="{f(v["mass"])}" rgba="0.79 0.85 0.94 1"/>\n')

    cm = CAM
    cam = (f'      <geom name="cam_mast" class="vis" type="cylinder" pos="{f(cm["x"], -0.055, (c["deck_z"] + cm["z"]) / 2)}" size="{f(0.006, (cm["z"] - c["deck_z"]) / 2)}" rgba="0.3 0.3 0.3 1"/>\n'
           f'      <geom name="cam_box" class="vis" type="box" pos="{f(cm["x"], -0.055, cm["z"])}" euler="0 {f(math.radians(cm["pitch_deg"]))} 0" size="0.0125 0.045 0.0125" rgba="0.1 0.1 0.1 1"/>\n'
           # MuJoCo 카메라는 -z 방향을 본다: x축 기준 회전으로 앞(+x)·아래를 보게 xyaxes 지정
           f'      <camera name="depth_cam" pos="{f(cm["x"] + 0.013, -0.055, cm["z"])}" fovy="{cm["fovy"]}" '
           f'xyaxes="0 -1 0 {f(math.sin(math.radians(cm["pitch_deg"])), 0.0, math.cos(math.radians(cm["pitch_deg"])))}"/>\n')

    xml = f"""<!--
  robot_v1: 메카넘 4륜 차체(단순화) + 청소 모듈 A + SO-ARM101(SO-101) 팔 — 2026-11-24
  이 파일은 scripts/build_robot_v1.py 가 만든다. 손으로 고치지 말고 스크립트의 CHASSIS 값을 고친 뒤 다시 돌린다.
  - 차체: Yahboom ROSMASTER X3 치수 기준(커뮤니티 URDF), 길이 {L} m, 폭 {W} m(바퀴 포함), 윗판 {c['deck_z']} m(추정), 질량 {c['mass']} kg
  - 이동: 평면 관절 3개(base_x, base_y 월드 기준 미끄럼 + base_yaw) + 속도 액추에이터. 메카넘 롤러는 만들지 않았다.
    최고 속도 {c['vmax']} m/s(판매처 Q&A, 확인 필요), 제자리 회전 {c['wmax']} rad/s(운동학 상한 v/(lx+ly))
  - 팔: TheRobotStudio SO-ARM100 저장소 Simulation/SO101/so101_new_calib.xml (Apache-2.0) 에서
    고정 집게 충돌 형상만 상자로 바꾼 사본(so101_new_calib_litterbot.xml)을 attach
  - 앞: V자 가이드(충돌 있음, θ {GUIDE['theta_deg']}°, 입 {GUIDE['mouth']} m, 목 {GUIDE['neck']} m) + 흡입구 판정 영역(site suction_zone)
  - 뒤: 회전 패드 2개 판정 영역(충돌 없음), 왼쪽 옆: 바구니, 위: 핸디 청소기 자리, 깊이 카메라 자리(depth_cam)
  치수·질량 중 출처가 없는 값은 모두 가정이다.
-->
<mujoco model="robot_v1">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.002" integrator="implicitfast"/>
  <visual>
    <headlight diffuse="0.55 0.55 0.55" ambient="0.35 0.35 0.35"/>
    <global offwidth="1600" offheight="1200"/>
  </visual>
  <default>
    <default class="body"><geom type="box" rgba="0.2 0.55 0.3 1" friction="0.6 0.005 0.0001"/></default>
    <default class="vis"><geom contype="0" conaffinity="0" mass="0"/></default>
    <default class="wheel"><geom type="cylinder" euler="1.5708 0 0" contype="0" conaffinity="0" mass="0" rgba="0.15 0.15 0.15 1"/></default>
    <default class="guide"><geom type="box" mass="0.02" rgba="0.6 0.36 0 1" friction="0.3 0.005 0.0001"/></default>
    <default class="zone"><geom contype="0" conaffinity="0" mass="0"/></default>
    <default class="basket"><geom type="box" mass="0.01" rgba="0.95 0.95 0.95 1"/></default>
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
      <geom name="chassis" class="body" pos="{f(0.0, 0.0, zc)}" size="{f(L / 2, body_w / 2, hz)}" mass="{f(c['mass'])}"/>
{wheels}{guides}{suction}{pads}{vac}{cam}{basket}      <frame name="arm_mount" pos="{f(ARM_X, 0.0, c['deck_z'])}">
        <attach model="so101" body="base" prefix="arm_"/>
      </frame>
    </body>
  </worldbody>
  <actuator>
    <!-- 속도 명령(월드 기준). 차체 기준 (vx, vy)는 yaw로 돌려 넣는다: src/checks/robot_v1_util.py drive() -->
    <velocity name="drive_x" joint="base_x" kv="400" ctrlrange="{f(-c['vmax'], c['vmax'])}"/>
    <velocity name="drive_y" joint="base_y" kv="400" ctrlrange="{f(-c['vmax'], c['vmax'])}"/>
    <velocity name="drive_yaw" joint="base_yaw" kv="20" ctrlrange="{f(-c['wmax'], c['wmax'])}"/>
  </actuator>
</mujoco>
"""
    return xml


def standalone(xml: str) -> str:
    """로봇만 보는 장면용: 바닥과 조명을 더한다."""
    floor = ('    <light pos="0 0 3" dir="0 0 -1" diffuse="0.7 0.7 0.7"/>\n'
             '    <geom name="floor" type="plane" size="2 2 0.1" rgba="0.8 0.62 0.4 1"/>\n')
    return xml.replace("  <worldbody>\n", "  <worldbody>\n" + floor, 1)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    (root / SO101_OUT).write_text(so101_derived((root / SO101_SRC).read_text(encoding="utf-8")), encoding="utf-8")
    xml = build()
    (root / "scenes" / "robot_v1.xml").write_text(standalone(xml), encoding="utf-8")
    print("wrote scenes/robot_v1.xml", CHASSIS)
