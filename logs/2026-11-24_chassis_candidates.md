# 2026-11-24 메카넘 차체 후보 조사 (실물 구매 후보 A + 제품 개념 숫자 B)

주인 결정(2026-11-24): "메카넘은 산업용 청소 로봇 차체, 또는 국내에서 판매 중인 비슷한 제품으로 가 보자." → 시뮬 차체를 지어낸 가정값이 아니라 **실제 제품 사양**에 맞춘다. 구매는 주인 결정이라 사지 않았다.

- 조사한 날: 2026-11-24 (웹 검색 + 판매·제조사 페이지 열람). 일부 페이지(Yahboom 공식몰, Hiwonder, AgileX 제품 페이지)는 요청 제한(HTTP 429)으로 열지 못했다 → 그 값은 검색 결과 요약이나 다른 판매처 값이고 '확인 필요'로 적었다.
- 가격은 페이지에 적힌 값 그대로다. 원화로 바꾸지 않았다(환율·배송·관세 확인 필요).

## A. 실물로 살 수 있는 메카넘(옴니) 이동 로봇 플랫폼

| 후보 | 판매처·가격 (본 날) | 크기 | 질량 | 최고 속도 | 탑재 하중 | 배터리·전압 | URDF/MJCF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Yahboom ROSMASTER X3** (메카넘, 알루미늄 차체, 520 모터) | RobotShop **889.00 USD** (Superior, Orin 보드 없음, 페이지 데이터 2026-10-14) [A1] · e-smartway 할인가 729.68 USD(구성 확인 필요) [A2] · **국내 판매처 못 찾음** | 300 × 199.4 mm(바퀴 포함), 바퀴 반지름 32.5 mm — **커뮤니티 URDF 값** [A3] (공식 치수표 못 찾음) | 판매처 표기 4.23 kg(포장 포함인지 확인 필요) [A4] · URDF base_mass 4.6 kg [A3] | 1.0 m/s (판매처 Q&A, 확인 필요) [A4] | 못 찾음 | 못 찾음 | 공식 못 찾음. **커뮤니티 ROS 2 패키지(BSD-3)** automaticaddison/yahboom_rosmaster에 X3 xacro·메시 있음 [A3] (바퀴는 원기둥 단순화, 롤러 없음, 바퀴 질량 9.1 kg은 비현실적이라 쓰지 않음) |
| AgileX LIMO (차동·애커만·궤도·메카넘 4모드) | 스페인 판매처 2,895 USD, 프랑스 판매처 2,371.20 EUR(부가세 포함으로 보임), 미국은 문의 [A5] · 국내 못 찾음 | 322 × 215 × 247 mm [A6] | 4.2 kg [A6] | LIMO Pro 판매처 1 m/s (모델·모드 확인 필요) [A5] | 판매처마다 4~4.8 kg (확인 필요) [A5] | 12V Li-ion 5600 mAh, 40분 [A6] | 공식 limo_ros(BSD-3)·limo_ros2에 URDF 있음, **메카넘 파일은 없음**(ackerman, four_diff만) [A7] |
| Hiwonder MentorPi M1 (메카넘, 알루미늄) | 가격 못 봄(페이지 429) | 212 × 171 × 147 mm [A8] | 1.2 kg [A8] | 못 찾음 | 못 찾음 | 7.4V 2200 mAh LiPo, 310 모터 4개 [A8] | 못 찾음 |
| Adeept 4WD 메카넘 키트 (라즈베리 파이 피코용) | **아이씨뱅큐 129,200원(VAT 별도) / 142,120원(VAT 포함)** [A9] | 페이지 텍스트에 없음 | 없음 | 없음 | 없음 | 없음 | 없음 |
| 자작 (메카넘 바퀴 단품 + 프로파일) | 디바이스마트 DFRobot 80 mm 휠 7,900원(VAT 별도, 한쪽) [A10] · 로보로보 메카넘 휠 세트 25,000원 [A11] · 로보블럭 100 mm 세트 330,000원(VAT 포함) [A10] | 자유 | 자유 | 모터에 따라 | 모터에 따라 | 자유 (팔과 같은 12V 가능) | 직접 작성 (지금 시뮬 모델 그대로 쓰면 됨) |

