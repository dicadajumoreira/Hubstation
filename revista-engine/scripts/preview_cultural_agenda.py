"""Preview de Agenda Cultural (S03). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import CulturalAgenda
from engine.theme import load_theme


# Inputs de teste — abril/2026 (Modelo 1)
DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "hero": {
        "categoria": "Estreia",
        "titulo": "O Diabo Veste Prada 2",
        "sinopse": (
            "Meryl Streep e Anne Hathaway voltam a vestir os figurinos "
            "icônicos. Vinte anos depois, a Runway encara o mundo digital "
            "e Miranda Priestly enfrenta uma rival inesperada."
        ),
        "data": "30 abr · cinemas",
        "foto": "",  # sem foto -> placeholder gradient
    },
    "cards_secundarios": [
        {
            "categoria": "Cinema",
            "titulo": "Michael",
            "descricao_curta": "Cinebiografia épica do Rei do Pop por Antoine Fuqua.",
            "data": "23 abr",
        },
        {
            "categoria": "Série",
            "titulo": "The Last of Us — T2",
            "descricao_curta": "Pedro Pascal e Bella Ramsey no pós-apocalipse mais intenso da TV.",
            "data": "abr · Max",
        },
        {
            "categoria": "Show",
            "titulo": "Coldplay em SP",
            "descricao_curta": "Turnê Music of the Spheres no Morumbi: luz, cor e confete.",
            "data": "11–13 abr",
        },
        {
            "categoria": "Game",
            "titulo": "GTA VI",
            "descricao_curta": "O game mais esperado da história. Novo mapa em Leonida.",
            "data": "mai 2026",
        },
        {
            "categoria": "Exposição",
            "titulo": "Van Gogh imersivo",
            "descricao_curta": "300 obras em imersão multissensorial 360° no CCBB SP.",
            "data": "até mai",
        },
        {
            "categoria": "Livro",
            "titulo": "Bienal do Livro SP",
            "descricao_curta": "Maior evento literário do país reúne autores e lançamentos.",
            "data": "16–27 abr",
        },
        {
            "categoria": "Cinema",
            "titulo": "Karate Kid: Legends",
            "descricao_curta": "Jackie Chan e Ralph Macchio juntos pela primeira vez. Nostalgia total.",
            "data": "30 mai",
        },
        {
            "categoria": "Série",
            "titulo": "ST: Histórias de 85",
            "descricao_curta": "Antologia do universo Hawkins. Novos personagens nos anos 80.",
            "data": "23 abr · Netflix",
        },
        {
            "categoria": "Show",
            "titulo": "Anitta — Especial Brasil",
            "descricao_curta": "Maior produção da carreira do pop-boy brasileiro. Quase esgotado.",
            "data": "3 mai",
        },
        {
            "categoria": "Game",
            "titulo": "Hollow Knight: Silksong",
            "descricao_curta": "O metroidvania mais esperado dos últimos anos finalmente chega.",
            "data": "2026",
        },
        {
            "categoria": "Evento",
            "titulo": "SPFW — Moda BR",
            "descricao_curta": "São Paulo Fashion Week apresenta coleções inverno das grandes grifes.",
            "data": "abr · SP",
        },
        {
            "categoria": "Show",
            "titulo": "Lollapalooza Brasil",
            "descricao_curta": "SZA, Arcade Fire e The Killers no maior festival urbano do país.",
            "data": "25–27 abr",
        },
        {
            "categoria": "Cinema",
            "titulo": "Thunderbolts*",
            "descricao_curta": "Anti-heróis em missão suicida. Florence Pugh e Sebastian Stan.",
            "data": "30 abr",
        },
        {
            "categoria": "Cinema",
            "titulo": "Missão: Impossível 8",
            "descricao_curta": "Tom Cruise no adeus definitivo de Ethan Hunt. Mais explosivo impossível.",
            "data": "23 mai",
        },
        {
            "categoria": "Série",
            "titulo": "Andor — T2",
            "descricao_curta": "A melhor série de Star Wars encerra com a resistência ao Império.",
            "data": "22 abr · Disney+",
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

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = CulturalAgenda()

    errors = section.validate(DEFAULT_INPUTS)
    if errors:
        print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    html_path = out_dir / "cultural_agenda_a4.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → {html_path}")
    pdf_path = out_dir / "cultural_agenda_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "cultural_agenda_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
