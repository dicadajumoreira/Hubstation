"""Preview da Capa (S01). Mesma lógica do preview_back_cover."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import Cover
from engine.theme import load_theme


# Inputs de teste — baseados em tema "pets" da edição 04/2026 do Gardens
DEFAULT_INPUTS = {
    "edicao_label": "EDIÇÃO 04 · ABRIL 2026 · GARDENS LIVING CLUB · @sindicompanybr",
    "tema_materia": "Pets no condomínio",
    "manchete": "O condomínio que ama pets vive melhor",
    "subtitulo": "Convivência, regulação e bons exemplos para áreas comuns que acolhem 160 milhões de animais.",
    "chamadas": [
        "Carta dos Síndicos · Páscoa em comunidade",
        "Nossos números · Inadimplência em 6,8%",
        "Receita do mês · Bolo de fubá da vovó",
    ],
    "foto_capa": "",  # vazio = usa gradiente placeholder
}


def render_html(section, theme, fmt, inputs):
    if fmt == "a4":
        bodies = section.render_a4(inputs, theme)
    else:
        bodies = section.render_mobile(inputs, theme)
    return theme.page_document("\n".join(bodies), format=fmt)


def html_to_pdf(html, pdf_path):
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
        return True
    except Exception as e:
        print(f"  WeasyPrint falhou: {e}")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            page.pdf(path=str(pdf_path), prefer_css_page_size=True)
            browser.close()
        return True
    except Exception as e:
        print(f"  Playwright também falhou: {e}")
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
    ap.add_argument("--foto", default="", help="Caminho/URL da foto de capa (default: gradiente placeholder)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = Cover()
    inputs = dict(DEFAULT_INPUTS)
    if args.foto:
        inputs["foto_capa"] = args.foto

    errors = section.validate(inputs)
    if errors:
        print(f"✗ Validação falhou: {errors}")
        sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(inputs)} pág")

    for fmt in ("a4",):  # mobile pausado nesta fase — A4 only
        print(f"\n[{fmt.upper()}]")
        html = render_html(section, theme, fmt, inputs)
        html_path = out_dir / f"cover_{fmt}.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"  ✓ HTML  → {html_path}")

        pdf_path = out_dir / f"cover_{fmt}.pdf"
        if html_to_pdf(html, pdf_path):
            print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
            png_path = out_dir / f"cover_{fmt}.png"
            if pdf_to_png(pdf_path, png_path):
                print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
