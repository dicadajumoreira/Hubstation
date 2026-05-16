"""
S02 — Carta do Síndico.

Página única, sempre 1 página. Voz do síndico do condomínio aos moradores.
Foto do síndico em destaque, texto longo (350-450 palavras), assinatura.

Inputs (Doc 01 §3 S02):
- genero ('masculino' | 'feminino') — define o título da seção
- nome_sindico (str) — quem assina
- cargo (str, default 'Síndico(a) Profissional')
- foto_sindico (str, opcional) — caminho/URL da foto
- object_position (str, default 'center 20%') — enquadramento da foto
- texto (str) — corpo (350-450 palavras, parágrafos separados por \\n\\n)
- mes_ano (str) — "ABRIL 2026" usado no kicker
- titulo (str) — subtítulo da carta, ex: "Abril azul, olhar aberto."

Regras (Doc 01):
- Título adapta ao gênero (Carta do/da Síndico/Síndica)
- Foto é a única imagem permitida
- Sem foto: usa placeholder em Sand
"""

from __future__ import annotations

import unicodedata

import re

from .base import A4, MOBILE, Section


def _saudacao(genero: str, n_pessoas: int = 1) -> str:
    """Decide o título da seção em função de gênero/quantidade."""
    g = (genero or "masculino").strip().lower()
    if g == "empresa":
        return "Carta da Sindicatura Profissional"
    if n_pessoas >= 2:
        return "Carta dos Síndicos" if g != "feminino" else "Carta das Síndicas"
    return "Carta da Síndica" if g == "feminino" else "Carta do Síndico"


