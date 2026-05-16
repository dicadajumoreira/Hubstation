"""
S14B — Convite para a comunidade de WhatsApp do condomínio.

Página renderizada quando o cadastro do condomínio tem o link da
comunidade salvo (campo `comunidade_url`). Aparece ao final da revista,
logo antes da contracapa. Convida os moradores a entrar na comunidade
oficial do prédio (link + QR code, quando houver).

Inputs:
- condominio (str)
- comunidade_url (str) — obrigatório (composer só inclui a seção se houver)
- qrcode_url (str opcional) — URL pública da imagem do QR code
"""

from __future__ import annotations

from html import escape as _esc

from .base import A4, MOBILE, Section


class CommunityInvite(Section):
    """Convite para a comunidade do condomínio (S14B)."""

    type = "community_invite"
    label = "Comunidade do Condomínio"

    def validate(self, inputs: dict) -> list[str]:
        return []  # composer condiciona a inclusão; sem URL não entra

    def paginate(self, inputs: dict) -> int:
        return 1 if (inputs.get("comunidade_url") or "").strip() else 0

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return self._render(inputs, theme, scale="a4", dims=A4)

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return self._render(inputs, theme, scale="mobile", dims=MOBILE)

    def _render(self, inputs: dict, theme, *, scale: str, dims) -> list[str]:
        url = (inputs.get("comunidade_url") or "").strip()
        if not url:
            return []
        condo = (inputs.get("condominio") or "").strip()
        qr = (inputs.get("qrcode_url") or "").strip()

        if scale == "a4":
            pad = "72px 64px"
            kicker_size = 12
            titulo_size = 40
            corpo_size = 14
            qr_box = 280
            link_size = 13
        else:
            pad = "48px 40px"
            kicker_size = 11
            titulo_size = 30
            corpo_size = 12.5
            qr_box = 230
            link_size = 12

        nome_alvo = f"do {condo}" if condo else "do condomínio"

        qr_html = (
            f'<div class="ci__qr"><img src="{_esc(qr)}" alt="QR code da comunidade" /></div>'
            if qr
            else ""
        )

        return [f"""
<section class="page community-invite-page">
  <div class="ci__content">
    <header class="ci__header">
      <div class="ci__kicker">COMUNIDADE DO CONDOMÍNIO</div>
      <h1 class="ci__titulo">Entre na comunidade de WhatsApp {_esc(nome_alvo)}.</h1>
    </header>
    <p class="ci__corpo">
      É o canal oficial do condomínio: avisos da gestão, novidades,
      manutenções e o dia a dia do prédio em primeira mão. Aponte a câmera
      do celular para o QR code ou acesse pelo link abaixo.
    </p>
    {qr_html}
    <div class="ci__link-wrap">
      <div class="ci__link-label">LINK DA COMUNIDADE</div>
      <div class="ci__link">{_esc(url)}</div>
    </div>
  </div>
</section>

<style>
  .community-invite-page {{
    background: var(--white);
    color: var(--onix);
    padding: {pad};
  }}
  .ci__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 22px;
  }}
  .ci__header {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }}
  .ci__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {kicker_size}px;
    font-weight: 700;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}
  .ci__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: {titulo_size}px;
    font-weight: 400;
    line-height: 1.05;
    letter-spacing: -0.02em;
    color: var(--onix);
    margin: 0;
    max-width: 22ch;
  }}
  .ci__corpo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {corpo_size}px;
    line-height: 1.6;
    color: var(--onix);
    max-width: 52ch;
    margin: 0;
  }}
  .ci__qr {{
    width: {qr_box}px;
    height: {qr_box}px;
    background: var(--white);
    border-radius: 16px;
    border: 3px solid var(--mint);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
  }}
  .ci__qr img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }}
  .ci__link-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }}
  .ci__link-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}
  .ci__link {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: {link_size}px;
    font-weight: 700;
    color: var(--white);
    background: var(--onix);
    padding: 10px 22px;
    border-radius: 999px;
    word-break: break-all;
    max-width: 80%;
  }}
</style>
"""]
