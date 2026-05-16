"""
S12 — Advertências e Multas.

Sempre 1 página fixa. Mostra dados AGREGADOS do mês (Doc 01 §3 S12 —
"nunca identificar moradores") + assuntos recorrentes + dicas "Como evitar"
baseadas nesses assuntos.

Inputs:
- total_advertencias (int)
- total_multas (int)
- valor_multas_brl (float)
- mes_referencia (str) — ex: "ABRIL 2026"
- assuntos_recorrentes (list[str]) — temas que mais geraram advertências
- dicas (list[dict]) — opcional, com {titulo, descricao}; auto se vazio
"""

from __future__ import annotations

import unicodedata

from .base import Section


def _fmt_brl(v: float) -> str:
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


# Lookup simples para auto-gerar dicas a partir de assuntos comuns.
# A equipe sempre pode passar dicas customizadas via input que sobrescrevem isso.
_DICAS_AUTO = [
    (("barulho", "som", "ruido", "ruído", "festa"),
     "Combine festas com antecedência",
     "Avise vizinhos diretamente impactados, respeite o silêncio após 22h em "
     "dias úteis e 23h nos fins de semana."),
    (("pet", "cachorro", "cao", "cão", "coleira", "animal"),
     "Coleira no hall e elevador",
     "Pets devem circular com coleira ou no colo em todas as áreas comuns. "
     "Recolha sempre os dejetos."),
    (("salao", "salão", "reserva", "festa"),
     "Reserve antes de usar áreas comuns",
     "Salão de festas, churrasqueira e quadra precisam de reserva pelo app "
     "ou portaria. Sem reserva, sem uso."),
    (("lixo", "reciclagem", "descarte"),
     "Descarte no horário certo",
     "Lixo orgânico vai para a lixeira nos horários definidos. Recicláveis "
     "limpos e secos, em sacos transparentes."),
    (("garagem", "vaga", "estaciona"),
     "Respeite vagas e fluxo",
     "Estacione apenas na vaga reservada. Evite bloquear vagas de visitantes "
     "ou vias de circulação."),
    (("elevador", "carga"),
     "Comunique mudanças e cargas",
     "Antes de transportar móveis ou objetos grandes, avise a portaria e "
     "use o elevador de serviço quando disponível."),
]


def _auto_dica(assunto: str) -> dict:
    """Retorna dica padrão baseada em palavras-chave do assunto."""
    a = assunto.lower()
    for kws, titulo, descricao in _DICAS_AUTO:
        if any(k in a for k in kws):
            return {"titulo": titulo, "descricao": descricao}
    return {
        "titulo": "Releia o regulamento interno",
        "descricao": "Se ficou em dúvida sobre o que é permitido, "
                     "consulte o regulamento ou fale com a administração.",
    }


