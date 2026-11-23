# 2026-11-23 롤러 솔 단순화 실험

- 목적: 기획안 6-5 '회전 솔' — MuJoCo에서 솔을 '강체 회전 원기둥 + 마찰'로 흉내 내면 꽁초·전단지 조각이 쓸려 들어가나
- 환경: MuJoCo 4.0.1, Apple M4, timestep 0.001 s, elliptic cone
- 장면: 차체가 0.1 m/s로 직진(16 s). 앞에 롤러(지름 4 cm, 폭 20 cm, 아랫면이 차 쪽으로 감기게 회전), 뒤에 경사판(약 26°) + 통. 일렬로 놓은 표적 10개
  - 꽁초: 캡슐 ø8 × 25 mm, 0.5 g / 전단지 조각: 판 40 × 40 × 1 mm, 0.8 g
- 판정: 끝났을 때 통 영역 안 / 차 밑으로 지나감 / 나머지(앞으로 밀림 등)
- 첫 시도는 롤러 관절이 발산(NaN)해 무효. 관절 armature 0.001·속도 이득 0.05로 고친 뒤 무작위 시드 3개로 돌림

## 결과 (시드 0, 1, 2)

```
# seed 0
butt  바닥 간격 2 mm: 통 안 1/10, 차 밑으로 지나감 1/10, 나머지(앞으로 밀림 등) 8/10
butt  바닥 간격 5 mm: 통 안 1/10, 차 밑으로 지나감 0/10, 나머지(앞으로 밀림 등) 9/10
flyer 바닥 간격 2 mm: 통 안 0/10, 차 밑으로 지나감 2/10, 나머지(앞으로 밀림 등) 8/10
flyer 바닥 간격 5 mm: 통 안 0/10, 차 밑으로 지나감 2/10, 나머지(앞으로 밀림 등) 8/10
# seed 1
butt  바닥 간격 2 mm: 통 안 1/10, 차 밑으로 지나감 0/10, 나머지(앞으로 밀림 등) 9/10
butt  바닥 간격 5 mm: 통 안 3/10, 차 밑으로 지나감 0/10, 나머지(앞으로 밀림 등) 7/10
flyer 바닥 간격 2 mm: 통 안 0/10, 차 밑으로 지나감 3/10, 나머지(앞으로 밀림 등) 7/10
flyer 바닥 간격 5 mm: 통 안 0/10, 차 밑으로 지나감 1/10, 나머지(앞으로 밀림 등) 9/10
# seed 2
butt  바닥 간격 2 mm: 통 안 0/10, 차 밑으로 지나감 0/10, 나머지(앞으로 밀림 등) 10/10
butt  바닥 간격 5 mm: 통 안 2/10, 차 밑으로 지나감 0/10, 나머지(앞으로 밀림 등) 8/10
flyer 바닥 간격 2 mm: 통 안 0/10, 차 밑으로 지나감 2/10, 나머지(앞으로 밀림 등) 8/10
flyer 바닥 간격 5 mm: 통 안 0/10, 차 밑으로 지나감 2/10, 나머지(앞으로 밀림 등) 8/10
```

## 해석

- 강체 롤러는 꽁초를 **통에 0~3개/10개**만 넣고 대부분 앞으로 밀어냈다. 전단지 조각은 **0개/10개**다.
- 진짜 솔은 털이 휘어 물체를 감싸 쓸어 올린다. 강체 원기둥은 그것을 흉내 내지 못하고, 맞추려면 접촉 파라미터 튜닝이 길어진다.
- 결론: 시뮬은 '수거 영역(솔 입 앞 상자 안에 들어온 작은 쓰레기는 수거로 본다)'으로 단순화하고, 솔이 실제로 쓸어 담는지는 **실물 벤치 시험**으로 확인한다(기획안 6-5).

## 코드

