"""Preview de Expediente (S14). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import Colophon
from engine.theme import load_theme


DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "nome_condominio": "Villa Park Osasco",
    "numero_edicao": 4,
    "ano_edicao": 2026,
    "nome_sindico": "Juliana Moreira",
    "cargo_sindico": "Síndica · CEO Sindicompany",
    "editor_responsavel": "Equipe Editorial Sindicompany",
    "equipe_condominio": [
        "Zeladoria | Gerência",
        "Equipe Manutenção",
        "Equipe de Limpeza",
        "Equipe de Portaria",
        "Equipe Administrativa",
    ],
    "equipe_sindicompany": [
        "Direção editorial",
        "Pauta e Produção",
        "Diagramação e Arte",
    ],
    "creditos_extras": [
        {
            "titulo": "Colaboradores",
            "nomes": [
                "Fotos de manutenção · Equipe técnica",
                "Pesquisa econômica · SECOVI-SP",
                "Curadoria cultural · Cinemark + Spotify Editorial",
            ],
        },
    ],
    "contato": "revista@sindicompany.com.br",
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
    section = Colophon()
    errors = section.validate(DEFAULT_INPUTS)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "colophon_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/colophon_a4.html")
    pdf_path = out_dir / "colophon_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "colophon_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
