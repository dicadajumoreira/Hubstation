"""Preview de Dicas Práticas (S05). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import Tips
from engine.theme import load_theme


DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "titulo_secao": "Pequenos gestos, convivência maior",
    "intro": (
        "Seis hábitos simples que reduzem atrito no condomínio sem virar "
        "regulamento. Pegue só os que fazem sentido pra rotina do seu prédio."
    ),
    "dicas": [
        {
            "titulo": "Cumprimente pelo nome",
            "corpo": "Guardar o nome do vizinho é uma forma silenciosa de reconhecimento. Faz com que o elevador deixe de ser um lugar incômodo.",
        },
        {
            "titulo": "Receba uma encomenda alheia",
            "corpo": "Cinco minutos seus economizam uma tarde toda de quem está trabalhando. Reciprocidade nasce naturalmente.",
        },
        {
            "titulo": "Avise antes da reforma",
            "corpo": "Comunique a portaria e os vizinhos próximos um dia antes. O barulho passa a ser tolerável quando deixa de ser surpresa.",
        },
        {
            "titulo": "Coleira sempre nas áreas comuns",
            "corpo": "Mesmo que seu pet seja dócil, vizinhos podem ter alergia ou medo. Coleira é cuidado coletivo, não desconfiança individual.",
        },
        {
            "titulo": "Reserve antes de usar",
            "corpo": "Salão, churrasqueira, quadra: reservar evita conflitos e garante que o espaço esteja em ordem quando você chegar.",
        },
        {
            "titulo": "Recolha sempre os dejetos",
            "corpo": "Saco no bolso é regra básica de quem sai com pet. Para quem encontra o esquecimento dos outros, paciência e bom humor.",
        },
        {
            "titulo": "Respeite o silêncio noturno",
            "corpo": "Após 22h em dias úteis (23h fim de semana), volume baixo e passos leves. Boa convivência se constrói no detalhe.",
        },
        {
            "titulo": "Devolva o que pediu emprestado",
            "corpo": "Furadeira, escada, cadeira extra: devolva no prazo e em ordem. Quem empresta de novo é quem confia.",
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
    section = Tips()
    errors = section.validate(DEFAULT_INPUTS)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "tips_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/tips_a4.html")
    pdf_path = out_dir / "tips_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "tips_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
