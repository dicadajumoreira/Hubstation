"""Preview de Vida Condominial (S12B). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import LifestyleArticle
from engine.theme import load_theme


# Inputs de teste — "Dia do Amigo" da Modelo 2 Villa Park 04/2026
DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "kicker": "Dia do Amigo",
    "titulo": "Amigos de porta: a camada invisível que faz o prédio funcionar",
    "subtitulo": "Em 18 de abril, uma data discreta lembra que vizinhança e amizade não são a mesma coisa — mas dão lugar uma à outra com mais frequência do que a gente percebe.",
    "foto_principal": "",
    "fontes": ["Pesquisa Datafolha · 2026", "Diego Leite · gestor de atendimento"],
    "corpo": (
        "Em 18 de abril celebramos o Dia do Amigo no Brasil. Uma data discreta, mas "
        "importante para quem trabalha com atendimento condominial: a amizade dentro "
        "do prédio não é detalhe, é o que faz o elevador virar uma pausa agradável "
        "em vez de um silêncio incômodo.\n\n"
        "Vizinhança e amizade não são a mesma coisa, claro. Ninguém é obrigado a "
        "gostar de quem vive ao lado. Mas existe uma distância intermediária entre "
        "o estranho e o amigo, e ela faz toda a diferença no dia a dia. É o morador "
        "que já sabe o seu nome, que pergunta pela sua mãe, que guarda a sua "
        "encomenda por você.\n\n"
        "Na rotina de quem trabalha em condomínio, esses pequenos gestos acontecem "
        "o tempo todo. O morador de um andar que sobe a sacola de compras da "
        "senhora mais adiante. A criança que aprendeu a cumprimentar o porteiro "
        "pelo nome. O vizinho que empresta a furadeira antes da reforma do outro "
        "virar problema.\n\n"
        "Nada disso é grande. Nada disso muda o mundo. Mas juntos, esses movimentos "
        "silenciosos formam a camada mais importante de um condomínio bem vivido: "
        "a rede de relações que transforma moradores em comunidade. O Dia do Amigo "
        "serve para lembrar disso. E para, quem sabe, puxar conversa no corredor.\n\n"
        "A pesquisa Datafolha de 2026 mostra que moradores que conhecem ao menos "
        "três vizinhos pelo nome relatam 41% menos conflitos sobre regras de "
        "convivência. O dado é simples, mas eloquente: relação reduz atrito. "
        "Cumprimentar é a primeira porta. O resto vem com o tempo."
    ),
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
    ap.add_argument("--foto", default="")
    args = ap.parse_args()
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)

    theme = load_theme()
    section = LifestyleArticle()
    inputs = dict(DEFAULT_INPUTS)
    if args.foto:
        inputs["foto_principal"] = args.foto

    errors = section.validate(inputs)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(inputs)} pág")

    print("\n[A4]")
    html = render_html(section, theme, inputs)
    (out_dir / "lifestyle_article_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/lifestyle_article_a4.html")
    pdf_path = out_dir / "lifestyle_article_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "lifestyle_article_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
