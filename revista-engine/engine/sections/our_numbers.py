"""
S11 — Nossos Números.

Fechamento financeiro do mês: KPIs + gráficos (donut de despesas, bar
chart de histórico, sparkline de inadimplência) + tabela de despesas +
nota de transparência.

Dados são EXATOS — nunca inventar (Doc 01 §3 S11).

Inputs:
- mes_referencia (str) — ex: "FEVEREIRO 2026"
- kpis (dict): receita_brl, despesas_brl, fundo_reserva_brl, inadimplencia_pct
- principais_despesas (list[dict]) — categorias com valor_brl, observacao opc.
- despesa_extra (dict opcional) — categoria fora-da-curva com descricao
- historico (list[dict] opcional) — últimos 5-6 meses para gráficos:
    {mes: str, receita_brl, despesas_brl, inadimplencia_pct}
- nota_transparencia (str) — texto no rodapé
"""

from __future__ import annotations

import unicodedata

import math

from .base import A4, Section


# Texto padrão se nada for passado (Doc 01 §3 S11 menciona "default fixo").
_NOTA_DEFAULT = (
    "Os valores apresentados refletem o balancete oficial fechado pela "
    "administradora. A prestação de contas completa está disponível na "
    "área restrita dos moradores, com extratos, comprovantes e relatórios "
    "auditáveis. Em caso de dúvida, procure a administração."
)


def _fmt_brl(v: float) -> str:
    """Formata valor em R$ com ponto de milhar e vírgula decimal (pt-BR)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "R$ —"
    sinal = "-" if v < 0 else ""
    v = abs(v)
    inteiro = int(v)
    centavos = round((v - inteiro) * 100)
    s = f"{inteiro:,}".replace(",", ".")
    return f"{sinal}R$ {s},{centavos:02d}"


def _fmt_pct(v: float) -> str:
    try:
        return f"{float(v):.1f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


class OurNumbers(Section):
    """Nossos Números (S11)."""

    type = "our_numbers"
    label = "Nossos Números"

    # =========================================================================
    # Contrato Section
    # =========================================================================

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        if not inputs.get("mes_referencia"):
            errors.append("Nossos Números: 'mes_referencia' é obrigatório (ex: 'FEVEREIRO 2026')")

        kpis = inputs.get("kpis") or {}
        if not isinstance(kpis, dict):
            errors.append("Nossos Números: 'kpis' deve ser um dicionário")
        else:
            # Aceita os 4 campos novos (preferidos) OU os 4 antigos (compat).
            novos = {"saldo_anterior_brl", "credito_mes_brl", "debito_mes_brl", "saldo_atual_brl"}
            antigos = {"receita_brl", "despesas_brl", "fundo_reserva_brl", "inadimplencia_pct"}
            tem_novos = any(k in kpis for k in novos)
            tem_antigos = any(k in kpis for k in antigos)
            if not tem_novos and not tem_antigos:
                errors.append("Nossos Números: kpis precisa ter ao menos um dos 4 campos novos (saldo_anterior_brl, credito_mes_brl, debito_mes_brl, saldo_atual_brl)")

        despesas = inputs.get("principais_despesas") or []
        if not isinstance(despesas, list):
            errors.append("Nossos Números: 'principais_despesas' deve ser lista")
        else:
            for i, d in enumerate(despesas):
                if not isinstance(d, dict) or "categoria" not in d or "valor_brl" not in d:
                    errors.append(f"Nossos Números: despesa[{i}] precisa de 'categoria' e 'valor_brl'")

        return errors

    def paginate(self, inputs: dict) -> int:
        return 1  # por enquanto — se a tabela ficar grande migramos pra 2

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        # Mobile pausado — devolve A4 mesmo (a engine de orquestração pode ignorar)
        return [self._render(inputs, theme)]

    # =========================================================================
    # Render (A4)
    # =========================================================================

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        kpis = inputs.get("kpis") or {}
        despesas = list(inputs.get("principais_despesas") or [])
        resumo_contas = list(inputs.get("resumo_contas") or [])
        previsto_realizado = list(inputs.get("previsto_realizado") or [])
        nota = (inputs.get("nota_transparencia") or _NOTA_DEFAULT).strip()
        dashboard_url = (inputs.get("dashboard_url") or "").strip()

        max_despesa = max(
            (float(d.get("valor_brl", 0)) for d in despesas), default=1.0
        ) or 1.0

        kpi_cards = self._render_kpi_cards(kpis, theme)
        donut_svg = _render_donut(despesas)
        resumo_contas_html = self._render_resumo_contas(resumo_contas, theme)
        previsto_html = self._render_previsto_realizado(previsto_realizado, theme)

        # Bloco principal:
        #  - Coluna ESQUERDA (40%): donut GRANDE + legenda — destaque visual
        #  - Coluna DIREITA  (60%): Resumo das contas (topo) + Previsto×Realizado (baixo)
        donut_block = ""
        if despesas:
            donut_block = f"""
      <div class="num-block num-block--donut">
        <h2 class="num-block__titulo">Despesas por categoria</h2>
        <div class="num-block__donut-wrap">
          {donut_svg}
        </div>
        {_render_donut_legend(despesas)}
      </div>"""

        right_blocks = []
        if resumo_contas:
            right_blocks.append(f"""
      <div class="num-block">
        <h2 class="num-block__titulo">Resumo das contas</h2>
        {resumo_contas_html}
      </div>""")
        if previsto_realizado:
            right_blocks.append(f"""
      <div class="num-block">
        <h2 class="num-block__titulo">Previsto × Realizado</h2>
        {previsto_html}
      </div>""")

        bloco_principal = ""
        if donut_block or right_blocks:
            right_html = "".join(right_blocks)
            # Se só tem donut: 1 coluna full-width.
            # Se só tem direita: 1 coluna full-width.
            # Caso normal: 2 colunas (donut esquerda, blocos direita).
            if donut_block and right_blocks:
                bloco_principal = f"""
    <div class="numbers__main numbers__main--split">
      {donut_block}
      <div class="numbers__col-right">
        {right_html}
      </div>
    </div>"""
            elif donut_block:
                bloco_principal = f"""
    <div class="numbers__main numbers__main--full">
      {donut_block}
    </div>"""
            else:
                bloco_principal = f"""
    <div class="numbers__main numbers__main--full">
      <div class="numbers__col-right">{right_html}</div>
    </div>"""

        return f"""
