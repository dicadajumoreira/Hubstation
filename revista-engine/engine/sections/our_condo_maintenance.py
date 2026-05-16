"""
S08 — Nosso Condomínio (Manutenções).

Páginas: 1-N dinâmico (Doc 01 §3 S08).

Regras de paginação:
- Manutenção com 6+ fotos → página inteira (hero) com foto grande + grid
- Manutenção com 3-5 fotos → card grande (large), 1 por página coletiva
- Manutenção com 1-2 fotos → card pequeno (small), até 2 por página
- Padrão: máx 6 fotos por página em A4

Para preview com placeholders, foto vira background colorido baseado no
hash do título.

Inputs:
- mes_referencia (str)
- nome_condominio (str)
- manutencoes (list[dict]):
  - titulo (str)
  - descricao (str opcional)
  - tipo_badge ('MANUTENÇÃO' | 'JARDIM' | 'ENGENHARIA' | 'OPERACIONAL' | 'SEGURANÇA')
  - fotos (list[str]) — paths/URLs ou strings vazias para placeholder
"""

from __future__ import annotations

import unicodedata

import hashlib

from .base import Section


_BADGE_COLORS = {
    "jardim":       ("#84C7D3", "#1A1C29"),
    "piscina":      ("#84C7D3", "#1A1C29"),
    "elevador":     ("#1A1C29", "#FFFFFF"),
    "maquinário":   ("#1A1C29", "#FFFFFF"),
    "maquinario":   ("#1A1C29", "#FFFFFF"),
    "pintura":      ("#D4AE94", "#1A1C29"),
    "reforma":      ("#D4AE94", "#1A1C29"),
    "limpeza":      ("#76B1BC", "#FFFFFF"),
    "hidráulica":   ("#B8C0FF", "#1A1C29"),
    "hidraulica":   ("#B8C0FF", "#1A1C29"),
    "elétrica":     ("#1A1C29", "#FFFFFF"),
    "eletrica":     ("#1A1C29", "#FFFFFF"),
    "estrutura":    ("#76B1BC", "#FFFFFF"),
    "engenharia":   ("#1A1C29", "#FFFFFF"),
    "operacional":  ("#76B1BC", "#FFFFFF"),
    "segurança":    ("#1A1C29", "#84C7D3"),
    "seguranca":    ("#1A1C29", "#84C7D3"),
    "manutenção":   ("#76B1BC", "#FFFFFF"),
    "manutencao":   ("#76B1BC", "#FFFFFF"),
}


def _badge_colors(badge: str) -> tuple[str, str]:
    return _BADGE_COLORS.get((badge or "manutenção").strip().lower(),
                              ("#76B1BC", "#FFFFFF"))


def _empacotar_por_fotos(mans: list[dict]) -> list[list[dict]]:
    """Distribui as manutenções em páginas com no máximo 2 pastas e
    até 6 fotos cada.

    Cada manutenção usa até 4 fotos próprias. Empacotador fecha a página
    quando adicionar a próxima ultrapassaria 6 fotos OU quando já tem
    2 pastas. Garante que todos os itens são listados.
    """
    MAX_PASTAS = 2
    MAX_FOTOS = 6
    pages: list[list[dict]] = []
    cur: list[dict] = []
    cur_count = 0
    for m in mans:
        n_disp = len(m.get("fotos") or [])
        n_usar = min(max(1, n_disp), 4)
        # Fecha se ultrapassaria 6 fotos OU já tem 2 pastas
        if cur and (cur_count + n_usar > MAX_FOTOS or len(cur) >= MAX_PASTAS):
            pages.append(cur)
            cur = []
            cur_count = 0
        item = dict(m)
        item["fotos_usadas"] = (m.get("fotos") or [])[:n_usar]
        cur.append(item)
        cur_count += n_usar
    if cur:
        pages.append(cur)
    return pages


# Paleta de placeholder (8 tonalidades sand/mint/lavender pra variar)
_PLACEHOLDER_PALETTES = [
    ("#84C7D3", "#76B1BC"),   # mint
    ("#D4AE94", "#B07A4B"),   # sand-80 → mais escuro
    ("#B8C0FF", "#6B70B8"),   # lavender
    ("#76B1BC", "#1A1C29"),   # mint-80 → onix
    ("#DABDA9", "#B07A4B"),   # sand
    ("#EFCAAF", "#D4AE94"),   # sand-90 → sand-80
    ("#84C7D3", "#1A1C29"),   # mint → onix
    ("#B8C0FF", "#84C7D3"),   # lavender → mint
]


