"""Preview de Novidades e Legislação (S07). A4 only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.sections import News
from engine.theme import load_theme


DEFAULT_INPUTS = {
    "mes_referencia": "ABRIL 2026",
    "intro": "O que mudou no mercado, na lei e na tecnologia condominial nos últimos 30 dias.",
    "noticias": [
        {
            "badge": "Legislação",
            "titulo": "STJ valida cobrança de taxa por uso intensivo do elevador em prédios mistos",
            "data": "12/04/2026",
            "resumo": "Decisão da Quarta Turma autoriza que assembleias deliberem cobrança extra para unidades comerciais que usem o elevador além da média residencial. Vale apenas com aprovação por maioria simples e regulamento atualizado.",
            "fonte": "STJ · Resp 2.187.443",
        },
        {
            "badge": "Mercado",
            "titulo": "Taxa condominial sobe 5,8% no primeiro trimestre",
            "data": "abril/2026",
            "resumo": "Aumento acima da inflação puxado por reajustes em pessoal e energia elétrica. SECOVI-SP recomenda revisão anual de orçamento e reservas para evitar chamadas extras a moradores.",
            "fonte": "SECOVI-SP · Boletim mensal",
        },
        {
            "badge": "Tecnologia",
            "titulo": "Reconhecimento facial em portarias chega a 1 em cada 5 prédios em SP",
            "data": "08/04/2026",
            "resumo": "Adoção cresceu 47% em 12 meses. LGPD exige consentimento explícito do morador e plano de descarte de dados; condomínios que ignoram regra arriscam multa de até 2% do faturamento.",
            "fonte": "ANPD + ABADI · 2026",
        },
        {
            "badge": "Novidade",
            "titulo": "Pix institucional já está disponível para condomínios em todos os bancos",
            "data": "02/04/2026",
            "resumo": "Recebimento de cotas via Pix QR estático foi liberado para CNPJ de condomínio em todos os bancos brasileiros. Tarifa zero, conciliação automática e baixa em segundos.",
            "fonte": "Banco Central · Comunicado 2026/03",
        },
        {
            "badge": "Mercado",
            "titulo": "Síndicos profissionais já gerenciam 38% dos prédios na Grande SP",
            "data": "abril/2026",
            "resumo": "Crescimento de 6 pontos em 2 anos. Conselheiros voluntários ainda predominam em prédios menores; profissionalização cresce com gestão remota e exigências regulatórias.",
            "fonte": "ABADI · Pesquisa 2026",
        },
        {
            "badge": "Legislação",
            "titulo": "Lei municipal exige sinalização tátil em entradas de prédios novos",
            "data": "29/03/2026",
            "resumo": "Capital paulista regulamenta a Lei 18.097/26: novos prédios e reformas estruturais devem incluir piso podotátil e sinalização em braille no hall e elevadores.",
            "fonte": "Prefeitura SP · DOM 29/03",
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
    section = News()
    errors = section.validate(DEFAULT_INPUTS)
    if errors: print(f"✗ {errors}"); sys.exit(1)
    print(f"✓ {section.label} validada · {section.paginate(DEFAULT_INPUTS)} pág")

    print("\n[A4]")
    html = render_html(section, theme, DEFAULT_INPUTS)
    (out_dir / "news_a4.html").write_text(html, encoding="utf-8")
    print(f"  ✓ HTML  → tmp_preview/news_a4.html")
    pdf_path = out_dir / "news_a4.pdf"
    if html_to_pdf(html, pdf_path):
        print(f"  ✓ PDF   → {pdf_path} ({pdf_path.stat().st_size//1024}KB)")
        png_path = out_dir / "news_a4.png"
        if pdf_to_png(pdf_path, png_path):
            print(f"  ✓ PNG   → {png_path}")


if __name__ == "__main__":
    main()
