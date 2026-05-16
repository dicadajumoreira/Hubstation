"""
S07 — Novidades e Legislação.

1 página fixa. 3 notícias dos últimos 30 dias com badge categorizado e
fonte sempre citada (Doc 01 §3 S07).

Inputs:
- mes_referencia (str)
- noticias (list[dict], 3 itens):
  - badge ('LEGISLAÇÃO' | 'MERCADO' | 'NOVIDADE' | 'TECNOLOGIA')
  - titulo (str)
  - data (str) — DD/MM/AAAA ou descritivo
  - resumo (str)
  - fonte (str)
"""

from __future__ import annotations

import re
import unicodedata

from .base import Section


# Cores do badge por tipo
_BADGE_COLORS = {
    "legislação": ("#1A1C29", "#FFFFFF"),
    "legislacao": ("#1A1C29", "#FFFFFF"),
    "mercado":    ("#D4AE94", "#1A1C29"),  # sand-80
    "novidade":   ("#84C7D3", "#1A1C29"),  # mint
    "tecnologia": ("#B8C0FF", "#1A1C29"),  # lavender
    "tech":       ("#B8C0FF", "#1A1C29"),
}


def _badge_colors(badge: str) -> tuple[str, str]:
    return _BADGE_COLORS.get((badge or "").strip().lower(), ("#76B1BC", "#FFFFFF"))


def _normalize_slug(s: str) -> str:
    """Slug para data-tipo (lowercase, sem acentos)."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


class News(Section):
    """Novidades e Legislação (S07)."""

    type = "news"
    label = "Novidades e Legislação"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        items = inputs.get("noticias") or []
        if not isinstance(items, list) or not items:
            errors.append("Novidades: 'noticias' precisa ser lista não-vazia")
        elif len(items) > 8:
            errors.append(f"Novidades: máximo 8 itens (recebido {len(items)})")
        else:
            for i, n in enumerate(items):
                if not n.get("fonte"):
                    errors.append(f"Novidades[{i}]: 'fonte' é obrigatória")
                if not n.get("titulo"):
                    errors.append(f"Novidades[{i}]: 'titulo' é obrigatório")
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        intro = (inputs.get("intro") or "").strip()
        items = list(inputs.get("noticias") or [])[:8]

        cards_html = "\n".join(self._render_card(n) for n in items)

        intro_html = (
            f'<p class="news__intro">{_escape(intro)}</p>'
            if intro else ""
        )

        return f"""
<section class="page news-page">
  <div class="news__content">
    <header class="news__header">
      <div class="news__kicker">NOVIDADES E LEGISLAÇÃO · {_escape(mes)}</div>
      <h1 class="news__titulo">O que aconteceu nos últimos 30 dias</h1>
      {intro_html}
    </header>

    <div class="news__list">
      {cards_html}
    </div>
  </div>
</section>

<style>
  .news-page {{
    background: var(--white);
    color: var(--onix);
    padding: 48px 56px 40px;
  }}

  .news__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }}

  .news__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 12px;
  }}

  .news__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 38px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
    margin-bottom: 8px;
    max-width: 22ch;
    text-wrap: balance;
  }}

  .news__intro {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.7;
    max-width: 60ch;
  }}

  .news__list {{
    display: flex;
    flex-direction: column;
    gap: 14px;
    flex: 1;
    min-height: 0;
  }}

  .news-card {{
    position: relative;
    background: var(--white);
    border: 1px solid var(--gray-20);
    border-radius: 8px;
    padding: 14px 22px 12px 32px;
    display: block;
    flex: 1;
    overflow: hidden;
  }}

  /* Tarja vertical colorida na esquerda — varia por tipo */
  .news-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 6px;
    background: var(--mint-80);
  }}

  .news-card[data-tipo="legislacao"]::before {{ background: #1A1C29; }}
  .news-card[data-tipo="mercado"]::before     {{ background: #B07A4B; }}
  .news-card[data-tipo="novidade"]::before    {{ background: #84C7D3; }}
  .news-card[data-tipo="tecnologia"]::before  {{ background: #6B70B8; }}

  /* Cards alternam entre branco e ultra-claro pra dar ritmo */
  .news-card:nth-child(2n) {{ background: #FAFAFA; }}

  .news-card__body {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .news-card__head {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4px;
  }}

  .badge {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 3px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
  }}

  .news-card__data {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--onix);
    opacity: 0.55;
  }}

  .news-card__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 18px;
    font-weight: 400;
    line-height: 1.12;
    color: var(--onix);
    letter-spacing: -0.018em;
    margin: 6px 0;
  }}

  .news-card__resumo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10.5px;
    line-height: 1.45;
    color: var(--onix);
    opacity: 0.82;
  }}

  .news-card__fonte {{
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid var(--gray-20);
    display: flex;
    align-items: baseline;
    gap: 12px;
  }}

  .news-card__fonte-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}

  .news-card__fonte-text {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: var(--onix);
    opacity: 0.8;
  }}
</style>
"""

    def _render_card(self, n: dict) -> str:
        bg, fg = _badge_colors(n.get("badge", ""))
        tipo_slug = _normalize_slug(n.get("badge", ""))
        return f"""
      <article class="news-card" data-tipo="{tipo_slug}">
        <div class="news-card__head">
          <span class="badge" style="background:{bg};color:{fg}">
            {_escape(n.get('badge', '—'))}
          </span>
          <span class="news-card__data">{_escape(n.get('data', ''))}</span>
        </div>
        <h3 class="news-card__titulo">{_escape(_strip_inline_citations(n.get('titulo', '')))}</h3>
        <p class="news-card__resumo">{_escape(_strip_inline_citations(n.get('resumo', '')))}</p>
      </article>"""


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