class Warnings(Section):
    """Advertências e Multas (S12)."""

    type = "warnings"
    label = "Advertências e Multas"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        for key in ("total_advertencias", "total_multas", "valor_multas_brl"):
            if key not in inputs:
                errors.append(f"Advertências: '{key}' é obrigatório (use 0 se não houve)")
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        n_adv = int(inputs.get("total_advertencias", 0) or 0)
        n_mul = int(inputs.get("total_multas", 0) or 0)
        valor = float(inputs.get("valor_multas_brl", 0) or 0)
        assuntos = list(inputs.get("assuntos_recorrentes") or [])
        dicas = list(inputs.get("dicas") or [])
        if not dicas and assuntos:
            # Auto-gerar dicas a partir dos assuntos (deduplicar pelo título)
            seen = set()
            for a in assuntos:
                d = _auto_dica(a)
                if d["titulo"] not in seen:
                    seen.add(d["titulo"])
                    dicas.append(d)

        kicker = "ADVERTÊNCIAS E MULTAS" + (f" · {mes}" if mes else "")

        # KPI cards
        kpis_html = f"""
      <div class="kpi-card">
        <div class="kpi-card__label">Advertências</div>
        <div class="kpi-card__value">{n_adv}</div>
        <div class="kpi-card__hint">notificações formais</div>
      </div>
      <div class="kpi-card kpi-card--mul">
        <div class="kpi-card__label">Multas</div>
        <div class="kpi-card__value">{n_mul}</div>
        <div class="kpi-card__hint">após reincidência</div>
      </div>
      <div class="kpi-card kpi-card--val">
        <div class="kpi-card__label">Valor total</div>
        <div class="kpi-card__value">{_fmt_brl(valor)}</div>
        <div class="kpi-card__hint">somado das multas</div>
      </div>
"""

        assuntos_html = ""
        if assuntos:
            items = "\n".join(
                f'<li class="assunto-row"><span class="assunto-row__num">{i+1:02d}</span>'
                f'<span class="assunto-row__txt">{_escape(a)}</span></li>'
                for i, a in enumerate(assuntos)
            )
            assuntos_html = f"""
        <h2 class="warnings__sub">Assuntos recorrentes</h2>
        <ol class="assuntos-list">{items}</ol>
"""

        dicas_html = ""
        if dicas:
            items = "\n".join(
                f"""<div class="dica-card">
        <h3 class="dica-card__titulo">{_escape(d.get('titulo',''))}</h3>
        <p class="dica-card__desc">{_escape(d.get('descricao',''))}</p>
      </div>"""
                for d in dicas[:6]
            )
            dicas_html = f"""
        <h2 class="warnings__sub">Como evitar</h2>
        <div class="dicas-grid">{items}</div>
"""

        nota = (
            "Por respeito à privacidade, divulgamos apenas dados agregados. "
            "Notificações individuais seguem o canal direto da administração."
        )

        return f"""
<section class="page warnings-page">
  <div class="warnings__content">
    <header class="warnings__header">
      <div class="warnings__kicker">{_escape(kicker)}</div>
      <h1 class="warnings__titulo">Convivência em números</h1>
    </header>

    <div class="warnings__kpis">{kpis_html}</div>

    <div class="warnings__cols">
      <div class="warnings__col">
        {assuntos_html}
      </div>
      <div class="warnings__col">
        {dicas_html}
      </div>
    </div>

    <footer class="warnings__nota">
      <span class="warnings__nota-label">Privacidade</span>
      <span class="warnings__nota-text">{_escape(nota)}</span>
    </footer>
  </div>
</section>

<style>
  .warnings-page {{
    background: var(--white);
    color: var(--onix);
    padding: 56px;
  }}

  .warnings__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }}

  .warnings__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 14px;
  }}

  .warnings__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 48px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
  }}

  /* KPIs — 3 cards */
  .warnings__kpis {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }}

  .kpi-card {{
    background: var(--gray-5);
    border-radius: 6px;
    padding: 18px 16px;
    border-left: 3px solid var(--mint);
  }}
  .kpi-card--mul {{ border-left-color: var(--sand-80); }}
  .kpi-card--val {{ border-left-color: var(--onix); }}

  .kpi-card__label {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 8px;
  }}

  .kpi-card__value {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 28px;
    font-weight: 400;
    color: var(--onix);
    line-height: 1;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }}

  .kpi-card__hint {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    color: var(--onix);
    opacity: 0.55;
    margin-top: 4px;
  }}

  /* 2 colunas: assuntos | dicas */
  .warnings__cols {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px;
    flex: 1;
    min-height: 0;
  }}

  .warnings__sub {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 18px;
    font-weight: 400;
    color: var(--onix);
    margin-bottom: 12px;
    border-bottom: 1px solid var(--gray-20);
    padding-bottom: 8px;
  }}

  .assuntos-list {{
    list-style: none;
    margin: 0; padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .assunto-row {{
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 6px 0;
    border-bottom: 1px solid var(--gray-5);
  }}

  .assunto-row__num {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 14px;
    color: var(--mint-80);
    flex-shrink: 0;
    width: 22px;
    font-variant-numeric: tabular-nums;
  }}

  .assunto-row__txt {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    line-height: 1.4;
    color: var(--onix);
  }}

  .dicas-grid {{
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}

  .dica-card {{
    background: var(--gray-5);
    border-radius: 6px;
    padding: 12px 14px;
  }}

  .dica-card__titulo {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: var(--onix);
    margin-bottom: 4px;
  }}

  .dica-card__desc {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    line-height: 1.4;
    color: var(--onix);
    opacity: 0.75;
  }}

  /* Nota */
  .warnings__nota {{
    border-top: 1px solid var(--gray-20);
    padding-top: 12px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }}

  .warnings__nota-label {{
    flex: 0 0 100px;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    padding-top: 2px;
  }}

  .warnings__nota-text {{
    flex: 1;
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    line-height: 1.45;
    color: var(--onix);
    opacity: 0.7;
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
