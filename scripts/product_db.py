"""제품 파라미터 DB — data/products/specs.csv(원본, 손으로 고침) → specs.json, 그리고 P05 분석 표.

    uv run python scripts/product_db.py          # specs.json 다시 쓰기 + 분석 표(마크다운)를 화면에 출력

CSV 규칙 (data/products/README.md): 한 행 = 한 제품, 페이지에서 직접 본 값만, 없으면 빈칸.
범위 값은 "3-5"처럼 쓴다 → JSON에서는 [3, 5]. ○/✕/모름 같은 표시는 글자 그대로 둔다.
"""
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "products" / "specs.csv"
JSON = ROOT / "data" / "products" / "specs.json"

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


def main():
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
