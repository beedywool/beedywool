#!/usr/bin/env python3
"""Génère les SVG Material 3 (thème clair + sombre) utilisés par le README.

Le contenu (nom, bio, chanson, lieux, stack…) vient du portfolio : modifie-le là-bas
(Pages CMS), puis lance :  python3 build.py   (PORTFOLIO_URL=… pour tester un autre site)
"""
import base64
import colorsys
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

# ─── Valeurs de secours (le portfolio a la priorité, voir load_portfolio) ─────
NAME = "beedywool"
TAGLINE = "Full-stack developer"
GREETING = "👋  Hello, world"
PILLS = ["Web", "Cloud"]

BIO = ("I'm a full stack developer cumulating 10+ years of experience in development, starting with video games in middle school."
" My goal is to create innovative and immersives experiences spanning into the real world with AR and VR technologies to make it a little bit livelier, even for just a few minutes."
" The old spark technology used to have is what I am seeking.")

ABOUT = [
    ("Currently working on", "An online store for neo-retro consoles"),
    ("Currently learning", "Unity and VR/AR development"),
    ("My hobby", "Travel and technology"),]

# Seul le lien est obligatoire : titre, artiste et pochette viennent de YouTube
# (ajoute title= ou artist= pour les remplacer)
SONG = dict(
    url="https://www.youtube.com/watch?v=MSmfAa_oSqE",
    album="雑踏、僕らの街",
)

PLACES = [
    dict(key="home", label="Based in", city="Montpellier", country="France",
         tz="Europe/Paris", scene="montpellier", photo="assets/montpellier.jpg", flag="FR"),
    dict(key="dream", label="Where I want to go", city="Guadalajara", country="Mexico",
         tz="America/Mexico_City", scene="guadalajara", photo="assets/guadalajara.jpg", flag="MX"),
]

SECTIONS = {
    "about": "About me",
    "stats": "GitHub stats",
    "stack": "Tech stack",
}

STACK = {
    "Languages": [
        ("JavaScript", "javascript", "F7DF1E"), ("TypeScript", "typescript", "3178C6"),
        ("Python", "python", "FFD43B"), ("PHP", "php", "8892BF"),
        ("Bash", "gnubash", "4EAA25"), ("Markdown", "markdown", "FFFFFF"),
    ],
    "Data": [
        ("PostgreSQL", "postgresql", "6E9BF5"), ("MySQL", "mysql", "7FB3E0"),
        ("MariaDB", "mariadb", "C49A6C"), ("SQLite", "sqlite", "44A8E0"),
        ("MongoDB", "mongodb", "47A248"), ("Redis", "redis", "FF4438"),
        ("Elasticsearch", "elasticsearch", "FEC514"),
    ],
    "Frontend & apps": [
        ("React", "react", "61DAFB"), ("Vue.js", "vuedotjs", "4FC08D"),
        ("Angular", "angular", "FF4F6D"), ("Vite", "vite", "9499FF"),
        ("Sass", "sass", "CC6699"), ("jQuery", "jquery", "78CFF5"),
        ("WebGL", "webgl", "E34F4F"), ("Flutter", "flutter", "54C5F8"),
        ("Electron", "electron", "9FEAF9"),
    ],
    "Backend": [
        ("Node.js", "nodedotjs", "5FA04E"), ("Bun", "bun", "FBF0DF"),
        ("Express", "express", "FFFFFF"), ("Prisma", "prisma", "FFFFFF"),
        ("JWT", "jsonwebtokens", "FFFFFF"), ("WordPress", "wordpress", "3DA1D6"),
        ("Apache", "apache", "F05A5A"), ("Nginx", "nginx", "2ECC71"),
    ],
    "Cloud & DevOps": [
        ("Cloudflare", "cloudflare", "F38020"), ("Google Cloud", "googlecloud", "4285F4"),
        ("OVH", "ovh", "7AA7FF"), ("Docker", "docker", "2496ED"),
        ("GitHub Actions", "githubactions", "2088FF"), ("Jenkins", "jenkins", "D24939"),
        ("GitHub", "github", "FFFFFF"), ("GitLab", "gitlab", "FC6D26"),
        ("npm", "npm", "CB3837"),
    ],
    "Testing & quality": [
        ("Jest", "jest", "E5426D"), ("Vitest", "vitest", "FCC72B"),
        ("Playwright", "playwright", "2EAD33"), ("ESLint", "eslint", "8080F2"),
    ],
    "Design": [
        ("Figma", "figma", "F24E1E"), ("Canva", "canva", "00C4CC"),
        ("Blender", "blender", "F5792A"), ("Aseprite", "aseprite", "B8C6D1"),
    ],
    "Tools": [
        ("Postman", "postman", "FF6C37"), ("Swagger", "swagger", "85EA2D"),
        ("FFmpeg", "ffmpeg", "5CB85C"), ("Jira", "jira", "2684FF"),
        ("Confluence", "confluence", "4C9AFF"), ("Trello", "trello", "4C9AFF"),
        ("Crowdin", "crowdin", "FFFFFF"),
    ],
}
# ─────────────────────────────────────────────────────────────────────────────

SCHEMES = {
    "dark": dict(
        surface="141218", sc="211F26", sch="2B2930",
        primary="D0BCFF", pc="4F378B", on_pc="EADDFF",
        secondary="CCC2DC", secc="4A4458", on_secc="E8DEF8",
        tertiary="EFB8C8", tc="633B48", on_tc="FFD8E4",
        on_surface="E6E0E9", on_sv="CAC4D0", outline="938F99", outline_v="49454F",
    ),
    "light": dict(
        surface="FEF7FF", sc="F3EDF7", sch="ECE6F0",
        primary="6750A4", pc="EADDFF", on_pc="21005D",
        secondary="625B71", secc="E8DEF8", on_secc="1D192B",
        tertiary="7D5260", tc="FFD8E4", on_tc="31111D",
        on_surface="1D1B20", on_sv="49454F", outline="79747E", outline_v="CAC4D0",
    ),
}

FONT = "'Google Sans Flex','Google Sans','Roboto Flex',Roboto,'Segoe UI',system-ui,sans-serif"
OUT = Path(__file__).parent / "assets"
ICONS = Path(__file__).parent / "icons"
CARDS = Path(__file__).parent / "cards"
W, GAP = 1000, 12
# Certaines icônes (ex. Playwright) ont disparu des versions récentes
ICON_SOURCES = ["13.21.0", "9.21.0"]
CACHE = Path(__file__).parent / ".cache"


def polar_shape(cx, cy, r, lobes, depth, steps=240):
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        rr = r * (1 + depth * math.cos(lobes * t))
        pts.append(f"{cx + rr * math.cos(t):.2f},{cy + rr * math.sin(t):.2f}")
    return "M" + " L".join(pts) + " Z"


SHAPES = {
    "cookie": (9, 0.07),
    "clover": (4, 0.17),
    "sunny": (8, 0.10),
    "flower": (6, 0.13),
}


def shape(kind, cx, cy, r):
    lobes, depth = SHAPES[kind]
    return polar_shape(cx, cy, r, lobes, depth)


