"""docs/00-기획안.md + docs/01-유저시나리오.md → docs/00-기획안.html (한 파일, 외부 CDN 없음)

실행: uv run --with markdown python docs/build_html.py
- 이미지(docs/img/*.png)는 base64로 넣는다.
- md의 ASCII 그림 두 개(지그재그 경로, 우회 경로)는 SVG 그림으로 바꿔 넣는다.
- 쓰레기 품목 비율 막대그림(환경운동연합 2020 성상조사, 출처 [2])을 1-1절 뒤에 넣는다.
"""
import base64
import html
import re
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
MD_MAIN = DOCS / "00-기획안.md"
MD_SCEN = DOCS / "01-유저시나리오.md"
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
def svg_litter_chart() -> str:
    data = [  # (품목, 개수, 우리 범위)
        ("담배꽁초", 6488, "대상 2 · 솔"),
        ("비닐봉지·포장지", 1965, "안 함"),
        ("일회용 종이컵", 655, "대상 1 · 집게"),
        ("일회용 플라스틱 컵", 654, "대상 1 · 집게"),
        ("일회용 마스크", 301, "안 함"),
        ("나머지 7개 품목", 1992, "확인 필요"),
    ]
    total = 12055
    W, row, left, barw = 640, 34, 150, 330
    H = row * len(data) + 40
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="길에서 주운 쓰레기 12,055점의 품목별 개수" class="chart">']
    for i, (name, n, tag) in enumerate(data):
        y = 10 + i * row
        w = max(2, barw * n / data[0][1])
        pct = 100 * n / total
        out.append(f'<g><title>{name}: {n:,}점 ({pct:.1f}%) · {tag}</title>'
                   f'<text x="{left-10}" y="{y+18}" text-anchor="end" class="t-label">{name}</text>'
                   f'<rect x="{left}" y="{y+5}" width="{w:.1f}" height="18" rx="4" class="bar"/>'
                   f'<text x="{left+w+8:.1f}" y="{y+18}" class="t-val">{n:,} ({pct:.1f}%)</text>'
                   f'<text x="{W-4}" y="{y+18}" text-anchor="end" class="t-tag">{tag}</text></g>')
    out.append(f'<text x="{left}" y="{H-6}" class="t-note">환경운동연합 2020 성상조사, 전국 13개 지역 12,055점 (출처 [2]). 나머지 7개 품목 내역은 확인 필요.</text>')
    out.append("</svg>")
    return "".join(out)


