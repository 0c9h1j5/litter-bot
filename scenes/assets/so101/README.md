# SO-101(SO-ARM101) MuJoCo 모델 — 출처와 변경

- **출처:** TheRobotStudio/SO-ARM100 저장소 `Simulation/SO101/` — https://github.com/TheRobotStudio/SO-ARM100
  - 받은 커밋: `141aea7bcac2744d92998e30268c413202a56f96` (2026-11-20), 받은 날 2026-11-24
  - 라이선스: Apache-2.0 → 같은 폴더의 `LICENSE` (원문 그대로)
  - 원본 README의 설명: onshape-to-robot으로 Onshape CAD에서 만든 파일, 서보(STS3215) 값은 Open Duck Mini 프로젝트에서 가져옴
- **넣은 것:** `so101_new_calib.xml`(원본 그대로) + 그 파일이 쓰는 메시 13개(`assets/*.stl`, 약 15 MB). URDF·leader 팔·`.part` 파일·카메라판은 넣지 않았다.
- **바꾼 것:** `so101_new_calib_litterbot.xml` (Apache-2.0 §4: 바꾼 파일에 바꾼 사실을 적음). `scripts/build_robot_v1.py`가 원본에서 만든다.
  - 고정 집게 부품(`wrist_roll_follower_so101_v1`)의 **충돌 형상만** 메시 → 상자 2개(손가락, 손바닥).
    MuJoCo는 메시 충돌을 볼록 껍질로 계산하는데, 이 부품은 서보 몸통과 고정 손가락이 한 메시라 껍질이 두 손가락 사이를 메운다(꼭짓점을 gripperframe 좌표로 옮겨 확인: 손가락 쪽 x > −0.07 m에서 껍질 윗면이 z 0.038 m까지 올라옴). 상자 치수는 그 꼭짓점 범위에서 잡았다.
  - 집게 두 면에 `condim="4"`(비틀림 마찰), 마찰 1.0(MuJoCo 기본값 그대로, 실물 PLA 집게는 더 낮을 수 있음 — 확인 필요).
  - 관절·질량·관성·액추에이터(kp 998.22, forcerange ±3.35 N·m)는 원본 그대로.

## new calib을 쓴 이유 (old calib이 아니라)

| | new calib (`so101_new_calib.xml`) | old calib (`so101_old_calib.xml`) |
| --- | --- | --- |
| 관절 0 | 각 관절 범위의 **가운데** | 팔을 **수평으로 쭉 편** 자세 |
| 원본 README | 기본값(Default), `scene.xml`이 이 파일을 씀 | 바꿔 쓸 수 있음 |
| LeRobot 보정 | LeRobot의 지금 보정 방식과 같은 0 (원본 README) | 예전 방식 |
| 위치 제어 이득 | kp 998.22, kv 2.731 (서보 P 이득 16을 가정해 계산했다는 주석) | kp 17.8 (근거 주석 없음) |

→ 실물 팔(LeRobot으로 보정)과 관절 0을 맞추고, 주석이 있는 이득을 쓰려고 **new calib**을 골랐다. 28차시 `so101_토크.py`는 '0 = 수평으로 쭉 편 자세'가 편해서 old calib을 썼는데, 여기서는 new calib에서 같은 자세를 IK로 찾아(손끝 0.409 m) 같은 방식으로 토크를 잰다(`src/checks/mecanum_so101_measure.py torque`).