## B. 산업용 실내 청소 로봇 (국내 판매·유통) — '제품 개념 기준 숫자'로만

값이 수천만 원이라 4주 실물로는 살 수 없다. 기획안 7장 '제품 개념'(패드 폭 1.0 m × 0.5 m/s)을 실제 제품 숫자와 비교하는 데 쓴다. **바퀴 방식은 어느 제품도 페이지에 없었다**(메카넘인지 확인 못 함).

| 제품 | 크기 (L × W × H) | 질량 | 최고 속도 | 청소 폭 | 가격 | 출처 |
| --- | --- | --- | --- | --- | --- | --- |
| Gausium Phantas | 590 × 455 × 620 mm | 65 kg | 사양표에 없음 | 흡입·쓸기 465 mm, 먼지 걸레 330 mm | 국내 매물 **25,000,000원(VAT 별도)**, 리스 월 574,000원(36개월) | [B1][B2] |
| Gausium Scrubber 50 | 810 × 700 × 1,070 mm | 148~157 kg | 1.2 m/s (청소 속도) | 406~460 mm (사이드 브러시 포함 780) | 못 찾음 | [B3] |
| Gausium Scrubber 75 | 1,370 × 962 × 1,417 mm | 400 kg | 1.1 m/s | 750 mm | 견적 문의 | [B4] |
| 휠리 J30 (라이노스) | 39 × 39 × 35 cm | 28 kg | 0.3 m/s | 흡입 26.5 cm (롤러 17, 사이드 브러시 36.8) | 없음 (도입 상담) | [B5] |
| 휠리 C30 (라이노스) | 49 × 52 × 75 cm | 35 kg (배터리 포함) | 0.8 m/s | 61 cm | 없음 (도입 상담) | [B6] |
| 클로봇 청소 로봇 | 사양이 이미지라 텍스트로 확인 못 함 (코디네이터 메모: 체육관 도입 사례 있음) | | | | | [B7] |
| (참고) SoftBank Whiz, 딥블루 Baby-Orca | 비교 페이지 요약에 2,500만 원 / 3,000만 원 — 원문 확인 못 함 (확인 필요) | | | | | [B8] |

→ 실제 제품의 청소 폭은 0.27~0.78 m, 속도는 0.3~1.2 m/s다. 기획안 7장의 '패드 폭 1.0 m'는 조사한 어느 제품보다 넓다 → 재계산 필요 목록에 넣었다.

## 추천 (판단 기준: SO-ARM101 0.6~0.8 kg·12V와 청소 모듈을 싣나 / 마루 긁힘 / 4주·예산 26만~48만 원 / URDF)

| 기준 | ROSMASTER X3 | LIMO | MentorPi M1 | Adeept 키트 | 자작 |
| --- | --- | --- | --- | --- | --- |
| 팔+청소기 싣기 | 알루미늄, 차체 4 kg급 — 넘어짐 여유 충분(시뮬 46~50 mm) | 4.2 kg, 하중 4 kg급(확인 필요) | **1.2 kg — 시뮬 계산상 팔·병 말고 1.23 kg 이상 필요** → 청소기를 함께 실으면 겨우 넘음, 여유 작음 | 크기·하중 모름 (확인 필요) | 설계하기 나름 |
| 전원 | 모름 (확인 필요) | 12V (팔과 같은 전압) | 7.4V (팔 12V 따로) | 모름 | 12V로 맞출 수 있음 |
| 마루 긁힘 | 바퀴 재질 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 고무 롤러 바퀴를 골라 살 수 있음 |
| 예산 (기획안 9장 차체 0~10만 원대) | **초과** (889 USD + 배송·관세) | **크게 초과** (약 2,900 USD) | 모름 | 안 (14만 원) | 바퀴 2.5만~33만 원 + 모터·드라이버 |
| URDF | 커뮤니티 xacro(치수만 믿을 만함) | 공식, 단 메카넘 없음 | 못 찾음 | 없음 | 지금 시뮬 모델 |

