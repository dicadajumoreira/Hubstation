"""Brand Kit Sindicompany — camada compartilhada de design.

Tokens complementares (gradientes, neutros, pares aprovados) + geradores
parametricos (logo recolorivel por mascara). Pensado pra ser consumido pelo
engine de carrossel agora e, no futuro, por revista e comunicados — por isso
nao depende de nada especifico do carrossel.

As 6 cores principais (Navy/Cyan/Beige/Lavender/Purple/White) ja vivem na
PALETTE do carrossel_generate, mapeadas nas chaves onix/mint/sand/lavender/
purple/white. Aqui ficam os tokens que ainda nao estavam estruturados.
"""

import base64
import os

# ---------------------------------------------------------------------------
# Tokens (Brand Hub 2026-05)
# ---------------------------------------------------------------------------

NEUTRALS = {
    "paper": "#FAF7F2",        # fundo padrao
    "paper_warm": "#F2EDE5",   # fundo secundario
    "line": "#E5DDD2",         # divisores
    "muted": "#8A8E96",        # texto auxiliar
}

# (from, to) — aplicados a 135 graus por padrao
GRADIENTS = {
    "aurora": ("#BFC0FF", "#88C8D0"),    # premium / IA / inovacao
    "sunset": ("#E0B098", "#BFC0FF"),    # editorial / humano
    "deep_sea": ("#182028", "#8890D0"),  # dark mode / premium
    "sand": ("#F0C8B8", "#E0B098"),      # soft / maternal
}

# 8 pares aprovados (bg, fg) — combinacoes oficiais do brandbook
APPROVED_PAIRS = [
    ("#182028", "#E0B098"),  # Navy + Beige   — Premium
    ("#182028", "#88C8D0"),  # Navy + Cyan    — Tech
    ("#FAF7F2", "#182028"),  # Paper + Navy   — Default
    ("#E0B098", "#182028"),  # Beige + Navy   — Humano
    ("#88C8D0", "#182028"),  # Cyan + Navy    — Energia
    ("#BFC0FF", "#182028"),  # Lavender + Navy — IA
]


def gradient_css(name: str, angle: int = 135) -> str:
    """CSS linear-gradient de um gradiente oficial. '' se nao existir."""
    g = GRADIENTS.get(name)
    if not g:
        return ""
    a, b = g
    return f"linear-gradient({angle}deg, {a} 0%, {b} 100%)"


# ---------------------------------------------------------------------------
# Patterns de canto (watermark discreto) — petalas em quarto de circulo
# ---------------------------------------------------------------------------
# PNGs pre-coloridos por cor da paleta em assets/patterns/sindicompany/.
# Usados como decoracao de canto em baixa opacidade (regra do brandbook:
# "Cantos solo para watermarks discretos (TR ou BL)").

CORNER_PATTERNS = {
    "navy": "canto-navy.png",
    "cyan": "canto-cyan.png",
    "beige": "canto-beige.png",
    "lavender": "canto-lavender.png",
    "purple": "canto-purple.png",
}

_PATTERN_CACHE: dict[str, str] = {}


def _pattern_data_url(filename: str) -> str:
    if filename in _PATTERN_CACHE:
        return _PATTERN_CACHE[filename]
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "assets", "patterns", "sindicompany", filename)
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        url = f"data:image/png;base64,{b64}"
    except Exception as e:  # noqa: BLE001
        print(f"[brand_kit] pattern {filename} nao carregou: {e}", flush=True)
        url = ""
    _PATTERN_CACHE[filename] = url
    return url


def _alpha_hex(op: float) -> str:
    return f"{max(0, min(255, int(op * 255))):02x}"


def sc_glow_overlay_html(
    c1: str,
    c2: str,
    *,
    op1: float = 0.30,
    op2: float = 0.26,
) -> str:
    """Camada de glow radial (profundidade sutil) sobre o fundo do slide.
    Dois focos de luz nas cores da marca, em cantos opostos. z-index 0."""
    a1 = _alpha_hex(op1)
    a2 = _alpha_hex(op2)
    return (
        '<div style="position:absolute;inset:0;z-index:0;pointer-events:none;'
        "background:"
        f"radial-gradient(circle at 82% 16%, {c1}{a1} 0%, transparent 46%),"
        f'radial-gradient(circle at 10% 90%, {c2}{a2} 0%, transparent 48%)"></div>'
    )


