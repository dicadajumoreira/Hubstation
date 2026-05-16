#!/usr/bin/env python3
"""
helpers.py — Funções compartilhadas para gerar carrosséis da Sindicompany.

Uso típico num script de build:

    from helpers import *

    logos = load_logos()
    fonts_css = build_font_faces()
    slide1 = make_cover_slide(
        headline="Seu título aqui, <span class='hl-mint'>com highlight</span>",
        badge="HISTÓRIA REAL",
        hero_image_b64=imagem_capa_b64,
        logos=logos,
        dots_active=0, dots_total=6,
    )
    # ... mais slides ...
    html = wrap_html([slide1, slide2, ...], fonts_css, legenda)
"""
import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
ASSETS_DIR = os.path.join(SKILL_ROOT, 'assets_processed')
FONTS_DIR = os.path.join(SKILL_ROOT, 'assets', 'fonts')


def asset_b64(filename, directory=None):
    """Lê arquivo e retorna como data URI base64."""
    directory = directory or ASSETS_DIR
    path = os.path.join(directory, filename)
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    ext = filename.rsplit('.', 1)[-1].lower()
    mime = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'woff2': 'font/woff2',
    }.get(ext, f'image/{ext}')
    return f'data:{mime};base64,{data}'


def load_logos():
    """Retorna dict com LOGO_CLARO e LOGO_ESCURO (já processados, com alpha)."""
    return {
        'LOGO_CLARO':  asset_b64('Logotipo_Sindicompany_5.png'),
        'LOGO_ESCURO': asset_b64('Logotipo_Sindicompany_6.png'),
    }


def load_patterns():
    """Retorna dict com patterns comuns (já processados)."""
    return {
        'PATTERN_ESQ_MINT':  asset_b64('Pattern_Criativos_Esquerdo__1.png'),
        'PATTERN_DIR_MINT':  asset_b64('Pattern_Criativos_Direito__1.png'),
        'PATTERN_ESQ_BEGE':  asset_b64('Pattern_Criativos_Esquerdo_Bege__1.png'),
        'PATTERN_DIR_BEGE':  asset_b64('Pattern_Criativos_Direito_Bege__1.png'),
    }


def load_all_icons():
    """Retorna dict com TODOS os 6 icons (processados com alpha).
    Use para aplicar a regra obrigatória de icon de fundo em cada slide."""
    return {
        f'ICON_{i}': asset_b64(f'Logotipo_Sindicompany__Icon_{i}.png')
        for i in range(1, 7)
    }


def load_icons():
    """Retorna dict com icons comuns (já processados)."""
    return {
        'ICON_MINT': asset_b64('Logotipo_Sindicompany__Icon_2.png'),
        'ICON_SAND': asset_b64('Logotipo_Sindicompany__Icon_1.png'),
        'ICON_ONIX': asset_b64('Logotipo_Sindicompany__Icon_5.png'),
    }


def background_icon(all_icons, slide_index, light_bg=False):
    """REGRA INEGOCIÁVEL DA SKILL: cada slide do carrossel precisa ter um
    dos Icon_1 a _6 no fundo. Essa função gera o markup <img> do icon de fundo,
    ciclando pelos 6 icons conforme o índice do slide.

    Args:
        all_icons: dict retornado por load_all_icons()
        slide_index: índice 0-based do slide no carrossel
        light_bg: True se o slide tem fundo claro (claro, sand, lavender)
                  — aplica filter:brightness(0) para renderizar em preto

    Returns:
        String HTML com o <img class='icon-bg'>.
    """
    icon_num = (slide_index % 6) + 1  # cicla 1..6
    icon_src = all_icons[f'ICON_{icon_num}']
    classes = 'icon-bg' + (' light-bg' if light_bg else '')
    return f'<img src="{icon_src}" class="{classes}" alt="" data-icon="{icon_num}">'


def build_font_faces():
    """Gera @font-face CSS com Epilogue embutida em base64 (sem dependência de rede)."""
    faces = []
    for weight in (400, 600, 700, 800, 900):
        path = os.path.join(FONTS_DIR, f'epilogue-{weight}.woff2')
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        faces.append(f"""
@font-face {{
  font-family: 'Epilogue';
  font-style: normal;
  font-weight: {weight};
  font-display: block;
  src: url(data:font/woff2;base64,{data}) format('woff2');
}}""")
    return '\n'.join(faces)


