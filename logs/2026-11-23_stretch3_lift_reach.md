# 2026-11-23 Stretch 3 리프트 높이 실측 (창문틀에 닿나)

기획안 v1.2의 '바닥 + 창문틀' 판단 근거. 주인 관찰(2026-11-23): 체육관 쓰레기는 벤치 쪽·구석·창문틀에 많이 남는다.

- 환경: MuJoCo 4.0.1, MuJoCo Menagerie 커밋 `370c439` (`hello_robot_stretch_3/scene.xml`, 예전 실측과 같은 커밋), macOS
- 방법: `joint_lift`와 `joint_wrist_pitch` 값을 qpos에 넣고 `mj_forward`(물리 스텝 없음). 그리퍼·손가락 body에 붙은 geom 중심의 z 최소/최대를 읽었다.

| 리프트 (`joint_lift`) | 손목 | 그리퍼 geom 중심 높이 (최소 / 최대) |
| --- | --- | --- |
| 0.0 m | 수평 (pitch 0) | 0.114 / 0.132 m |
| 0.5 m | 수평 | 0.614 / 0.632 m |
| 1.1 m (최대) | 수평 | 1.214 / 1.232 m |
| 1.1 m | 아래로 (pitch -1.57) | 1.002 / 1.199 m |

- 모델 XML의 리프트 관절 범위는 `range="0.0 1.1"`(m)이다. 손목이 수평이면 그리퍼 높이 ≈ 리프트 + 약 0.12 m.
- 그래서 **모델 기준 그리퍼 중심은 바닥 근처(손목을 아래로 하면 약 1~2 cm, 2026-11-22 실측)부터 약 1.22 m까지** 간다. 창문틀 윗면이 1.0 m(가정)라면 높이 6 cm짜리 캔의 중심(약 1.06 m)을 리프트 약 0.94 m로 잡을 수 있다. 다만 손목을 아래로 꺾으면(pitch -1.57) 그리퍼가 위로 약 0.1 m 짧아진다. 생수병(높이 21 cm)의 중심을 그리퍼 최고 높이(약 1.22 m) 안에서 잡으려면 **창문틀 윗면이 약 1.1 m 이하**여야 한다 → 기획안 K-7 기준.
- 팔은 로봇 오른쪽(-y)으로 0.42~0.94 m(로봇 중심 기준)에 닿는다. 창문틀 깊이 0.20 m(가정)이면 로봇을 벽과 나란히 세우고 팔을 벽 쪽으로 뻗는다.
- 실제 Stretch 3 하드웨어의 리프트 범위는 공식 문서에서 찾지 못했다(확인 필요). 공식 하드웨어 가이드에서 확인한 것은 팔 길이 0.52 m, 권장 가반하중 2 kg뿐이다: https://docs-arch.hello-robot.com/0.3/hardware/hardware_guide_stretch_3/ (참고: 후속 모델 Stretch 4 데이터시트는 리프트 120 cm라고 적는다 — 다른 모델이라 쓰지 않는다)
- 물리 스텝 없이 잰 값이라 접촉·처짐은 반영하지 않았다. 4일차 장면 v1에서 실제로 창문틀 위 캔을 잡아 다시 확인한다.

재현: `uv run python src/checks/stretch_lift.py mujoco_menagerie/hello_robot_stretch_3/scene.xml` (Menagerie를 따로 받은 뒤). 핵심 부분:

```python
import mujoco
m = mujoco.MjModel.from_xml_path("mujoco_menagerie/hello_robot_stretch_3/scene.xml"); d = mujoco.MjData(m)
q = lambda n, v: d.qpos.__setitem__(m.jnt_qposadr[m.joint(n).id], v)
q("joint_lift", 1.1); q("joint_wrist_pitch", 0.0); mujoco.mj_forward(m, d)
print(max(d.geom_xpos[g][2] for g in range(m.ngeom) if "finger" in m.body(m.geom_bodyid[g]).name or "gripper" in m.body(m.geom_bodyid[g]).name))
```