def sc_corner_overlay_html(
    color_name: str,
    *,
    opacity: float = 0.10,
    position: str = "right bottom",
    size: str = "40%",
    z: int = 0,
) -> str:
    """Div absoluto com o pattern de canto pra decorar um slide. '' se a
    cor nao existir ou o arquivo faltar."""
    fn = CORNER_PATTERNS.get(color_name)
    if not fn:
        return ""
    url = _pattern_data_url(fn)
    if not url:
        return ""
    return (
        f'<div style="position:absolute;inset:0;z-index:{z};'
        f"pointer-events:none;opacity:{opacity};"
        f"background-image:url({url});background-repeat:no-repeat;"
        f'background-position:{position};background-size:{size}"></div>'
    )


# ---------------------------------------------------------------------------
# Logo recolorivel por mascara (pixel-perfect com o master)
# ---------------------------------------------------------------------------
# O simbolo (casas concentricas + ponto) e renderizado via CSS mask-image
# sobre o canal alpha do artwork original. As casas e o ponto sao coloridos
# independentemente via background-color -> recolorivel em runtime, fiel ao
# master. Arquivos em assets/logos/sindicompany/.

# proporcao do master: 454 x 512  ->  altura = largura * 1.128
SYMBOL_RATIO = 512 / 454

_MASK_CACHE: dict[str, str] = {}


def _mask_data_url(name: str) -> str:
    """data: URL base64 de uma mascara do simbolo. '' se nao encontrar.
    Cache por processo."""
    if name in _MASK_CACHE:
        return _MASK_CACHE[name]
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "assets", "logos", "sindicompany", name)
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        url = f"data:image/png;base64,{b64}"
    except Exception as e:  # noqa: BLE001
        print(f"[brand_kit] mascara {name} nao carregou: {e}", flush=True)
        url = ""
    _MASK_CACHE[name] = url
    return url


def sc_symbol_html(
    size_px: float,
    house_color: str,
    dot_color: str | None = None,
    *,
    dot: bool = True,
) -> str:
    """Simbolo Sindicompany recolorivel. `house_color` colore as casas;
    `dot_color` o ponto (default = house_color). '' se a mascara faltar."""
    mh = _mask_data_url("mask-houses.png")
    if not mh:
        return ""
    md = _mask_data_url("mask-dot.png")
    h = size_px * SYMBOL_RATIO
    dot_color = dot_color or house_color
    base = (
        "position:absolute;inset:0;-webkit-mask-size:contain;mask-size:contain;"
        "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;"
        "-webkit-mask-position:center;mask-position:center"
    )
    houses = (
        f'<div style="{base};background:{house_color};'
        f'-webkit-mask-image:url({mh});mask-image:url({mh})"></div>'
    )
    dot_div = ""
    if dot and md:
        dot_div = (
            f'<div style="{base};background:{dot_color};'
            f'-webkit-mask-image:url({md});mask-image:url({md})"></div>'
        )
    return (
        f'<div style="position:relative;display:inline-block;flex-shrink:0;'
        f'width:{size_px}px;height:{h:.1f}px">{houses}{dot_div}</div>'
    )


def sc_logo_horizontal_html(
    width: float,
    house_color: str,
    dot_color: str,
    wordmark_color: str,
    *,
    klass: str = "",
) -> str:
    """Lockup horizontal: simbolo recolorivel + wordmark 'sindicompany' em
    Provicali. Proporcoes rastreadas do master (svg-kit.jsx): simbolo=18.3%
    da largura, fonte=15.8%, gap=0.5%. Provicali precisa estar embutida no
    <head> (sindicompany-fonts-inline.css). '' se a mascara faltar."""
    # Proporcoes medidas do master (sindicompany-horizontal-color.png):
    # simbolo = 18.3% da largura, gap = 0.3%, cap-height do wordmark = 10.6%
    # -> font-size ~= 15.1% da largura (cap/font ~= 0.7). Largura do container
    # fica natural (o wordmark define) pra nunca cortar o "y"/®.
    symbol_size = width * 0.183
    font_size = width * 0.151
    gap = width * 0.003
    sym = sc_symbol_html(symbol_size, house_color, dot_color)
    if not sym:
        return ""
    cls = f' class="{klass}"' if klass else ""
    return (
        f'<div{cls} style="display:inline-flex;align-items:center;'
        f'gap:{gap:.1f}px;">'
        f"{sym}"
        f"<span style=\"font-family:'Provicali','Epilogue',system-ui,sans-serif;"
        f"font-style:normal;font-weight:400;font-size:{font_size:.1f}px;"
        f"color:{wordmark_color};letter-spacing:-0.02em;line-height:0.85;"
        f"display:inline-flex;align-items:flex-start;"
        f'margin-top:{symbol_size * 0.04:.1f}px;white-space:nowrap;">'
        f"sindicompany"
        f"<sup style=\"font-size:0.18em;font-family:'Epilogue',sans-serif;"
        f'font-weight:500;margin-top:0.4em;margin-left:0.1em;">&#174;</sup>'
        f"</span></div>"
    )


