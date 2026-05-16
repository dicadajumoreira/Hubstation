"""
Preview de uma seção: renderiza HTML, gera PDF e PNG pra revisão visual.

Uso:
    python3 scripts/preview_back_cover.py [--out tmp_preview]

Gera 4 arquivos no diretório de saída:
    back_cover_a4.html       — HTML auto-contido (abre no navegador)
    back_cover_a4.pdf        — PDF (impressão / compartilhamento)
    back_cover_a4.png        — captura visual da página
    back_cover_mobile.*      — versões mobile

Renderização: tenta weasyprint (puro Python), depois playwright se disponível.
Conversão PDF→PNG: pdftoppm (poppler-utils).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Permite rodar sem instalar o pacote
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import BackCover
from engine.theme import load_theme


def render_html(section, theme, fmt: str, inputs: dict) -> str:
    if fmt == "a4":
        bodies = section.render_a4(inputs, theme)
    elif fmt == "mobile":
        bodies = section.render_mobile(inputs, theme)
    else:
        raise ValueError(f"Formato desconhecido: {fmt!r}")
    body = "\n".join(bodies)
    return theme.page_document(body, format=fmt)


def html_to_pdf(html: str, pdf_path: Path) -> bool:
    """Tenta WeasyPrint primeiro; depois Playwright. Retorna True se gerou."""
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
        return True
    except Exception as e:
        print(f"  WeasyPrint falhou ({e.__class__.__name__}: {e}); tentando Playwright...")

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
        print(f"  Playwright também falhou ({e.__class__.__name__}: {e})")
        return False


def pdf_to_png(pdf_path: Path, png_path: Path, dpi: int = 150) -> bool:
    """Converte primeira página do PDF em PNG via pdftoppm."""
    if not shutil.which("pdftoppm"):
        print("  pdftoppm não encontrado; pule PNG (apt-get install poppler-utils)")
        return False
    try:
        # pdftoppm gera <prefix>-1.png; usar prefixo temporário e renomear
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
    except subprocess.CalledProcessError as e:
        print(f"  pdftoppm falhou: {e.stderr.decode()[:200]}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tmp_preview", help="Diretório de saída")
    ap.add_argument(
        "--proxima",
        default="Próxima edição: junho 2026",
        help="Label opcional 'próxima edição' no rodapé",
    )
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Carregando tema...")
    theme = load_theme()
    print(f"  ✓ {theme.nome} · paleta com {len(theme.paleta)} cores · "
          f"{theme.fonte_titulos.family}/{theme.fonte_corpo.family}")

    section = BackCover()
    inputs = {"proxima_edicao_label": args.proxima}

    errors = section.validate(inputs)
    if errors:
        print(f"  ✗ Erros de validação: {errors}")
        sys.exit(1)
    print(f"  ✓ Seção {section.label} validada · {section.paginate(inputs)} página(s)")

    for fmt in ("a4",):  # mobile pausado nesta fase — A4 only
        print(f"\n[{fmt.upper()}]")
        html = render_html(section, theme, fmt, inputs)

        html_path = out_dir / f"back_cover_{fmt}.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"  ✓ HTML  → {html_path} ({len(html)//1024}KB)")

        pdf_path = out_dir / f"back_cover_{fmt}.pdf"
        if html_to_pdf(html, pdf_path):
            print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
            png_path = out_dir / f"back_cover_{fmt}.png"
            if pdf_to_png(pdf_path, png_path):
                print(f"  ✓ PNG   → {png_path} ({png_path.stat().st_size//1024}KB)")

    print(f"\nPronto. Abra os arquivos em {out_dir}/ para revisar.")


if __name__ == "__main__":
    main()