def base_style(c):
    return f"""<style>
  text {{ font-family: {FONT}; }}
  .spin  {{ transform-box: fill-box; transform-origin: center; animation: spin 48s linear infinite; }}
  .spinr {{ transform-box: fill-box; transform-origin: center; animation: spin 36s linear infinite reverse; }}
  .float {{ animation: float 6s ease-in-out infinite; }}
  .fade  {{ animation: fade .8s cubic-bezier(.2,0,0,1) backwards; }}
  @keyframes spin  {{ to {{ transform: rotate(360deg); }} }}
  @keyframes float {{ 50% {{ transform: translateY(-8px); }} }}
  @keyframes fade  {{ from {{ opacity: 0; transform: translateY(12px); }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


# Chasse (‰ d'em) des caractères ASCII 32→126 en graisse Medium, moyenne de
# Google Sans et Noto Sans : sert à coller un élément juste après un texte
_WIDTHS = """246 266 393 650 564 848 688 218 326 326 496 570 266 386 266 354 614 508 556
564 590 570 569 556 574 569 266 266 542 576 542 473 894 676 637 688 724 561 539 770 731
312 419 644 530 900 750 807 600 807 624 559 558 710 637 952 630 596 582 335 354 335 530
460 363 558 617 522 617 573 367 614 604 252 252 544 252 918 602 607 617 617 409 486 386
602 534 805 520 534 487 354 404 354 560""".split()
CHAR_EM = {chr(32 + i): int(v) / 1000 for i, v in enumerate(_WIDTHS)}


def title_width(s, size):
    return sum(CHAR_EM.get(ch, .6) for ch in s) * size


def text_width(s, size):
    return sum(0.68 if ch.isupper() else 0.56 for ch in s) * size


def header(c):
    w, h = W, 300
    dx = W - 900
    pills, x = [], 48
    fills = [(c["pc"], c["on_pc"]), (c["secc"], c["on_secc"]), (c["tc"], c["on_tc"])]
    for i, label in enumerate(PILLS):
        bg, fg = fills[i % 3]
        pw = text_width(label, 15) + 40
        pills.append(
            f'<rect x="{x}" y="226" width="{pw:.0f}" height="40" rx="20" fill="#{bg}"/>'
            f'<text x="{x + pw / 2:.0f}" y="251" font-size="15" font-weight="500" '
            f'text-anchor="middle" fill="#{fg}">{escape(label)}</text>'
        )
        x += pw + 8
    # Les emoji sont plus larges que les lettres : environ 0,8 em
    chip_w = title_width(GREETING, 14) + 28 + sum(.2 * 14 for ch in GREETING if ord(ch) > 0xFFFF)
    px = 48 + chip_w + 8
    pride_w = 12 + 24 + 12 if PRIDE else 0
    stripes = "".join(
        f'<rect x="{px + 12}" y="{52 + i * 16 / 6:.2f}" width="24" height="{16 / 6 + .3:.2f}" fill="#{col}"/>'
        for i, col in enumerate(["E40303", "FF8C00", "FFED00", "008026", "004CFF", "732982"])
    )
    pride = (f'<rect x="{px}" y="44" width="{pride_w:.0f}" height="32" rx="8" fill="none" stroke="#{c["outline"]}"/>'
             f'<clipPath id="pride"><rect x="{px + 12}" y="52" width="24" height="16" rx="3"/></clipPath>'
             f'<g clip-path="url(#pride)">{stripes}</g>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>{escape(NAME)} | {escape(TAGLINE)}</title>
{base_style(c)}
<defs><clipPath id="card"><rect width="{w}" height="{h}" rx="36"/></clipPath></defs>
<g clip-path="url(#card)">
  <rect width="{w}" height="{h}" fill="#{c['sc']}"/>
  <path class="spin" d="{shape('cookie', 705 + dx, 135, 118)}" fill="#{c['pc']}"/>
  <text x="{705 + dx}" y="152" font-size="52" font-weight="500" text-anchor="middle" fill="#{c['on_pc']}"
        style="font-family:'JetBrains Mono','Fira Code',ui-monospace,monospace">&lt;/&gt;</text>
  <path class="spinr" d="{shape('clover', 845 + dx, 262, 78)}" fill="#{c['tc']}"/>
  <path class="spin" d="{shape('sunny', 585 + dx, 262, 38)}" fill="#{c['secc']}"/>
  <g class="float"><circle cx="{840 + dx}" cy="52" r="14" fill="#{c['primary']}"/></g>
  <rect x="{530 + dx}" y="22" width="88" height="34" rx="17" fill="#{c['outline_v']}" transform="rotate(-24 {574 + dx} 39)"/>
</g>
<g class="fade">
  <rect x="48" y="44" width="{chip_w:.0f}" height="32" rx="8" fill="none" stroke="#{c['outline']}"/>
  <text x="62" y="65" font-size="14" font-weight="500" fill="#{c['on_sv']}">{escape(GREETING)}</text>
  {pride if PRIDE else ''}
  <text x="44" y="158" font-size="68" font-weight="500" letter-spacing="-1" fill="#{c['on_surface']}">{escape(NAME)}</text>
  <text x="48" y="198" font-size="21" fill="#{c['on_sv']}">{escape(TAGLINE)}</text>
  {''.join(pills)}
</g>
</svg>
"""


def section(c, key, title, kind, index):
    w, h, top = W, 72 + 28, 28
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>{escape(title)}</title>
{base_style(c)}
<g transform="translate(0 {top})">
<path class="spin" d="{shape(kind, 36, 36, 30)}" fill="#{c['pc']}"/>
<text x="36" y="42" font-size="16" font-weight="600" text-anchor="middle" fill="#{c['on_pc']}">{index:02d}</text>
<text x="84" y="46" font-size="30" font-weight="500" fill="#{c['on_surface']}">{escape(title)}</text>
<rect x="{108 + text_width(title, 30):.0f}" y="35" width="{max(0, w - 108 - text_width(title, 30)):.0f}" height="2" rx="1" fill="#{c['outline_v']}"/>
</g>
</svg>
"""


def wrap(s, n, max_lines=3):
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > n:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    return lines[:max_lines]


def bio(c):
    lines = wrap(BIO, 68, 6)
    w, h = W, 92 + 32 * len(lines)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>Introduction</title>
{base_style(c)}
<defs><clipPath id="bio"><rect width="{w}" height="{h}" rx="28"/></clipPath></defs>
<g class="fade" clip-path="url(#bio)">
  <rect width="{w}" height="{h}" fill="#{c['sc']}"/>
  <path class="spin" d="{shape('flower', W - 70, h - 10, 120)}" fill="#{c['pc']}"/>
  <path class="spinr" d="{shape('cookie', W - 188, 26, 38)}" fill="#{c['tc']}"/>
  <text x="28" y="50" font-size="17" font-weight="500" fill="#{c['primary']}">Hi, I'm {escape(NAME)}</text>
  <text x="28" y="94" font-size="22" fill="#{c['on_surface']}">{"".join(f'<tspan x="28" dy="{0 if j == 0 else 32}">{escape(l)}</tspan>' for j, l in enumerate(lines))}</text>
</g>
</svg>
"""


