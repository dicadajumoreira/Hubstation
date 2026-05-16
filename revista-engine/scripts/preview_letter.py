"""Preview da Carta do Síndico (S02)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import Letter
from engine.theme import load_theme


# Inputs de teste — Carta da Juliana, Villa Park 04/2026 (Modelo 2)
DEFAULT_INPUTS = {
    "genero": "feminino",
    "nome_sindico": "Juliana Moreira",
    "cargo": "Síndica · CEO Sindicompany",
    "mes_ano": "ABRIL 2026",
    "titulo": "Abril azul, olhar aberto.",
    "foto_sindico": "",
    "object_position": "center 25%",
    "texto": (
        "Queridos moradores do Villa Park Osasco, abril é o mês em que o mundo "
        "veste azul para falar de autismo — e nós aproveitamos esta edição para "
        "colocar a conversa sobre inclusão no centro da revista. Não porque seja "
        "uma pauta nova, mas porque é o tipo de tema que precisa voltar, voltar "
        "e voltar, até virar parte natural do jeito como vivemos aqui.\n\n"
        "Um condomínio acolhedor não é o que tem mais regras, nem o mais "
        "silencioso, nem o mais organizado. É aquele em que as diferenças "
        "cabem. Onde uma criança autista pode transitar sem ser mal vista numa "
        "crise sensorial. Onde um aviso de simulado chega com antecedência. "
        "Onde o porteiro sabe reconhecer quem precisa de um acolhimento a mais.\n\n"
        "Inclusão, como diz a matéria de capa, não é favor: é respeito, é "
        "convivência, é humanidade. Nas próximas páginas, você encontra dados "
        "e direitos da pessoa com TEA, seis gestos práticos que podem "
        "transformar o convívio em qualquer prédio, e uma agenda cultural com "
        "títulos que ajudam a enxergar o espectro por dentro.\n\n"
        "No campo financeiro, o último fechamento oficial é o de fevereiro, "
        "com saldo de R$ 186 mil, fundo de reserva preservado em R$ 107 mil "
        "e queda de 1,40% na inadimplência. Que este abril seja, para o "
        "Villa Park Osasco, um mês de olhar aberto. Boa leitura."
    ),
}


def render_html(section, theme, fmt, inputs):
    bodies = section.render_a4(inputs, theme) if fmt == "a4" else section.render_mobile(inputs, theme)
    return theme.page_document("\n".join(bodies), format=fmt)


def html_to_pdf(html, pdf_path):
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
        return True
    except Exception as e:
        print(f"  WeasyPrint falhou: {e}")
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
    ap.add_argument("--foto", default="", help="Caminho/URL da foto do síndico")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = Letter()
    inputs = dict(DEFAULT_INPUTS)
    if args.foto:
        inputs["foto_sindico"] = args.foto

    errors = section.validate(inputs)
    if errors:
        print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(inputs)} pág")

    for fmt in ("a4",):  # mobile pausado nesta fase — A4 only
        print(f"\n[{fmt.upper()}]")
        html = render_html(section, theme, fmt, inputs)
        html_path = out_dir / f"letter_{fmt}.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"  ✓ HTML  → {html_path}")
        pdf_path = out_dir / f"letter_{fmt}.pdf"
        if html_to_pdf(html, pdf_path):
            print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
            png_path = out_dir / f"letter_{fmt}.png"
            if pdf_to_png(pdf_path, png_path):
                print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
