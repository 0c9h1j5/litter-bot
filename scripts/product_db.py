"""제품 파라미터 DB — data/products/specs.csv(원본, 손으로 고침) → specs.json, 그리고 P05 분석 표.

    uv run python scripts/product_db.py          # specs.json 다시 쓰기 + 분석 표(마크다운)를 화면에 출력
    uv run python scripts/product_db.py params   # config/robot_params.yaml → P05 '7. 우리 로봇 파라미터' 절을 다시 씀

CSV 규칙 (data/products/README.md): 한 행 = 한 제품, 페이지에서 직접 본 값만, 없으면 빈칸.
범위 값은 "3-5"처럼 쓴다 → JSON에서는 [3, 5]. ○/✕/모름 같은 표시는 글자 그대로 둔다.
"""
import csv
import json
import statistics
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "products" / "specs.csv"
JSON = ROOT / "data" / "products" / "specs.json"
PARAMS = ROOT / "config" / "robot_params.yaml"
P05 = ROOT / "docs" / "05-제품파라미터-분석.md"

# P05의 '건식 체육관급' 묶음: 국내 체육관·학교에 팔리거나 체육관 용도로 홍보된 건식(또는 건식 모드) 로봇
DRY_GYM = ["wheelie_j30", "wheelie_c30", "lionsbot_r3vac", "pudu_cc1pro", "pudu_mt1vac", "softbank_whiz", "gausium_phantas"]
TEXT_COLS = {"id", "name", "company", "country", "type", "area_claimed_label", "main_brush", "dust_mop", "sensor_lidar",
             "sensor_depth", "sensor_camera", "sensor_bumper", "sensor_cliff", "price_currency", "price_date", "price_kind",
             "gym_case", "source_url", "checked_date", "note", "side_brushes"}
# 채움 비율을 셀 '사양' 칸 (id·이름·출처·날짜·비고 같은 관리 칸은 뺌)
SPEC_COLS_SKIP = {"id", "name", "company", "country", "type", "source_url", "checked_date", "note", "area_claimed_label",
                  "price_currency", "price_date", "price_kind"}


def parse(v):
    """'' → None, '3-5' → [3.0, 5.0], '28' → 28.0, 그 밖은 글자 그대로."""
    v = v.strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        pass
    if "-" in v:
        a, b = v.split("-", 1)
        try:
            return [float(a), float(b)]
        except ValueError:
            pass
    return v


def load():
    with CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        out.append({k: (v.strip() or None) if k in TEXT_COLS else parse(v) for k, v in r.items()})
    return rows, out


def lo(v):
    return v[0] if isinstance(v, list) else v


def hi(v):
    return v[1] if isinstance(v, list) else v


def mid(v):
    return (v[0] + v[1]) / 2 if isinstance(v, list) else v


def fmt(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, list):
        return f"{fmt(x[0], nd)}~{fmt(x[1], nd)}"
    s = f"{x:,.{nd}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def fill_ratio(raw):
    cols = [c for c in raw[0] if c not in SPEC_COLS_SKIP]
    filled = sum(1 for r in raw for c in cols if r[c].strip())
    return filled, len(raw) * len(cols), len(cols)


def range_table(data, cols):
    by = {d["id"]: d for d in data}
    lines = ["| 칸 | 단위 | 값 있는 제품 수 | 최소 | 중앙 | 최대 |", "| --- | --- | --- | --- | --- | --- |"]
    for col, unit in cols:
        vals = [by[i][col] for i in DRY_GYM if isinstance(by[i][col], (float, list))]
        if not vals:
            lines.append(f"| {col} | {unit} | 0/{len(DRY_GYM)} | — | — | — |")
            continue
        lines.append(f"| {col} | {unit} | {len(vals)}/{len(DRY_GYM)} | {fmt(min(lo(v) for v in vals))} | "
                     f"{fmt(statistics.median(mid(v) for v in vals))} | {fmt(max(hi(v) for v in vals))} |")
    return "\n".join(lines)