def facts(c):
    cols, gap, ch = 3, GAP, 208
    cw = (W - (cols - 1) * gap) / cols
    rows = math.ceil(len(ABOUT) / cols)
    w, h = W, rows * ch + (rows - 1) * gap
    tones = [("pc", "on_pc"), ("secc", "on_secc"), ("tc", "on_tc")]
    kinds = ["cookie", "clover", "sunny", "flower"]
    cards = []
    for i, (label, value) in enumerate(ABOUT):
        x, y = (i % cols) * (cw + gap), (i // cols) * (ch + gap)
        bg, _ = tones[i % 3]
        lines = "".join(
            f'<tspan x="{x + 24}" dy="{0 if j == 0 else 28}">{escape(l)}</tspan>'
            for j, l in enumerate(wrap(value, 25))
        )
        cards.append(f"""<g class="fade" style="animation-delay:{i * 90}ms">
  <rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="24" fill="#{c['sc']}"/>
  <path d="{shape(kinds[i % 4], x + 46, y + 46, 22)}" fill="#{c[bg]}"/>
  <text x="{x + 24}" y="{y + 108}" font-size="17" font-weight="500" fill="#{c['on_sv']}">{escape(label)}</text>
  <text x="{x + 24}" y="{y + 144}" font-size="22" fill="#{c['on_surface']}">{lines}</text>
</g>""")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>Right now</title>
{base_style(c)}
{''.join(cards)}
</svg>
"""


def favorites(c):
    # Comme sur le portfolio : cartes côte à côte, 2 éléments + une tuile « +N » (le README
    # ne peut pas se déplier, la carte entière mène à la section Favorites du portfolio)
    shown, cols, pad, gap = 2, 2, 24, 12
    cw = (W - (cols - 1) * GAP) / cols
    tile_w = (cw - 2 * pad - 2 * gap) / 3
    tile_h = tile_w * 4 / 3
    card_h = 74 + tile_h + 44
    on_p = c['pc'] if c is SCHEMES['dark'] else 'FFFFFF'
    cards = []
    for gi, group in enumerate(FAVORITES):
        cx, cy = (gi % cols) * (cw + GAP), (gi // cols) * (card_h + GAP)
        tiles = []
        for i, item in enumerate(group["items"][:shown]):
            x, y = pad + i * (tile_w + gap), 74
            cid = f"fav{gi}-{i}"
            raw = cached_download(item["image"]) if item.get("image") else None
            if item.get("logo"):
                bg, fit, inset = "FEF7FF", "xMidYMid meet", 14
            else:
                bg, fit, inset = c["sch"], "xMidYMid slice", 0
            art = (f'<image href="data:image/webp;base64,{base64.b64encode(raw).decode()}" x="{x + inset:.1f}" y="{y + inset}" '
                   f'width="{tile_w - 2 * inset:.1f}" height="{tile_h - 2 * inset:.1f}" preserveAspectRatio="{fit}"/>') if raw else ""
            tiles.append(f"""<clipPath id="{cid}"><rect x="{x:.1f}" y="{y}" width="{tile_w:.1f}" height="{tile_h:.1f}" rx="16"/></clipPath>
    <g clip-path="url(#{cid})"><rect x="{x:.1f}" y="{y}" width="{tile_w:.1f}" height="{tile_h:.1f}" fill="#{bg}"/>{art}</g>
    <text x="{x:.1f}" y="{y + tile_h + 24:.1f}" font-size="15" font-weight="500" fill="#{c['on_surface']}">{escape(item['name'])}</text>""")
        rest = len(group["items"]) - shown
        if rest > 0:
            x = pad + shown * (tile_w + gap)
            tiles.append(f"""<rect x="{x:.1f}" y="74" width="{tile_w:.1f}" height="{tile_h:.1f}" rx="16" fill="#{c['secc']}"/>
    <text x="{x + tile_w / 2:.1f}" y="{74 + tile_h / 2:.1f}" font-size="28" font-weight="500" text-anchor="middle" fill="#{c['on_secc']}">+{rest}</text>
    <text x="{x + tile_w / 2:.1f}" y="{74 + tile_h / 2 + 26:.1f}" font-size="14" text-anchor="middle" fill="#{c['on_secc']}">Show all</text>""")
        label_w = title_width(group["label"], 15) + 52
        icon_name = group.get("icon") if group.get("icon") in MI else "note"
        cards.append(f"""<g transform="translate({cx:.1f} {cy:.1f})" class="fade" style="animation-delay:{gi * 90}ms">
  <clipPath id="favcard{gi}"><rect width="{cw:.1f}" height="{card_h:.1f}" rx="28"/></clipPath>
  <g clip-path="url(#favcard{gi})">
    <rect width="{cw:.1f}" height="{card_h:.1f}" fill="#{c['sc']}"/>
    <path class="spin" d="{shape('flower' if gi % 2 == 0 else 'clover', cw - 30, 20, 58)}" fill="#{c['tc']}" opacity=".5"/>
  </g>
  <rect x="{pad}" y="22" width="{label_w:.0f}" height="34" rx="17" fill="#{c['primary']}"/>
  {icon(icon_name, pad + 12, 30, 18, on_p)}
  <text x="{pad + 36}" y="44" font-size="15" font-weight="600" fill="#{on_p}">{escape(group['label'])}</text>
  {''.join(tiles)}
</g>""")
    rows = max(1, math.ceil(len(FAVORITES) / cols))
    h = rows * card_h + (rows - 1) * GAP
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h:.0f}" viewBox="0 0 {W} {h:.0f}" role="img">
<title>Favorites</title>
{base_style(c)}
{''.join(cards)}
</svg>
"""


def portfolio_link(c):
    # Carte-bouton sous l'en-tête : le README ne peut pas avoir de vrai bouton, toute l'image est un lien
    h, bh = 104, 56
    site = PORTFOLIO.split("://", 1)[-1].rstrip("/")
    label = "Visit portfolio"
    bw = title_width(label, 17) + 24 + 26 + 24
    bx, by = W - 24 - bw, (h - bh) / 2
    on_p = c['pc'] if c is SCHEMES['dark'] else 'FFFFFF'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img">
<title>Visit my portfolio: {escape(site)}</title>
{base_style(c)}
<defs><clipPath id="cta"><rect width="{W}" height="{h}" rx="28"/></clipPath></defs>
<g class="fade" clip-path="url(#cta)">
  <rect width="{W}" height="{h}" fill="#{c['sc']}"/>
  <path class="spin" d="{shape('sunny', 52, 52, 26)}" fill="#{c['pc']}"/>
  {icon('outward', 40, 40, 24, c['on_pc'])}
  <text x="100" y="47" font-size="22" font-weight="500" fill="#{c['on_surface']}">Check out my portfolio</text>
  <text x="100" y="74" font-size="16" fill="#{c['on_sv']}">More about me and my projects</text>
  <rect x="{bx:.0f}" y="{by:.0f}" width="{bw:.0f}" height="{bh}" rx="28" fill="#{c['primary']}"/>
  <text x="{bx + 24:.0f}" y="{by + 35:.0f}" font-size="17" font-weight="600" fill="#{on_p}">{escape(label)}</text>
  {icon('outward', bx + bw - 24 - 22, by + 17, 22, on_p)}
</g>
</svg>
"""


def subsection(c, title, kind):
    # Titre de sous-partie, comme sur le portfolio : petite forme + titre, sans numéro ni trait
    w, h = W, 60
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>{escape(title)}</title>
{base_style(c)}
<g class="fade">
  <path d="{shape(kind, 14, 34, 13)}" fill="#{c['primary']}"/>
  <text x="40" y="43" font-size="24" font-weight="500" fill="#{c['on_surface']}">{escape(title)}</text>
</g>
</svg>
"""


def hobby(c):
    lines = wrap(TRAVEL["intro"], 74, 4)
    pad_x, top = 124, 50
    text_h = top + 44 + 30 * (len(lines) - 1)
    chips, x, y, chip_h = [], pad_x, text_h + 28, 40
    for name, code in TRAVEL["been"]:
        cw = 12 + 27 + 10 + title_width(name, 15) + 16
        if x + cw > W - 28:
            x, y = pad_x, y + chip_h + 8
        chips.append(f'<rect x="{x + .5:.1f}" y="{y + .5}" width="{cw - 1:.0f}" height="{chip_h - 1}" rx="8" fill="#{c["sc"]}" stroke="#{c["outline_v"]}"/>'
                     f'{flag(code.upper(), x + 12, y + 11)}'
                     f'<text x="{x + 49:.0f}" y="{y + 25}" font-size="15" font-weight="500" fill="#{c["on_surface"]}">{escape(name)}</text>')
        x += cw + 8
    h = (y + chip_h + 28) if chips else text_h + 30
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img">
<title>Hobby: travel</title>
{base_style(c)}
<defs><clipPath id="hobby"><rect width="{W}" height="{h}" rx="28"/></clipPath></defs>
<g class="fade" clip-path="url(#hobby)">
  <rect width="{W}" height="{h}" fill="#{c['sc']}"/>
  <path class="spin" d="{shape('flower', 64, 64, 36)}" fill="#{c['tc']}"/>
  {icon('pin', 50, 50, 28, c['on_tc'])}
  <text x="{pad_x}" y="{top}" font-size="17" font-weight="500" fill="#{c['primary']}">Travel</text>
  <text x="{pad_x}" y="{top + 38}" font-size="20" fill="#{c['on_surface']}">{"".join(f'<tspan x="{pad_x}" dy="{0 if j == 0 else 30}">{escape(l)}</tspan>' for j, l in enumerate(lines))}</text>
  <g style="font-family:inherit">{''.join(chips)}</g>
</g>
</svg>
"""


def icon_path(slug):
    ICONS.mkdir(exist_ok=True)
    cached = ICONS / f"{slug}.svg"
    if not cached.exists():
        for version in ICON_SOURCES:
            url = f"https://cdn.jsdelivr.net/npm/simple-icons@{version}/icons/{slug}.svg"
            try:
                cached.write_bytes(urllib.request.urlopen(url, timeout=15).read())
                break
            except OSError:
                continue
        else:
            raise SystemExit(f"Icône introuvable : {slug}")
    m = re.search(r'<path d="([^"]+)"', cached.read_text())
    if not m or not re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZzEe0-9.,\-\s]+", m.group(1)):
        raise SystemExit(f"Icône invalide : {slug}")
    return m.group(1)


def luminance(hex_):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def legible(hex_, bg, target=3.0):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    step = -0.02 if luminance(bg) > 0.5 else 0.02
    while contrast(hex_, bg) < target:
        l = min(1, max(0, l + step))
        if l in (0, 1):
            break
        hex_ = "".join(f"{round(v * 255):02X}" for v in colorsys.hls_to_rgb(h, l, s))
    return hex_


def stack(c):
    cols, gap, pad = 2, GAP, 22
    cw = (W - gap) / cols
    chip_h, chip_gap, top = 40, 10, 66
    cards, heights = [], []
    for name, items in STACK.items():
        chips, x, y, n = [], pad, top, 0
        for label, slug, color in items:
            cw_chip = 10 + 24 + 10 + text_width(label, 16) + 18
            if x + cw_chip > cw - pad:
                x, y = pad, y + chip_h + chip_gap
            fill = legible(color, c["sc"])
            chips.append(f"""<g class="fade" style="animation-delay:{n * 40}ms">
    <rect x="{x + .5:.1f}" y="{y + .5}" width="{cw_chip - 1:.0f}" height="{chip_h - 1}" rx="8" fill="#{c['sc']}" stroke="#{c['outline_v']}"/>
    <path transform="translate({x + 10} {y + 8})" d="{icon_path(slug)}" fill="#{fill}"/>
    <text x="{x + 44}" y="{y + 26}" font-size="16" font-weight="500" fill="#{c['on_sv']}">{escape(label)}</text>
  </g>""")
            x += cw_chip + chip_gap
            n += 1
        cards.append((name, len(items), chips))
        heights.append(y + chip_h + pad)

    rows = math.ceil(len(cards) / cols)
    row_h = [max(heights[r * cols:(r + 1) * cols]) for r in range(rows)]
    out, y0 = [], 0
    for i, (name, count, chips) in enumerate(cards):
        r = i // cols
        x0, y0 = (i % cols) * (cw + gap), sum(row_h[:r]) + r * gap
        bw = 22 + 8 * len(str(count))
        bx = pad + title_width(name, 19) + 8
        out.append(f"""<g transform="translate({x0} {y0})">
  <rect width="{cw}" height="{row_h[r]}" rx="24" fill="#{c['sc']}"/>
  <text x="{pad}" y="42" font-size="19" font-weight="500" fill="#{c['primary']}">{escape(name)}</text>
  <rect x="{bx:.0f}" y="26" width="{bw}" height="22" rx="11" fill="#{c['secc']}"/>
  <text x="{bx + bw / 2:.0f}" y="41.5" font-size="13" font-weight="600" text-anchor="middle" fill="#{c['on_secc']}">{count}</text>
  {''.join(chips)}
</g>""")
    h = sum(row_h) + (rows - 1) * gap
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img">
<title>Tech stack</title>
{base_style(c)}
{''.join(out)}
</svg>
"""


MI = dict(
    pin="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
    prev="M6 6h2v12H6zm3.5 6 8.5 6V6z",
    next="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z",
    pause="M6 19h4V5H6v14zm8-14v14h4V5h-4z",
    note="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z",
    outward="M6 6v2h8.59L5 17.59 6.41 19 16 9.41V18h2V6z",
    tv="M21 3H3c-1.11 0-2 .89-2 2v12c0 1.1.89 2 2 2h5v2h8v-2h5c1.1 0 1.99-.9 1.99-2L23 5c0-1.11-.9-2-2-2zm0 14H3V5h18v12z",
    gamepad="M21.58 16.09l-1.09-7.66A3.996 3.996 0 0 0 16.53 5H7.47C5.48 5 3.79 6.46 3.51 8.43l-1.09 7.66C2.2 17.63 3.39 19 4.94 19c.68 0 1.32-.27 1.8-.75L9 16h6l2.25 2.25c.48.48 1.13.75 1.8.75 1.56 0 2.75-1.37 2.53-2.91zM11 11H9v2H8v-2H6v-1h2V8h1v2h2v1zm4-1c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm2 3c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z",
    book="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z",
    movie="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z",
)


def icon(name, x, y, size, fill):
    return f'<path transform="translate({x} {y}) scale({size / 24:.3f})" d="{MI[name]}" fill="#{fill}"/>'


def song_info():
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([\w-]{11})", SONG["url"])
    if not m:
        raise SystemExit(f"Lien YouTube non reconnu : {SONG['url']}")
    vid = m.group(1)
    url = f"https://www.youtube.com/watch?v={vid}"
    CACHE.mkdir(exist_ok=True)
    meta_file, cover_file = CACHE / f"song-{vid}.json", CACHE / f"cover-{vid}.jpg"
    if not meta_file.exists():
        meta = json.load(urllib.request.urlopen(
            f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json", timeout=15))
        # maxresdefault est en 16:9 ; hqdefault (4:3) a des bandes noires en haut et en bas
        for name, letterbox in (("maxresdefault", False), ("hqdefault", True)):
            try:
                cover_file.write_bytes(urllib.request.urlopen(
                    f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=15).read())
                meta["letterbox"] = letterbox
                break
            except OSError:
                continue
        meta_file.write_text(json.dumps(meta))
    meta = json.loads(meta_file.read_text())
    return dict(
        url=url,
        title=SONG.get("title") or meta["title"],
        artist=SONG.get("artist") or meta["author_name"].removesuffix(" - Topic"),
        album=SONG.get("album", ""),
        cover=base64.b64encode(cover_file.read_bytes()).decode(),
        letterbox=meta["letterbox"],
    )


def song(c, info):
    w, h = W, 232
    dx = W - 900
    img = f"data:image/jpeg;base64,{info['cover']}"
    # Pochette : recadrage carré au centre, en sautant les bandes noires du format 4:3
    if info["letterbox"]:
        aw, ah = 184 * 16 / 9, 184 / .75
        art = f'x="{24 - (aw - 184) / 2:.1f}" y="{24 - (ah - 184) / 2:.1f}" width="{aw:.1f}" height="{ah:.1f}" preserveAspectRatio="none"'
    else:
        art = 'x="24" y="24" width="184" height="184" preserveAspectRatio="xMidYMid slice"'
    subtitle = f"{info['artist']}  ·  {info['album']}" if info["album"] else info["artist"]
    x0, y0, prog_w, played = 232, 186, 444 + dx, .55
    amp, wl = 3.5, 24
    wave = " L".join(
        f"{x:.1f},{amp * math.sin(2 * math.pi * x / wl):.2f}"
        for x in [i / 2 - wl for i in range(int((prog_w * played + 2 * wl) * 2))]
    )
    px = prog_w * played
    on_p = c['pc'] if c is SCHEMES['dark'] else 'FFFFFF'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>Favorite song: {escape(info['title'])} by {escape(info['artist'])}</title>
{base_style(c)}
<style>
  .wave {{ animation: wave 2.8s linear infinite; }}
  @keyframes wave {{ from {{ transform: translateX(-{wl}px); }} to {{ transform: none; }} }}
</style>
<defs>
  <clipPath id="card"><rect width="{w}" height="{h}" rx="28"/></clipPath>
  <clipPath id="art"><rect x="24" y="24" width="184" height="184" rx="20"/></clipPath>
  <clipPath id="played"><rect x="0" y="-10" width="{px:.0f}" height="20"/></clipPath>
  <filter id="blur" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="36"/></filter>
</defs>
<g clip-path="url(#card)">
  <image href="{img}" x="-50" y="{-(w + 100 - h) / 2:.0f}" width="{w + 100}" height="{w + 100}" filter="url(#blur)" preserveAspectRatio="xMidYMid slice"/>
  <rect width="{w}" height="{h}" fill="#{c['sc']}" opacity=".8"/>
</g>
<g clip-path="url(#art)"><image href="{img}" {art}/></g>
<g class="fade">
  <rect x="{x0}" y="24" width="{title_width('Favorite song', 15) + 52:.0f}" height="34" rx="17" fill="#{c['primary']}"/>
  {icon('note', x0 + 12, 32, 18, on_p)}
  <text x="{x0 + 36}" y="46" font-size="15" font-weight="600" fill="#{on_p}">Favorite song</text>
  <text x="{x0}" y="102" font-size="36" font-weight="500" fill="#{c['on_surface']}">{escape(info['title'])}</text>
  <text x="{x0}" y="136" font-size="19" fill="#{c['on_sv']}">{escape(subtitle)}</text>
  <g transform="translate({x0} {y0})">
    <g clip-path="url(#played)"><path class="wave" d="M{wave}" fill="none" stroke="#{c['primary']}" stroke-width="4" stroke-linecap="round"/></g>
    <rect x="{px + 10:.0f}" y="-2" width="{prog_w - px - 10:.0f}" height="4" rx="2" fill="#{c['outline_v']}"/>
    <rect x="{px - 1:.0f}" y="-11" width="4" height="22" rx="2" fill="#{c['primary']}"/>
  </g>
  {icon('prev', 712 + dx, 100, 32, c['on_surface'])}
  <rect x="{764 + dx}" y="80" width="72" height="72" rx="24" fill="#{c['primary']}"/>
  {icon('pause', 784 + dx, 100, 32, on_p)}
  {icon('next', 852 + dx, 100, 32, c['on_surface'])}
  <rect x="{764.5 + dx}" y="24.5" width="111" height="31" rx="8" fill="none" stroke="#{c['outline']}"/>
  <path transform="translate({776 + dx} 33) scale(.6)" d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.6 15.6V8.4l6.3 3.6-6.3 3.6z" fill="#FF0033"/>
  <text x="{800 + dx}" y="45" font-size="14" font-weight="500" fill="#{c['on_sv']}">YouTube</text>
</g>
</svg>
"""


PHASES = {
    "day": dict(sky1="7FB2F0", sky2="DCE9FF", orb="FFD86B", far="8FA9C9", mid="6E9A62",
                near="557F4B", detail="3F6338", accent="F2C14E", agave="5E9C93", stone="E9D9BF"),
    "golden": dict(sky1="F08C6A", sky2="FFD9A8", orb="FF9F5A", far="B07F8E", mid="8C7A4E",
                   near="6C5E3A", detail="4E4329", accent="FFB547", agave="6F8F78", stone="E8B98C"),
    "night": dict(sky1="141633", sky2="3B3266", orb="F1E6C3", far="3A3D66", mid="2C3A3A",
                  near="1F2B29", detail="152020", accent="FFD27A", agave="2F4F4C", stone="4B4766"),
}


def phase_for(hour):
    if 7 <= hour < 18:
        return "day"
    if 6 <= hour < 7 or 18 <= hour < 20:
        return "golden"
    return "night"


def sky(p, w, h, phase):
    orb_y = {"day": 52, "golden": 128, "night": 50}[phase]
    stars = ""
    if phase == "night":
        pts = [(40, 30), (88, 62), (150, 24), (205, 54), (262, 18), (300, 70), (390, 34), (420, 80), (120, 96), (236, 92)]
        stars = "".join(f'<circle cx="{x}" cy="{y}" r="{1.2 + (i % 3) * .5}" fill="#FFFFFF" opacity=".8"/>' for i, (x, y) in enumerate(pts))
    moon_cut = f'<circle cx="{346 + 9}" cy="{orb_y - 6}" r="22" fill="url(#sky)"/>' if phase == "night" else ""
    return f"""<defs><linearGradient id="sky" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{h}">
  <stop offset="0" stop-color="#{p['sky1']}"/><stop offset="1" stop-color="#{p['sky2']}"/></linearGradient></defs>
<rect width="{w}" height="{h}" fill="url(#sky)"/>{stars}
<circle cx="346" cy="{orb_y}" r="{30 if phase == 'golden' else 24}" fill="#{p['orb']}"/>{moon_cut}"""


def stone_pine(x, y, s, fill):
    return (f'<rect x="{x - 2 * s:.1f}" y="{y - 30 * s:.1f}" width="{4 * s:.1f}" height="{30 * s:.1f}" rx="{2 * s:.1f}" fill="#{fill}"/>'
            f'<ellipse cx="{x:.1f}" cy="{y - 34 * s:.1f}" rx="{26 * s:.1f}" ry="{9 * s:.1f}" fill="#{fill}"/>'
            f'<ellipse cx="{x + 10 * s:.1f}" cy="{y - 40 * s:.1f}" rx="{14 * s:.1f}" ry="{7 * s:.1f}" fill="#{fill}"/>')


def cypress(x, y, s, fill):
    return f'<path d="M{x},{y} C{x - 7 * s},{y - 20 * s} {x - 4 * s},{y - 44 * s} {x},{y - 56 * s} C{x + 4 * s},{y - 44 * s} {x + 7 * s},{y - 20 * s} {x},{y} Z" fill="#{fill}"/>'


def scene_montpellier(p, w, h):
    rows = "".join(
        f'<path d="M{-40 + i * 46},{h} L{150 + i * 14},{150}" stroke="#{p["detail"]}" stroke-width="2" opacity=".55"/>'
        for i in range(12)
    )
    return f"""<path d="M90,150 C150,140 205,116 238,86 L252,70 L259,76 L264,150 Z" fill="#{p['far']}"/>
<path d="M0,124 C60,112 100,128 150,124 C200,120 240,104 300,112 C360,120 400,108 {w},116 L{w},{h} L0,{h} Z" fill="#{p['far']}" opacity=".55"/>
<path d="M0,150 C80,136 160,152 240,144 C320,136 380,146 {w},138 L{w},{h} L0,{h} Z" fill="#{p['mid']}"/>
<path d="M0,170 C120,158 260,172 {w},160 L{w},{h} L0,{h} Z" fill="#{p['near']}"/>
<g clip-path="url(#field)">{rows}</g>
{stone_pine(70, 166, 1.25, p['detail'])}{stone_pine(380, 160, 1, p['detail'])}
{cypress(410, 162, 1, p['detail'])}{cypress(424, 164, .8, p['detail'])}
<defs><clipPath id="field"><path d="M0,170 C120,158 260,172 {w},160 L{w},{h} L0,{h} Z"/></clipPath></defs>"""


def agave(x, y, s, fill):
    leaves = []
    for a in (-75, -50, -25, 0, 25, 50, 75):
        r = math.radians(a - 90)
        ln = (22 if abs(a) < 30 else 17) * s
        tx, ty = x + ln * math.cos(r), y + ln * math.sin(r)
        nx, ny = -math.sin(r) * 3 * s, math.cos(r) * 3 * s
        leaves.append(f"M{x - nx:.1f},{y - ny:.1f} L{tx:.1f},{ty:.1f} L{x + nx:.1f},{y + ny:.1f} Z")
    return f'<path d="{" ".join(leaves)}" fill="#{fill}"/>'


def scene_guadalajara(p, w, h):
    cx, base = 230, 156
    def tower(tx):
        return (f'<rect x="{tx - 11}" y="{base - 62}" width="22" height="62" fill="#{p["stone"]}"/>'
                f'<rect x="{tx - 8}" y="{base - 74}" width="16" height="12" fill="#{p["stone"]}"/>'
                f'<path d="M{tx - 9},{base - 74} L{tx},{base - 118} L{tx + 9},{base - 74} Z" fill="#{p["accent"]}"/>'
                f'<rect x="{tx - 1}" y="{base - 128}" width="2" height="12" fill="#{p["stone"]}"/>'
                f'<rect x="{tx - 4}" y="{base - 52}" width="8" height="14" rx="4" fill="#{p["detail"]}" opacity=".5"/>')
    row = lambda y, s, n, off: "".join(agave(off + i * (w / n), y, s, p["agave"]) for i in range(n + 1))
    return f"""<path d="M0,128 L60,104 L110,120 L170,96 L230,118 L300,92 L360,116 L{w},100 L{w},{h} L0,{h} Z" fill="#{p['far']}"/>
<rect x="{cx - 34}" y="{base - 46}" width="68" height="46" fill="#{p['stone']}"/>
<path d="M{cx - 18},{base - 46} A18,18 0 0 1 {cx + 18},{base - 46} Z" fill="#{p['accent']}"/>
<rect x="{cx - 7}" y="{base - 30}" width="14" height="30" rx="7" fill="#{p['detail']}" opacity=".5"/>
{tower(cx - 42)}{tower(cx + 42)}
<path d="M0,152 C120,144 300,160 {w},148 L{w},{h} L0,{h} Z" fill="#{p['mid']}"/>
<path d="M0,170 C140,164 300,174 {w},166 L{w},{h} L0,{h} Z" fill="#{p['near']}"/>
{row(164, .55, 14, 6)}{row(184, .8, 9, 20)}{row(212, 1.1, 6, 0)}"""


SCENES = {"montpellier": scene_montpellier, "guadalajara": scene_guadalajara}


def tricolor(x, y, w, h, colors):
    third = w / 3
    return "".join(f'<rect x="{x + i * third:.1f}" y="{y}" width="{third + .5:.1f}" height="{h}" fill="#{col}"/>'
                   for i, col in enumerate(colors))


def flag_image(code, x, y, w, h):
    # Pays non dessinés à la main : drapeau flag-icons (même source que le portfolio)
    data = cached_download(f"https://cdn.jsdelivr.net/npm/flag-icons@7.5.0/flags/4x3/{code.lower()}.svg")
    if not data:
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#888"/>'
    return (f'<image href="data:image/svg+xml;base64,{base64.b64encode(data).decode()}" x="{x}" y="{y}" '
            f'width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice"/>')


def flag(code, x, y, w=27, h=18):
    drawn = {
        "FR": lambda: tricolor(x, y, w, h, ["002654", "FFFFFF", "ED2939"]),
        "MX": lambda: tricolor(x, y, w, h, ["006847", "FFFFFF", "CE1126"])
              + f'<circle cx="{x + w / 2}" cy="{y + h / 2}" r="{h * .2:.1f}" fill="none" stroke="#5B8C3A" stroke-width="1.2"/>'
              + f'<circle cx="{x + w / 2}" cy="{y + h / 2 - .5}" r="{h * .11:.1f}" fill="#8C5A2B"/>',
    }
    body = drawn[code]() if code in drawn else flag_image(code, x, y, w, h)
    return (f'<clipPath id="flag{code}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4"/></clipPath>'
            f'<g clip-path="url(#flag{code})">{body}</g>'
            f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="3.5" fill="none" stroke="#000" stroke-opacity=".15"/>')


PHOTO_TINT = {"day": ("000000", 0), "golden": ("FF8A3D", .18), "night": ("0B1033", .5)}


def landscape(pl, p, phase, w, sh):
    photo = pl.get("photo")
    raw = None
    if photo:
        raw = cached_download(photo) if photo.startswith("http") else (Path(__file__).parent / photo).read_bytes()
    local = Path(__file__).parent / "assets" / f"{pl['city'].lower()}.jpg"
    if not raw and local.exists():
        # Portfolio injoignable : photo du dépôt si elle existe
        photo, raw = str(local), local.read_bytes()
    if not raw:
        scene = SCENES[pl["scene"]](p, w, sh) if pl.get("scene") in SCENES else ""
        return f'<svg width="{w}" height="{sh}" viewBox="0 0 {w} {sh}">{sky(p, w, sh, phase)}{scene}</svg>'
    suffix = Path(urllib.parse.urlparse(photo).path).suffix.lower()
    mime = {".png": "image/png", ".webp": "image/webp"}.get(suffix, "image/jpeg")
    data = base64.b64encode(raw).decode()
    tint, alpha = PHOTO_TINT[phase]
    return (f'<image href="data:{mime};base64,{data}" width="{w}" height="{sh}" preserveAspectRatio="xMidYMid slice"/>'
            f'<rect width="{w}" height="{sh}" fill="#{tint}" opacity="{alpha}"/>')


def place(c, pl, now=None):
    w, h, sh = (W - GAP) / 2, 336, 210
    now = (now or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo(pl["tz"]))
    phase = phase_for(now.hour)
    p = PHASES[phase]
    off = now.utcoffset().total_seconds() / 3600
    utc = f"UTC{off:+.0f}" if off == int(off) else f"UTC{off:+.1f}"
    chip = f"{pl['city']}, {pl['country']}"
    chip_w = title_width(chip, 15) + 50
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>{escape(pl['label'])}: {escape(chip)}, {now:%H:%M} ({utc})</title>
{base_style(c)}
<defs><clipPath id="card"><rect width="{w}" height="{h}" rx="28"/></clipPath></defs>
<g clip-path="url(#card)">
  <rect width="{w}" height="{h}" fill="#{c['sc']}"/>
  {landscape(pl, p, phase, w, sh)}
</g>
<g class="fade">
  <rect x="16" y="16" width="{chip_w:.0f}" height="36" rx="18" fill="#{c['surface']}" opacity=".92"/>
  {icon('pin', 26, 24, 20, c['primary'])}
  <text x="52" y="39" font-size="15" font-weight="500" fill="#{c['on_surface']}">{escape(chip)}</text>
  <text x="24" y="{sh + 38}" font-size="15" font-weight="500" fill="#{c['primary']}">{escape(pl['label'])}</text>
  <text x="24" y="{sh + 76}" font-size="30" font-weight="500" fill="#{c['on_surface']}">{escape(pl['city'])}</text>
  {flag(pl['flag'], 24, sh + 90)}
  <text x="61" y="{sh + 104}" font-size="17" fill="#{c['on_sv']}">{escape(pl['country'])}</text>
  <text x="{w - 24}" y="{sh + 76}" font-size="40" font-weight="500" text-anchor="end" fill="#{c['on_surface']}"
        style="font-variant-numeric: tabular-nums">{now:%H:%M}</text>
  <text x="{w - 24}" y="{sh + 104}" font-size="15" text-anchor="end" fill="#{c['on_sv']}">{now:%a} · {utc}</text>
</g>
</svg>
"""


def places(c, now=None):
    pw, ph = (W - GAP) / 2, 336
    parts = []
    for i, pl in enumerate(PLACES):
        inner = place(c, pl, now).split(">", 1)[1].rsplit("</svg>", 1)[0]
        # ids préfixés pour éviter les collisions entre les deux cartes
        inner = re.sub(r'id="([^"]+)"', rf'id="{pl["key"]}-\1"', inner)
        inner = re.sub(r"url\(#([^)]+)\)", rf"url(#{pl['key']}-\1)", inner)
        parts.append(f'<svg x="{i * (pw + GAP)}" width="{pw}" height="{ph}" viewBox="0 0 {pw} {ph}">{inner}</svg>')
    title = " · ".join(f"{pl['label']}: {pl['city']}, {pl['country']}" for pl in PLACES)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{ph}" viewBox="0 0 {W} {ph}" role="img">
<title>{escape(title)}</title>
{''.join(parts)}
</svg>
"""


LOGIN = "beedywool"
STATS_QUERY = """query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    pullRequests { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount } }
      }
    }
  }
}"""


def github_token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("GITHUB_TOKEN manquant (ou connecte-toi avec `gh auth login`)")


def fetch_stats():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": STATS_QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {github_token()}", "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in data:
        raise SystemExit(f"API GitHub : {data['errors']}")
    u = data["data"]["user"]
    repos = u["repositories"]
    langs = {}
    for r in repos["nodes"]:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"]))
            langs[name] = (size + e["size"], color or "938F99")
    cc = u["contributionsCollection"]
    days = [d["contributionCount"] for wk in cc["contributionCalendar"]["weeks"] for d in wk["contributionDays"]]
    return dict(
        stars=sum(r["stargazerCount"] for r in repos["nodes"]),
        repos=repos["totalCount"],
        prs=u["pullRequests"]["totalCount"],
        commits=cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        total=cc["contributionCalendar"]["totalContributions"],
        weeks=[[d["contributionCount"] for d in wk["contributionDays"]] for wk in cc["contributionCalendar"]["weeks"]],
        days=days,
        langs=sorted(langs.items(), key=lambda kv: -kv[1][0]),
    )


def streaks(days):
    longest = run = 0
    for n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current, tail = 0, days[:-1] if days and not days[-1] else days  # aujourd'hui pas encore compté
    for n in reversed(tail):
        if not n:
            break
        current += 1
    return current, longest


def fmt(n):
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 10000 else f"{n:,}".replace(",", " ")


def mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    pb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(pa, pb))


def stats(c, st):
    tones = ["pc", "secc", "tc", "pc"]
    kinds = ["cookie", "clover", "sunny", "flower"]
    tiles = [("Stars earned", st["stars"]), ("Commits · 1 year", st["commits"]),
             ("Pull requests", st["prs"]), ("Repositories", st["repos"])]
    tw, th = (W - 3 * GAP) / 4, 116
    out = []
    for i, (label, value) in enumerate(tiles):
        x = i * (tw + GAP)
        out.append(f"""<g class="fade" style="animation-delay:{i * 70}ms">
  <rect x="{x}" y="0" width="{tw}" height="{th}" rx="24" fill="#{c['sc']}"/>
  <path d="{shape(kinds[i], x + 36, 38, 14)}" fill="#{c[tones[i]]}"/>
  <text x="{x + 60}" y="43" font-size="15" font-weight="500" fill="#{c['on_sv']}">{label}</text>
  <text x="{x + 24}" y="94" font-size="36" font-weight="500" fill="#{c['on_surface']}">{fmt(value)}</text>