class Letter(Section):
    """Carta do Síndico (S02)."""

    type = "letter"
    label = "Carta do Síndico"

    # =========================================================================
    # Contrato Section
    # =========================================================================

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        if not inputs.get("nome_sindico"):
            errors.append("Carta: 'nome_sindico' é obrigatório")
        if not inputs.get("texto"):
            errors.append("Carta: 'texto' é obrigatório")
        else:
            n_words = len(inputs["texto"].split())
            if n_words < 150:
                errors.append(
                    f"Carta: texto curto demais ({n_words} palavras; mínimo 150, "
                    "ideal 350-450)"
                )
        genero = inputs.get("genero", "masculino")
        if genero not in ("masculino", "feminino", "empresa"):
            errors.append(
                f"Carta: 'genero' deve ser 'masculino', 'feminino' ou 'empresa' "
                f"(recebido {genero!r})"
            )
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme, scale="a4")]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme, scale="mobile")]

    # =========================================================================
    # Render
    # =========================================================================

    def _render(self, inputs: dict, theme, *, scale: str) -> str:
        nome = (inputs.get("nome_sindico") or "").strip()
        genero = inputs.get("genero", "masculino").strip().lower()
        if genero == "empresa":
            _cargo_default = "Sindicatura Profissional"
        elif genero == "feminino":
            _cargo_default = "Síndica Profissional"
        else:
            _cargo_default = "Síndico Profissional"
        cargo = (inputs.get("cargo") or _cargo_default).strip()
        foto = (inputs.get("foto_sindico") or "").strip()
        object_position = (inputs.get("object_position") or "center 20%").strip()
        texto = (inputs.get("texto") or "").strip()
        mes_ano = (inputs.get("mes_ano") or "").strip()
        titulo = (inputs.get("titulo") or "").strip()

        kicker_label = _saudacao(genero, n_pessoas=1).upper()
        kicker = f"{kicker_label}" + (f" · {mes_ano}" if mes_ano else "")

        # Tamanhos por formato. layout_dir: row (foto ao lado) ou column (foto em cima).
        if scale == "a4":
            padding = 60
            kicker_size = 11
            titulo_size = 56
            corpo_size = 12
            corpo_leading = 1.5
            assinatura_nome_size = 16
            assinatura_cargo_size = 9
            foto_w = 220
            foto_h = 280
            layout_dir = "row"
        else:  # mobile — empilha foto em cima do texto pra texto longo caber
            padding = 32
            kicker_size = 11
            titulo_size = 36
            corpo_size = 11
            corpo_leading = 1.42
            assinatura_nome_size = 15
            assinatura_cargo_size = 9
            foto_w = 476   # full-width do mobile (540 - 2*32 padding)
            foto_h = 150   # bem mais raso pra liberar espaço pro texto
            layout_dir = "column"

        # Quebra parágrafos (separados por linha em branco)
        paragrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
        if not paragrafos:
            paragrafos = [texto] if texto else []
        paragrafos = [_strip_inline_citations(p) for p in paragrafos]
        paragrafos = [p for p in paragrafos if p]

        # Defesa de overflow: limita o texto total da carta a ~380 palavras
        # (cabe confortavelmente em A4 com o layout atual). Se vier maior,
        # corta no último parágrafo e adiciona reticências.
        max_palavras = 380 if scale == "a4" else 260
        total = 0
        paragrafos_clip: list[str] = []
        for p in paragrafos:
            palavras = p.split()
            restante = max_palavras - total
            if restante <= 0:
                break
            if len(palavras) > restante:
                p_cortado = " ".join(palavras[:restante]).rstrip(",.;:") + "…"
                paragrafos_clip.append(p_cortado)
                total += restante
                break
            paragrafos_clip.append(p)
            total += len(palavras)
        paragrafos = paragrafos_clip

        # Primeiro parágrafo recebe drop cap
        body_html_parts = []
        for i, p in enumerate(paragrafos):
            cls = "letter__p letter__p--first" if i == 0 else "letter__p"
            body_html_parts.append(f'<p class="{cls}">{_escape(p)}</p>')
        body_html = "\n".join(body_html_parts)

        # Foto: arquivo real OU placeholder
        if foto:
            foto_bg = (
                f"background-image: url('{_escape_attr(foto)}');\n"
                f"      background-size: cover;\n"
                f"      background-position: {object_position};\n"
                f"      background-repeat: no-repeat;"
            )
        else:
            # Placeholder Sand com gradiente sutil
            foto_bg = (
                "background: radial-gradient(ellipse at 50% 30%, "
                "var(--sand-90) 0%, var(--sand) 50%, var(--sand-80) 100%);"
            )

        titulo_html = (
            f'<h1 class="letter__titulo">{_escape(titulo)}</h1>'
            if titulo else ""
        )

        return f"""
<section class="page letter-page" data-format="{scale}">
  <div class="letter__content">
    <header class="letter__header">
      <div class="letter__kicker">{_escape(kicker)}</div>
      {titulo_html}
    </header>

    <div class="letter__layout">
      <aside class="letter__photo" style="{foto_bg}" aria-hidden="true"></aside>
      <div class="letter__body">{body_html}</div>
    </div>

    <footer class="letter__signature">
      <div class="letter__sig-name">{_escape(nome)}</div>
      <div class="letter__sig-cargo">{_escape(cargo)}</div>
    </footer>
  </div>
</section>

<style>
  .letter-page {{
    background: var(--white);
    color: var(--onix);
    padding: {padding}px;
  }}

  .letter__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;  /* defesa: corta se algum texto inesperado passar */
  }}

  .letter__header {{
    margin-bottom: 28px;
  }}

  .letter__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {kicker_size}px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 18px;
  }}

  .letter__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: {titulo_size}px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
    max-width: 18ch;
    text-wrap: balance;
  }}

  .letter__layout {{
    display: flex;
    flex-direction: {layout_dir};
    gap: 24px;
    flex: 1;
    min-height: 0;
  }}

  .letter__photo {{
    width: {foto_w}px;
    height: {foto_h}px;
    flex-shrink: 0;
    border-radius: 4px;
    /* background-image vem inline no <aside> pra não vazar entre cartas
       quando há mais de uma na mesma revista (síndico + gestor). */
  }}

  .letter__body {{
    flex: 1;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {corpo_size}px;
    font-weight: 400;
    line-height: {corpo_leading};
    color: var(--onix);
    text-align: justify;
    hyphens: auto;
  }}

  .letter__p {{
    margin-bottom: {corpo_size}px;
    text-indent: 0;
    /* Preserva quebras de linha dentro do paragrafo (digitadas pelo
       autor) — sem isso, single newlines somem na renderizacao. */
    white-space: pre-line;
  }}

  /* Primeiro parágrafo levemente maior pra destaque editorial */
  .letter__p--first {{
    font-size: {corpo_size + 1}px;
    color: var(--onix);
  }}

  .letter__signature {{
    margin-top: 24px;
    padding-top: 18px;
    border-top: 1px solid var(--gray-20);
    text-align: right;
  }}

  .letter__sig-name {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: {assinatura_nome_size}px;
    font-weight: 400;
    letter-spacing: -0.01em;
    color: var(--onix);
    line-height: 1.1;
  }}

  .letter__sig-cargo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {assinatura_cargo_size}px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-top: 4px;
  }}
</style>
"""


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
    # IMPORTANTE: usar [ \t]+ (nao \s+) pra nao colapsar newlines proximos
    # de pontuacao — quebras de linha dentro do paragrafo precisam ser
    # preservadas pra serem renderizadas via white-space: pre-line.
    out = re.sub(r"[ \t]+([.,;:!?])", r"\1", out)
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
