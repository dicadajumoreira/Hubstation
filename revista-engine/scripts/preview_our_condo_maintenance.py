"""Preview de Nosso Condomínio — Manutenções (S08). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import OurCondoMaintenance
from engine.theme import load_theme


# Inputs de teste — manutenções típicas de Villa Park 04/2026
DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "nome_condominio": "Villa Park Osasco",
    "manutencoes": [
        {"titulo": "Manutenção do Jardim",     "tipo_badge": "JARDIM",      "fotos": [""]},
        {"titulo": "Substituição da Esteira",   "tipo_badge": "MANUTENÇÃO",  "fotos": [""]},
        {"titulo": "Iluminação da Cancela",     "tipo_badge": "SEGURANÇA",   "fotos": [""]},
        {"titulo": "Reparo de Tubulação",       "tipo_badge": "MANUTENÇÃO",  "fotos": [""]},
        {"titulo": "Solda do Portão",           "tipo_badge": "SEGURANÇA",   "fotos": [""]},
        {"titulo": "Dedetização",               "tipo_badge": "OPERACIONAL", "fotos": [""]},
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
    """Renderiza todas as páginas do PDF em PNGs separados (suffix -1, -2, ...)."""
    if not shutil.which("pdftoppm"): return False
    prefix = png_path.with_suffix("")
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png",
         str(pdf_path), str(prefix)],
        check=True, capture_output=True,
    )
    # pdftoppm gera <prefix>-1.png, <prefix>-2.png etc
    return any(prefix.parent.glob(f"{prefix.name}-*.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tmp_preview")
    args = ap.parse_args()
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = OurCondoMaintenance()
    errors = section.validate(DEFAULT_INPUTS)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "our_condo_maintenance_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/our_condo_maintenance_a4.html")
    pdf_path = out_dir / "our_condo_maintenance_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "our_condo_maintenance_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