</g>""")

    y2, cw, ch = th + GAP, (W - GAP) / 2, 220
    cur, longest = streaks(st["days"])
    out.append(f"""<g class="fade" style="animation-delay:280ms" transform="translate(0 {y2})">
  <rect width="{cw}" height="{ch}" rx="24" fill="#{c['sc']}"/>
  <path class="spin" d="{shape('sunny', 112, 118, 66)}" fill="#{c['pc']}"/>
  <text x="112" y="126" font-size="44" font-weight="500" text-anchor="middle" fill="#{c['on_pc']}">{cur}</text>
  <text x="112" y="150" font-size="14" font-weight="500" text-anchor="middle" fill="#{c['on_pc']}">day{'s' if cur != 1 else ''}</text>
  <text x="216" y="58" font-size="17" font-weight="500" fill="#{c['primary']}">Current streak</text>
  <text x="216" y="104" font-size="15" fill="#{c['on_sv']}">Longest streak</text>
  <text x="216" y="134" font-size="26" font-weight="500" fill="#{c['on_surface']}">{longest} day{'s' if longest != 1 else ''}</text>
  <text x="216" y="168" font-size="15" fill="#{c['on_sv']}">Contributions · 1 year</text>
  <text x="216" y="198" font-size="26" font-weight="500" fill="#{c['on_surface']}">{fmt(st['total'])}</text>