```python
# 롤러 솔 단순화 비교: (1) 강체 회전 원기둥 + 마찰 (2) 수거 영역(입에 들어오면 수거)
# 차체는 x로 0.1 m/s 직진(slide), 앞에 롤러(지름 4 cm, 폭 20 cm), 뒤에 경사판 + 통
import mujoco, numpy as np, sys
rng=np.random.default_rng(int(sys.argv[1]) if len(sys.argv)>1 else 0)
def scene(kind, n=10, gap=0.003, spin=-30.0, fr=1.5):
    items=[]
    for i in range(n):
        x=0.3+i*0.12; y=rng.uniform(-0.07,0.07); yaw=rng.uniform(0,np.pi)
        if kind=='butt':
            items.append(f'<body name="it{i}" pos="{x} {y} 0.004" euler="0 1.5708 {yaw}"><freejoint/><geom type="capsule" size="0.004 0.0085" mass="0.0005" friction="{fr} 0.01 0.001"/></body>')
        else: # 전단지 조각: 얇은 판 4x4 cm, 두께 1 mm
            items.append(f'<body name="it{i}" pos="{x} {y} 0.0006" euler="0 0 {yaw}"><freejoint/><geom type="box" size="0.02 0.02 0.0005" mass="0.0008" friction="{fr} 0.01 0.001"/></body>')
    r=0.02
    return f'''<mujoco><option timestep="0.001" cone="elliptic" impratio="5"/>
<worldbody><geom type="plane" size="3 3 .1" friction="0.6 0.01 0.001"/>
<body name="car" pos="0 0 0"><joint name="x" type="slide" axis="1 0 0"/>
  <geom type="box" pos="-0.12 0 0.08" size="0.1 0.12 0.02" mass="2" contype="0" conaffinity="0"/>
  <body name="roller" pos="0.0 0 {r+gap}"><joint name="spin" type="hinge" axis="0 1 0" armature="0.001" damping="0.0005"/>
    <geom type="cylinder" size="{r} 0.1" euler="1.5708 0 0" mass="0.05" friction="{fr} 0.01 0.001"/></body>
  <geom name="ramp" type="box" pos="-0.045 0 0.012" euler="0 -0.45 0" size="0.03 0.1 0.001" friction="0.3 0.01 0.001"/>
  <geom type="box" pos="-0.13 0 0.002" size="0.06 0.1 0.002" contype="0" conaffinity="0" rgba="0 1 0 .3"/>
  <geom type="box" pos="-0.19 0 0.04" size="0.002 0.1 0.04"/>
  <geom type="box" pos="-0.13 0.102 0.04" size="0.06 0.002 0.04"/><geom type="box" pos="-0.13 -0.102 0.04" size="0.06 0.002 0.04"/>
  <geom type="box" pos="-0.13 0 0.03" size="0.06 0.1 0.002"/>
</body>
{''.join(items)}</worldbody>
<actuator><velocity joint="x" kv="500"/><velocity joint="spin" kv="0.05"/></actuator></mujoco>'''
for kind in ['butt','flyer']:
  for gap in [0.002,0.005]:
    m=mujoco.MjModel.from_xml_string(scene(kind,gap=gap)); d=mujoco.MjData(m)
    d.ctrl[0]=0.1; d.ctrl[1]=-40  # 롤러 아랫면이 뒤로(차 쪽으로) 감기는 방향
    car=m.body('car').id
    for _ in range(int(16/m.opt.timestep)): mujoco.mj_step(m,d)
    cx=d.xpos[car][0]
    got=0; passed=0
    for i in range(10):
        p=d.body(f'it{i}').xpos
        rel=p[0]-cx
        if -0.19<rel<-0.07 and abs(p[1])<0.1 and p[2]>0.004: got+=1
        elif rel<-0.2: passed+=1
    print(f"{kind:5s} 바닥 간격 {gap*1000:.0f} mm: 통 안 {got}/10, 차 밑으로 지나감 {passed}/10, 나머지(앞으로 밀림 등) {10-got-passed}/10")
```
