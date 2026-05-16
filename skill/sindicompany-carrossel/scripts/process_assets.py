#!/usr/bin/env python3
"""
process_assets.py — Setup único (rodar 1x antes do primeiro carrossel).

Os PNGs em /mnt/project/ estão em modo RGB sem canal alfa (fundo preto sólido).
Esse script gera versões RGBA com fundo transparente dentro da skill,
usando luminância como alpha. Também gera um LOGO_ESCURO limpo derivando a
forma do LOGO_CLARO e recolorindo em onix (o Logotipo_Sindicompany_6.png
original é onix sobre preto, luminância não separa os dois).

Uso:
    python3 scripts/process_assets.py

Resultado: assets_processed/ com todos os PNGs prontos para uso.
"""
from PIL import Image
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
SRC = '/mnt/project'
DST = os.path.join(SKILL_ROOT, 'assets_processed')
os.makedirs(DST, exist_ok=True)

ONIX = (26, 28, 41)

def black_to_alpha(src_path, dst_path):
    """RGB com fundo preto → RGBA. Alpha = max(r,g,b)."""
    im = Image.open(src_path).convert('RGB')
    w, h = im.size
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sp, op = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = sp[x, y]
            op[x, y] = (r, g, b, max(r, g, b))
    out.save(dst_path, 'PNG')

def black_to_alpha_binary(src_path, dst_path, threshold=15):
    """RGB com fundo preto → RGBA com alpha BINÁRIO.
    Pixels com max(r,g,b) < threshold viram totalmente transparentes.
    Demais ficam totalmente opacos.

    Usado para PATTERNS: evita pixels semi-transparentes que geram
    borda fantasma quando o pattern é renderizado em opacidade full
    sobre o slide. Os patterns têm áreas cinzas que devem aparecer
    como cinza sólido, não semi-translúcidas.
    """
    im = Image.open(src_path).convert('RGB')
    w, h = im.size
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sp, op = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = sp[x, y]
            if max(r, g, b) < threshold:
                op[x, y] = (0, 0, 0, 0)
            else:
                op[x, y] = (r, g, b, 255)
    out.save(dst_path, 'PNG')

def pattern_to_accents(src_path, dst_path):
    """Processa um Pattern_Decorativo extraindo APENAS as formas coloridas
    de destaque (mint/sand/lavender/branco), descartando o fundo preto E
    as formas onix-escuras que criariam "borda fantasma" sobre o slide.

    Critério: pixel é considerado destaque se for claramente colorido
    (cor saturada como mint/sand/lavender) ou claro (branco/quase-branco).
    Pixels escuros (max < 80) viram totalmente transparentes.

    Após o thresholding:
    1. Aplica um crop interno de 8px nas bordas pra eliminar bordas residuais
    2. Detecta e zera colunas/linhas com >90% de pixels sólidos (faixas
       verticais/horizontais decorativas que aparecem como riscos no slide)

    Resultado: o pattern aparece como acentos coloridos flutuando sobre
    o slide, sem retângulos escuros, sem bordas geométricas e sem
    riscos verticais residuais.
    """
    im = Image.open(src_path).convert('RGB')
    w, h = im.size
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sp, op = im.load(), out.load()
    DARK_THRESHOLD = 80
    EDGE_CROP = 8
    LINE_RATIO = 0.90  # > 90% pixels sólidos numa coluna/linha = é uma linha decorativa, descartar

    # Passo 1: thresholding + edge crop
    for y in range(h):
        for x in range(w):
            if x < EDGE_CROP or x >= w - EDGE_CROP or y < EDGE_CROP or y >= h - EDGE_CROP:
                op[x, y] = (0, 0, 0, 0)
                continue
            r, g, b = sp[x, y]
            if max(r, g, b) < DARK_THRESHOLD:
                op[x, y] = (0, 0, 0, 0)
            else:
                op[x, y] = (r, g, b, 255)

    # Passo 2: detectar colunas com >LINE_RATIO de pixels sólidos e zerar
    threshold_count_v = int(h * LINE_RATIO)
    for x in range(w):
        col_count = sum(1 for y in range(h) if op[x, y][3] > 0)
        if col_count > threshold_count_v:
            for y in range(h):
                op[x, y] = (0, 0, 0, 0)

    # Passo 3: mesma coisa para linhas horizontais
    threshold_count_h = int(w * LINE_RATIO)
    for y in range(h):
        row_count = sum(1 for x in range(w) if op[x, y][3] > 0)
        if row_count > threshold_count_h:
            for x in range(w):
                op[x, y] = (0, 0, 0, 0)

    out.save(dst_path, 'PNG')