def dots(active, total=6):
    """Navegação de dots na base do slide."""
    return '<div class="dots">' + ''.join(
        f'<span class="dot{" active" if i == active else ""}"></span>'
        for i in range(total)
    ) + '</div>'


def header(logos, on_dark=True):
    """Header bar com logo correto e handle."""
    logo = logos['LOGO_CLARO'] if on_dark else logos['LOGO_ESCURO']
    return f'''<div class="header-bar">
      <img src="{logo}" alt="sindicompany" class="header-logo">
      <span class="header-handle">@sindicompanybr</span>
    </div>'''


def load_all_icons():
    """Carrega os icons casinha LIMPOS (geométricos, sem fotos sobrepostas).

    Os icons 3 e 4 do projeto contêm fotos/avatares dentro da casinha
    e não funcionam como decoração de fundo. Excluídos.

    Retorna dict separado por compatibilidade de fundo:
        'dark':  [icon1_sand, icon2_mint, icon6_white]  para slides escuros
        'light': [icon5_onix]                            para slides claros
    """
    return {
        'dark': [
            asset_b64('Logotipo_Sindicompany__Icon_1.png'),  # sand
            asset_b64('Logotipo_Sindicompany__Icon_2.png'),  # mint
            asset_b64('Logotipo_Sindicompany__Icon_6.png'),  # white
        ],
        'light': [
            asset_b64('Logotipo_Sindicompany__Icon_5.png'),  # onix
        ],
    }


def background_icon(all_icons, slide_index, light_bg=False):
    """REGRA INEGOCIÁVEL: todo slide (exceto a capa) tem um icon casinha
    sutil no fundo.

    Em slides escuros, cicla entre 3 variações (sand, mint, white) pelo
    índice do slide. Em slides claros, usa sempre o icon onix (única
    variação compatível com fundo claro).

    Renderiza grande, ancorado embaixo à direita, atrás do conteúdo (z-index:0),
    com opacidade muito baixa pra funcionar como assinatura visual sem competir.
    """
    if light_bg:
        icon = all_icons['light'][0]
        cls = 'background-icon on-light'
    else:
        pool = all_icons['dark']
        icon = pool[slide_index % len(pool)]
        cls = 'background-icon'
    return f'<img src="{icon}" alt="" class="{cls}">'


def cover_icon_stamp(all_icons, variant='mint'):
    """REGRA INEGOCIÁVEL: a CAPA tem uma das casinhas Icon_1 a _6 no canto
    inferior direito, em opacidade FULL (sem transparência) — como um selo
    de marca sobre a foto.

    Por padrão usa o Icon_2 (mint), que harmoniza com a paleta da marca
    sobre fundos escuros. Pode ser trocado pelo argumento `variant`:
        'mint'  → Icon_2 (default, mais brand)
        'sand'  → Icon_1
        'white' → Icon_6
    """
    pool = all_icons['dark']
    idx = {'sand': 0, 'mint': 1, 'white': 2}.get(variant, 1)
    icon = pool[idx]
    return f'<img src="{icon}" alt="" class="cover-icon-stamp">'


def load_decorative_patterns():
    """Carrega os 6 Pattern_Decorativo (Azul_Escuro 1/2, Roxo 1/2, Bege 1/2).

    Cada pattern é um composição vertical com formas geométricas.
    Agrupados por cor pra escolha automática conforme o tipo de fundo do slide.
    """
    return {
        'azul_escuro': [
            asset_b64('Pattern_Decorativo_Azul_Escuro___1.png'),  # estreito
            asset_b64('Pattern_Decorativo_Azul_Escuro___2.png'),  # largo
        ],
        'roxo': [
            asset_b64('Pattern_Decorativo_Roxo___1.png'),
            asset_b64('Pattern_Decorativo_Roxo___2.png'),
        ],
        'bege': [
            asset_b64('Pattern_Decorativo__Bege.png'),
            asset_b64('Pattern_Decorativo__Bege__2.png'),
        ],
    }


def load_pattern_canto():
    """Carrega os 5 Pattern_Canto (Azul, Azul_Claro, Bege, Roxo_Claro, Roxo_Escuro).

    Cada pattern é um quadrado 504×504 com formas geométricas circulares
    decorativas. Organizados por cor para escolha automática pelo tipo
    de fundo do slide.
    """
    return {
        'azul':        asset_b64('Pattern_Canto_1__Azul.png'),         # onix escuro
        'azul_claro':  asset_b64('Pattern_Canto_1__Azul_Claro.png'),   # mint
        'bege':        asset_b64('Pattern_Canto_1__Bege.png'),         # sand
        'roxo_claro':  asset_b64('Pattern_Canto_1__Roxo_Claro.png'),   # lavender claro
        'roxo_escuro': asset_b64('Pattern_Canto_1__Roxo_Escuro.png'),  # lavender escuro
    }