**추천: 시뮬 기준 차체 = Yahboom ROSMASTER X3.** 치수가 공개(커뮤니티 URDF)된 메카넘 후보 중 기획안의 차체 폭 약 0.20 m와 거의 같고(199.4 mm), 알루미늄 차체에 4 kg급이라 SO-101을 얹어도 넘어짐 여유가 있다. 그래서 `scripts/build_robot_v1.py`의 `CHASSIS`를 X3 값으로 두었다.
**실물 구매는 주인 결정이 필요하다:** X3는 889 USD(배송·관세 별도)로 기획안 9장의 차체 예산(0~10만 원대)과 필수 합계(26만~48만 원)를 넘는다. 예산 안에서는 Adeept 키트(142,120원, VAT 포함)뿐인데 크기·하중이 공개되지 않아 팔과 청소기를 실을 수 있는지 모른다(확인 필요). 세 번째 길은 고무 롤러 메카넘 바퀴로 X3 치수에 맞춰 자작하는 것이다(시뮬 모델을 그대로 쓸 수 있음).

## 출처 (본 날 2026-11-24)
- [A1] https://www.robotshop.com/products/yahboom-rosmaster-x3-ros2-robot-with-mecanum-wheel-superior-without-orin-super-board
- [A2] https://e-smartway.com/products/rosmaster-x3-ros2-robot-mecanum-wheel-aluminum-alloy-frame-autopilot-lidar-mapping-for-jetson-nano-orin-nx-orin-nano-raspberrypi (검색 결과 요약값, 페이지 직접 확인 못 함)
- [A3] https://github.com/automaticaddison/yahboom_rosmaster (커밋 `6f99244`, `yahboom_rosmaster_description/urdf/mech/rosmaster_x3_base.urdf.xacro`, `mecanum_wheel.urdf.xacro`, LICENSE = BSD 3-Clause 문구)
- [A4] https://rcdrone.top/products/yahboom-rosmaster-x3-plus-robot , 판매처 목록 (검색 결과 요약 — 최고 속도 1.0 m/s는 판매처 Q&A, 무게 4.23 kg는 판매처 표기. 어떤 구성인지 확인 필요)
- [A5] https://www.roboticscenter.ai/store/product/agilex-limo , https://www.robotlab.com/store/limo-agilex/ (검색 결과 요약)
- [A6] https://docs.trossenrobotics.com/agilex_limo_docs/specifications/limo.html
- [A7] https://github.com/agilexrobotics/limo_ros/tree/master/limo_description/urdf , https://github.com/agilexrobotics/limo_ros2/tree/humble/limo_description/urdf
- [A8] https://hiwonder.com/products/mentorpi-m1-monocular-camera-version , https://openelab.io/products/mentorpi-m1-car (검색 결과 요약, 페이지 직접 열기는 429)
- [A9] https://www.icbanq.com/P016133529
- [A10] https://www.devicemart.co.kr/goods/catalog?code=0015000300050002
- [A11] https://roboroboshop.com/product/%EB%A9%94%EC%B9%B4%EB%84%98-%ED%9C%A0-set/365/
- [B1] https://gausium.com/specs/phantas/
- [B2] https://www.daara.co.kr/sell/s_view.php?no=1027508
- [B3] https://gausium.com/specs/scrubber50/
- [B4] https://gausium.com/scrubber-75
- [B5] https://wheelie.co.kr/j30
- [B6] https://wheelie.co.kr/c30
- [B7] https://clobot.co.kr/cleaning_robot
- [B8] https://www.myrobotsolution.com/store/service?categoryId=26 (검색 결과 요약)