def _placeholder_gradient(seed: str) -> str:
    """Gera CSS gradient para placeholder de foto baseado em hash do seed."""
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    c1, c2 = _PLACEHOLDER_PALETTES[h % len(_PLACEHOLDER_PALETTES)]
    angle = 100 + (h >> 8) % 80  # 100-180 graus
    return f"background: linear-gradient({angle}deg, {c1} 0%, {c2} 100%);"


def _photo_bg(foto: str, seed: str) -> str:
    """Background CSS pra um slot de foto (real ou placeholder)."""
    if foto:
        return (
            f"background-image: url('{_escape_attr(foto)}');"
            f"background-size: cover; background-position: center;"
        )
    return _placeholder_gradient(seed)


def _display_size(n_photos: int) -> str:
    if n_photos >= 6:
        return "hero"
    if n_photos >= 3:
        return "large"
    return "small"


class OurCondoMaintenance(Section):
    """Nosso Condomínio (Manutenções) — S08."""

    type = "our_condo_maintenance"
    label = "Nosso Condomínio — Manutenções"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        mans = inputs.get("manutencoes") or []
        if not isinstance(mans, list):
            errors.append("Manutenções: 'manutencoes' deve ser lista")
        return errors

    def paginate(self, inputs: dict) -> int:
        # 1 abertura + N páginas. Empacotamento dinâmico por nº de fotos.
        mans = list(inputs.get("manutencoes") or [])
        return 1 + max(1, len(_empacotar_por_fotos(mans)))

    def render_a4(self, inputs: dict, theme) -> list[str]:
        mans = list(inputs.get("manutencoes") or [])
        paginas_de_itens = _empacotar_por_fotos(mans) or [[]]

        pages = [self._render_abertura(inputs, theme)]
        for itens in paginas_de_itens:
            chunk_inputs = dict(inputs)
            chunk_inputs["manutencoes"] = itens
            pages.append(self._render_cards(chunk_inputs, theme))
        return pages

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return self.render_a4(inputs, theme)

    def _render_abertura(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        condo = (inputs.get("nome_condominio") or "").strip().upper()
        foto = (inputs.get("foto_capa_caderno") or "").strip()

        # Foto vertical (portrait) → preenche tudo (cover); horizontal/quadrada
        # → contém sem cortar (contain) sobre fundo onix. Detecção via PIL.
        if foto:
            is_portrait = _is_portrait(foto)
            size_mode = "cover" if is_portrait else "contain"
            foto_bg_css = (
                f"background-image: url('{_escape_attr(foto)}');"
                f"background-size: {size_mode};"
                f"background-position: center;"
                f"background-repeat: no-repeat;"
                f"background-color: var(--onix);"
            )
        else:
            foto_bg_css = (
                "background: linear-gradient(135deg, "
                "#84C7D3 0%, #76B1BC 35%, #1A1C29 100%);"
            )

        return f"""
<section class="page maint-cover-page">
  <div class="maint-cover__foto" style="{foto_bg_css}"></div>
  <div class="maint-cover__texto">
    <div class="maint-cover__kicker">{_escape(condo)} · {_escape(mes)}</div>
    <h1 class="maint-cover__titulo">Nosso<br>Condomínio</h1>
    <p class="maint-cover__lede">As manutenções, melhorias e cuidados que fizemos por aqui este mês.</p>
  </div>
</section>

<style>
  .maint-cover-page {{
    background: var(--white);
    color: var(--onix);
    padding: 0;
    display: flex;
    flex-direction: column;
  }}

  .maint-cover__foto {{
    flex: 1 1 auto;
    height: 70%;
    width: 100%;
  }}

  .maint-cover__texto {{
    flex: 0 0 30%;
    padding: 32px 56px 40px;
    background: var(--white);
    display: flex;
    flex-direction: column;
    justify-content: center;
    border-top: 3px solid var(--mint);
  }}

  .maint-cover__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 14px;
  }}

  .maint-cover__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 60px;
    font-weight: 400;
    line-height: 0.92;
    letter-spacing: -0.03em;
    color: var(--onix);
    margin: 0 0 12px;
  }}

  .maint-cover__lede {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.65;
    max-width: 60ch;
    margin: 0;
  }}
</style>
"""

    def _render_cards(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        condo = (inputs.get("nome_condominio") or "").strip()
        mans = list(inputs.get("manutencoes") or [])

        # Cada manutenção da página vira uma "seção" com badge + título +
        # grid de fotos (cada item usa seu campo 'fotos_usadas' definido
        # pelo empacotamento; total da página fica entre 4 e 6 fotos).
        secoes_html = "\n".join(
            self._render_secao(m, theme) for m in mans
        )

        return f"""
<section class="page maint-page">
  <div class="maint__content">
    <header class="maint__header">
      <div class="maint__kicker">NOSSO CONDOMÍNIO · {_escape(mes)}</div>
      <h1 class="maint__titulo">O que fizemos pelo {_escape(condo)} este mês</h1>
    </header>

    <div class="maint__list">
      {secoes_html}
    </div>
  </div>
</section>

<style>
  .maint-page {{
    background: var(--white);
    color: var(--onix);
    padding: 48px 56px 40px;
  }}

  .maint__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }}

  .maint__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 10px;
  }}

  .maint__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 36px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
    margin-bottom: 6px;
    max-width: 22ch;
    text-wrap: balance;
  }}

  .maint__list {{
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}

  .maint-secao {{
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}

  .maint-secao__head {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-wrap: wrap;
  }}

  .badge {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 3px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
  }}

  .maint-secao__titulo {{
    /* Stack robusta de fontes pra cobrir 100% pt-BR (acentos, cedilha,
       til, circunflexo). Epilogue primeiro; se falhar, cai pra fontes
       do sistema (DejaVu/Liberation no Linux) que sempre renderizam
       caracteres acentuados. */
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 19px;
    font-weight: 600;
    line-height: 1.1;
    color: var(--onix);
    letter-spacing: -0.018em;
    margin: 0;
  }}

  .maint-secao__grid {{
    flex: 1;
    min-height: 0;
    display: grid;
    gap: 8px;
  }}
  .maint-secao__grid--1 {{ grid-template-columns: 1fr; }}
  .maint-secao__grid--2 {{ grid-template-columns: 1fr 1fr; }}
  .maint-secao__grid--3 {{ grid-template-columns: 1.4fr 1fr 1fr; grid-template-rows: 1fr 1fr; }}
  .maint-secao__grid--3 > :first-child {{ grid-row: span 2; }}
  .maint-secao__grid--4 {{ grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }}

  .maint-foto {{
    border-radius: 6px;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    min-height: 0;
  }}
</style>
"""

    def _render_secao(self, m: dict, theme) -> str:
        titulo = (m.get("titulo") or "").strip()
        badge = (m.get("tipo_badge") or "MANUTENÇÃO").strip()
        # 'fotos_usadas' é definido pelo empacotador (até 4 por seção).
        # Se não vier, fallback: pega tudo de 'fotos' (até 4).
        fotos = list(m.get("fotos_usadas") or (m.get("fotos") or [])[:4])
        n = max(1, min(4, len(fotos)))
        bg, fg = _badge_colors(badge)

        if fotos:
            cells = []
            for i, foto in enumerate(fotos[:n]):
                seed = titulo + str(i) + foto
                photo_bg = _photo_bg(foto, seed)
                cells.append(f'<div class="maint-foto" style="{photo_bg}"></div>')
            grid_html = (
                f'<div class="maint-secao__grid maint-secao__grid--{n}">'
                f'{"".join(cells)}'
                f'</div>'
            )
        else:
            # Sem fotos: ainda lista o item (placeholder gradient)
            seed = titulo or "manut"
            photo_bg = _photo_bg("", seed)
            grid_html = (
                f'<div class="maint-secao__grid maint-secao__grid--1">'
                f'<div class="maint-foto" style="{photo_bg}"></div>'
                f'</div>'
            )

        return f"""
      <article class="maint-secao">
        <div class="maint-secao__head">
          <span class="badge" style="background:{bg};color:{fg}">{_escape(badge)}</span>
          <h3 class="maint-secao__titulo">{_escape(titulo)}</h3>
        </div>
        {grid_html}
      </article>"""


def _is_portrait(foto_url: str) -> bool:
    """Detecta se a foto é vertical (altura > largura).

    Aceita file:// URI (path local) ou http(s):// URL (Supabase). Em
    qualquer falha de leitura (formato não suportado, rede off,
    arquivo ausente), retorna False — fallback é o layout 'contain'
    que é seguro pra qualquer proporção.
    """
    if not foto_url:
        return False
    try:
        from io import BytesIO
        from urllib.parse import unquote, urlparse

        from PIL import Image  # type: ignore

        parsed = urlparse(foto_url)
        if parsed.scheme in ("file", ""):
            local_path = unquote(parsed.path)
            with Image.open(local_path) as img:
                w, h = img.size
        elif parsed.scheme in ("http", "https"):
            import urllib.request
            req = urllib.request.Request(
                foto_url, headers={"User-Agent": "revista-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with Image.open(BytesIO(data)) as img:
                w, h = img.size
        else:
            return False
        return h > w
    except Exception as e:  # noqa: BLE001
        print(f"[s08] _is_portrait falhou pra {foto_url[:80]}: {type(e).__name__}: {e}", flush=True)
        return False


def _escape(s: str) -> str:
    return (
        unicodedata.normalize("NFC", s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_attr(s: str) -> str:
    return _escape(s).replace('"', "&quot;").replace("'", "&#39;")