</g>""")

    top = st["langs"][:6]
    total = sum(v[0] for _, v in st["langs"]) or 1
    bar_w, bx, seg = cw - 48, 24, []
    shown = sum(v[0] for _, v in top) or 1
    for name, (size, color) in top:
        sw = bar_w * size / shown
        seg.append(f'<rect x="{bx:.1f}" y="66" width="{max(sw - 4, 2):.1f}" height="12" rx="6" fill="{escape(color)}"/>')
        bx += sw
    legend = []
    for i, (name, (size, color)) in enumerate(top):
        lx, ly = 24 + (i % 2) * (cw - 48) / 2, 120 + (i // 2) * 36
        legend.append(f'<circle cx="{lx + 6}" cy="{ly - 5}" r="6" fill="{escape(color)}"/>'
                      f'<text x="{lx + 20}" y="{ly}" font-size="16" fill="#{c["on_surface"]}">{escape(name)}</text>'
                      f'<text x="{lx + (cw - 48) / 2 - 16}" y="{ly}" font-size="15" text-anchor="end" fill="#{c["on_sv"]}">{100 * size / total:.1f}%</text>')
    out.append(f"""<g class="fade" style="animation-delay:350ms" transform="translate({cw + GAP} {y2})">
  <rect width="{cw}" height="{ch}" rx="24" fill="#{c['sc']}"/>
  <text x="24" y="44" font-size="17" font-weight="500" fill="#{c['primary']}">Top languages</text>
  {''.join(seg)}{''.join(legend)}
