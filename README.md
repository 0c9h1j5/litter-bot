# litter-bot — 가게 앞 청소로봇

새싹 로보틱스 SW 운영 팀프로젝트(1인 팀, 2026-11-23 ~ 12-18). 영업 전 아침, 가게 앞 평평한 보도를 직선 줄로 훑으며 팔이 닿는 컵·캔·페트병 같은 큰 쓰레기를 집는 로봇을 MuJoCo(Hello Robot Stretch 3)로 입증하고, 메카넘 차 + 3D 프린트 집게 축소판으로 실내에서 시연한다. 꽁초용 회전 솔은 다음 단계다.

**먼저 읽기:** [기획안](docs/00-기획안.md) (발표용 페이지: [docs/00-기획안.html](docs/00-기획안.html)를 브라우저로 열기) → [유저 시나리오](docs/01-유저시나리오.md) → [팀 차터](docs/charter.md)

## 파일 트리
규칙: README가 입구이고, `docs/`의 번호 문서(00-, 01-, …)는 읽는 순서다. 수업 제출 이름이 정해진 문서(charter.md, register.md)는 이름을 그대로 둔다.

```
litter-bot/
├── README.md                     입구 (이 파일)
├── docs/
│   ├── 00-기획안.md               P00 기획안 (원본)
│   ├── 00-기획안-요약.md           P00 한 장 요약 (발표 첫 장)
│   ├── 00-기획안.html             P00 발표용 한 파일 페이지 (기획안 + 유저 시나리오, 이미지 포함)
│   ├── 01-유저시나리오.md          P01 페르소나 2명 × 지금 vs 로봇과 함께, 요구사항 R-01~R-16
│   ├── charter.md                D02 팀 차터 v0.2
│   ├── register.md               D00 산출물 목록
│   ├── build_html.py             md → html 변환 (uv run --with markdown python docs/build_html.py)
│   └── img/                      그림 (MuJoCo 직접 렌더)
├── scenes/sidewalk_v0.xml        MuJoCo 장면 뼈대 (4일차에 장면 v1: 5 m × 3 m + Stretch 3)
├── src/                          로봇 프로그램 (04 스테이지부터)
├── tests/                        테스트 (3일차 판정 테스트부터)
└── logs/                         실행·실험 기록
    ├── 2026-11-22_stretch3_measurements.md   Stretch 3 모델 실측값
    ├── 2026-11-23_roller_brush.md            롤러 솔 단순화 실험
    └── 2026-11-23_snow_particles.md          눈 입자 시뮬 비용 실험
```

## 환경 맞추기
```bash
git clone https://github.com/0c9h1j5/litter-bot.git
cd litter-bot
uv sync
uv run mjpython -m mujoco.viewer --mjcf=scenes/sidewalk_v0.xml   # macOS
uv run python -m mujoco.viewer --mjcf=scenes/sidewalk_v0.xml     # Windows·Linux
```