def recolor_logo_from_claro(src_claro_path, dst_path, color_rgb):
    """Usa a forma do LOGO_CLARO (branco em preto) e recolore para color_rgb.
    Resultado: logo na cor desejada sobre fundo transparente."""
    im = Image.open(src_claro_path).convert('RGB')
    w, h = im.size
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sp, op = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = sp[x, y]
            a = max(r, g, b)  # luminância = onde o logo está
            op[x, y] = (*color_rgb, a)
    out.save(dst_path, 'PNG')

ASSETS = [
    # Icons
    'Logotipo_Sindicompany__Icon_1.png',
    'Logotipo_Sindicompany__Icon_2.png',
    'Logotipo_Sindicompany__Icon_3.png',
    'Logotipo_Sindicompany__Icon_4.png',
    'Logotipo_Sindicompany__Icon_5.png',
    'Logotipo_Sindicompany__Icon_6.png',
    # Patterns canto
    'Pattern_Canto_1__Azul.png',
    'Pattern_Canto_1__Azul_Claro.png',
    'Pattern_Canto_1__Bege.png',
    'Pattern_Canto_1__Roxo_Claro.png',
    'Pattern_Canto_1__Roxo_Escuro.png',
    # Patterns criativos (lateral)
    'Pattern_Criativos_Direito__1.png',
    'Pattern_Criativos_Direito_Bege__1.png',
    'Pattern_Criativos_Direito_Roxo__3.png',
    'Pattern_Criativos_Esquerdo__1.png',
    'Pattern_Criativos_Esquerdo_Bege__1.png',
    'Pattern_Criativos_Esquerdo_Roxo__1.png',
    # Patterns decorativos
    'Pattern_Decorativo_Azul_Escuro___1.png',
    'Pattern_Decorativo_Azul_Escuro___2.png',
    'Pattern_Decorativo_Roxo___1.png',
    'Pattern_Decorativo_Roxo___2.png',
    'Pattern_Decorativo__Bege.png',
    'Pattern_Decorativo__Bege__2.png',
    # Patterns fundo
    'Pattern_Fundo_1.png',
    'Pattern_Fundo_2.png',
]

def main():
    if not os.path.isdir(SRC):
        print(f'ERRO: {SRC} não existe. Abortando.', file=sys.stderr)
        sys.exit(1)

    count = 0
    for filename in ASSETS:
        src = os.path.join(SRC, filename)
        if not os.path.exists(src):
            print(f'  SKIP {filename} (não encontrado)')
            continue
        dst = os.path.join(DST, filename)
        # Pattern_Decorativo E Pattern_Canto usam "pattern_to_accents" — extrai
        # só os acentos coloridos descartando áreas escuras E pixels anti-aliased
        # que criariam borda fantasma. Outros patterns usam binary alpha.
        # Icons usam luminance alpha.
        if filename.startswith('Pattern_Decorativo') or filename.startswith('Pattern_Canto'):
            pattern_to_accents(src, dst)
            mode = 'pattern (accents only)'
        elif filename.startswith('Pattern_'):
            black_to_alpha_binary(src, dst)
            mode = 'pattern (binary alpha)'
        else:
            black_to_alpha(src, dst)
            mode = 'icon (luminance alpha)'
        print(f'  OK   {filename}  [{mode}]')
        count += 1

    # Logos: derivar ambos a partir do Logotipo_Sindicompany_5.png
    # (que é white-on-black, a única fonte confiável da forma do logo)
    logo5_src = os.path.join(SRC, 'Logotipo_Sindicompany_5.png')
    if not os.path.exists(logo5_src):
        print(f'ERRO: {logo5_src} não encontrado. Logos não gerados.', file=sys.stderr)
        sys.exit(1)

    recolor_logo_from_claro(
        logo5_src,
        os.path.join(DST, 'Logotipo_Sindicompany_5.png'),
        (255, 255, 255),
    )
    print('  OK   Logotipo_Sindicompany_5.png (LOGO_CLARO recolorido para branco)')
    count += 1

    recolor_logo_from_claro(
        logo5_src,
        os.path.join(DST, 'Logotipo_Sindicompany_6.png'),
        ONIX,
    )
    print('  OK   Logotipo_Sindicompany_6.png (LOGO_ESCURO derivado e recolorido para onix)')
    count += 1

    print(f'\n✓ {count} assets processados em: {DST}')

if __name__ == '__main__':
    main()
