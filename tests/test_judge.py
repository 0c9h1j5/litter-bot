"""판정 테스트 T-01~T-08 — docs/requirements.md ② 요구사항 표와 R ↔ T 대응 표.

사람이 쓴 시험지다. src/judge.py를 구현할 때 이 파일은 고치지 않는다.
경계값은 '딱 경계 = 성공, 하나 넘으면 = 실패'로 쓴다 (교안 test_one_wrong_is_success 정신).
기준값이 12/01에 바뀌면 이 파일의 경계값을 사람이 먼저 고친다.
"""

from judge import judge_full_mode, judge_short_mode


def short_result(**changes):
    """짧은 모드 정상 한 판 (벤치 구역 5개 중 5개, 커버리지 98%, 300 s, 안전 위반 없음)."""
    result = {
        "elapsed_s": 300.0,
        "coverage_pct": 98.0,
        "collected": 5,
        "targets": 5,
        "base_collisions": 0,
        "zone_exits": 0,
        "person_stop_s": [0.6],
        "forbidden_picks": 0,
        "lost_items_seen": 1,
        "lost_items_photographed": 1,
    }
    result.update(changes)
    return result


def full_result(**changes):
    """전체 모드 정상 한 판 (10개 중 9개, 커버리지 97%, 모드 1 300 s, 모드 2 450 s)."""
    result = {
        "mode1_elapsed_s": 300.0,
        "mode2_elapsed_s": 450.0,
        "coverage_pct": 97.0,
        "collected": 9,
        "targets": 10,
        "base_collisions": 0,
        "zone_exits": 0,
        "person_stop_s": [],
        "forbidden_picks": 0,
        "lost_items_seen": 0,
        "lost_items_photographed": 0,
    }
    result.update(changes)
    return result


def test_short_normal_is_success():
    """T-01 (R-04, R-06, R-18): 짧은 모드 정상 한 판은 성공."""
    assert judge_short_mode(short_result())


def test_short_four_of_five_is_success():
    """T-02 (R-04): 벤치 구역 5개 중 딱 4개(80%)면 성공 — '80% 이상'."""
    assert judge_short_mode(short_result(collected=4))


def test_short_three_of_five_is_fail():
    """T-03 (R-04): 5개 중 3개(60%)는 실패."""
    assert not judge_short_mode(short_result(collected=3))


def test_short_time_boundary():
    """T-04 (R-18): 딱 360 s는 성공, 360.5 s는 실패 — '360 s 이하'."""
    assert judge_short_mode(short_result(elapsed_s=360.0))
    assert not judge_short_mode(short_result(elapsed_s=360.5))


def test_short_coverage_boundary():
    """T-05 (R-06): 커버리지 딱 95.0%는 성공, 94.9%는 실패 — '95% 이상'."""
    assert judge_short_mode(short_result(coverage_pct=95.0))
    assert not judge_short_mode(short_result(coverage_pct=94.9))


def test_safety_violation_is_fail():
    """T-06 (R-24, R-16, R-09): 충돌 1회, 구역 밖 1회, 사람 앞 정지 1.0 s 초과는 다른 게 다 좋아도 실패."""
    assert not judge_short_mode(short_result(base_collisions=1))
    assert not judge_short_mode(short_result(zone_exits=1))
    # 사람이 두 번 들어왔고 한 번이라도 1초를 넘으면 실패, 딱 1.0 s는 성공
    assert not judge_short_mode(short_result(person_stop_s=[0.5, 1.01]))
    assert judge_short_mode(short_result(person_stop_s=[0.5, 1.0]))


def test_forbidden_pick_or_missing_photo_is_fail():
    """T-07 (R-10, R-11, R-17): 분실물·물 찬 병·소지품을 1번이라도 집거나, 본 분실물 사진을 빠뜨리면 실패."""
    assert not judge_short_mode(short_result(forbidden_picks=1))
    assert not judge_short_mode(short_result(lost_items_seen=2, lost_items_photographed=1))
    # 분실물이 없으면 사진 0장도 성공
    assert judge_short_mode(short_result(lost_items_seen=0, lost_items_photographed=0))


def test_full_mode_boundaries():
    """T-08 (R-26, R-04, R-06, R-24): 전체 모드 — 정상·딱 경계는 성공, 하나 넘으면 실패."""
    assert judge_full_mode(full_result())
    # 딱 경계: 10개 중 8개, 커버리지 95%, 모드 1 480 s, 모드 2 600 s
    assert judge_full_mode(
        full_result(collected=8, coverage_pct=95.0, mode1_elapsed_s=480.0, mode2_elapsed_s=600.0)
    )
    assert not judge_full_mode(full_result(collected=7))
    assert not judge_full_mode(full_result(mode1_elapsed_s=480.5))
    assert not judge_full_mode(full_result(mode2_elapsed_s=600.5))
    assert not judge_full_mode(full_result(base_collisions=1))
