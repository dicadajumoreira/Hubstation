"""Preview de Curiosidades do Setor (S06). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import IndustryFacts
from engine.theme import load_theme


DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "intro": "Quatro dados que dão contexto ao mercado de condomínios e ajudam a entender o que vai além do dia a dia do prédio.",
    "curiosidades": [
        {
            "fato": "27% dos brasileiros vivem em apartamento",
            "contexto": "A verticalização cresce 4× mais rápido que o crescimento populacional total. Cidades como São Paulo já têm 47% dos lares em prédios.",
            "fonte": "IBGE · Censo 2022",
        },
        {
            "fato": "R$ 612 é a taxa média mensal",
            "contexto": "Valor médio nacional pago por unidade. Pessoal e energia respondem por 64% das despesas; manutenção corretiva é o item que mais varia entre meses.",
            "fonte": "SECOVI-SP · 2025",
        },
        {
            "fato": "78% dos condomínios têm pet",
            "contexto": "Dois em cada três apartamentos brasileiros têm pelo menos um animal. Cães lideram, seguidos de gatos e aves. Conflitos sobre o tema são minoria — só 3,6%.",
            "fonte": "Abinpet · 2025",
        },
        {
            "fato": "1 em cada 4 prédios tem painel solar",
            "contexto": "A geração de energia em áreas comuns cresceu 38% no último ano. Investimento médio se paga em 4–6 anos com a economia na conta de luz.",
            "fonte": "ABSOLAR · 2026",
        },
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
    section = IndustryFacts()
    errors = section.validate(DEFAULT_INPUTS)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "industry_facts_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/industry_facts_a4.html")
    pdf_path = out_dir / "industry_facts_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "industry_facts_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
