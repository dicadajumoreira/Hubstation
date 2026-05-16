"""
S09 — Nosso Condomínio (Eventos).

Caderno limpo: só grids de 4-6 fotos por página, sem títulos por foto.
Apenas um header de página com kicker editorial e título 'O que rolou
no {condomínio}'.

Inputs:
- mes_referencia (str)
- nome_condominio (str)
- eventos (list[dict]):
  - titulo (str) — usado APENAS pra seed do placeholder se faltar foto
  - fotos (list[str]) — todas as fotos vão pro pool da página
"""

from __future__ import annotations

import unicodedata

import hashlib

from .base import Section


_PLACEHOLDER_PALETTES = [
    ("#84C7D3", "#76B1BC"),
    ("#D4AE94", "#B07A4B"),
    ("#B8C0FF", "#6B70B8"),
    ("#76B1BC", "#1A1C29"),
    ("#DABDA9", "#B07A4B"),
    ("#EFCAAF", "#D4AE94"),
    ("#84C7D3", "#1A1C29"),
    ("#B8C0FF", "#84C7D3"),
]


def _placeholder_gradient(seed: str) -> str:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    c1, c2 = _PLACEHOLDER_PALETTES[h % len(_PLACEHOLDER_PALETTES)]
    angle = 100 + (h >> 8) % 80
    return f"background: linear-gradient({angle}deg, {c1} 0%, {c2} 100%);"


def _photo_bg(foto: str, seed: str) -> str:
    if foto:
        return (
            f"background-image: url('{_escape_attr(foto)}');"
            f"background-size: cover; background-position: center;"
        )
    return _placeholder_gradient(seed)


def _todas_as_fotos(eventos: list[dict]) -> list[str]:
    """Pool de fotos de todos os eventos, mantendo ordem dos eventos.
    Sem agrupamento por título — só fotos."""
    out: list[str] = []
    for ev in eventos:
        fotos = list(ev.get("fotos") or [])
        out.extend(fotos)
    return out


def _empacotar_fotos(fotos: list[str]) -> list[list[str]]:
    """Distribui fotos em páginas: tenta 6 por página, mas se sobra
    1-3 no fim, redistribui pra evitar página esquelética."""
    n = len(fotos)
    if n == 0:
        return []
    if n <= 6:
        return [fotos]

    # Calcula número de páginas alvo: arredonda pra cima, mas tentando
    # manter cada página com 4-6 fotos.
    n_pages = (n + 5) // 6  # 6 por página inicialmente
    # Se a última página fica com 1-3 fotos, tenta nivelar.
    base = n // n_pages
    extra = n % n_pages

    pages: list[list[str]] = []
    idx = 0
    for i in range(n_pages):
        size = base + (1 if i < extra else 0)
        # Garante 4-6 fotos por página (limita pelos extremos)
        size = max(4, min(6, size))
        pages.append(fotos[idx : idx + size])
        idx += size
    # Se sobraram fotos por causa do clamp, joga na última página
    if idx < n:
        pages[-1].extend(fotos[idx:])
    return pages


