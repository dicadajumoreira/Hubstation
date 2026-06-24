"""Renderiza as 42 capas do Brand Hub Sindicompany em PNG + monta mosaico.

Output:
- revista-engine/tmp_preview/cover-archetypes/<slug>.png  (42 arquivos)
- revista-engine/tmp_preview/cover-archetypes-mosaic.png  (grid 6x7 com label)
"""
from __future__ import annotations

import base64
import io
import os
import sys
import time
from pathlib import Path

# Stubs pros modulos que dependem de env vars de runtime — n s queremos
# importar carrossel_generate sem tocar Supabase/OpenAI.
import types
sys.modules.setdefault("api.supabase_client", types.ModuleType("api.supabase_client"))
sys.modules["api.supabase_client"]._client = None  # type: ignore[attr-defined]
sys.modules.setdefault("api.text_gen", types.ModuleType("api.text_gen"))
sys.modules["api.text_gen"]._client = None  # type: ignore[attr-defined]
sys.modules["api.text_gen"].MODEL = "x"  # type: ignore[attr-defined]
sys.modules["api.text_gen"]._gerar_json = lambda *a, **k: {}  # type: ignore[attr-defined]

# Add revista-engine ao path se o script for chamado de fora.
HERE = Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from api import carrossel_generate as cg  # noqa: E402

OUT_DIR = ENGINE_ROOT / "tmp_preview" / "cover-archetypes"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MOSAIC_PATH = ENGINE_ROOT / "tmp_preview" / "cover-archetypes-mosaic.png"

# Marca pra renderizar como (logos, paleta, handle do @sindicompanybr)
cg._BRAND = "sindicompanybr"
cg._COVER_ARCHETYPE = ""

# Resolucao final pro preview: device_scale_factor=0.4 sobre o
# layout CSS nativo (3072x3839) resulta em 1229x1535 PNG por capa.
PREVIEW_SCALE = 0.4
PREVIEW_W = int(cg.SLIDE_W * PREVIEW_SCALE)
PREVIEW_H = int(cg.SLIDE_H * PREVIEW_SCALE)

# Foto placeholder pros arquetipos COM foto: gradient Cyan->Beige com
# label "FOTO DA ETAPA 3" centralizado. Gerada em PNG, encodada como
# data URL pra ser injetada igual a uma URL HTTP real.
def _placeholder_photo_data_url() -> str:
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1080, 1350  # 4:5 nativo do feed
    img = Image.new("RGB", (W, H), (132, 199, 211))  # Cyan base
    # Gradient diagonal cyan -> beige
    for y in range(H):
        for x in range(W):
            t = (x + y) / (W + H)
            r = int((1 - t) * 132 + t * 218)
            g = int((1 - t) * 199 + t * 176)
            b = int((1 - t) * 211 + t * 152)
            img.putpixel((x, y), (r, g, b))
    draw = ImageDraw.Draw(img)
    label = "FOTO DA ETAPA 3"
    # Tenta font sistema; senao fallback default
    font = None
    for fp in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ):
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 70)
                break
            except OSError:
                pass
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((W - tw) / 2, (H - th) / 2),
        label,
        fill=(24, 32, 40),
        font=font,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# Conteudo representativo por arquetipo. Para os que tem convencao de
# body especial (versus, grid-stats, etc.), passamos o formato correto.
DEFAULT_TITULO = "O síndico que mede, melhora sempre."
DEFAULT_BODY = "Dado real: redução de 92% em inadimplência em 6 meses."