def corner_pattern(cantos, slide_type='escuro'):
    """REGRA INEGOCIÁVEL: todo slide (exceto a capa) tem um Pattern_Canto
    no canto superior direito como elemento decorativo de marca.

    Escolhe a cor pelo tipo de fundo:
        - escuro/cta → azul_claro (mint, contraste sobre onix)
        - claro      → azul (onix, contraste sobre gray-5)
        - sand       → roxo_escuro (contraste sobre sand)
        - lavender   → roxo_escuro

    O elemento é renderizado com transparência aplicada (regra inegociável
    de imagens de fundo) e rotacionado 180° pra ancorar no canto direito superior.
    """
    color_map = {
        'escuro':   'azul_claro',
        'cta':      'azul_claro',
        'claro':    'azul',
        'sand':     'roxo_escuro',
        'lavender': 'roxo_escuro',
    }
    color = color_map.get(slide_type, 'azul_claro')
    return f'<img src="{cantos[color]}" alt="" class="corner-pattern">'


def background_pattern(patterns, slide_index, slide_type='escuro'):
    """REGRA INEGOCIÁVEL: todo slide (exceto capa) tem um Pattern_Decorativo
    no fundo, ancorado à esquerda, atrás do conteúdo.

    Escolhe a cor do pattern automaticamente pelo tipo de fundo:
        - escuro/cta → roxo (formas lavender, mais sutis)
        - claro      → bege (formas sand)
        - sand       → bege
        - lavender   → roxo

    Cicla entre as 2 variações (estreita/larga) pelo índice do slide.
    """
    color_map = {
        'escuro':   'roxo',
        'cta':      'roxo',
        'claro':    'bege',
        'sand':     'bege',
        'lavender': 'roxo',
    }
    color = color_map.get(slide_type, 'roxo')
    pool = patterns[color]
    pat = pool[slide_index % len(pool)]
    return f'<img src="{pat}" alt="" class="background-pattern">'


def load_decorativo_patterns():
    """Carrega os 6 Pattern_Decorativo, separados por compatibilidade de fundo.

    Patterns são strips verticais geométricos. Aplicados como segunda
    assinatura visual (junto com o background_icon).
    """
    return {
        'dark': [
            asset_b64('Pattern_Decorativo_Azul_Escuro___1.png'),
            asset_b64('Pattern_Decorativo_Azul_Escuro___2.png'),
            asset_b64('Pattern_Decorativo_Roxo___1.png'),
            asset_b64('Pattern_Decorativo_Roxo___2.png'),
        ],
        'light': [
            asset_b64('Pattern_Decorativo__Bege.png'),
            asset_b64('Pattern_Decorativo__Bege__2.png'),
        ],
    }