<section class="page numbers-page">
  <div class="numbers__content">
    <header class="numbers__header">
      <div class="numbers__kicker">NOSSOS NÚMEROS · {_escape(mes)}</div>
      <h1 class="numbers__titulo">Fechamento financeiro</h1>
    </header>

    <div class="numbers__kpis">
      {kpi_cards}
    </div>

    {bloco_principal}

    <footer class="numbers__nota">
      <span class="numbers__nota-label">Transparência</span>
      <span class="numbers__nota-text">{_escape(nota)}</span>
    </footer>
  </div>
</section>

<style>
  .numbers-page {{
    background: var(--white);
    color: var(--onix);
    padding: 40px 44px 36px;
  }}

  .numbers__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }}

  .numbers__header {{
    margin-bottom: 0;
    border-bottom: 2px solid var(--mint);
    padding-bottom: 14px;
  }}

  .numbers__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 8px;
  }}

  .numbers__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 38px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
  }}

  .numbers__lede {{
    display: none;
  }}

  /* KPI cards: 4 colunas, mais respiráveis */
  .numbers__kpis {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }}

  .kpi-card {{
    background: var(--white);
    border: 1px solid var(--gray-20);
    border-radius: 8px;
    padding: 18px 18px 16px;
    border-top: 3px solid var(--mint);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}

  .kpi-card--credito {{ border-top-color: #2A8A6F; }}
  .kpi-card--debito {{ border-top-color: #C46A47; }}
  .kpi-card--saldo {{ border-top-color: var(--onix); background: var(--onix); }}
  .kpi-card--saldo .kpi-card__label {{ color: var(--mint); }}
  .kpi-card--saldo .kpi-card__value {{ color: var(--white); }}

  .kpi-card__label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8.5px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--mint-80);
  }}

  .kpi-card__value {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 20px;
    font-weight: 400;
    letter-spacing: -0.015em;
    color: var(--onix);
    line-height: 1.05;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    margin-top: 4px;
  }}

  /* Bloco principal: 2 colunas — donut grande à esquerda, tabelas à direita */
  .numbers__main {{
    flex: 1;
    min-height: 0;
    display: grid;
    gap: 16px;
    align-items: stretch;
  }}
  .numbers__main--full {{ grid-template-columns: 1fr; }}
  .numbers__main--split {{ grid-template-columns: 1.1fr 1.4fr; }}

  .numbers__col-right {{
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-height: 0;
  }}
  .numbers__col-right .num-block {{ flex: 1; min-height: 0; }}

  .num-block {{
    background: var(--gray-5);
    border-radius: 8px;
    padding: 18px 20px 16px;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }}

  .num-block--donut {{
    align-items: stretch;
    background: var(--white);
    border: 1px solid var(--gray-20);
    padding: 20px 22px 18px;
  }}

  .num-block__donut-wrap {{
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 8px 0 14px;
  }}

  .num-block__titulo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 12px;
    text-align: left;
  }}

  .donut-chart {{
    width: 220px; height: 220px;
  }}

  .donut-chart__total-label {{
    font-size: 3px;
  }}

  .donut-chart__total {{
    font-size: 6.5px;
  }}

  .numbers__empty {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    color: var(--onix);
    opacity: 0.5;
    margin: 0;
  }}

  /* Resumo das contas */
  .resumo-contas {{
    width: 100%;
    border-collapse: collapse;
  }}

  .resumo-contas tr {{
    border-bottom: 1px solid var(--gray-20);
  }}

  .resumo-contas tr:last-child {{ border-bottom: none; }}

  .resumo-contas td {{
    padding: 6px 0;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
  }}

  .resumo-contas__nome {{
    font-size: 10px;
    font-weight: 500;
    color: var(--onix);
  }}

  .resumo-contas__valor {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 11.5px;
    font-weight: 400;
    color: var(--onix);
    text-align: right;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.005em;
  }}

  /* Previsto x Realizado — colunas compactas */
  .prev-real {{
    width: 100%;
    border-collapse: collapse;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
  }}

  .prev-real .pr__th {{
    font-size: 7px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--mint-80);
    padding: 3px 0 6px;
    text-align: right;
  }}

  .prev-real tbody tr {{
    border-top: 1px solid var(--gray-20);
  }}

  .prev-real td {{
    padding: 5px 0;
    font-size: 9.5px;
  }}

  .prev-real .pr__cat {{
    color: var(--onix);
    font-weight: 500;
    max-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}

  .prev-real .pr__val {{
    font-variant-numeric: tabular-nums;
    text-align: right;
    color: var(--onix);
    padding-left: 6px;
  }}

  .prev-real .pr__diff {{
    font-variant-numeric: tabular-nums;
    text-align: right;
    font-weight: 700;
    padding-left: 6px;
    width: 40px;
  }}

  .pr-status--ok {{ color: #2A8A6F; }}
  .pr-status--over {{ color: #C46A47; }}

  .donut-chart {{
    width: 140px; height: 140px;
    margin: 4px 0 14px;
  }}

  .donut-chart__total-label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 3.4px;
    font-weight: 600;
    letter-spacing: 0.2em;
    fill: var(--mint-80);
  }}

  .donut-chart__total {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 7.5px;
    fill: var(--onix);
  }}

  .donut-legend {{
    list-style: none;
    margin: 0; padding: 0;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 6px;
    text-align: left;
  }}

  .donut-legend__item {{
    display: grid;
    grid-template-columns: 10px 1fr auto;
    align-items: center;
    gap: 10px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    color: var(--onix);
    padding: 5px 0;
    border-bottom: 1px solid var(--gray-20);
  }}

  .donut-legend__item:last-child {{ border-bottom: none; }}

  .donut-legend__dot {{
    width: 10px; height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
  }}

  .donut-legend__cat {{
    color: var(--onix);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}

  .donut-legend__pct {{
    font-weight: 700;
    color: var(--onix);
    font-variant-numeric: tabular-nums;
    font-size: 11px;
  }}

  /* Sparkline na KPI da inadimplência */
  .sparkline {{
    width: 100%;
    height: 22px;
    margin-top: 6px;
    opacity: 0.65;
  }}

  .chart-empty {{
    font-size: 11px;
    color: var(--onix);
    opacity: 0.5;
    padding: 24px 0;
    text-align: center;
  }}

  /* Despesas table — sem card, integrada na coluna da direita */
  .numbers__despesas {{
    display: flex;
    flex-direction: column;
    min-height: 0;
  }}

  .numbers__sub {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 18px;
  }}

  .despesa-row {{
    display: grid;
    grid-template-columns: 1fr 110px;
    align-items: center;
    column-gap: 14px;
    padding: 10px 0;
    border-bottom: 1px solid var(--gray-20);
  }}

  .despesa-row:last-child {{ border-bottom: none; }}

  .despesa-row__cat {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: var(--onix);
  }}

  .despesa-row__val {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 15px;
    font-weight: 400;
    color: var(--onix);
    text-align: right;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.01em;
  }}

  .despesa-row__bar-wrap {{
    grid-column: 1 / -1;
    margin-top: 6px;
    height: 4px;
    background: var(--gray-20);
    border-radius: 2px;
    overflow: hidden;
  }}

  .despesa-row__bar {{
    height: 100%;
    background: var(--mint);
    border-radius: 2px;
  }}

  .despesa-row__obs {{
    grid-column: 1 / -1;
    margin-top: 4px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    color: var(--onix);
    opacity: 0.55;
    font-style: italic;
  }}

  /* Nota de transparência */
  .numbers__nota {{
    border-top: 1px solid var(--gray-20);
    padding-top: 12px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    flex-wrap: wrap;
  }}

  .numbers__nota-label {{
    flex: 0 0 100px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    padding-top: 2px;
  }}

  .numbers__nota-text {{
    flex: 1;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    line-height: 1.45;
    color: var(--onix);
    opacity: 0.7;
  }}
