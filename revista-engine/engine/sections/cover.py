"""
S01 — Capa.

Primeira página da revista. Foto de fundo ocupa 100%, gradiente escuro
no topo e fundo para garantir legibilidade da tipografia branca, manchete
em destaque, subtítulo, e chamadas das matérias dessa edição.

Inputs (Doc 01 §3 S01):
- tema_materia (str, opcional) — tema real da matéria de capa
- manchete (str, obrigatório) — texto principal grande
- subtitulo (str, opcional, máx 12 palavras) — apoio à manchete
- chamadas (list[str], 0–4) — chamadas curtas no rodapé
- foto_capa (str, opcional) — URL ou caminho da foto de fundo
- edicao_label (str, obrigatório) — "EDIÇÃO 05 · MAIO 2026 · GARDENS @sindicompanybr"

Quando foto_capa é vazia, usa um gradiente Mint→Onix como placeholder
(útil pra preview e pra fallback se a equipe esquecer de subir foto).
"""

from __future__ import annotations

import unicodedata

from .base import A4, MOBILE, Section


class Cover(Section):
    """Capa da revista (S01)."""

    type = "cover"
    label = "Capa"

    # =========================================================================
    # Contrato Section
    # =========================================================================

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        if not inputs.get("manchete"):
            errors.append("Capa: 'manchete' é obrigatória")
        if not inputs.get("edicao_label"):
            errors.append("Capa: 'edicao_label' é obrigatório (ex: 'EDIÇÃO 05 · MAIO 2026 · ...')")

        chamadas = inputs.get("chamadas")
        if chamadas is not None:
            if not isinstance(chamadas, list):
                errors.append("Capa: 'chamadas' deve ser uma lista de strings")
            elif len(chamadas) > 4:
                errors.append(f"Capa: máximo 4 chamadas, recebido {len(chamadas)}")

        subtitulo = inputs.get("subtitulo", "")
        if subtitulo and len(subtitulo.split()) > 14:
            errors.append("Capa: 'subtitulo' deveria ter até 12 palavras (recebido " +
                          f"{len(subtitulo.split())})")

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
        edicao = (inputs.get("edicao_label") or "").strip()
        manchete = (inputs.get("manchete") or "").strip()
        subtitulo = (inputs.get("subtitulo") or "").strip()
        chamadas = list(inputs.get("chamadas") or [])
        foto = (inputs.get("foto_capa") or "").strip()

        if scale == "a4":
            edicao_size = 10
            manchete_size = 64
            subtitulo_size = 17
            chamada_size = 13
            chamada_label_size = 9
            padding = 56
            logo_w = 397   # até metade da página A4 (794/2)
        else:  # mobile
            edicao_size = 11
            manchete_size = 52
            subtitulo_size = 17
            chamada_size = 14
            chamada_label_size = 10
            padding = 40
            logo_w = 270   # ~metade da página mobile (540/2)

        # Logo do condomínio (se cadastrado) substitui o Sindicompany.
        # A editora deve subir um logo que funcione em fundo escuro
        # (transparente ou com cores claras).
        logo_url = (inputs.get("logo_url") or "").strip()
        if logo_url:
            # Logo do condomínio: respeita até metade da página em largura
            # e limita altura pra não estourar layout em logos verticais.
            logo_svg = (
                f'<img src="{_escape(logo_url)}" alt="Logo" '
                f'style="max-width:100%;max-height:{int(logo_w * 0.95)}px;'
                f'width:auto;height:auto;object-fit:contain;" />'
            )
        else:
            logo_svg = theme.logo_svg("white")

        # Background: foto real OU gradiente placeholder (Mint -> Onix).
        # Aplicado direto na .cover-page (mais confiável em WeasyPrint do
        # que um div absoluto com `inset: 0`).
        if foto:
            page_bg = (
                f"background-image: url('{_escape_attr(foto)}');\n"
                f"    background-size: cover;\n"
                f"    background-position: center center;\n"
                f"    background-repeat: no-repeat;"
            )
        else:
            page_bg = (
                "background: linear-gradient(140deg, "
                "var(--mint) 0%, var(--mint-80) 38%, var(--onix) 100%);"
            )

        # Lista de chamadas
        chamadas_html = ""
        if chamadas:
            items = "\n".join(
                f'<li class="cover__chamada"><span class="cover__chamada-bullet">·</span>'
                f'{_escape(str(c))}</li>'
                for c in chamadas[:4]
            )
            chamadas_html = f"""
      <div class="cover__chamadas-block">
        <div class="cover__chamadas-label">Nesta edição</div>
        <ul class="cover__chamadas">{items}</ul>
      </div>"""

        subtitulo_html = (
            f'<p class="cover__subtitulo">{_escape(subtitulo)}</p>'
            if subtitulo else ""
        )

        return f"""
<section class="page cover-page" data-format="{scale}">
  <div class="cover__overlay"></div>
  <header class="cover__header">
    <div class="cover__logo">{logo_svg}</div>
    <div class="cover__edicao">{_escape(edicao)}</div>
  </header>
  <div class="cover__bottom">
    <div class="cover__main">
      <h1 class="cover__manchete">{_escape(manchete)}</h1>
      {subtitulo_html}
    </div>
    {chamadas_html}
  </div>
</section>

<style>
  .cover-page {{
    position: relative;
    overflow: hidden;
    color: var(--white);
    background-color: var(--onix);
    {page_bg}
  }}

  .cover__overlay {{
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(
      180deg,
      rgba(26, 28, 41, 0.55) 0%,
      rgba(26, 28, 41, 0.05) 22%,
      rgba(26, 28, 41, 0.05) 42%,
      rgba(26, 28, 41, 0.78) 76%,
      rgba(26, 28, 41, 0.96) 100%
    );
    z-index: 1;
  }}

  .cover__header {{
    position: absolute;
    top: {padding}px; left: {padding}px; right: {padding}px;
    z-index: 2;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
  }}

  .cover__bottom {{
    position: absolute;
    bottom: {padding}px; left: {padding}px; right: {padding}px;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }}

  .cover__logo {{
    width: {logo_w}px;
    /* O spec menciona mix-blend-mode: screen pra logo "emanando luz".
       Em PDF (WeasyPrint) blend-modes têm suporte limitado; usamos
       brightness pra dar um efeito similar e seguro. */
    filter: brightness(1.15) drop-shadow(0 2px 8px rgba(0,0,0,0.25));
  }}

  .cover__logo svg {{
    width: 100%;
    height: auto;
    display: block;
  }}

  .cover__edicao {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {edicao_size}px;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    text-align: right;
    line-height: 1.6;
    max-width: 240px;
    color: var(--white);
    opacity: 0.95;
  }}

  .cover__main {{
    max-width: 100%;
  }}

  .cover__manchete {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: {manchete_size}px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.022em;
    color: var(--white);
    max-width: 11ch;
    text-wrap: balance;
  }}

  .cover__subtitulo {{
    /* Subtítulo destacado com fundo: pílula sand sobre o hero da capa */
    display: inline-block;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {subtitulo_size}px;
    font-weight: 500;
    line-height: 1.4;
    letter-spacing: -0.005em;
    color: var(--onix);
    background: var(--sand);
    padding: 8px 14px;
    border-radius: 4px;
    margin-top: 18px;
    max-width: 38ch;
  }}

  .cover__chamadas-block {{
    border-top: 1px solid rgba(255, 255, 255, 0.22);
    padding-top: 16px;
  }}

  .cover__chamadas-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {chamada_label_size}px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--sand);
    margin-bottom: 10px;
  }}

  .cover__chamadas {{
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}

  .cover__chamada {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {chamada_size}px;
    font-weight: 400;
    line-height: 1.4;
    color: var(--white);
  }}

  .cover__chamada-bullet {{
    color: var(--sand);
    margin-right: 8px;
    font-weight: 700;
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
