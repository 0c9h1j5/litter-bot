"""시뮬 영상 (발표·검토용) — media/sim/*.mp4, *.gif. 지금은 pick_to_bin 하나 (주인: '일단 하나만 먼저').

    uv run --with pillow --with imageio --with imageio-ffmpeg python src/sim/make_videos.py      # pick (약 30 s)
    uv run --with pillow --with imageio --with imageio-ffmpeg python src/sim/make_videos.py trials   # 9곳 성공 수

로봇 = robot_v2 'wide_side' (주인 결정 2026-11-24: 넓은 차체 39 × 28 cm + 옆에 거는 통, 운행 0.3 m/s).
장면 = gym_v2 (기본 = wide_side, gym_v0 5 m × 3 m + 로봇). scripts/build_robot_v2.py 가 만든다.

1. pick    : 벤치 앞 빈 생수병(뚜껑 모양, 가정)의 목·뚜껑을 잡아 옆 통에 넣고 크래들로 접기.
             집기 방식 = src/checks/mecanum_so101_measure.py pick() 그대로(v1 8/9 방식) + smooth_arc=True.
             wide_side 9곳 시험 결과는 logs/2026-11-24_wide_side_pick.md (7/9). 영상은 그중 성공한 병 위치(가운데, 0/0).
(나중에: full_mode_sweep — 장면 전체 훑기 + 커버리지 색 + 충전 자리 복귀, person_stop — 사람 대역 1 m 안 정지·재개)

영상 숫자(시간·성공 수)는 모두 이 스크립트의 시뮬 값이다. 실행할 때 media/sim/numbers.json 에도 남긴다.
시뮬은 속도 명령을 바로 따라간다(가속·제동 미반영, 메카넘 롤러 없음) — robot_v2 실측 기록과 같다.
"""
import json
import sys
import time
import warnings
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "checks"))
sys.path.insert(0, str(ROOT / "scripts"))
import mecanum_so101_measure as M  # noqa: E402
from build_robot_v2 import STOW_WIDE  # noqa: E402
from robot_v1_util import drive, ids  # noqa: E402

warnings.filterwarnings("ignore")
SCENE = "scenes/gym_v2.xml"   # 기본 robot_v2 = wide_side (scripts/build_robot_v2.py)
OUT = ROOT / "media" / "sim"
W, H, FPS = 1280, 720, 30
GIF_W, GIF_FPS = 640, 10
FONT_PATHS = ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"]
NUM = {}
PICK = dict(bottle="cap", quiet=True, scene=SCENE, zone="bin_zone", x_g=0.40, smooth_arc=True)
TRIALS_OK = (7, 9)     # `make_videos.py trials` 결과 (logs/2026-11-24_wide_side_pick.md). 바뀌면 여기를 고친다


def font(sz):
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


F_BIG, F_SM = font(30), font(22)


# ---------------------------------------------------------------- 그리기 도구
def add_geom(scn, typ, size, pos, mat, rgba):
    if scn.ngeom >= scn.maxgeom:
        return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, typ, np.asarray(size, float), np.asarray(pos, float), np.asarray(mat, float).ravel(),
                        np.asarray(rgba, np.float32))
    scn.ngeom += 1


def add_capsule(scn, a, b, r, rgba):
    if scn.ngeom >= scn.maxgeom:
        return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), np.eye(3).ravel(), np.asarray(rgba, np.float32))
    mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_CAPSULE, r, np.asarray(a, float), np.asarray(b, float))
    scn.ngeom += 1


def caption(img, lines, sub=None):
    """왼쪽 위 자막 (반투명 검은 띠)."""
    im = Image.fromarray(img).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    y, boxes = 14, []
    for k, t in enumerate(lines):
        f_ = F_BIG if k == 0 else F_SM
        bb = dr.textbbox((22, y), t, font=f_)
        boxes.append((t, f_, y)); y = bb[3] + 8
    wmax = max(dr.textbbox((22, yy), t, font=f_)[2] for t, f_, yy in boxes)
    dr.rounded_rectangle((10, 8, wmax + 14, y + 4), 10, fill=(0, 0, 0, 150))
    for t, f_, yy in boxes:
        dr.text((22, yy), t, font=f_, fill=(255, 255, 255, 255))
    if sub:
        bb = dr.textbbox((0, 0), sub, font=F_SM)
        x0, y0 = 12, H - (bb[3] - bb[1]) - 22
        dr.rounded_rectangle((x0 - 4, y0 - 6, x0 + bb[2] + 10, H - 8), 8, fill=(0, 0, 0, 140))
        dr.text((x0 + 4, y0 - 2), sub, font=F_SM, fill=(230, 230, 230, 255))
    return np.array(Image.alpha_composite(im, ov).convert("RGB"))


