# litter-bot — 체육관 정리 로봇

새싹 로보틱스 SW 운영 팀프로젝트(1인 팀, 2026-11-23 ~ 12-18). 사람 없는 빈 시간(첫 대관 전·마지막 대관 후·대관이 비는 시간)에 실내 체육관 코트·벤치 주변의 생수병·캔·컵을 로봇팔로 집고(핫스폿 순회: 벤치 → 구석 — 유일한 차별점) 마루 먼지·흙먼지·셔틀콕 깃털을 극세사 패드로 미는(직선 훑기, 주 기능) 로봇을 MuJoCo(실물과 같은 메카넘 + SO-101 모델 `robot_v2`)로 입증하고, 메카넘 차 + 청소 모듈 A(옆솔(실물은 V자 가이드로 시작)·밑 흡입·뒤 회전 패드) + 차체에 얹은 SO-ARM101 팔 축소판으로 실내 마루에서 시연한다. 실제 체육관 운행은 시설 동의·안전 확인을 전제로 한다.

**제출물 안내:**
- 1일차: 팀 차터 [docs/charter.md](docs/charter.md) (D02 v1.0, 검토) · 산출물 목록 [docs/register.md](docs/register.md) (D00 v0.7) · 저장소 https://github.com/0c9h1j5/litter-bot
- 2일차: 문제 정의서 [docs/problem.md](docs/problem.md) (D01 v2.1, 검토)
- 3일차: 요구사항 명세 [docs/requirements.md](docs/requirements.md) (D03 v0.6, 검토) · 판정 테스트 [tests/test_judge.py](tests/test_judge.py) (v0.6으로 새로 씀, 사람 몫) · 판정 함수 [src/judge.py](src/judge.py) (시그니처만, 구현은 다음 작업 — `uv run pytest -q tests` → 29개 중 28 failed `NotImplementedError`, 1 passed)

**먼저 읽기:** [기획안](docs/00-기획안.md) (발표용 페이지: [docs/00-기획안.html](docs/00-기획안.html)를 브라우저로 열기) → [한 장 요약](docs/00-기획안-요약.md) → [유저 시나리오](docs/01-유저시나리오.md) → [현장 계수표](docs/02-현장계수표.md) → [팀 차터](docs/charter.md)

## 파일 트리
규칙: README가 입구이고, `docs/`의 번호 문서(00-, 01-, 02-, …)는 읽는 순서다. 수업 제출 이름이 정해진 문서(charter.md, register.md)는 이름을 그대로 둔다.

