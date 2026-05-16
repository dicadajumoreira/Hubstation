"""Preview de Nossos Números (S11). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import OurNumbers
from engine.theme import load_theme


# Inputs de teste — Villa Park 04/2026 (Modelo 2 cita: saldo R$186k, fundo R$107k, queda 1,40% inad)
DEFAULT_INPUTS = {
    "mes_referencia": "FEVEREIRO 2026",
    "kpis": {
        "receita_brl": 280_000.00,
        "despesas_brl": 94_000.00,
        "fundo_reserva_brl": 107_000.00,
        "inadimplencia_pct": 4.0,
    },
    "principais_despesas": [
        {"categoria": "Pessoal e encargos", "valor_brl": 38_500.00, "observacao": "Folha + INSS"},
        {"categoria": "Energia elétrica",   "valor_brl": 12_400.00, "observacao": "Áreas comuns"},
        {"categoria": "Limpeza e conservação", "valor_brl": 9_800.00, "observacao": ""},
        {"categoria": "Manutenção predial", "valor_brl": 14_200.00, "observacao": "Bombas + jardim"},
        {"categoria": "Segurança",          "valor_brl": 11_300.00, "observacao": "Vigilância 24h"},
        {"categoria": "Administração",      "valor_brl": 6_900.00,  "observacao": ""},
        {"categoria": "Outros",             "valor_brl": 900.00,    "observacao": ""},
    ],
    "despesa_extra": {
        "categoria": "Substituição da esteira da academia",
        "valor_brl": 8_400.00,
        "descricao": (
            "Equipamento atingiu fim de vida útil; substituição com modelo "
            "novo cobrindo garantia de 24 meses. Aprovado pelo conselho em "
            "reunião ordinária de janeiro."
        ),
    },
    "historico": [
        {"mes": "OUT", "receita_brl": 248_000, "despesas_brl": 178_000, "inadimplencia_pct": 5.4},
        {"mes": "NOV", "receita_brl": 261_000, "despesas_brl": 172_000, "inadimplencia_pct": 5.1},
        {"mes": "DEZ", "receita_brl": 288_000, "despesas_brl": 192_000, "inadimplencia_pct": 4.9},
        {"mes": "JAN", "receita_brl": 274_000, "despesas_brl": 187_000, "inadimplencia_pct": 4.4},
        {"mes": "FEV", "receita_brl": 280_000, "despesas_brl": 94_000,  "inadimplencia_pct": 4.0},
    ],
    "nota_transparencia": "",  # usa default da seção
}


def render_html(section, theme, inputs):
    bodies = section.render_a4(inputs, theme)
    return theme.page_document("\n".join(bodies), format="a4")


def html_to_pdf(html, pdf_path):
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
        return True
    except Exception as e:
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
    section = OurNumbers()
    inputs = DEFAULT_INPUTS

    errors = section.validate(inputs)
    if errors:
        print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(inputs)} pág")

    print("\n[A4]")
    html = render_html(section, theme, inputs)
    html_path = out_dir / "our_numbers_a4.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → {html_path}")
    pdf_path = out_dir / "our_numbers_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "our_numbers_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
