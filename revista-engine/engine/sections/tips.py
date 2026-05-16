"""
S05 — Dicas Práticas.

1 página fixa (cabe 6–8 dicas; pode crescer pra 2 se preciso). Tom direto,
sem jargão, acionável (Doc 01 §3 S05).

Inputs:
- mes_referencia (str)
- titulo_secao (str opcional) — substitui "Dicas práticas" se passado
- intro (str opcional) — texto curto de abertura
- dicas (list[dict]):
  - titulo (str)
  - corpo (str, 1–2 linhas)
"""

from __future__ import annotations

import unicodedata

from .base import Section


class Tips(Section):
    """Dicas Práticas (S05)."""

    type = "tips"
    label = "Dicas Práticas"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        dicas = inputs.get("dicas") or []
        if not isinstance(dicas, list) or not dicas:
            errors.append("Dicas: 'dicas' precisa ser lista não-vazia")
        elif len(dicas) > 8:
            errors.append(f"Dicas: máximo 8 itens (recebido {len(dicas)})")
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        titulo = (inputs.get("titulo_secao") or "Dicas práticas").strip()
        intro = (inputs.get("intro") or "").strip()
        dicas = list(inputs.get("dicas") or [])[:8]

        cards_html = "\n".join(
            f"""
      <article class="dica-card">
        <div class="dica-card__num">{i+1:02d}</div>
        <div class="dica-card__divider"></div>
        <div class="dica-card__body">
          <h3 class="dica-card__titulo">{_escape(d.get('titulo', ''))}</h3>
          <p class="dica-card__corpo">{_escape(d.get('corpo', ''))}</p>
        </div>
      </article>"""
            for i, d in enumerate(dicas)
        )

        intro_html = (
            f'<p class="tips__intro">{_escape(intro)}</p>'
            if intro else ""
        )

        return f"""
<section class="page tips-page">
  <div class="tips__content">
    <header class="tips__header">
      <div class="tips__kicker">DICAS PRÁTICAS · {_escape(mes)}</div>
      <h1 class="tips__titulo">{_escape(titulo)}</h1>
      {intro_html}
    </header>

    <div class="tips__grid">
      {cards_html}
    </div>
  </div>
</section>

<style>
  .tips-page {{
    background: var(--white);
    color: var(--onix);
    padding: 48px 56px 40px;
  }}

  .tips__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }}

  .tips__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 12px;
  }}

  .tips__titulo {{
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

  .tips__intro {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.7;
    max-width: 60ch;
  }}

  /* Grid de dicas — 2 colunas, altura preenche resto da página */
  .tips__grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    grid-auto-rows: 1fr;
    gap: 12px;
    flex: 1;
    min-height: 0;
  }}

  .dica-card {{
    background: var(--white);
    border: 1px solid var(--gray-20);
    border-radius: 8px;
    padding: 22px 22px 20px;
    display: block;
    position: relative;
    overflow: hidden;
  }}

  /* Tarja de cor no topo, varia por card pra criar ritmo */
  .dica-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: #84C7D3; /* mint default */
  }}

  .dica-card:nth-child(4n+1)::before {{ background: #84C7D3; }} /* mint */
  .dica-card:nth-child(4n+2)::before {{ background: #D4AE94; }} /* sand-80 */
  .dica-card:nth-child(4n+3)::before {{ background: #B8C0FF; }} /* lavender */
  .dica-card:nth-child(4n+4)::before {{ background: #76B1BC; }} /* mint-80 */

  /* Backgrounds alternados de card pra dar variedade */
  .dica-card:nth-child(8n+5),
  .dica-card:nth-child(8n+6),
  .dica-card:nth-child(8n+7),
  .dica-card:nth-child(8n+8) {{
    background: #FAFAFA;
  }}

  .dica-card__num {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 56px;
    font-weight: 400;
    line-height: 0.85;
    color: #76B1BC;
    font-variant-numeric: tabular-nums;
    margin-bottom: 4px;
    letter-spacing: -0.04em;
  }}

  .dica-card:nth-child(4n+2) .dica-card__num {{ color: #B07A4B; }}
  .dica-card:nth-child(4n+3) .dica-card__num {{ color: #6B70B8; }}
  .dica-card:nth-child(4n+4) .dica-card__num {{ color: #1A1C29; }}

  .dica-card__divider {{
    width: 32px;
    height: 2px;
    background: var(--mint-80);
    margin-bottom: 10px;
  }}

  .dica-card:nth-child(4n+2) .dica-card__divider {{ background: #B07A4B; }}
  .dica-card:nth-child(4n+3) .dica-card__divider {{ background: #6B70B8; }}
  .dica-card:nth-child(4n+4) .dica-card__divider {{ background: #1A1C29; }}

  .dica-card__body {{
    margin-top: 0;
  }}

  .dica-card__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 18px;
    font-weight: 400;
    line-height: 1.1;
    color: var(--onix);
    margin-bottom: 8px;
    letter-spacing: -0.015em;
  }}

  .dica-card__corpo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11.5px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.8;
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
