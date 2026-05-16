"""Preview de Matéria de Capa (S04). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import CoverStory
from engine.theme import load_theme


# Inputs de teste — tema "Pets" da Modelo 1 Gardens 04/2026
DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "kicker": "Especial de capa",
    "manchete": "O condomínio que ama pets vive melhor",
    "subtitulo": "O Brasil tem 160 milhões de animais de estimação. Em muitos prédios, tem mais pet do que gente — e conviver bem exige um pouco mais do que boa vontade.",
    "foto_principal": "",
    "fontes": ["IBGE · Censo 2022", "Abinpet 2025", "STJ · jurisprudência consolidada"],
    "corpo_blocos": [
        {"tipo": "paragrafo", "texto": "A presença de pets nos condomínios deixou de ser exceção para virar regra. Em São Paulo, dois em cada três apartamentos abrigam ao menos um animal — número que subiu 18% nos últimos cinco anos. Cães lideram, gatos avançam, aves resistem. E com eles vêm conflitos previsíveis: barulho, pelo, alergia, dejeto."},
        {"tipo": "intertitulo", "texto": "O que diz a lei"},
        {"tipo": "paragrafo", "texto": "A legislação brasileira é clara: condomínios não podem proibir a posse de animais de estimação. O STJ consolidou esse entendimento em 2019, declarando nula qualquer convenção que vete de forma genérica a presença de pets nas unidades privativas."},
        {"tipo": "dado_box", "numero": "78%", "contexto": "dos condomínios brasileiros têm pelo menos um pet morando nas unidades. Em São Paulo capital, esse número sobe para 84%.", "fonte": "Abinpet · 2025"},
        {"tipo": "paragrafo", "texto": "O que o condomínio pode fazer é regulamentar a convivência. Coleira nas áreas comuns, higiene do espaço de circulação, limites de tamanho ou raça quando há risco real comprovado. Tudo passa por assembleia, regimento atualizado, e — principalmente — comunicação."},
        {"tipo": "pull_quote", "texto": "Inclusão não é favor: é convivência, é respeito, é humanidade.", "autor": "Juliana Moreira · CEO Sindicompany"},
        {"tipo": "intertitulo", "texto": "Como reduzir conflitos no dia a dia"},
        {"tipo": "paragrafo", "texto": "A pesquisa Datafolha de 2026 mostra que prédios com regulamento claro sobre pets têm 41% menos reclamações formais. O segredo está na clareza, não no rigor: regras simples, conhecidas por todos, sem zonas cinzentas."},
    ],
}


def render_html(section, theme, inputs):
    bodies = section.render_a4(inputs, theme)
    return theme.page_document("\n".join(bodies), format="a4")


def html_to_pdf(html, pdf_path):
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
        return True
    except Exception:
        import traceback; traceback.print_exc()
        return False


def pdf_to_png(pdf_path, png_path, dpi=150):
    if not shutil.which("pdftoppm"): return False
    prefix = png_path.with_suffix("")
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", "-f", "1", "-l", "1",
         str(pdf_path), str(prefix)],
        check=True, capture_output=True,
    )
    g = prefix.parent / f"{prefix.name}-1.png"
    if g.exists(): g.rename(png_path)
    return png_path.exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tmp_preview")
    args = ap.parse_args()
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = CoverStory()
    errors = section.validate(DEFAULT_INPUTS)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "cover_story_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/cover_story_a4.html")
    pdf_path = out_dir / "cover_story_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "cover_story_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