def svg_zigzag() -> str:
    # 5 m × 3 m 띠, 1 m = 110 px
    s, ox, oy = 110, 40, 40
    W, H = ox * 2 + 5 * s, oy + 3 * s + 70
    lines_y = [0.25 + 0.43 * k for k in range(7)]  # 줄 위치(가정, 줄 간격 약 0.43~0.47 m 표시용)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="가게 앞 5 m × 3 m 구역을 직선 줄로 훑는 경로와 화분 우회" class="diagram">']
    out.append(f'<rect x="{ox}" y="{oy}" width="{5*s}" height="{3*s}" class="area"/>')
    out.append(f'<line x1="{ox}" y1="{oy}" x2="{ox+5*s}" y2="{oy}" class="wall"/>'
               f'<text x="{ox}" y="{oy-10}" class="t-label">가게 벽</text>')
    out.append(f'<line x1="{ox}" y1="{oy+3*s}" x2="{ox+5*s}" y2="{oy+3*s}" class="curb"/>'
               f'<text x="{ox}" y="{oy+3*s+18}" class="t-label">연석 (차도 쪽, 넘지 않음)</text>')
    # 첫 줄의 팔 띠(오른쪽 = 아래쪽)
    y0 = oy + lines_y[0] * s
    out.append(f'<rect x="{ox+4}" y="{y0+0.42*s*0.5:.1f}" width="{5*s-8}" height="{0.52*s*0.5:.1f}" class="band"><title>첫 줄에서 팔이 닿는 띠 (로봇 오른쪽 0.42~0.94 m, 그림은 축소)</title></rect>')
    # 화분
    px, py = ox + 2.6 * s, oy + lines_y[3] * s
    out.append(f'<rect x="{px-18}" y="{py-18}" width="36" height="36" rx="4" class="obst"><title>고정 장애물(화분): 0.30 m 앞에서 멈춘 뒤 우회해 같은 줄로 복귀</title></rect>'
               f'<text x="{px}" y="{py+4}" text-anchor="middle" class="t-small">화분</text>')
    pts = []
    for k, ly in enumerate(lines_y):
        y = oy + ly * s
        xa, xb = (ox + 12, ox + 5 * s - 12) if k % 2 == 0 else (ox + 5 * s - 12, ox + 12)
        if k == 3:  # 우회
            d = 1 if xb > xa else -1
            x1 = px - d * 52
            x2 = px + d * 52
            yb = y - 40
            out.append(f'<path d="M{xa} {y} L{x1} {y} L{x1+d*14} {yb} L{x2-d*14} {yb} L{x2} {y} L{xb} {y}" class="path"/>')
            out.append(f'<circle cx="{x1}" cy="{y}" r="4" class="stop"><title>멈춤 (0.30 m 앞)</title></circle>')
        else:
            out.append(f'<line x1="{xa}" y1="{y}" x2="{xb}" y2="{y}" class="path"/>')
        ah = 8 if xb > xa else -8
        out.append(f'<path d="M{xb-ah} {y-5} L{xb} {y} L{xb-ah} {y+5}" class="arrow"/>')
        if k < len(lines_y) - 1:
            y2 = oy + lines_y[k + 1] * s
            out.append(f'<line x1="{xb}" y1="{y}" x2="{xb}" y2="{y2}" class="shift"/>')
        pts.append(y)
    # 사람
    hx, hy = ox + 1.2 * s, oy + lines_y[5] * s
    out.append(f'<circle cx="{hx}" cy="{hy-26}" r="9" class="person"><title>사람: 피하지 않고 1 m 안이면 멈춰서 기다림</title></circle>'
               f'<text x="{hx+14}" y="{hy-22}" class="t-small">사람 → 멈춰서 기다림</text>')
    # 좁은 틈
    gx = ox + 4.6 * s
    out.append(f'<rect x="{gx-6}" y="{oy+2}" width="30" height="{lines_y[1]*s-6:.0f}" class="skip"><title>좁은 틈: 건너뛰고 \'청소 못 한 구역\'으로 기록</title></rect>')
    # 범례
    ly = oy + 3 * s + 40
    out.append(f'<line x1="{ox}" y1="{ly}" x2="{ox+30}" y2="{ly}" class="path"/><text x="{ox+36}" y="{ly+4}" class="t-small">줄 (직진)</text>'
               f'<line x1="{ox+120}" y1="{ly}" x2="{ox+150}" y2="{ly}" class="shift"/><text x="{ox+156}" y="{ly+4}" class="t-small">줄 끝: 돌지 않고 옆 칸으로(후진)</text>'
               f'<rect x="{ox+350}" y="{ly-7}" width="24" height="14" class="band"/><text x="{ox+380}" y="{ly+4}" class="t-small">팔이 닿는 띠</text>'
               f'<rect x="{ox+470}" y="{ly-7}" width="24" height="14" class="skip"/><text x="{ox+500}" y="{ly+4}" class="t-small">청소 못 한 구역</text>')
    out.append("</svg>")
    return "".join(out)


def svg_bypass() -> str:
    W, H = 620, 170
    y, yb = 110, 50
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="고정 장애물 우회 경로" class="diagram">']
    out.append(f'<rect x="270" y="{y-25}" width="80" height="50" rx="6" class="obst"/><text x="310" y="{y+5}" text-anchor="middle" class="t-small">화분</text>')
    out.append(f'<path d="M20 {y} L200 {y} L230 {yb} L390 {yb} L420 {y} L600 {y}" class="path"/>')
    out.append(f'<path d="M592 {y-5} L600 {y} L592 {y+5}" class="arrow"/>')
    out.append(f'<line x1="20" y1="{y}" x2="600" y2="{y}" class="ghost"/>')
    out.append(f'<circle cx="200" cy="{y}" r="5" class="stop"/><text x="200" y="{y+24}" text-anchor="middle" class="t-small">① 0.30 m 앞 멈춤</text>')
    out.append(f'<text x="310" y="{yb-10}" text-anchor="middle" class="t-small">② 팔 반대쪽(치운 쪽)으로 비켜 지나감</text>')
    out.append(f'<circle cx="420" cy="{y}" r="5" class="stop"/><text x="440" y="{y+24}" text-anchor="middle" class="t-small">③ 끝 + 여유 뒤 같은 줄로 복귀 (±5 cm)</text>')
    out.append(f'<text x="20" y="{y-8}" class="t-small">원래 줄</text>')
    out.append("</svg>")
    return "".join(out)