ARCH_DATA: dict[str, dict[str, str]] = {
    # SEM foto — convenções diversas
    "editorial-question": {
        "titulo": "E se o condomínio fosse uma empresa?",
        "body": "Spoiler: já é. Você que ainda não viu.",
    },
    "stat-slap": {"titulo": "92%", "body": "menos inadimplência em 6 meses"},
    "numbered-guide": {"titulo": "5 passos pra reduzir inadimplência", "body": "Sem pressão. Sem advogado."},
    "manifesto": {
        "titulo": "Síndico não é mediador de briga. É gestor de operação.",
        "body": "",
    },
    "pattern-explosion": {"titulo": "Como medir o que importa", "body": "Comece pelo que dá pra cobrar."},
    "pull-quote": {"titulo": "Juliana Moreira", "body": "Sem medir, não se administra um condomínio."},
    "headline-only": {"titulo": "Quem mede, melhora.", "body": ""},
    "glow-hero": {"titulo": "O futuro da gestão condominial", "body": "Dados, transparência, decisões."},
    "versus": {
        "titulo": "Inadimplência alta? O problema raramente é o morador.",
        "body": "ignorar atrasos e esperar | medir, cobrar com método e comunicar",
    },
    "sticky-note": {"titulo": "Lembrete pro próximo síndico", "body": "Mede antes de cobrar. Sempre."},
    "mythbuster": {
        "titulo": "Verdade ou mito?",
        "body": "Condomínio não precisa medir nada — é casa de gente. | Sem dado, decisão vira chute. Com dado, decisão vira gestão.",
    },
    "brackets": {"titulo": "Síndico que mede, melhora sempre.", "body": "Sem exceção."},
    "type-tower": {"titulo": "Mede compara ajusta repete", "body": "É só isso."},
    "split-color": {"titulo": "Onde o caos vira gestão", "body": "Aqui."},
    "grid-stats": {
        "titulo": "Em números",
        "body": "92%: inadimplência ↓; R$240k: economia/ano; 18m: payback; 4.8: NPS moradores",
    },
    "highlight": {"titulo": "O síndico que **mede** sempre melhora.", "body": "Dado real."},
    "stamp": {"titulo": "Inadimplência cai 92% quando o síndico mede.", "body": "Fato"},
    "bullet-list": {
        "titulo": "5 passos pra reduzir inadimplência",
        "body": "Meça o status mensal; Comunique aberto; Cobre com método; Acompanhe o que mexe; Compartilhe o resultado",
    },
    "wallpaper": {"titulo": "A revolução silenciosa", "body": "Da gestão condominial brasileira."},
    "underline": {"titulo": "Quem **mede** sempre melhora.", "body": "Comprovado em 47 condomínios."},
    "timeline": {
        "titulo": "Como reduzimos a inadimplência em 6 meses",
        "body": "Diagnóstico do baseline; Plano de cobrança; Comunicação aberta; Medição mensal; Compartilhamento de resultados",
    },
    "conversation": {
        "titulo": "Quando o síndico mede, o condomínio nota.",
        "body": "Oi síndico, vai aumentar a taxa? | Não, vou reduzir | Sério? Como? | Medi o que importa e cortei o que não.",
    },
    "receipt": {
        "titulo": "Resultado em 6 meses",
        "body": "Inadimplência: -92%; Custos operacionais: -23%; NPS dos moradores: +18; Total economizado: R$ 240.000",
    },
    "corner-tape": {"titulo": "Achados do mês", "body": "Quando o síndico mede, sempre vira história."},
    "ribbon": {"titulo": "Edição especial", "body": "Sindicompany 2026"},
    "polaroid-stack": {"titulo": "Histórias reais", "body": "De síndicos que viraram referência."},
    "maxi-quote": {"titulo": "Quem mede,", "body": "ganha."},
    "calendar": {"titulo": "Próxima medição mensal", "body": "MAIO | 18"},
    # COM foto — uso da foto da etapa 3
    "dark-premium": {"titulo": "Por dentro do síndico que entrega.", "body": "Bastidores."},
    "magazine-cover": {"titulo": "O síndico que mudou tudo", "body": "Como dados viraram a virada do condomínio."},
    "split-portrait": {"titulo": "Juliana Moreira", "body": "A síndica que mede antes de decidir."},
    "hero-portrait": {"titulo": "A nova síndica", "body": "Que abriu os números."},
    "avatar-quote": {"titulo": "Juliana Moreira", "body": "Sem medir, não se administra um condomínio."},
    "photo-circle": {"titulo": "Síndico que mede, melhora.", "body": "Sempre."},
    "photo-banner": {"titulo": "O que aprendi em 47 condomínios", "body": "Em 6 anos de gestão profissional."},
    "floating-card": {"titulo": "Da operação à decisão", "body": "Sem ruído."},
    "photo-blur": {"titulo": "O caos que vira gestão", "body": "Aqui dentro."},
    "cinema": {"titulo": "O síndico em ação", "body": "Bastidores do que o morador não vê."},
    "polaroid": {"titulo": "O síndico do andar 12", "body": "Que mediu tudo, mudou tudo."},
    "portrait-frame": {"titulo": "Síndico do Mês", "body": "Quem mede sempre melhora."},
    "photo-strip": {"titulo": "O condomínio que mudou", "body": "Em 6 meses."},
    "photo-grid": {"titulo": "Aprendi vendo o síndico medir.", "body": "E vou repetir."},
}


def _make_html(name: str, fn, foto_url: str) -> str:
    data = ARCH_DATA.get(name, {"titulo": DEFAULT_TITULO, "body": DEFAULT_BODY})
    titulo = data.get("titulo", DEFAULT_TITULO)
    body = data.get("body", "")
    # Reusa o setup do _slide_html: head_fonts inline + logo data URL
    sindi_css = cg._sindicompany_fonts_css()
    if sindi_css:
        head_fonts = f"<style>{sindi_css}</style>"
    else:
        head_fonts = (
            '<link href="https://fonts.googleapis.com/css2?'
            'family=Epilogue:wght@400;600;800;900&display=swap" '
            'rel="stylesheet">'
        )
    font_display = "'Epilogue', sans-serif"
    font_body = "'Epilogue', sans-serif"
    logo_url = cg._logo_slot_data_url(5) or ""
    logo_top_img = (
        f'<img class="logo-top" src="{logo_url}" alt="" />' if logo_url else ""
    )
    handle = "@sindicompanybr"
    return fn(
        titulo=titulo,
        body=body,
        handle=handle,
        logo_top_img=logo_top_img,
        head_fonts=head_fonts,
        font_display=font_display,
        font_body=font_body,
        foto_capa_url=foto_url,
    )