</style>
"""

    def _render_kpi_cards(self, kpis: dict, theme) -> str:
        # Novos campos preferidos; cai pros antigos por compat (revistas antigas).
        saldo_ant = kpis.get("saldo_anterior_brl", kpis.get("fundo_reserva_brl", 0))
        credito = kpis.get("credito_mes_brl", kpis.get("receita_brl", 0))
        debito = kpis.get("debito_mes_brl", kpis.get("despesas_brl", 0))
        saldo_atual = kpis.get(
            "saldo_atual_brl",
            float(saldo_ant or 0) + float(credito or 0) - float(debito or 0),
        )

        return f"""
      <div class="kpi-card">
        <div class="kpi-card__label">Saldo anterior</div>
        <div class="kpi-card__value">{_fmt_brl(saldo_ant)}</div>
      </div>
      <div class="kpi-card kpi-card--credito">
        <div class="kpi-card__label">Crédito do mês</div>
        <div class="kpi-card__value">{_fmt_brl(credito)}</div>
      </div>
      <div class="kpi-card kpi-card--debito">
        <div class="kpi-card__label">Débito do mês</div>
        <div class="kpi-card__value">{_fmt_brl(debito)}</div>
      </div>
      <div class="kpi-card kpi-card--saldo">
        <div class="kpi-card__label">Saldo atual</div>
        <div class="kpi-card__value">{_fmt_brl(saldo_atual)}</div>
      </div>"""

    def _render_resumo_contas(self, contas: list, theme) -> str:
        if not contas:
            return '<p class="numbers__empty">Sem dados de contas.</p>'
        rows = []
        for c in contas:
            nome = _escape(str(c.get("conta", "") or c.get("nome", "")))
            saldo = _fmt_brl(c.get("saldo_brl", 0) or 0)
            rows.append(f"""
        <tr>
          <td class="resumo-contas__nome">{nome}</td>
          <td class="resumo-contas__valor">{saldo}</td>
        </tr>""")
        return f"""
      <table class="resumo-contas">
        <tbody>{''.join(rows)}</tbody>
      </table>"""

    def _render_previsto_realizado(self, items: list, theme) -> str:
        if not items:
            return '<p class="numbers__empty">Sem dados de orçamento.</p>'
        rows = []
        for it in items:
            cat = _escape(str(it.get("categoria", "")))
            prev = float(it.get("previsto_brl", 0) or 0)
            real = float(it.get("realizado_brl", 0) or 0)
            diff_pct = ((real - prev) / prev * 100) if prev else 0.0
            # Status: verde se gastou menos que previsto, sand se gastou mais
            status_cls = "pr-status--ok" if real <= prev else "pr-status--over"
            sinal = "+" if diff_pct >= 0 else ""
            diff_str = f"{sinal}{diff_pct:.0f}%" if prev else "—"
            rows.append(f"""
        <tr>
          <td class="pr__cat">{cat}</td>
          <td class="pr__val">{_fmt_brl(prev)}</td>
          <td class="pr__val">{_fmt_brl(real)}</td>
          <td class="pr__diff {status_cls}">{diff_str}</td>
        </tr>""")
        return f"""
      <table class="prev-real">
        <thead>
          <tr>
            <th></th>
            <th class="pr__th">Previsto</th>
            <th class="pr__th">Realizado</th>
            <th class="pr__th">Δ</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>"""

    def _render_despesas(self, despesas: list, max_v: float, theme) -> str:
        if not despesas:
            return '<div class="despesa-row"><span class="despesa-row__cat">—</span></div>'

        # Ordena do maior pro menor — leitura mais natural na revista
        despesas_ord = sorted(
            despesas,
            key=lambda d: float(d.get("valor_brl", 0) or 0),
            reverse=True,
        )
        rows = []
        for d in despesas_ord:
            cat = _escape(str(d.get("categoria", "")))
            val = float(d.get("valor_brl", 0) or 0)
            obs = _escape(str(d.get("observacao", "")))
            pct = max(0, min(100, (val / max_v) * 100)) if max_v else 0
            obs_html = f'<div class="despesa-row__obs">{obs}</div>' if obs else ""
            rows.append(f"""
      <div class="despesa-row">
        <div class="despesa-row__cat">{cat}</div>
        <div class="despesa-row__val">{_fmt_brl(val)}</div>
        <div class="despesa-row__bar-wrap">
          <div class="despesa-row__bar" style="width: {pct:.1f}%;"></div>
        </div>
        {obs_html}
      </div>""")
        return "\n".join(rows)


def _escape(s: str) -> str:
    return (
        unicodedata.normalize("NFC", s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_attr(s: str) -> str:
    return _escape(s).replace('"', "&quot;").replace("'", "&#39;")


# =============================================================================
# Helpers de gráficos SVG (sem dependências externas)
# =============================================================================

# Paleta cíclica para slices do donut. Ordem escolhida para maximizar
# contraste entre slices adjacentes (cyan→tan→roxo→teal→beige→dark).
_CHART_PALETTE = [
    "#84C7D3",   # mint
    "#D4AE94",   # sand-80
    "#B8C0FF",   # lavender
    "#76B1BC",   # mint-80
    "#DABDA9",   # sand
    "#1A1C29",   # onix
    "#EFCAAF",   # sand-90
    "#E0E0E2",   # gray-20
]


def _render_donut(despesas: list[dict]) -> str:
    """SVG donut chart das despesas. Slices proporcionais ao valor_brl."""
    if not despesas:
        return ""

    total = sum(float(d.get("valor_brl", 0) or 0) for d in despesas)
    if total <= 0:
        return ""

    # Geometria: viewBox 100x100, anel entre r=30 e r=42
    cx, cy = 50, 50
    r_outer, r_inner = 42, 30
    # Stroke width = r_outer - r_inner = 12, mas vamos desenhar como path
    # com fatias precisas usando arcos.

    slices = []
    angle = -math.pi / 2  # começa no topo (12h)
    for i, d in enumerate(despesas):
        valor = float(d.get("valor_brl", 0) or 0)
        if valor <= 0:
            continue
        frac = valor / total
        end = angle + frac * 2 * math.pi
        large_arc = 1 if frac > 0.5 else 0
        x1, y1 = cx + r_outer * math.cos(angle), cy + r_outer * math.sin(angle)
        x2, y2 = cx + r_outer * math.cos(end), cy + r_outer * math.sin(end)
        x3, y3 = cx + r_inner * math.cos(end), cy + r_inner * math.sin(end)
        x4, y4 = cx + r_inner * math.cos(angle), cy + r_inner * math.sin(angle)
        path = (
            f"M {x1:.3f} {y1:.3f} "
            f"A {r_outer} {r_outer} 0 {large_arc} 1 {x2:.3f} {y2:.3f} "
            f"L {x3:.3f} {y3:.3f} "
            f"A {r_inner} {r_inner} 0 {large_arc} 0 {x4:.3f} {y4:.3f} Z"
        )
        color = _CHART_PALETTE[i % len(_CHART_PALETTE)]
        slices.append(f'<path d="{path}" fill="{color}" />')
        angle = end

    total_fmt = _fmt_brl(total).replace("R$ ", "")
    return f"""
