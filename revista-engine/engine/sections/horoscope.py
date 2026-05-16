"""
S13 — Signos do Mês.

1 página fixa. Grid 3×4 com 12 signos do zodíaco. Tom leve, ~30-40
palavras por previsão (Doc 01 §3 S13).

Inputs:
- mes_referencia (str) — ex: "ABRIL 2026"
- previsoes (dict[str, str | dict]) — 12 chaves obrigatórias:
    aries, touro, gemeos, cancer, leao, virgem, libra,
    escorpiao, sagitario, capricornio, aquario, peixes
  Cada valor pode ser:
    - string (texto da previsão), ou
    - dict {texto: str}
"""

from __future__ import annotations

import unicodedata

from .base import Section


# Ordem oficial + metadados (data zodiacal e símbolo Unicode)
_SIGNOS = [
    ("aries",       "Áries",        "21 mar – 19 abr", "♈"),
    ("touro",       "Touro",        "20 abr – 20 mai", "♉"),
    ("gemeos",      "Gêmeos",       "21 mai – 20 jun", "♊"),
    ("cancer",      "Câncer",       "21 jun – 22 jul", "♋"),
    ("leao",        "Leão",         "23 jul – 22 ago", "♌"),
    ("virgem",      "Virgem",       "23 ago – 22 set", "♍"),
    ("libra",       "Libra",        "23 set – 22 out", "♎"),
    ("escorpiao",   "Escorpião",    "23 out – 21 nov", "♏"),
    ("sagitario",   "Sagitário",    "22 nov – 21 dez", "♐"),
    ("capricornio", "Capricórnio",  "22 dez – 19 jan", "♑"),
    ("aquario",     "Aquário",      "20 jan – 18 fev", "♒"),
    ("peixes",      "Peixes",       "19 fev – 20 mar", "♓"),
]


class Horoscope(Section):
    """Signos do Mês (S13)."""

    type = "horoscope"
    label = "Signos do Mês"

    def validate(self, inputs: dict) -> list[str]:
        errors: list[str] = []
        previsoes = inputs.get("previsoes") or {}
        if not isinstance(previsoes, dict):
            errors.append("Signos: 'previsoes' deve ser um dicionário com 12 chaves")
            return errors
        faltantes = [s[0] for s in _SIGNOS if s[0] not in previsoes]
        if faltantes:
            errors.append(
                "Signos: faltam previsões para: " + ", ".join(faltantes)
            )
        return errors

    def paginate(self, inputs: dict) -> int:
        return 1

    def render_a4(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def render_mobile(self, inputs: dict, theme) -> list[str]:
        return [self._render(inputs, theme)]

    def _render(self, inputs: dict, theme) -> str:
        mes = (inputs.get("mes_referencia") or "").strip().upper()
        previsoes = inputs.get("previsoes") or {}

        cards = []
        for slug, nome, datas, simbolo in _SIGNOS:
            raw = previsoes.get(slug, "")
            texto = raw.get("texto", "") if isinstance(raw, dict) else str(raw)
            cards.append(f"""
      <article class="signo-card">
        <div class="signo-card__symbol">{simbolo}</div>
        <div class="signo-card__nome">{_escape(nome)}</div>
        <div class="signo-card__datas">{_escape(datas)}</div>
        <p class="signo-card__texto">{_escape(texto)}</p>
      </article>""")

        return f"""
<section class="page horoscope-page">
  <div class="horoscope__content">
    <header class="horoscope__header">
      <div class="horoscope__kicker">SIGNOS · {_escape(mes)}</div>
      <h1 class="horoscope__titulo">O céu deste mês</h1>
      <p class="horoscope__sub">
        Uma leitura curta do que o mês reserva para cada signo.
        Pegue leve — diversão antes de superstição.
      </p>
    </header>

    <div class="horoscope__grid">
      {''.join(cards)}
    </div>
  </div>
</section>

<style>
  .horoscope-page {{
    background: var(--white);
    color: var(--onix);
    padding: 48px 56px 40px;
  }}

  .horoscope__content {{
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }}

  .horoscope__kicker {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 12px;
  }}

  .horoscope__titulo {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 44px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.025em;
    color: var(--onix);
    margin-bottom: 6px;
  }}

  .horoscope__sub {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    color: var(--onix);
    opacity: 0.65;
    line-height: 1.4;
    max-width: 60ch;
  }}

  .horoscope__grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(4, 1fr);
    gap: 10px;
    flex: 1;
    min-height: 0;
  }}

  .signo-card {{
    background: var(--gray-5);
    border-radius: 6px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow: hidden;
  }}

  /* Cores rotativas por linha — toca um sinal visual sutil de variedade */
  .signo-card:nth-child(3n+1) {{ background: #F4F4F5; }}
  .signo-card:nth-child(3n+2) {{ background: #EEF7F8; }} /* mint vibe */
  .signo-card:nth-child(3n+3) {{ background: #F7EFE9; }} /* sand vibe */

  .signo-card__symbol {{
    font-size: 28px;
    line-height: 1;
    color: var(--mint-80);
    font-weight: 400;
  }}

  .signo-card__nome {{
    font-family: '{theme.fonte_titulos.family}', 'Liberation Serif', 'DejaVu Serif', Georgia, serif;
    font-size: 16px;
    font-weight: 400;
    color: var(--onix);
    line-height: 1.1;
    margin-top: 4px;
  }}

  .signo-card__datas {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--mint-80);
    margin-bottom: 6px;
  }}

  .signo-card__texto {{
    font-family: '{theme.fonte_corpo.family}', 'DejaVu Sans', 'Liberation Sans', 'Helvetica Neue', Arial, sans-serif;
    font-size: 9.5px;
    font-weight: 400;
    line-height: 1.45;
    color: var(--onix);
    opacity: 0.85;
    flex: 1;
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
