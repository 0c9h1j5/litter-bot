"""docs/00-기획안.md + docs/01-유저시나리오.md → docs/00-기획안.html (한 파일, 외부 CDN 없음)

실행: uv run --with markdown python docs/build_html.py
- 이미지(docs/img/*.png)는 base64로 넣는다.
- md의 ASCII 그림(체육관 장면 위에서 본 그림)은 SVG 그림으로 바꿔 넣는다 (핫스폿 순회 + 직선 훑기).
- 부록: 유저 시나리오(01), 현장 계수표(02).
"""
import base64
import html
import re
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
MD_MAIN = DOCS / "00-기획안.md"
MD_SCEN = DOCS / "01-유저시나리오.md"
MD_FIELD = DOCS / "02-현장계수표.md"
OUT = DOCS / "00-기획안.html"


def fix_lists(text: str) -> str:
    """python-markdown은 목록 앞에 빈 줄이 있어야 목록으로 본다. 문단 바로 뒤 목록에 빈 줄을 넣는다."""
    out, prev, in_code = [], "", False
    item = re.compile(r"^(\d+\.|-) ")
    for line in text.split("\n"):
        if line.startswith("```"):
            in_code = not in_code
        if (not in_code and item.match(line) and prev.strip() and not item.match(prev.lstrip())
                and not prev.startswith("|") and not prev.startswith("  ")):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def md_to_html(text: str) -> str:
    h = markdown.markdown(fix_lists(text), extensions=["tables", "fenced_code", "sane_lists"])
    return re.sub(r"<hr\s*/?>", "", h)


def embed_images(h: str) -> str:
    def rep(m):
        src = m.group(1)
        p = DOCS / src
        if not p.exists():
            return m.group(0)
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f'src="data:image/png;base64,{b64}"'
    return re.sub(r'src="(img/[^"]+\.png)"', rep, h)


