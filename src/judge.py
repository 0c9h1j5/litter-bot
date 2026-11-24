"""판정 함수 — D03 요구사항 명세(docs/requirements.md v0.6)의 성공 조건을 코드로 판정한다.

교안 원칙: 테스트(tests/test_judge.py)는 사람이 쓰고, 이 파일의 구현은 에이전트에게 맡긴다.
구현할 때 tests/test_judge.py는 고치지 않는다.

v0.6 (주인 결정 2026-11-24): 대관 사이 '짧은 모드'를 없앴다 — judge_short_mode·SHORT_MAX_S(360 s)는 지웠다.
주 판정은 전체 모드 한 판(빈 시간 안에 장면 전체 청소 + 핫스폿 집기 + 충전 자리 복귀),
선택 기능은 관리자 버튼 '벤치만 줍기'(R-32).

입력 result = 시뮬 1회(한 판) 결과 dict. 키와 단위:

    공통 (전체 모드·벤치만 줍기)
      collected             int    통에 넣은 집게 대상 수                                      (R-04)
      targets               int    그 판의 집게 대상 수 (전체 모드 10, 벤치만 줍기 5), > 0       (R-04)
      dock_dist_m           float  끝난 위치(로봇 원점)와 충전 자리 사이 수평 거리 (m)          (R-18, R-32)
      base_collisions       int    베이스·몸체가 장애물에 닿은 횟수                              (R-24)
      zone_exits            int    베이스가 운행 구역 밖으로 나간 횟수                            (R-16)
      person_stop_s         list[float]  사람 대역이 앞쪽 1 m 안에 들어온 순간부터 정지까지 걸린 시간 (s),
                                   들어온 횟수만큼. 빈 리스트 = 사람 없음                       (R-09)
      forbidden_picks       int    분실물·물이 남은 병·공·가방·신발을 집은 횟수                  (R-10·R-11·R-17)
      lost_items_seen       int    본 분실물(물이 남은 병 포함) 수                               (R-17)
      lost_items_photographed int  그중 사진·위치를 기록한 수                                    (R-17)

    전체 모드만
      elapsed_s             float  전체 모드 시작부터 충전 자리에 돌아와 멈출 때까지 시뮬 시간 (s)  (R-18)
      mode1_elapsed_s       float  모드 1(핫스폿 순회) 시뮬 시간 (s)                             (R-26)
      mode2_elapsed_s       float  모드 2(직선 훑기) 시뮬 시간 (s)                               (R-26)
      grid_cells            int    장면 전체 5 cm 격자 칸 수 (시뮬 5 m × 3 m = 6,000)            (R-06)
      obstacle_cells        int    그중 장애물(벤치·벽 등)이 차지해 칠할 수 없는 칸 수 — 분모에서 뺌  (R-06)
      covered_cells         int    패드가 한 번 이상 지나간 칸 수 (장애물 칸 제외, 건너뛴 칸은 안 셈) (R-06)

    벤치만 줍기에는 시간·커버리지 칸이 없다 (R-32는 시간 기준을 정하지 않음, 바닥은 밀지 않음).
    dict에 다른 키가 더 있어도 무시한다.

기준값 (docs/requirements.md v0.6 ②. 12/01 재조정 폭 안에서 바뀔 수 있음):
    수거율 80% 이상(>=), 장면 커버리지 95% 이상(>=, 분모 = grid_cells − obstacle_cells),
    전체 모드 650 s 이하(<=, 주인 확정 2026-11-24, 운행 0.3 m/s 기준), 충전 자리 반경 0.1 m 이하(<=, 가정),
    모드 1 480 s 이하(<=), 모드 2 600 s 이하(<=), 충돌 0, 구역 밖 0,
    사람 앞 정지 1.0 s 이하(<=, 모든 회), 금지 물건 집기 0, 분실물 사진 기록 100%.
    10회 집계: 수거율은 회별 비율의 평균 80% 이상 + 최저 회 60% 이상, 나머지는 10회 모두 한 판 기준.

부동소수점 오차를 피하려고 비율(수거율·커버리지)은 정수끼리 곱해 비교한다
(예: collected * 100 >= 80 * targets, covered * 100 >= 95 * (grid − obstacle)).
장면 설정 오류(targets <= 0, grid_cells − obstacle_cells <= 0, 10회 집계에 10개가 아닌 결과)는 ValueError.
"""

