"""판정 테스트 — docs/requirements.md v0.6 ② 요구사항 표와 'R ↔ T 대응' 표.

사람이 쓴 시험지다 (교안 원칙: 테스트는 사람이, 판정 함수 구현은 에이전트가).
src/judge.py를 구현할 때 이 파일은 고치지 않는다. 기준값이 바뀌면 사람이 이 파일의 경계값을 먼저 고친다.

v0.6 (주인 결정 2026-11-24): 대관 사이 '짧은 모드'는 없앴다 (judge_short_mode·SHORT_MAX_S 삭제).
주 판정 = 전체 모드 한 판 (장면 전체 청소 + 핫스폿 집기 + 충전 자리 복귀, 650 s 이하).
선택 기능 = 관리자 버튼 '벤치만 줍기'(R-32, 시간 기준 없음).

경계값은 '딱 경계 = 성공, 한 칸 넘으면 = 실패'로 쓴다. '하나만 틀림'은 두 가지로 본다:
  - 집게 대상 10개 중 1개를 놓친 판(9/10)은 성공 — 수거율은 비율 기준이다.
  - 다른 조건이 모두 좋아도 지켜야 할 조건 하나만 어기면 실패 (T-35).
테스트 안의 칸 수·시간 같은 '정상 한 판' 값은 테스트용 예시다 (실측 아님). 예: 장애물 칸 300은 장면 v2에서 셀 값의 자리.
"""

import pytest

import judge
from judge import decide_start, judge_bench_only, judge_full_mode, judge_ten_runs


# ---------------------------------------------------------------- 정상 한 판 (테스트용 예시 값)

def full_result(**changes):
    """전체 모드 정상 한 판.

    10개 중 9개 수거, 장면 6,000칸 중 장애물 300칸 → 남은 5,700칸 중 5,600칸 통과(98.2%),
    전체 480 s(①-2 C-30 예상과 같은 값), 모드 1 175 s · 모드 2 300 s, 충전 자리에서 0.03 m에 멈춤, 안전 위반 없음.
    """
    result = {
        "elapsed_s": 480.0,
        "mode1_elapsed_s": 175.0,
        "mode2_elapsed_s": 300.0,
        "grid_cells": 6000,
        "obstacle_cells": 300,
        "covered_cells": 5600,
        "collected": 9,
        "targets": 10,
        "dock_dist_m": 0.03,
        "base_collisions": 0,
        "zone_exits": 0,
        "person_stop_s": [],
        "forbidden_picks": 0,
        "lost_items_seen": 1,
        "lost_items_photographed": 1,
    }
    result.update(changes)
    return result


def bench_result(**changes):
    """벤치만 줍기(R-32) 정상 한 판: 벤치 구역 5개 중 5개, 충전 자리에서 0.05 m, 사람 한 번 와서 0.6 s에 멈춤."""
    result = {
        "collected": 5,
        "targets": 5,
        "dock_dist_m": 0.05,
        "base_collisions": 0,
        "zone_exits": 0,
        "person_stop_s": [0.6],
        "forbidden_picks": 0,
        "lost_items_seen": 0,
        "lost_items_photographed": 0,
    }
    result.update(changes)
    return result


# ---------------------------------------------------------------- 전체 모드 한 판 (Must R-04 · R-06 · R-18)

def test_t01_full_normal_is_success():
    """T-01 (R-04, R-06, R-18): 전체 모드 정상 한 판(충전 자리 복귀 포함)은 성공."""
    assert judge_full_mode(full_result()) is True


def test_t02_full_collection_boundary_is_success():
    """T-02 (R-04): 10개 중 1개 놓침(9/10)·딱 8개(80%)는 성공 — '80% 이상'."""
    assert judge_full_mode(full_result(collected=9))
    assert judge_full_mode(full_result(collected=8))


def test_t03_full_seven_of_ten_is_fail():
    """T-03 (R-04): 10개 중 7개(70%)는 실패. 0개도 실패."""
    assert not judge_full_mode(full_result(collected=7))
    assert not judge_full_mode(full_result(collected=0))