class Video:
    """mp4(H.264, 30 fps) + 같은 내용의 작은 gif(가로 640, 10 fps)."""

    def __init__(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.mp4 = imageio.get_writer(OUT / f"{name}.mp4", fps=FPS, codec="libx264", quality=None, pixelformat="yuv420p",
                                      macro_block_size=16, ffmpeg_params=["-crf", "23", "-preset", "slow"])
        self.gif, self.n = [], 0

    def add(self, img):
        self.mp4.append_data(img)
        if self.n % (FPS // GIF_FPS) == 0:
            self.gif.append(Image.fromarray(img).resize((GIF_W, GIF_W * H // W), Image.LANCZOS))
        self.n += 1

    def close(self):
        self.mp4.close()
        pal = [g.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for g in self.gif]
        pal[0].save(OUT / f"{self.name}.gif", save_all=True, append_images=pal[1:], duration=1000 // GIF_FPS, loop=0, optimize=True)
        sec = self.n / FPS
        mb = {e: (OUT / f"{self.name}.{e}").stat().st_size / 1e6 for e in ("mp4", "gif")}
        print(f"  {self.name}: {sec:.1f} s, mp4 {mb['mp4']:.2f} MB, gif {mb['gif']:.2f} MB")
        NUM.setdefault(self.name, {}).update(video_s=round(sec, 1), mp4_MB=round(mb["mp4"], 2), gif_MB=round(mb["gif"], 2))


class Cams:
    def __init__(self, m, main, top, top_size=(400, 240)):
        self.r = mujoco.Renderer(m, H, W, max_geom=20000)
        self.ri = mujoco.Renderer(m, top_size[1], top_size[0], max_geom=20000)
        self.main, self.top, self.ts = self._cam(*main), self._cam(*top), top_size
        self.opt = mujoco.MjvOption(); self.opt.sitegroup[:] = 1

    @staticmethod
    def _cam(lookat, dist, az, el):
        c = mujoco.MjvCamera(); c.lookat[:] = lookat; c.distance = dist; c.azimuth = az; c.elevation = el
        return c

    def frame(self, d, extra=None):
        self.r.update_scene(d, self.main, self.opt)
        if extra: extra(self.r.scene)
        img = self.r.render().copy()
        self.ri.update_scene(d, self.top, self.opt)
        if extra: extra(self.ri.scene)
        ins = self.ri.render()
        tw, th = self.ts
        x0, y0 = W - tw - 14, 14
        img[y0 - 3:y0 + th + 3, x0 - 3:x0 + tw + 3] = 255
        img[y0:y0 + th, x0:x0 + tw] = ins
        return img


# ---------------------------------------------------------------- 1. pick
def pick_video():
    print("[pick] 시뮬 (mecanum_so101_measure.pick, wide_side, 병 위치 가운데)")
    frames, holder = [], {}
    orig = mujoco.mj_step
    nxt = [0.0]

    def hook(m, d, *a):          # pick() 안의 mj_step 마다: 30 fps 시뮬 시간 간격으로 상태 기록 (동작은 그대로)
        orig(m, d, *a)
        holder["m"], holder["d"] = m, d
        if d.time >= nxt[0]:
            frames.append((d.time, d.qpos.copy(), float(d.ctrl[m.actuator("arm_gripper").id])))
            nxt[0] += 1.0 / FPS

    mujoco.mj_step = hook
    try:
        r = M.pick(shift=(0.0, 0.0), **PICK)
        m, d = holder["m"], holder["d"]
        t_c0 = d.time
        I = ids(m); seg = []
        M.move(m, d, I, np.array(STOW_WIDE), 0.0, seg)       # 크래들로 접기 (넓은 차체 자세)
        for _ in range(250): drive(m, d, I, 0, 0, 0); mujoco.mj_step(m, d)
        t_cradle = d.time - t_c0
    finally:
        mujoco.mj_step = orig
    b = m.body("litter_bottle1").id
    sid = m.site("bin_zone").id
    rel = d.site_xmat[sid].reshape(3, 3).T @ (d.xpos[b] - d.site_xpos[sid])
    still_in = bool(np.all(np.abs(rel[:2]) <= m.site_size[sid][:2]))
    res = dict(success=bool(r["inside"]), still_in_after_cradle=still_in, t_drive=round(r["t_drive"], 2), t_arm=round(r["t_arm"], 2),
               t_cradle=round(t_cradle, 2), t_end=round(frames[-1][0], 2), trials=f"{TRIALS_OK[0]}/{TRIALS_OK[1]} (wide_side, 병 위치 ±2 cm 9곳)")
    NUM["pick_to_bin"] = res
    print("  결과", res)
    # 단계 = pick() 이 돌려준 구간 길이(segs): 위로, 내려오기, 닫기, 들기, 호, 멈춤, 내리기, 벌리기, 통 위로, 접기
    t_arm0 = 0.5 + r["t_drive"]
    names = ["병 위로 팔 뻗기", "병 위에서 내려오기", "목·뚜껑 잡기", "들어 올리기", "옆 통 위로 옮기기", "옆 통 위로 옮기기",
             "통 안으로 내리기", "놓기", "손 빼기", "이동 자세로 접기"]
    edges = t_arm0 + np.cumsum(r["segs"])

    def phase(t):
        if t < t_arm0: return "병 쪽으로 다가가기 (0.3 m/s)"
        if t >= t_c0: return "크래들로 팔 접기"
        k = int(np.searchsorted(edges, t))
        return names[min(k, len(names) - 1)]

    dd = mujoco.MjData(m)
    cams = Cams(m, ([-0.05, 0.55, 0.22], 1.45, 35, -24), ([-0.1, 0.5, 0.0], 1.25, 90, -78))
    v = Video("pick_to_bin")
    for (t, q, g) in frames:
        dd.qpos[:] = q; mujoco.mj_forward(m, dd)
        ph = phase(t)
        raw = cams.frame(dd)
        img = caption(raw, [f"생수병 집어 옆 통에 넣기 — {ph}",
                            f"시뮬 시간 {t:5.1f} s · 배속 ×1",
                            "넓은 차체 39×28 cm + 옆에 거는 통 (주인 결정)"],
                      sub=f"병 위치 {TRIALS_OK[1]}곳 중 {TRIALS_OK[0]}곳 성공한 방식, 그중 가운데 위치(성공) · 다가가기 {r['t_drive']:.1f} s + 팔 {r['t_arm']:.1f} s + 접기 {t_cradle:.1f} s")
        v.add(img)
    end = caption(raw, [f"{'성공' if r['inside'] and still_in else '실패'}: 병이 옆 통 안",
                         f"다가가기 {r['t_drive']:.1f} s · 팔 동작 {r['t_arm']:.1f} s · 크래들 접기 {t_cradle:.1f} s",
                         f"같은 방식 병 위치 ±2 cm {TRIALS_OK[1]}곳 중 {TRIALS_OK[0]}곳 성공 ({TRIALS_OK[1] - TRIALS_OK[0]}곳은 통 밖)"])
    for _ in range(FPS * 2): v.add(end)
    v.close()


def trials():
    """영상과 같은 설정으로 병 위치 ±2 cm 9곳 (v1 pick_trials 와 같은 격자). 성공 수를 TRIALS_OK 와 비교."""
    ok = 0
    for dx in (-0.02, 0.0, 0.02):
        for dy in (-0.02, 0.0, 0.02):
            r = M.pick(shift=(dx, dy), **PICK)
            ok += r["inside"]
            print(f"  병 위치 ({dx:+.2f}, {dy:+.2f}) m: {'성공' if r['inside'] else '실패'}  다가가기 {r['t_drive']:.2f} s, 팔 {r['t_arm']:.2f} s, "
                  f"병(통 기준) {np.round(r['bottle_rel'], 3).tolist()}")
    print(f"  {ok}/9 성공 (TRIALS_OK = {TRIALS_OK})")
    NUM["pick_trials"] = dict(ok=int(ok), n=9)


if __name__ == "__main__":
    what = sys.argv[1:] or ["pick"]
    t0 = time.time()
    nf = OUT / "numbers.json"
    if nf.exists():
        NUM.update(json.loads(nf.read_text()))
    for w in what:
        {"pick": pick_video, "trials": trials}[w]()
    OUT.mkdir(parents=True, exist_ok=True)
    NUM["_env"] = dict(mujoco=mujoco.__version__, scene=SCENE)
    nf.write_text(json.dumps(NUM, ensure_ascii=False, indent=1))
    print(f"(실행 {time.time() - t0:.0f} s)")