# ---------- SVG 그림 ----------
def svg_gym() -> str:
    """gym_v0 장면(5 m x 3 m)을 위에서 본 그림. x: -2.5~2.5 (오른쪽 = 끝 벽), y: -1.5~1.5 (위 = 옆 벽)."""
    s, ox, oy = 112, 30, 30
    X = lambda x: ox + (x + 2.5) * s
    Y = lambda y: oy + (1.5 - y) * s
    W, H = int(ox * 2 + 5 * s), int(oy + 3 * s + 80)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="체육관 장면을 위에서 본 그림: 핫스폿 순회 경로와 밀대 직선 훑기 줄" class="diagram">']
    o.append(f'<rect x="{X(-2.5)}" y="{Y(1.5)}" width="{5*s}" height="{3*s}" class="floor"/>')
    # 코트 안 (밀대 구역)
    o.append(f'<rect x="{X(-2.5)}" y="{Y(0.6)}" width="{4.5*s}" height="{2.1*s}" class="court"><title>코트 안 4.5 m × 2.1 m — 모드 2 밀대 구역</title></rect>')
    # 밀대 줄 (줄 간격 0.27 m)
    ys = [0.45 - 0.27 * k for k in range(8)]
    for k, yy in enumerate(ys):
        xa, xb = (X(-2.35), X(1.85)) if k % 2 == 0 else (X(1.85), X(-2.35))
        o.append(f'<line x1="{xa:.1f}" y1="{Y(yy):.1f}" x2="{xb:.1f}" y2="{Y(yy):.1f}" class="mop"/>')
        if k < len(ys) - 1:
            o.append(f'<line x1="{xb:.1f}" y1="{Y(yy):.1f}" x2="{xb:.1f}" y2="{Y(ys[k+1]):.1f}" class="mop-shift"/>')
    # 라인·벽
    o.append(f'<line x1="{X(-2.5)}" y1="{Y(0.6)}" x2="{X(2.0)}" y2="{Y(0.6)}" class="cline"/>'
             f'<line x1="{X(2.0)}" y1="{Y(0.6)}" x2="{X(2.0)}" y2="{Y(-1.5)}" class="cline"/>')
    o.append(f'<line x1="{X(-2.5)}" y1="{Y(1.5)}" x2="{X(2.5)}" y2="{Y(1.5)}" class="wall"/>'
             f'<line x1="{X(2.5)}" y1="{Y(1.5)}" x2="{X(2.5)}" y2="{Y(-1.5)}" class="wall"/>')
    o.append(f'<text x="{X(-2.45)}" y="{Y(1.5)-8}" class="t-label">옆 벽</text>'
             f'<text x="{X(2.5)}" y="{Y(1.5)-8}" text-anchor="end" class="t-label">끝 벽 (오른쪽)</text>'
             f'<text x="{X(-2.45)}" y="{Y(0.6)-6}" class="t-small">사이드라인</text>'
             f'<text x="{X(2.0)-6}" y="{Y(-1.0)}" text-anchor="end" class="t-small">엔드라인</text>')
    # 창문틀·벤치·의자·가방·공
    o.append(f'<rect x="{X(-1.5)}" y="{Y(1.5)}" width="{1.2*s}" height="{0.2*s}" class="sill"><title>창문틀 (확장): 윗면 1.0 m (가정), 깊이 0.20 m</title></rect>')
    o.append(f'<rect x="{X(-0.4)}" y="{Y(1.3)}" width="{2.0*s}" height="{0.4*s}" rx="3" class="obst"><title>선수 벤치 (길이 2 m, 높이 0.45 m)</title></rect>'
             f'<text x="{X(1.2)}" y="{Y(1.05)+4}" text-anchor="middle" class="t-on">선수 벤치</text>')
    o.append(f'<rect x="{X(1.7)}" y="{Y(1.35)}" width="{0.4*s}" height="{0.4*s}" rx="3" class="obst"><title>접이식 의자 (장애물)</title></rect>')
    o.append(f'<rect x="{X(-2.05)}" y="{Y(1.1)}" width="{0.5*s}" height="{0.3*s}" rx="3" class="obst"><title>가방 (소지품 — 집지 않음)</title></rect>'
             f'<text x="{X(-1.8)}" y="{Y(0.95)+4}" text-anchor="middle" class="t-on">가방</text>')
    o.append(f'<circle cx="{X(-1.4)}" cy="{Y(-0.3)}" r="{0.12*s:.1f}" class="ball"><title>농구공 — 장애물 (구 모양 규칙)</title></circle>')
    # 쓰레기
    items = [(0.1, 0.8), (0.9, 0.78), (1.3, 1.1), (0.4, 1.12), (-0.2, 0.85), (2.3, 1.3), (2.35, 0.95), (2.25, 0.7), (-1.2, 1.4), (-0.6, 1.4)]
    for x, y in items:
        o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="5" class="litter"/>')
    o.append(f'<circle cx="{X(0.3):.1f}" cy="{Y(-0.7):.1f}" r="5" class="litter"><title>핫스폿 밖에 떨어진 캔 — 모드 2 중 0.30 m 앞에서 멈추고 기록</title></circle>')
    # 순회 경로
    pts = [(-2.2, 0.3), (0.6, 0.3), (0.6, 0.72), (2.1, 0.95), (2.1, 0.47), (-0.9, 0.47), (-0.9, 0.85), (-1.35, 0.62), (-2.2, 0.3)]
    d = "M" + " L".join(f"{X(x):.1f} {Y(y):.1f}" for x, y in pts)
    o.append(f'<path d="{d}" class="route"><title>모드 1: 출발 → ① 벤치 구역 → ② 구석 → 복귀, ③ 창문틀은 확장 (가정)</title></path>')
    for i, (x, y, t) in enumerate([(0.6, 0.72, "벤치 구역"), (2.1, 0.95, "구석"), (-0.9, 0.85, "창문틀")]):
        o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="11" class="hot"/><text x="{X(x):.1f}" y="{Y(y)+4:.1f}" text-anchor="middle" class="t-hot">{i+1}</text>')
    o.append(f'<rect x="{X(-2.2)-9:.1f}" y="{Y(0.3)-9:.1f}" width="18" height="18" rx="3" class="start"><title>출발·충전 자리</title></rect>')
    # 범례
    ly = oy + 3 * s + 34
    o.append(f'<line x1="{ox}" y1="{ly}" x2="{ox+30}" y2="{ly}" class="route"/><text x="{ox+36}" y="{ly+4}" class="t-small">모드 1 핫스폿 순회 (①벤치 → ②구석, ③창문틀은 확장)</text>'
             f'<line x1="{ox+330}" y1="{ly}" x2="{ox+360}" y2="{ly}" class="mop"/><text x="{ox+366}" y="{ly+4}" class="t-small">모드 2 밀대 직선 훑기 (줄 간격 0.27 m)</text>'
             f'<circle cx="{ox+8}" cy="{ly+24}" r="5" class="litter"/><text x="{ox+20}" y="{ly+28}" class="t-small">병·캔·컵 (장면 배치, 가정)</text>'
             f'<rect x="{ox+330}" y="{ly+17}" width="24" height="14" class="sill"/><text x="{ox+360}" y="{ly+28}" class="t-small">창문틀 (확장, 높이 1.0 m 가정)</text>')
    o.append("</svg>")
    return "".join(o)


