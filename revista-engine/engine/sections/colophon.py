"""
S14 — Expediente.

1 página fixa. Créditos editoriais sempre presentes (Síndico, Equipe do
Condomínio, Equipe Sindicompany) + extras opcionais (Doc 01 §3 S14).

Inputs:
- mes_referencia (str)
- nome_condominio (str)
- numero_edicao (int) e ano_edicao (int)
- nome_sindico (str)  ← vem da Carta (S02)
- cargo_sindico (str opcional)
- equipe_condominio (list[str] opcional)
- equipe_sindicompany (list[str] opcional)
- creditos_extras (list[dict] opcional) — {titulo, nomes (list)}
- editor_responsavel (str opcional)
- contato (str opcional) — endereço/email para correções
"""

from __future__ import annotations

import unicodedata

from .base import Section


class Colophon(Section):
    """Expediente (S14)."""

    type = "colophon"
    label = "Expediente"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        if not inputs.get("nome_condominio"):
            errors.append("Expediente: 'nome_condominio' é obrigatório")
        if not inputs.get("nome_sindico"):
            errors.append("Expediente: 'nome_sindico' é obrigatório (mesma da Carta)")
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        condo = (inputs.get("nome_condominio") or "").strip()
        edicao = inputs.get("numero_edicao", 0)
        ano = inputs.get("ano_edicao", 0)
        sindico = (inputs.get("nome_sindico") or "").strip()
        cargo_sindico = (inputs.get("cargo_sindico") or "Síndico(a) Profissional").strip()
        by_logo_url = (inputs.get("by_logo_url") or "").strip()
        label_sindico = (inputs.get("label_sindico") or "Síndico").strip()
        equipe_condo = list(inputs.get("equipe_condominio") or [])
        equipe_sc = list(inputs.get("equipe_sindicompany") or [])
        equipe_sc_titulo = (inputs.get("equipe_sc_titulo") or "Equipe Sindicompany").strip()
        extras = list(inputs.get("creditos_extras") or [])
        editor = (inputs.get("editor_responsavel") or "").strip()
        contato = (inputs.get("contato") or "").strip()

        # Filtro de seguranca: nunca incluir "Diego Leite" em nenhuma lista
        # (equipe ou fontes), independente do que vier do composer/DB.
        def _sem_diego(lst):
            return [n for n in lst if "diego leite" not in str(n).lower()]
        equipe_condo = _sem_diego(equipe_condo)

        # Separa fontes (vão pro rodapé inline) dos demais blocos.
        fontes_lista: list[str] = []
        outros_extras: list[tuple[str, list[str]]] = []
        for c in extras:
            t = (c.get("titulo") or "").strip()
            ns = list(c.get("nomes") or [])
            if not (t and ns):
                continue
            if t.lower().startswith("fonte"):
                fontes_lista = _sem_diego([str(n) for n in ns])
            else:
                outros_extras.append((t, _sem_diego(ns)))

        # Equipe Sindicompany: usa default se vazio
        if not equipe_sc:
            equipe_sc = ["Direção editorial", "Pauta e Produção", "Diagramação e Arte"]

        # Equipe do condomínio: usa default genérico se vazio
        if not equipe_condo:
            equipe_condo = [f"Equipe administrativa · {condo}"]

        edicao_str = f"Edição {edicao:02d} · {ano}" if (edicao and ano) else ""
        sindico_value = f"{sindico} · {cargo_sindico}" if sindico else "—"

        # Renderiza blocos extras (não-fontes) na coluna esquerda
        extras_html = "\n".join(
            f"""
        <div class="exp-block">
          <div class="exp-block__titulo">{_escape(t)}</div>
          <ul class="exp-block__list">
            {''.join(f'<li>{_escape(str(n))}</li>' for n in ns)}
          </ul>
        </div>"""
            for t, ns in outros_extras
        )

        equipe_condo_html = "".join(
            f'<li>{_escape(str(n))}</li>' for n in equipe_condo
        )
        equipe_sc_html = "".join(
            f'<li>{_escape(str(n))}</li>' for n in equipe_sc
        )

        fontes_html = ""
        if fontes_lista:
            fontes_inline = " | ".join(_escape(str(n)) for n in fontes_lista)
            fontes_html = f"""
      <div class="exp-fontes">
        <div class="exp-block__titulo">Fontes de Pesquisa</div>
        <p class="exp-fontes__text">{fontes_inline}</p>
      </div>"""

        editor_html = (
            f'<div class="ficha-item"><span class="ficha-item__label">Editor</span>'
            f'<span class="ficha-item__value">{_escape(editor)}</span></div>'
            if editor else ""
        )

        return f"""
<section class="page colophon-page">
  <div class="exp">
    <header class="exp__header">
      <div class="exp__kicker">EXPEDIENTE · {_escape(mes)}</div>
      <h1 class="exp__titulo">Quem fez esta edição</h1>
    </header>

    <div class="exp__ficha">
      <div class="ficha-item">
        <span class="ficha-item__label">Publicação</span>
        <span class="ficha-item__value">Revista mensal de moradores</span>
      </div>
      <div class="ficha-item">
        <span class="ficha-item__label">Condomínio</span>
        <span class="ficha-item__value">{_escape(condo)}</span>
      </div>
      <div class="ficha-item">
        <span class="ficha-item__label">Edição</span>
        <span class="ficha-item__value">{_escape(edicao_str)}</span>
      </div>
      {editor_html}
    </div>

    <div class="exp__main">
      <div class="exp-col exp-col--esq">
        <div class="exp-block exp-block--hero">
          <div class="exp-block__titulo">{_escape(label_sindico)}</div>
          <div class="exp-block__sindico">{_escape(sindico_value)}</div>
        </div>
        <div class="exp-block">
          <div class="exp-block__titulo">{_escape(equipe_sc_titulo)}</div>
          <ul class="exp-block__list">{equipe_sc_html}</ul>
        </div>
      </div>
      <div class="exp-col exp-col--dir">
        <div class="exp-block">
          <div class="exp-block__titulo">Equipe do Condomínio</div>
          <ul class="exp-block__list">{equipe_condo_html}</ul>
        </div>
        {extras_html}
      </div>
    </div>

    {fontes_html}

    <footer class="exp__footer">
      {f'<img class="exp__brand-img" src="{_escape(by_logo_url)}" alt="by sindicompany" />' if by_logo_url else ''}
      <span class="exp__legal">
        Revista produzida por equipe editorial dedicada, sob curadoria
        da {_escape(label_sindico.lower())} responsável e da gestão do condomínio.
        {f'Correções e sugestões: {_escape(contato)}.' if contato else ''}
        Todos os direitos reservados.
      </span>
    </footer>
  </div>
</section>

<style>
  .colophon-page {{
    background: var(--white);
    color: var(--onix);
    padding: 36px 44px 28px;
  }}

  .exp {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}

  /* Header compacto com linha mint embaixo */
  .exp__header {{
    border-bottom: 2px solid var(--mint);
    padding-bottom: 10px;
  }}

  .exp__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.26em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 6px;
  }}

  .exp__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 30px;
    font-weight: 400;
    line-height: 1.0;
    letter-spacing: -0.022em;
    color: var(--onix);
    margin: 0;
  }}

  /* Ficha técnica: 4 colunas, fundo cinza claro */
  .exp__ficha {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px 18px;
    background: var(--gray-5);
    border-radius: 6px;
    padding: 12px 16px;
  }}

  .ficha-item {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .ficha-item__label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 7.5px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}

  .ficha-item__value {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 12px;
    color: var(--onix);
    line-height: 1.15;
  }}

  /* Bloco principal: 2 colunas */
  .exp__main {{
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 1fr 1.25fr;
    gap: 18px;
    align-content: start;
  }}

  .exp-col {{
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}

  /* Cada bloco de crédito */
  .exp-block {{
    border-top: 2px solid var(--mint);
    padding-top: 8px;
  }}
  .exp-col--esq .exp-block:nth-child(1) {{ border-top-color: #84C7D3; }} /* mint — síndico */
  .exp-col--esq .exp-block:nth-child(2) {{ border-top-color: #B8C0FF; }} /* lavender — sindicompany */
  .exp-col--dir .exp-block:nth-child(1) {{ border-top-color: #D4AE94; }} /* sand-80 — condomínio */
  .exp-col--dir .exp-block:nth-child(2) {{ border-top-color: #76B1BC; }} /* mint-80 — extras */

  .exp-block__titulo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8.5px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 8px;
  }}

  .exp-block__sindico {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 14px;
    line-height: 1.2;
    color: var(--onix);
  }}

  .exp-block__list {{
    list-style: none;
    margin: 0; padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10.5px;
    line-height: 1.35;
    color: var(--onix);
  }}

  /* Fontes de Pesquisa: linha cheia abaixo do bloco principal */
  .exp-fontes {{
    border-top: 2px solid #DABDA9; /* sand */
    padding-top: 8px;
  }}
  .exp-fontes__text {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9.5px;
    line-height: 1.6;
    color: var(--onix);
    margin: 0;
  }}

  /* Footer legal compacto */
  .exp__footer {{
    border-top: 1px solid var(--gray-20);
    padding-top: 10px;
    display: flex;
    gap: 14px;
    align-items: center;
  }}

  .exp__brand {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 11px;
    font-weight: 600;
    color: var(--onix);
    flex-shrink: 0;
  }}

  .exp__brand-img {{
    height: 28px;
    width: auto;
    flex-shrink: 0;
    object-fit: contain;
    display: block;
  }}

  .exp__legal {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8.5px;
    line-height: 1.45;
    color: var(--onix);
    opacity: 0.6;
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