```
litter-bot/
├── README.md                     입구 (이 파일)
├── docs/
│   ├── 00-기획안.md               P00 기획안 v1.5 (원본) — 현장: 실내 체육관
│   ├── 00-기획안-요약.md           P00 한 장 요약 (발표 첫 장)
│   ├── 00-기획안.html             P00 발표용 한 파일 페이지 (기획안 + 유저 시나리오, 이미지 포함)
│   ├── 01-유저시나리오.md          P01 관리자·대관 팀·동호인 × 지금 vs 로봇과 함께, 요구사항 R-01~R-20
│   ├── 02-현장계수표.md            P02 경기 직후 한 장 (폰으로 채우기)
│   ├── 03-현장데이터-요약.md        P03 현장 데이터 (실측 + 추정) 요약 — 자동 생성
│   ├── 04-유사제품조사.md          P04 v1.0 국내외 유사 제품 32개 · 사람이 미는 장비 비교 · 우리 차별점(겹치는 점 포함)
│   ├── charter.md                D02 팀 차터 v1.0 (검토)
│   ├── decisions.md              결정 기록 (주인 결정, 날짜·이유·출처)
│   ├── problem.md                D01 문제 정의서 v2.1 (검토) — 사용자 3인·대관 사이 흐름·불편 숫자·경쟁 사례·출처
│   ├── register.md               D00 산출물 목록 v0.7 (G1 점검표 포함)
│   ├── requirements.md           D03 요구사항 명세 v0.4 (검토) — 계층·계산·요구사항 표 R-01~R-31·단계별 요구사항·R↔T
│   ├── build_html.py             md → html 변환 (uv run --with markdown python docs/build_html.py)
│   └── img/                      그림 (MuJoCo 직접 렌더: robot_v2.png, robot_v1.png, gym_v1.png, gym_v0.png, depth_test.png, 예전 scene_v0.png · 스케치: module_a_sketch.svg · 개념 이미지(AI 생성): concept_cleaning.jpg, concept_pickup.jpg, scenario_4cut.jpg · 외형 예시: example_render.jpg, example_top.jpg(AI 생성), example_drawing.jpg(벡터 도면))
├── scenes/
│   ├── robot_v2*.xml             로봇 v2: 주인 설계 배치(앞 가운데 팔·크래들, 옆솔·밑 흡입·뒤 패드 판정 영역). 기본 robot_v2.xml = 넓은 차체 + 팔 옆에 거는 통(wide_side), 비교용 x3·x3b·wide·wide_long(묻힌 통) (scripts/build_robot_v2.py가 생성)
│   ├── gym_v2*.xml               장면 v2: gym_v0 + robot_v2 (차체 안마다 1개)
│   ├── robot_v1.xml              로봇만: 메카넘 차체(ROSMASTER X3 치수, 단순화) + 청소 모듈 A + SO-101 팔 + 옆 바구니 + 깊이 카메라 자리 (scripts/build_robot_v1.py가 생성)
│   ├── gym_v1.xml                장면 v1: gym_v0 + robot_v1
│   ├── gym_v0.xml                MuJoCo 장면 뼈대: 농구 코트 일부 5 m × 3 m + 라인·벤치·창문틀 (로봇 없음)
│   ├── sidewalk_v0.xml           예전 가게 앞 장면 (v1.1, 참고용)
│   └── assets/so101/             SO-101 MJCF·메시 (TheRobotStudio/SO-ARM100, Apache-2.0 — 출처·변경은 README.md)
├── src/
│   ├── judge.py                  D03 판정 함수 judge_full_mode / judge_bench_only / judge_ten_runs / decide_start (v0.6 시그니처만, 구현 전)
│   └── checks/                   확인용 스크립트 (장면·로봇 렌더, 메카넘+SO-101 실측, 예전 Stretch 리프트 높이, 깊이 돌출 검출)
├── scripts/
│   ├── build_robot_v2.py         robot_v2*.xml·gym_v2*.xml 생성 (차체 치수 VARIANTS)
│   ├── build_robot_v1.py         robot_v1.xml 생성 (차체 치수 CHASSIS 한 곳)
│   └── field_summary.py          현장 데이터 요약 생성 (uv run python scripts/field_summary.py)
├── tests/
│   └── test_judge.py             D03 판정 테스트 T-01~T-10·T-21·T-22·T-32~T-36 (uv run pytest -q tests)
└── logs/                         실행·실험·현장 기록
    ├── daily.md                              매일 기록 (한 일 / 막힌 일 / 할 일)
    ├── field/field_count.csv                 실측(현장 계수) — 경기 1회 = 한 줄 추가
    ├── field/field_estimate_v1.csv           현장 관찰 기반 추정 (사설·구민·학교 대표 행)
    ├── field/field_count_template.csv        현장 계수 CSV 템플릿 (예시 줄 포함)
    ├── field/2026-11-23_주인회고.md            주인 회고(체육관 약 10곳, 기억 기반) — 1차 근거
    ├── 2026-11-24_robot_v2_measurements.md   robot_v2(주인 설계) 실측: 묻힌 통에 넣기·크래들·넘어짐·차체 비교 + 요구사항 재계산
    ├── 2026-11-24_robot_v2_wide_side_pick.md  기본 차체(넓은 차체 + 팔 옆 통) 넣기 실측: 가운데 1회 성공, 9곳 0/9
    ├── 2026-11-24_mecanum_so101_measurements.md  메카넘 + SO-101 실측 (속도·팔 닿는 범위·병 집기·토크, Stretch와 비교)
    ├── 2026-11-24_chassis_candidates.md      메카넘 차체 후보 조사 (구매 후보·산업용 청소 로봇 사양, 추천)
    ├── 2026-11-22_stretch3_measurements.md   Stretch 3 모델 실측값 (속도·회전·패드 높이) — 예전 시뮬 로봇, 비교용
    ├── 2026-11-23_stretch3_lift_reach.md     Stretch 3 리프트별 그리퍼 높이 (창문틀)
    ├── 2026-11-23_depth_protrusion.md        깊이 렌더로 바닥 위 돌출물 찾기
    ├── 2026-11-23_roller_brush.md            롤러 솔 단순화 실험 (v1.1)
    └── 2026-11-23_snow_particles.md          눈 입자 시뮬 비용 실험 (v1.1)
```

## 환경 맞추기
```bash
git clone https://github.com/0c9h1j5/litter-bot.git
cd litter-bot
uv sync
uv run pytest -q tests                                       # 판정 테스트 (v0.6: 구현 전이라 28 failed · 1 passed)
uv run mjpython -m mujoco.viewer --mjcf=scenes/gym_v0.xml   # macOS
uv run python -m mujoco.viewer --mjcf=scenes/gym_v0.xml     # Windows·Linux
uv run --with pillow python src/checks/render_scene.py scenes/gym_v0.xml docs/img/gym_v0.png   # 그림 다시 만들기

# 장면 v1 (메카넘 차체 + SO-101)
uv run mjpython -m mujoco.viewer --mjcf=scenes/gym_v1.xml    # macOS (Windows·Linux는 python)
uv run mjpython -m mujoco.viewer --mjcf=scenes/robot_v1.xml  # 로봇만
uv run python scripts/build_robot_v1.py                       # 차체 치수를 바꾼 뒤 robot_v1.xml 다시 만들기
uv run python src/checks/mecanum_so101_measure.py             # 실측 (약 30 s) → logs/2026-11-24_mecanum_so101_measurements.md
uv run --with pillow python src/checks/render_robot.py robot docs/img/robot_v1.png
uv run --with pillow python src/checks/render_robot.py gym docs/img/gym_v1.png

# 로봇 v2 (주인 설계 배치)
uv run python scripts/build_robot_v2.py                       # robot_v2*.xml, gym_v2*.xml
uv run python src/checks/robot_v2_measure.py                  # 실측 (약 15분) → logs/2026-11-24_robot_v2_measurements.md
uv run --with pillow python src/checks/render_robot.py robot2 docs/img/robot_v2.png
```
