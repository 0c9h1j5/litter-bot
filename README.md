# litter-bot — 쓰레기 줍는 로봇

새싹 로보틱스 SW 운영 팀프로젝트. 가게 앞 평평한 바닥의 작은 쓰레기를 이동형 로봇팔(Hello Robot Stretch 3)이 줍는 것을 MuJoCo로 입증하고, 3D 프린트 축소판 실물로 시연한다.

## 폴더
| 폴더 | 들어갈 것 |
| --- | --- |
| `scenes/` | MuJoCo 장면 XML (`sidewalk_v0.xml` 뼈대, 4일차에 장면 v0) |
| `src/` | 로봇 프로그램 (04 스테이지부터) |
| `tests/` | 테스트 (3일차 판정 테스트부터) |
| `docs/` | 산출물 문서: [charter.md](docs/charter.md), [register.md](docs/register.md) … |
| `logs/` | 실행 기록 (05 스테이지부터) |

## 환경 맞추기
```bash
git clone https://github.com/0c9h1j5/litter-bot.git
cd litter-bot
uv sync
uv run mjpython -m mujoco.viewer --mjcf=scenes/sidewalk_v0.xml   # macOS
uv run python -m mujoco.viewer --mjcf=scenes/sidewalk_v0.xml     # Windows·Linux
```
