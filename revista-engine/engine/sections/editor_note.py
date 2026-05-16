"""
S12C — Nota da Edição.

Página opcional renderizada quando a editora preenche 'notas_editor'
no form de Nova Edição. Texto livre da editora pra essa edição
específica (algo que ela quer comunicar diretamente, fora dos
demais cadernos editoriais).

Inputs:
- texto (str)
- mes_referencia (str)
- nome_condominio (str opcional)
"""

from __future__ import annotations

import unicodedata

from .base import Section


class EditorNote(Section):
    """Nota da Edição — S12C."""

    type = "editor_note"
    label = "Nota da Edição"

    def validate(self, inputs: dict) -> list[str]:
        return []  # texto vazio = não inclui (composer já condiciona)

    def paginate(self, inputs: dict) -> int:
        return 1 if (inputs.get("texto") or "").strip() else 0

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return self._render(inputs, theme)

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return self._render(inputs, theme)

    def _render(self, inputs: dict, theme) -> list[str]:
        texto = (inputs.get("texto") or "").strip()
        if not texto:
            return []
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        condo = (inputs.get("nome_condominio") or "").strip()

        # Quebra em parágrafos (linhas em branco)
        paragrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
        if not paragrafos:
            paragrafos = [texto]
        body_html = "\n".join(
            f'<p class="note__p">{_escape(p)}</p>' for p in paragrafos
        )

        return [f"""
<section class="page editor-note-page">
  <div class="note__content">
    <header class="note__header">
      <div class="note__kicker">NOTA DESTA EDIÇÃO · {_escape(mes)}</div>
      <h1 class="note__titulo">Da editora para você</h1>
    </header>
    <div class="note__body">{body_html}</div>
    {f'<footer class="note__footer">{_escape(condo)}</footer>' if condo else ''}
  </div>
</section>

<style>
  .editor-note-page {{
    background: var(--white);
    color: var(--onix);
    padding: 60px 64px 48px;
  }}
  .note__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }}
  .note__header {{
    border-bottom: 2px solid var(--mint);
    padding-bottom: 16px;
  }}
  .note__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.26em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 10px;
  }}
  .note__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 38px;
    font-weight: 400;
    line-height: 1.0;
    letter-spacing: -0.025em;
    color: var(--onix);
    margin: 0;
  }}
  .note__body {{
    flex: 1;
    min-height: 0;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13.5px;
    line-height: 1.6;
    color: var(--onix);
    max-width: 65ch;
  }}
  .note__p {{ margin: 0 0 12px; }}
  .note__p:last-child {{ margin-bottom: 0; }}
  .note__footer {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--onix);
    opacity: 0.5;
    border-top: 1px solid var(--gray-20);
    padding-top: 12px;
  }}
</style>
"""]


def _escape(s: str) -> str:
    return (
        unicodedata.normalize("NFC", s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
