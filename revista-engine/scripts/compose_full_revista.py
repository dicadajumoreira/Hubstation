"""
Compose full revista — assembly all 16 sections em 1 PDF.

Ordem editorial (Doc 01 §4):
  1. S01  Capa
  2. S02  Carta do Síndico
  3. S03  Agenda Cultural
  4. S04  Matéria de Capa
  5. S05  Dicas Práticas
  6. S06  Curiosidades do Setor
  7. S07  Novidades e Legislação
  8. S08  Nosso Condomínio — Manutenções (2 págs: abertura + cards)
  9. S09  Nosso Condomínio — Eventos
  10. S10 Receita do Mês
  11. S11 Nossos Números
  12. S12 Advertências e Multas
  13. S12B Vida Condominial
  14. S13 Signos do Mês
  15. S14 Expediente
  16. S15 Contracapa
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.theme import load_theme
from engine.sections import (
    BackCover, Colophon, Cover, CoverStory, CulturalAgenda, Horoscope,
    IndustryFacts, Letter, LifestyleArticle, News, OurCondoEvents,
    OurCondoMaintenance, OurNumbers, Recipe, Tips, Warnings,
)

# Import test inputs from each preview script
BACK_COVER_DEFAULT = {"proxima_edicao_label": "Próxima edição: maio 2026"}
from scripts.preview_colophon import DEFAULT_INPUTS as COLOPHON_DEFAULT       # type: ignore
from scripts.preview_cover import DEFAULT_INPUTS as COVER_DEFAULT             # type: ignore
from scripts.preview_cover_story import DEFAULT_INPUTS as COVER_STORY_DEFAULT  # type: ignore
from scripts.preview_cultural_agenda import DEFAULT_INPUTS as AGENDA_DEFAULT   # type: ignore
from scripts.preview_horoscope import DEFAULT_INPUTS as HOROSCOPE_DEFAULT     # type: ignore
from scripts.preview_industry_facts import DEFAULT_INPUTS as INDUSTRY_DEFAULT  # type: ignore
from scripts.preview_letter import DEFAULT_INPUTS as LETTER_DEFAULT           # type: ignore
from scripts.preview_lifestyle_article import DEFAULT_INPUTS as LIFE_DEFAULT  # type: ignore
from scripts.preview_news import DEFAULT_INPUTS as NEWS_DEFAULT               # type: ignore
from scripts.preview_our_condo_events import DEFAULT_INPUTS as EVENTS_DEFAULT  # type: ignore
from scripts.preview_our_condo_maintenance import DEFAULT_INPUTS as MAINT_DEFAULT  # type: ignore
from scripts.preview_our_numbers import DEFAULT_INPUTS as NUMBERS_DEFAULT     # type: ignore
from scripts.preview_recipe import DEFAULT_INPUTS as RECIPE_DEFAULT           # type: ignore
from scripts.preview_tips import DEFAULT_INPUTS as TIPS_DEFAULT               # type: ignore
from scripts.preview_warnings import DEFAULT_INPUTS as WARNINGS_DEFAULT       # type: ignore


# Ordem editorial canônica
SEQUENCE = [
    ("S01 Capa",                   Cover(),                  COVER_DEFAULT),
    ("S02 Carta do Síndico",       Letter(),                 LETTER_DEFAULT),
    ("S03 Agenda Cultural",        CulturalAgenda(),         AGENDA_DEFAULT),
    ("S04 Matéria de Capa",        CoverStory(),             COVER_STORY_DEFAULT),
    ("S05 Dicas Práticas",         Tips(),                   TIPS_DEFAULT),
    ("S06 Curiosidades",           IndustryFacts(),          INDUSTRY_DEFAULT),
    ("S07 Novidades e Legislação", News(),                   NEWS_DEFAULT),
    ("S08 Manutenções",            OurCondoMaintenance(),    MAINT_DEFAULT),
    ("S09 Eventos",                OurCondoEvents(),         EVENTS_DEFAULT),
    ("S10 Receita do Mês",         Recipe(),                 RECIPE_DEFAULT),
    ("S11 Nossos Números",         OurNumbers(),             NUMBERS_DEFAULT),
    ("S12 Advertências e Multas",  Warnings(),               WARNINGS_DEFAULT),
    ("S12B Vida Condominial",      LifestyleArticle(),       LIFE_DEFAULT),
    ("S13 Signos do Mês",          Horoscope(),              HOROSCOPE_DEFAULT),
    ("S14 Expediente",             Colophon(),               COLOPHON_DEFAULT),
    ("S15 Contracapa",             BackCover(),              BACK_COVER_DEFAULT),
]


def compose_html(theme) -> tuple[str, list[tuple[str, int]]]:
    """Concatena bodies de todas as seções num doc HTML único.
    Retorna (html, [(label, num_pages), ...])."""
    bodies = []
    page_log = []

    for label, section, inputs in SEQUENCE:
        errors = section.validate(inputs)
        if errors:
            print(f"  ⚠ {label}: validação tem warnings: {errors}")
        section_bodies = section.render_a4(inputs, theme)
        bodies.extend(section_bodies)
        page_log.append((label, len(section_bodies)))
        print(f"  ✓ {label} · {len(section_bodies)} pág")

    full_html = theme.page_document("\n".join(bodies), format="a4")
    return full_html, page_log


def html_to_pdf(html: str, pdf_path: Path) -> bool:
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
        return True
    except Exception:
        import traceback; traceback.print_exc()
        return False


def pdf_to_thumbnails(pdf_path: Path, out_dir: Path, dpi: int = 80) -> list[Path]:
    """Renderiza cada página do PDF como PNG thumbnail."""
    if not shutil.which("pdftoppm"):
        return []
    prefix = out_dir / "thumb"
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(prefix)],
        check=True, capture_output=True,
    )
    return sorted(out_dir.glob("thumb-*.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tmp_preview")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Compondo revista completa…")
    theme = load_theme()
    print(f"✓ Tema {theme.nome} carregado")

    print(f"\nMontando {len(SEQUENCE)} seções:")
    html, page_log = compose_html(theme)

    total_pages = sum(n for _, n in page_log)
    print(f"\n📑 Total: {total_pages} páginas")

    html_path = out_dir / "revista_completa.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"✓ HTML  → {html_path} ({len(html)//1024}KB)")

    pdf_path = out_dir / "revista_completa.pdf"
    if html_to_pdf(html, pdf_path):
        size_kb = pdf_path.stat().st_size // 1024
        print(f"✓ PDF   → {pdf_path} ({size_kb}KB) · {total_pages} páginas")

        # Thumbnails para preview rápido
        thumbs_dir = out_dir / "thumbs_revista"
        if thumbs_dir.exists():
            shutil.rmtree(thumbs_dir)
        thumbs_dir.mkdir()
        thumbs = pdf_to_thumbnails(pdf_path, thumbs_dir)
        print(f"✓ Thumbs → {len(thumbs)} arquivos em {thumbs_dir}/")


if __name__ == "__main__":
    main()
