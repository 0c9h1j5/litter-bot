"""판정 함수 — D03 요구사항 명세(docs/requirements.md)의 성공 조건을 코드로 판정한다.

교안 원칙: 테스트(tests/test_judge.py)는 사람이 쓰고, 이 파일의 구현은 에이전트에게 맡긴다.
구현할 때 tests/test_judge.py는 고치지 않는다.

입력 result = 시뮬 1회(한 판) 결과 dict. 키와 단위:

    공통
      coverage_pct          float  패드가 한 번 이상 지나간 5 cm 격자 칸 비율 (%), 0~100   (R-06)
      collected             int    바구니에 넣은 집게 대상 수                               (R-04)
      targets               int    그 판의 집게 대상 수 (짧은 모드 5, 전체 모드 10), > 0     (R-04)
      base_collisions       int    베이스·몸체가 장애물에 닿은 횟수                          (R-24)
      zone_exits            int    베이스가 운행 구역 밖으로 나간 횟수                        (R-16)
      person_stop_s         list[float]  사람 대역이 앞쪽 1 m 안에 들어온 순간부터 정지까지 걸린 시간 (s),
                                   들어온 횟수만큼. 빈 리스트 = 사람 없음                   (R-09)
      forbidden_picks       int    분실물·물이 남은 병·공·가방·신발을 집은 횟수              (R-10·R-11·R-17)
      lost_items_seen       int    본 분실물(물이 남은 병 포함) 수                           (R-17)
      lost_items_photographed int  그중 사진·위치를 기록한 수                                (R-17)

    짧은 모드만
      elapsed_s             float  짧은 모드 시작부터 끝까지 시뮬 시간 (s)                   (R-18)

    전체 모드만
      mode1_elapsed_s       float  모드 1(핫스폿 순회) 시뮬 시간 (s)                         (R-26)
      mode2_elapsed_s       float  모드 2(직선 훑기) 시뮬 시간 (s)                           (R-26)

기준값 (docs/requirements.md ②, 기획안 11장. 12/01 재조정 폭 안에서 바뀔 수 있음):
    수거율 80% 이상(>=), 커버리지 95% 이상(>=), 짧은 모드 360 s 이하(<=),
    모드 1 480 s 이하(<=), 모드 2 600 s 이하(<=), 충돌 0, 구역 밖 0,
    사람 앞 정지 1.0 s 이하(<=, 모든 회), 금지 물건 집기 0, 분실물 사진 기록 100%.

한 판 판정이다. 10회 평균·최저 회 기준은 T-21(10회 집계, 예정)에서 본다.
"""


# 기준값 — 바뀌면 여기만 고친다 (경계 포함 방향은 명세 문장 그대로).
COLLECTION_MIN_PCT = 80      # R-04 수거율 80% 이상
COVERAGE_MIN_PCT = 95.0      # R-06 커버리지 95% 이상
SHORT_MAX_S = 360.0          # R-18 짧은 모드 360 s 이하
MODE1_MAX_S = 480.0          # R-26 모드 1 480 s 이하
MODE2_MAX_S = 600.0          # R-26 모드 2 600 s 이하
PERSON_STOP_MAX_S = 1.0      # R-09 사람 앞 정지 1.0 s 이하 (모든 회)


def _collection_ok(result: dict) -> bool:
    """R-04: 개수가 아니라 비율로 본다. 부동소수점 오차를 피하려고 정수끼리 비교한다."""
    targets = result["targets"]
    if targets <= 0:
        raise ValueError("targets는 0보다 커야 한다")
    return result["collected"] * 100 >= COLLECTION_MIN_PCT * targets


def _coverage_ok(result: dict) -> bool:
    """R-06: 커버리지 95% 이상."""
    return result["coverage_pct"] >= COVERAGE_MIN_PCT


def _safety_ok(result: dict) -> bool:
    """R-24 충돌 0, R-16 구역 밖 0, R-09 사람 앞 정지 매번 1.0 s 이하."""
    return (
        result["base_collisions"] == 0
        and result["zone_exits"] == 0
        and all(t <= PERSON_STOP_MAX_S for t in result["person_stop_s"])
    )


def _lost_items_ok(result: dict) -> bool:
    """R-10·R-11·R-17 금지 물건 집기 0, R-17 본 분실물 사진·위치 기록 100%."""
    return (
        result["forbidden_picks"] == 0
        and result["lost_items_photographed"] >= result["lost_items_seen"]
    )


def _common_ok(result: dict) -> bool:
    return (
        _collection_ok(result)
        and _coverage_ok(result)
        and _safety_ok(result)
        and _lost_items_ok(result)
    )


def judge_short_mode(result: dict) -> bool:
    """짧은 모드 한 판이 성공인지 판정한다.

    R-04(수거율 80% 이상), R-06(커버리지 95% 이상), R-18(360 s 이하)과
    안전·분실물 조건(R-09, R-10, R-11, R-16, R-17, R-24)을 모두 지키면 True.
    """
    return _common_ok(result) and result["elapsed_s"] <= SHORT_MAX_S


def judge_full_mode(result: dict) -> bool:
    """전체 모드 한 판이 성공인지 판정한다.

    R-04(수거율 80% 이상), R-06(커버리지 95% 이상), R-26(모드 1 480 s 이하, 모드 2 600 s 이하)과
    안전·분실물 조건(R-09, R-10, R-11, R-16, R-17, R-24)을 모두 지키면 True.
    """
    return (
        _common_ok(result)
        and result["mode1_elapsed_s"] <= MODE1_MAX_S
        and result["mode2_elapsed_s"] <= MODE2_MAX_S
    )
