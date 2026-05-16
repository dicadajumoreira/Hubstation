"""
S12B — Vida Condominial.

Matéria secundária editorial. 1-2 páginas (dinâmico) — função do tamanho
do texto. Tom MAIS LEVE que a Matéria de Capa (Doc 01 §3 S12B).

Inputs:
- kicker (str, ≤3 palavras)
- titulo (str, 8–14 palavras)
- subtitulo (str)
- corpo (str, 300–600 palavras — uma de: texto corrido, lista numerada, Q&A)
- foto_principal (str opcional)
- fontes (list[str] opcional, NÃO obrigatórias diferente da Matéria de Capa)
- mes_referencia (str)
"""

from __future__ import annotations

import unicodedata

import re

from .base import Section


class LifestyleArticle(Section):
    """Vida Condominial (S12B)."""

    type = "lifestyle_article"
    label = "Vida Condominial"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        if not inputs.get("titulo"):
            errors.append("Vida Condominial: 'titulo' é obrigatório")
        if not inputs.get("corpo"):
            errors.append("Vida Condominial: 'corpo' é obrigatório")
        else:
            n = len(inputs["corpo"].split())
            if n < 200:
                errors.append(
                    f"Vida Condominial: corpo curto ({n} palavras; ideal 300-600)"
                )
        kicker = inputs.get("kicker", "")
        if kicker and len(kicker.split()) > 4:
            errors.append("Vida Condominial: 'kicker' deveria ter até 3 palavras")
        return errors

    def paginate(self, inputs: dict) -> int:
        # Sempre 1 por enquanto. Quando passar de ~600 palavras consideramos 2.
        n = len((inputs.get("corpo") or "").split())
        return 2 if n > 700 else 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        kicker = (inputs.get("kicker") or "VIDA CONDOMINIAL").strip().upper()
        titulo = (inputs.get("titulo") or "").strip()
        subtitulo = (inputs.get("subtitulo") or "").strip()
        corpo = (inputs.get("corpo") or "").strip()
        foto = (inputs.get("foto_principal") or "").strip()
        fontes = list(inputs.get("fontes") or [])

        # Background do hero
        if foto:
            photo_css = (
                f"background-image: url('{_escape_attr(foto)}');\n"
                f"      background-size: cover;\n"
                f"      background-position: center;\n"
                f"      background-repeat: no-repeat;"
            )
        else:
            photo_css = (
                "background: linear-gradient(120deg, "
                "var(--lavender) 0%, var(--mint) 50%, var(--mint-80) 100%);"
            )

        # Quebrar parágrafos
        paragrafos = [p.strip() for p in corpo.split("\n\n") if p.strip()]
        if not paragrafos:
            paragrafos = [corpo] if corpo else []
        paragrafos = [_strip_inline_citations(p) for p in paragrafos]
        paragrafos = [p for p in paragrafos if p]

        body_html = "\n".join(
            f'<p class="life__p">{_escape(p)}</p>' for p in paragrafos
        )

        # Fontes movidas pro Expediente — não exibimos mais aqui.
        fontes_html = ""

        subtitulo_html = (
            f'<p class="life__subtitulo">{_escape(subtitulo)}</p>'
            if subtitulo else ""
        )

        return f"""
<section class="page life-page">
  <header class="life__hero" style="{photo_css}">
    <div class="life__hero-overlay"></div>
    <div class="life__hero-content">
      <div class="life__kicker">{_escape(kicker)} · {_escape(mes)}</div>
      <h1 class="life__titulo">{_escape(titulo)}</h1>
      {subtitulo_html}
    </div>
  </header>

  <div class="life__body">
    <div class="life__cols">{body_html}</div>
    {fontes_html}
  </div>
</section>

<style>
  .life-page {{
    background: var(--white);
    color: var(--onix);
    padding: 0;
    display: flex;
    flex-direction: column;
  }}

  .life__hero {{
    position: relative;
    height: 320px;
    flex-shrink: 0;
    overflow: hidden;
  }}

  .life__hero-overlay {{
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(
      180deg,
      rgba(26,28,41,0.0) 0%,
      rgba(26,28,41,0.0) 30%,
      rgba(26,28,41,0.65) 75%,
      rgba(26,28,41,0.92) 100%
    );
  }}

  .life__hero-content {{
    position: absolute;
    left: 56px; right: 56px; bottom: 36px;
    color: var(--white);
  }}

  .life__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--sand);
    margin-bottom: 10px;
  }}

  .life__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 40px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--white);
    max-width: 18ch;
    margin-bottom: 8px;
    text-wrap: balance;
  }}

  .life__subtitulo {{
    /* Subtítulo destacado com fundo (pílula sand sobre o hero) */
    display: inline-block;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    font-weight: 500;
    line-height: 1.4;
    color: var(--onix);
    background: var(--sand);
    padding: 6px 12px;
    border-radius: 4px;
    max-width: 50ch;
  }}

  .life__body {{
    padding: 32px 56px 40px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }}

  .life__cols {{
    flex: 1;
    max-width: 60ch;
    margin: 0 auto;
  }}

  .life__p {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12.5px;
    line-height: 1.65;
    color: var(--onix);
    margin-bottom: 14px;
    text-align: justify;
    hyphens: auto;
  }}

  /* Primeiro parágrafo com peso editorial sutilmente diferente */
  .life__p:first-child {{
    font-size: 14px;
    line-height: 1.55;
    color: var(--onix);
  }}

  .life__fontes {{
    display: flex;
    gap: 10px;
    align-items: baseline;
    padding-top: 12px;
    border-top: 1px solid var(--gray-20);
  }}

  .life__fontes-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}

  .life__fontes-text {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    color: var(--onix);
    opacity: 0.7;
  }}
</style>
"""


# Remove citações inline geradas pela IA: ([texto](url)), [texto](url),
# (https://...) e URLs nuas. As fontes aparecem só no rodapé "Fontes".
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
