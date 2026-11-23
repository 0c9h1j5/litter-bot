# 2026-11-23 눈 입자 시뮬 비용 실험

- 목적: 기획안 16장 '눈 치우기' 검토 — 눈을 작은 구 입자로 단순화하면 MuJoCo가 얼마나 느려지나
- 환경: MuJoCo 4.0.1, Apple M4, Python 3.14, 렌더 없음, timestep 0.002 s
- 장면: 평면 + 구 입자 한 층(격자 배치, 입자 0.5 g) + 상자 블레이드(5 kg)가 x 방향 0.3 m/s로 밂, 시뮬 2 s
- 실행: 맨 아래 코드를 `snow_bench.py`로 저장한 뒤 `uv run python snow_bench.py 0.02` (인자 = 입자 반지름 m)

## 결과

```
입자   100개 (반지름 1 cm, 덮는 면적 0.04 m²): 시뮬 2 s에 벽시계 0.10 s → 실시간의 20.35배, 접촉 194개
입자   400개 (반지름 1 cm, 덮는 면적 0.16 m²): 시뮬 2 s에 벽시계 0.44 s → 실시간의 4.56배, 접촉 728개
입자  1024개 (반지름 1 cm, 덮는 면적 0.41 m²): 시뮬 2 s에 벽시계 1.29 s → 실시간의 1.55배, 접촉 1842개
입자  2025개 (반지름 1 cm, 덮는 면적 0.81 m²): 시뮬 2 s에 벽시계 2.66 s → 실시간의 0.75배, 접촉 3843개
입자   100개 (반지름 2 cm, 덮는 면적 0.16 m²): 시뮬 2 s에 벽시계 0.11 s → 실시간의 18.77배, 접촉 204개
입자   400개 (반지름 2 cm, 덮는 면적 0.64 m²): 시뮬 2 s에 벽시계 0.47 s → 실시간의 4.25배, 접촉 804개
입자  1024개 (반지름 2 cm, 덮는 면적 1.64 m²): 시뮬 2 s에 벽시계 1.29 s → 실시간의 1.55배, 접촉 2005개
입자  2025개 (반지름 2 cm, 덮는 면적 3.24 m²): 시뮬 2 s에 벽시계 2.74 s → 실시간의 0.73배, 접촉 4057개
```

(두 번째 실행 값이라 기획안 표와 소수 둘째 자리가 조금 다를 수 있다.)

## 해석

- 입자 수에 거의 비례해 느려진다. 2,000개쯤에서 실시간보다 느려진다.
- 5 m × 5 m를 반지름 2 cm 입자 한 층으로 덮으면 약 15,600개 → 단순 비례 추정 실시간의 약 0.1배.
- 결론: 눈 시뮬은 1 m × 3 m 띠, 2,000개 이하 '맛보기'만 현실적이다.

## 코드

```python
# 눈을 작은 구 입자로 단순화했을 때 비용: 블레이드(상자)가 입자 더미를 밀 때 실시간 배속
import mujoco, time, sys, numpy as np
def build(n_side, r):
    parts=[]
    sp=2*r
    x0=-(n_side*sp)/2
    for i in range(n_side):
        for j in range(n_side):
            parts.append(f'<body pos="{x0+i*sp+0.5:.4f} {x0+j*sp:.4f} {r:.4f}"><freejoint/><geom type="sphere" size="{r}" mass="0.0005" rgba="1 1 1 1"/></body>')
    return f'''<mujoco><option timestep="0.002"/>
<worldbody><geom type="plane" size="5 5 .1"/>
<body name="blade" pos="-1.5 0 0.05"><joint name="x" type="slide" axis="1 0 0"/><geom type="box" size="0.02 {n_side*sp/2+0.1} 0.05" mass="5"/></body>
{''.join(parts)}</worldbody>
<actuator><velocity joint="x" kv="200"/></actuator></mujoco>'''
r=float(sys.argv[1]) if len(sys.argv)>1 else 0.01
for n_side in [10,20,32,45]:
    m=mujoco.MjModel.from_xml_string(build(n_side,r)); d=mujoco.MjData(m)
    d.ctrl[0]=0.3  # 0.3 m/s로 밀기
    T=2.0; steps=int(T/m.opt.timestep)
    t=time.perf_counter()
    for _ in range(steps): mujoco.mj_step(m,d)
    w=time.perf_counter()-t
    print(f"입자 {n_side*n_side:5d}개 (반지름 {r*100:.0f} cm, 덮는 면적 {(n_side*2*r)**2:.2f} m²): 시뮬 {T:.0f} s에 벽시계 {w:.2f} s → 실시간의 {T/w:.2f}배, 접촉 {d.ncon}개")
```
