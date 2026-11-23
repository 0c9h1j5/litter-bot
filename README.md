# litter-bot — 체육관 정리 로봇

새싹 로보틱스 SW 운영 팀프로젝트(1인 팀, 2026-11-23 ~ 12-18). 대관과 대관 사이 실내 체육관에서, 코트·벤치 주변의 생수병·캔·컵을 집고(핫스폿 순회: 벤치 → 구석 → 창문틀) 마루 먼지를 극세사 패드로 미는(직선 훑기) 로봇을 MuJoCo(Hello Robot Stretch 3)로 입증하고, 메카넘 차 + 3D 프린트 집게 + 모터 없는 패드 축소판으로 실내 마루에서 시연한다. 실제 체육관 운행은 시설 동의·안전 확인을 전제로 한다.

**먼저 읽기:** [기획안](docs/00-기획안.md) (발표용 페이지: [docs/00-기획안.html](docs/00-기획안.html)를 브라우저로 열기) → [한 장 요약](docs/00-기획안-요약.md) → [유저 시나리오](docs/01-유저시나리오.md) → [현장 계수표](docs/02-현장계수표.md) → [팀 차터](docs/charter.md)

## 파일 트리
규칙: README가 입구이고, `docs/`의 번호 문서(00-, 01-, 02-, …)는 읽는 순서다. 수업 제출 이름이 정해진 문서(charter.md, register.md)는 이름을 그대로 둔다.

```
litter-bot/
├── README.md                     입구 (이 파일)
├── docs/
│   ├── 00-기획안.md               P00 기획안 v1.2 (원본) — 현장: 실내 체육관
│   ├── 00-기획안-요약.md           P00 한 장 요약 (발표 첫 장)
│   ├── 00-기획안.html             P00 발표용 한 파일 페이지 (기획안 + 유저 시나리오, 이미지 포함)
│   ├── 01-유저시나리오.md          P01 관리자·대관 팀·동호인 × 지금 vs 로봇과 함께, 요구사항 R-01~R-16
│   ├── 02-현장계수표.md            P02 경기 직후 한 장 (폰으로 채우기)
│   ├── charter.md                D02 팀 차터 v0.3
│   ├── register.md               D00 산출물 목록
│   ├── build_html.py             md → html 변환 (uv run --with markdown python docs/build_html.py)
│   └── img/                      그림 (MuJoCo 직접 렌더: gym_v0.png, depth_test.png, 예전 scene_v0.png)
├── scenes/
│   ├── gym_v0.xml                MuJoCo 장면 뼈대: 농구 코트 일부 5 m × 3 m + 라인·벤치·창문틀 (4일차에 장면 v1: + Stretch 3)
│   └── sidewalk_v0.xml           예전 가게 앞 장면 (v1.1, 참고용)
├── src/
│   └── checks/                   확인용 스크립트 (장면 렌더, Stretch 리프트 높이, 깊이 돌출 검출)
├── tests/                        테스트 (3일차 판정 테스트부터)
└── logs/                         실행·실험·현장 기록
    ├── field/field_count_template.csv        현장 계수 CSV 템플릿 (경기 1회 = 한 줄)
    ├── 2026-11-22_stretch3_measurements.md   Stretch 3 모델 실측값 (속도·회전·패드 높이)
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
uv run mjpython -m mujoco.viewer --mjcf=scenes/gym_v0.xml   # macOS
uv run python -m mujoco.viewer --mjcf=scenes/gym_v0.xml     # Windows·Linux
uv run --with pillow python src/checks/render_scene.py scenes/gym_v0.xml docs/img/gym_v0.png   # 그림 다시 만들기
```