</g>""")

    y3 = y2 + ch + GAP
    weeks = st["weeks"][-53:]
    cell_gap = 4
    cell = (W - 48 - (len(weeks) - 1) * cell_gap) / len(weeks)
    nonzero = sorted(n for wk in weeks for n in wk if n)
    q = [nonzero[int(len(nonzero) * f)] if nonzero else 1 for f in (.25, .5, .75)]
    levels = [c["sch"]] + [mix(c["pc"], c["primary"], t) for t in (0, .35, .7, 1)]
    cells = []
    for wi, wk in enumerate(weeks):
        for di, n in enumerate(wk):
            lvl = 0 if not n else 1 + sum(n > t for t in q)
            cells.append(f'<rect x="{24 + wi * (cell + cell_gap):.1f}" y="{64 + di * (cell + cell_gap):.1f}" '
                         f'width="{cell:.1f}" height="{cell:.1f}" rx="4" fill="#{levels[lvl]}"/>')
    hh = 64 + 7 * cell + 6 * cell_gap + 24
    out.append(f"""<g class="fade" style="animation-delay:420ms" transform="translate(0 {y3})">
  <rect width="{W}" height="{hh:.0f}" rx="24" fill="#{c['sc']}"/>
  <text x="24" y="44" font-size="17" font-weight="500" fill="#{c['primary']}">Contributions</text>
  <text x="{W - 24}" y="44" font-size="15" text-anchor="end" fill="#{c['on_sv']}">{fmt(st['total'])} in the last year</text>
  {''.join(cells)}