def _render_pngs() -> list[tuple[str, Path]]:
    """Renderiza todas as 42 capas em PNG reduzido. Reusa um Playwright
    para acelerar — abre browser uma vez, renderiza N paginas."""
    from playwright.sync_api import sync_playwright

    foto_url = _placeholder_photo_data_url()
    print(f"[preview] foto placeholder: {len(foto_url) // 1024} KB")

    items = list(cg.COVER_ARCHETYPES_SC.items())
    print(f"[preview] {len(items)} arquetipos para renderizar")

    results: list[tuple[str, Path]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            ctx = browser.new_context(
                viewport={"width": cg.SLIDE_W, "height": cg.SLIDE_H},
                device_scale_factor=PREVIEW_SCALE,
            )
            for i, (name, fn) in enumerate(items, 1):
                t0 = time.time()
                html = _make_html(name, fn, foto_url)
                page = ctx.new_page()
                page.set_content(html, wait_until="networkidle")
                try:
                    page.wait_for_function(
                        "document.fonts && document.fonts.status === 'loaded'",
                        timeout=8000,
                    )
                except Exception:
                    pass
                out = OUT_DIR / f"{i:02d}_{name}.png"
                page.screenshot(
                    path=str(out),
                    full_page=False,
                    type="png",
                    clip={"x": 0, "y": 0, "width": cg.SLIDE_W, "height": cg.SLIDE_H},
                )
                page.close()
                dt = time.time() - t0
                print(f"[preview] {i:02d}/{len(items)} {name:18s} -> {out.name} ({dt:.1f}s)")
                results.append((name, out))
        finally:
            browser.close()
    return results


def _build_mosaic(results: list[tuple[str, Path]]) -> Path:
    """Monta grid 6 colunas x 7 linhas (42 = 6x7) com labels."""
    from PIL import Image, ImageDraw, ImageFont

    # Grid dinamico em funcao da quantidade — minimiza cells vazios.
    n = len(results)
    import math as _m
    cols = min(5, n)
    rows = _m.ceil(n / cols)
    cell_w, cell_h = 614, 768  # thumb size
    label_h = 72
    pad = 24
    grid_w = cols * cell_w + (cols + 1) * pad
    grid_h = rows * (cell_h + label_h) + (rows + 1) * pad
    bg = (245, 240, 232)  # Paper-ish
    mosaic = Image.new("RGB", (grid_w, grid_h), bg)
    draw = ImageDraw.Draw(mosaic)

    font_label = None
    for fp in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ):
        if os.path.exists(fp):
            try:
                font_label = ImageFont.truetype(fp, 32)
                break
            except OSError:
                pass
    if font_label is None:
        font_label = ImageFont.load_default()

    for idx, (name, path) in enumerate(results):
        r = idx // cols
        c = idx % cols
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((cell_w, cell_h), Image.LANCZOS)
        mosaic.paste(thumb, (x + (cell_w - thumb.width) // 2, y))
        # Label
        meta = cg.COVER_ARCHETYPES_SC.get(name)
        # has-photo prefix
        has_photo = name in {
            "dark-premium", "magazine-cover", "split-portrait", "hero-portrait",
            "avatar-quote", "photo-circle", "photo-banner", "floating-card",
            "photo-blur", "cinema", "polaroid", "portrait-frame",
            "photo-strip", "photo-grid",
        }
        prefix = "📷 " if has_photo else "   "
        label = f"{prefix}{idx + 1:02d}. {name}"
        bbox = draw.textbbox((0, 0), label, font=font_label)
        tw = bbox[2] - bbox[0]
        draw.text(
            (x + (cell_w - tw) // 2, y + cell_h + 12),
            label,
            fill=(24, 32, 40),
            font=font_label,
        )

    mosaic.save(MOSAIC_PATH, format="PNG", optimize=True)
    return MOSAIC_PATH


def main() -> int:
    print("[preview] iniciando")
    print(f"[preview] output dir: {OUT_DIR}")
    print(f"[preview] preview size: {PREVIEW_W}x{PREVIEW_H} per cover")
    results = _render_pngs()
    print("[preview] montando mosaico...")
    out = _build_mosaic(results)
    print(f"[preview] mosaico: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
