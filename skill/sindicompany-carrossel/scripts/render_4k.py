#!/usr/bin/env python3
"""
render_4k.py — Renderiza cada .slide de um HTML em PNG 4K individual.

Usa Chromium via Playwright com device_scale_factor=2.844 para produzir
PNGs em 3072×3839 (razão 4:5 do Instagram feed, qualidade 4K vertical).

Uso:
    python3 scripts/render_4k.py <html_path> <output_dir> [prefixo]

Exemplo:
    python3 scripts/render_4k.py \\
        /mnt/user-data/outputs/carrossel_tema.html \\
        /mnt/user-data/outputs \\
        carrossel_tema

Resultado: <prefixo>_slide_N.png para cada slide encontrado.
"""
import os
import sys
from playwright.sync_api import sync_playwright

SCALE = 2.844  # 1080*2.844 ≈ 3072, 1350*2.844 ≈ 3840

def render(html_path, out_dir, prefix='slide'):
    os.makedirs(out_dir, exist_ok=True)
    outputs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={'width': 1080, 'height': 1350},
            device_scale_factor=SCALE,
        )
        page = ctx.new_page()
        page.goto(f'file://{os.path.abspath(html_path)}', wait_until='networkidle')
        # Garantir que as fontes embutidas finalizaram o decode antes do screenshot
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(1500)

        slides = page.query_selector_all('.slide')
        print(f'Slides encontrados: {len(slides)}')
        for i, el in enumerate(slides, start=1):
            out = os.path.join(out_dir, f'{prefix}_{i:02d}.png')
            el.screenshot(path=out, type='png')
            kb = os.path.getsize(out) // 1024
            outputs.append(out)
            print(f'  [{i}] {os.path.basename(out)} ({kb} KB)')

        browser.close()
    return outputs

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    html_path = sys.argv[1]
    out_dir = sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else 'slide'
    render(html_path, out_dir, prefix)

if __name__ == '__main__':
    main()
