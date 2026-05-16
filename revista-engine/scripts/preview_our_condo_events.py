"""Preview de Nosso Condomínio — Eventos (S09). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import OurCondoEvents
from engine.theme import load_theme


DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "nome_condominio": "Villa Park Osasco",
    "eventos": [
        {
            "titulo": "Páscoa em comunidade",
            "data": "5 de abril",
            "descricao": "Caça aos ovos no parquinho reuniu mais de 80 crianças.",
            "fotos": [""],
        },
        {
            "titulo": "Vacinação infantil",
            "data": "12 de abril",
            "descricao": "Posto de saúde móvel atendeu moradores no salão de festas.",
            "fotos": [""],
        },
        {
            "titulo": "Feira de troca de livros",
            "data": "20 de abril",
            "descricao": "Iniciativa do conselho cultural circulou mais de 200 livros.",
            "fotos": [""],
        },
        {
            "titulo": "Aulão de yoga",
            "data": "27 de abril",
            "descricao": "Manhã de domingo no jardim com instrutora convidada.",
            "fotos": [""],
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
        ["pdftoppm", "-r", str(dpi), "-png",
         str(pdf_path), str(prefix)],
        check=True, capture_output=True,
    )
    return any(prefix.parent.glob(f"{prefix.name}-*.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tmp_preview")
    args = ap.parse_args()
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = OurCondoEvents()
    errors = section.validate(DEFAULT_INPUTS)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "our_condo_events_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/our_condo_events_a4.html")
    pdf_path = out_dir / "our_condo_events_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "our_condo_events_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
