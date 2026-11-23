"""현장 데이터 요약: logs/field/*.csv → docs/03-현장데이터-요약.md (자동 생성)

실행: uv run python scripts/field_summary.py

- 읽는 파일: logs/field/field_estimate_v1.csv (주인 회고 추정), logs/field/field_count*.csv (실측).
  field_count_template.csv의 예시 줄(gym_id = 예시)은 건너뛴다.
- source 칸: estimate_owner_recall(추정) / field_count(실측). 비어 있으면 field_count로 본다.
- 범위값은 중앙값 칸 + *_min / *_max 칸. 실측 행은 보통 중앙값 칸만 채운다.
- 채택값(기획안이 쓰는 값): 유형별 실측 행이 3개 이상이면 실측 평균, 1~2개면 실측과 추정을
  (실측 행 수 / 3) 비중으로 섞고, 0개면 추정만 쓴다.
"""
import csv
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELD = ROOT / "logs" / "field"
OUT = ROOT / "docs" / "03-현장데이터-요약.md"

TYPES = ["사설", "구민", "학교"]
LOCS = [("bench", "벤치 구역"), ("corner", "코트 구석"), ("sill", "창문틀"), ("court", "코트 안"), ("elsewhere", "기타")]
ITEMS = [("bottle", "생수병"), ("can", "캔"), ("cup", "컵"), ("bag_crumpled", "구겨진 봉지"), ("bag_flat", "납작한 봉지"), ("other", "기타")]
GRIP = ["bottle", "can", "cup", "bag_crumpled"]  # 집게 대상 (K-1)
DAYS = {"사설": 30, "구민": 30, "학교": 22}  # 한 달 운영일 (가정)
FULL_WEIGHT_N = 3  # 실측 행이 이만큼 모이면 실측만 쓴다
LABEL = {"field_count": "실측(현장 계수)",
         "estimate_owner_recall": "현장 관찰 기반 추정(체육관 약 10곳·1년, 기획자 직접 이용)"}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_rows():
    rows = []
    files = [FIELD / "field_estimate_v1.csv"] + sorted(p for p in FIELD.glob("field_count*.csv"))
    for f in files:
        if not f.exists():
            continue
        with f.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("gym_id") or "").strip() == "예시" or not (r.get("gym_type") or "").strip():
                    continue
                r["source"] = (r.get("source") or "").strip() or "field_count"
                r["_file"] = f.name
                rows.append(r)
    return rows