def pick_logo_colors(bg_is_dark: bool, p: dict) -> tuple[str, str, str]:
    """(casas, ponto, wordmark) do lockup conforme o fundo do slide.
    Fundo escuro -> tudo branco + ponto beige; fundo claro/colorido ->
    tudo navy + ponto beige. Mono por segurança de leitura sobre os
    fundos variados dos slides de conteudo."""
    beige = p.get("sand", "#E0B098")
    if bg_is_dark:
        white = p.get("white", "#FFFFFF")
        return white, beige, white
    navy = p.get("onix", "#182028")
    return navy, beige, navy


# ---------------------------------------------------------------------------
# Paginacao do slide — pool de estilos (varia por carrossel)
# ---------------------------------------------------------------------------
# Substitui o numero gigante de fundo. O estilo e escolhido UMA vez por
# carrossel (deterministico pelo id) e fica consistente em todos os slides;
# entre carrosseis varia, dando ritmo ao feed. Tamanhos em px do slide 4K
# (3072x3839). `color` = cor do indicador ativo (navy no claro, branco no
# escuro); o inativo usa a mesma cor com alpha.

PAGINATION_STYLES = ["dots", "ticks", "bar", "index"]
# pool com peso: dots aparece mais (preferido), mas todos entram
PAGINATION_POOL = ["dots", "dots", "ticks", "bar", "index"]


def pick_pagination_style(seed: str) -> str:
    """Escolhe um estilo do pool de forma deterministica pelo seed (id do
    carrossel). Mesmo carrossel -> mesmo estilo; carrosseis diferentes ->
    estilos diferentes."""
    if not seed:
        return PAGINATION_POOL[0]
    h = sum(ord(c) for c in str(seed))
    return PAGINATION_POOL[h % len(PAGINATION_POOL)]


def sc_pagination_html(
    style: str,
    idx: int,
    total: int,
    accent: str,
    fg: str,
    *,
    font: str = "'Epilogue', sans-serif",
) -> str:
    """HTML absoluto da paginacao. Cores da marca: `accent` no indicador
    ativo, `fg` (texto) esmaecido na trilha. `font` = fonte numerica da
    marca (estilo 'index'). idx 1-based."""
    track = f"{fg}33"  # ~20% alpha do texto da marca
    if style == "bar":
        pct = max(0.0, min(1.0, idx / total)) * 100 if total else 0
        return (
            f'<div style="position:absolute;left:0;right:0;bottom:0;height:16px;'
            f'background:{fg}1f;z-index:3">'
            f'<div style="height:100%;width:{pct:.1f}%;background:{accent}"></div>'
            f"</div>"
        )
    if style == "index":
        return (
            f'<div style="position:absolute;right:180px;bottom:170px;'
            f'text-align:right;z-index:3;font-family:{font}">'
            f'<div style="font-size:180px;font-weight:800;color:{fg};'
            f'line-height:0.8;letter-spacing:-0.04em">{idx:02d}</div>'
            f'<div style="font-size:64px;font-weight:600;color:{accent};'
            f'margin-top:8px">/ {total:02d}</div></div>'
        )
    if style == "ticks":
        bars = "".join(
            f'<span style="width:22px;height:{72 if i == idx - 1 else 38}px;'
            f'border-radius:11px;background:{accent if i == idx - 1 else track}">'
            f"</span>"
            for i in range(total)
        )
        return (
            f'<div style="position:absolute;right:180px;bottom:250px;z-index:3;'
            f'display:flex;gap:20px;align-items:flex-end">{bars}</div>'
        )
    # default: dots
    dots = "".join(
        f'<span style="width:32px;height:32px;border-radius:50%;'
        f'background:{accent if i == idx - 1 else track}"></span>'
        for i in range(total)
    )
    return (
        f'<div style="position:absolute;right:180px;bottom:250px;z-index:3;'
        f'display:flex;gap:28px;align-items:center">{dots}</div>'
    )


def pick_symbol_colors(bg_is_dark: bool, p: dict) -> tuple[str, str]:
    """(casas, ponto) conforme o fundo do slide, seguindo o brandbook:
    fundo escuro -> casas brancas + ponto beige; fundo claro -> casas navy
    + ponto beige (par "humano"). Usa as chaves da paleta da marca."""
    beige = p.get("sand", "#E0B098")
    if bg_is_dark:
        return p.get("white", "#FFFFFF"), beige
    return p.get("onix", "#182028"), beige