CSS = """
:root{--bg:#fbfaf7;--surface:#ffffff;--ink:#1d1f23;--ink2:#4a4f57;--muted:#767c86;--line:#e3e1db;--accent:#1f6f5c;--accent-soft:#e3f1ec;--warn:#9a5b00;--warn-soft:#fdf1dc;--bar:#2f7d68;--obst:#8a8f98;--skip:#d9822b;--code:#f3f1ec;--maru:#e6c89c;--maru2:#efd6ae}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15171a;--surface:#1d2024;--ink:#eceae4;--ink2:#c4c7cc;--muted:#9aa0a8;--line:#30343a;--accent:#5cc3a3;--accent-soft:#1d3a32;--warn:#f0b35a;--warn-soft:#3a2c17;--bar:#5cc3a3;--obst:#8a8f98;--skip:#e39a4c;--code:#24272c;--maru:#5a4630;--maru2:#6a523a}}
:root[data-theme="dark"]{--bg:#15171a;--surface:#1d2024;--ink:#eceae4;--ink2:#c4c7cc;--muted:#9aa0a8;--line:#30343a;--accent:#5cc3a3;--accent-soft:#1d3a32;--warn:#f0b35a;--warn-soft:#3a2c17;--bar:#5cc3a3;--obst:#8a8f98;--skip:#e39a4c;--code:#24272c;--maru:#5a4630;--maru2:#6a523a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard","Noto Sans KR","Malgun Gothic",sans-serif;word-break:keep-all;overflow-wrap:anywhere}
.wrap{max-width:980px;margin:0 auto;padding:0 16px 80px}
header.hero{padding:48px 0 24px;border-bottom:1px solid var(--line);margin-bottom:24px}
.kicker{color:var(--accent);font-weight:700;letter-spacing:.02em;font-size:14px}
h1{font-size:clamp(28px,5vw,42px);line-height:1.2;margin:8px 0 12px}
.lede{font-size:18px;color:var(--ink2);max-width:46em}
.meta{color:var(--muted);font-size:14px;margin-top:12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:24px 0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card b{display:block;color:var(--accent);font-size:13px;margin-bottom:4px}
.card span{font-size:15px}
nav.toc{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:16px 0 32px;font-size:14px}
nav.toc ol{margin:6px 0 0;padding-left:0;list-style:none;columns:2;column-gap:32px}
@media (max-width:640px){nav.toc ol{columns:1}}
nav.toc li{margin:2px 0}
nav.toc a{color:var(--ink2);text-decoration:none}nav.toc a:hover{color:var(--accent)}
h2{font-size:26px;margin:56px 0 12px;padding-top:12px;border-top:2px solid var(--ink)}
h3{font-size:19px;margin:32px 0 8px;color:var(--ink)}
p,li{color:var(--ink)}
a{color:var(--accent)}
blockquote{margin:16px 0;padding:10px 16px;background:var(--warn-soft);border-left:4px solid var(--warn);border-radius:6px;color:var(--ink)}
blockquote p{margin:4px 0}
.tbl{overflow-x:auto;margin:12px 0 20px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.55}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{background:var(--accent-soft);font-weight:700;white-space:nowrap}
tr:last-child td{border-bottom:0}
code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.9em}
pre{background:var(--code);padding:12px;border-radius:8px;overflow-x:auto;font-size:13px;line-height:1.4}
pre code{background:none;padding:0}
img{max-width:100%;height:auto;border-radius:10px;border:1px solid var(--line);display:block;margin:12px 0 4px}
figure{margin:16px 0 24px}
figcaption,em{color:var(--muted)}
svg{width:100%;height:auto;display:block;margin:12px 0}
svg .bar{fill:var(--bar)} svg .t-label{fill:var(--ink2);font-size:13px} svg .t-val{fill:var(--ink);font-size:13px;font-weight:600}
svg .t-tag{fill:var(--muted);font-size:12px} svg .t-note{fill:var(--muted);font-size:11px} svg .t-small{fill:var(--ink2);font-size:12px}
svg .area{fill:var(--surface);stroke:var(--line);stroke-width:1.5} svg .wall{stroke:var(--ink);stroke-width:4} svg .curb{stroke:var(--warn);stroke-width:4;stroke-dasharray:10 6}
svg .band{fill:var(--accent-soft);stroke:none} svg .obst{fill:var(--obst);opacity:.8} svg .skip{fill:var(--skip);opacity:.35}
svg .path{fill:none;stroke:var(--accent);stroke-width:2.5;stroke-linejoin:round} svg .shift{stroke:var(--accent);stroke-width:2;stroke-dasharray:4 4}
svg .arrow{fill:none;stroke:var(--accent);stroke-width:2.5} svg .stop{fill:var(--warn)} svg .person{fill:none;stroke:var(--warn);stroke-width:2.5}
svg .ghost{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 5}
svg .floor{fill:var(--maru);stroke:var(--line)} svg .court{fill:var(--maru2)} svg .cline{stroke:#fff;stroke-width:3}
svg .mop{stroke:var(--accent);stroke-width:2;opacity:.55;stroke-dasharray:6 4} svg .mop-shift{stroke:var(--accent);stroke-width:1.5;opacity:.4}
svg .route{fill:none;stroke:var(--warn);stroke-width:3;stroke-linejoin:round} svg .hot{fill:var(--warn)} svg .t-hot{fill:#fff;font-size:12px;font-weight:700}
svg .litter{fill:#2a7de1;stroke:#fff;stroke-width:1.2} svg .sill{fill:#8a6a4a} svg .ball{fill:#d9682b} svg .start{fill:var(--ink)} svg .t-on{fill:#fff;font-size:12px}
.part{margin-top:72px;padding:20px 0 0;border-top:6px double var(--line)}
.part-title{font-size:14px;color:var(--accent);font-weight:700}
footer{margin-top:64px;color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:16px}
"""


