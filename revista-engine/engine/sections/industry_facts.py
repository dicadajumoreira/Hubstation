"""
S06 — Curiosidades do Setor.

1 página fixa. 4–5 fatos sobre o mercado condominial brasileiro com fonte
sempre citada (Doc 01 §3 S06).

Inputs:
- mes_referencia (str)
- curiosidades (list[dict]):
  - fato (str curta) — número/dado/headline
  - contexto (str) — explica/contextualiza
  - fonte (str) — SECOVI-SP, IBGE, CBIC etc.
"""

from __future__ import annotations

import unicodedata

from .base import Section


class IndustryFacts(Section):
    """Curiosidades do Setor (S06)."""

    type = "industry_facts"
    label = "Curiosidades do Setor"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        items = inputs.get("curiosidades") or []
        if not isinstance(items, list) or not items:
            errors.append("Curiosidades: 'curiosidades' precisa ser lista não-vazia")
        elif len(items) > 6:
            errors.append(f"Curiosidades: máximo 6 itens (recebido {len(items)})")
        else:
            for i, c in enumerate(items):
                if not c.get("fonte"):
                    errors.append(f"Curiosidades[{i}]: 'fonte' é obrigatória")
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
        items = list(inputs.get("curiosidades") or [])[:6]

        cards_html = "\n".join(
            f"""
      <article class="fact-card">
        <div class="fact-card__fato">{_escape(c.get('fato', ''))}</div>
        <p class="fact-card__contexto">{_escape(c.get('contexto', ''))}</p>
        <div class="fact-card__fonte">
          <span class="fact-card__fonte-label">Fonte</span>
          <span class="fact-card__fonte-text">{_escape(c.get('fonte', ''))}</span>
        </div>
      </article>"""
            for c in items
        )

        intro_html = (
            f'<p class="industry__intro">{_escape(intro)}</p>'
            if intro else ""
        )

        return f"""
<section class="page industry-page">
  <div class="industry__content">
    <header class="industry__header">
      <div class="industry__kicker">CURIOSIDADES DO SETOR · {_escape(mes)}</div>
      <h1 class="industry__titulo">Números que falam sobre morar bem</h1>
      {intro_html}
    </header>

    <div class="industry__grid">
      {cards_html}
    </div>
  </div>
</section>

<style>
  .industry-page {{
    background: var(--white);
    color: var(--onix);
    padding: 48px 56px 40px;
  }}

  .industry__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }}

  .industry__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 12px;
  }}

  .industry__titulo {{
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

  .industry__intro {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.7;
    max-width: 60ch;
  }}

  /* Grid: 1 grande no topo + 4 menores */
  .industry__grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    grid-auto-rows: 1fr;
    gap: 14px;
    flex: 1;
    min-height: 0;
  }}

  .fact-card {{
    background: var(--gray-5);
    border-radius: 8px;
    padding: 24px 22px 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    position: relative;
    overflow: hidden;
  }}

  .fact-card:nth-child(4n+1) {{ background: #EEF7F8; }} /* mint vibe */
  .fact-card:nth-child(4n+2) {{ background: #F7EFE9; }} /* sand vibe */
  .fact-card:nth-child(4n+3) {{ background: #F1F1FA; }} /* lavender vibe */
  .fact-card:nth-child(4n+4) {{ background: #F4F4F5; }} /* gray */

  .fact-card__fato {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 30px;
    font-weight: 400;
    line-height: 1.0;
    letter-spacing: -0.02em;
    color: var(--onix);
  }}

  .fact-card:nth-child(4n+1) .fact-card__fato {{ color: #1A1C29; }}

  .fact-card__contexto {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11.5px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.78;
    flex: 1;
  }}

  .fact-card__fonte {{
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px solid rgba(26, 28, 41, 0.12);
    display: flex;
    gap: 10px;
    align-items: baseline;
  }}

  .fact-card__fonte-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}

  .fact-card__fonte-text {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 600;
    color: var(--onix);
    opacity: 0.75;
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
