"""Preview de Signos do Mês (S13). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import Horoscope
from engine.theme import load_theme


# Previsões de teste, ~30-40 palavras cada, tom leve
DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "previsoes": {
        "aries": "Energia em alta para projetos no condomínio. Você vai querer mover o que estiver parado. Cuidado para não atropelar quem está no mesmo elevador. Paciência com vizinhos rende mais que pressa.",
        "touro": "Mês de pequenas reformas e ajustes em casa. O orçamento pede atenção: peça orçamentos, compare. Conforto chega quando você se permite trocar o que já não serve.",
        "gemeos": "Conversas no hall e nas reuniões podem render alianças inesperadas. Boa hora para se candidatar a algum conselho ou propor uma melhoria coletiva. Comunicação é seu superpoder.",
        "cancer": "Foco no aconchego de casa. Reorganizar um cômodo, plantar uma erva na varanda, convidar alguém pra um café — gestos pequenos com efeito grande no humor do mês.",
        "leao": "Brilho garantido em eventos do prédio. Se for organizar uma festa de Páscoa, você é a pessoa certa. Lembre só de incluir os mais quietos: vizinhança boa cabe todo mundo.",
        "virgem": "Mês de organização. Documentação, listas, prestação de contas — tudo passa por você naturalmente. Aproveite para revisar o regulamento; você vai notar coisas que ninguém viu.",
        "libra": "Conflitos em áreas comuns pedem sua mediação. Você sabe ouvir os dois lados sem perder a leveza. Não evite a conversa difícil; ela traz alívio que a fofoca não traz.",
        "escorpiao": "Intensidade visita seus relacionamentos próximos. Mês bom para esclarecer mal-entendidos antigos com vizinhos. Verdades ditas com cuidado fortalecem a convivência diária.",
        "sagitario": "Vontade de explorar fora do prédio aumenta. Inscreva-se em uma atividade nova no bairro. Conhecer gente diferente vai te trazer histórias que cabem no elevador.",
        "capricornio": "Trabalho duro rende reconhecimento. Se você vem se dedicando ao condomínio em silêncio, espere ouvir um obrigado neste mês. Aceite — você merece.",
        "aquario": "Ideias inovadoras encontram terreno fértil. Proponha uma melhoria coletiva — horta, biblioteca compartilhada, mutirão de troca. O grupo está mais aberto do que você imagina.",
        "peixes": "Sensibilidade aflorada. Você vai perceber humores e tensões antes dos outros. Use essa antena com gentileza: um cumprimento atento pode mudar o dia de um vizinho.",
    },
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
    section = Horoscope()

    errors = section.validate(DEFAULT_INPUTS)
    if errors:
        print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    html_path = out_dir / "horoscope_a4.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → {html_path}")
    pdf_path = out_dir / "horoscope_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "horoscope_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