class OurCondoEvents(Section):
    """Caderno de Eventos — S09. 4-6 fotos por página, sem títulos."""

    type = "our_condo_events"
    label = "Nosso Condomínio — Eventos"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        eventos = inputs.get("eventos") or []
        if not isinstance(eventos, list):
            errors.append("Eventos: 'eventos' deve ser lista")
        return errors

    def paginate(self, inputs: dict) -> int:
        eventos = list(inputs.get("eventos") or [])
        fotos = _todas_as_fotos(eventos)
        # Sempre 1 página mínima quando a seção é incluída
        if not fotos:
            return 1
        return max(1, len(_empacotar_fotos(fotos)))

    def render_a4(self, inputs: dict, theme) -> list[str]:
        eventos = list(inputs.get("eventos") or [])
        fotos = _todas_as_fotos(eventos)
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        condo = (inputs.get("nome_condominio") or "").strip()
        if not fotos:
            # Sem fotos: página de abertura do caderno (a editora marcou
            # tem_eventos=sim mas o ZIP veio vazio ou não foi enviado).
            return [self._render_abertura(mes, condo, theme)]
        paginas = _empacotar_fotos(fotos)
        return [
            self._render_page(pg, mes, condo, theme, idx=i, total=len(paginas))
            for i, pg in enumerate(paginas)
        ]

    def _render_abertura(self, mes: str, condo: str, theme) -> str:
        return f"""
<section class="page event-page">
  <div class="ev__abertura">
    <div class="ev__abertura-content">
      <div class="ev__kicker">EVENTO NO CONDOMÍNIO · {_escape(mes)}</div>
      <h1 class="ev__titulo">O que rolou no {_escape(condo)}</h1>
      <p class="ev__abertura-lede">As fotos dos eventos deste mês estarão disponíveis em breve.</p>
    </div>
  </div>
</section>

<style>
  .event-page {{
    background: var(--white);
    color: var(--onix);
    padding: 0;
  }}
  .ev__abertura {{
    width: 100%; height: 100%;
    background: linear-gradient(135deg, #84C7D3 0%, #76B1BC 50%, #1A1C29 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 56px;
  }}
  .ev__abertura-content {{
    color: var(--white);
    text-align: center;
    max-width: 30ch;
  }}
  .ev__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--mint);
    margin-bottom: 18px;
  }}
  .ev__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 56px;
    font-weight: 400;
    line-height: 0.95;
    letter-spacing: -0.025em;
    color: var(--white);
    margin: 0 0 18px;
    text-wrap: balance;
  }}
  .ev__abertura-lede {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    color: var(--white);
    opacity: 0.85;
    margin: 0;
  }}
</style>
"""

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return self.render_a4(inputs, theme)

    def _render_page(
        self, fotos: list[str], mes: str, condo: str, theme,
        *, idx: int, total: int,
    ) -> str:
        n = len(fotos)
        cells = []
        for i, foto in enumerate(fotos):
            seed = f"{condo}{idx}{i}{foto}"
            bg = _photo_bg(foto, seed)
            cells.append(f'<div class="ev-foto" style="{bg}"></div>')

        # Só a primeira página leva o título grande; páginas seguintes
        # têm header reduzido pra dar mais espaço pras fotos.
        if idx == 0:
            header_html = f"""
    <header class="ev__header">
      <div class="ev__kicker">EVENTO NO CONDOMÍNIO · {_escape(mes)} · {_escape(condo)}</div>
      <h1 class="ev__titulo">O que rolou no {_escape(condo)}</h1>
    </header>"""
        else:
            header_html = f"""
    <header class="ev__header ev__header--cont">
      <div class="ev__kicker">EVENTO NO CONDOMÍNIO · {_escape(mes)} · {_escape(condo)} · {idx + 1}/{total}</div>
    </header>"""

        return f"""
<section class="page event-page">
  <div class="ev__content">
    {header_html}
    <div class="ev__grid ev__grid--{n}">
      {''.join(cells)}
    </div>
  </div>
</section>

<style>
  .event-page {{
    background: var(--white);
    color: var(--onix);
    padding: 36px 40px;
  }}

  .ev__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }}

  .ev__header {{
    border-bottom: 2px solid var(--mint);
    padding-bottom: 12px;
  }}

  .ev__header--cont {{
    border-bottom: 1px solid var(--gray-20);
    padding-bottom: 8px;
  }}

  .ev__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 6px;
  }}

  .ev__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 36px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.024em;
    color: var(--onix);
    margin: 0;
    max-width: 22ch;
    text-wrap: balance;
  }}

  .ev__grid {{
    flex: 1;
    min-height: 0;
    display: grid;
    gap: 10px;
  }}
  /* 4 fotos: 2x2 */
  .ev__grid--4 {{ grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }}
  /* 5 fotos: foto grande + 4 menores */
  .ev__grid--5 {{
    grid-template-columns: 1fr 1fr 1fr;
    grid-template-rows: 1.4fr 1fr;
  }}
  .ev__grid--5 > :first-child {{ grid-column: 1 / -1; }}
  /* 6 fotos: 3x2 */
  .ev__grid--6 {{ grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 1fr 1fr; }}

  /* Casos extremos (página única com 1-3 fotos) */
  .ev__grid--1 {{ grid-template-columns: 1fr; }}
  .ev__grid--2 {{ grid-template-columns: 1fr 1fr; }}
  .ev__grid--3 {{ grid-template-columns: 1.4fr 1fr 1fr; grid-template-rows: 1fr 1fr; }}
  .ev__grid--3 > :first-child {{ grid-row: span 2; }}

  .ev-foto {{
    border-radius: 6px;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    min-height: 0;
  }}
</style>
"""


def _escape(s: str) -> str:
    return (
        unicodedata.normalize("NFC", s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_attr(s: str) -> str:
    return _escape(s).replace('"', "&quot;").replace("'", "&#39;")