def wrap_tables(h: str) -> str:
    return h.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")


def slugify(h: str, prefix: str) -> tuple[str, list]:
    toc = []
    n = [0]

    def rep(m):
        n[0] += 1
        hid = f"{prefix}{n[0]}"
        text = re.sub("<[^>]+>", "", m.group(1))
        toc.append((hid, text))
        return f'<h2 id="{hid}">{m.group(1)}</h2>'
    return re.sub(r"<h2>(.*?)</h2>", rep, h), toc


def replace_ascii(h: str) -> str:
    blocks = re.findall(r"<pre><code>(.*?)</code></pre>", h, flags=re.S)
    for b in blocks:
        if "gym_v0" in b and "사이드라인" in b:
            h = h.replace(f"<pre><code>{b}</code></pre>", f"<figure>{svg_gym()}<figcaption>그림. 장면 gym_v0(5 m × 3 m)을 위에서 본 그림. 모드 1은 핫스폿(벤치·구석, 창문틀은 확장)을 돌며 집고, 모드 2는 코트 안을 직선 줄로 민다. 위치·줄 간격은 가정. 마우스를 올리면 설명이 나온다.</figcaption></figure>")
    return h


def main():
    main_md = MD_MAIN.read_text()
    scen_md = MD_SCEN.read_text()
    # 시나리오 문서 링크 → 같은 페이지 안 앵커
    main_md = main_md.replace("(01-유저시나리오.md)", "(#scenario)").replace("(02-현장계수표.md)", "(#field)")
    field_md = MD_FIELD.read_text().replace("(00-기획안.md)", "(#top)")
    h_field = md_to_html("\n".join(field_md.split("\n")[3:]))
    scen_md = scen_md.replace("(00-기획안.md)", "(#top)")

    # 제목·머리말은 hero로 따로 만든다
    lines = main_md.split("\n")
    body_md = "\n".join(lines[3:])
    h_main = md_to_html(body_md)
    h_main = replace_ascii(h_main)
    h_main, toc = slugify(h_main, "s")

    scen_lines = scen_md.split("\n")
    h_scen = md_to_html("\n".join(scen_lines[3:]))
    h_scen, toc2 = slugify(h_scen, "u")

    # 그림: md의 ![..](img/..) → figure
    h_all = h_main
    h_all = re.sub(r"<p><img ([^>]+)/?>\s*<em>(.*?)</em></p>", r"<figure><img \1><figcaption>\2</figcaption></figure>", h_all, flags=re.S)
    h_all = embed_images(h_all)

    toc_html = "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in toc)
    toc_html += '<li><a href="#scenario">부록 B. 유저 시나리오 전문</a></li><li><a href="#field">부록 C. 현장 계수표</a></li>'

    cards = [
        ("주 기능 · 밀기", "모터 없는 극세사 패드로 먼지·흙먼지·셔틀콕 깃털을 직선 줄로 민다. 성과 = 닦은 면적 %"),
        ("보조 · 집기", "벤치 쪽 생수병·구겨진 과자 봉지를 핫스폿 순회로 집는다. 분실물은 사진·알림"),
        ("운영 모드", "짧은 모드(벤치 + 벤치 앞 띠) / 전체 모드. 다음 팀 입장 전 끝, 사람 5~20분보다 짧게"),
        ("성공 기준(시뮬)", "커버리지 95% · 짧은 모드 360 s · 분실물 집기 0 · 수거율 80% · 충돌 0"),
        ("앞 모듈 교체형", "모듈 A 밀대(필수) ↔ 모듈 B 제설 날(확장). 여름~가을 체육관, 겨울 출입로"),
        ("근거·검증", "1차 근거 주인 회고(n≈10곳) → 11/24~30 계수로 확인 · 관리자 1명 이상 시험 운영 동의"),
    ]
    cards_html = "".join(f'<div class="card"><b>{a}</b><span>{b}</span></div>' for a, b in cards)

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>체육관 정리 로봇</title>
<meta name="description" content="새싹 팀프로젝트 litter-bot 기획안 v1.3 — 대관 사이 체육관 정리 로봇 (MuJoCo Stretch 3 시뮬 + 메카넘 축소판)">
<style>{CSS}</style></head>
<body><div class="wrap" id="top">
<header class="hero">
<div class="kicker">litter-bot · 기획안 v1.3 · 2026-11-23</div>
<h1>체육관 정리 로봇</h1>
<p class="lede">대관과 대관 사이, 코트의 먼지·흙먼지·셔틀콕 깃털을 극세사 밀대로 밀어 다음 팀이 미끄럽지 않게 하고(주 기능), 벤치 쪽 생수병·과자 봉지는 집게로 집는다(보조). 4주 동안 MuJoCo(Stretch 3)로 입증하고 메카넘 축소판으로 실내 마루에서 시연한다. 실제 체육관 운행은 시설 동의·안전 확인을 전제로 한다.</p>
<div class="meta">작성 최현준(PM·시뮬·개발·QA, 1인 팀) · 검토 AI 심사위원 리뷰 1회 · 숫자 옆 (가정)·(확인 필요)·(실측)·(주인 관찰)·(주인 회고) 표시를 꼭 함께 읽을 것</div>
<div class="cards">{cards_html}</div>
</header>
<nav class="toc"><b>목차</b><ol>{toc_html}</ol></nav>
<main>{wrap_tables(h_all)}
<section class="part" id="scenario"><div class="part-title">부록 B</div><h1 style="font-size:30px">유저 시나리오 전문 (docs/01-유저시나리오.md)</h1>{wrap_tables(h_scen)}</section>
<section class="part" id="field"><div class="part-title">부록 C</div><h1 style="font-size:30px">현장 계수표 (docs/02-현장계수표.md)</h1>{wrap_tables(h_field)}</section>
</main>
<footer>원본: docs/00-기획안.md, docs/01-유저시나리오.md, docs/02-현장계수표.md · 이 페이지는 docs/build_html.py로 만든다 · 그림 1·2는 MuJoCo 직접 렌더 · 현장 사진은 넣지 않고(얼굴 보호) 출처 링크만 둔다.</footer>
</div></body></html>"""
    OUT.write_text(page)
    print(OUT, f"{len(page)/1024:.0f} KB")


if __name__ == "__main__":
    main()