</g>""")
    h = y3 + hh
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h:.0f}" viewBox="0 0 {W} {h:.0f}" role="img">
<title>GitHub stats: {st['stars']} stars, {st['commits']} commits, {st['prs']} pull requests, current streak {cur} days</title>
{base_style(c)}
{''.join(out)}
</svg>
"""


def pad(svg):
    """Ajoute l'espace commun sous chaque image : le README les empile sans marge."""
    def grow(m):
        h = float(m.group(2)) + GAP
        return f'{m.group(1)}height="{h:g}" viewBox="0 0 {m.group(3)} {h:g}"'
    return re.sub(r'(<svg xmlns[^>]*?)height="([\d.]+)" viewBox="0 0 ([\d.]+) [\d.]+"', grow, svg, count=1)


def build_live():
    CARDS.mkdir(exist_ok=True)
    st = fetch_stats()
    for mode, c in SCHEMES.items():
        (CARDS / f"places-{mode}.svg").write_text(pad(places(c)))
        (CARDS / f"stats-{mode}.svg").write_text(pad(stats(c, st)))
    print(f"Cartes live générées dans {CARDS}")


# ─── Données du portfolio ────────────────────────────────────────────────────
# Le contenu vient du portfolio : son build publie profile.json à partir de
# portfolio-config.json (modifiable avec Pages CMS). Les valeurs en haut du fichier
# ne servent que de secours si le site est injoignable et sans copie en cache.
PORTFOLIO = os.environ.get("PORTFOLIO_URL", "https://portfolio.mignon.casa")
PRIDE = True
TRAVEL = dict(intro="", been=[])
FAVORITES = []


