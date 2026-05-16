"""
S10 — Receita do Mês.

1 página fixa. Foto, título, tempo de preparo, ingredientes, modo de preparo
e dica opcional. Receita simples, sazonal ao mês (Doc 01 §3 S10).

Inputs:
- mes_referencia (str)
- titulo_receita (str)
- tempo_preparo (str) — "25 min · serve 8 pessoas"
- foto_receita (str opcional) — caminho/URL
- ingredientes (list[str])
- modo_preparo (list[str])
- dica (str opcional)
- intro (str opcional) — texto curto de abertura
"""

from __future__ import annotations

import unicodedata

from .base import Section


class Recipe(Section):
    """Receita do Mês (S10)."""

    type = "recipe"
    label = "Receita do Mês"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        if not inputs.get("titulo_receita"):
            errors.append("Receita: 'titulo_receita' é obrigatório")
        ing = inputs.get("ingredientes") or []
        if not isinstance(ing, list) or not ing:
            errors.append("Receita: 'ingredientes' precisa ser lista não-vazia")
        prep = inputs.get("modo_preparo") or []
        if not isinstance(prep, list) or not prep:
            errors.append("Receita: 'modo_preparo' precisa ser lista não-vazia")
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        titulo = (inputs.get("titulo_receita") or "").strip()
        tempo = (inputs.get("tempo_preparo") or "").strip()
        foto = (inputs.get("foto_receita") or "").strip()
        intro = (inputs.get("intro") or "").strip()
        ingredientes = list(inputs.get("ingredientes") or [])
        preparo = list(inputs.get("modo_preparo") or [])
        dica = (inputs.get("dica") or "").strip()

        # Background da foto (real ou placeholder warm-toned)
        if foto:
            photo_css = (
                f"background-image: url('{_escape_attr(foto)}');\n"
                f"      background-size: cover;\n"
                f"      background-position: center;\n"
                f"      background-repeat: no-repeat;"
            )
        else:
            photo_css = (
                "background: radial-gradient(ellipse at 60% 40%, "
                "var(--sand-90) 0%, var(--sand) 50%, var(--sand-80) 100%);"
            )

        ingredientes_html = "\n".join(
            f'<li class="ing-item">{_escape(str(i))}</li>' for i in ingredientes
        )
        preparo_html = "\n".join(
            f'<li class="prep-item"><span class="prep-num">{n+1:02d}</span>'
            f'<span class="prep-text">{_escape(str(p))}</span></li>'
            for n, p in enumerate(preparo)
        )

        dica_html = ""
        if dica:
            dica_html = f"""
    <aside class="recipe__dica">
      <div class="recipe__dica-label">Dica da casa</div>
      <p class="recipe__dica-text">{_escape(dica)}</p>
    </aside>"""

        intro_html = (
            f'<p class="recipe__intro">{_escape(intro)}</p>'
            if intro else ""
        )

        return f"""
<section class="page recipe-page">
  <div class="recipe__content">
    <header class="recipe__header">
      <div class="recipe__kicker">RECEITA · {_escape(mes)}</div>
      <h1 class="recipe__titulo">{_escape(titulo)}</h1>
      {f'<div class="recipe__tempo">{_escape(tempo)}</div>' if tempo else ''}
      {intro_html}
    </header>

    <div class="recipe__photo" style="{photo_css}"></div>

    <div class="recipe__cols">
      <div class="recipe__col">
        <h2 class="recipe__sub">Ingredientes</h2>
        <ul class="recipe__ing-list">{ingredientes_html}</ul>
      </div>
      <div class="recipe__col">
        <h2 class="recipe__sub">Modo de preparo</h2>
        <ol class="recipe__prep-list">{preparo_html}</ol>
      </div>
    </div>

    {dica_html}
  </div>
</section>

<style>
  .recipe-page {{
    background: var(--white);
    color: var(--onix);
    padding: 48px 56px 40px;
  }}

  .recipe__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }}

  .recipe__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 10px;
  }}

  .recipe__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 40px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
    margin-bottom: 8px;
  }}

  .recipe__tempo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--sand-80);
    margin-bottom: 8px;
  }}

  .recipe__intro {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    line-height: 1.5;
    color: var(--onix);
    opacity: 0.75;
    max-width: 60ch;
  }}

  .recipe__photo {{
    width: 100%;
    height: 240px;
    border-radius: 8px;
  }}

  .recipe__cols {{
    display: grid;
    grid-template-columns: 5fr 7fr;
    gap: 28px;
  }}

  .recipe__sub {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 20px;
    font-weight: 400;
    color: var(--onix);
    margin-bottom: 12px;
    border-bottom: 1px solid var(--gray-20);
    padding-bottom: 6px;
  }}

  .recipe__ing-list {{
    list-style: none;
    margin: 0; padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  .ing-item {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11.5px;
    line-height: 1.4;
    color: var(--onix);
    padding: 4px 0;
    padding-left: 14px;
    position: relative;
    border-bottom: 1px dotted var(--gray-20);
  }}

  .ing-item::before {{
    content: "";
    position: absolute;
    left: 2px; top: 11px;
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--mint-80);
  }}

  .recipe__prep-list {{
    list-style: none;
    margin: 0; padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}

  .prep-item {{
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }}

  .prep-num {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 14px;
    color: var(--mint-80);
    flex-shrink: 0;
    width: 22px;
    line-height: 1.3;
  }}

  .prep-text {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11.5px;
    line-height: 1.5;
    color: var(--onix);
  }}

  .recipe__dica {{
    background: var(--sand);
    border-radius: 6px;
    padding: 14px 18px;
  }}

  .recipe__dica-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--onix);
    margin-bottom: 6px;
  }}

  .recipe__dica-text {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11.5px;
    line-height: 1.5;
    color: var(--onix);
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
