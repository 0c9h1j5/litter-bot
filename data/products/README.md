# 제품 사양 DB (`specs.csv`)

상용 청소 로봇·사람 장비의 사양을 한 행 = 한 제품으로 모은 표. 우리 로봇 파라미터(`config/robot_params.yaml`)의 근거이고, 분석은 [docs/05-제품파라미터-분석.md](../../docs/05-제품파라미터-분석.md) (P05).

- **원본은 `specs.csv`** (손으로 고친다). `specs.json`은 `uv run python scripts/product_db.py`가 만든다(같은 내용, 숫자는 숫자로, 범위 "3-5"는 [3, 5]).
- **규칙:** 페이지에서 직접 확인한 값만 적는다. 업체 표시값은 비고에 '업체 주장', 단위를 바꾸거나 곱한 값은 '계산'. 못 찾으면 빈칸(지어내지 않음). 같은 페이지 안에서 엇갈리는 값은 비고에 둘 다 적는다.
- 확인 날짜 2026-11-24. 출처는 `source_url` 칸(여러 개면 ` ; `로 나눔). 출처 번호는 [P04](../../docs/04-유사제품조사.md)와 같은 페이지를 다시 열어 본 것이다.

## 칸

| 칸 | 뜻 · 단위 |
| --- | --- |
| id | 제품 키 (yaml `source`에서 씀) |
| name, company, country | 이름, 회사(제조 / 국내 유통), 나라 |
| type | 건식 / 습식 / 겸용(건·습식 모드 둘 다) / 팔(바닥 물건 집는 팔) / 사람(사람이 미는 장비) |
| length_mm, width_mm, height_mm, weight_kg | 크기 mm, 무게 kg (배터리 포함 여부는 비고) |
| max_speed_mps, work_speed_mps | 최고 속도, 작업 속도 m/s (km/h·m/min은 m/s로 바꿈 = 계산) |
| clean_width_mm | 청소 폭 mm (옆솔 포함 여부는 비고) |
| area_claimed_m2h, area_claimed_label | 업체 표시 시간당 면적과 그 구분(최대 / 이론 최대 / 표시(구분 없음) …) |
| area_practical_m2h | 업체가 '실제·practical·estimated actual'이라고 적은 시간당 면적 |
| suction_kpa | 흡입력 kPa (Pa는 ÷1000) |
| side_brushes, main_brush, dust_mop | 옆솔 수, 메인(롤러) 솔 ○, 먼지 걸레·물걸레 ○ |
| dustbin_l | 먼지통·먼지봉투 L |
| battery_v, battery_ah, battery_wh, runtime_h, charge_h | 배터리 V·Ah·Wh(V×Ah = 계산), 연속 작동 h, 충전 h |
| min_pass_mm, threshold_mm | 최소 통과 폭 mm, 넘을 수 있는 턱 mm |
| sensor_lidar … sensor_cliff | 라이다 / 깊이(3D) 카메라 / RGB 카메라 / 범퍼(충돌 감지) / 낙하 센서 — 페이지에 적혀 있으면 ○, 없으면 빈칸 |
| noise_db | 소음 dB |
| price_value, price_currency, price_date, price_kind | 가격, 통화, 확인 시점, 구매/렌탈 |
| arm_payload_g, arm_dof | 팔 하중 g, 자유도 |
| gym_case | 체육관 사례 ○ / 모름 / ✕ (P04 기준) |
| source_url, checked_date, note | 출처, 확인 날짜, 비고 |