def test_t04_full_time_boundary():
    """T-04 (R-18): FULL_MAX_S = 650 s 이하 — 649 s·딱 650 s 성공, 650.5 s·651 s 실패."""
    assert judge.FULL_MAX_S == 650.0
    assert judge_full_mode(full_result(elapsed_s=649.0))
    assert judge_full_mode(full_result(elapsed_s=650.0))
    assert not judge_full_mode(full_result(elapsed_s=650.5))
    assert not judge_full_mode(full_result(elapsed_s=651.0))


def test_t05_full_coverage_boundary_scene_minus_obstacles():
    """T-05 (R-06): 장면 전체 커버리지 95% 이상, 분모 = 장면 전체 칸 − 장애물 칸.

    6,000칸 − 장애물 300칸 = 5,700칸. 95.0% = 딱 5,415칸 → 성공, 5,414칸(94.98%) → 실패.
    """
    assert judge_full_mode(full_result(covered_cells=5415))
    assert not judge_full_mode(full_result(covered_cells=5414))
    # 장애물 칸을 분모에서 빼야 통과한다: 장애물 0칸이면 같은 5,415칸이 6,000칸 중 90.25% → 실패
    assert not judge_full_mode(full_result(covered_cells=5415, obstacle_cells=0))
    # 장애물이 없는 장면에서 딱 95.0% = 5,700칸 → 성공
    assert judge_full_mode(full_result(covered_cells=5700, obstacle_cells=0))
    # 다 지나감(100%)도 성공
    assert judge_full_mode(full_result(covered_cells=5700))


def test_t06_full_safety_violation_is_fail():
    """T-06 (R-24, R-16, R-09): 충돌 1회, 구역 밖 1회, 사람 앞 정지 1.0 s 초과는 다른 게 다 좋아도 실패."""
    assert not judge_full_mode(full_result(base_collisions=1))
    assert not judge_full_mode(full_result(zone_exits=1))
    # 사람이 두 번 들어왔고 한 번이라도 1초를 넘으면 실패, 딱 1.0 s는 성공
    assert not judge_full_mode(full_result(person_stop_s=[0.5, 1.01]))
    assert judge_full_mode(full_result(person_stop_s=[0.5, 1.0]))
    # 사람이 한 번도 안 들어온 판(빈 리스트)은 성공 — 빈 시간 운영의 보통 경우
    assert judge_full_mode(full_result(person_stop_s=[]))


def test_t07_full_forbidden_pick_or_missing_photo_is_fail():
    """T-07 (R-10, R-11, R-17): 분실물·물 찬 병·소지품을 1번이라도 집거나, 본 분실물 사진을 빠뜨리면 실패."""
    assert not judge_full_mode(full_result(forbidden_picks=1))
    assert not judge_full_mode(full_result(lost_items_seen=2, lost_items_photographed=1))
    # 분실물이 없으면 사진 0장도 성공
    assert judge_full_mode(full_result(lost_items_seen=0, lost_items_photographed=0))


def test_t08_full_mode_parts_and_all_at_boundary():
    """T-08 (R-26, R-04, R-06, R-18): 모드 1 480 s · 모드 2 600 s 이하(Should, 판정은 계속 검사)와 '모두 딱 경계'.

    모드 1 480.5 s · 모드 2 600.5 s는 실패. 모든 칸이 동시에 딱 경계(8/10, 95.0%, 650 s, 모드 1 480 s, 복귀 0.10 m)면 성공.
    """
    assert not judge_full_mode(full_result(mode1_elapsed_s=480.5))
    assert not judge_full_mode(full_result(mode2_elapsed_s=600.5))
    assert judge_full_mode(full_result(mode1_elapsed_s=480.0))
    assert judge_full_mode(
        full_result(collected=8, covered_cells=5415, elapsed_s=650.0,
                    mode1_elapsed_s=480.0, mode2_elapsed_s=170.0, dock_dist_m=0.10)
    )


def test_t09_collection_is_ratio_not_count():
    """T-09 (R-04, 단계 4): 12/01에 대상 수가 바뀌어도 개수가 아니라 비율 80%로 판정 (K-4)."""
    assert judge_full_mode(full_result(collected=16, targets=20))
    assert not judge_full_mode(full_result(collected=15, targets=20))
    assert judge_full_mode(full_result(collected=4, targets=5))
    assert not judge_full_mode(full_result(collected=3, targets=5))
    assert judge_full_mode(full_result(collected=4, targets=4))
    assert not judge_full_mode(full_result(collected=3, targets=4))


