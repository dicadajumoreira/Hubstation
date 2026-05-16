"""
S03 — Agenda Cultural.

1 página fixa. Zona A (hero ~50%) + zona B (grid 2 colunas com 4–5 cards
secundários). Tom editorial leve.

Inputs (Doc 01 §3 S03):
- mes_referencia (str)
- hero (dict): categoria, titulo, sinopse, foto (path/URL opcional)
- cards_secundarios (list[dict]): categoria, titulo, descricao_curta,
  data (opcional, ex: "30 abr")
"""

from __future__ import annotations

import unicodedata

import re

from .base import Section


# Cor do badge por categoria (lookup case-insensitive)
_CATEGORIA_COLORS = {
    "cinema":     ("#1A1C29", "#FFFFFF"),  # onix bg, white text
    "série":      ("#76B1BC", "#FFFFFF"),  # mint-80
    "serie":      ("#76B1BC", "#FFFFFF"),
    "streaming":  ("#76B1BC", "#FFFFFF"),
    "show":       ("#D4AE94", "#1A1C29"),  # sand-80
    "shows":      ("#D4AE94", "#1A1C29"),
    "música":     ("#D4AE94", "#1A1C29"),
    "musica":     ("#D4AE94", "#1A1C29"),
    "game":       ("#B8C0FF", "#1A1C29"),  # lavender
    "games":      ("#B8C0FF", "#1A1C29"),
    "tech":       ("#B8C0FF", "#1A1C29"),
    "arte":       ("#84C7D3", "#1A1C29"),  # mint
    "exposição":  ("#84C7D3", "#1A1C29"),
    "exposicao":  ("#84C7D3", "#1A1C29"),
    "evento":     ("#84C7D3", "#1A1C29"),
    "livro":      ("#EFCAAF", "#1A1C29"),  # sand-90
    "estreia":    ("#1A1C29", "#FFFFFF"),
}


def _badge_colors(cat: str) -> tuple[str, str]:
    """Retorna (background, color) para o badge da categoria."""
    if not cat:
        return ("#1A1C29", "#FFFFFF")
    key = cat.strip().lower()
    return _CATEGORIA_COLORS.get(key, ("#1A1C29", "#FFFFFF"))