from fractions import Fraction


# 기준값 — 바뀌면 여기만 고친다 (경계 포함 방향은 명세 문장 그대로).
COLLECTION_MIN_PCT = 80        # R-04 수거율 80% 이상 (한 판, 10회 평균)
COLLECTION_RUN_MIN_PCT = 60    # R-04 10회 중 최저 회 60% 이상
COVERAGE_MIN_PCT = 95          # R-06 장면 커버리지 95% 이상
FULL_MAX_S = 650.0             # R-18 전체 모드 + 충전 자리 복귀 650 s 이하 (주인 확정 2026-11-24)
DOCK_RADIUS_M = 0.1            # R-18·R-32 충전 자리 반경 0.1 m 안 (가정)
MODE1_MAX_S = 480.0            # R-26 모드 1 480 s 이하
MODE2_MAX_S = 600.0            # R-26 모드 2 600 s 이하
PERSON_STOP_MAX_S = 1.0        # R-09 사람 앞 정지 1.0 s 이하 (모든 회)
RUNS = 10                      # 시드 10개 10회 (기획안 11장)



def _targets(result: dict) -> tuple[int, int]:
    """수거 수·대상 수. 대상이 0개 이하면 장면 설정 오류(ValueError)."""
    targets = result["targets"]
    if targets <= 0:
        raise ValueError(f"집게 대상 수가 0 이하: targets = {targets}")
    return result["collected"], targets


def _ratio_ok(part: int, whole: int, min_pct: int) -> bool:
    """part / whole >= min_pct %  — 정수 곱으로 비교 (부동소수점 오차 없음)."""
    return part * 100 >= min_pct * whole


def _safety_ok(result: dict) -> bool:
    """안전·분실물 (R-09, R-10, R-11, R-16, R-17, R-24) — 전체 모드·벤치만 줍기 공통."""
    return (
        result["base_collisions"] == 0                                        # R-24
        and result["zone_exits"] == 0                                         # R-16
        and all(t <= PERSON_STOP_MAX_S for t in result["person_stop_s"])      # R-09 (모든 회)
        and result["forbidden_picks"] == 0                                    # R-10·R-11·R-17
        and result["lost_items_photographed"] >= result["lost_items_seen"]    # R-17 사진 100%
    )


def _full_rest_ok(result: dict) -> bool:
    """전체 모드의 수거율·커버리지 밖 조건: R-18 시간·복귀, R-26 모드별 시간, 안전·분실물."""
    return (
        result["elapsed_s"] <= FULL_MAX_S                 # R-18 시간
        and result["dock_dist_m"] <= DOCK_RADIUS_M        # R-18 복귀
        and result["mode1_elapsed_s"] <= MODE1_MAX_S      # R-26
        and result["mode2_elapsed_s"] <= MODE2_MAX_S      # R-26
        and _safety_ok(result)
    )


def judge_full_mode(result: dict) -> bool:
    """전체 모드 한 판이 성공인지 판정한다.

    모두 지키면 True:
      R-04 수거율 80% 이상 (collected / targets, 비율)
      R-06 장면 전체 커버리지 95% 이상 (covered_cells / (grid_cells − obstacle_cells))
      R-18 elapsed_s <= FULL_MAX_S(650 s) 이고 dock_dist_m <= DOCK_RADIUS_M(0.1 m)
      R-26 mode1_elapsed_s <= 480 s, mode2_elapsed_s <= 600 s
      안전 R-09(person_stop_s 모두 <= 1.0 s), R-16(zone_exits 0), R-24(base_collisions 0)
      분실물 R-10·R-11·R-17(forbidden_picks 0, lost_items_photographed >= lost_items_seen)
    targets <= 0 또는 grid_cells − obstacle_cells <= 0 이면 ValueError.
    """
    collected, targets = _targets(result)
    paintable = result["grid_cells"] - result["obstacle_cells"]
    if paintable <= 0:
        raise ValueError(f"칠할 칸이 없음: grid_cells − obstacle_cells = {paintable}")
    return (
        _ratio_ok(collected, targets, COLLECTION_MIN_PCT)                 # R-04
        and _ratio_ok(result["covered_cells"], paintable, COVERAGE_MIN_PCT)  # R-06
        and _full_rest_ok(result)
    )