def cached_download(url):
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / f"dl-{hashlib.sha1(url.encode()).hexdigest()[:16]}"
    if not cached.exists():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "beedywool-readme"})
            res = urllib.request.urlopen(req, timeout=20)
            # Un site en mode SPA renvoie sa page HTML (200) pour les fichiers absents
            if res.headers.get_content_type() == "text/html":
                return None
            cached.write_bytes(res.read())
        except OSError:
            return None
    return cached.read_bytes()


def load_portfolio():
    global NAME, TAGLINE, GREETING, PILLS, PRIDE, BIO, ABOUT, SONG, PLACES, STACK, PORTFOLIO, TRAVEL, FAVORITES
    cached = CACHE / "profile.json"
    try:
        req = urllib.request.Request(f"{PORTFOLIO}/profile.json", headers={"User-Agent": "beedywool-readme"})
        data = json.load(urllib.request.urlopen(req, timeout=20))
        CACHE.mkdir(exist_ok=True)
        cached.write_text(json.dumps(data))
    except (OSError, ValueError) as e:
        if not cached.exists():
            print(f"Portfolio injoignable ({e}) : valeurs par défaut de build.py")
            return
        print(f"Portfolio injoignable ({e}) : dernière copie en cache")
        data = json.loads(cached.read_text())

    site = data.get("site") or PORTFOLIO
    if site != PORTFOLIO:
        # PORTFOLIO_URL=… (test d'un autre build) : images prises sur ce site, liens vers le site public
        data = json.loads(json.dumps(data).replace(site, PORTFOLIO))
    PORTFOLIO = site
    NAME, TAGLINE = data["name"], data["title"]
    GREETING, PILLS, PRIDE = data["greeting"], data["tags"], bool(data.get("prideFlag"))
    BIO = data["bio"]
    ABOUT = [(f["label"], f["value"]) for f in data["facts"]]
    if data.get("song"):
        SONG = {k: data["song"].get(k, "") for k in ("url", "title", "artist", "album")}
    PLACES = [
        dict(key=f"place{i}", label=p["label"], city=p["city"], country=p["country"], tz=p["timezone"],
             scene=p["city"].lower() if p["city"].lower() in SCENES else None,
             photo=p.get("photo"), flag=p["code"].upper())
        for i, p in enumerate(data["places"])
    ]
    STACK = {g["category"]: [(s["name"], s["icon"], s["color"].lstrip("#")) for s in g["items"]]
             for g in data["stack"]}
    FAVORITES = data.get("favorites") or []
    travel = data.get("travel") or {}
    TRAVEL = dict(intro=travel.get("intro", ""),
                  been=[(p["city"], p["code"]) for p in travel.get("places", [])]
                  + [(p["name"], p["code"]) for p in travel.get("countries", [])])


def write_readme(info):
    # Le README est entièrement généré : même structure que la section About du portfolio
    cards = "https://raw.githubusercontent.com/beedywool/beedywool/refs/heads/cards"

    def pic(dark, light, alt):
        alt = escape(alt, quote=False).replace('"', "&quot;")
        return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}">'
                f'<img align="top" width="100%" alt="{alt}" src="{light}"></picture>')

    def asset(name, alt):
        return pic(f"assets/{name}-dark.svg", f"assets/{name}-light.svg", alt)

    def live(name, alt):
        return pic(f"{cards}/{name}-dark.svg", f"{cards}/{name}-light.svg", alt)

    song_alt = f"Favorite song: {info['title']} by {info['artist']}"
    places_alt = " · ".join(f"{pl['label']}: {pl['city']}, {pl['country']}" for pl in PLACES)
    lines = [
        f'<a href="{PORTFOLIO}">{asset("header", f"{NAME} | {TAGLINE}")}</a>',
        f'<a href="{PORTFOLIO}">{asset("portfolio", "Visit my portfolio: " + PORTFOLIO.split("://", 1)[-1])}</a>',
        asset("section-about", "01 | About me"),
        asset("sub-intro", "Introduction"),
        asset("bio", f"Hi, I'm {NAME}. {BIO}"),
        live("places", places_alt),
        asset("sub-now", "Right now"),
        asset("facts", " · ".join(f"{l}: {v}" for l, v in ABOUT)),
        asset("sub-favorites", "Favorites"),
        f'<a href="{info["url"]}">{asset("song", song_alt)}</a>',
    ]
    if FAVORITES:
        fav_alt = " · ".join(f"{g['label']}: " + ", ".join(i["name"] for i in g["items"]) for g in FAVORITES)
        lines.append(f'<a href="{PORTFOLIO}/#h-favorites">{asset("favorites", fav_alt)}</a>')
    if TRAVEL["intro"]:
        been = ", ".join(n for n, _ in TRAVEL["been"])
        lines += [asset("sub-hobby", "Hobby"), asset("hobby", f"Travel: {TRAVEL['intro']} Been to: {been}")]
    lines += [
        asset("section-stats", "02 | GitHub stats"),
        live("stats", "GitHub stats: stars, commits, pull requests, repositories, streak, top languages and contributions"),
        asset("section-stack", "03 | Tech stack"),
        asset("stack", ", ".join(n for items in STACK.values() for n, _, _ in items)),
    ]
    (Path(__file__).parent / "README.md").write_text("<p>\n" + "\n".join(lines) + "\n</p>\n")


def main():
    load_portfolio()
    if sys.argv[1:] == ["live"]:
        return build_live()
    build_live()
    OUT.mkdir(exist_ok=True)
    kinds = ["cookie", "clover", "sunny", "flower"]
    info = song_info()
    write_readme(info)
    subs = {"intro": ("Introduction", "cookie"), "now": ("Right now", "clover"),
            "favorites": ("Favorites", "sunny"), "hobby": ("Hobby", "flower")}
    for mode, c in SCHEMES.items():
        (OUT / f"header-{mode}.svg").write_text(pad(header(c)))
        (OUT / f"portfolio-{mode}.svg").write_text(pad(portfolio_link(c)))
        (OUT / f"bio-{mode}.svg").write_text(pad(bio(c)))
        (OUT / f"facts-{mode}.svg").write_text(pad(facts(c)))
        if TRAVEL["intro"]:
            (OUT / f"hobby-{mode}.svg").write_text(pad(hobby(c)))
        if FAVORITES:
            (OUT / f"favorites-{mode}.svg").write_text(pad(favorites(c)))
        for key, (title, kind) in subs.items():
            (OUT / f"sub-{key}-{mode}.svg").write_text(pad(subsection(c, title, kind)))
        (OUT / f"stack-{mode}.svg").write_text(pad(stack(c)))
        (OUT / f"song-{mode}.svg").write_text(pad(song(c, info)))
        for i, (key, title) in enumerate(SECTIONS.items()):
            (OUT / f"section-{key}-{mode}.svg").write_text(pad(section(c, key, title, kinds[i % 4], i + 1)))
    print(f"SVG générés dans {OUT}")


if __name__ == "__main__":
    main()