class CulturalAgenda(Section):
    """Agenda Cultural (S03)."""

    type = "cultural_agenda"
    label = "Agenda Cultural"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        hero = inputs.get("hero") or {}
        if not isinstance(hero, dict):
            errors.append("Agenda: 'hero' deve ser um dict")
            return errors
        if not hero.get("titulo"):
            errors.append("Agenda: hero.titulo é obrigatório")

        cards = inputs.get("cards_secundarios") or []
        if not isinstance(cards, list):
            errors.append("Agenda: 'cards_secundarios' deve ser lista")
        elif len(cards) > 18:
            errors.append(f"Agenda: máximo 18 cards secundários (recebido {len(cards)})")
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        hero = inputs.get("hero") or {}
        cards = list(inputs.get("cards_secundarios") or [])[:18]

        hero_html = self._render_hero(hero, theme)
        cards_html = self._render_cards(cards, theme)

        return f"""
<section class="page agenda-page">
  <div class="agenda__content">
    <header class="agenda__header">
      <div class="agenda__kicker">AGENDA CULTURAL · {_escape(mes)}</div>
      <h1 class="agenda__titulo">Vale a pena ver, ouvir e visitar</h1>
      <p class="agenda__sub">
        Uma seleção do que há de mais interessante nos cinemas, palcos
        e telas neste mês.
      </p>
    </header>

    {hero_html}

    <div class="agenda__cards">
      {cards_html}
    </div>
  </div>
</section>

<style>
  .agenda-page {{
    background: var(--white);
    color: var(--onix);
    padding: 48px 56px 40px;
  }}

  .agenda__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }}

  .agenda__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 10px;
  }}

  .agenda__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 38px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
    margin-bottom: 6px;
  }}

  .agenda__sub {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    color: var(--onix);
    opacity: 0.65;
    line-height: 1.4;
    max-width: 60ch;
  }}

  /* Hero */
  .agenda-hero {{
    display: flex;
    gap: 18px;
    align-items: stretch;
    background: var(--gray-5);
    border-radius: 8px;
    overflow: hidden;
  }}

  .agenda-hero__photo {{
    flex: 0 0 50%;
    min-height: 240px;
    background-position: center;
    background-size: cover;
    background-repeat: no-repeat;
  }}

  .agenda-hero__body {{
    flex: 1;
    padding: 18px 22px 18px 0;
    display: block;
  }}

  .agenda-hero__label,
  .agenda-hero__titulo,
  .agenda-hero__sinopse,
  .agenda-hero__data {{
    margin-bottom: 10px;
  }}

  .agenda-hero__data {{
    margin-bottom: 0;
  }}

  .agenda-hero__label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}

  .agenda-hero__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 26px;
    font-weight: 400;
    line-height: 1.0;
    letter-spacing: -0.02em;
    color: var(--onix);
  }}

  .agenda-hero__sinopse {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11.5px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.85;
  }}

  .agenda-hero__data {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--onix);
    opacity: 0.6;
    padding-top: 4px;
    border-top: 1px solid var(--gray-20);
  }}

  /* Cards secundários — grid 4 colunas, preenche a página inteira */
  .agenda__cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    grid-auto-rows: 1fr;
    gap: 10px;
    flex: 1;
    min-height: 0;
  }}

  .agenda-card {{
    background: var(--gray-5);
    border-radius: 6px;
    padding: 10px 11px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow: hidden;
    position: relative;
  }}

  /* Alterna sutilmente o fundo dos cards pra dar ritmo visual */
  .agenda-card:nth-child(4n+1) {{ background: #F4F4F5; }}
  .agenda-card:nth-child(4n+2) {{ background: #EEF7F8; }}  /* mint vibe */
  .agenda-card:nth-child(4n+3) {{ background: #F7EFE9; }}  /* sand vibe */
  .agenda-card:nth-child(4n+4) {{ background: #EEF0FF; }}  /* lavender vibe */

  /* Borda lateral colorida por categoria */
  .agenda-card::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: var(--mint);
  }}
  .agenda-card[data-categoria="NETFLIX"]::before,
  .agenda-card[data-categoria="STREAMING"]::before {{ background: #E50914; }}
  .agenda-card[data-categoria="CINEMA"]::before {{ background: #1A1C29; }}
  .agenda-card[data-categoria="TEATRO"]::before {{ background: #B07A4B; }}
  .agenda-card[data-categoria="MÚSICA"]::before,
  .agenda-card[data-categoria="MUSICA"]::before {{ background: #6B70B8; }}

  .agenda-card__head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 4px;
    margin-bottom: 2px;
  }}

  .badge {{
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 6.5px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }}

  .agenda-card__data {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: var(--onix);
    opacity: 0.55;
  }}

  .agenda-card__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 13px;
    font-weight: 500;
    line-height: 1.15;
    color: var(--onix);
    margin-top: 2px;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  .agenda-card__desc {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9.5px;
    line-height: 1.4;
    color: var(--onix);
    opacity: 0.78;
    margin-top: 4px;
    display: -webkit-box;
    -webkit-line-clamp: 5;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  .agenda-card__local {{
    margin-top: auto;
    padding-top: 6px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 7.5px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--onix);
    opacity: 0.6;
  }}
</style>
"""

    # --------------------------------------------------------------
    def _render_hero(self, hero: dict, theme) -> str:
        if not hero or not hero.get("titulo"):
            return ""
        cat = (hero.get("categoria") or "").strip()
        bg, fg = _badge_colors(cat)
        foto = (hero.get("foto") or "").strip()
        if foto:
            photo_css = (
                f"background-image: url('{_escape_attr(foto)}');"
            )
        else:
            # Placeholder gradient
            photo_css = (
                "background: linear-gradient(135deg, "
                "var(--lavender) 0%, var(--mint) 60%, var(--mint-80) 100%);"
            )
        data = (hero.get("data") or "").strip()

        return f"""
    <article class="agenda-hero">
      <div class="agenda-hero__photo" style="{photo_css}"></div>
      <div class="agenda-hero__body">
        <span class="agenda-hero__label">
          <span class="badge" style="background:{bg};color:{fg}">
            {_escape(cat) or 'DESTAQUE'}
          </span>
        </span>
        <h2 class="agenda-hero__titulo">{_escape(_strip_inline_citations(hero.get('titulo','')))}</h2>
        <p class="agenda-hero__sinopse">{_escape(_strip_inline_citations(hero.get('sinopse','')))}</p>
        {f'<div class="agenda-hero__data">{_escape(data)}</div>' if data else ''}
      </div>
    </article>
"""

    # --------------------------------------------------------------
    def _render_cards(self, cards: list[dict], theme) -> str:
        if not cards:
            return ""
        items = []
        for c in cards:
            cat = (c.get("categoria") or "").strip()
            cat_attr = cat.upper()
            bg, fg = _badge_colors(cat)
            data = (c.get("data") or "").strip()
            local = (c.get("local") or "").strip()
            items.append(f"""
      <article class="agenda-card" data-categoria="{_escape_attr(cat_attr)}">
        <div class="agenda-card__head">
          <span class="badge" style="background:{bg};color:{fg}">{_escape(cat) or '—'}</span>
          {f'<span class="agenda-card__data">{_escape(data)}</span>' if data else ''}
        </div>
        <h3 class="agenda-card__titulo">{_escape(_strip_inline_citations(c.get('titulo','')))}</h3>
        <p class="agenda-card__desc">{_escape(_strip_inline_citations(c.get('descricao_curta','') or c.get('descricao','')))}</p>
        {f'<div class="agenda-card__local">{_escape(local)}</div>' if local else ''}
      </article>""")
        return "\n".join(items)


# Remove citações inline geradas pela IA (markdown links e URLs nuas).
_RE_PAREN_LINK = re.compile(r"\s*\(\[[^\]]+\]\([^)]+\)\)")
_RE_INLINE_LINK = re.compile(r"\s*\[([^\]]+)\]\([^)]+\)")
_RE_PAREN_URL = re.compile(r"\s*\((?:https?://|www\.)[^\s)]+\)")
_RE_BARE_URL = re.compile(r"\s*https?://\S+")


def _strip_inline_citations(text: str) -> str:
    if not text:
        return text
    out = _RE_PAREN_LINK.sub("", text)
    out = _RE_INLINE_LINK.sub(r" \1", out)
    out = _RE_PAREN_URL.sub("", out)
    out = _RE_BARE_URL.sub("", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([.,;:!?])", r"\1", out)
    return out.strip()


def _escape(s: str) -> str:
    return (
        unicodedata.normalize("NFC", s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_attr(s: str) -> str:
    return _escape(s).replace('"', "&quot;").replace("'", "&#39;")