def mean(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def per_game(rows):
    """유형 하나, source 하나의 행들 → 지표 dict (평균)."""
    if not rows:
        return None
    m = {"n": len(rows)}
    for loc, _ in LOCS:
        for it, _ in ITEMS:
            m[f"{loc}_{it}"] = mean([num(r.get(f"{loc}_{it}")) or 0 for r in rows])
    for it, _ in ITEMS:
        m[it] = sum(m[f"{loc}_{it}"] for loc, _ in LOCS)
    for loc, _ in LOCS:
        m[loc] = sum(m[f"{loc}_{it}"] for it, _ in ITEMS)
    m["grip"] = sum(m[it] for it in GRIP)
    m["total"] = sum(m[it] for it, _ in ITEMS)
    for k in ["dust_clump", "grit_level", "feather_level", "lost_items", "full_bottle"]:
        m[k] = mean([num(r.get(k)) for r in rows])

    def total_sec(r):  # 밀대 포함 총 정리 시간: human_total_sec, 없으면 pick + mop
        t = num(r.get("human_total_sec"))
        if t is None and num(r.get("human_pick_sec")) is not None:
            t = num(r.get("human_pick_sec")) + (num(r.get("human_mop_sec")) or 0)
        return t

    m["pick_sec"] = mean([num(r.get("human_pick_sec")) for r in rows])
    m["pick_min"] = mean([num(r.get("human_pick_sec_min")) or num(r.get("human_pick_sec")) for r in rows])
    m["pick_max"] = mean([num(r.get("human_pick_sec_max")) or num(r.get("human_pick_sec")) for r in rows])
    m["tot_sec"] = mean([total_sec(r) for r in rows])
    m["tot_min"] = mean([num(r.get("human_total_sec_min")) or total_sec(r) for r in rows])
    m["tot_max"] = mean([num(r.get("human_total_sec_max")) or total_sec(r) for r in rows])
    m["slots"] = mean([num(r.get("slots_per_day")) for r in rows])
    m["slots_min"] = mean([num(r.get("slots_per_day_min")) or num(r.get("slots_per_day")) for r in rows])
    m["slots_max"] = mean([num(r.get("slots_per_day_max")) or num(r.get("slots_per_day")) for r in rows])
    m["gap"] = mean([num(r.get("gap_to_next_min")) for r in rows])
    m["bin_entrance"] = mean([1.0 if (r.get("bin_location") or "") == "entrance" else 0.0 for r in rows if r.get("bin_location")])
    return m


def blend(est, fld):
    """채택값: 실측 행 수에 따라 추정과 실측을 섞는다. 값이 없는 쪽은 다른 쪽을 쓴다."""
    if fld is None:
        return est, 0.0
    w = min(1.0, fld["n"] / FULL_WEIGHT_N)
    if est is None:
        return fld, 1.0
    out = {}
    for k in est:
        a, b = est.get(k), fld.get(k)
        if a is None:
            out[k] = b
        elif b is None:
            out[k] = a
        else:
            out[k] = a * (1 - w) + b * w
    out["n"] = fld["n"]
    return out, w


def f(v, d=1):
    return "—" if v is None else f"{v:.{d}f}"


def daily(m, t):
    if not m or m.get("slots") is None or m.get("tot_sec") is None:
        return None
    lo = m["tot_min"] / 60 * m["slots_min"]
    mid = m["tot_sec"] / 60 * m["slots"]
    hi = m["tot_max"] / 60 * m["slots_max"]
    return lo, mid, hi, lo * DAYS[t] / 60, mid * DAYS[t] / 60, hi * DAYS[t] / 60


def main():
    rows = load_rows()
    by = {(t, s): [r for r in rows if r["gym_type"].strip() == t and r["source"] == s]
          for t in TYPES for s in ("estimate_owner_recall", "field_count")}
    n_est = sum(1 for r in rows if r["source"] == "estimate_owner_recall")
    n_fld = sum(1 for r in rows if r["source"] == "field_count")
    L = []
    L.append("# 현장 데이터 (실측 + 추정) — 요약\n")
    status = f"실측 {n_fld}건 · 추정 {n_est}건" + (" — 실측 보강 진행 중(11/24~)" if n_fld == 0 else "")
    L.append(f"**{status}**\n")
    L.append("P03 · 자동 생성 — `scripts/field_summary.py`가 `logs/field/*.csv`에서 만든다(손으로 고치지 않는다). 관련: [기획안 1장·13장·11장](00-기획안.md), [현장 계수표](02-현장계수표.md)\n")
    L.append(f"> **1차 근거 = {LABEL['estimate_owner_recall']}. {LABEL['field_count']}이 들어오는 대로 갱신한다.** "
             f"출처 구분: `field_count` = {LABEL['field_count']}, `estimate_owner_recall` = {LABEL['estimate_owner_recall']}. 추정은 실측이라고 부르지 않는다. "
             f"채택값은 유형별 실측이 {FULL_WEIGHT_N}행 이상이면 실측만, 1~2행이면 섞고, 0행이면 추정만 쓴다.\n")
    L.append("**갱신 3단계:** ① `logs/field/field_count.csv`에 경기 1회 = 한 줄 추가(`source=field_count`) → ② `uv run python scripts/field_summary.py` → ③ 이 문서가 다시 만들어진다(HTML은 `uv run --with markdown python docs/build_html.py`).\n")

    L.append("## 1. 추정 → 실측 비율\n")
    L.append("| 유형 | 추정 (현장 관찰 기반) | 실측 (현장 계수) | 채택값의 실측 비중 |\n| --- | --- | --- | --- |")
    adopted = {}
    for t in TYPES:
        est = per_game(by[(t, "estimate_owner_recall")])
        fld = per_game(by[(t, "field_count")])
        a, w = blend(est, fld)
        adopted[t] = (a, est, fld, w)
        L.append(f"| {t} | {len(by[(t, 'estimate_owner_recall')])} | {len(by[(t, 'field_count')])} | {w*100:.0f}% |")
    L.append("")

    L.append("## 2. 경기 1회당 품목 수 (채택값)\n")
    L.append("| 유형 | " + " | ".join(n for _, n in ITEMS) + " | **집게 대상 합계** (병·캔·컵·구겨진 봉지) | K-1 (1개 미만이면 집게를 확장으로) |")
    L.append("| --- | " + " | ".join("---" for _ in ITEMS) + " | --- | --- |")
    for t in TYPES:
        a = adopted[t][0]
        if not a:
            continue
        k1 = "**발동**" if a["grip"] < 1 else ("**경계 — 계수로 확인**" if a["grip"] < 1.5 else "통과")
        L.append(f"| {t} | " + " | ".join(f(a[it]) for it, _ in ITEMS) + f" | {f(a['grip'])} | {k1} |")
    L.append("")
    L.append("먼지·바닥 (채택값, 단계 0 없음 ~ 3 많음):\n")
    L.append("| 유형 | 먼지 뭉치 (개) | 흙먼지 (0~3) | 셔틀콕 깃털 (0~3) | 분실물 (개/경기) | 물이 찬 병 |\n| --- | --- | --- | --- | --- | --- |")
    for t in TYPES:
        a = adopted[t][0]
        if a:
            L.append(f"| {t} | {f(a['dust_clump'])} | {f(a['grit_level'])} | {f(a['feather_level'])} | {f(a['lost_items'])} | {f(a['full_bottle'])} |")
    L.append("")

    L.append("## 3. 위치 분포 (채택값, 경기당 품목 수 기준)\n")
    L.append("| 유형 | " + " | ".join(n for _, n in LOCS) + " | 쓰레기통이 입구 쪽인 비율 |")
    L.append("| --- | " + " | ".join("---" for _ in LOCS) + " | --- |")
    for t in TYPES:
        a = adopted[t][0]
        if not a:
            continue
        tot = a["total"] or 1
        be = "—" if a["bin_entrance"] is None else f"{a['bin_entrance'] * 100:.0f}%"
        L.append(f"| {t} | " + " | ".join(f"{a[loc] / tot * 100:.0f}%" for loc, _ in LOCS) + f" | {be} |")
    L.append("")

    L.append("## 4. 사람 정리 시간과 하루·월 정리 시간 (채택값)\n")
    L.append("| 유형 | 쓰레기만 (분, 최소~중앙~최대) | 밀대 포함 (분) | 하루 타임 수 | 다음 대관까지 (분, 중앙) | **하루 정리 시간 (분)** | **한 달 (시간)** |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    for t in TYPES:
        a = adopted[t][0]
        if not a:
            continue
        d = daily(a, t)
        pick = f"{f(a['pick_min']/60 if a['pick_min'] else None,0)}~{f(a['pick_sec']/60 if a['pick_sec'] else None,1)}~{f(a['pick_max']/60 if a['pick_max'] else None,0)}"
        tot = f"{f(a['tot_min']/60 if a['tot_min'] else None,0)}~{f(a['tot_sec']/60 if a['tot_sec'] else None,0)}~{f(a['tot_max']/60 if a['tot_max'] else None,0)}"
        sl = f"{f(a['slots_min'],0)}~{f(a['slots_max'],0)}"
        dd = "—" if not d else f"{d[0]:.0f}~{d[2]:.0f} (중앙 {d[1]:.0f})"
        mm = "—" if not d else f"{d[3]:.0f}~{d[5]:.0f} (중앙 {d[4]:.0f})"
        L.append(f"| {t} | {pick} | {tot} | {sl} | {f(a['gap'],0)} | {dd} | {mm} |")
    L.append(f"\n한 달 운영일: " + ", ".join(f"{t} {DAYS[t]}일" for t in TYPES) + " (가정). 정리 횟수 = 하루 타임 수(각 타임 뒤 1회).\n")

    L.append("## 5. 출처별 원값 (실측 / 추정 나란히)\n")
    L.append("| 유형 | source | 행 | 집게 대상 합계 | 과자 봉지 (구겨짐+납작) | 벤치 구역 비율 | 쓰레기만 (분) | 밀대 포함 (분) |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for t in TYPES:
        for lab, idx in (("추정 (현장 관찰 기반)", 1), ("실측 (현장 계수)", 2)):
            m = adopted[t][idx]
            if not m:
                L.append(f"| {t} | {lab} | 0 | — | — | — | — | — |")
                continue
            tot = m["total"] or 1
            L.append(f"| {t} | {lab} | {m['n']} | {f(m['grip'])} | {f(m['bag_crumpled'] + m['bag_flat'])} | {m['bench']/tot*100:.0f}% | "
                     f"{f(m['pick_sec']/60 if m['pick_sec'] else None)} | {f(m['tot_sec']/60 if m['tot_sec'] else None)} |")
    L.append("")
    L.append("## 6. 읽는 법·한계\n")
    L.append("- 추정 행은 기획자가 최근 1년 동안 체육관 약 10곳(학교·구민·사설)을 **직접 이용하며 관찰한 것**(`logs/field/2026-11-23_주인회고.md`)을 유형별 대표 행으로 옮긴 것이다. 현장에서 센 계수는 아니므로 실측과 나눠 적는다. 회고에 없는 칸(구겨짐/납작 비율, 먼지 뭉치 개수, 다음 대관까지 분)은 `note` 칸에 '가정'으로 적었다.")
    L.append("- 실측 행이 들어오면 위 표의 채택값과 비율이 자동으로 바뀐다. 기획안 1-5(왜 로봇인가), 4장·K-1(집게 대상), 6-8(운영 모드), 11장(성공 기준 재조정)은 이 문서의 채택값을 따른다.")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: 추정 {n_est}행, 실측 {n_fld}행")


if __name__ == "__main__":
    main()
