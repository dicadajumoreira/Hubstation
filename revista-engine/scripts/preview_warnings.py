"""Preview de Advertências e Multas (S12). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import Warnings
from engine.theme import load_theme


DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "total_advertencias": 8,
    "total_multas": 2,
    "valor_multas_brl": 850.00,
    "assuntos_recorrentes": [
        "Barulho após as 22h em finais de semana",
        "Animais fora da coleira em áreas comuns",
        "Uso indevido do salão de festas (sem reserva)",
        "Lixo descartado fora do horário",
        "Veículos estacionados em vagas alheias",
    ],
    # dicas vazia -> auto-geradas a partir dos assuntos
    "dicas": [],
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
    generated = prefix.parent / f"{prefix.name}-1.png"
    if generated.exists():
        generated.rename(png_path)
    return png_path.exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tmp_preview")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = Warnings()
    inputs = DEFAULT_INPUTS

    errors = section.validate(inputs)
    if errors:
        print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(inputs)} pág")

    print("\n[A4]")
    html = render_html(section, theme, inputs)
    html_path = out_dir / "warnings_a4.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → {html_path}")
    pdf_path = out_dir / "warnings_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "warnings_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