def base_css(fonts_css):
    """CSS base para todos os carrosséis. Inclui fontes, paleta, tipografia,
    tipos de slide (capa, escuro, claro, sand, cta) e patterns decorativos."""
    return fonts_css + """

:root{
  --onix:#1A1C29; --sand:#DABDA9; --mint:#84C7D3; --lavender:#B8C0FF;
  --white:#FFFFFF; --gray-5:#F4F4F5;
}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Epilogue',sans-serif;}
body{
  font-family:'Epilogue',sans-serif;background:#0d0d0d;
  display:flex;flex-direction:column;align-items:center;
  padding:40px 20px;gap:40px;
}
.slide{
  width:1080px;height:1350px;position:relative;overflow:hidden;
  display:flex;flex-direction:column;
  box-shadow:0 30px 80px rgba(0,0,0,0.5);
  font-family:'Epilogue',sans-serif;
}

/* Tipos de fundo */
.escuro,.cta{background:var(--onix);color:var(--white);}
.claro{background:var(--gray-5);color:var(--onix);}
.sand{background:var(--sand);color:var(--onix);}
.lavender{background:var(--lavender);color:var(--onix);}

/* Header bar */
.header-bar{
  display:flex;justify-content:space-between;align-items:center;
  padding:42px 64px;z-index:10;position:relative;
}
.header-logo{height:46px;width:auto;object-fit:contain;display:block;}
.header-handle{
  font-family:'Epilogue',sans-serif;font-size:20px;font-weight:500;
  opacity:0.6;letter-spacing:0.5px;color:var(--white);
}
.claro .header-handle,.sand .header-handle,.lavender .header-handle{
  color:var(--onix);opacity:0.55;
}

/* Slide content */
.slide-content{position:relative;z-index:5;flex:1;display:flex;flex-direction:column;}
.padded{padding:40px 72px 130px;justify-content:center;gap:32px;}

/* Tipografia */
.titulo-capa{
  font-family:'Epilogue',sans-serif;font-weight:900;font-size:78px;line-height:1.04;
  letter-spacing:-0.025em;color:var(--white);
}
.titulo-slide{
  font-family:'Epilogue',sans-serif;font-weight:800;font-size:78px;line-height:1.06;
  letter-spacing:-0.02em;color:var(--white);
}
.titulo-slide.dark{color:var(--onix);}
.texto-principal{
  font-family:'Epilogue',sans-serif;font-weight:600;font-size:46px;line-height:1.32;
  color:rgba(255,255,255,0.88);
}
.texto-principal.dark{color:var(--onix);}
.texto-principal.destaque-mint{color:var(--mint);font-weight:700;}
.texto-principal.destaque-sand{color:var(--sand);font-weight:700;}
.texto-secundario{
  font-family:'Epilogue',sans-serif;font-weight:400;font-size:34px;line-height:1.45;
  color:rgba(255,255,255,0.72);
}
.texto-secundario.dark{color:rgba(26,28,41,0.78);}

.hl-mint{color:var(--mint);}
.hl-sand{color:var(--sand);}
.hl-lavender{color:var(--lavender);}

.badge{
  font-family:'Epilogue',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:5px;text-transform:uppercase;
  color:var(--mint);align-self:flex-start;
}
.badge.dark{color:var(--onix);opacity:0.65;}

/* CAPA — texto SEMPRE na metade de baixo, foto livre em cima */
.capa{background:var(--onix);}
.hero-img{
  position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  object-position:center 30%;z-index:0;
}
.hero-overlay{
  position:absolute;inset:0;z-index:1;
  background:linear-gradient(to top,
    rgba(26,28,41,0.97) 0%,
    rgba(26,28,41,0.92) 40%,
    rgba(26,28,41,0.55) 50%,
    rgba(26,28,41,0.12) 65%,
    rgba(26,28,41,0.05) 100%);
}
.capa .header-bar{z-index:10;}
.capa-content{
  position:absolute;top:50%;left:0;right:0;bottom:0;
  padding:40px 72px 130px;
  display:flex;flex-direction:column;justify-content:flex-end;
  gap:30px;z-index:5;
}
.capa .titulo-capa{
  max-width:780px; /* deixa espaço pro cover-icon-stamp à direita */
}
.badge-capa{
  font-family:'Epilogue',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:6px;text-transform:uppercase;color:var(--mint);
  align-self:flex-start;
  padding:14px 22px;border:2px solid var(--mint);border-radius:4px;
}

/* Lista numerada (slides tipo "virada") */
.lista-acoes{list-style:none;display:flex;flex-direction:column;gap:36px;margin-top:8px;}
.lista-acoes li{
  display:flex;gap:32px;align-items:flex-start;
  font-family:'Epilogue',sans-serif;font-weight:500;font-size:42px;line-height:1.32;
  color:rgba(255,255,255,0.92);
}
.lista-acoes li strong{font-weight:800;color:var(--white);}
.lista-acoes .num{
  font-family:'Epilogue',sans-serif;font-weight:900;font-size:62px;line-height:1;
  color:var(--mint);min-width:70px;letter-spacing:-0.04em;
}

/* CTA */
.cta-content{padding:60px 72px 140px;justify-content:center;gap:38px;}
.cta-marca{
  font-family:'Epilogue',sans-serif;font-weight:800;font-size:32px;
  letter-spacing:10px;text-transform:lowercase;color:var(--mint);
}
.titulo-cta{
  font-family:'Epilogue',sans-serif;font-weight:900;font-size:84px;line-height:1.04;
  letter-spacing:-0.02em;color:var(--white);
}
.pergunta-box{
  margin-top:18px;padding:36px 0;
  border-top:2px solid rgba(132,199,211,0.3);
  border-bottom:2px solid rgba(132,199,211,0.3);
}
.pergunta{
  font-family:'Epilogue',sans-serif;font-weight:700;font-size:42px;line-height:1.25;
  color:var(--white);
}
.pergunta-sub{
  font-family:'Epilogue',sans-serif;font-weight:400;font-size:32px;
  color:rgba(255,255,255,0.75);margin-top:10px;
}
.pergunta-sub strong{color:var(--mint);font-weight:800;}
.tagline{
  font-family:'Epilogue',sans-serif;font-weight:400;font-style:italic;
  font-size:26px;color:var(--sand);margin-top:18px;letter-spacing:0.5px;
}

/* Dots */
.dots{
  display:flex;gap:12px;justify-content:center;
  position:absolute;bottom:50px;left:50%;transform:translateX(-50%);
  z-index:10;
}
.dot{width:10px;height:10px;border-radius:50%;background:rgba(255,255,255,0.3);transition:all .3s;}
.dot.active{background:var(--mint);width:32px;border-radius:5px;}
.claro .dot,.sand .dot,.lavender .dot{background:rgba(26,28,41,0.25);}
.claro .dot.active,.sand .dot.active,.lavender .dot.active{background:var(--onix);}

/* Patterns decorativos (assets já com alpha — sem blend mode) */
.pattern-lateral{
  position:absolute;top:0;height:100%;width:55%;max-width:620px;
  object-fit:contain;opacity:0.18;pointer-events:none;z-index:1;
}
.pattern-lateral.esquerdo{left:0;object-position:left center;}
.pattern-lateral.direito{right:0;object-position:right center;}

/* Background icon — REGRA INEGOCIÁVEL: presente em TODOS os slides
   como assinatura visual sutil da marca. Cicla entre os 6 icons. */
.background-icon{
  position:absolute;
  right:-180px;bottom:-120px;
  width:780px;height:auto;
  opacity:0.07;
  pointer-events:none;
  z-index:0;
}
.background-icon.on-light{opacity:0.06;}
.cta .background-icon{opacity:0.08;}

/* Cover icon stamp — REGRA INEGOCIÁVEL: na CAPA, uma das casinhas Icon_1 a _6
   aparece no canto inferior direito em opacidade FULL (sem transparência),
   como selo de marca sobre a foto. Posicionado pra não competir com o título
   nem com os dots. */
.cover-icon-stamp{
  position:absolute;
  bottom:90px;right:50px;
  width:170px;height:auto;
  opacity:1;
  pointer-events:none;
  z-index:6;
}

/* Background pattern decorativo — REGRA INEGOCIÁVEL: presente em todos os
   slides exceto a capa. Pattern_Decorativo posicionado como acento de canto
   inferior esquerdo com bleed off-screen, pra não competir com o texto.
   SEMPRE com opacidade reduzida (regra inegociável: imagens de fundo
   sempre com transparência aplicada). */
.background-pattern{
  position:absolute;
  left:-90px;bottom:-80px;
  height:520px;width:auto;
  object-fit:contain;object-position:left bottom;
  opacity:0.20;
  pointer-events:none;
  z-index:0;
}

/* Corner pattern — REGRA INEGOCIÁVEL: Pattern_Canto no canto superior direito
   de todo slide (exceto a capa). Rotacionado 180° pra que as formas circulares
   "saiam" do canto. SEMPRE com transparência aplicada (regra de imagens de fundo). */
.corner-pattern{
  position:absolute;
  top:-60px;right:-60px;
  width:340px;height:340px;
  transform:rotate(180deg);
  opacity:0.18;
  pointer-events:none;
  z-index:0;
}

.capa .background-pattern{display:none;}

/* Legenda Instagram */
.legenda-wrap{
  width:1080px;background:#1a1a1a;border:1px solid #2a2a2a;
  border-radius:12px;padding:48px;margin-top:20px;color:#e8e8e8;
  font-family:'Epilogue',sans-serif;
}
.legenda-wrap h3{
  font-size:18px;font-weight:700;letter-spacing:3px;
  text-transform:uppercase;color:var(--mint);margin-bottom:24px;
}
.legenda-wrap pre{
  font-family:'Epilogue',sans-serif;font-size:18px;line-height:1.65;
  white-space:pre-wrap;word-wrap:break-word;color:#d4d4d4;
}
"""


def wrap_html(slides_html_list, fonts_css, legenda, title='Carrossel Sindicompany'):
    """Monta HTML completo autocontido."""
    css = base_css(fonts_css)
    slides_joined = '\n'.join(slides_html_list)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{slides_joined}
<div class="legenda-wrap">
  <h3>Legenda Instagram</h3>
  <pre>{legenda}</pre>
</div>
</body>
</html>
"""