def efficiency_table(data):
    """시간당 면적 ÷ (청소 폭 × 속도 × 3600). 속도는 작업 속도가 있으면 그것, 없으면 최고 속도 (계산)."""
    lines = ["| 제품 | 종류 | 청소 폭 m | 속도 m/s (종류) | 폭 × 속도 m²/h (계산) | 표시 m²/h (구분) | 표시 ÷ 폭×속도 | 표시에서 거꾸로 셈한 속도 m/s | 실제 m²/h | 실제 ÷ 표시 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for d in data:
        w, a = d["clean_width_mm"], d["area_claimed_m2h"]
        if w is None or (a is None and d["area_practical_m2h"] is None):
            continue
        v, vk = (d["work_speed_mps"], "작업") if d["work_speed_mps"] else (d["max_speed_mps"], "최고")
        wm = mid(w) / 1000
        theo = wm * v * 3600 if v else None
        p = d["area_practical_m2h"]
        lines.append(
            f"| {d['name']} | {d['type']} | {fmt(wm, 3)} | {fmt(v) + ' (' + vk + ')' if v else '—'} | {fmt(theo, 0)} | "
            f"{fmt(a, 0)} ({d['area_claimed_label'] or '—'}) | {fmt(mid(a) / theo) if (a and theo) else '—'} | "
            f"{fmt(mid(a) / (wm * 3600)) if a else '—'} | {fmt(p, 0)} | "
            f"{fmt(mid(p) / mid(a)) if (p and a) else '—'} |")
    return "\n".join(lines)


# yaml → 표 (새싹봇 참고 스크립트 yaml2md.py를 옮김)
GROUP_NAMES = {"chassis": "차체", "operation": "운행·목표", "cleaning": "청소 모듈", "side_bin": "옆 통(집은 쓰레기)",
               "arm": "로봇팔", "camera": "카메라", "battery": "배터리", "meta": "축소 비율"}


def _pval(v):
    if isinstance(v, list):
        return " ~ ".join(map(str, v)) if all(isinstance(x, (int, float)) for x in v) else ", ".join(map(str, v))
    return str(v)


def _param_rows(d, group):
    out = []
    for k, v in d.items():
        if isinstance(v, dict) and "value" in v:
            out.append((group, k, _pval(v["value"]), v.get("unit", ""), v.get("source", ""),
                        str(v.get("note", "")).replace("|", "/")))
        elif isinstance(v, dict):
            out += _param_rows(v, GROUP_NAMES.get(k, k))
    return out


def params_markdown():
    y = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))
    L = ["## 7. 우리 로봇 파라미터 (config/robot_params.yaml 전체)", "",
         "`uv run python scripts/product_db.py params`가 [config/robot_params.yaml](../config/robot_params.yaml)에서 만든 표다(손으로 고치지 말고 yaml을 고친 뒤 다시 돌린다). "
         "`근거` 읽는 법: 제품 id = 그 상용 제품 값(data/products/specs.csv), 계산 = DB 값으로 계산, 기획자 결정, 시뮬 = 시뮬 실측, 다른 기록 = 저장소의 다른 기록 파일, 가정 = 근거 없음(실측·기획자 확정 뒤 바꿈).", ""]
    meta = [r for r in _param_rows({"meta": y["meta"]}, "공통")]
    L += ["### 7-0. 축소 비율 (meta)", "", "| 묶음 | 이름 | 값 | 단위 | 근거 | 메모 |", "| --- | --- | --- | --- | --- | --- |"]
    L += [f"| {g} | {k} | {v} | {u} | {s} | {n} |" for g, k, v, u, s, n in meta] + [""]
    for sec, title in (("scale_model", "7-1. 축소판 · 시뮬 (scale_model)"),
                       ("product_concept", "7-2. 제품 개념 (product_concept, 실제 체육관용 — 만들지 않음)")):
        L += [f"### {title}", "", "| 묶음 | 이름 | 값 | 단위 | 근거 | 메모 |", "| --- | --- | --- | --- | --- | --- |"]
        L += [f"| {g} | {k} | {v} | {u} | {s} | {n} |" for g, k, v, u, s, n in _param_rows(y[sec], "공통")]
        L.append("")
    return "\n".join(L)


def write_params_section():
    """P05에서 '## 7.' 절(없으면 '## 변경 기록' 바로 앞)을 yaml 표로 바꿔 쓴다."""
    doc = P05.read_text(encoding="utf-8")
    end = doc.index("## 변경 기록")
    start = doc.find("## 7. 우리 로봇 파라미터")
    start = end if start == -1 else start
    P05.write_text(doc[:start] + params_markdown() + "\n" + doc[end:], encoding="utf-8")


def main():
    if sys.argv[1:] == ["params"]:
        write_params_section()
        print("wrote", P05.relative_to(ROOT), "7절")
        return
    raw, data = load()
    JSON.write_text(json.dumps({"source": "data/products/specs.csv (scripts/product_db.py가 변환)", "products": data},
                               ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    filled, total, ncols = fill_ratio(raw)
    print(f"행 {len(raw)}개, 사양 칸 {ncols}개, 채움 {filled}/{total} = {filled / total:.0%}\n")
    by_type = {}
    for d in data:
        by_type[d["type"]] = by_type.get(d["type"], 0) + 1
    print("종류별:", ", ".join(f"{k} {v}" for k, v in by_type.items()), "\n")
    print("### 건식 체육관급 범위 (" + ", ".join(DRY_GYM) + ")\n")
    print(range_table(data, [("length_mm", "mm"), ("width_mm", "mm"), ("height_mm", "mm"), ("weight_kg", "kg"),
                             ("max_speed_mps", "m/s"), ("clean_width_mm", "mm"), ("area_claimed_m2h", "m²/h"),
                             ("area_practical_m2h", "m²/h"), ("suction_kpa", "kPa"), ("dustbin_l", "L"),
                             ("battery_wh", "Wh"), ("runtime_h", "h"), ("charge_h", "h"), ("min_pass_mm", "mm"),
                             ("noise_db", "dB")]))
    print("\n### 효율 비교 (모든 제품 중 청소 폭과 면적이 있는 것)\n")
    print(efficiency_table(data))


if __name__ == "__main__":
    main()
