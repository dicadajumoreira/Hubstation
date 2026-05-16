"""
S04 — Matéria de Capa.

Matéria editorial principal. 2-4 páginas (dinâmico, depende do conteúdo
— por ora rendemos como 1 página rica com layout editorial; expansão
multi-página fica para fase posterior).

Inputs (Doc 01 §3 S04):
- kicker (str, ≤4 palavras)
- manchete (str)
- subtitulo (str)
- foto_principal (str opcional)
- corpo_blocos (list[dict]) — cada bloco tem `tipo` e payload:
  - {tipo: "paragrafo", texto: str}
  - {tipo: "intertitulo", texto: str}
  - {tipo: "pull_quote", texto: str, autor: str opc.}
  - {tipo: "dado_box", numero: str, contexto: str, fonte: str}
  - {tipo: "foto_secundaria", url: str, legenda: str}
- fontes (list[str]) — OBRIGATÓRIO (Doc 01 regra explícita)
- mes_referencia (str)
"""

from __future__ import annotations

import unicodedata

import re

from .base import Section


class CoverStory(Section):
    """Matéria de Capa (S04)."""

    type = "cover_story"
    label = "Matéria de Capa"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        if not inputs.get("manchete"):
            errors.append("Matéria de Capa: 'manchete' é obrigatória")
        if not inputs.get("corpo_blocos"):
            errors.append("Matéria de Capa: 'corpo_blocos' precisa ter pelo menos um bloco")
        fontes = inputs.get("fontes")
        if not fontes or not isinstance(fontes, list) or not any(fontes):
            errors.append("Matéria de Capa: 'fontes' é OBRIGATÓRIA — cite ao menos uma")
        kicker = inputs.get("kicker", "")
        if kicker and len(kicker.split()) > 5:
            errors.append("Matéria de Capa: 'kicker' deveria ter até 4 palavras")
        return errors

    def paginate(self, inputs: dict) -> int:
        # Por ora 1 página fixa. Multi-página vem com paginação dinâmica.
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        kicker = (inputs.get("kicker") or "ESPECIAL DE CAPA").strip().upper()
        manchete = (inputs.get("manchete") or "").strip()
        subtitulo = (inputs.get("subtitulo") or "").strip()
        foto = (inputs.get("foto_principal") or "").strip()
        blocos = list(inputs.get("corpo_blocos") or [])
        fontes = list(inputs.get("fontes") or [])

        # Hero
        if foto:
            photo_css = (
                f"background-image: url('{_escape_attr(foto)}');\n"
                f"      background-size: cover;\n"
                f"      background-position: center;\n"
                f"      background-repeat: no-repeat;"
            )
        else:
            photo_css = (
                "background: linear-gradient(135deg, "
                "var(--mint-80) 0%, var(--lavender) 50%, var(--sand) 100%);"
            )

        body_html = self._render_blocos(blocos)
        # Fontes movidas pro Expediente — não exibimos mais aqui.
        fontes_html = ""

        return f"""
<section class="page story-page">
  <header class="story__hero" style="{photo_css}">
    <div class="story__hero-overlay"></div>
    <div class="story__hero-content">
      <div class="story__kicker">{_escape(kicker)} · {_escape(mes)}</div>
      <h1 class="story__manchete">{_escape(manchete)}</h1>
      {f'<p class="story__subtitulo">{_escape(subtitulo)}</p>' if subtitulo else ''}
    </div>
  </header>

  <div class="story__body">
    {body_html}
    {fontes_html}
  </div>
</section>

<style>
  .story-page {{
    background: var(--white);
    color: var(--onix);
    padding: 0;
    display: flex;
    flex-direction: column;
  }}

  .story__hero {{
    position: relative;
    height: 290px;
    flex-shrink: 0;
    overflow: hidden;
  }}

  .story__hero-overlay {{
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(
      180deg,
      rgba(26,28,41,0.0) 0%,
      rgba(26,28,41,0.0) 35%,
      rgba(26,28,41,0.7) 78%,
      rgba(26,28,41,0.95) 100%
    );
  }}

  .story__hero-content {{
    position: absolute;
    left: 56px; right: 56px; bottom: 36px;
    color: var(--white);
  }}

  .story__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--mint);
    margin-bottom: 14px;
  }}

  .story__manchete {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 38px;
    font-weight: 400;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: var(--white);
    max-width: 16ch;
    margin-bottom: 8px;
    text-wrap: balance;
  }}

  .story__subtitulo {{
    /* Subtítulo destacado com fundo (pílula sand sobre o hero) */
    display: inline-block;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12.5px;
    font-weight: 500;
    line-height: 1.4;
    color: var(--onix);
    background: var(--sand);
    padding: 6px 12px;
    border-radius: 4px;
    max-width: 50ch;
  }}

  .story__body {{
    padding: 24px 56px 28px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-width: 100%;
  }}

  .story__p {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    line-height: 1.5;
    color: var(--onix);
    text-align: justify;
    hyphens: auto;
    margin-bottom: 0;
  }}

  .story__p:first-of-type {{
    font-size: 12.5px;
    line-height: 1.5;
  }}

  .story__intertitulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 18px;
    font-weight: 400;
    line-height: 1.05;
    letter-spacing: -0.015em;
    color: var(--onix);
    margin-top: 6px;
    border-top: 1px solid var(--mint-80);
    padding-top: 8px;
  }}

  .story__pull-quote {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 19px;
    font-weight: 400;
    line-height: 1.15;
    color: var(--mint-80);
    text-align: center;
    padding: 12px 24px;
    border-top: 2px solid var(--mint-80);
    border-bottom: 2px solid var(--mint-80);
    margin: 8px 0;
    letter-spacing: -0.01em;
  }}

  .story__pull-quote::before {{ content: "\\201C"; }}
  .story__pull-quote::after  {{ content: "\\201D"; }}

  .story__pull-quote-autor {{
    display: block;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--onix);
    opacity: 0.6;
    margin-top: 10px;
  }}

  .story__dado {{
    background: var(--mint);
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin: 4px 0;
  }}

  .story__dado-numero {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 28px;
    font-weight: 400;
    line-height: 0.95;
    color: var(--onix);
    letter-spacing: -0.025em;
  }}

  .story__dado-contexto {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11.5px;
    line-height: 1.4;
    color: var(--onix);
    opacity: 0.85;
  }}

  .story__dado-fonte {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--onix);
    opacity: 0.65;
    margin-top: 4px;
  }}

  .story__fontes {{
    display: flex;
    gap: 12px;
    align-items: baseline;
    padding-top: 12px;
    margin-top: 10px;
    border-top: 1px solid var(--gray-20);
  }}

  .story__fontes-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}

  .story__fontes-text {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    color: var(--onix);
    opacity: 0.75;
  }}
</style>
"""

    def _render_blocos(self, blocos: list[dict]) -> str:
        out = []
        for b in blocos:
            tipo = (b.get("tipo") or "paragrafo").strip().lower()
            if tipo == "paragrafo":
                out.append(f'<p class="story__p">{_escape(_strip_inline_citations(b.get("texto", "")))}</p>')
            elif tipo == "intertitulo":
                out.append(f'<h2 class="story__intertitulo">{_escape(_strip_inline_citations(b.get("texto", "")))}</h2>')
            elif tipo == "pull_quote":
                autor = b.get("autor", "").strip()
                autor_html = (
                    f'<span class="story__pull-quote-autor">{_escape(autor)}</span>'
                    if autor else ""
                )
                out.append(
                    f'<blockquote class="story__pull-quote">'
                    f'{_escape(_strip_inline_citations(b.get("texto", "")))}{autor_html}</blockquote>'
                )
            elif tipo == "dado_box":
                out.append(f"""
    <div class="story__dado">
      <div class="story__dado-numero">{_escape(b.get("numero", ""))}</div>
      <div class="story__dado-contexto">{_escape(b.get("contexto", ""))}</div>
      {f'<div class="story__dado-fonte">Fonte · {_escape(b.get("fonte", ""))}</div>' if b.get("fonte") else ''}
    </div>""")
            elif tipo == "foto_secundaria":
                # Foto secundária — placeholder por ora
                pass  # Sem foto real por enquanto
        return "\n".join(out)


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