def test_t32_full_must_return_to_dock():
    """T-32 (R-18): 끝난 위치가 충전 자리 반경 0.1 m(가정) 안이어야 성공 — 딱 0.10 m 성공, 0.11 m 실패.

    다른 게 다 좋아도 충전 자리로 돌아오지 않으면(예: 1.5 m 밖) 실패.
    """
    assert judge.DOCK_RADIUS_M == 0.1
    assert judge_full_mode(full_result(dock_dist_m=0.0))
    assert judge_full_mode(full_result(dock_dist_m=0.10))
    assert not judge_full_mode(full_result(dock_dist_m=0.11))
    assert not judge_full_mode(full_result(dock_dist_m=1.5))


@pytest.mark.parametrize(
    "broken",
    [
        {"collected": 7},             # R-04
        {"covered_cells": 5414},      # R-06
        {"elapsed_s": 650.5},         # R-18 시간
        {"dock_dist_m": 0.11},        # R-18 복귀
        {"mode1_elapsed_s": 480.5},   # R-26
        {"mode2_elapsed_s": 600.5},   # R-26
        {"base_collisions": 1},       # R-24
        {"zone_exits": 1},            # R-16
        {"person_stop_s": [1.01]},    # R-09
        {"forbidden_picks": 1},       # R-10·R-11·R-17
        {"lost_items_seen": 1, "lost_items_photographed": 0},  # R-17
    ],
    ids=["R-04", "R-06", "R-18-time", "R-18-dock", "R-26-mode1", "R-26-mode2",
         "R-24", "R-16", "R-09", "R-10-11-17", "R-17-photo"],
)
def test_t35_full_one_wrong_is_fail(broken):
    """T-35 (R-04, R-06, R-18, R-26, R-24, R-16, R-09, R-10, R-11, R-17): 조건 하나만 경계 밖이고 나머지는 정상이면 실패."""
    assert judge_full_mode(full_result()) is True
    assert judge_full_mode(full_result(**broken)) is False


def test_t36_full_bad_scene_raises():
    """T-36 (R-04, R-06): 장면 설정 오류는 성공·실패를 내지 않고 ValueError — 대상 0개, 칠할 칸 0칸."""
    with pytest.raises(ValueError):
        judge_full_mode(full_result(targets=0))
    with pytest.raises(ValueError):
        judge_full_mode(full_result(grid_cells=300, obstacle_cells=300, covered_cells=0))


# ---------------------------------------------------------------- 벤치만 줍기 (R-32, 선택 기능)

def test_t10_bench_only_safety_and_lost_items():
    """T-10 (R-09, R-10, R-11, R-16, R-17, R-24, 단계 6·7): 벤치만 줍기도 안전·분실물 조건은 전체 모드와 같다."""
    assert not judge_bench_only(bench_result(base_collisions=1))
    assert not judge_bench_only(bench_result(zone_exits=1))
    assert not judge_bench_only(bench_result(person_stop_s=[1.01]))
    assert judge_bench_only(bench_result(person_stop_s=[1.0, 0.3]))
    assert not judge_bench_only(bench_result(forbidden_picks=1))
    assert not judge_bench_only(bench_result(lost_items_seen=1, lost_items_photographed=0))


def test_t33_bench_only_collection_and_dock():
    """T-33 (R-32, R-04): 벤치 구역 5개 중 딱 4개 성공, 3개 실패, 충전 자리 0.10 m 성공 / 0.11 m 실패. 시간 기준 없음.

    벤치만 줍기는 바닥을 밀지 않으므로 커버리지·시간 칸이 없어도 판정한다.
    """
    assert judge_bench_only(bench_result()) is True
    assert judge_bench_only(bench_result(collected=4))
    assert not judge_bench_only(bench_result(collected=3))
    assert judge_bench_only(bench_result(dock_dist_m=0.10))
    assert not judge_bench_only(bench_result(dock_dist_m=0.11))
    # 시간 칸이 있어도 보지 않는다 (R-32는 시간 기준을 정하지 않음)
    assert judge_bench_only(bench_result(elapsed_s=10_000.0))
    with pytest.raises(ValueError):
        judge_bench_only(bench_result(targets=0))