CSS = """
:root{--bg:#fbfaf7;--surface:#ffffff;--ink:#1d1f23;--ink2:#4a4f57;--muted:#767c86;--line:#e3e1db;--accent:#1f6f5c;--accent-soft:#e3f1ec;--warn:#9a5b00;--warn-soft:#fdf1dc;--bar:#2f7d68;--obst:#8a8f98;--skip:#d9822b;--code:#f3f1ec}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15171a;--surface:#1d2024;--ink:#eceae4;--ink2:#c4c7cc;--muted:#9aa0a8;--line:#30343a;--accent:#5cc3a3;--accent-soft:#1d3a32;--warn:#f0b35a;--warn-soft:#3a2c17;--bar:#5cc3a3;--obst:#8a8f98;--skip:#e39a4c;--code:#24272c}}
:root[data-theme="dark"]{--bg:#15171a;--surface:#1d2024;--ink:#eceae4;--ink2:#c4c7cc;--muted:#9aa0a8;--line:#30343a;--accent:#5cc3a3;--accent-soft:#1d3a32;--warn:#f0b35a;--warn-soft:#3a2c17;--bar:#5cc3a3;--obst:#8a8f98;--skip:#e39a4c;--code:#24272c}
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
        if "줄 1" in b and "연석" in b:
            h = h.replace(f"<pre><code>{b}</code></pre>", f"<figure>{svg_zigzag()}<figcaption>그림. 5 m × 3 m 가게 앞을 직선 줄로 훑는 경로 (위에서 본 그림, 줄 간격·위치는 가정). 마우스를 올리면 설명이 나온다.</figcaption></figure>")
        elif "우회 경로" in b:
            h = h.replace(f"<pre><code>{b}</code></pre>", f"<figure>{svg_bypass()}<figcaption>그림. 고정 장애물 우회 규칙 (멈춤 거리 0.30 m, 복귀 오차 ±5 cm는 가정).</figcaption></figure>")
    return h


def main():
    main_md = MD_MAIN.read_text()
    scen_md = MD_SCEN.read_text()
    # 시나리오 문서 링크 → 같은 페이지 안 앵커
    main_md = main_md.replace("(01-유저시나리오.md)", "(#scenario)")
    scen_md = scen_md.replace("(00-기획안.md)", "(#top)")

    # 제목·머리말은 hero로 따로 만든다
    lines = main_md.split("\n")
    body_md = "\n".join(lines[3:])
    h_main = md_to_html(body_md)
    # 1-1 표 뒤에 막대그림
    h_main = h_main.replace("<h3>1-2.", f"<figure>{svg_litter_chart()}</figure><h3>1-2.", 1)
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
    toc_html += '<li><a href="#scenario">부록 B. 유저 시나리오 전문</a></li>'

    cards = [
        ("대상", "컵·캔은 집게, 꽁초는 회전 솔. 비닐·전단지·액체·유리는 안 함"),
        ("이동 전략", "직선 줄로 훑고 팔이 닿는 것만 멈춰서 집기. 장애물은 우회 뒤 같은 줄로"),
        ("운행 조건", "건조한 평탄 보도, 경사 1/25 이하, 턱 1 cm 이하, 영업 전 아침 1회"),
        ("성공 기준(시뮬)", "커버리지 95%, 10개 중 8개, 720 s, 충돌 0"),
        ("실물", "메카넘 축소판, 실내 2 m × 2 m, 3개 중 2개, 5분"),
        ("4주", "11/23 ~ 12/18 · 1주 정하기 → 2주 한 개 → 3주 열 개·측정 → 4주 시연"),
    ]
    cards_html = "".join(f'<div class="card"><b>{a}</b><span>{b}</span></div>' for a, b in cards)

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>가게 앞 청소로봇 기획안</title>
<meta name="description" content="새싹 팀프로젝트 litter-bot 기획안 v1.0 — 가게 앞 청소로봇 (MuJoCo Stretch 3 시뮬 + 메카넘 축소판)">
<style>{CSS}</style></head>
<body><div class="wrap" id="top">
<header class="hero">
<div class="kicker">litter-bot · 기획안 v1.0 · 2026-11-23</div>
<h1>가게 앞 청소로봇</h1>
<p class="lede">영업 전 아침, 가게 앞 평평한 보도에 버려진 컵·캔은 집게로 집고 꽁초는 회전 솔로 쓸어 담는다. 이번 4주에는 컵·캔 집기를 MuJoCo(Stretch 3)로 입증하고, 메카넘 축소판으로 실내에서 시연한다.</p>
<div class="meta">작성 최현준(PM·시뮬·개발·QA, 1인 팀) · 검토 AI 심사위원 리뷰 1회 + grok 2차 의견 · 숫자 옆 (가정)·(확인 필요)·(실측) 표시를 꼭 함께 읽을 것</div>
<div class="cards">{cards_html}</div>
</header>
<nav class="toc"><b>목차</b><ol>{toc_html}</ol></nav>
<main>{wrap_tables(h_all)}
<section class="part" id="scenario"><div class="part-title">부록 B</div><h1 style="font-size:30px">유저 시나리오 전문 (docs/01-유저시나리오.md)</h1>{wrap_tables(h_scen)}</section>
</main>
<footer>원본: docs/00-기획안.md, docs/01-유저시나리오.md · 이 페이지는 docs/build_html.py로 만든다 · 그림 1·2는 MuJoCo 직접 렌더 · 기사 사진은 넣지 않고 출처 링크만 둔다.</footer>
</div></body></html>"""
    OUT.write_text(page)
    print(OUT, f"{len(page)/1024:.0f} KB")


if __name__ == "__main__":
    main()
