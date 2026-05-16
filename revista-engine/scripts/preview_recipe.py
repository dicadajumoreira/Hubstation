"""Preview de Receita do Mês (S10). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import Recipe
from engine.theme import load_theme


# Receita citada na Modelo 2 (Villa Park 04/2026): Creme de abóbora com gengibre
DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "titulo_receita": "Creme de abóbora com gengibre",
    "tempo_preparo": "35 min · serve 6 pessoas",
    "intro": (
        "Confortável para o início do outono, esse creme aveludado leva pouca "
        "manteiga e ganha personalidade do gengibre fresco. Cremoso por dentro, "
        "leve no estômago."
    ),
    "foto_receita": "",  # vazio = placeholder
    "ingredientes": [
        "800 g de abóbora cabotiá descascada e em cubos",
        "1 cebola média picada",
        "2 dentes de alho amassados",
        "1 colher de sopa de gengibre fresco ralado",
        "1 colher de sopa de azeite extra-virgem",
        "1 litro de caldo de legumes",
        "150 ml de leite de coco",
        "Sal, pimenta-do-reino e noz-moscada a gosto",
        "Sementes de abóbora tostadas (para finalizar)",
    ],
    "modo_preparo": [
        "Numa panela média, refogue a cebola no azeite até ficar translúcida. Adicione o alho e o gengibre, mexendo por mais 1 minuto.",
        "Acrescente os cubos de abóbora e o caldo de legumes. Tempere com sal, pimenta e noz-moscada. Cozinhe em fogo médio por cerca de 20 minutos, até a abóbora ficar bem macia.",
        "Bata o conteúdo da panela no liquidificador (ou use um mixer) até virar um creme liso e sem grumos.",
        "Volte para o fogo, junte o leite de coco e ajuste o sal. Cozinhe por mais 3 minutos só para incorporar.",
        "Sirva quente, finalizado com sementes de abóbora tostadas e um fio de azeite.",
    ],
    "dica": (
        "Prefira a abóbora cabotiá (japonesa) — ela tem polpa firme, é menos "
        "aguada e fica mais cremosa. Se sobrar, congele em porções: dura até "
        "2 meses e esquenta direto da geladeira."
    ),
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
    if not shutil.which("pdftoppm"):
        return False
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
    section = Recipe()
    errors = section.validate(DEFAULT_INPUTS)
    if errors:
        print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "recipe_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/recipe_a4.html")
    pdf_path = out_dir / "recipe_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "recipe_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