def judge_bench_only(result: dict) -> bool:
    """관리자 버튼 '벤치만 줍기'(R-32, 선택 기능) 한 판이 성공인지 판정한다.

    모두 지키면 True:
      R-32·R-04 벤치 구역 수거율 80% 이상 (5개 중 4개)
      R-32 dock_dist_m <= DOCK_RADIUS_M(0.1 m) — 충전 자리로 돌아옴
      안전·분실물 조건은 judge_full_mode와 같음 (R-09, R-10, R-11, R-16, R-17, R-24)
    시간·커버리지는 보지 않는다(R-32에 기준 없음, 바닥은 밀지 않음). targets <= 0 이면 ValueError.
    """
    collected, targets = _targets(result)
    return (
        _ratio_ok(collected, targets, COLLECTION_MIN_PCT)   # R-32·R-04
        and result["dock_dist_m"] <= DOCK_RADIUS_M          # R-32
        and _safety_ok(result)
    )


def judge_ten_runs(results: list[dict]) -> bool:
    """전체 모드 10회(시드 10개) 집계가 성공인지 판정한다 (T-21).

    모두 지키면 True:
      R-04 회별 수거율(collected / targets)의 평균 80% 이상, 최저 회 60% 이상
           — 한 회가 80% 미만이어도 평균·최저 기준을 넘으면 집계는 통과
      나머지(R-06, R-18 시간·복귀, R-26, 안전, 분실물)는 10회 모두 judge_full_mode의 같은 기준
    len(results) != RUNS(10) 이면 ValueError. 각 회의 설정 오류도 judge_full_mode처럼 ValueError.
    """
    if len(results) != RUNS:
        raise ValueError(f"10회 집계에는 결과 {RUNS}개가 필요함: {len(results)}개")
    rates = []        # 회별 수거율 (분수로 정확히)
    others_ok = True
    for r in results:
        collected, targets = _targets(r)
        paintable = r["grid_cells"] - r["obstacle_cells"]
        if paintable <= 0:
            raise ValueError(f"칠할 칸이 없음: grid_cells − obstacle_cells = {paintable}")
        rates.append(Fraction(collected, targets))
        others_ok = (others_ok
                     and _ratio_ok(r["covered_cells"], paintable, COVERAGE_MIN_PCT)  # R-06
                     and _full_rest_ok(r))
    mean_ok = sum(rates) * 100 >= COLLECTION_MIN_PCT * len(rates)   # 평균 80% 이상
    min_ok = min(rates) * 100 >= COLLECTION_RUN_MIN_PCT             # 최저 회 60% 이상
    return mean_ok and min_ok and others_ok


def decide_start(time_to_next_booking_s: float, people_on_court: int, bench_button: bool = False) -> str:
    """출발할지, 어떤 모드로 할지 고른다 (R-25 가정 규칙, R-01, R-32 — T-22).

    반환: "full"(전체 모드) · "bench_only"(벤치만 줍기) · "none"(출발 안 함)
      people_on_court >= 1                               → "none" (R-01, 버튼을 눌러도)
      bench_button 이 True                               → "bench_only" (남은 시간과 관계없음, R-32)
      time_to_next_booking_s >= FULL_MAX_S(650 s)        → "full"
      그 밖                                               → "none"
    하던 줄을 멈추고 복귀하는 규칙(대관 시작이 다가올 때)은 문턱 숫자가 정해지지 않아 여기 없다 (확인 필요).
    """
    if people_on_court >= 1:
        return "none"         # R-01: 사람이 있으면 버튼을 눌러도 출발 안 함
    if bench_button:
        return "bench_only"   # R-32
    if time_to_next_booking_s >= FULL_MAX_S:
        return "full"         # R-25
    return "none"
