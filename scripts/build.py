"""Gera os SVGs do README de perfil (whoami + contribuições).

Uso: python scripts/build.py
Dependência: Pillow. Roda localmente e no GitHub Actions (ver .github/workflows/update.yml).
"""
import io
import json
import re
import urllib.request
from datetime import date
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

USER = "Luizwiegert"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
BG, BAR, BORDER = "#0d1117", "#161b22", "#30363d"
FG, DIM, GREEN, BLUE = "#c9d1d9", "#8b949e", "#3fb950", "#58a6ff"
LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

INFO = [
    ("nome", "Luiz Eduardo Wiegert"),
    ("curso", "Sistemas de Informação · UNIVAG"),
    ("foco", "Dev AI-first"),
    ("ia", "Claude Code · MCP · Agentes · Automações"),
    ("stack", "React Native · Expo · Firebase · JS"),
    ("projetos", "Book-Level · Moviegram · JARVIS"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


# ---------- retrato ASCII ----------

RAMP = " .:-=+*#%@"
COLS, ROWS = 64, 32


def ascii_portrait(img):
    img = img.convert("RGB").resize((256, 256), Image.LANCZOS)
    # fundo de estúdio é cinza claro: pixels pouco saturados e claros,
    # ligados à borda da imagem, viram "vazio"
    hsv = img.convert("HSV")
    mask = Image.new("L", img.size, 0)
    pixels = getattr(hsv, "get_flattened_data", hsv.getdata)()
    mask.putdata([255 if s < 40 and 105 < v < 245 else 0 for _, s, v in pixels])
    key = 128
    for i in range(0, 256, 8):
        for seed in ((i, 0), (0, i), (255, i)):
            if mask.getpixel(seed) == 255:
                ImageDraw.floodfill(mask, seed, key)
    gray = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=2)
    gray = gray.resize((COLS, ROWS), Image.LANCZOS)
    mask = mask.resize((COLS, ROWS), Image.NEAREST)
    lines = []
    for y in range(ROWS):
        row = ""
        for x in range(COLS):
            if mask.getpixel((x, y)) == key:
                row += " "
            else:
                v = gray.getpixel((x, y)) / 255
                row += RAMP[1 + min(len(RAMP) - 2, int(v * (len(RAMP) - 1)))]
        lines.append(row.rstrip())
    while lines and not lines[0]:
        lines.pop(0)
    return lines


# ---------- peças de SVG ----------

def window(w, h, title, body, extra_css=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">
<style>
text{{font-family:{FONT};font-size:13px;fill:{FG}}}
.dim{{fill:{DIM}}}.g{{fill:{GREEN}}}.b{{fill:{BLUE}}}
.in{{opacity:0;animation:in .5s ease-out forwards}}
@keyframes in{{to{{opacity:1}}}}
.cur{{animation:blink 1s steps(1) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
{extra_css}
@media (prefers-reduced-motion:reduce){{.in,.cell{{animation:none;opacity:1}}.cur{{animation:none}}}}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<path d="M.5 34V10.5a10 10 0 0 1 10-10h{w - 21}a10 10 0 0 1 10 10V34z" fill="{BAR}"/>
<line x1=".5" y1="34" x2="{w - .5}" y2="34" stroke="{BORDER}"/>
<circle cx="20" cy="17" r="5.5" fill="#ff5f56"/><circle cx="38" cy="17" r="5.5" fill="#ffbd2e"/><circle cx="56" cy="17" r="5.5" fill="#27c93f"/>
<text x="{w / 2}" y="21.5" text-anchor="middle" class="dim" style="font-size:12px">{escape(title)}</text>
{body}
</svg>
"""


def prompt(y, cmd):
    return (f'<text x="24" y="{y}"><tspan class="g">luiz@github</tspan><tspan class="dim">:</tspan>'
            f'<tspan class="b">~</tspan><tspan class="dim">$ </tspan>{escape(cmd)}</text>')


def whoami_svg(portrait):
    w = 840
    art_x, art_y, art_w, lh = 24, 86, 300, 9.4
    out = [prompt(62, "whoami")]
    for i, line in enumerate(portrait):
        if not line.strip():
            continue
        tl = art_w * len(line) / COLS
        out.append(
            f'<text class="in" style="font-size:7.8px;animation-delay:{0.3 + i * 0.04:.2f}s" fill="{FG}" '
            f'x="{art_x}" y="{art_y + i * lh:.1f}" textLength="{tl:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve">{escape(line)}</text>')
    art_bottom = art_y + len(portrait) * lh

    x, y = 372, 104
    out.append(f'<text class="in" style="animation-delay:.5s" x="{x}" y="{y}">'
               f'<tspan class="g" font-weight="bold">luiz</tspan><tspan class="dim">@</tspan>'
               f'<tspan class="g" font-weight="bold">github</tspan></text>')
    out.append(f'<text class="in dim" style="animation-delay:.6s" x="{x}" y="{y + 20}">───────────</text>')
    for i, (k, v) in enumerate(INFO):
        yy = y + 46 + i * 26
        out.append(f'<text class="in" style="animation-delay:{0.7 + i * 0.12:.2f}s" x="{x}" y="{yy}">'
                   f'<tspan class="b">{escape(k)}</tspan><tspan x="{x + 76}">{escape(v)}</tspan></text>')
    py = y + 46 + len(INFO) * 26 + 6
    for i, c in enumerate(["#ff7b72", "#ffa657", "#e3b341", GREEN, BLUE, "#bc8cff", "#f778ba", FG]):
        out.append(f'<rect class="in" style="animation-delay:{1.5 + i * 0.05:.2f}s" x="{x + i * 26}" y="{py}" '
                   f'width="20" height="12" rx="2" fill="{c}"/>')

    h = int(art_bottom + 44)
    out.append(prompt(h - 22, "") + f'<rect class="cur" x="126" y="{h - 34}" width="8" height="15" fill="{FG}"/>')
    return window(w, h, "luiz@github: ~", "\n".join(out))


def contributions():
    html = fetch(f"https://github.com/users/{USER}/contributions").decode("utf-8")
    counts = {}
    for cid, text in re.findall(r'<tool-tip[^>]*for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)</tool-tip>', html):
        m = re.match(r"\s*(\d+) contribution", text)
        counts[cid] = int(m.group(1)) if m else 0
    days = []
    for tag in re.findall(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', html):
        d = re.search(r'data-date="([\d-]+)"', tag).group(1)
        cid = re.search(r'id="([^"]+)"', tag).group(1)
        lvl = int(re.search(r'data-level="(\d)"', tag).group(1))
        days.append((date.fromisoformat(d), lvl, counts.get(cid, 0)))
    days.sort()
    return days


def contributions_svg(days):
    w, cell, gap = 840, 11, 3
    step = cell + gap
    first = days[0][0]
    offset = (first.weekday() + 1) % 7  # domingo = linha 0
    weeks = (offset + len(days) + 6) // 7
    gx = (w - weeks * step + gap) / 2 + 12
    gy = 106
    total = sum(c for _, _, c in days)
    out = [prompt(62, "./contributions.sh")]
    for r, label in ((1, "seg"), (3, "qua"), (5, "sex")):
        out.append(f'<text class="dim" style="font-size:10px" x="{gx - 8}" y="{gy + r * step + 9}" text-anchor="end">{label}</text>')
    last_month = None
    for i, (d, lvl, n) in enumerate(days):
        col, row = divmod(offset + i, 7)
        x, y = gx + col * step, gy + row * step
        if d.month != last_month and d.day <= 7 and col < weeks - 1:
            out.append(f'<text class="dim" style="font-size:10px" x="{x}" y="{gy - 8}">{MESES[d.month - 1]}</text>')
            last_month = d.month
        tip = f"{n} em {d.strftime('%d/%m/%Y')}"
        out.append(f'<rect class="cell" style="animation-delay:{0.2 + col * 0.022:.2f}s" x="{x:.1f}" y="{y}" '
                   f'width="{cell}" height="{cell}" rx="2" fill="{LEVELS[lvl]}"><title>{tip}</title></rect>')
    fy = gy + 7 * step + 22
    plural = "contribuição" if total == 1 else "contribuições"
    out.append(f'<text x="{gx}" y="{fy}"><tspan class="g" font-weight="bold">{total}</tspan> {plural} no último ano</text>')
    lx = gx + weeks * step - gap - (5 * step - gap) - 34
    out.append(f'<text class="dim" style="font-size:10px" x="{lx + 5 * step + 5}" y="{fy - 1}">mais</text>')
    out.append(f'<text class="dim" style="font-size:10px" x="{lx - 8}" y="{fy - 1}" text-anchor="end">menos</text>')
    for i, c in enumerate(LEVELS):
        out.append(f'<rect x="{lx + i * step:.1f}" y="{fy - 10}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')
    css = (".cell{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .35s ease-out forwards}"
           "@keyframes pop{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:scale(1)}}")
    return window(w, int(fy + 24), "luiz@github: ~/contributions", "\n".join(out), css)


def main():
    ASSETS.mkdir(exist_ok=True)
    user = json.loads(fetch(f"https://api.github.com/users/{USER}"))
    avatar = Image.open(io.BytesIO(fetch(user["avatar_url"] + "&s=460")))
    portrait = ascii_portrait(avatar)
    (ASSETS / "whoami.svg").write_text(whoami_svg(portrait), encoding="utf-8")
    (ASSETS / "contributions.svg").write_text(contributions_svg(contributions()), encoding="utf-8")
    print("\n".join(portrait))


if __name__ == "__main__":
    main()