# ---------------------------------------------------------------- 10회 집계 (T-21)

def ten(**changes):
    return [full_result(**changes) for _ in range(10)]


def test_t21_ten_runs_aggregate():
    """T-21 (R-04, R-06, R-18, R-24): 시드 10개 10회 집계.

    R-04 = 회별 수거율의 10회 평균 80% 이상 + 최저 회 60% 이상. 나머지(R-06·R-18·R-26·안전·분실물)는 10회 모두 한 판 기준.
    """
    assert judge_ten_runs(ten()) is True
    # 평균 딱 80%: 8/10이 10번 → 성공
    assert judge_ten_runs(ten(collected=8))
    # 한 회만 6/10(60%)이고 나머지 9회는 9/10 → 평균 87%, 최저 60% → 성공 (그 회는 한 판 기준으로는 실패지만 집계는 통과)
    runs = ten()
    runs[3] = full_result(collected=6)
    assert judge_ten_runs(runs)
    # 한 회가 5/10(50%) → 최저 회 60% 미만 → 실패 (평균은 86%)
    runs[3] = full_result(collected=5)
    assert not judge_ten_runs(runs)
    # 평균 79%: 8/10 9회 + 7/10 1회 → 실패
    runs = ten(collected=8)
    runs[0] = full_result(collected=7)
    assert not judge_ten_runs(runs)
    # 10회 중 한 회만 650.5 s → 실패 ('10회 모두')
    runs = ten()
    runs[9] = full_result(elapsed_s=650.5)
    assert not judge_ten_runs(runs)
    # 10회 중 한 회만 충돌 1 → 실패 (R-24 '10회 모두')
    runs = ten()
    runs[5] = full_result(base_collisions=1)
    assert not judge_ten_runs(runs)
    # 10회 중 한 회만 충전 자리 밖 → 실패
    runs = ten()
    runs[0] = full_result(dock_dist_m=0.11)
    assert not judge_ten_runs(runs)


def test_t21_ten_runs_needs_exactly_ten():
    """T-21 (R-04): 집계는 시드 10개 10회 — 9회·11회는 ValueError."""
    with pytest.raises(ValueError):
        judge_ten_runs(ten()[:9])
    with pytest.raises(ValueError):
        judge_ten_runs(ten() + [full_result()])


# ---------------------------------------------------------------- 출발 판단 (T-22)

def test_t22_start_only_with_enough_empty_time():
    """T-22 (R-25, R-01): 사람이 없고 다음 대관까지 남은 시간 ≥ FULL_MAX_S(650 s)면 'full', 짧으면 'none'.

    딱 650 s 'full', 649 s 'none'. 사람이 1명이라도 있으면 시간이 충분해도 'none'(R-01).
    """
    assert decide_start(time_to_next_booking_s=650.0, people_on_court=0) == "full"
    assert decide_start(time_to_next_booking_s=8 * 3600.0, people_on_court=0) == "full"
    assert decide_start(time_to_next_booking_s=649.0, people_on_court=0) == "none"
    assert decide_start(time_to_next_booking_s=0.0, people_on_court=0) == "none"
    assert decide_start(time_to_next_booking_s=8 * 3600.0, people_on_court=1) == "none"


def test_t22_bench_button():
    """T-22 (R-32, R-01): 관리자 버튼을 누르면 남은 시간과 관계없이 'bench_only'. 사람이 있으면 버튼을 눌러도 'none'."""
    assert decide_start(time_to_next_booking_s=300.0, people_on_court=0, bench_button=True) == "bench_only"
    assert decide_start(time_to_next_booking_s=8 * 3600.0, people_on_court=0, bench_button=True) == "bench_only"
    assert decide_start(time_to_next_booking_s=300.0, people_on_court=2, bench_button=True) == "none"


# ---------------------------------------------------------------- 짧은 모드 삭제 (T-34)

def test_t34_short_mode_is_removed():
    """T-34 (R-18 v0.6, Won't): 대관 사이 짧은 모드는 없앴다 — judge_short_mode·SHORT_MAX_S(360 s)가 남아 있으면 안 된다."""
    assert not hasattr(judge, "judge_short_mode")
    assert not hasattr(judge, "SHORT_MAX_S")
