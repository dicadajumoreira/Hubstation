"""
S14C — Equipe de Atendimento.

Pagina que apresenta a equipe de atendimento (compartilhada entre todos
os condominios) na revista mensal. Renderizada logo depois do convite
da comunidade (S14B), quando o condominio tem comunidade cadastrada.

Inputs:
- condominio (str)
- membros (list[dict]): [{nome, cargo, foto_url}]
"""

from __future__ import annotations

from html import escape as _esc

from .base import A4, MOBILE, Section


class TeamSupport(Section):
    """Equipe de Atendimento (S14C)."""

    type = "team_support"
    label = "Equipe de Atendimento"

    def validate(self, inputs: dict) -> list[str]:
        return []  # composer condiciona inclusao

    def paginate(self, inputs: dict) -> int:
        membros = list(inputs.get("membros") or [])
        return 1 if membros else 0

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return self._render(inputs, theme, scale="a4", dims=A4)

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return self._render(inputs, theme, scale="mobile", dims=MOBILE)

    def _render(self, inputs: dict, theme, *, scale: str, dims) -> list[str]:
        membros = list(inputs.get("membros") or [])
        if not membros:
            return []
        condo = (inputs.get("condominio") or "").strip()

        if scale == "a4":
            pad = "60px 64px"
            kicker_size = 12
            titulo_size = 40
            corpo_size = 14
            avatar_size = 130
            nome_size = 14
            cargo_size = 11
            grid_gap = 24
        else:
            pad = "44px 36px"
            kicker_size = 11
            titulo_size = 30
            corpo_size = 12.5
            avatar_size = 110
            nome_size = 13
            cargo_size = 10
            grid_gap = 18

        cards_html = "\n".join(
            f"""
        <div class="ts-card">
          {f'<img class="ts-card__avatar" src="{_esc(m.get("foto_url",""))}" alt="{_esc(m.get("nome",""))}" />' if m.get("foto_url") else '<div class="ts-card__avatar ts-card__avatar--placeholder"></div>'}
          <div class="ts-card__nome">{_esc(m.get("nome", ""))}</div>
          <div class="ts-card__cargo">{_esc(m.get("cargo", ""))}</div>
        </div>"""
            for m in membros
        )

        intro = (
            f"Estes sao os profissionais que cuidam do atendimento do "
            f"{_esc(condo)} no dia a dia. Quando precisar de ajuda, fale com a equipe."
            if condo
            else "Estes sao os profissionais que cuidam do atendimento do condominio no dia a dia."
        )

        return [f"""
<section class="page team-support-page">
  <div class="ts__content">
    <header class="ts__header">
      <div class="ts__kicker">EQUIPE DE ATENDIMENTO</div>
      <h1 class="ts__titulo">Quem cuida do seu condomínio</h1>
      <p class="ts__intro">{intro}</p>
    </header>
    <div class="ts__grid">
      {cards_html}
    </div>
  </div>
</section>

<style>
  .team-support-page {{
    background: var(--white);
    color: var(--onix);
    padding: {pad};
  }}
  .ts__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }}
  .ts__header {{
    border-bottom: 2px solid var(--mint);
    padding-bottom: 14px;
  }}
  .ts__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', sans-serif;
    font-size: {kicker_size}px;
    font-weight: 700;
    letter-spacing: 0.26em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 8px;
  }}
  .ts__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: {titulo_size}px;
    font-weight: 400;
    line-height: 1.05;
    letter-spacing: -0.02em;
    margin: 0;
  }}
  .ts__intro {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', sans-serif;
    font-size: {corpo_size}px;
    line-height: 1.55;
    color: var(--onix);
    margin: 10px 0 0;
    max-width: 60ch;
  }}
  .ts__grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax({avatar_size + 30}px, 1fr));
    gap: {grid_gap}px;
    align-items: start;
  }}
  .ts-card {{
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }}
  .ts-card__avatar {{
    width: {avatar_size}px;
    height: {avatar_size}px;
    border-radius: 50%;
    object-fit: cover;
    background: var(--gray-10);
    margin-bottom: 10px;
    border: 3px solid var(--mint);
  }}
  .ts-card__avatar--placeholder {{
    background: var(--gray-20);
  }}
  .ts-card__nome {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', sans-serif;
    font-size: {nome_size}px;
    font-weight: 700;
    color: var(--onix);
    line-height: 1.2;
  }}
  .ts-card__cargo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', sans-serif;
    font-size: {cargo_size}px;
    font-weight: 500;
    color: var(--mint-80);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 2px;
    line-height: 1.2;
  }}
</style>
"""]