<svg viewBox="0 0 100 100" class="donut-chart" preserveAspectRatio="xMidYMid meet">
  {''.join(slices)}
  <text x="50" y="48" text-anchor="middle" font-size="4" font-weight="600"
        letter-spacing="0.18em" fill="#76B1BC"
        font-family="sans-serif">TOTAL</text>
  <text x="50" y="58" text-anchor="middle" font-size="7"
        fill="#1A1C29" font-family="serif">R$ {total_fmt}</text>
</svg>
"""


def _render_donut_legend(despesas: list[dict]) -> str:
    """Lista de legenda colorida ao lado do donut."""
    if not despesas:
        return ""
    total = sum(float(d.get("valor_brl", 0) or 0) for d in despesas) or 1
    items = []
    for i, d in enumerate(despesas):
        valor = float(d.get("valor_brl", 0) or 0)
        pct = (valor / total) * 100
        cat = _escape(str(d.get("categoria", "")))
        color = _CHART_PALETTE[i % len(_CHART_PALETTE)]
        items.append(f"""
        <li class="donut-legend__item">
          <span class="donut-legend__dot" style="background:{color}"></span>
          <span class="donut-legend__cat">{cat}</span>
          <span class="donut-legend__pct">{pct:.1f}%</span>
        </li>""")
    return f'<ul class="donut-legend">{"".join(items)}</ul>'


def _render_sparkline(series: list[float], color: str = "currentColor") -> str:
    """Mini sparkline SVG pra mostrar tendência (ex: inadimplência últimos meses)."""
    if not series or len(series) < 2:
        return ""
    W, H = 120, 24
    pad = 2
    mn, mx = min(series), max(series)
    rng = (mx - mn) or 1
    xs = [pad + i * (W - 2 * pad) / (len(series) - 1) for i in range(len(series))]
    ys = [pad + (1 - (v - mn) / rng) * (H - 2 * pad) for v in series]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    last_x, last_y = xs[-1], ys[-1]
    return f"""
<svg viewBox="0 0 {W} {H}" class="sparkline" preserveAspectRatio="none">
  <polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2" fill="{color}" />
</svg>
"""
