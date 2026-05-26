"""
Engine de geração de carrossel Instagram da Sindicompany.

Pipeline:
  1. Lê o registro `carrosseis` no Supabase pelo id
  2. Gera copy estruturada via GPT (N slides com tipo + título + body)
  3. Renderiza HTML por slide com paleta + Epilogue
  4. Playwright captura cada slide como PNG 3072×3839 (4K vertical 4:5)
  5. Sobe os PNGs no bucket público condominios-fotos/__carrosseis/<id>/
  6. Gera legenda Instagram via GPT
  7. Atualiza o registro: png_paths, legenda, status=publicada

Falha em qualquer etapa: marca status=erro com erro_mensagem.

Uso (CLI):
    python -m api.carrossel_generate <carrossel_id>
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import re
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from api import brand_kit
from api.supabase_client import _client as _sb_client
from api.text_gen import _client as _openai_client, MODEL, _gerar_json


# Marca do carrossel atual — setada em main() antes de qualquer
# lookup de asset. Define qual conjunto de buckets/handle/logo usar.
_BRAND = "sindicompanybr"

# Arquetipo de capa do Brand Hub Sindicompany 2026-05-17. Setado em
# gerar_carrossel() a partir do campo carrosseis.cover_archetype.
# Vazio = usa o fallback da env var SINDICOMPANY_COVER_ARCHETYPE
# (legado) ou a capa classica se a env nao estiver setada.
_COVER_ARCHETYPE = ""

# Estilo de paginacao do slide (dots/ticks/bar/index), escolhido UMA vez
# por carrossel em gerar_carrossel pra variar entre carrosseis. Vazio = dots.
_PAGINATION_STYLE = ""

# Estilo de capa (classic/house), escolhido por carrossel. "house" so
# aplica quando ha foto de capa (Sindicompany). Vazio = classic.
_CAPA_STYLE = ""

# Seed do carrossel (id) — usada pra variar a decoracao de pattern por slide.
_CARROSSEL_SEED = ""

# Cor do pattern do carrossel (navy/beige/purple) — varia o feed.
_PATTERN_COLOR = "navy"

# Identidade da marca atual, vinda da tabela `marcas`. Setadas em
# gerar_carrossel() a partir do slug. Para as 3 marcas chumbadas
# (sindicompanybr/bysindicompany/consvictabr) prefixo e handle continuam
# vindo das funcoes hardcoded; estes globais so sao usados por MARCA NOVA.
_BRAND_PALETTE: dict[str, str] | None = None
_BRAND_PREFIX = ""  # bucket_prefix do DB (ex: __minhamarca-)
_BRAND_HANDLE = ""  # handle do DB (ex: @minhamarca)
_BRAND_NAME = ""  # nome de exibicao do DB (ex: Lavandery)
# Tipografia data-driven da marca (coluna marcas.tipografia). Só usada por
# marca nova — as 3 chumbadas seguem com as fontes embutidas. Shape:
# {"display","body","numeric","faces":[{family,weight,style,file}, ...]}
_BRAND_TIPOGRAFIA: dict[str, Any] | None = None


def _asset_prefix() -> str:
    """Prefixo dos buckets de assets conforme a marca:
    - sindicompanybr -> '__'           (ex: __patterns/, __icons/)
    - bysindicompany -> '__by-'        (ex: __by-patterns/, __by-icons/)
    - consvictabr    -> '__consvicta-' (ex: __consvicta-patterns/, ...)"""
    if _BRAND == "bysindicompany":
        return "__by-"
    if _BRAND == "consvictabr":
        return "__consvicta-"
    if _BRAND == "sindicompanybr":
        return "__"
    # Marca nova: prefixo do cadastro (tabela marcas). Fallback defensivo
    # __<slug>- igual ao default que o cadastro grava.
    return _BRAND_PREFIX or f"__{_BRAND}-"


def _handle() -> str:
    if _BRAND == "bysindicompany":
        return "@bysindicompany"
    if _BRAND == "consvictabr":
        return "@consvictabr"
    if _BRAND == "sindicompanybr":
        return "@sindicompanybr"
    return _BRAND_HANDLE or f"@{_BRAND}"


def _brand_label() -> str:
    """Nome de exibicao da marca (ex: badge do CTA). 3 marcas chumbadas
    mantem o rotulo exato; marca nova usa o nome do cadastro, caindo no
    handle sem @ ou no slug."""
    if _BRAND == "bysindicompany":
        return "By Sindicompany"
    if _BRAND == "consvictabr":
        return "Consvicta"
    if _BRAND == "sindicompanybr":
        return "Sindicompany"
    return _BRAND_NAME or _handle().lstrip("@") or _BRAND


_PATTERNS_CACHE: list[str] | None = None  # data URLs prontos pra uso


def _patterns_data_urls() -> list[str]:
    """Baixa todos os patterns disponiveis em
    condominios-fotos/__patterns/pattern-{1..20}.{png,jpg,webp}
    e devolve lista de data URLs (base64). Cache por processo pra
    nao re-baixar a cada slide. Falha silenciosa se nao houver
    patterns ou SUPABASE_URL nao estiver setada."""
    global _PATTERNS_CACHE
    if _PATTERNS_CACHE is not None:
        return _PATTERNS_CACHE

    out: list[str] = []
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _PATTERNS_CACHE = out
        return out

    for i in range(1, 21):
        for ext in ("svg", "png", "jpg", "jpeg", "webp"):
            url = (
                f"{base}/storage/v1/object/public/"
                f"condominios-fotos/{_asset_prefix()}patterns/pattern-{i}.{ext}"
            )
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "carrossel-engine/1.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status != 200:
                        continue
                    content = resp.read()
                    ctype = (
                        resp.headers.get("Content-Type", "image/png")
                        .split(";")[0]
                        .strip()
                    )
                b64 = base64.b64encode(content).decode("ascii")
                out.append(f"data:{ctype};base64,{b64}")
                break  # achou nessa ext, vai pro proximo i
            except urllib.error.HTTPError:
                continue
            except Exception as e:  # noqa: BLE001
                print(
                    f"[carrossel] pattern-{i}.{ext} falhou: {type(e).__name__}: {e}",
                    flush=True,
                )
                break

    _PATTERNS_CACHE = out
    print(f"[carrossel] {len(out)} pattern(s) carregado(s)", flush=True)
    return out


_PATTERNS_SHUFFLED_CACHE: list[str] | None = None


def _patterns_shuffled() -> list[str]:
    """Mesma lista de _patterns_data_urls(), mas embaralhada uma vez
    por processo. Como o engine roda um processo novo por carrossel
    (workflow GitHub Actions), cada carrossel pega uma ordem diferente
    — evita 'sempre os mesmos patterns na mesma posicao'.

    Dentro do mesmo carrossel, a ordem e estavel — todos os slides
    leem da mesma lista embaralhada, garantindo variedade entre
    adjacentes."""
    global _PATTERNS_SHUFFLED_CACHE
    if _PATTERNS_SHUFFLED_CACHE is not None:
        return _PATTERNS_SHUFFLED_CACHE
    base = list(_patterns_data_urls())
    random.shuffle(base)
    _PATTERNS_SHUFFLED_CACHE = base
    return base


def _pattern_for_slide(slide_idx: int, *, is_cta: bool = False, is_capa: bool = False) -> str:
    """Devolve uma data URL ciclando entre patterns aleatorizados pelo
    indice do slide, ou string vazia se nenhum pattern existir.

    Whitelist por slide: certos slides so podem usar patterns
    especificos (curadoria da marca). Pra esses, sorteia um do
    whitelist. Pra os demais, usa o shuffle global.

    Consvicta: curadoria por tom de fundo do slide. Capa+CTA sao
    escuros (onix) -> patterns dark (slots 2/4/6/9/12/13). Slides
    internos cycling entre tons claros -> patterns light (slots
    1/3/5/7/8/10/11)."""
    if _BRAND == "consvictabr":
        # Slides escuros (capa onix-gradient ou CTA onix) -> patterns dark
        dark_slots = [2, 4, 6, 9, 12, 13]
        # Slides claros (mint/sand/lavender/white/gray_5) -> patterns light
        light_slots = [1, 3, 5, 7, 8, 10, 11]
        target = dark_slots if (is_cta or is_capa) else light_slots
        shuffled = list(target)
        random.shuffle(shuffled)
        for slot in shuffled:
            url = _pattern_slot_data_url(slot)
            if url:
                return url
        # Bucket vazio? cai no shuffle global (que tambem vai vir
        # vazio se nada foi uploaded, devolvendo "")
        pats = _patterns_shuffled()
        return pats[(slide_idx - 1) % len(pats)] if pats else ""

    allowed = _SLIDE_PATTERN_WHITELIST.get(slide_idx)
    if allowed:
        # Embaralha os slots permitidos e devolve o primeiro que
        # tiver arquivo no Storage.
        shuffled_allowed = list(allowed)
        random.shuffle(shuffled_allowed)
        for slot in shuffled_allowed:
            url = _pattern_slot_data_url(slot)
            if url:
                return url
        return ""
    pats = _patterns_shuffled()
    if not pats:
        return ""
    return pats[(slide_idx - 1) % len(pats)]


# Curadoria de patterns por slide. Slot 1..20 mapeia pra
# __patterns/pattern-N.X. Slides nao listados aqui usam o shuffle
# global de TODOS os patterns disponiveis.
_SLIDE_PATTERN_WHITELIST: dict[int, list[int]] = {
    2: [1, 3, 8, 10, 11, 14, 16, 17],
    3: [1, 3, 8, 10, 11, 16, 17],
    4: [1, 3, 4, 6, 8, 10, 11, 13, 16, 17, 18, 19],
    5: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    6: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 19],
}


_PATTERN_SLOT_CACHE: dict[int, str] = {}


def _pattern_slot_data_url(slot: int) -> str:
    """Baixa um pattern especifico em __patterns/pattern-{slot}.X.
    Cache por slot. String vazia se nao houver arquivo no slot."""
    if slot in _PATTERN_SLOT_CACHE:
        return _PATTERN_SLOT_CACHE[slot]
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _PATTERN_SLOT_CACHE[slot] = ""
        return ""
    for ext in ("svg", "png", "jpg", "jpeg", "webp"):
        url = (
            f"{base}/storage/v1/object/public/"
            f"condominios-fotos/{_asset_prefix()}patterns/pattern-{slot}.{ext}"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "carrossel-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                content = resp.read()
                ctype = (
                    resp.headers.get("Content-Type", "image/png")
                    .split(";")[0]
                    .strip()
                )
            b64 = base64.b64encode(content).decode("ascii")
            url_str = f"data:{ctype};base64,{b64}"
            _PATTERN_SLOT_CACHE[slot] = url_str
            return url_str
        except urllib.error.HTTPError:
            continue
        except Exception:  # noqa: BLE001
            break
    _PATTERN_SLOT_CACHE[slot] = ""
    return ""


_ICON_CACHE: str | None = None
_ICONS_LIST_CACHE: list[str] | None = None
_ICON_SLOT_CACHE: dict[int, str] = {}
_LOGO_SLOT_CACHE: dict[int, str] = {}
_CONSVICTA_FONTS_CSS_CACHE: str | None = None
_SINDICOMPANY_FONTS_CSS_CACHE: str | None = None

# Biblioteca de icones Consvicta (86 SVGs). Cache em memoria por processo.
# Estrutura: {nome_sem_ext: svg_string}. Carrega lazily na primeira chamada.
_CONSVICTA_ICONS_CACHE: dict[str, str] | None = None

# Mapa de palavras-chave -> nomes de icones (file stem, sem extensao).
# Match e LOWERCASE substring no titulo+body do slide. Multi-match: o
# nome com MAIOR especificidade (mais letras) ganha. Sem match: cai no
# fallback default (depende do contexto do slide: capa/cta/interno).
#
# Filenames seguem padrao "NN-nome-com-hifen.svg" (Geral) ou
# "prefixo-nome.svg" (categorias). Os keywords sao derivados dos nomes
# + sinonimos comuns do mercado condominial.
_CONSVICTA_ICON_KEYWORDS: dict[str, tuple[str, ...]] = {
    # Geral (60)
    "01-documento": ("documento", "papel", "pdf"),
    "02-relatorio": ("relatorio", "relatório", "report"),
    "03-pasta": ("pasta", "arquivo", "arquivos"),
    "04-contrato": ("contrato", "assinatura", "acordo"),
    "05-balancete": ("balancete", "balanço", "balanco", "contabil", "contábil"),
    "06-ata": ("ata", "ata de"),
    "07-arquivo": ("arquivo", "documento antigo"),
    "08-sindico": ("sindico", "síndico"),
    "09-morador": ("morador", "condômino", "condomino"),
    "10-visitante": ("visitante", "visita"),
    "11-equipe": ("equipe", "time", "colaborador", "colaboradores"),
    "12-porteiro": ("porteiro", "portaria"),
    "13-funcionario": ("funcionario", "funcionário", "empregado", "colaborador"),
    "14-boleto": ("boleto", "fatura", "cobrança bancaria"),
    "15-pagamento": ("pagamento", "pagar", "pagou"),
    "16-cobranca": ("cobrança", "cobranca"),
    "17-inadimplencia": ("inadimplencia", "inadimplência", "atraso", "atrasado"),
    "18-orcamento": ("orçamento", "orcamento", "previsao", "previsão"),
    "19-prestacao-contas": ("prestação", "prestacao", "prestação de contas"),
    "20-taxa-condominial": ("taxa", "taxa condominial", "condomínio"),
    "21-protecao": ("proteção", "protecao", "seguranca", "segurança"),
    "22-cadeado": ("cadeado", "trancado", "fechado"),
    "23-chave": ("chave", "chaves", "acesso fisico"),
    "24-camera-seguranca": ("câmera", "camera", "monitoramento", "cftv"),
    "25-acesso": ("acesso", "controle de acesso"),
    "26-alarme": ("alarme", "alerta sonoro"),
    "28-email": ("email", "e-mail", "mensagem"),
    "29-comunicado": ("comunicado", "informativo", "informe"),
    "30-assembleia": ("assembleia", "assembléia", "reunião", "reuniao"),
    "31-aviso": ("aviso", "alerta", "atenção", "atencao"),
    "32-aplicativo": ("aplicativo", "app", "mobile"),
    "33-assembleia-virtual": ("assembleia virtual", "assembléia virtual", "online", "remota"),
    "36-integracao": ("integração", "integracao", "integrado"),
    "37-edificio": ("edifício", "edificio", "prédio", "predio", "torre"),
    "38-portaria": ("portaria", "recepção", "recepcao"),
    "39-elevador": ("elevador", "elevadores"),
    "40-estacionamento": ("estacionamento", "garagem", "vaga"),
    "41-area-comum": ("área comum", "area comum", "espaço", "espaco"),
    "43-limpeza": ("limpeza", "faxina", "limpo"),
    "44-mensageria": ("mensageria", "encomenda", "pacote"),
    "45-manobrista": ("manobrista", "valet"),
    "48-coworking": ("coworking", "trabalho compartilhado"),
    "49-carro-eletrico": ("carro elétrico", "carro eletrico", "ev", "elétrico"),
    "50-mini-mercado": ("mercado", "mercadinho", "loja"),
    "51-concierge": ("concierge", "conciergerie"),
    "52-salao-festas": ("salão", "salao", "festa", "evento"),
    "55-agenda": ("agenda", "calendario", "calendário", "data"),
    "57-regulamento": ("regulamento", "regimento", "regra"),
    "58-voto": ("voto", "votação", "votacao"),
    "59-solicitacao": ("solicitação", "solicitacao", "pedido"),
    "60-relatorio-financeiro": ("financeiro", "finança", "financa", "dre", "demonstrativo"),
    # Aplicativo
    "app-assembleia-virtual": ("assembleia virtual", "ao vivo digital"),
    "app-fale-porteiro": ("fale porteiro", "interfone", "intercom"),
    "app-pagamento-cartao": ("cartão", "cartao", "cartao de credito"),
    "app-reserva-area": ("reserva", "agendamento"),
    "app-segunda-via": ("segunda via", "2a via"),
    "app-sindico-online": ("síndico online", "sindico online"),
    "app-solicitacoes": ("solicitações", "solicitacoes"),
    "app-visitantes": ("visitantes", "registro de visita"),
    # Diferenciais
    "dif-atendimento-24h": ("24h", "atendimento", "plantão", "plantao", "suporte"),
    "dif-reducao-custo": ("redução de custo", "reducao de custo", "economia", "economizar"),
    "dif-revisao-contrato": ("revisão de contrato", "revisao de contrato"),
    "dif-seguro": ("seguro", "apólice", "apolice"),
    "dif-tecnologia": ("tecnologia", "tech", "digital"),
    # Equipe
    "equipe-administrativo": ("administrativo", "administração", "administracao"),
    "equipe-cobranca": ("cobrança", "cobranca"),
    "equipe-comunicacao": ("comunicação", "comunicacao", "marketing"),
    "equipe-juridico": ("jurídico", "juridico", "advogado", "lei"),
    "equipe-tecnologia": ("tecnologia", "ti", "tech"),
    # Facilities
    "fac-carro-eletrico": ("carro elétrico", "carro eletrico", "carregador"),
    "fac-concierge": ("concierge",),
    "fac-coworking": ("coworking",),
    "fac-lava-rapido": ("lava rápido", "lava rapido", "lava jato"),
    "fac-lavanderia": ("lavanderia", "lavar"),
    "fac-manobrista": ("manobrista",),
    "fac-mensageria": ("mensageria", "delivery"),
    "fac-mini-mercado": ("mercado", "mercadinho"),
}

# Ancoras por contexto: quando NAO ha match no texto, o engine cai
# nesses defaults em vez de pegar aleatorio. Mantem a marca coesa.
_CONSVICTA_ICON_DEFAULTS = {
    "capa": "37-edificio",
    "cta": "dif-atendimento-24h",
    "interno": "02-relatorio",
    "lista": "55-agenda",
    "tutorial": "01-documento",
    "dado_choca": "60-relatorio-financeiro",
    "mito_verdade": "31-aviso",
    "historia_real": "09-morador",
    "antes_depois": "dif-reducao-custo",
    "opiniao": "29-comunicado",
}


def _consvicta_icons_load() -> dict[str, str]:
    """Carrega todos os 86 SVGs da biblioteca Consvicta em memoria
    (~370KB total). Cache no processo. Chave = stem do arquivo
    (ex: '05-balancete'). Valor = string SVG completa."""
    global _CONSVICTA_ICONS_CACHE
    if _CONSVICTA_ICONS_CACHE is not None:
        return _CONSVICTA_ICONS_CACHE
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(here, "assets", "icons", "consvicta")
    cache: dict[str, str] = {}
    try:
        for cat in os.listdir(root):
            cat_dir = os.path.join(root, cat)
            if not os.path.isdir(cat_dir):
                continue
            for fname in os.listdir(cat_dir):
                if not fname.endswith(".svg"):
                    continue
                stem = fname[:-4]
                try:
                    with open(
                        os.path.join(cat_dir, fname), "r", encoding="utf-8"
                    ) as f:
                        cache[stem] = f.read()
                except Exception:  # noqa: BLE001
                    continue
    except Exception as e:  # noqa: BLE001
        print(f"[carrossel] icones consvicta nao carregaram: {e}", flush=True)
    print(f"[carrossel] {len(cache)} icones consvicta em memoria", flush=True)
    _CONSVICTA_ICONS_CACHE = cache
    return cache


def _consvicta_icon_svg_recolored(stem: str, color: str) -> str:
    """Devolve o SVG do icone trocando a cor do stroke (#81D8D0
    original) pela cor passada. Sem alocacao se nao achar."""
    icons = _consvicta_icons_load()
    svg = icons.get(stem)
    if not svg:
        return ""
    return svg.replace('#81D8D0', color).replace('#81d8d0', color)


def _consvicta_icon_data_url(stem: str, color: str) -> str:
    """Data URL pronto pra usar em <img src=...>. SVG recolorido pra
    contraste correto com o fundo do slide."""
    svg = _consvicta_icon_svg_recolored(stem, color)
    if not svg:
        return ""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _consvicta_pick_icon(
    titulo: str, body: str, fallback_ctx: str = "interno"
) -> str:
    """Faz match keyword no titulo+body do slide e devolve o stem do
    icone mais relevante. Sem match: usa o default do contexto
    (capa/cta/interno + formato)."""
    haystack = f"{titulo} {body}".lower()
    best_stem = ""
    best_score = 0
    for stem, kws in _CONSVICTA_ICON_KEYWORDS.items():
        for kw in kws:
            if kw in haystack:
                # specificity = comprimento do keyword (mais especifico vence)
                score = len(kw)
                if score > best_score:
                    best_score = score
                    best_stem = stem
    if best_stem:
        return best_stem
    return _CONSVICTA_ICON_DEFAULTS.get(fallback_ctx, "02-relatorio")


def _consvicta_fonts_css() -> str:
    """CSS @font-face com as 3 famílias Consvicta embutidas em base64
    (Cormorant Garamond 300/400/500 + italics, Outfit 200-600, Bebas
    Neue 400). Arquivo em api/assets/fonts/consvicta/. Cache por
    processo. String vazia se nao encontrar — engine cai pros
    fallbacks system (Georgia/system-ui/Impact)."""
    global _CONSVICTA_FONTS_CSS_CACHE
    if _CONSVICTA_FONTS_CSS_CACHE is not None:
        return _CONSVICTA_FONTS_CSS_CACHE
    here = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(
        here, "assets", "fonts", "consvicta", "consvicta-fonts-inline.css"
    )
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            _CONSVICTA_FONTS_CSS_CACHE = f.read()
        print(
            f"[carrossel] consvicta-fonts-inline.css carregado "
            f"({len(_CONSVICTA_FONTS_CSS_CACHE)//1024} KB)",
            flush=True,
        )
    except Exception as e:  # noqa: BLE001
        print(
            f"[carrossel] consvicta-fonts-inline.css nao encontrado: {e}",
            flush=True,
        )
        _CONSVICTA_FONTS_CSS_CACHE = ""
    return _CONSVICTA_FONTS_CSS_CACHE


def _sindicompany_fonts_css() -> str:
    """CSS @font-face com Provicali (.otf, 400) + Epilogue Variable
    (.woff2, 100-900 normal/italic) embutidos em base64. Arquivo em
    api/assets/fonts/sindicompany/. Cache por processo. String vazia
    se nao encontrar — engine cai pro fallback Epilogue do Google
    Fonts."""
    global _SINDICOMPANY_FONTS_CSS_CACHE
    if _SINDICOMPANY_FONTS_CSS_CACHE is not None:
        return _SINDICOMPANY_FONTS_CSS_CACHE
    here = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(
        here, "assets", "fonts", "sindicompany", "sindicompany-fonts-inline.css"
    )
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            _SINDICOMPANY_FONTS_CSS_CACHE = f.read()
        print(
            f"[carrossel] sindicompany-fonts-inline.css carregado "
            f"({len(_SINDICOMPANY_FONTS_CSS_CACHE)//1024} KB)",
            flush=True,
        )
    except Exception as e:  # noqa: BLE001
        print(
            f"[carrossel] sindicompany-fonts-inline.css nao encontrado: {e}",
            flush=True,
        )
        _SINDICOMPANY_FONTS_CSS_CACHE = ""
    return _SINDICOMPANY_FONTS_CSS_CACHE


_BRAND_FONTS_CACHE: dict[str, tuple[str, str, str, str] | None] = {}


def _font_format(file: str) -> str:
    f = file.lower()
    if f.endswith(".woff2"):
        return "woff2"
    if f.endswith(".woff"):
        return "woff"
    if f.endswith(".otf"):
        return "opentype"
    return "truetype"


def _font_mime(file: str) -> str:
    f = file.lower()
    if f.endswith(".woff2"):
        return "font/woff2"
    if f.endswith(".woff"):
        return "font/woff"
    if f.endswith(".otf"):
        return "font/otf"
    return "font/ttf"


def _brand_fonts_from_tipografia() -> tuple[str, str, str, str] | None:
    """Monta (head_fonts, font_display, font_body, font_numeric) a partir da
    tipografia data-driven (_BRAND_TIPOGRAFIA), baixando cada arquivo de fonte
    do bucket ({prefixo}fonts/) e embutindo em base64 como @font-face. Devolve
    None se nao houver tipografia utilizavel ou se nenhum arquivo carregar —
    aí o caller cai nas fontes embutidas. Cache por marca/processo."""
    if _BRAND in _BRAND_FONTS_CACHE:
        return _BRAND_FONTS_CACHE[_BRAND]

    tip = _BRAND_TIPOGRAFIA
    faces = tip.get("faces") if isinstance(tip, dict) else None
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not isinstance(faces, list) or not faces or not base:
        _BRAND_FONTS_CACHE[_BRAND] = None
        return None

    prefix = _asset_prefix()
    blocks: list[str] = []
    for f in faces:
        if not isinstance(f, dict):
            continue
        file = str(f.get("file") or "").strip()
        family = str(f.get("family") or "").strip()
        if not file or not family:
            continue
        weight = f.get("weight") or 400
        style = f.get("style") or "normal"
        url = (
            f"{base}/storage/v1/object/public/"
            f"condominios-fotos/{prefix}fonts/{urllib.parse.quote(file)}"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "carrossel-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    continue
                content = resp.read()
            b64 = base64.b64encode(content).decode("ascii")
            blocks.append(
                "@font-face{"
                f"font-family:'{family}';"
                f"font-style:{style};"
                f"font-weight:{weight};"
                "font-display:swap;"
                f"src:url(data:{_font_mime(file)};base64,{b64}) "
                f"format('{_font_format(file)}');"
                "}"
            )
            print(
                f"[carrossel] fonte {file} embutida ({len(content)//1024} KB)",
                flush=True,
            )
        except Exception as e:  # noqa: BLE001
            print(f"[carrossel] fonte {file} falhou: {e}", flush=True)
            continue

    if not blocks:
        _BRAND_FONTS_CACHE[_BRAND] = None
        return None

    head = f"<style>{''.join(blocks)}</style>"
    fd = str(tip.get("display") or "").strip() or "system-ui, sans-serif"
    fb = str(tip.get("body") or "").strip() or "system-ui, sans-serif"
    fn = str(tip.get("numeric") or "").strip() or fb
    result = (head, fd, fb, fn)
    _BRAND_FONTS_CACHE[_BRAND] = result
    return result


def _logo_slot_data_url(slot: int) -> str:
    """Devolve data URL do logo em __logos/logo-{slot}.X. Cache por
    slot. String vazia se nao houver."""
    if slot in _LOGO_SLOT_CACHE:
        return _LOGO_SLOT_CACHE[slot]
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _LOGO_SLOT_CACHE[slot] = ""
        return ""
    for ext in ("png", "svg", "webp", "jpg", "jpeg"):
        url = (
            f"{base}/storage/v1/object/public/"
            f"condominios-fotos/{_asset_prefix()}logos/logo-{slot}.{ext}"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "carrossel-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                content = resp.read()
                ctype = (
                    resp.headers.get("Content-Type", "image/png")
                    .split(";")[0]
                    .strip()
                )
            b64 = base64.b64encode(content).decode("ascii")
            url_str = f"data:{ctype};base64,{b64}"
            _LOGO_SLOT_CACHE[slot] = url_str
            print(f"[carrossel] logo-{slot}.{ext} carregado", flush=True)
            return url_str
        except urllib.error.HTTPError:
            continue
        except Exception:  # noqa: BLE001
            break
    _LOGO_SLOT_CACHE[slot] = ""
    return ""


def _icon_slot_data_url(slot: int) -> str:
    """Devolve data URL do icon especifico em __icons/icon-{slot}.X.
    Cache por slot. String vazia se nao houver."""
    if slot in _ICON_SLOT_CACHE:
        return _ICON_SLOT_CACHE[slot]
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _ICON_SLOT_CACHE[slot] = ""
        return ""
    for ext in ("png", "svg", "webp", "jpg", "jpeg"):
        url = (
            f"{base}/storage/v1/object/public/"
            f"condominios-fotos/{_asset_prefix()}icons/icon-{slot}.{ext}"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "carrossel-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                content = resp.read()
                ctype = (
                    resp.headers.get("Content-Type", "image/png")
                    .split(";")[0]
                    .strip()
                )
            b64 = base64.b64encode(content).decode("ascii")
            url_str = f"data:{ctype};base64,{b64}"
            _ICON_SLOT_CACHE[slot] = url_str
            print(f"[carrossel] icon-{slot}.{ext} carregado", flush=True)
            return url_str
        except urllib.error.HTTPError:
            continue
        except Exception:  # noqa: BLE001
            break
    _ICON_SLOT_CACHE[slot] = ""
    return ""


def _icon_data_url() -> str:
    """Devolve data URL do icon principal (slot 1 em __icons/icon-1.X)
    pra usar como marca no canto inferior direito dos slides. Cache
    no processo. String vazia se nao houver."""
    global _ICON_CACHE
    if _ICON_CACHE is not None:
        return _ICON_CACHE
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _ICON_CACHE = ""
        return ""
    for ext in ("png", "svg", "webp", "jpg", "jpeg"):
        url = (
            f"{base}/storage/v1/object/public/"
            f"condominios-fotos/{_asset_prefix()}icons/icon-1.{ext}"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "carrossel-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                content = resp.read()
                ctype = (
                    resp.headers.get("Content-Type", "image/png")
                    .split(";")[0]
                    .strip()
                )
            b64 = base64.b64encode(content).decode("ascii")
            _ICON_CACHE = f"data:{ctype};base64,{b64}"
            print(f"[carrossel] icon-1.{ext} carregado", flush=True)
            return _ICON_CACHE
        except urllib.error.HTTPError:
            continue
        except Exception as e:  # noqa: BLE001
            print(
                f"[carrossel] icon-1.{ext} falhou: {type(e).__name__}: {e}",
                flush=True,
            )
            break
    _ICON_CACHE = ""
    return ""


def _icons_all_data_urls() -> list[str]:
    """Baixa todos os icons do CARROSSEL em
    __icon-carrossel/icon-{1..20}.X e devolve lista de data URLs na
    ordem dos slots. Cache por processo. Slots vazios sao pulados.

    Bucket separado de __icons/ (que eh a biblioteca geral). Esse aqui
    e exclusivo da engine de carrossel: cada slot preenche o fundo de
    um slide especifico."""
    global _ICONS_LIST_CACHE
    if _ICONS_LIST_CACHE is not None:
        return _ICONS_LIST_CACHE
    out: list[str] = []
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _ICONS_LIST_CACHE = out
        return out
    for i in range(1, 21):
        for ext in ("png", "svg", "webp", "jpg", "jpeg"):
            url = (
                f"{base}/storage/v1/object/public/"
                f"condominios-fotos/{_asset_prefix()}icon-carrossel/icon-{i}.{ext}"
            )
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "carrossel-engine/1.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status != 200:
                        continue
                    content = resp.read()
                    ctype = (
                        resp.headers.get("Content-Type", "image/png")
                        .split(";")[0]
                        .strip()
                    )
                b64 = base64.b64encode(content).decode("ascii")
                out.append(f"data:{ctype};base64,{b64}")
                break  # achou nessa ext, vai pro proximo i
            except urllib.error.HTTPError:
                continue
            except Exception:  # noqa: BLE001
                break
    _ICONS_LIST_CACHE = out
    print(f"[carrossel] {len(out)} icon-carrossel carregado(s)", flush=True)
    return out


# Slots dos 20 fundos no bucket __consvicta-icon-carrossel/ separados
# por tom dominante do SVG. Light = fundo predominantemente claro
# (cream/off-white), funciona em slides claros (mint/sand/lavender/
# white/gray_5). Dark = fundo predominantemente escuro (ink/grafite/
# gradient escuro), funciona em capa + CTA (onix). Tons mistos vao
# pro pool DARK por seguranca (10 split, 15 linhas dark, etc).
_CONSVICTA_FUNDO_LIGHT_SLOTS = [6, 14, 19]  # offwhite-elegante, moldura-interna, gold-edge
_CONSVICTA_FUNDO_DARK_SLOTS = [
    1, 2, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15, 16, 17, 18, 20
]


def _consvicta_fundo_for_slide(slide_idx: int, *, is_cta: bool, is_capa: bool) -> str:
    """Pega um fundo curado pelo tom do slide. Roda apos garantir que
    o bucket __consvicta-icon-carrossel/ tem assets uploaded. Se algum
    slot estiver vazio, pula pra o proximo do pool. Sem assets, volta
    "" e o caller cai no fallback (logo simbolo)."""
    # Slide tom: capa+CTA escuros (onix), internos claros
    is_dark = is_cta or is_capa
    pool = _CONSVICTA_FUNDO_DARK_SLOTS if is_dark else _CONSVICTA_FUNDO_LIGHT_SLOTS
    # Cycla pelo pool por slide_idx pra cada slide ter um fundo diferente
    # (mod sobre o tamanho do pool, nao do total de 20)
    if not pool:
        return ""
    # Tenta o slot ideal primeiro, depois fallback pros vizinhos
    start = (slide_idx - 1) % len(pool)
    for offset in range(len(pool)):
        slot = pool[(start + offset) % len(pool)]
        url = _consvicta_fundo_slot_data_url(slot)
        if url:
            return url
    return ""


_CONSVICTA_FUNDO_SLOT_CACHE: dict[int, str] = {}


def _consvicta_fundo_slot_data_url(slot: int) -> str:
    """Baixa o fundo do bucket __consvicta-icon-carrossel/icon-{slot}.X
    e cacheia por slot. String vazia se nao houver."""
    if slot in _CONSVICTA_FUNDO_SLOT_CACHE:
        return _CONSVICTA_FUNDO_SLOT_CACHE[slot]
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _CONSVICTA_FUNDO_SLOT_CACHE[slot] = ""
        return ""
    for ext in ("svg", "png", "webp", "jpg", "jpeg"):
        url = (
            f"{base}/storage/v1/object/public/"
            f"condominios-fotos/__consvicta-icon-carrossel/icon-{slot}.{ext}"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "carrossel-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                content = resp.read()
                ctype = (
                    resp.headers.get("Content-Type", "image/svg+xml")
                    .split(";")[0]
                    .strip()
                )
            b64 = base64.b64encode(content).decode("ascii")
            url_str = f"data:{ctype};base64,{b64}"
            _CONSVICTA_FUNDO_SLOT_CACHE[slot] = url_str
            return url_str
        except urllib.error.HTTPError:
            continue
        except Exception:  # noqa: BLE001
            break
    _CONSVICTA_FUNDO_SLOT_CACHE[slot] = ""
    return ""


def _icon_for_slide(slide_idx: int, *, is_cta: bool = False, is_capa: bool = False) -> str:
    """Mapeia: slot 1 -> slide 2, slot 2 -> slide 3, etc.
    Capa (slide_idx 1) NAO recebe Fundo Carrossel — retorna vazio.

    Excecao Consvicta: capa E todos os slides recebem fundo curado
    pelo tom (light pra internos claros, dark pra capa+CTA). Se o
    bucket __consvicta-icon-carrossel/ estiver vazio, usa o logo
    simbolo (slot 2 de __consvicta-logos) como fallback decorativo
    pra preencher visualmente o slide (a opacity baixa do .icon-bg
    suaviza o efeito)."""
    if _BRAND == "consvictabr":
        # Picker curado por tom (light/dark) — vai DIRETO no slot
        # certo do bucket em vez de pegar da lista geral. Ja faz
        # cycling dentro do pool do tom certo.
        url = _consvicta_fundo_for_slide(
            slide_idx, is_cta=is_cta, is_capa=is_capa
        )
        if url:
            return url
        # Bucket vazio? Fallback: logo simbolo como brand reinforcement
        sym = _logo_slot_data_url(2)
        return sym or ""
    # Outras marcas: comportamento original (capa sem fundo)
    icons = _icons_all_data_urls()
    if not icons or slide_idx < 2:
        return ""
    return icons[(slide_idx - 2) % len(icons)]

BUCKET = "condominios-fotos"
SLIDE_W = 3072
SLIDE_H = 3839  # 4:5 vertical

# Paleta oficial Sindicompany — Brand Hub 2026-05-17
# (Navy/Cyan/Beige/Lavender/Purple/White). Mantém as chaves antigas
# (onix/mint/sand/lavender/white/gray_5) pra compatibilidade com o
# template HTML — só os valores HEX trocam.
#  - onix     -> Navy (texto/fundos principais)
#  - mint     -> Cyan (acento, confiança)
#  - sand     -> Beige (calor, humano)
#  - lavender -> Lavender novo (inovação, tech)
#  - purple   -> Purple novo (profundidade, IA) — nova chave opcional
#  - white    -> White puro
#  - gray_5   -> Paper warm (substitui o gray_5 frio antigo)
PALETTE = {
    "onix": "#182028",       # Navy
    "mint": "#88C8D0",       # Cyan
    "sand": "#E0B098",       # Beige
    "lavender": "#BFC0FF",   # Lavender
    "purple": "#8890D0",     # Purple (nova — Brand Hub 2026-05-17)
    "white": "#FFFFFF",
    "gray_5": "#FAF7F2",     # Paper
}

# Paleta oficial Consvicta (Brand Book). Mapeia para as mesmas chaves
# que o template usa, pra trocar sem mudar o HTML dos slides:
#  - onix     -> Preto Profundo
#  - mint     -> Tiffany / Pantone 1837 Blue (cor signature da marca)
#  - sand     -> Ouro Envelhecido
#  - lavender -> Ouro Claro
#  - white    -> Branco Puro
#  - gray_5   -> Off-White
PALETTE_CONSVICTA = {
    # Cores reais do site consvicta.com.br (extraídas dos HTML).
    # Onix do site e WARM (#1A1714), nao puro preto — combina melhor
    # com o ouro envelhecido e o off-white. Tiffany e ouro batem o
    # brand book.
    "onix": "#1A1714",        # Warm Onix (site)
    "mint": "#81D8D0",        # Tiffany / Pantone 1837 Blue (signature)
    "sand": "#B08D57",        # Ouro Envelhecido
    "lavender": "#C9A96E",    # Ouro Claro (variante)
    "white": "#FDFCF9",       # Paper (off-white quente)
    "gray_5": "#F5F5F2",      # Off-White (textura suave)
}


def _palette() -> dict[str, str]:
    """Paleta ativa da marca. Base chumbada (compat das 3 marcas atuais)
    sobreposta pelos valores do DB (marcas.paleta), quando houver. O merge
    garante que toda chave que o template usa exista mesmo se o DB so
    trouxer parte das cores (marca nova herda as chaves que faltam)."""
    base = PALETTE_CONSVICTA if _BRAND == "consvictabr" else PALETTE
    if _BRAND_PALETTE:
        return {**base, **_BRAND_PALETTE}
    return base


def _rel_lum(hexc: str) -> float:
    """Luminancia relativa (WCAG) de um hex #rrggbb. 0=preto, 1=branco."""
    h = (hexc or "").lstrip("#")
    if len(h) != 6:
        return 0.0
    try:
        r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 0.0

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(a: str, b: str) -> float:
    """Razao de contraste WCAG entre duas cores (1 a 21)."""
    la, lb = _rel_lum(a), _rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _adjust_for_contrast(color: str, bg: str, target: float) -> str:
    """Escurece (fundo claro) ou clareia (fundo escuro) a cor ate atingir
    o contraste alvo no fundo, mantendo o tom. Pra paletas pastel, em que
    nenhuma cor cromatica contrasta sozinha em fundo claro."""
    h = color.lstrip("#")
    if len(h) != 6:
        return color
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    darken = _rel_lum(bg) > 0.35
    for _ in range(24):
        cur = f"#{r:02x}{g:02x}{b:02x}"
        if _contrast(cur, bg) >= target:
            return cur
        if darken:
            r, g, b = int(r * 0.85), int(g * 0.85), int(b * 0.85)
        else:
            r, g, b = (
                r + int((255 - r) * 0.15),
                g + int((255 - g) * 0.15),
                b + int((255 - b) * 0.15),
            )
    return f"#{r:02x}{g:02x}{b:02x}"


def _pick_title_color(bg: str, fg: str, p: dict[str, str]) -> str:
    """Cor do TITULO, distinta da cor do corpo (fg), pra criar hierarquia
    cromatica em TODO slide. Escolhe a cor cromatica da marca com melhor
    contraste no fundo; se nenhuma chega a 3:1 (paleta pastel em fundo
    claro), escurece/clareia a melhor delas ate ficar legivel. So cai em
    fg se a marca nao tiver nenhuma cor cromatica. Vale pra qualquer paleta."""
    cands = [
        c
        for c in (p.get(k) for k in ("mint", "purple", "sand", "lavender"))
        if c and c.lower() != bg.lower()
    ]
    if not cands:
        return fg
    cands.sort(key=lambda c: _contrast(c, bg), reverse=True)
    best = cands[0]
    if _contrast(best, bg) >= 3.0:
        return best
    return _adjust_for_contrast(best, bg, 4.0)


def _fetch_marca(slug: str) -> dict[str, Any] | None:
    """Le a marca do Supabase (paleta, bucket_prefix, handle, nome) numa
    query. Qualquer falha (marca ausente, erro de rede) cai em None ->
    identidade chumbada. Zero regressao independente do estado do banco."""
    try:
        sb = _sb_client()
        res = (
            sb.table("marcas")
            .select("paleta, bucket_prefix, handle, nome")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:  # noqa: BLE001 — fallback proposital
        print(f"[carrossel] marca do DB indisponivel ({e}); usando chumbada", flush=True)
        return None


def _paleta_from_marca(marca: dict[str, Any] | None) -> dict[str, str] | None:
    """Extrai a paleta (str->str) da marca, descartando lixo. None se vazia."""
    if not marca:
        return None
    paleta = marca.get("paleta")
    if isinstance(paleta, dict) and paleta:
        return {
            str(k): str(v)
            for k, v in paleta.items()
            if isinstance(v, str) and v.strip()
        }
    return None


def _fetch_marca_tipografia(slug: str) -> dict[str, Any] | None:
    """Le marcas.tipografia (jsonb). Query SEPARADA de _fetch_marca de
    proposito: se a coluna ainda nao existir (migration nao rodada), so a
    tipografia fica indisponivel — paleta/prefixo/handle seguem normais.
    None = sem fontes proprias -> engine usa as embutidas."""
    try:
        sb = _sb_client()
        res = (
            sb.table("marcas")
            .select("tipografia")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        tip = rows[0].get("tipografia")
        if isinstance(tip, dict) and tip.get("faces"):
            return tip
        return None
    except Exception as e:  # noqa: BLE001 — fallback proposital
        print(f"[carrossel] tipografia do DB indisponivel ({e})", flush=True)
        return None


# =============================================================================
# Supabase helpers
# =============================================================================


def _fetch_carrossel(carrossel_id: str) -> dict[str, Any] | None:
    sb = _sb_client()
    res = sb.table("carrosseis").select("*").eq("id", carrossel_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def _update_carrossel(carrossel_id: str, fields: dict[str, Any]) -> None:
    sb = _sb_client()
    sb.table("carrosseis").update(fields).eq("id", carrossel_id).execute()


def _upload_png(carrossel_id: str, slide_idx: int, png_bytes: bytes) -> str:
    sb = _sb_client()
    path = f"__carrosseis/{carrossel_id}/slide-{slide_idx}.png"
    sb.storage.from_(BUCKET).upload(
        path=path,
        file=png_bytes,
        file_options={"content-type": "image/png", "upsert": "true"},
    )
    pub = sb.storage.from_(BUCKET).get_public_url(path)
    if isinstance(pub, str):
        return pub
    # supabase-py 2.x retorna string direta; algumas versões retornam dict
    return pub.get("publicUrl") if isinstance(pub, dict) else str(pub)


def _upload_slides_zip(
    carrossel_id: str, png_bytes_por_slide: list[bytes]
) -> str:
    """Empacota todos os PNGs em um ZIP e sobe pro bucket. Devolve URL
    publica. Cada PNG vai como slide-N.png (mesma convencao dos
    individuais)."""
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for i, png in enumerate(png_bytes_por_slide, start=1):
            zf.writestr(f"slide-{i}.png", png)
    zip_bytes = buf.getvalue()
    sb = _sb_client()
    path = f"__carrosseis/{carrossel_id}/slides.zip"
    sb.storage.from_(BUCKET).upload(
        path=path,
        file=zip_bytes,
        file_options={"content-type": "application/zip", "upsert": "true"},
    )
    pub = sb.storage.from_(BUCKET).get_public_url(path)
    if isinstance(pub, str):
        return pub
    return pub.get("publicUrl") if isinstance(pub, dict) else str(pub)


# =============================================================================
# Copy generation (GPT)
# =============================================================================

# Instrucoes detalhadas por formato — so o bloco do formato escolhido
# eh injetado no prompt.
FORMATO_INSTRUCOES = {
    "historia_real": (
        "FORMATO: HISTORIA REAL (a formula que mais engaja — 2o maior viral da conta).\n"
        "- De um NOME PROPRIO brasileiro ao personagem, variando a cada roteiro (nunca use sempre o mesmo nome), nunca 'um morador'. Detalhes concretos: '10 anos', '23%', '12 a 8'. NUNCA cite numero de apartamento/unidade nem nome de condominio.\n"
        "- CONFLITO MORAL (o coracao do post): NAO pode ter vilao obvio. Coloque DUAS coisas legitimas em tensao — ex: o sindico querido e dedicado X o condominio que precisava de gestao dura. Deixe explicito que 'sao coisas diferentes'.\n"
        "- FINAL AMBIGUO: mostre o CUSTO HUMANO junto do resultado. Os numeros melhoraram, MAS algo se perdeu (relacoes, amizades, quem nao se cumprimenta mais) — ninguem 'venceu' limpo. A ambiguidade e o que gera o debate.\n"
        "- Personagens/situacoes podem ser compostos. NUNCA cite nome de condominio (real ou inventado), endereco, nem numero de unidade/apartamento.\n"
        "ESTRUTURA (arco da historia): "
        "1(capa) personagem + evento dramatico, sem resolver ('Ele foi sindico por 10 anos. Votaram pra tirar ele. 12 a 8.') + tarja FORMATO. "
        "2 A SITUACAO: quem e o personagem (humano, querido) e a tensao por baixo. "
        "3 O QUE NINGUEM FALAVA: o problema oculto; o conflito moral aflora ('ser querido' != 'saber gerir'). "
        "4 A DECISAO/VIRADA: o que aconteceu e o FINAL AMBIGUO (o que ganhou E o que doeu). "
        "5 O RESULTADO: numeros concretos depois (ex: 'de 23% pra 4%'), em lista quando couber. "
        "ultimo (CTA) PERGUNTA DE POSICIONAMENTO que OBRIGA a escolher um lado ('Voce teria votado com os 12 ou com os 8?'), "
        "terminando com '[[Comenta 12 ou 8]]' + uma linha curta legendando cada lado ('12 = sindico profissional · 8 = ficava com o Carlos')."
    ),
    "lista": (
        "FORMATO: LISTA (educativo, pontos equivalentes).\n"
        "- MAXIMO 5 itens, cada um cabe em UMA linha.\n"
        "- Ordene do MENOS obvio pro MAIS surpreendente: o item final precisa chocar.\n"
        "- Numeros sao parte do design (Black 900, mint, grande). Sem bullet points no texto.\n"
        "ESTRUTURA: 1(capa) 'X coisas que [acao provocativa]'. "
        "2 a N-1 um item por slide (numero no titulo + explicacao curta no body). "
        "ultimo CTA 'Qual voce nao sabia? Comenta o numero aqui'."
    ),
    "mito_verdade": (
        "FORMATO: MITO VS VERDADE (mito juridico universalmente vivido — a formula que MAIS viralizou).\n"
        "- FOQUE EM UM UNICO MITO, desenvolvido a fundo. NUNCA varios pares rasos de mito/verdade.\n"
        "- O mito tem que ser uma CRENCA que quase todo mundo ja assumiu como obvia ('o sindico tem obrigacao de resolver, ne?').\n"
        "- A verdade precisa ser ESPECIFICA: 'a regra/lei diz exatamente o oposto' (cite artigo/REsp quando der).\n"
        "FORMULA DA CAPA (siga A RISCA — foi o que viralizou): "
        "(1) uma CENA concreta do dia a dia que todo mundo ja viveu, curtissima ('Vizinho barulhento as 3h. Voce liga pro sindico.'); "
        "(2) a CRENCA obvia em seguida, com uma CONTRADICAO curta (2 a 3 palavras) entre [[ ]] — ex: '[[obrigacao de resolver]]'; "
        "(3) termine com PERGUNTA BINARIA (sim/nao) — 'ne?', 'certo?'. + tarja FORMATO.\n"
        "ESTRUTURA (arco de UM mito so): capa -> MITO (enuncia a crenca errada) -> O PROBLEMA (consequencia real) -> "
        "VERDADE (o que a regra realmente diz, especifico) -> O QUE FAZER (passos praticos, lista numerada) -> CTA. "
        "tipo dos slides: 'mito' / 'verdade'. "
        "CTA (ultimo): frase de CONTRADICAO memoravel ('Sindico bom nao resolve tudo. Ele resolve o que e dele resolver.') + "
        "PERGUNTA BINARIA, terminando com '[[Comenta SIM ou NAO]]'."
    ),
    "antes_depois": (
        "FORMATO: ANTES / DEPOIS (resultado tangivel de gestao profissional).\n"
        "- O 'depois' precisa ter NUMERO concreto ('caiu de 23% pra 4% em 6 meses').\n"
        "- O 'antes' precisa ser RECONHECIVEL. NUNCA fabricar resultados.\n"
        "ESTRUTURA: 1(capa) o dado do 'depois' em destaque (resultado final primeiro). "
        "2 o 'antes'. 3 o problema raiz. 4 o que mudou. 5 o 'depois' detalhado com numeros. "
        "ultimo CTA 'Seu condominio esta no antes ou no depois?'."
    ),
    "dado_choca": (
        "FORMATO: DADO QUE CHOCA (estatistica surpreendente com fonte).\n"
        "- So dados que voce conhece com FONTE IDENTIFICAVEL (SindicoNet, IBGE, SECOVI, STJ, leis federais, reportagens datadas). NUNCA invente. NUNCA 'estudos mostram'/'especialistas afirmam'.\n"
        "- Reescreva o dado com suas palavras. Cite a fonte no slide E na legenda ('Fonte: SindicoNet, 2025'). Sem dado real seguro? Use uma referencia legal solida reescrita como dado.\n"
        "ESTRUTURA: 1(capa) SO o numero em destaque (Black 900, mint/sand, ocupa o slide), sem contexto. "
        "2 o que esse numero significa na vida do morador. 3 quem esta dentro do dado. "
        "4 o contraponto. 5 o que fazer com a info. ultimo CTA 'Voce esta nesse numero? SIM ou NAO'."
    ),
    "tutorial": (
        "FORMATO: TUTORIAL RAPIDO (acao pratica que da pra fazer hoje).\n"
        "- MAXIMO 5 passos, cada um COMECA com verbo de acao (Solicite, Anote, Envie, Guarde, Exija).\n"
        "- Sem jargao juridico sem traducao imediata. Precisa ser acionavel HOJE.\n"
        "- O ULTIMO slide tem um modelo de texto/script que o morador copia direto.\n"
        "ESTRUTURA: 1(capa) o problema que o tutorial resolve, em pergunta. "
        "2 por que a maioria nao faz (a barreira). 3 a N-1 um passo por slide, numerado, verbo de acao. "
        "ultimo o modelo/script copiavel + CTA 'Salva esse post. Voce vai precisar'."
    ),
    "opiniao": (
        "FORMATO: OPINIAO FORTE (posicao clara da MARCA sobre tema polemico).\n"
        "- A opiniao e da MARCA (perfil), nao de personagem ficticio. Precisa de 2-3 razoes concretas.\n"
        "- ANTECIPE o contra-argumento num slide ('sei que voce discorda, mas...') + responda.\n"
        "- NUNCA atacar pessoas. CTA obrigatoriamente de DEBATE.\n"
        "ESTRUTURA: 1(capa) a afirmacao provocativa sem contexto, MAX 6 palavras. "
        "2 o problema que motivou (dado/situacao). 3 argumento 1. 4 o contra-argumento + resposta. "
        "5 argumento 2 e consequencia pratica. ultimo CTA 'Concorda ou discorda? Comenta CONCORDO ou DISCORDO'."
    ),
    "hook_punch": (
        "FORMATO: HOOK PUNCH (o mais agressivo — para o scroll na hora).\n"
        "- Frases CURTAS e fortes, poucas palavras por slide, ritmo rapido, tensao alta. Cada slide e um soco.\n"
        "- Nada de explicacao longa: impacto emocional progressivo, um golpe por slide. Varios slides tipo 'frase'.\n"
        "- Use verdade humana e palavras magneticas. Capa: a frase mais forte possivel, max 6 palavras."
    ),
    "pov": (
        "FORMATO: POV (identificacao extrema, 'isso sou eu').\n"
        "- Capa comeca com 'POV:' + situacao MUITO especifica e reconhecivel (ex: 'POV: voce abriu o grupo do condominio as 22h').\n"
        "- Tom cinematografico, presente, 2a pessoa ('voce...'). Escalada emocional ate uma verdade humana.\n"
        "- Objetivo: 'sou eu / e alguem que conheco' -> marcar/compartilhar. CTA de identificacao ou compartilhamento."
    ),
    "tweet": (
        "FORMATO: TWEET STYLE (frase curta, printavel, repostavel).\n"
        "- Cada slide e uma frase de efeito que funciona SOZINHA (observacao humana, verdade incomoda, indireta). Leitura instantanea.\n"
        "- Quase todos os slides sao tipo 'frase' (limpo/centralizado). Nada de paragrafo. 1 ideia por slide.\n"
        "- Pensado pra print/repost e branding. CTA leve de compartilhamento."
    ),
    "expectativa_realidade": (
        "FORMATO: EXPECTATIVA VS REALIDADE (humor + identificacao).\n"
        "- Capa apresenta a EXPECTATIVA idealizada; os slides mostram a REALIDADE absurda/caotica, com humor leve.\n"
        "- Contraste forte e identificavel. Otimo pra meme. Fechamento com reflexao leve. CTA de compartilhamento."
    ),
    "erro_fatal": (
        "FORMATO: ERRO FATAL (medo de errar).\n"
        "- Capa nomeia O erro que custa caro (ex: 'O erro que destroi assembleias').\n"
        "- Mostra a consequencia, AMPLIFICA o prejuizo, entrega a solucao pratica. Ativa medo + utilidade. CTA de salvar."
    ),
    "bastidor": (
        "FORMATO: BASTIDOR REAL (documental, humaniza).\n"
        "- Mostra o bastidor real (visita tecnica, reuniao dificil, vistoria) + um DETALHE INVISIVEL que so quem vive percebe.\n"
        "- Tom de quem esta dentro, percepcao premium. Termina em reflexao/frase forte. CTA de identificacao ou autoridade."
    ),
    "camada_invisivel": (
        "FORMATO: CAMADA INVISIVEL (profundidade emocional).\n"
        "- Parte de uma situacao comum e revela a CAMADA emocional escondida (ex: 'muita reclamacao nasce do cansaco').\n"
        "- Provoca o 'nunca pensei nisso'. Verdade humana + frase memoravel. CTA emocional/de compartilhamento."
    ),
    "dialogo": (
        "FORMATO: DIALOGO (conversa).\n"
        "- Troca curta de falas entre dois personagens, falantes nomeados no inicio (ex: body 'Morador: Mas e rapidinho.' / proximo 'Sindico: Todo problema comeca com rapidinho.').\n"
        "- Escalada emocional e PUNCH na ultima fala. Leitura rapida, humana. Nao citar condominio/unidade. CTA de identificacao."
    ),
    "desabafo": (
        "FORMATO: DESABAFO CONTROLADO (emocional, intimo).\n"
        "- Mostra a dor/pressao real de quem gere — vulnerabilidade CONTROLADA, sem vitimismo.\n"
        "- Tom intimo, humano, de quem entende por dentro; cria comunidade (ex: 'Tem dia que o sindico so queria desligar o celular.'). Termina em reflexao/frase forte. CTA emocional."
    ),
    "escalada": (
        "FORMATO: A ESCALADA (tensao crescente, cinematografico).\n"
        "- Comeca numa situacao simples e PIORA a cada slide (caos crescente) ate um pico, depois reflexao final.\n"
        "- Cada slide eleva a tensao do anterior; prende ate o fim. Use micro-tensao. CTA de debate ou identificacao."
    ),
}


# Esqueleto emocional por nº de slides. RESPIRO = slide tipo 'frase';
# ultimo slide = sempre CTA. O FORMATO/tema encaixa dentro do arco.
_ESTRUTURA_POR_SLIDES: dict[int, str] = {
    5: "1 Gancho reconhecivel (cena/personagem concreto vivido) · 2 A crenca (o que todo mundo acha) · 3 A rachadura + a virada (verdade incomoda, com ancora) · 4 O custo / o que fazer · 5 CTA de posicionamento (escolha um lado)",
    6: "1 Gancho reconhecivel · 2 A crenca / a situacao · 3 A rachadura (o que ninguem fala) · 4 A virada (verdade incomoda + ancora) · 5 O custo / o que fazer · 6 CTA de posicionamento",
    7: "1 Gancho reconhecivel · 2 A crenca · 3 A rachadura · 4 Micro-tensao (abre loop) · 5 A virada (verdade incomoda + ancora) · 6 O custo / o que fazer · 7 CTA de posicionamento",
    8: "1 Gancho reconhecivel · 2 A crenca · 3 A rachadura · 4 A virada (verdade incomoda + ancora) · 5 RESPIRO (tipo 'frase') · 6 O custo / o que fazer · 7 Frase memoravel · 8 CTA de posicionamento",
    9: "1 Gancho reconhecivel · 2 Contexto/cena · 3 A crenca · 4 A rachadura · 5 Micro-tensao · 6 A virada (verdade incomoda + ancora) · 7 O custo / o que fazer · 8 Frase memoravel · 9 CTA de posicionamento",
    10: "1 Gancho reconhecivel · 2 Contexto/personagem · 3 A crenca · 4 A rachadura · 5 Micro-tensao · 6 A virada (verdade incomoda + ancora) · 7 RESPIRO (tipo 'frase') · 8 O custo / o que fazer · 9 Frase memoravel (manifesto) · 10 CTA de posicionamento",
}


def _gerar_copy(carrossel: dict[str, Any]) -> dict[str, Any]:
    """Gera os textos dos slides + legenda Instagram via GPT.

    Retorna dict com:
      - slides: list[{tipo, titulo, body}] — N slides conforme n_slides
      - legenda: str — legenda Instagram pronta pra colar
    """
    n_slides = int(carrossel.get("n_slides") or 6)
    titulo = (carrossel.get("titulo") or "").strip()
    tema = (carrossel.get("tema") or "").strip()
    formato = (carrossel.get("formato") or "historia_real").strip()
    briefing = (carrossel.get("briefing") or "").strip()
    objetivo = (carrossel.get("objetivo") or "").strip()

    formato_label = formato.replace("_", " ")
    instrucoes_formato = FORMATO_INSTRUCOES.get(
        formato,
        f"FORMATO: {formato_label} (estrutura livre, mantendo a voz e os 7 passos).",
    )
    casa = chr(0x1F3E1)
    is_by = _BRAND == "bysindicompany"
    is_consvicta = _BRAND == "consvictabr"
    obj_map_sindico = {
        "comentarios": "OBJETIVO: GERAR COMENTARIOS. CTA que gera DEBATE, coerente "
        "com a emocao — opiniao forte, posicionamento ou dilema (ex: 'Isso e "
        "convivencia ou abuso?', 'Ate onde vai o limite?', 'O problema comeca em "
        "quem?'). Binario SIM/NAO so quando a discussao for de fato binaria; nao "
        "repita sempre. Tema com dois lados defensaveis. Sucesso = debate, nao alcance.",
        "salvamentos": "OBJETIVO: GERAR SALVAMENTOS. Conteudo util e confiavel, "
        "linguagem objetiva. Ancore lei/artigo/numero. CTA 'Salva esse post' / "
        "'Manda no grupo do condominio'. Nunca CTA de debate.",
        "clientes": "OBJETIVO: ATRAIR CLIENTES. Mostre o caos, a dor, o antes e o "
        "resultado com numeros reais. Nunca venda direto. A marca pode aparecer e "
        "a tagline 'Por mais lares.' pode entrar no fechamento. CTA leve "
        "('Seu condominio esta assim?', 'A gente resolve', 'Link na bio').",
        "educar": "OBJETIVO: EDUCAR MORADORES. Surpresa + identificacao. Linguagem "
        "muito acessivel, sem juridiques. Primeiro o problema conhecido, depois o "
        "que ele nao sabia. CTA depende do tema (salvar OU debate binario).",
    }
    obj_map_by = {
        "comentarios": "OBJETIVO: DEBATE ENTRE SINDICOS. Identificacao + divisao "
        "entre sindicos profissionais. CTA tipo 'SINDICO OPERACIONAL ou ESTRATEGICO', "
        "'COBRARIA ou RELEVARIA', 'DEMITIRIA ou TREINARIA'. Temas: sindico que faz "
        "tudo sozinho, excesso de WhatsApp, conselho toxico, sindrome do sindico 24h, "
        "romantizacao da sobrecarga. NUNCA dica de condominio pro morador.",
        "salvamentos": "OBJETIVO: CRESCIMENTO PROFISSIONAL DO SINDICO. Ferramenta/"
        "framework/checklist que melhora a gestao. Muito escaneavel e pratico. CTA "
        "'Salva isso', 'Todo sindico precisa guardar', 'Manda pra outro sindico'.",
        "clientes": "OBJETIVO: ATRAIR SINDICOS PRO BY SINDICOMPANY. O sindico pensa "
        "'nao quero crescer sozinho'. By como ELITE DE MERCADO/estrutura/posicionamento "
        "- nunca franquia, nunca recrutamento comum. Mostra bastidores, equipe, "
        "suporte, processos, networking. Dor: fazer tudo sozinho, refem do WhatsApp, "
        "nao conseguir crescer. CTA seletivo ('Talvez o proximo passo da sua "
        "sindicatura seja esse', 'Nem todo sindico esta pronto pra crescer assim').",
        "autoridade": "OBJETIVO: POSICIONAR AUTORIDADE NO MERCADO. Eleva o By como "
        "REFERENCIA em sindicatura profissional. Linguagem sofisticada, estrategica, "
        "menos emocional, menos humor. Temas: futuro da sindicatura, profissionalizacao "
        "do mercado, erros estruturais do setor, gestao por dados, sindico como "
        "empresario. CTA institucional ('O mercado mudou', 'A sindicatura esta "
        "evoluindo', 'Por mais sindicos preparados'). Bom com formato Manifesto/"
        "tendencia/dado que choca/visao estrategica.",
    }
    obj_map = obj_map_by if is_by else obj_map_sindico
    objetivo_bloco = (f"\n{obj_map[objetivo]}\n" if objetivo in obj_map else "")
    if is_by:
        persona = (
            "Voce e redator do @bysindicompany — marca da Sindicompany pra SINDICOS "
            "PROFISSIONAIS, aspirantes a sindicatura e sindicos em crescimento. NAO "
            "fala com o morador. Tom aspiracional, provocativo, estrategico, "
            "empresarial. Vende estrutura, pertencimento, crescimento, posicionamento, "
            "autoridade, escala, networking, suporte. Fale como mentor que ja chegou."
        )
        assinatura = "By Sindicompany. Sindicatura no proximo nivel."
    elif is_consvicta:
        persona = (
            "Voce e redator do @consvictabr (Consvicta). Tom claro, atual, proximo "
            "de quem le, sem maquiar. Frases curtas e diretas. Voz propria; comece "
            "dentro da cabeca do leitor. Sem gerundio decorativo, sem clichês "
            "corporativos, sem cliche motivacional."
        )
        assinatura = "Consvicta."
    else:
        persona = (
            "Voce e redator do @sindicompanybr (Sindicompany — sindicos "
            "profissionais SP/RJ). VOCE FALA COM O MORADOR COMUM, nao com o sindico. "
            "Escreve como pessoa inteligente corrigindo um amigo, NUNCA como empresa "
            "instruindo cliente."
        )
        assinatura = f"Por mais lares. {casa}"
    if is_consvicta:
        contexto = (
            "- Contexto: gestao condominial BOUTIQUE — administradora que conhece "
            "o predio pelo nome. Pelo angulo de DECISAO, GOVERNANCA, PRESTACAO DE "
            "CONTAS, conselho × administradora. Pelo menos UM slide menciona "
            "'condominio', 'administracao condominial' ou 'gestao' literal.\n"
        )
    elif is_by:
        contexto = (
            "- Contexto: bastidores e realidade da SINDICATURA PROFISSIONAL — gestao, "
            "lideranca, mercado, carreira, estrutura. Quando falar de condominio, e "
            "sempre pelo angulo de quem GERE, nao de quem mora.\n"
        )
    else:
        contexto = (
            "- Contexto condominial sempre (assembleia, taxa, sindico, morador, "
            "area comum, regulamento, convivencia, fachada, manutencao). Pelo menos "
            "UM slide menciona 'condominio' ou 'condominial' literal.\n"
        )
    anti_leak = (
        "- PROIBIDO mencionar 'Sindicompany', 'By Sindicompany', '@sindicompanybr', "
        "'@bysindicompany' ou qualquer outra administradora alem da Consvicta. "
        "Concorrentes NUNCA aparecem nos slides nem na legenda.\n"
        "- PROIBIDO usar 'Por mais lares' — nao e tagline da Consvicta. A "
        "assinatura correta e 'Administracao condominial que entrega resultado.'\n"
        if is_consvicta
        else ""
    )
    extra_negra = (
        ", o sucesso e uma jornada, acredite no seu potencial, saia da zona de "
        "conforto, o ceu e o limite, mindset vencedor"
        if is_by
        else ""
    )

    prompt = (
        f"{persona}\n\n"
        f"{objetivo_bloco}"
        f"BRIEFING:\n"
        f"- Título interno: {titulo}\n"
        f"- Tema: {tema}\n"
        f"- Formato: {formato_label}\n"
        f"- Quantidade de slides: {n_slides}\n"
        + (f"- Contexto extra: {briefing}\n" if briefing else "")
        + f"\n{instrucoes_formato}\n\n"
        + (
            "IMPORTANTE: quando objetivo e formato apontarem direcoes "
            "diferentes, o OBJETIVO manda (CTA, tom, estrutura).\n\n"
            if objetivo_bloco
            else ""
        )
        + f"VOZ (vale pra TODOS os formatos):\n"
        f"Estrutura narrativa do post de maior alcance: CENA concreta (comeca no meio) -> "
        f"SUPOSICAO do leitor (termina com 'ne?'/'certo?') -> CONTRADICAO em <=3 palavras -> "
        f"EXPLICACAO uma ideia por frase -> FECHAMENTO paradoxal/quotavel -> CTA binario/escala. "
        f"A ASSINATURA '{assinatura}' aparece SO na legenda, nunca nos slides. "
        f"Use a estrutura de slides do FORMATO acima; a voz aqui e o tom de cada slide.\n\n"
        f"REGRAS GERAIS:\n"
        f"- Capa: NUNCA escreva o tema '{tema}' como titulo nem o repita literalmente — o tema e so o ASSUNTO que guia o conteudo, nao vira texto do slide. A capa entra DIRETO no gancho. Capa inteira (titulo + body) tem no max 20 palavras.\n"
        f"- HOOK DA CAPA (prioridade maxima): o titulo da capa e a frase que PARA O SCROLL — verdade incomoda, identificacao, tensao ou curiosidade. Curto, leitura instantanea no celular. NUNCA slogan corporativo ou frase que comeca devagar.\n"
        f"- DESTAQUE DO HOOK: envolva o trecho MAIS FORTE do hook (2 a 5 palavras) entre [[ ]] — ex: 'WhatsApp [[nao e assembleia]].'. So no titulo da capa.\n"
        f"- ANCORAS DE ATENCAO (retencao): nos slides de conteudo, marque com [[ ]] no BODY no maximo 1 trecho de alto impacto por slide (+1 secundario no maximo) — verdade incomoda, identificacao, tensao, frase memoravel ou PALAVRA MAGNETICA (caos, silencio, pressao, desgaste, autoridade, conflito, refem, invisivel, bastidor, premium, processo, improviso, abandono, controle, presenca, sobrecarga, suporte, confianca, clareza, metodo, crise). NUNCA mais de 2 por slide.\n"
        f"- CTA DE POSICIONAMENTO (formula campea — vale pra TODO formato): o ULTIMO slide SEMPRE forca o leitor a TOMAR UM LADO e comentar — e o que mais viraliza. De DUAS opcoes concretas e carregadas (nunca genericas) e peca o voto: binario ('[[Comenta SIM ou NAO]]') ou de lado ('Voce teria votado com os 12 ou os 8? [[Comenta 12 ou 8]]' + 1 linha curta legendando cada lado: '12 = sindico profissional · 8 = ficava com o Carlos'). Marque entre [[ ]] APENAS a ACAO (2 a 5 palavras), nunca uma frase inteira. NUNCA termine so com frase memoravel. So em post claramente utilitario (modelo/script, checklist) vale trocar por '[[Salva esse post]]'/'[[Manda no grupo]]' — mas o DEFAULT e escolher um lado. PROIBIDO o CTA preguicoso 'Concorda?'/'O que acha?' SEM dois lados concretos.\n"
        f"- ESTRUTURA (FORMULA CAMPEA — siga este esqueleto, encaixando o FORMATO/tema): {_ESTRUTURA_POR_SLIDES.get(n_slides, 'Gancho reconhecivel -> a crenca (o que todo mundo acha) -> a rachadura (o que ninguem fala) -> a virada (verdade incomoda + ancora) -> o custo/o que fazer -> CTA de posicionamento')}. O motor de TODO post: pega uma crenca que o publico tem, mostra com cena/personagem concreto que ela esta errada ou e mais complexa, e forca o leitor a tomar posicao. Slides RESPIRO usam tipo 'frase'. Alterne o tom (tensao, identificacao, reflexao); nunca o mesmo por varios slides. Use MINI PLOT TWIST quando couber.\n"
        f"- VOZ HUMANA: frases falaveis, ritmo oral, sem juridiques nem academiques. EFEITO ESPELHO: ao menos 1 frase que faca pensar 'isso sou eu'. AUTORIDADE INVISIVEL: nunca dizer 'somos referencia'; a autoridade aparece na clareza e na observacao humana.\n"
        f"- IMPERFEICAO HUMANA: nao soe polido demais o tempo todo. Use frases secas, curtas, quebradas quando couber ('E ai comeca o problema.', 'E isso pesa.'). Parece escrito por alguem de DENTRO, nao por IA.\n"
        f"- DENSIDADE VARIAVEL: nunca todos os slides igualmente carregados. Emocional/memoravel/respiro = pouco texto; tecnico = mais. O ritmo segura a leitura.\n"
        f"- Cada slide interno: tipo + titulo (3-7 palavras) + body (1-3 frases curtas, max 35 palavras).\n"
        f"- MICRO-TENSAO (retencao entre slides): os slides do MEIO terminam com um gancho que puxa o proximo (curiosidade, tensao, continuacao), nunca 100% fechados. Marque a frase de tensao/cliffhanger entre ~~ ~~ (vira SUBLINHADO, distinto do grifo do [[ ]]) — ex: '~~Mas o problema comeca depois.~~'. Evite explicacao tecnica continua e slides conclusivos no meio. So o ULTIMO slide (CTA) e a frase final memoravel podem fechar.\n"
        f"- VERDADE HUMANA (o que MAIS viraliza): condominio e comportamento humano. Prefira observacoes reais da vida que facam pensar 'isso e MUITO verdade' a explicacao tecnica. Ex: 'O problema raramente comeca no problema.', 'Sindico forte tambem cansa.', 'O grupo do WhatsApp muda o comportamento das pessoas.'.\n"
        f"- ABERTURA: depois do hook, o slide 2 entra DIRETO na emocao/situacao/conflito — nunca introducao corporativa, 'texto de palestra' ou explicacao lenta.\n"
        f"- GATILHO DE COMPARTILHAMENTO: construa pensando 'por que alguem mandaria isso pra outra pessoa?'. Ative ao menos um: indireta social, identificacao ('isso sou eu'), 'finalmente alguem falou', alerta, status/inteligencia ou pertencimento.\n"
        f"- FRASE PRINTAVEL + INDIRETA SOCIAL: inclua ao menos 1 frase digna de print/repost, forte e memoravel (ex: 'Condominio nao funciona no grito. Funciona no processo.'). Vale a indireta (parece reflexao, e indireta): 'Tem morador que quer regra. Ate a regra chegar nele.'.\n"
        f"- RESPIRO VISUAL (ritmo): alterne slides densos e leves; NUNCA todos com a mesma densidade. Inclua ao menos 1 slide com tipo 'frase': SO uma frase curta e memoravel, com body vazio — vai num layout limpo e centralizado.\n"
        f"- SENSACAO EDITORIAL: o carrossel deve parecer revista/manifesto, nao post de marketing generico. Menos texto, mais peso.\n"
        f"- NUNCA cite numero de apartamento/unidade nem nome de condominio (real ou inventado) em nenhum slide ou legenda.\n"
        f"- Em posts educativos (mito, dado, tutorial, lista juridica): pelo menos UMA ancora — artigo (ex: 'Codigo Civil, art. 1.336'), decisao judicial (ex: 'STJ, REsp 1.699.022/SP, 2019') OU dado com fonte nomeada e datada.\n"
        f"{contexto}"
        f"{anti_leak}\n"
        f"LEGENDA Instagram: replica a narrativa em texto corrido (4-8 linhas), hook na primeira linha, termina OBRIGATORIAMENTE com '{assinatura}' e EXATAMENTE 3 hashtags na linha seguinte"
        + (" (use #consvicta + 2 hashtags do tema — JAMAIS #sindicompany ou #bysindicompany)" if is_consvicta else "")
        + ".\n\n"
        f"REGRAS DE PORTUGUES E VOZ:\n"
        f"- Acentos corretos em toda palavra: voce, sindico, condominio, gestao, esta, sao.\n"
        f"- Fale 'voce', voz ativa, sujeito explicito. Frase curta: um sujeito, um predicado, acabou.\n"
        f"- PROIBIDO: gerundio (evitando, garantindo, proporcionando), travessao (—), aspas curvas (“”), emoji decorativo no slide, frases de introducao ('e importante ressaltar', 'vale destacar', 'nesse contexto'), CTA comercial em post educativo ('Fale com a Sindicompany').\n"
        f"- LISTA NEGRA: papel fundamental, momento crucial, cenario em constante evolucao, destacando a importancia, o futuro e promissor, juntos somos mais fortes, destaca-se, vibrante, no coracao de, em meio a, reflete a, simboliza a, evidencia a, um verdadeiro testemunho, desafios e oportunidades, rica diversidade, nao apenas X mas tambem Y, mergulhando em, celebrando a, fomentando o, pavimentando o caminho, estudos mostram, especialistas afirmam{extra_negra}.\n"
        f"- Use exemplos concretos (artigos de lei, REsp, numeros, acoes reais).\n\n"
        f"Devolva JSON estrito (sem markdown):\n"
        f'{{ "slides": [{{"tipo":"capa","titulo":"...","body":"..."}}, '
        f'{{"tipo":"texto","titulo":"...","body":"..."}}, ... '
        f'(total {n_slides} slides) ], "legenda":"..." }}'
    )

    marca_fallback = (
        "Consvicta"
        if is_consvicta
        else "By Sindicompany"
        if is_by
        else "Sindicompany"
    )
    hashtags_fallback = (
        "#consvicta #condominio #gestaocondominial"
        if is_consvicta
        else "#bysindicompany #sindico #gestaocondominial"
        if is_by
        else "#sindicompany #condominio #sindico"
    )
    fallback = {
        "slides": (
            [
                {
                    "tipo": "capa",
                    "titulo": titulo or tema or marca_fallback,
                    "body": "",
                }
            ]
            + [
                {
                    "tipo": "texto",
                    "titulo": f"Ponto {i}",
                    "body": "Conteúdo do slide.",
                }
                for i in range(2, n_slides)
            ]
            + [
                {
                    "tipo": "cta",
                    "titulo": "O que você acha?",
                    "body": "Comenta aqui embaixo.",
                }
            ]
        )[:n_slides],
        "legenda": (
            f"{titulo or tema}\n\n"
            f"Conta nos comentários se você já passou por isso.\n\n"
            f"{hashtags_fallback}"
        ),
    }

    data = _gerar_json(prompt, fallback, expected_keys=["slides"])
    # Garante n_slides exato
    slides = list(data.get("slides") or [])[:n_slides]
    while len(slides) < n_slides:
        slides.append({"tipo": "texto", "titulo": "", "body": ""})
    data["slides"] = slides
    return data


# =============================================================================
# HTML render
# =============================================================================


FORMATO_LABELS = {
    "historia_real": "História Real",
    "lista": "Lista",
    "mito_verdade": "Mito vs Verdade",
    "antes_depois": "Antes / Depois",
    "dado_choca": "Dado que Choca",
    "tutorial": "Tutorial Rápido",
    "opiniao": "Opinião Forte",
    "hook_punch": "Hook Punch",
    "pov": "POV",
    "tweet": "Tweet",
    "expectativa_realidade": "Expectativa vs Realidade",
    "erro_fatal": "Erro Fatal",
    "bastidor": "Bastidor Real",
    "camada_invisivel": "Camada Invisível",
    "dialogo": "Diálogo",
    "desabafo": "Desabafo",
    "escalada": "A Escalada",
}


def _formato_label(formato: str) -> str:
    """Devolve o rotulo amigavel do formato (ja em titulo). Se for um
    valor desconhecido, faz best-effort trocando _ por espaco."""
    f = (formato or "").strip().lower()
    return FORMATO_LABELS.get(f, f.replace("_", " ").title() or "Carrossel")


_SC_NAVY = "#182028"
_SC_CYAN = "#88C8D0"
_SC_BEIGE = "#E0B098"
_SC_LAVENDER = "#BFC0FF"
_SC_PURPLE = "#8890D0"
_SC_PAPER = "#FAF7F2"
_SC_PAPER_WARM = "#F2EDE5"


def _extract_stat(titulo: str) -> tuple[str, str]:
    """Tenta destacar um numero/percent/multiplicador do titulo pros
    arquetipos "Stat slap" e "Numbered guide". Devolve (num, resto).
    Casos: "87% aprovam" -> ("87%", "aprovam"); "3x mais" ->
    ("3x", "mais"); "Pintura nova" -> ("", "Pintura nova")."""
    m = re.search(r"\d{1,4}(?:[.,]\d+)?\s*(?:%|x|X)?", titulo)
    if not m:
        return ("", titulo)
    num = m.group(0).replace(" ", "")
    resto = (titulo[: m.start()] + titulo[m.end():]).strip()
    resto = re.sub(r"\s+", " ", resto).strip(" .,-—–")
    return (num, resto)


def _capa_editorial_question(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — arquetipo de capa "Editorial Question".

    Duas variantes selecionadas automaticamente conforme presenca de
    foto_capa_url:

    1. SEM FOTO (minimalista): Fundo Paper, faixa Beige no topo,
       titulo Epilogue 800 com fracao italic Purple + roman Navy,
       simbolo Sindicompany no canto inferior direito, handle Cyan.

    2. COM FOTO ("Editorial Photo"): Foto ocupa metade superior
       (45% da altura). Faixa Beige fina (4%) separa foto e bloco
       de texto. Metade inferior em fundo Paper com pergunta italic
       Purple + roman Navy. Simbolo pequeno no canto inferior direito.

    Paleta hardcoded das constantes Brand Hub (nao usa _palette()
    legacy). Mantem logo_top_img no topo pra consistencia com os
    outros slides do mesmo carrossel. Aplica so pras marcas Sindicompany
    (sindicompanybr + bysindicompany), nunca Consvicta.
    """
    NAVY = _SC_NAVY
    CYAN = _SC_CYAN
    BEIGE = _SC_BEIGE
    PURPLE = _SC_PURPLE
    PAPER = _SC_PAPER
    PAPER_WARM = _SC_PAPER_WARM

    # Simbolo Sindicompany no canto inferior direito. Pegamos um logo
    # menor (slot 2 ou 3) e filtramos pra Navy via CSS. Vazio se nao
    # houver upload — slide funciona sem.
    symbol_url = _logo_slot_data_url(2) or _logo_slot_data_url(3) or ""
    symbol_img = (
        f'<img class="corner-symbol" src="{symbol_url}" alt="" />'
        if symbol_url
        else ""
    )

    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )

    # Split do titulo: a primeira sentenca/frase ate o "?" ganha
    # destaque italic Purple; o resto fica em Navy roman. Best-effort
    # pra qualquer titulo (se nao tiver "?", titulo inteiro vai roman).
    titulo_h = _h(titulo)
    if "?" in titulo_h:
        head, _, tail = titulo_h.partition("?")
        titulo_render = (
            f'<span class="q">{head}?</span>'
            f'<span class="rest">{tail.strip()}</span>'
            if tail.strip()
            else f'<span class="q">{head}?</span>'
        )
    else:
        titulo_render = f'<span class="rest">{titulo_h}</span>'

    has_photo = bool(foto_capa_url)

    # === Variante COM FOTO ===
    if has_photo:
        return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {PAPER};
    color: {NAVY};
    overflow: hidden;
    position: relative;
  }}
  .photo {{
    /* Foto ocupa 45% do topo — proporcao editorial classica do
       Brand Hub (foto grande mas deixa metade pra respiro). */
    position: absolute; top: 0; left: 0; right: 0;
    height: 45%;
    background-image: url('{foto_capa_url}');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .divider {{
    /* Faixa Beige fina (4%) entre foto e bloco de texto. */
    position: absolute; left: 0; right: 0;
    top: 45%; height: 4%;
    background: linear-gradient(180deg, {BEIGE} 0%, {PAPER_WARM} 100%);
    z-index: 1;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .content {{
    /* Bloco de texto na metade inferior, abaixo da divider. */
    position: absolute;
    left: 180px; right: 180px;
    top: 53%; bottom: 220px;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    line-height: 0.98;
    letter-spacing: -0.025em;
    text-wrap: balance;
  }}
  .capa-titulo .q {{
    color: {PURPLE};
    font-style: italic;
    font-weight: 800;
  }}
  .capa-titulo .rest {{
    color: {NAVY};
    display: block;
    margin-top: 0.15em;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 78px;
    line-height: 1.30;
    color: {NAVY};
    opacity: 0.78;
    margin-top: 60px;
    max-width: 28ch;
  }}
  .corner-symbol {{
    /* Simbolo menor na variante com foto (deixa o texto respirar). */
    position: absolute;
    bottom: 80px; right: 180px;
    width: 320px; height: 320px;
    object-fit: contain;
    z-index: 1;
    filter: brightness(0) saturate(100%);
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="photo"></div>
  <div class="divider"></div>
  <div class="content">
    <h1 class="capa-titulo">{titulo_render}</h1>
    {body_html}
  </div>
  {symbol_img}
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""

    # === Variante SEM FOTO (minimalista) ===
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {PAPER};
    color: {NAVY};
    overflow: hidden;
    position: relative;
  }}
  .top-band {{
    /* Faixa quente de 8% no topo — assina o arquetipo Editorial. */
    position: absolute; top: 0; left: 0; right: 0;
    height: 8%;
    background: linear-gradient(180deg, {BEIGE} 0%, {PAPER_WARM} 100%);
    z-index: 0;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 18%; bottom: 28%;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 280px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    text-wrap: balance;
  }}
  .capa-titulo .q {{
    color: {PURPLE};
    font-style: italic;
    font-weight: 800;
  }}
  .capa-titulo .rest {{
    color: {NAVY};
    display: block;
    margin-top: 0.15em;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 92px;
    line-height: 1.30;
    color: {NAVY};
    opacity: 0.78;
    margin-top: 80px;
    max-width: 26ch;
  }}
  .corner-symbol {{
    position: absolute;
    bottom: 80px; right: 180px;
    width: 640px; height: 640px;
    object-fit: contain;
    z-index: 1;
    filter: brightness(0) saturate(100%);
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 72px;
    font-weight: 600;
    color: {CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="top-band"></div>
  <div class="content">
    <h1 class="capa-titulo">{titulo_render}</h1>
    {body_html}
  </div>
  {symbol_img}
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_stat_slap(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",  # nao usada — capa sem foto por design
) -> str:
    """Brand Hub 2026-05-17 — capa 03 "Stat slap".

    Numero gigante (extraido do titulo) ocupando o centro, fundo Beige
    quente, resto do titulo + body abaixo. Se o titulo nao tiver numero,
    cai num layout "first word giant" usando a primeira palavra do
    titulo como protagonista visual."""
    del foto_capa_url
    num, resto = _extract_stat(titulo)
    if not num:
        parts = titulo.strip().split(" ", 1)
        num = parts[0]
        resto = parts[1] if len(parts) > 1 else ""
    body_html = f'<p class="capa-body">{_h(body)}</p>' if body else ""
    resto_html = (
        f'<p class="resto">{_h(resto)}</p>' if resto else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_BEIGE};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .stat {{
    position: absolute;
    left: 180px; right: 180px;
    top: 26%;
    font-family: {font_display};
    font-weight: 800;
    font-size: 1400px;
    line-height: 0.82;
    letter-spacing: -0.05em;
    color: {_SC_NAVY};
    text-align: left;
    z-index: 2;
  }}
  .resto {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 520px;
    font-family: {font_display};
    font-weight: 800;
    font-size: 180px;
    line-height: 0.98;
    letter-spacing: -0.02em;
    color: {_SC_NAVY};
    text-wrap: balance;
    z-index: 2;
  }}
  .capa-body {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 320px;
    font-family: {font_body};
    font-size: 78px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    max-width: 28ch;
    z-index: 2;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="stat">{_h(num)}</div>
  {resto_html}
  {body_html}
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_numbered_guide(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 04 "Numbered guide".

    Split vertical: numero grande Navy na esquerda (50%), headline +
    body Navy na direita (50%) sobre fundo Paper. Numero vem do
    titulo via _extract_stat; fallback "01" se o titulo nao tiver
    numero (caso comum em guia "passo a passo")."""
    del foto_capa_url
    num, resto = _extract_stat(titulo)
    if not num:
        num = "01"
        resto = titulo
    body_html = f'<p class="capa-body">{_h(body)}</p>' if body else ""
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .left {{
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 50%;
    display: flex; align-items: center; justify-content: center;
    z-index: 2;
  }}
  .num {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 1500px;
    line-height: 0.82;
    letter-spacing: -0.06em;
    color: {_SC_NAVY};
  }}
  .right {{
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 50%;
    padding: 0 180px 0 60px;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 2;
  }}
  .resto {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 78px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 60px;
    max-width: 24ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="left"><div class="num">{_h(num)}</div></div>
  <div class="right">
    <h1 class="resto">{_h(resto)}</h1>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_manifesto(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 05 "Manifesto".

    Tipografia gigante italic sobre fundo Cyan. Headline em peso 800
    italic ocupa quase a tela toda, body Navy menor abaixo. Sem
    enfeite, sem foto — a frase eh o evento."""
    del foto_capa_url
    body_html = f'<p class="capa-body">{_h(body)}</p>' if body else ""
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_CYAN};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 20%; bottom: 26%;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-style: italic;
    font-size: 320px;
    line-height: 0.94;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 88px;
    line-height: 1.28;
    color: {_SC_NAVY};
    opacity: 0.82;
    margin-top: 80px;
    max-width: 26ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_pattern_explosion(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 06 "Pattern explosion".

    Faixa de pattern hero ocupando os 45% superiores, card Paper na
    base com headline + body. Usa o primeiro pattern disponivel da
    biblioteca; sem pattern, cai num fundo Lavender flat (mesma silhueta
    visual, sem quebrar layout)."""
    del foto_capa_url
    patterns = _patterns_data_urls()
    pattern_url = patterns[0] if patterns else ""
    pattern_top = (
        f'<div class="pattern-top" style="background-image: url(\'{pattern_url}\')"></div>'
        if pattern_url
        else '<div class="pattern-top pattern-fallback"></div>'
    )
    body_html = f'<p class="capa-body">{_h(body)}</p>' if body else ""
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .pattern-top {{
    position: absolute; top: 0; left: 0; right: 0;
    height: 45%;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .pattern-fallback {{
    background: {_SC_LAVENDER};
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .card {{
    position: absolute;
    left: 0; right: 0;
    top: 45%; bottom: 0;
    background: {_SC_PAPER};
    padding: 140px 180px 220px;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 240px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 82px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 70px;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {pattern_top}
  <div class="card">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_headline_only(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 14 "Headline-only".

    Tipografia gigante roman sobre fundo Beige, sem foto, sem ornamento.
    Mesma logica do Manifesto mas sem italic e em fundo quente."""
    del foto_capa_url
    body_html = f'<p class="capa-body">{_h(body)}</p>' if body else ""
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_BEIGE};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 18%; bottom: 26%;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 360px;
    line-height: 0.92;
    letter-spacing: -0.03em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 88px;
    line-height: 1.28;
    color: {_SC_NAVY};
    opacity: 0.82;
    margin-top: 80px;
    max-width: 26ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_dark_premium(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 02 "Dark Premium".

    Foto full-bleed + gradient Navy (transparente no topo → opaco em
    baixo) + headline branca grande ancorada na base. Sem foto cai num
    fundo Navy solido com a mesma headline no mesmo lugar."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_layer = (
            f'<div class="photo" style="background-image: url(\'{foto_capa_url}\')"></div>'
            '<div class="gradient"></div>'
        )
    else:
        photo_layer = '<div class="solid-navy"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_NAVY};
    color: #ffffff;
    overflow: hidden;
    position: relative;
  }}
  .photo {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .solid-navy {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: {_SC_NAVY};
    z-index: 0;
  }}
  .gradient {{
    /* Gradient Navy cobrindo a metade inferior pra texto legivel. */
    position: absolute; top: 35%; left: 0; right: 0; bottom: 0;
    background: linear-gradient(180deg,
      rgba(24,32,40,0.0) 0%,
      rgba(24,32,40,0.85) 45%,
      rgba(24,32,40,0.97) 100%);
    z-index: 1;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 280px;
    z-index: 3;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 260px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: #ffffff;
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 82px;
    line-height: 1.30;
    color: #ffffff;
    opacity: 0.82;
    margin-top: 60px;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {photo_layer}
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_magazine_cover(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 07 "Magazine cover".

    Tres bandas verticais: masthead Navy no topo (~14% altura) com o
    logo, foto central (~52%) sem corte de rosto, faixa Paper na base
    (~34%) com headline + body. Sem foto cai num fundo Beige na faixa
    central, mantendo a estrutura editorial."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_band = (
            f'<div class="photo-band" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        photo_band = '<div class="photo-band photo-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .masthead {{
    position: absolute; top: 0; left: 0; right: 0;
    height: 14%;
    background: {_SC_NAVY};
    z-index: 0;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .photo-band {{
    position: absolute; left: 0; right: 0;
    top: 14%; height: 52%;
    background-size: cover;
    background-position: center top;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .photo-fallback {{
    background: {_SC_BEIGE};
  }}
  .paper-band {{
    position: absolute; left: 0; right: 0;
    top: 66%; bottom: 0;
    background: {_SC_PAPER};
    padding: 110px 180px 220px;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 1;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 78px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 60px;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="masthead"></div>
  {photo_band}
  <div class="paper-band">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_split_portrait(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 11 "Split portrait".

    Split vertical 45/55: foto retrato a esquerda em 45% da largura,
    bloco de texto Paper a direita em 55% com headline Navy + body.
    Sem foto a faixa esquerda vira um fundo Beige solido, mantendo a
    geometria editorial."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_col = (
            f'<div class="photo-col" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        photo_col = '<div class="photo-col photo-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .photo-col {{
    position: absolute; left: 0; top: 0; bottom: 0;
    width: 45%;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .photo-fallback {{
    background: {_SC_BEIGE};
  }}
  .text-col {{
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 55%;
    padding: 180px 180px 220px 120px;
    display: flex; flex-direction: column; justify-content: center;
    z-index: 1;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: calc(45% + 120px);
    width: calc(55% - 300px); max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 200px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 72px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 60px;
    max-width: 22ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: calc(45% + 120px);
    font-family: {font_body};
    font-size: 60px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {photo_col}
  <div class="text-col">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_hero_portrait(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 25 "Hero portrait".

    Foto full-bleed cobrindo tudo + tag mono "PERFIL · ED.05" no topo
    centrada sobre faixa Navy translucida + box Beige ancorada na base
    com headline Navy. Sem foto: faixa hero vira Navy solido, mantendo
    tag + box."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_layer = (
            f'<div class="photo" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        photo_layer = '<div class="photo photo-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_NAVY};
    color: #ffffff;
    overflow: hidden;
    position: relative;
  }}
  .photo {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .photo-fallback {{
    background: {_SC_NAVY};
  }}
  .tag-bar {{
    position: absolute; top: 0; left: 0; right: 0;
    height: 11%;
    background: rgba(24,32,40,0.65);
    display: flex; align-items: center; justify-content: center;
    z-index: 2;
  }}
  .tag {{
    font-family: {font_body};
    font-size: 60px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #ffffff;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .beige-box {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 220px;
    background: {_SC_BEIGE};
    padding: 120px 110px;
    z-index: 3;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 200px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 72px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.82;
    margin-top: 50px;
    max-width: 26ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {photo_layer}
  <div class="tag-bar"><span class="tag">PERFIL · {_brand_label().upper()}</span></div>
  {logo_top_img}
  <div class="beige-box">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_avatar_quote(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 33 "Avatar quote".

    Fundo Paper, aspas Beige gigantes no topo, citacao italic Navy
    (body) ocupando o meio, avatar circular pequeno + atribuicao
    (titulo) na base. Sem foto: avatar vira um circulo Beige solido
    mantendo o ritmo visual."""
    avatar_bg = (
        f"background-image: url('{foto_capa_url}'); background-size: cover; background-position: center;"
        if foto_capa_url
        else f"background: {_SC_BEIGE};"
    )
    quote_text = body or titulo
    attribution = (
        f'<div class="attribution">{_h(titulo)}</div>'
        if body and titulo
        else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .marks {{
    position: absolute;
    top: 460px; left: 180px;
    font-family: {font_display};
    font-weight: 800;
    font-size: 820px;
    line-height: 0.7;
    color: {_SC_BEIGE};
    z-index: 1;
    pointer-events: none;
  }}
  .quote {{
    position: absolute;
    left: 180px; right: 180px;
    top: 36%;
    font-family: {font_display};
    font-style: italic;
    font-weight: 500;
    font-size: 200px;
    line-height: 1.1;
    letter-spacing: -0.015em;
    color: {_SC_NAVY};
    text-wrap: balance;
    z-index: 2;
  }}
  .avatar-row {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 320px;
    display: flex; align-items: center;
    z-index: 3;
  }}
  .avatar {{
    width: 280px; height: 280px;
    border-radius: 50%;
    background-repeat: no-repeat;
    flex-shrink: 0;
    {avatar_bg}
  }}
  .attribution {{
    margin-left: 60px;
    font-family: {font_body};
    font-weight: 600;
    font-size: 76px;
    line-height: 1.20;
    color: {_SC_NAVY};
    letter-spacing: -0.01em;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="marks">&ldquo;</div>
  {logo_top_img}
  <div class="quote">{_h(quote_text)}</div>
  <div class="avatar-row">
    <div class="avatar"></div>
    {attribution}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_photo_circle(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 38 "Foto circular".

    Fundo Paper. Foto recortada num circulo grande CENTRALIZADO no topo
    do slide (~2200px de diametro), com a imagem sempre centralizada
    dentro do circulo (background-position: center center). Texto
    inferior esquerdo com headline grande Navy + body. Sem foto:
    circulo vira Beige solido, preservando a geometria."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    circle_style = (
        f"background-image: url('{foto_capa_url}'); background-size: cover; background-position: center center;"
        if foto_capa_url
        else f"background: {_SC_BEIGE};"
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .photo-circle {{
    position: absolute;
    top: 420px;
    left: 50%;
    transform: translateX(-50%);
    width: 2200px; height: 2200px;
    border-radius: 50%;
    {circle_style}
    box-shadow: 0 60px 120px rgba(24,32,40,0.18);
    z-index: 1;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 180px;
    right: 180px;
    bottom: 320px;
    text-align: center;
    z-index: 3;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 200px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 72px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.82;
    margin-top: 50px;
    max-width: 28ch;
    margin-left: auto; margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  <div class="photo-circle"></div>
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_pull_quote(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 10 "Pull quote".

    Fundo Paper. Par de aspas Beige gigantes no topo, citacao italic
    Navy (body, ou titulo se body vazio) ocupando o centro, atribuicao
    mono na base. Capa sem foto por design."""
    del foto_capa_url
    quote_text = body or titulo
    attribution_text = titulo if body else ""
    attribution_html = (
        f'<div class="attribution">— {_h(attribution_text)}</div>'
        if attribution_text
        else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .marks {{
    position: absolute;
    top: 380px; left: 160px;
    font-family: {font_display};
    font-weight: 800;
    font-size: 1100px;
    line-height: 0.7;
    color: {_SC_BEIGE};
    z-index: 1;
    pointer-events: none;
  }}
  .quote {{
    position: absolute;
    left: 220px; right: 220px;
    top: 40%;
    font-family: {font_display};
    font-style: italic;
    font-weight: 500;
    font-size: 240px;
    line-height: 1.08;
    letter-spacing: -0.015em;
    color: {_SC_NAVY};
    text-wrap: balance;
    z-index: 2;
  }}
  .attribution {{
    position: absolute;
    left: 220px;
    bottom: 320px;
    font-family: {font_body};
    font-weight: 600;
    font-size: 72px;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  <div class="marks">&ldquo;</div>
  {logo_top_img}
  <div class="quote">{_h(quote_text)}</div>
  {attribution_html}
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_glow_hero(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 23 "Glow hero".

    Fundo Navy, simbolo Sindicompany gigante no centro com dois glows
    radiais atras (Cyan + Beige). Headline Branca abaixo do simbolo,
    body sutil. Capa sem foto por design."""
    del foto_capa_url
    symbol_url = (
        _logo_slot_data_url(2)
        or _logo_slot_data_url(3)
        or _logo_slot_data_url(1)
        or ""
    )
    symbol_img = (
        f'<img class="hero-symbol" src="{symbol_url}" alt="" />'
        if symbol_url
        else '<div class="hero-symbol-fallback"></div>'
    )
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_NAVY};
    color: #ffffff;
    overflow: hidden;
    position: relative;
  }}
  .glow-a {{
    position: absolute;
    top: 18%; left: 50%;
    transform: translateX(-50%);
    width: 2200px; height: 2200px;
    border-radius: 50%;
    background: radial-gradient(circle, {_SC_CYAN} 0%, rgba(136,200,208,0) 60%);
    opacity: 0.55;
    filter: blur(80px);
    z-index: 1;
    pointer-events: none;
  }}
  .glow-b {{
    position: absolute;
    top: 22%; left: 50%;
    transform: translateX(-50%);
    width: 1600px; height: 1600px;
    border-radius: 50%;
    background: radial-gradient(circle, {_SC_BEIGE} 0%, rgba(224,176,152,0) 65%);
    opacity: 0.45;
    filter: blur(60px);
    z-index: 2;
    pointer-events: none;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .hero-symbol {{
    position: absolute;
    top: 22%; left: 50%;
    transform: translateX(-50%);
    width: 1100px; height: 1100px;
    object-fit: contain;
    filter: brightness(0) invert(1);
    z-index: 3;
  }}
  .hero-symbol-fallback {{
    position: absolute;
    top: 28%; left: 50%;
    transform: translateX(-50%);
    width: 800px; height: 800px;
    border-radius: 50%;
    background: rgba(255,255,255,0.08);
    border: 4px solid rgba(255,255,255,0.18);
    z-index: 3;
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 320px;
    text-align: center;
    z-index: 4;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 240px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: #ffffff;
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 78px;
    line-height: 1.30;
    color: #ffffff;
    opacity: 0.78;
    margin-top: 50px;
    max-width: 28ch;
    margin-left: auto;
    margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 5;
  }}
</style></head>
<body>
  <div class="glow-a"></div>
  <div class="glow-b"></div>
  {symbol_img}
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_versus(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 09 "Versus".

    Fundo Paper. Comparativo erro vs acerto em duas linhas: pilula
    vermelha "ERRADO" + texto riscado, depois pilula Cyan "CERTO" +
    texto Navy. Headline (titulo) acima como provocacao. Body opcional
    como contexto curto na base. Capa sem foto por design.

    Convencao: o body deve vir no formato "errado | certo" — o pipe
    separa as duas linhas. Sem pipe, o titulo eh repetido como provocacao
    e a linha de baixo fica vazia."""
    del foto_capa_url
    parts = (body or "").split("|", 1)
    errado = parts[0].strip() if parts else ""
    certo = parts[1].strip() if len(parts) > 1 else ""
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 28%;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 200px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .rows {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 320px;
    display: flex; flex-direction: column; gap: 60px;
  }}
  .row {{
    display: flex; align-items: center; gap: 50px;
  }}
  .pill {{
    flex-shrink: 0;
    padding: 24px 50px;
    border-radius: 999px;
    font-family: {font_body};
    font-weight: 800;
    font-size: 60px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #ffffff;
  }}
  .pill-wrong {{ background: #C13F3F; }}
  .pill-right {{ background: {_SC_CYAN}; color: {_SC_NAVY}; }}
  .row-text {{
    font-family: {font_display};
    font-weight: 600;
    font-size: 88px;
    line-height: 1.15;
    color: {_SC_NAVY};
  }}
  .row-text.wrong {{
    text-decoration: line-through;
    text-decoration-thickness: 6px;
    text-decoration-color: rgba(195,63,63,0.7);
    opacity: 0.6;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="rows">
    <div class="row">
      <span class="pill pill-wrong">Errado</span>
      <span class="row-text wrong">{_h(errado or "&nbsp;")}</span>
    </div>
    <div class="row">
      <span class="pill pill-right">Certo</span>
      <span class="row-text">{_h(certo or "&nbsp;")}</span>
    </div>
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_sticky_note(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 20 "Sticky note".

    Fundo Paper. Card grande Beige levemente rotacionado (-2.5deg)
    tipo post-it ocupando o centro, com headline Navy bold + body
    Navy abaixo. Pequena dobra/sombra sugerindo papel. Capa sem foto
    por design."""
    del foto_capa_url
    body_html = (
        f'<p class="note-body">{_h(body)}</p>' if body else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .note-wrap {{
    position: absolute;
    inset: 0;
    display: flex; align-items: center; justify-content: center;
    z-index: 2;
  }}
  .note {{
    width: 78%;
    background: {_SC_BEIGE};
    padding: 160px 140px;
    transform: rotate(-2.5deg);
    box-shadow:
      0 60px 120px rgba(24,32,40,0.18),
      0 12px 30px rgba(24,32,40,0.12);
    position: relative;
  }}
  .note::before {{
    /* Dobra superior esquerda do post-it */
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 140px; height: 140px;
    background: linear-gradient(135deg,
      rgba(255,255,255,0.45) 0%,
      rgba(255,255,255,0) 60%);
    pointer-events: none;
  }}
  .note-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    line-height: 0.94;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .note-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 78px;
    line-height: 1.28;
    color: {_SC_NAVY};
    opacity: 0.82;
    margin-top: 55px;
    max-width: 26ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="note-wrap">
    <div class="note">
      <h1 class="note-titulo">{_h(titulo)}</h1>
      {body_html}
    </div>
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_photo_banner(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 31 "Photo banner".

    Banda foto top 60% + Paper bottom 40% com headline Navy ancorada
    no canto inferior esquerdo do bloco de texto e body abaixo dela.
    Sem foto: banda top fica Beige solida."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_band = (
            f'<div class="photo-band" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        photo_band = '<div class="photo-band photo-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .photo-band {{
    position: absolute; left: 0; right: 0; top: 0;
    height: 60%;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .photo-fallback {{
    background: {_SC_BEIGE};
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .paper-band {{
    position: absolute; left: 0; right: 0;
    top: 60%; bottom: 0;
    background: {_SC_PAPER};
    padding: 160px 180px 220px;
    z-index: 1;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    line-height: 0.95;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 76px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.80;
    margin-top: 55px;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {photo_band}
  {logo_top_img}
  <div class="paper-band">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_floating_card(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 42 "Floating card".

    Fundo Navy + glow Beige radial atras. Foto centralizada num card
    com sombra profunda ocupando ~70% da largura. Headline Branca
    abaixo do card. Sem foto: card vira Beige solido, mantendo a
    estrutura visual."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        card_inner = (
            f'<div class="card-photo" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        card_inner = '<div class="card-photo card-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_NAVY};
    color: #ffffff;
    overflow: hidden;
    position: relative;
  }}
  .glow {{
    position: absolute;
    top: 18%; left: 50%;
    transform: translateX(-50%);
    width: 2400px; height: 2400px;
    border-radius: 50%;
    background: radial-gradient(circle, {_SC_BEIGE} 0%, rgba(224,176,152,0) 60%);
    opacity: 0.40;
    filter: blur(70px);
    z-index: 1;
    pointer-events: none;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .card {{
    position: absolute;
    top: 16%; left: 50%;
    transform: translateX(-50%);
    width: 70%;
    aspect-ratio: 4 / 5;
    background: #ffffff;
    padding: 40px;
    box-shadow:
      0 80px 160px rgba(0,0,0,0.50),
      0 24px 60px rgba(0,0,0,0.35);
    z-index: 3;
  }}
  .card-photo {{
    width: 100%; height: 100%;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }}
  .card-fallback {{
    background: {_SC_BEIGE};
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 320px;
    text-align: center;
    z-index: 4;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 180px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: #ffffff;
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 68px;
    line-height: 1.30;
    color: #ffffff;
    opacity: 0.78;
    margin-top: 40px;
    max-width: 28ch;
    margin-left: auto; margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 5;
  }}
</style></head>
<body>
  <div class="glow"></div>
  <div class="card">{card_inner}</div>
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_mythbuster(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 08 "Mythbuster".

    Fundo Paper. Bloco MITO (label Beige) com a crenca incorreta em
    italic Navy + bloco VERDADE (label Cyan) com a correcao em Navy
    bold. Titulo opcional como pergunta acima ('verdade ou mito?').
    Body usa formato 'mito | verdade' (pipe separador). Capa sem
    foto por design."""
    del foto_capa_url
    parts = (body or "").split("|", 1)
    mito = parts[0].strip() if parts else ""
    verdade = parts[1].strip() if len(parts) > 1 else ""
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 24%;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 170px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .blocks {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 320px;
    display: flex; flex-direction: column; gap: 80px;
  }}
  .block {{
    border-left: 14px solid;
    padding-left: 60px;
  }}
  .block-mito {{ border-color: {_SC_BEIGE}; }}
  .block-verdade {{ border-color: {_SC_CYAN}; }}
  .label {{
    display: inline-block;
    padding: 18px 40px;
    border-radius: 8px;
    font-family: {font_body};
    font-weight: 800;
    font-size: 52px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 38px;
  }}
  .label-mito {{ background: {_SC_BEIGE}; color: {_SC_NAVY}; }}
  .label-verdade {{ background: {_SC_CYAN}; color: {_SC_NAVY}; }}
  .block-text {{
    font-family: {font_display};
    font-size: 96px;
    line-height: 1.10;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .block-text.mito {{
    font-style: italic;
    opacity: 0.65;
  }}
  .block-text.verdade {{
    font-weight: 700;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="blocks">
    <div class="block block-mito">
      <span class="label label-mito">Mito</span>
      <div class="block-text mito">{_h(mito or "&nbsp;")}</div>
    </div>
    <div class="block block-verdade">
      <span class="label label-verdade">Verdade</span>
      <div class="block-text verdade">{_h(verdade or "&nbsp;")}</div>
    </div>
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_brackets(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 17 "Brackets".

    Fundo Paper. Colchetes Beige gigantes ancorados nas laterais
    (left + right), envolvendo a headline Navy bold centralizada.
    Body opcional Navy mono pequeno abaixo da headline. Capa sem
    foto por design."""
    del foto_capa_url
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .bracket {{
    position: absolute;
    top: 28%; bottom: 28%;
    width: 200px;
    font-family: {font_display};
    font-weight: 200;
    font-size: 1400px;
    line-height: 0.6;
    color: {_SC_BEIGE};
    z-index: 1;
    pointer-events: none;
    display: flex; align-items: center;
  }}
  .bracket-l {{
    left: 80px;
  }}
  .bracket-r {{
    right: 80px;
    justify-content: flex-end;
  }}
  .content {{
    position: absolute;
    left: 320px; right: 320px;
    top: 30%; bottom: 30%;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    text-align: center;
    z-index: 3;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 70px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 50px;
    max-width: 26ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="bracket bracket-l">[</div>
  <div class="bracket bracket-r">]</div>
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_photo_blur(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 37 "Photo blur".

    Foto full-bleed desfocada como background + camada Navy translucida
    + headline Branca crisp centralizada. Efeito glassmorphism. Sem
    foto cai num fundo Navy solido com a headline mantida no centro."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_layer = (
            f'<div class="photo-blur" style="background-image: url(\'{foto_capa_url}\')"></div>'
            '<div class="overlay"></div>'
        )
    else:
        photo_layer = '<div class="solid-navy"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_NAVY};
    color: #ffffff;
    overflow: hidden;
    position: relative;
  }}
  .photo-blur {{
    position: absolute;
    top: -100px; left: -100px; right: -100px; bottom: -100px;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    filter: blur(80px) saturate(1.05);
    transform: scale(1.15);
    z-index: 0;
  }}
  .overlay {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(24,32,40,0.55);
    z-index: 1;
  }}
  .solid-navy {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: {_SC_NAVY};
    z-index: 0;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    text-align: center;
    z-index: 3;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 260px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: #ffffff;
    text-wrap: balance;
    text-shadow: 0 8px 40px rgba(0,0,0,0.35);
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 78px;
    line-height: 1.30;
    color: #ffffff;
    opacity: 0.90;
    margin-top: 60px;
    max-width: 28ch;
    margin-left: auto; margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {photo_layer}
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_cinema(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 39 "Cinema".

    Fundo Navy + faixa horizontal central (40% altura, perfeitamente
    centralizada vertical: 30%-70%) com a foto em formato cinemascope.
    A imagem fica sempre centralizada dentro da faixa (background-
    position: center center, background-size: cover). Headline branca
    acima da faixa, body Cyan abaixo. Sem foto: faixa central vira
    Beige solida."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        cinema_band = (
            f'<div class="cinema-band" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        cinema_band = '<div class="cinema-band cinema-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_NAVY};
    color: #ffffff;
    overflow: hidden;
    position: relative;
  }}
  .cinema-band {{
    position: absolute;
    left: 0; right: 0;
    top: 30%; height: 40%;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    z-index: 1;
  }}
  .cinema-fallback {{
    background: {_SC_BEIGE};
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 30%;
    transform: translateY(-100%);
    padding-bottom: 80px;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 200px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: #ffffff;
    text-wrap: balance;
  }}
  .footer {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 220px;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 500;
    font-size: 70px;
    line-height: 1.30;
    color: {_SC_CYAN};
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {cinema_band}
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="footer">
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_type_tower(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 12 "Type tower".

    Fundo Paper. Palavras da headline empilhadas verticalmente com
    tamanhos crescentes (do menor pro maior) e tratamentos
    alternados (regular Navy, italic Navy, bold Cyan, mega Navy).
    Body opcional Navy pequeno na base. Capa sem foto por design.

    A primeira palavra fica pequena, e cada palavra subsequente
    cresce em tamanho — o efeito final eh uma 'torre' tipografica
    crescente. Funciona melhor com 3-5 palavras."""
    del foto_capa_url
    words = (titulo or "").split()
    if not words:
        words = [""]
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    # 4 tracks de estilo que se repetem
    sizes = [110, 160, 220, 280]
    treatments = [
        "navy-regular",
        "navy-italic",
        "cyan-bold",
        "navy-mega",
    ]
    lines = []
    for i, w in enumerate(words):
        size = sizes[min(i, len(sizes) - 1)]
        treat = treatments[i % len(treatments)]
        lines.append(
            f'<div class="line {treat}" style="font-size: {size}px;">{_h(w)}</div>'
        )
    tower = "\n".join(lines)
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .tower {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    display: flex; flex-direction: column;
    gap: 18px;
    z-index: 2;
  }}
  .line {{
    font-family: {font_display};
    line-height: 0.95;
    letter-spacing: -0.025em;
    text-wrap: balance;
  }}
  .navy-regular {{ color: {_SC_NAVY}; font-weight: 500; }}
  .navy-italic  {{ color: {_SC_NAVY}; font-weight: 500; font-style: italic; opacity: 0.65; }}
  .cyan-bold    {{ color: {_SC_CYAN}; font-weight: 800; }}
  .navy-mega    {{ color: {_SC_NAVY}; font-weight: 800; }}
  .footer {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 220px;
    z-index: 3;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 68px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="tower">{tower}</div>
  <div class="footer">{body_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_split_color(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 24 "Split color".

    Diagonal split: triangulo Beige cobrindo a metade superior
    esquerda + triangulo Navy cobrindo a metade inferior direita.
    Headline grande cruzando o split — palavra 1 sobre Beige
    (cor Navy), palavra 2 sobre Navy (cor Beige). Capa sem foto
    por design."""
    del foto_capa_url
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_BEIGE};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .navy-tri {{
    /* Triangulo Navy cobrindo a metade inferior direita */
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: {_SC_NAVY};
    clip-path: polygon(100% 0, 100% 100%, 0 100%);
    z-index: 1;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 3;
    text-align: center;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 260px;
    line-height: 0.94;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
    /* Texto fica sobre os dois fundos — usa mix-blend pra inverter
       cor onde cruza o triangulo Navy */
    mix-blend-mode: difference;
    color: #ffffff;
  }}
  .footer {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 220px;
    text-align: right;
    z-index: 4;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 500;
    font-size: 72px;
    line-height: 1.28;
    color: {_SC_BEIGE};
    max-width: 26ch;
    margin-left: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; right: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_BEIGE};
    letter-spacing: 0.04em;
    z-index: 5;
  }}
</style></head>
<body>
  <div class="navy-tri"></div>
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
  </div>
  <div class="footer">{body_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_polaroid(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 32 "Polaroid".

    Fundo Paper. Foto montada num quadro tipo polaroid (moldura
    branca grossa, mais grossa embaixo, sombra profunda, rotacao
    sutil -2deg) centralizada. Caption manuscrita-style abaixo da
    foto. Headline Navy bold abaixo da polaroid. Sem foto: quadro
    fica com fundo Beige."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_inner = (
            f'<div class="polaroid-photo" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        photo_inner = '<div class="polaroid-photo polaroid-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .polaroid-wrap {{
    position: absolute;
    top: 14%; left: 50%;
    transform: translateX(-50%) rotate(-2deg);
    width: 60%;
    z-index: 2;
  }}
  .polaroid {{
    background: #ffffff;
    padding: 60px 60px 220px;
    box-shadow:
      0 80px 160px rgba(24,32,40,0.30),
      0 24px 50px rgba(24,32,40,0.20);
  }}
  .polaroid-photo {{
    width: 100%;
    aspect-ratio: 1 / 1;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }}
  .polaroid-fallback {{
    background: {_SC_BEIGE};
  }}
  .polaroid-caption {{
    font-family: {font_display};
    font-style: italic;
    font-weight: 500;
    font-size: 78px;
    color: {_SC_NAVY};
    text-align: center;
    margin-top: 50px;
    opacity: 0.85;
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 280px;
    text-align: center;
    z-index: 4;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 170px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 64px;
    line-height: 1.28;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 40px;
    max-width: 30ch;
    margin-left: auto; margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 5;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="polaroid-wrap">
    <div class="polaroid">
      {photo_inner}
    </div>
  </div>
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_portrait_frame(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 40 "Portrait frame".

    Fundo Paper. Foto montada num quadro tipo retrato em moldura
    grossa Beige (60px borda) com inner border Navy fino (8px),
    sombras duplas pra simular profundidade. Tag mono no topo
    indicando 'EDIÇÃO · MMM YYYY'. Headline + body abaixo do
    quadro. Sem foto: interno do quadro vira Navy solido."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_inner = (
            f'<div class="frame-photo" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        photo_inner = '<div class="frame-photo frame-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .tag {{
    position: absolute;
    top: 380px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 56px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: {_SC_NAVY};
    opacity: 0.7;
    z-index: 4;
  }}
  .frame-wrap {{
    position: absolute;
    top: 18%; left: 50%;
    transform: translateX(-50%);
    width: 62%;
    aspect-ratio: 4 / 5;
    background: {_SC_BEIGE};
    padding: 60px;
    box-shadow:
      0 80px 140px rgba(24,32,40,0.28),
      0 18px 40px rgba(24,32,40,0.18);
    z-index: 2;
  }}
  .frame-inner {{
    width: 100%; height: 100%;
    border: 8px solid {_SC_NAVY};
  }}
  .frame-photo {{
    width: 100%; height: 100%;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }}
  .frame-fallback {{
    background: {_SC_NAVY};
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 280px;
    text-align: center;
    z-index: 4;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 170px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 64px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 40px;
    max-width: 30ch;
    margin-left: auto; margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 5;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="tag">PERFIL · {_brand_label().upper()}</div>
  <div class="frame-wrap">
    <div class="frame-inner">
      {photo_inner}
    </div>
  </div>
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_grid_stats(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 15 "Grid stats".

    Fundo Paper. Grid 2x2 com 4 numeros/percentuais gigantes Navy
    + label curta abaixo. Titulo grande Navy ancorado acima do
    grid. Body usa convencao 'n1: l1; n2: l2; n3: l3; n4: l4' —
    cada par numero:label separado por ';', numero e label
    separados por ':'. Capa sem foto por design."""
    del foto_capa_url
    raw = (body or "").strip()
    pairs = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            n, l = chunk.split(":", 1)
            pairs.append((n.strip(), l.strip()))
        else:
            pairs.append((chunk, ""))
    while len(pairs) < 4:
        pairs.append(("—", ""))
    pairs = pairs[:4]
    # 4 quadrantes — cores alternam pra dar ritmo
    colors = [_SC_NAVY, _SC_CYAN, _SC_NAVY, _SC_BEIGE]
    cells = []
    for i, (num, lab) in enumerate(pairs):
        c = colors[i]
        cells.append(
            '<div class="cell">'
            f'<div class="cell-num" style="color: {c};">{_h(num)}</div>'
            f'<div class="cell-lab">{_h(lab)}</div>'
            "</div>"
        )
    grid_html = "\n".join(cells)
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 22%;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 160px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .grid {{
    position: absolute;
    left: 180px; right: 180px;
    top: 44%;
    bottom: 240px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 80px;
  }}
  .cell {{
    display: flex; flex-direction: column;
    justify-content: center;
    border-top: 6px solid {_SC_NAVY};
    padding-top: 30px;
  }}
  .cell-num {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 280px;
    line-height: 0.92;
    letter-spacing: -0.04em;
  }}
  .cell-lab {{
    font-family: {font_body};
    font-weight: 600;
    font-size: 56px;
    line-height: 1.20;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 24px;
    max-width: 20ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="grid">{grid_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_highlight(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 18 "Highlight".

    Fundo Paper. Headline gigante com UMA palavra em destaque
    sublinhado Cyan pintada como marca-texto. Convencao: a palavra
    a destacar vem entre **asteriscos** dentro do titulo (markdown-
    like). Body opcional Navy mono na base. Capa sem foto por design.

    Ex: 'O sindico que **mede** sempre melhora' renderiza 'mede' com
    fundo Cyan."""
    del foto_capa_url
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    # Substitui **palavra** por <span class="hl">palavra</span>
    titulo_html = _h(titulo or "")
    import re as _re
    titulo_html = _re.sub(
        r"\*\*([^*]+)\*\*",
        r'<span class="hl">\1</span>',
        titulo_html,
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 280px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-titulo .hl {{
    /* Marca-texto Cyan: gradient horizontal cobrindo ~60% da altura
       da palavra, posicao alta pra parecer destacador real */
    background: linear-gradient(180deg,
      transparent 0%,
      transparent 35%,
      {_SC_CYAN} 35%,
      {_SC_CYAN} 92%,
      transparent 92%);
    padding: 0 8px;
    box-decoration-break: clone;
    -webkit-box-decoration-break: clone;
  }}
  .footer {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 220px;
    z-index: 3;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 68px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{titulo_html}</h1>
  </div>
  <div class="footer">{body_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_stamp(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 30 "Stamp".

    Fundo Paper. Headline Navy grande ancorada acima do meio. Selo
    estilo carimbo vermelho diagonal (-18deg) sobre a headline,
    com borda dupla e texto 'FATO' / 'VERDADE' centralizado.
    Convencao: a palavra do selo vem no body (default 'FATO').
    Capa sem foto por design."""
    del foto_capa_url
    stamp_word = (body or "Fato").strip().upper()
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 38%;
    transform: translateY(-50%);
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .stamp-wrap {{
    position: absolute;
    bottom: 320px;
    right: 240px;
    transform: rotate(-18deg);
    z-index: 4;
    pointer-events: none;
  }}
  .stamp {{
    border: 14px solid #C13F3F;
    padding: 50px 90px;
    color: #C13F3F;
    font-family: {font_display};
    font-weight: 800;
    font-size: 220px;
    letter-spacing: 0.06em;
    line-height: 1;
    text-transform: uppercase;
    background: rgba(255,255,255,0.05);
    opacity: 0.92;
    /* Cantos quadrados + sombra interna sutil pra parecer carimbo */
    box-shadow: inset 0 0 0 6px #C13F3F;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
  </div>
  <div class="stamp-wrap">
    <div class="stamp">{_h(stamp_word)}</div>
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_photo_strip(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 35 "Photo strip".

    Fundo Paper. Foto em strip horizontal estreito centralizado
    (~22% da altura) ocupando full-bleed. Headline Navy bold
    ancorada acima da strip, body Navy abaixo. Sem foto: strip
    vira Beige solida."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        strip = (
            f'<div class="strip" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        strip = '<div class="strip strip-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .strip {{
    position: absolute;
    left: 0; right: 0;
    top: 39%; height: 22%;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 1;
  }}
  .strip-fallback {{
    background: {_SC_BEIGE};
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 39%;
    transform: translateY(-100%);
    padding-bottom: 70px;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 200px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .footer {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 220px;
    z-index: 3;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 72px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.80;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {strip}
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="footer">{body_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_bullet_list(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 19 "Bullet list".

    Fundo Paper. Headline Navy grande no topo + lista de 3 a 5 bullets
    com pilulas numeradas Cyan + texto Navy. Body usa convencao
    'item1; item2; item3' (separados por ';'). Capa sem foto por
    design."""
    del foto_capa_url
    raw = (body or "").strip()
    items = [x.strip() for x in raw.split(";") if x.strip()]
    if not items:
        items = ["—"]
    items = items[:5]
    rows = []
    for i, txt in enumerate(items, start=1):
        rows.append(
            '<div class="row">'
            f'<span class="pill">{i:02d}</span>'
            f'<span class="row-text">{_h(txt)}</span>'
            "</div>"
        )
    rows_html = "\n".join(rows)
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 24%;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 180px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .rows {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 320px;
    display: flex; flex-direction: column; gap: 50px;
  }}
  .row {{
    display: flex; align-items: center; gap: 50px;
  }}
  .pill {{
    flex-shrink: 0;
    width: 130px; height: 130px;
    border-radius: 50%;
    background: {_SC_CYAN};
    color: {_SC_NAVY};
    display: flex; align-items: center; justify-content: center;
    font-family: {font_display};
    font-weight: 800;
    font-size: 70px;
    letter-spacing: -0.02em;
  }}
  .row-text {{
    font-family: {font_display};
    font-weight: 600;
    font-size: 82px;
    line-height: 1.18;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="rows">{rows_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_wallpaper(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 26 "Wallpaper".

    Fundo Paper. Pattern Sindicompany (S_SVG) repetido em tile
    cobrindo toda a tela em opacidade reduzida. Card Beige
    centralizado vertical (~50% altura) com label Cyan no topo +
    headline Navy grande + body Navy pequeno. Capa sem foto por
    design."""
    del foto_capa_url
    body_html = (
        f'<p class="card-body">{_h(body)}</p>' if body else ""
    )
    pattern_url = (
        _logo_slot_data_url(2)
        or _logo_slot_data_url(3)
        or _logo_slot_data_url(1)
        or ""
    )
    pattern_layer = (
        f'<div class="pattern" style="background-image: url(\'{pattern_url}\');"></div>'
        if pattern_url
        else ''
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .pattern {{
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-repeat: repeat;
    background-size: 320px 320px;
    opacity: 0.16;
    z-index: 0;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .card {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    background: {_SC_BEIGE};
    padding: 140px 130px;
    z-index: 3;
    box-shadow: 0 60px 120px rgba(24,32,40,0.18);
  }}
  .card-label {{
    display: inline-block;
    padding: 18px 36px;
    background: {_SC_CYAN};
    color: {_SC_NAVY};
    font-family: {font_body};
    font-weight: 800;
    font-size: 48px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 60px;
  }}
  .card-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 200px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .card-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 72px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.80;
    margin-top: 50px;
    max-width: 26ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {pattern_layer}
  {logo_top_img}
  <div class="card">
    <span class="card-label">{_brand_label()}</span>
    <h1 class="card-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_underline(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 34 "Underline".

    Fundo Paper. Headline Navy gigante com UMA palavra entre
    **asteriscos** ganhando um underline grosso Cyan (12px) logo
    abaixo. Diferente do highlight (que pinta marca-texto sobre a
    palavra) este so destaca pelo sublinhado, com tipografia
    inalterada. Capa sem foto por design.

    Ex: 'Quem **mede** sempre melhora.' """
    del foto_capa_url
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    titulo_html = _h(titulo or "")
    import re as _re
    titulo_html = _re.sub(
        r"\*\*([^*]+)\*\*",
        r'<span class="u">\1</span>',
        titulo_html,
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 2;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 260px;
    line-height: 1.04;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-titulo .u {{
    /* Underline grosso Cyan, posicionado pra simular pinceladas
       sob a palavra. Usa box-shadow inset pra dar peso visual. */
    text-decoration: underline;
    text-decoration-color: {_SC_CYAN};
    text-decoration-thickness: 24px;
    text-underline-offset: 12px;
  }}
  .footer {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 220px;
    z-index: 3;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 68px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{titulo_html}</h1>
  </div>
  <div class="footer">{body_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_photo_grid(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 36 "Photo grid".

    Grid horizontal 50/50: foto na metade superior + Paper bloco
    na metade inferior. Headline Navy bold + body Navy ancorados
    no canto inferior esquerdo do bloco. Sem foto: metade superior
    vira Beige solido."""
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    if foto_capa_url:
        photo_half = (
            f'<div class="photo-half" style="background-image: url(\'{foto_capa_url}\')"></div>'
        )
    else:
        photo_half = '<div class="photo-half photo-fallback"></div>'
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .photo-half {{
    position: absolute;
    left: 0; right: 0; top: 0;
    height: 50%;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }}
  .photo-fallback {{
    background: {_SC_BEIGE};
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .text-half {{
    position: absolute;
    left: 0; right: 0;
    top: 50%; bottom: 0;
    background: {_SC_PAPER};
    padding: 160px 180px 220px;
    z-index: 1;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 210px;
    line-height: 0.95;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 74px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 50px;
    max-width: 28ch;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {photo_half}
  {logo_top_img}
  <div class="text-half">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_timeline(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 16 "Timeline".

    Fundo Paper. Linha vertical Navy a esquerda, com 3 a 5 pontos
    Cyan circulares numerados — cada um seguido de texto Navy ao
    lado. Headline grande no topo. Body usa convencao
    'etapa1; etapa2; etapa3' (separados por ';'). Capa sem foto."""
    del foto_capa_url
    raw = (body or "").strip()
    items = [x.strip() for x in raw.split(";") if x.strip()]
    if not items:
        items = ["—"]
    items = items[:5]
    rows = []
    for i, txt in enumerate(items, start=1):
        rows.append(
            '<div class="step">'
            f'<div class="dot"><span>{i:02d}</span></div>'
            f'<div class="step-text">{_h(txt)}</div>'
            "</div>"
        )
    steps_html = "\n".join(rows)
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 22%;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 170px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .steps {{
    position: absolute;
    left: 220px; right: 180px;
    bottom: 320px;
    display: flex; flex-direction: column; gap: 60px;
    /* Linha vertical Navy atrás dos pontos */
  }}
  .steps::before {{
    content: "";
    position: absolute;
    top: 70px; bottom: 70px;
    left: 65px;
    width: 6px;
    background: {_SC_NAVY};
    opacity: 0.20;
    z-index: 0;
  }}
  .step {{
    display: flex; align-items: center; gap: 60px;
    position: relative; z-index: 1;
  }}
  .dot {{
    flex-shrink: 0;
    width: 130px; height: 130px;
    border-radius: 50%;
    background: {_SC_CYAN};
    color: {_SC_NAVY};
    display: flex; align-items: center; justify-content: center;
    font-family: {font_display};
    font-weight: 800;
    font-size: 60px;
    letter-spacing: -0.02em;
    box-shadow: 0 0 0 14px {_SC_PAPER};
  }}
  .step-text {{
    font-family: {font_display};
    font-weight: 600;
    font-size: 78px;
    line-height: 1.18;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="steps">{steps_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_conversation(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 21 "Conversation".

    Fundo Paper. Bolhas de chat estilo DM/WhatsApp empilhadas
    verticalmente, alternando incoming (esquerda Beige) e outgoing
    (direita Cyan). Headline opcional grande no topo. Body usa
    convencao 'msg1 | msg2 | msg3 | msg4' (pipe separador, alterna
    in/out). Capa sem foto por design."""
    del foto_capa_url
    raw = (body or "").strip()
    msgs = [x.strip() for x in raw.split("|") if x.strip()]
    if not msgs:
        msgs = ["—"]
    msgs = msgs[:6]
    bubbles = []
    for i, txt in enumerate(msgs):
        side = "in" if i % 2 == 0 else "out"
        bubbles.append(
            f'<div class="bubble bubble-{side}">{_h(txt)}</div>'
        )
    chat_html = "\n".join(bubbles)
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 22%;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 150px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .chat {{
    position: absolute;
    left: 220px; right: 220px;
    bottom: 320px;
    display: flex; flex-direction: column; gap: 36px;
  }}
  .bubble {{
    max-width: 78%;
    padding: 50px 70px;
    font-family: {font_body};
    font-weight: 500;
    font-size: 72px;
    line-height: 1.20;
    border-radius: 50px;
    /* Cantos diferentes pra cada lado simulam tail real do chat */
  }}
  .bubble-in {{
    background: {_SC_BEIGE};
    color: {_SC_NAVY};
    align-self: flex-start;
    border-bottom-left-radius: 12px;
  }}
  .bubble-out {{
    background: {_SC_CYAN};
    color: {_SC_NAVY};
    align-self: flex-end;
    border-bottom-right-radius: 12px;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 3;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="chat">{chat_html}</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_receipt(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 29 "Receipt".

    Fundo Paper. Bloco estreito centralizado tipo nota fiscal /
    recibo (papel-bege com linhas) listando itens + valores. Titulo
    no topo do recibo, linhas duplas, total na base. Body usa
    convencao 'item1: valor1; item2: valor2; ...' (semicolons
    separam linhas, dois-pontos separa descricao do valor). Capa
    sem foto por design."""
    del foto_capa_url
    raw = (body or "").strip()
    lines = []
    total = ""
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            n, v = chunk.split(":", 1)
            lines.append((n.strip(), v.strip()))
        else:
            lines.append((chunk, ""))
    if lines and lines[-1][0].lower().startswith("total"):
        total = lines[-1][1]
        lines = lines[:-1]
    if not lines:
        lines = [("—", "—")]
    lines = lines[:6]
    items_html = "\n".join(
        f'<div class="rec-row"><span class="rec-name">{_h(n)}</span><span class="rec-dots"></span><span class="rec-val">{_h(v)}</span></div>'
        for n, v in lines
    )
    total_block = (
        f'<div class="rec-total"><span>Total</span><span class="rec-total-val">{_h(total)}</span></div>'
        if total
        else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_NAVY};
    color: #ffffff;
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) invert(1);
  }}
  .receipt {{
    position: absolute;
    left: 50%; top: 50%;
    transform: translate(-50%, -50%);
    width: 70%;
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    padding: 110px 90px 90px;
    box-shadow: 0 80px 160px rgba(0,0,0,0.45);
    /* Borda serrilhada inferior (ziguezague tipo papel rasgado) */
    -webkit-mask-image:
      linear-gradient(#000,#000),
      conic-gradient(from -45deg at bottom, #0000 90deg, #000 0) 50% 100%/40px 20px repeat-x;
  }}
  .rec-title {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 110px;
    line-height: 0.96;
    color: {_SC_NAVY};
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .rec-sub {{
    font-family: {font_body};
    font-weight: 600;
    font-size: 36px;
    color: {_SC_NAVY};
    opacity: 0.65;
    text-align: center;
    margin-top: 14px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
  }}
  .rec-divider {{
    border-top: 4px dashed {_SC_NAVY};
    opacity: 0.4;
    margin: 60px 0;
  }}
  .rec-row {{
    display: flex; align-items: flex-end; gap: 12px;
    font-family: {font_body};
    font-size: 56px;
    font-weight: 500;
    color: {_SC_NAVY};
    margin-bottom: 30px;
  }}
  .rec-name {{ flex: 0 0 auto; }}
  .rec-dots {{
    flex: 1 1 auto;
    border-bottom: 4px dotted {_SC_NAVY};
    opacity: 0.35;
    transform: translateY(-8px);
  }}
  .rec-val {{ flex: 0 0 auto; font-weight: 700; }}
  .rec-total {{
    display: flex; align-items: center; justify-content: space-between;
    font-family: {font_display};
    font-weight: 800;
    font-size: 84px;
    color: {_SC_NAVY};
    margin-top: 30px;
    padding-top: 30px;
    border-top: 6px solid {_SC_NAVY};
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .rec-total-val {{ color: {_SC_NAVY}; }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="receipt">
    <div class="rec-title">{_h(titulo)}</div>
    <div class="rec-sub">{_brand_label()} · Recibo</div>
    <div class="rec-divider"></div>
    {items_html}
    {total_block}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_corner_tape(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 41 "Corner tape".

    Fundo Paper com fitas adesivas Cyan diagonais nos 4 cantos
    'prendendo' o papel. Headline Navy gigante centralizada + body
    Navy mono abaixo. Estetica zine / mood board. Capa sem foto
    por design."""
    del foto_capa_url
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .tape {{
    position: absolute;
    width: 400px; height: 110px;
    background: {_SC_CYAN};
    opacity: 0.88;
    box-shadow: 0 12px 30px rgba(24,32,40,0.18);
    z-index: 2;
  }}
  .tape::before, .tape::after {{
    /* Bordas serrilhadas das fitas (cantos rasgados) */
    content: "";
    position: absolute;
    top: 0; bottom: 0;
    width: 24px;
    background:
      linear-gradient(45deg, transparent 50%, {_SC_PAPER} 50%) top left/24px 24px no-repeat,
      linear-gradient(-45deg, transparent 50%, {_SC_PAPER} 50%) bottom left/24px 24px no-repeat,
      linear-gradient(135deg, transparent 50%, {_SC_PAPER} 50%) top right/24px 24px no-repeat,
      linear-gradient(-135deg, transparent 50%, {_SC_PAPER} 50%) bottom right/24px 24px no-repeat;
    background-color: transparent;
  }}
  .tape::before {{ left: -2px; }}
  .tape::after  {{ right: -2px; transform: scaleX(-1); }}
  .tape-tl {{ top: 80px;  left: -50px;  transform: rotate(-25deg); }}
  .tape-tr {{ top: 80px;  right: -50px; transform: rotate(25deg);  }}
  .tape-bl {{ bottom: 80px; left: -50px;  transform: rotate(25deg);  }}
  .tape-br {{ bottom: 80px; right: -50px; transform: rotate(-25deg); }}
  .logo-top {{
    position: absolute;
    top: 220px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .content {{
    position: absolute;
    left: 240px; right: 240px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 3;
    text-align: center;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 260px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 500;
    font-size: 70px;
    line-height: 1.30;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 60px;
    max-width: 28ch;
    margin-left: auto; margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 180px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  <div class="tape tape-tl"></div>
  <div class="tape tape-tr"></div>
  <div class="tape tape-bl"></div>
  <div class="tape tape-br"></div>
  {logo_top_img}
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_ribbon(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 13 "Ribbon".

    Fundo Paper. Fita Cyan diagonal larga (-25deg) atravessando o
    slide do canto inferior esquerdo ao canto superior direito,
    com texto Navy bold curto (body) escrito na fita em uppercase.
    Headline Navy gigante centralizada acima/abaixo conforme cabe.
    Capa sem foto por design."""
    del foto_capa_url
    ribbon_text = (body or titulo or _brand_label()).strip().upper()
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .ribbon-wrap {{
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(-25deg);
    width: 200%;
    z-index: 2;
    pointer-events: none;
  }}
  .ribbon {{
    background: {_SC_CYAN};
    padding: 80px 0;
    text-align: center;
    color: {_SC_NAVY};
    font-family: {font_display};
    font-weight: 800;
    font-size: 140px;
    letter-spacing: 0.06em;
    line-height: 1;
    box-shadow:
      0 30px 80px rgba(24,32,40,0.20),
      0 8px 16px rgba(24,32,40,0.10);
  }}
  .head {{
    position: absolute;
    left: 180px; right: 180px;
    top: 16%;
    z-index: 3;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 170px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="head"><h1 class="capa-titulo">{_h(titulo)}</h1></div>
  <div class="ribbon-wrap">
    <div class="ribbon">{_h(ribbon_text)}</div>
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_polaroid_stack(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 22 "Polaroid stack".

    Fundo Paper. 3 polaroides Beige empilhadas no centro com rotacoes
    leves diferentes (-8deg/3deg/-2deg) e sombras profundas, simulando
    fotos espalhadas sobre mesa. Caption da polaroide central virou
    o titulo. Headline Navy abaixo do stack. Capa sem foto por
    design (as polaroides ficam Beige solidas)."""
    del foto_capa_url
    body_html = (
        f'<p class="capa-body">{_h(body)}</p>' if body else ""
    )
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .stack {{
    position: absolute;
    top: 16%; left: 50%;
    transform: translateX(-50%);
    width: 50%;
    aspect-ratio: 4 / 5;
  }}
  .pol {{
    position: absolute;
    inset: 0;
    background: #ffffff;
    padding: 40px 40px 130px;
    box-shadow:
      0 50px 100px rgba(24,32,40,0.22),
      0 16px 36px rgba(24,32,40,0.14);
  }}
  .pol-inner {{
    width: 100%; height: 100%;
    background: {_SC_BEIGE};
  }}
  .pol-1 {{ transform: rotate(-8deg) translate(-60px, -10px); }}
  .pol-2 {{ transform: rotate(3deg)  translate(40px,  20px); }}
  .pol-3 {{ transform: rotate(-2deg); z-index: 2; }}
  .pol-3 .pol-inner {{
    background: {_SC_CYAN};
  }}
  .pol-caption {{
    position: absolute;
    bottom: 28px; left: 0; right: 0;
    text-align: center;
    font-family: {font_display};
    font-style: italic;
    font-weight: 500;
    font-size: 52px;
    color: {_SC_NAVY};
    opacity: 0.78;
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 280px;
    text-align: center;
    z-index: 4;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 170px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: 400;
    font-size: 64px;
    line-height: 1.28;
    color: {_SC_NAVY};
    opacity: 0.78;
    margin-top: 40px;
    max-width: 30ch;
    margin-left: auto; margin-right: auto;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 5;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="stack">
    <div class="pol pol-1"><div class="pol-inner"></div></div>
    <div class="pol pol-2"><div class="pol-inner"></div></div>
    <div class="pol pol-3">
      <div class="pol-inner"></div>
      <div class="pol-caption">{_brand_label()} · {_h(handle)}</div>
    </div>
  </div>
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
    {body_html}
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_maxi_quote(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 27 "Maxi quote".

    Fundo Paper. Citacao gigante em duas linhas com cores e
    tratamentos diferentes: linha 1 (titulo) em italic Navy bold,
    linha 2 (body) em italic Cyan extra-bold sublinhado. Ponto final
    Beige gigante na base como acento visual. Capa sem foto por
    design.

    Quando o usuario quer 'uma frase com efeito', body separa o
    pensamento principal do contraponto."""
    del foto_capa_url
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .quote {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 2;
  }}
  .line1 {{
    font-family: {font_display};
    font-style: italic;
    font-weight: 700;
    font-size: 240px;
    line-height: 1.0;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .line2 {{
    font-family: {font_display};
    font-style: italic;
    font-weight: 800;
    font-size: 240px;
    line-height: 1.0;
    letter-spacing: -0.025em;
    color: {_SC_CYAN};
    text-wrap: balance;
    margin-top: 30px;
    /* Sublinhado grosso pra dar peso visual */
    text-decoration: underline;
    text-decoration-color: {_SC_CYAN};
    text-decoration-thickness: 18px;
    text-underline-offset: 14px;
  }}
  .accent {{
    position: absolute;
    right: 180px;
    bottom: 260px;
    font-family: {font_display};
    font-weight: 800;
    font-size: 380px;
    line-height: 0.6;
    color: {_SC_BEIGE};
    z-index: 1;
    pointer-events: none;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 180px;
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_NAVY};
    letter-spacing: 0.04em;
    z-index: 4;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="quote">
    <div class="line1">{_h(titulo)}</div>
    <div class="line2">{_h(body or "")}</div>
  </div>
  <div class="accent">.</div>
  <div class="handle">{handle}</div>
</body></html>
"""


def _capa_calendar(
    *,
    titulo: str,
    body: str,
    handle: str,
    logo_top_img: str,
    head_fonts: str,
    font_display: str,
    font_body: str,
    foto_capa_url: str = "",
) -> str:
    """Brand Hub 2026-05-17 — capa 28 "Calendar".

    Fundo Paper. Bloco de calendario Navy centralizado no topo, tipo
    folha de calendario destacavel: header Beige com nome do mes,
    numero gigante no centro do bloco. Headline Navy ancorada abaixo
    do bloco + body. Body usa convencao 'mes | dia' (pipe separa).
    Default: mes=MAIO, dia=18. Capa sem foto por design."""
    del foto_capa_url
    raw = (body or "").strip()
    parts = raw.split("|", 1)
    mes_label = (parts[0].strip() if parts and parts[0].strip() else "MAIO").upper()
    dia_label = (parts[1].strip() if len(parts) > 1 and parts[1].strip() else "18")
    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {_SC_PAPER};
    color: {_SC_NAVY};
    overflow: hidden;
    position: relative;
  }}
  .logo-top {{
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: brightness(0) saturate(100%);
  }}
  .cal {{
    position: absolute;
    top: 18%; left: 50%;
    transform: translateX(-50%) rotate(-2deg);
    width: 56%;
    background: #ffffff;
    border: 12px solid {_SC_NAVY};
    box-shadow: 0 60px 120px rgba(24,32,40,0.28),
                0 20px 40px rgba(24,32,40,0.18);
    z-index: 2;
  }}
  .cal-header {{
    background: {_SC_BEIGE};
    padding: 40px 0;
    text-align: center;
    font-family: {font_body};
    font-weight: 800;
    font-size: 90px;
    color: {_SC_NAVY};
    letter-spacing: 0.10em;
    border-bottom: 12px solid {_SC_NAVY};
  }}
  .cal-day {{
    padding: 100px 0 120px;
    text-align: center;
    font-family: {font_display};
    font-weight: 800;
    font-size: 540px;
    line-height: 0.85;
    color: {_SC_NAVY};
    letter-spacing: -0.05em;
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    bottom: 280px;
    text-align: center;
    z-index: 4;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: 800;
    font-size: 170px;
    line-height: 0.96;
    letter-spacing: -0.025em;
    color: {_SC_NAVY};
    text-wrap: balance;
  }}
  .handle {{
    position: absolute;
    bottom: 100px; left: 50%;
    transform: translateX(-50%);
    font-family: {font_body};
    font-size: 64px;
    font-weight: 600;
    color: {_SC_CYAN};
    letter-spacing: 0.04em;
    z-index: 5;
  }}
</style></head>
<body>
  {logo_top_img}
  <div class="cal">
    <div class="cal-header">{_h(mes_label)}</div>
    <div class="cal-day">{_h(dia_label)}</div>
  </div>
  <div class="content">
    <h1 class="capa-titulo">{_h(titulo)}</h1>
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""


# Registry dos arquetipos de capa do Brand Hub Sindicompany 2026-05-17.
#
# REGRA INDISPENSAVEL: todo arquetipo que tem variante COM FOTO deve
# usar exatamente a foto carregada pelo operador na etapa 3 "Foto da
# capa" do /sindicompany/carrossel/novo. Essa URL chega como
# foto_capa_url no parametro de cada funcao, originada de
# carrosseis.foto_capa_url no Supabase. NAO buscar foto stock, NAO
# gerar via IA, NAO usar foto de outro slide — sempre a foto da etapa 3.
#
# Arquetipos SEM foto (capas 03/04/05/06/14 e similares) descartam o
# parametro via `del foto_capa_url` no inicio da funcao.
#
# Arquetipos COM foto (capas 02/07/11/25/31/32/33/35/36/37/38/39/40/42
# do doc) devem ler foto_capa_url e renderizar a foto. Se foto_capa_url
# vier vazia, eh aceitavel cair pra uma variante minimalista sem foto
# (ver _capa_editorial_question como referencia).
COVER_ARCHETYPES_SC = {
    # SEM foto (7) — selecionados pela Juliana 2026-05-18
    "numbered-guide": _capa_numbered_guide,
    "manifesto": _capa_manifesto,
    "pattern-explosion": _capa_pattern_explosion,
    "sticky-note": _capa_sticky_note,
    "brackets": _capa_brackets,
    "type-tower": _capa_type_tower,
    "corner-tape": _capa_corner_tape,
    # COM foto (10) — consomem foto_capa_url da etapa 3
    "dark-premium": _capa_dark_premium,
    "magazine-cover": _capa_magazine_cover,
    "split-portrait": _capa_split_portrait,
    "hero-portrait": _capa_hero_portrait,
    "photo-circle": _capa_photo_circle,
    "photo-banner": _capa_photo_banner,
    "photo-blur": _capa_photo_blur,
    "cinema": _capa_cinema,
    "polaroid": _capa_polaroid,
    "portrait-frame": _capa_portrait_frame,
}
# Arquetipos removidos da selecao (funcoes _capa_* mantidas no arquivo
# por enquanto pra preservar git history e permitir voltar facil; limpeza
# do dead code fica pra commit dedicado): editorial-question, stat-slap,
# pull-quote, headline-only, glow-hero, versus, mythbuster, split-color,
# grid-stats, highlight, stamp, bullet-list, wallpaper, underline,
# timeline, conversation, receipt, ribbon, maxi-quote, calendar,
# polaroid-stack, avatar-quote, floating-card, photo-strip, photo-grid.


def _slide_pagination(
    slide_idx: int,
    total: int,
    is_frase: bool,
    accent: str,
    fg_color: str,
    font_numeric: str,
) -> str:
    """Paginacao do slide (pool por carrossel), pra TODAS as marcas. Cores
    da marca (accent + texto) e fonte numerica da marca. Frase/respiro nao
    recebe marcador. Substitui o antigo numero gigante (bignum)."""
    if is_frase:
        return ""
    return brand_kit.sc_pagination_html(
        _PAGINATION_STYLE or "dots",
        slide_idx,
        total,
        accent,
        fg_color,
        font=font_numeric,
    )


def _slide_html(
    *,
    slide_idx: int,
    total: int,
    tipo: str,
    titulo: str,
    body: str,
    formato: str = "",
    foto_capa_url: str = "",
    foto_slide_url: str = "",
    is_capa: bool = False,
) -> str:
    """Monta o HTML de um único slide pronto pra renderizar."""
    p = _palette()
    handle = _handle()
    is_consvicta = _BRAND == "consvictabr"
    # Consvicta usa tipografia propria (Cormorant Garamond + Outfit +
    # Bebas Neue), embutida via base64. Sindicompany/By Sindicompany
    # usam Provicali (wordmark) + Epilogue (display/body/numeric)
    # tambem embutidas via base64 do Brand Hub 2026-05-17. Sem
    # dependencia de Google Fonts no render.
    # Marca nova com tipografia propria (zip de fontes importado): embute as
    # fontes do bucket. Se nao houver/falhar, cai no caminho embutido padrao.
    # Para as 3 marcas chumbadas _BRAND_TIPOGRAFIA e None -> brand_fonts None.
    brand_fonts = _brand_fonts_from_tipografia()
    if brand_fonts:
        head_fonts, font_display, font_body, font_numeric = brand_fonts
    elif is_consvicta:
        head_fonts = f"<style>{_consvicta_fonts_css()}</style>"
        font_display = "'Cormorant Garamond', Georgia, serif"
        font_body = "'Outfit', system-ui, sans-serif"
        font_numeric = "'Bebas Neue', Impact, sans-serif"
    else:
        sindi_css = _sindicompany_fonts_css()
        if sindi_css:
            head_fonts = f"<style>{sindi_css}</style>"
        else:
            # Fallback: Google Fonts Epilogue se o CSS inline nao tiver
            # sido empacotado por algum motivo.
            head_fonts = (
                '<link href="https://fonts.googleapis.com/css2?'
                'family=Epilogue:wght@400;600;800;900&display=swap" '
                'rel="stylesheet">'
            )
        font_display = "'Epilogue', sans-serif"
        font_body = "'Epilogue', sans-serif"
        font_numeric = "'Epilogue', sans-serif"
    # Logo 5 sempre no topo de TODOS os slides (capa + internos + CTA)
    # Logo no topo de TODOS os slides. @sindicompanybr usa o slot 5;
    # @bysindicompany usa o slot 1 (LOGO 1 do bucket __by-logos).
    # @bysindicompany usa LOGO 1 do bucket __by-logos no topo;
    # @consvictabr usa LOGO 1 do bucket __consvicta-logos; @sindicompanybr
    # usa o slot 5 do bucket __logos (logo principal Sindicompany).
    if _BRAND == "sindicompanybr":
        # Logo recolorivel (Brand Kit): simbolo por mascara + wordmark
        # Provicali, colorido pelo fundo do slide (capa/CTA escuros ->
        # branco; conteudo claro -> navy). Substitui o PNG de slot fixo.
        _bg_dark = (
            is_capa
            or (tipo or "").strip().lower() == "cta"
            or slide_idx == total
        )
        _hc, _dc, _wc = brand_kit.pick_logo_colors(_bg_dark, _palette())
        logo_top_img = brand_kit.sc_logo_horizontal_html(
            720, _hc, _dc, _wc, klass="logo-top"
        )
        if not logo_top_img:  # mascara ausente -> fallback pro slot legado
            _u = _logo_slot_data_url(5)
            logo_top_img = (
                f'<img class="logo-top" src="{_u}" alt="" />' if _u else ""
            )
    else:
        if _BRAND == "bysindicompany":
            logo_top_slot = 1
        elif _BRAND == "consvictabr":
            logo_top_slot = 1
        else:
            logo_top_slot = 5
        logo_top_url = _logo_slot_data_url(logo_top_slot)
        logo_top_img = (
            f'<img class="logo-top" src="{logo_top_url}" alt="" />'
            if logo_top_url
            else ""
        )

    if is_capa:
        # Slide 1: foto na metade de cima + texto sobre overlay escuro embaixo.
        # Sem foto: Sindicompany usa o gradiente Deep Sea (navy->purple);
        # demais marcas mantem o fallback mint->onix.
        _capa_grad = (
            brand_kit.gradient_css("deep_sea")
            if _BRAND == "sindicompanybr"
            else f'linear-gradient(135deg, {p["mint"]} 0%, {p["onix"]} 100%)'
        )
        bg = (
            f'<div class="hero-img" style="background-image: url(\'{foto_capa_url}\')"></div>'
            if foto_capa_url
            else f'<div class="hero-img" style="background: {_capa_grad};"></div>'
        )
        body_html = (
            f'<p class="capa-body">{_h_with_data(body, is_consvicta)}</p>'
            if body
            else ""
        )
        # Capa: Consvicta usa smart-picker (biblioteca de 86 icones
        # embutida, escolhe por keyword do titulo+body). Outras marcas
        # seguem o slot fixo 2 do bucket __icons/.
        if is_consvicta:
            stem = _consvicta_pick_icon(titulo, body, fallback_ctx="capa")
            # Na capa o fundo eh sempre escuro (hero img) → icone branco.
            icon_url = _consvicta_icon_data_url(stem, "#FDFCF9")
        elif _BRAND == "sindicompanybr":
            # Brand Kit ja cobre a marca (logo recolorivel); nao usa o icone
            # legado do bucket __icons na capa (senao o que for subido na
            # galeria de Icons reaparece no canto da capa).
            icon_url = ""
        else:
            icon_url = _icon_slot_data_url(2)
        icon_img = (
            f'<img class="brand-icon" src="{icon_url}" alt="" />' if icon_url else ""
        )
        # Watermark do logo Consvicta — REMOVIDO por decisao de design
        # (limpa o fundo dos carrosseis @consvictabr). Mantem variavel
        # vazia pra nao quebrar o CSS template.
        watermark_url = ""
        watermark_div = ""
        # Pattern + Fundo Carrossel na CAPA pra Consvicta — sempre
        # aplicados pra enriquecer visualmente. Outras marcas nao
        # tem pattern na capa (comportamento legado).
        capa_pattern_url = (
            _pattern_for_slide(1, is_capa=True) if is_consvicta else ""
        )
        capa_pattern_div = (
            '<div class="pattern-bg-capa"></div>' if capa_pattern_url else ""
        )
        capa_fundo_url = (
            _icon_for_slide(1, is_capa=True) if is_consvicta else ""
        )
        capa_fundo_div = (
            '<div class="icon-bg-capa"></div>' if capa_fundo_url else ""
        )

        # Brand Hub 2026-05-17: arquetipo de capa lido da variavel de
        # modulo _COVER_ARCHETYPE (setada em gerar_carrossel a partir
        # do campo carrosseis.cover_archetype, ou da env var legada
        # SINDICOMPANY_COVER_ARCHETYPE). Vazio ou desconhecido mantem
        # a capa classica. So aplica pras marcas Sindicompany
        # (sindicompanybr + bysindicompany), nunca pra Consvicta.
        archetype_fn = COVER_ARCHETYPES_SC.get(_COVER_ARCHETYPE)
        if archetype_fn is not None and not is_consvicta:
            return archetype_fn(
                titulo=titulo,
                body=body,
                handle=handle,
                logo_top_img=logo_top_img,
                head_fonts=head_fonts,
                font_display=font_display,
                font_body=font_body,
                foto_capa_url=foto_capa_url,
            )

        # Capa editorial (Brand Kit): a foto entra na silhueta da casa
        # (symbolWindow). So Sindicompany, quando o carrossel sorteou o
        # estilo "house" E ha foto de capa. Fundo Deep Sea.
        if (
            _BRAND == "sindicompanybr"
            and _CAPA_STYLE == "house"
            and foto_capa_url
        ):
            _hero = brand_kit.sc_symbol_window_html(
                1500, foto_capa_url, p["mint"], photo_focus="50% 28%"
            )
            if _hero:
                _deep = brand_kit.gradient_css("deep_sea")
                _badge = _h(_formato_label(formato))
                return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{ font-family: {font_body}; background: {_deep};
    color: {p["white"]}; overflow: hidden; position: relative; }}
  .logo-top {{ position: absolute; top: 100px; left: 180px; z-index: 5; }}
  .hero-window {{ position: absolute; top: 380px; left: 0; right: 0;
    display: flex; justify-content: center; }}
  .content {{ position: absolute; left: 180px; right: 180px; bottom: 430px;
    z-index: 4; }}
  .badge {{ display: inline-block; border: 3px solid rgba(255,255,255,0.4);
    color: {p["white"]}; font-family: {font_body}; font-weight: 700;
    font-size: 60px; letter-spacing: 0.18em; padding: 18px 34px;
    border-radius: 10px; text-transform: uppercase; }}
  .capa-titulo {{ font-family: {font_display}; font-weight: 800;
    font-size: 232px; line-height: 0.95; letter-spacing: -0.02em;
    color: {p["white"]}; margin-top: 44px; text-wrap: balance;
    max-width: 17ch; }}
  .hook-hl {{ color: {p["lavender"]}; background-image: linear-gradient(
    transparent 62%, {p["lavender"]}33 62%); background-repeat: no-repeat; }}
  .handle {{ position: absolute; bottom: 120px; left: 180px;
    font-family: {font_body}; font-size: 77px; font-weight: 600;
    color: {p["white"]}; opacity: 0.85; letter-spacing: 0.08em; }}
</style></head>
<body>
  {logo_top_img}
  <div class="hero-window">{_hero}</div>
  <div class="content">
    <span class="badge">{_badge}</span>
    <h1 class="capa-titulo">{_h_hook(titulo, is_consvicta)}</h1>
  </div>
  <div class="handle">{handle}</div>
</body></html>
"""

        # Cor do titulo da capa: cromatica da marca, legivel no painel
        # escuro (onix) onde o texto da capa fica. Corpo segue em sand.
        capa_titulo_color = _pick_title_color(p["onix"], p["white"], p)
        # Hook visual: se a copy marcou o trecho-chave com [[...]], a base do
        # titulo fica neutra (branca) e o trecho marcado recebe a cor da
        # marca + grifo (.hook-hl). Sem marcador, o titulo inteiro fica na
        # cor da marca (comportamento anterior).
        capa_has_hook = "[[" in (titulo or "")
        capa_titulo_base = p["white"] if capa_has_hook else capa_titulo_color
        # Divisor (linha decorativa) varia o estilo por carrossel.
        capa_div_decl = (
            brand_kit.divider_css(
                brand_kit.pick_line_style(_CARROSSEL_SEED), p["mint"]
            )
            if _BRAND == "sindicompanybr"
            else f'background:{p["mint"]};height:6px;border-radius:3px;'
        )
        return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {p["onix"]};
    color: {p["white"]};
    overflow: hidden;
    position: relative;
  }}
  .logo-watermark {{
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 2200px; height: 2200px;
    background-image: url('{watermark_url}');
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
    opacity: 0.06;
    pointer-events: none;
    z-index: 1;
  }}
  .pattern-bg-capa {{
    /* Pattern dark da Consvicta cobrindo a capa toda, 40% opacity
       (peso visual do brand book). Senta entre o hero-img e o
       overlay pro texto continuar legivel. */
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image: url('{capa_pattern_url}');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    opacity: 0.40;
    pointer-events: none;
    z-index: 1;
  }}
  .icon-bg-capa {{
    /* Fundo Carrossel da capa Consvicta (slot 1 ou fallback logo
       simbolo) — grande, baixa opacidade, rente a borda esquerda
       inferior (mirror do bottom-right do icone). */
    position: absolute;
    bottom: 0; left: 0;
    width: 2400px; height: 2400px;
    background-image: url('{capa_fundo_url}');
    background-repeat: no-repeat;
    background-position: left bottom;
    background-size: contain;
    opacity: 0.12;
    pointer-events: none;
    z-index: 1;
  }}
  .hero-img {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }}
  .vignette {{
    /* Vignette cinematografica — escurece sutilmente os cantos pra
       dar profundidade e foco no centro da foto. */
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at center,
      transparent 50%,
      rgba(26,28,41,0.45) 100%);
    pointer-events: none;
  }}
  .overlay {{
    /* Texto da capa ocupa exatamente 50% (metade de baixo).
       Topo segue limpo pra a foto aparecer; metade de baixo tem
       gradiente forte pra contraste do titulo. */
    position: absolute; top: 50%; left: 0; right: 0; bottom: 0;
    background: linear-gradient(180deg,
      rgba(26,28,41,0.0) 0%,
      rgba(26,28,41,0.85) 18%,
      rgba(26,28,41,0.96) 100%
    );
  }}
  .content {{
    /* Caixa de texto cobre exatamente a metade inferior do slide. */
    position: absolute;
    left: 180px; right: 180px;
    top: 50%; bottom: 0;
    padding: 100px 0 220px;
    display: flex; flex-direction: column; justify-content: center;
  }}
  /* Tamanhos calibrados pra Instagram display (1080w). Slide eh
     3072w (escala 2.844x), por isso os px CSS sao maiores que os
     px display que a marca pediu:
       capa titulo  100 display -> 285 css
       capa body     50 display -> 142 css
       capa @        28 display ->  80 css */
  .badge {{
    /* Tarja de FORMATO em destaque: caixa de contorno fino,
       fundo transparente, texto branco em caixa-alta com tracking
       largo (estilo editorial dos exemplos da marca). */
    display: inline-block;
    border: 4px solid rgba(255,255,255,0.65);
    background: transparent;
    color: {p["white"]};
    font-family: {font_numeric if is_consvicta else font_body};
    font-weight: 700;
    font-size: 64px;
    letter-spacing: 0.30em;
    text-transform: uppercase;
    padding: 28px 56px;
    border-radius: 10px;
    margin-bottom: 50px;
  }}
  .accent-line {{
    /* Divisor sob o badge — estilo varia por carrossel. */
    width: 180px; margin-bottom: 50px; {capa_div_decl}
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: {500 if is_consvicta else 900};
    font-size: {300 if is_consvicta else 257}px;
    line-height: {1.0 if is_consvicta else 0.95};
    letter-spacing: -0.015em;
    color: {capa_titulo_base};
    text-wrap: balance;
    font-style: {('italic' if is_consvicta else 'normal')};
  }}
  /* Hook visual: trecho-chave do hook destacado — cor da marca + grifo
     (marca-texto) na mesma cor em baixa opacidade. Leitura instantanea. */
  .hook-hl {{
    color: {capa_titulo_color};
    background-image: linear-gradient(transparent 60%, {capa_titulo_color}33 60%);
    background-repeat: no-repeat;
    padding: 0 0.04em;
    border-radius: 4px;
  }}
  .capa-body {{
    font-family: {font_body};
    font-weight: {400 if is_consvicta else 600};
    font-size: 142px;
    line-height: 1.25;
    color: {p["sand"]};
    margin-top: 48px;
    max-width: 24ch;
    letter-spacing: {('0.005em' if is_consvicta else 'normal')};
  }}
  .handle {{
    position: absolute;
    bottom: 80px; left: 180px;
    font-family: {font_body};
    font-size: 80px;
    font-weight: {500 if is_consvicta else 600};
    color: {p["mint"]};
    letter-spacing: {('0.20em' if is_consvicta else '0.08em')};
    text-transform: {('lowercase' if is_consvicta else 'none')};
  }}
  /* Numeros / percentuais destacados inline no body/titulo
     ("23%", "20+", "6 meses"). Bebas Neue + tiffany pra reforco
     de marca, ligeiramente maior que o redor. */
  .data-hi {{
    font-family: {font_numeric};
    font-weight: 400;
    color: {p["mint"]};
    font-size: 1.12em;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }}
  /* Ambient layer Consvicta — orbs radiais e cross-hatch sutis,
     copia do hero do site consvicta.com.br. So Consvicta. */
  .ambient {{
    position: absolute; inset: 0;
    pointer-events: none;
    z-index: 1;
  }}
  .ambient-grid {{
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(176,141,87,0.05) 2px, transparent 2px),
      linear-gradient(90deg, rgba(176,141,87,0.05) 2px, transparent 2px);
    background-size: 200px 200px;
    pointer-events: none;
  }}
  .ambient-orb {{
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
    filter: blur(20px);
  }}
  .ambient-orb-gold {{
    top: -10%; right: -8%;
    width: 1800px; height: 1800px;
    background: radial-gradient(circle, rgba(176,141,87,0.18) 0%, transparent 60%);
  }}
  .ambient-orb-tiff {{
    bottom: -12%; left: -10%;
    width: 1500px; height: 1500px;
    background: radial-gradient(circle, rgba(129,216,208,0.14) 0%, transparent 60%);
  }}
  .brand-icon {{
    /* Capa: corner icon bottom-right.
       Consvicta usa biblioteca de line icons -> reduz pra 320px e
       adiciona stroke-width sutil. Outras marcas mantem 440px. */
    position: absolute;
    bottom: 80px; right: 180px;
    width: {320 if is_consvicta else 440}px;
    height: {320 if is_consvicta else 440}px;
    object-fit: contain;
    {('stroke-width: 1.8;' if is_consvicta else '')}
  }}
  .logo-top {{
    /* Logo da marca no topo de TODOS os slides. Consvicta usa SVG
       preto; capa tem hero img escura → inverte pra branco. */
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: {('brightness(0) invert(1)' if is_consvicta else 'none')};
  }}
</style></head>
<body>
  {bg}
  <div class="vignette"></div>
  {capa_pattern_div}
  {capa_fundo_div}
  {watermark_div}
  <div class="overlay"></div>
  <div class="content">
    <span class="badge">{_h(_formato_label(formato))}</span>
    <div class="accent-line"></div>
    <h1 class="capa-titulo">{_h_hook(titulo, is_consvicta)}</h1>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
  {icon_img}
</body></html>
"""

    # Slides internos: cada slide ganha uma cor de fundo diferente,
    # ciclando pares e impares por listas separadas. Garante que
    # consecutivos nao repitam (pares cycle 2, impares cycle 3).
    # Excecao: ULTIMO SLIDE (CTA) sempre fundo onix pra fechar o
    # carrossel com peso de marca.
    is_cta = tipo == "cta" or slide_idx == total
    # Slide "respiro"/frase printavel: layout centralizado e minimalista
    # (frase grande, muito espaco, sem badge/numero) — cria ritmo visual.
    # Acionado por tipo frase/respiro/quote; nao afeta os slides normais.
    is_frase = (tipo or "").strip().lower() in ("frase", "respiro", "quote") and not is_cta
    if is_cta:
        bg_color = p["onix"]
        fg_color = p["white"]
        accent = p["mint"]
        accent_text = p["onix"]
    else:
        if _BRAND == "sindicompanybr" and not is_frase:
            # Fundo limpo do Brand Kit: base off-white (alterna Paper /
            # Paper Warm pra variedade sutil) + glow por cima. Substitui o
            # ciclo de cores solidas antigo.
            bg_color = (
                p["gray_5"] if slide_idx % 2 == 0 else brand_kit.NEUTRALS["paper_warm"]
            )
        else:
            pares = [p["mint"], p["sand"]]
            impares = [p["lavender"], p["white"], p["gray_5"]]
            if slide_idx % 2 == 0:
                bg_color = pares[(slide_idx // 2 - 1) % len(pares)]
            else:
                bg_color = impares[((slide_idx - 1) // 2 - 1) % len(impares)]

        fg_color = p["onix"]
        # Accent: nas cores muito claras (white / gray_5 / paper warm) usa
        # mint pra destacar; nas medias (mint / sand / lavender) usa onix.
        if bg_color in (p["white"], p["gray_5"], brand_kit.NEUTRALS["paper_warm"]):
            accent = p["mint"]
            accent_text = p["onix"]
        else:
            accent = p["onix"]
            accent_text = p["white"]

    if is_cta:
        badge_label = _brand_label()
    elif _BRAND == "sindicompanybr":
        # Numero do slide fica SO na paginacao (canto). O badge do topo vira
        # tag de categoria (formato), sem duplicar a numeracao.
        badge_label = _formato_label(formato)
    else:
        badge_label = f"{slide_idx} / {total}"

    # Cor do titulo distinta do corpo (fg_color) -> hierarquia cromatica.
    # Puxada da paleta da marca por contraste; cai em fg se nada servir.
    titulo_color = _pick_title_color(bg_color, fg_color, p)
    # Divisor (linha decorativa) varia o estilo por carrossel.
    content_div_decl = (
        brand_kit.divider_css(brand_kit.pick_line_style(_CARROSSEL_SEED), accent)
        if _BRAND == "sindicompanybr"
        else f"background:{accent};height:6px;border-radius:3px;"
    )
    # Elemento "aspas" no slide de frase/respiro (tratamento de citacao).
    # Usa o accent DA MARCA (varia por marca). Consvicta tem estetica
    # propria -> nao recebe.
    quote_mark_div = (
        brand_kit.sc_quote_mark_html(accent)
        if (is_frase and not is_consvicta)
        else ""
    )

    body_html = (
        f'<p class="slide-body">{_h_hook(body, is_consvicta, "cta-acao" if is_cta else "body-hl")}</p>'
        if body
        else ""
    )

    # Brand Kit: watermark de canto (petalas) discreto no topo-direito.
    # So Sindicompany (Consvicta tem ambient proprio). CTA escuro usa canto
    # cyan mais visivel; conteudo claro usa navy bem sutil.
    corner_overlay_div = ""
    if _BRAND == "sindicompanybr" and not is_frase:
        _stat = "" if is_cta else brand_kit.detect_stat(body)
        if is_cta:
            corner_overlay_div = brand_kit.sc_corner_overlay_html(
                "cyan", opacity=0.15, position="right top", size="44%"
            )
        elif _stat:
            # Slide com dado claro (%, R$, "3 meses") -> stat block (numero
            # de destaque) no lugar da decoracao. So quando ha o dado.
            corner_overlay_div = brand_kit.sc_stat_block_html(_stat, titulo_color)
        else:
            # Decoracao rotativa: cada slide ganha uma forma/posicao de
            # pattern diferente (ou o acento symbolPhoto), em opacidade baixa.
            # Variedade entre slides e entre carrosseis.
            corner_overlay_div = brand_kit.sc_slide_decor_html(
                _CARROSSEL_SEED, slide_idx, p, foto_capa_url, color=_PATTERN_COLOR
            )

    # Brand Kit: receita de fundo. bg_color (hex) segue servindo o calculo
    # de contraste; bg_css e o que pinta de fato. Sindicompany: CTA usa
    # gradiente Deep Sea, respiro usa Sunset, conteudo mantem a cor base +
    # glow radial sutil pra profundidade. Demais marcas: solido (legado).
    bg_css = bg_color
    glow_div = ""
    if _BRAND == "sindicompanybr":
        if is_cta:
            bg_css = brand_kit.gradient_css("deep_sea")
        elif is_frase:
            bg_css = brand_kit.gradient_css("sunset")
        else:
            glow_div = brand_kit.sc_glow_overlay_html(
                p["mint"], p["lavender"], op1=0.30, op2=0.26
            )

    # Estilo do botao da acao do CTA (.cta-acao). Sindicompany varia o estilo
    # por carrossel (pill/square/aurora/sunset); demais usam o highlight
    # accent legado.
    if _BRAND == "sindicompanybr" and is_cta:
        cta_acao_decl = brand_kit.cta_acao_css(
            brand_kit.pick_cta_style(_CARROSSEL_SEED), p
        )
    else:
        cta_acao_decl = (
            f"background:{accent};color:{accent_text};"
            f"font-weight:{600 if is_consvicta else 800};"
            "padding:0.12em 0.34em;border-radius:14px;"
            "-webkit-box-decoration-break:clone;box-decoration-break:clone;"
        )

    # Pattern de fundo:
    # - Slides internos: pattern ciclando, tile 800x800, 10% opacity
    # - CTA (ultimo): Consvicta usa picker dark; outras marcas fixam
    #   Pattern 1 (legado). Mesma regra tile/opacity.
    # Sindicompany: NAO usa o tile antigo — o watermark de canto (Brand Kit)
    # ja e a textura da marca; o tile competiria com glow/gradiente.
    if _BRAND == "sindicompanybr":
        pattern_url = ""
    elif is_cta:
        if is_consvicta:
            pattern_url = _pattern_for_slide(slide_idx, is_cta=True)
        else:
            pats = _patterns_data_urls()
            pattern_url = pats[0] if pats else ""
    else:
        pattern_url = _pattern_for_slide(slide_idx)
    pattern_div = '<div class="pattern-bg"></div>' if pattern_url else ""

    # Tamanhos calibrados pra Instagram (1080w display). Slide 4K
    # = 2.844x, por isso CSS px = display px * 2.844 (arredondado).
    # Internos (mid 75/47/27 display): titulo 213, body 134, footer 77.
    # CTA (mid 80/52/29 display):     titulo 228, body 148, @ 82.
    if is_cta:
        titulo_font = 228
        body_font = 148
        handle_font = 82
        pagination_font = 82
        badge_font = 82
    else:
        titulo_font = 213
        body_font = 134
        handle_font = 77
        pagination_font = 77
        badge_font = 80

    # Fundo Carrossel: usado como icon-bg grande nos slides.
    # Consvicta: TODO slide (incluindo CTA) recebe pra enriquecer
    # visualmente — _icon_for_slide tem fallback pro logo simbolo.
    # Picker curado por tom do slide (light/dark). Outras marcas:
    # CTA segue sem fundo (legado).
    # Sindicompany: NAO usa o Fundo Carrossel legado — o Brand Kit ja tem
    # glow + decoracao de pattern propria (senao o pattern antigo do bucket
    # reaparece no fundo).
    if _BRAND == "sindicompanybr":
        icon_url_internal = ""
    elif is_consvicta:
        icon_url_internal = _icon_for_slide(
            slide_idx, is_cta=is_cta, is_capa=False
        )
    elif not is_cta:
        icon_url_internal = _icon_for_slide(slide_idx)
    else:
        icon_url_internal = ""
    icon_bg_div = (
        '<div class="icon-bg"></div>' if icon_url_internal else ""
    )
    # Foto opcional por slide (sobrescreve cor de fundo + pattern
    # quando a editora subiu uma na Etapa 3).
    slide_foto_div = (
        '<div class="slide-foto"></div><div class="slide-foto-overlay"></div>'
        if foto_slide_url
        else ""
    )
    # Brand-icon do canto inferior direito. Outras marcas: SO em CTA
    # (slot fixo Icon 6). Consvicta: TODO slide ganha um icone
    # smart-pickado da biblioteca de 86 (semanticamente relacionado
    # com o titulo+body). Em CTA escuro, icone branco. Em slides
    # claros, icone na cor do accent (preto/mint).
    if is_consvicta:
        stem_corner = _consvicta_pick_icon(
            titulo, body,
            fallback_ctx=("cta" if is_cta else "interno"),
        )
        # No CTA fundo onix -> icone em mint (cor accent). Slides claros
        # (mint/sand/lavender/white/gray_5) -> icone em accent (onix
        # ou mint conforme o calculo de contraste).
        corner_url = _consvicta_icon_data_url(stem_corner, accent)
    else:
        corner_url = _icon_slot_data_url(6) if is_cta else ""
    icon_img_internal = (
        f'<img class="brand-icon" src="{corner_url}" alt="" />'
        if corner_url
        else ""
    )
    # Posicao do fundo carrossel: rente a borda direita nos pares
    # (2, 4, 6) e rente a borda esquerda nos impares (3, 5, 7).
    # Imagem mantem a cor original — sem filter pra preservar a paleta
    # subida no admin Fundo Carrossel.
    icon_bleed_side = "right" if slide_idx % 2 == 0 else "left"
    # Numero editorial vai no lado OPOSTO pra equilibrar a massa visual.
    icon_bleed_side_oposto = "left" if slide_idx % 2 == 0 else "right"

    # Watermark do logo Consvicta atras de tudo (mesmo padrao da capa).
    # Watermark do logo nos slides internos/CTA — REMOVIDO por
    # decisao de design pra Consvicta (limpa o fundo).
    watermark_url_internal = ""
    watermark_div_internal = ""
    # Logo SVG vem em preto. Em slide CLARO (internos mint/sand/etc.)
    # deixa preto. Em slide ESCURO (CTA onix), inverte pra branco
    # via filter CSS. Vale tanto pro .logo-top quanto pro
    # .logo-watermark.
    logo_filter = (
        "brightness(0) invert(1)" if is_cta else "brightness(0)"
    )

    return f"""
<!doctype html><html><head><meta charset="utf-8">
{head_fonts}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {SLIDE_W}px; height: {SLIDE_H}px; }}
  body {{
    font-family: {font_body};
    background: {bg_css};
    color: {fg_color};
    overflow: hidden;
    position: relative;
  }}
  .logo-watermark {{
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 2400px; height: 2400px;
    background-image: url('{watermark_url_internal}');
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
    opacity: {0.07 if is_cta else 0.06};
    filter: {logo_filter};
    pointer-events: none;
    z-index: 1;
  }}
  .pattern-bg {{
    /* Pattern da marca como textura de fundo. Sindicompany/By:
       10% (textura sutil). Consvicta: 40% (peso visual do brand
       book — os patterns sao parte do sistema visual, nao decoracao).
       Uma unica instancia cobre todo o slide; cover preserva aspect
       ratio. */
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image: url('{pattern_url}');
    background-repeat: no-repeat;
    background-position: center center;
    background-size: cover;
    opacity: {0.40 if is_consvicta else 0.10};
    pointer-events: none;
  }}
  .frame-corner {{
    /* Molduras editoriais finas no canto superior direito —
       substitui a bola antiga, vibe revista premium. */
    position: absolute;
    top: 180px; right: 180px;
    width: 180px; height: 180px;
    border-top: 6px solid {accent};
    border-right: 6px solid {accent};
    opacity: 0.55;
  }}
  .bignum {{
    /* Numero gigante do slide como elemento editorial — opacidade
       baixa pra nao competir com texto principal. Usa o accent pra
       reforco de marca. Posicionado oposto ao Fundo Carrossel
       (pares: esquerda; impares: direita) pra equilibrar massa.
       Consvicta usa Bebas Neue (condensada) — visual editorial
       premium, mais alta e estreita. */
    position: absolute;
    bottom: 200px;
    {icon_bleed_side_oposto}: 180px;
    font-family: {font_numeric};
    font-size: {880 if is_consvicta else 720}px;
    font-weight: {400 if is_consvicta else 900};
    line-height: 0.85;
    color: {accent};
    opacity: {0.14 if is_consvicta else 0.10};
    letter-spacing: {('0.02em' if is_consvicta else '-0.04em')};
    pointer-events: none;
  }}
  .content {{
    position: absolute;
    left: 180px; right: 180px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 2;
    {('text-align: center;' if is_frase else '')}
  }}
  .badge {{
    display: inline-block;
    background: {accent};
    color: {accent_text};
    font-family: {font_numeric if is_consvicta else font_body};
    font-weight: {400 if is_consvicta else 800};
    font-size: {badge_font}px;
    letter-spacing: {('0.30em' if is_consvicta else '0.18em')};
    text-transform: uppercase;
    padding: 22px 40px;
    border-radius: 10px;
    margin-bottom: 50px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.12);
  }}
  .accent-line {{
    /* Divisor sob o badge — estilo varia por carrossel. */
    width: 180px; margin-bottom: 50px; {content_div_decl}
  }}
  .slide-titulo {{
    font-family: {font_display};
    font-weight: {500 if is_consvicta else 800};
    font-size: {(titulo_font + 70) if is_frase else ((titulo_font + 30) if is_consvicta else titulo_font)}px;
    line-height: {1.02 if is_consvicta else 0.95};
    letter-spacing: -0.015em;
    color: {titulo_color};
    margin-bottom: {0 if is_frase else 56}px;
    text-wrap: balance;
    max-width: {'16ch' if is_frase else '18ch'};
    {('margin-left: auto; margin-right: auto;' if is_frase else '')}
    font-style: {('italic' if is_consvicta else 'normal')};
  }}
  .slide-body {{
    font-family: {font_body};
    font-weight: {400 if is_consvicta else 500};
    font-size: {body_font}px;
    line-height: {1.4 if is_consvicta else 1.35};
    color: {fg_color};
    opacity: 0.88;
    max-width: 22ch;
    letter-spacing: {('0.005em' if is_consvicta else 'normal')};
  }}
  /* Ancora de atencao no corpo: trecho de alto impacto marcado com [[...]]
     -> cor da marca (mesma do titulo do slide) + peso + grifo marca-texto.
     Cria ritmo visual e impede blocos de texto iguais. */
  .body-hl {{
    color: {titulo_color};
    font-weight: {600 if is_consvicta else 800};
    background-image: linear-gradient(transparent 60%, {titulo_color}30 60%);
    background-repeat: no-repeat;
    border-radius: 4px;
  }}
  /* CTA: acao marcada vira BOTAO/caixa (cor da marca + texto contrastante
     + seta leve) — parece acionavel, nunca escondido. */
  .cta-acao {{ {cta_acao_decl} }}
  .cta-acao::after {{ content: " \\2192"; }}
  /* Para palavras destacadas dentro do body — 55-70 display
     (mid 62 -> 176 css). Use <span class="destaque">…</span>. */
  .destaque {{
    font-family: {font_numeric if is_consvicta else font_body};
    font-weight: {400 if is_consvicta else 800};
    font-size: 176px;
    line-height: 1.1;
    color: {accent};
  }}
  .handle {{
    position: absolute;
    bottom: 120px; left: 180px;
    font-family: {font_body};
    font-size: {handle_font}px;
    font-weight: {500 if is_consvicta else 600};
    color: {accent};
    letter-spacing: {('0.20em' if is_consvicta else '0.08em')};
    text-transform: {('lowercase' if is_consvicta else 'none')};
  }}
  .brand-icon {{
    /* Slides internos Consvicta: icone smart-pickado no TOP-RIGHT
       (260px), pra nao colidir com a .bignum (que ocupa o canto
       inferior em pares/impares). CTA: bottom-right (320px),
       posicao classica.
       Outras marcas: bottom-right 440px (so aparece em CTA). */
    position: absolute;
    {('top: 320px; right: 180px;' if (is_consvicta and not is_cta) else 'bottom: 80px; right: 180px;')}
    width: {(260 if (is_consvicta and not is_cta) else (320 if is_consvicta else 440))}px;
    height: {(260 if (is_consvicta and not is_cta) else (320 if is_consvicta else 440))}px;
    object-fit: contain;
  }}
  .logo-top {{
    /* Logo da marca no topo de TODOS os slides. SVG preto da Consvicta
       inverte pra branco em slides escuros (CTA). */
    position: absolute;
    top: 100px; left: 180px;
    width: 700px; max-height: 220px;
    object-fit: contain;
    z-index: 5;
    filter: {(logo_filter if is_consvicta else 'none')};
  }}
  .slide-foto {{
    /* Foto opcional por slide (sobrescreve cor de fundo + pattern).
       Cobre o slide inteiro. Renderiza so quando a editora subiu uma
       foto pro slide na Etapa 3. */
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image: url('{foto_slide_url}');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }}
  .slide-foto-overlay {{
    /* Gradiente escuro pra texto ficar legivel sobre a foto. */
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(180deg,
      rgba(26,28,41,0.30) 0%,
      rgba(26,28,41,0.55) 60%,
      rgba(26,28,41,0.85) 100%
    );
  }}
  .icon-bg {{
    /* Imagem 'Fundo Carrossel': 90% da largura do slide (~2765px),
       grudada no canto INFERIOR direito ou esquerdo (pares -> direita,
       impares -> esquerda). 0mm da borda lateral E 0mm da borda
       inferior. Mantem a cor original do arquivo (sem CSS filter).
       Opacity 0.15 — suave o suficiente pra nao competir com o texto. */
    position: absolute;
    bottom: 0;
    {icon_bleed_side}: 0;
    width: 2765px; height: 2765px;
    background-image: url('{icon_url_internal}');
    background-repeat: no-repeat;
    background-position: {icon_bleed_side} bottom;
    background-size: contain;
    opacity: 0.15;
    pointer-events: none;
  }}
  /* Numeros/percentuais destacados inline ("23%", "20+", "6 meses").
     Bebas Neue + accent — sensacao de infografico inline. So
     Consvicta (controle pelo _h_with_data). */
  .data-hi {{
    font-family: {font_numeric};
    font-weight: 400;
    color: {accent};
    font-size: 1.12em;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }}
  /* Ambient layer Consvicta — orbs radiais e cross-hatch sutis
     replicando o hero do consvicta.com.br. Atmosfera editorial sem
     competir com texto. */
  .ambient-grid {{
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(176,141,87,0.055) 2px, transparent 2px),
      linear-gradient(90deg, rgba(176,141,87,0.055) 2px, transparent 2px);
    background-size: 200px 200px;
    pointer-events: none;
    z-index: 0;
  }}
  .ambient-orb {{
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
    filter: blur(30px);
    z-index: 0;
  }}
  .ambient-orb-gold {{
    top: -10%; right: -8%;
    width: 1800px; height: 1800px;
    background: radial-gradient(circle,
      rgba(176,141,87,{0.22 if is_cta else 0.16}) 0%, transparent 62%);
  }}
  .ambient-orb-tiff {{
    bottom: -12%; left: -10%;
    width: 1500px; height: 1500px;
    background: radial-gradient(circle,
      rgba(129,216,208,{0.18 if is_cta else 0.13}) 0%, transparent 62%);
  }}
</style></head>
<body>
  {glow_div}
  {pattern_div}
  {corner_overlay_div}
  {('<div class="ambient-grid"></div><div class="ambient-orb ambient-orb-gold"></div><div class="ambient-orb ambient-orb-tiff"></div>') if is_consvicta else ''}
  {watermark_div_internal}
  {slide_foto_div}
  {icon_bg_div}
  <div class="frame-corner"></div>
  {_slide_pagination(slide_idx, total, is_frase, accent, fg_color, font_numeric)}
  <div class="content">
    {quote_mark_div}
    {('' if is_frase else f'<span class="badge">{_h(badge_label)}</span>')}
    {('' if is_frase else f'<div class="accent-line"></div>')}
    <h2 class="slide-titulo">{_h_with_data(titulo, is_consvicta)}</h2>
    {('' if is_frase else body_html)}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
  {icon_img_internal}
</body></html>
"""


def _h(s: str) -> str:
    esc = (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Marcadores -> destaque (estilos .hl/.tns-hl injetados globalmente no
    # render). Cobrem TODOS os templates (capa, internos, ~20 arquetipos)
    # sem editar cada um, pra qualquer marca. Texto sem marcador nao muda.
    #   [[...]]  -> grifo/marca-texto (.hl)        : hook, ancora, palavra magnetica
    #   ~~...~~  -> sublinhado forte (.tns-hl)      : frase de TENSAO
    esc = _HOOK_PATTERN.sub(r'<span class="hl">\1</span>', esc)
    return _TENSION_PATTERN.sub(r'<span class="tns-hl">\1</span>', esc)


# Marcadores de destaque. [[..]] = grifo; ~~..~~ = sublinhado (tensao).
_HOOK_PATTERN = re.compile(r"\[\[(.+?)\]\]")
_TENSION_PATTERN = re.compile(r"~~(.+?)~~")


def _h_hook(s: str, enabled: bool, cls: str = "hook-hl") -> str:
    """Renderiza o(s) trecho(s) marcado(s) com [[...]] como
    <span class="{cls}">, pra destacar a parte mais forte do hook na capa
    (cls=hook-hl) ou as ancoras de atencao no corpo (cls=body-hl). Fora do
    trecho aplica _h_with_data normal. Sem marcador, igual a _h_with_data."""
    s = s or ""
    out: list[str] = []
    last = 0
    for m in _HOOK_PATTERN.finditer(s):
        out.append(_h_with_data(s[last : m.start()], enabled))
        out.append(
            f'<span class="{cls}">{_h_with_data(m.group(1), enabled)}</span>'
        )
        last = m.end()
    out.append(_h_with_data(s[last:], enabled))
    return "".join(out)


# Padrao pra detectar dados quantitativos em texto: "23%", "20+",
# "6 meses", "4 horas", "100%", "R$ 5", "Art. 1.336", "2x". Casamos
# DEPOIS de escapar HTML, entao trabalha com texto plano. So pega a
# primeira parte numerica + unidade, sem comer letras vizinhas.
_DATA_NUM_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(R\$\s?\d+(?:[.,]\d+)*"
    r"|\d+(?:[.,]\d+)?\s*%"
    r"|\d+\s*\+"
    # Unidades temporais — ORDEM IMPORTA: mais longas primeiro
    # (senao "30 minutos" casa so "30 min" porque regex eh greedy
    # da esquerda pra direita na alternancia).
    r"|\d+(?:[.,]\d+)?\s+(?:minutos|semanas|meses|horas|dias|anos|min)\b"
    r"|\d+x\b)",
    re.IGNORECASE,
)


def _h_with_data(s: str, enabled: bool) -> str:
    """Versao do _h() que destaca numeros/percentuais/unidades com
    <span class="data-hi"> — Bebas Neue + accent color — pra dar
    sensacao de infografico inline no body/titulo. So ativa quando
    enabled=True (Consvicta). Senao, igual a _h()."""
    escaped = _h(s)
    if not enabled or not escaped:
        return escaped
    return _DATA_NUM_PATTERN.sub(
        r'<span class="data-hi">\1</span>', escaped
    )


# =============================================================================
# Playwright render
# =============================================================================


# Estilo do destaque generico .hl, injetado em TODO slide no render — cobre
# capa classica, internos e os ~20 arquetipos sem editar cada template.
# Marca-texto na cor do PROPRIO texto (color-mix) + peso: adapta a qualquer
# fundo/cor/marca. Degrada pra so-negrito se o navegador ignorar color-mix.
_HL_STYLE = (
    "<style>.hl{font-weight:800;"
    "background-image:linear-gradient(transparent 58%,"
    "color-mix(in srgb, currentColor 22%, transparent) 58%);"
    "background-repeat:no-repeat;border-radius:4px}"
    # Tensao: sublinhado forte na cor do proprio texto (distinto do grifo).
    ".tns-hl{font-weight:700;text-decoration:underline;"
    "text-decoration-thickness:0.09em;text-underline-offset:0.12em;"
    "text-decoration-skip-ink:none}</style>"
)


def _render_slide_png(html: str) -> bytes:
    """Renderiza HTML em PNG 3072×3839 via Playwright sync.

    Importante: aguarda document.fonts.ready ANTES de screenshot pra
    garantir que as fontes inline base64 (Consvicta usa Cormorant
    Garamond + Outfit + Bebas Neue embutidas) ja foram parseadas e
    aplicadas ao layout. Sem isso, o screenshot pode pegar fallback
    (Times/Arial) e ignorar as fontes da marca."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            ctx = browser.new_context(
                viewport={"width": SLIDE_W, "height": SLIDE_H},
                device_scale_factor=1,
            )
            page = ctx.new_page()
            html_out = (
                html.replace("</head>", _HL_STYLE + "</head>", 1)
                if "</head>" in html
                else _HL_STYLE + html
            )
            page.set_content(html_out, wait_until="networkidle")
            # Garante que TODAS as fontes da marca (inline base64) estejam
            # carregadas E aplicadas antes do screenshot. Fontes @font-face
            # carregam de forma PREGUICOSA (so quando usadas), entao forcamos
            # o load de cada face e aguardamos document.fonts.ready. Sem isso,
            # marcas com fontes pesadas (Consvicta = 2.3MB) podem ser
            # capturadas no fallback serif (Georgia) — fonte fora da marca.
            try:
                page.evaluate(
                    "async () => {"
                    "  try { await Promise.all("
                    "    Array.from(document.fonts).map((f) => f.load())"
                    "  ); } catch (e) {}"
                    "  if (document.fonts && document.fonts.ready) {"
                    "    await document.fonts.ready;"
                    "  }"
                    "}"
                )
            except Exception:  # noqa: BLE001
                pass
            # Buffer pro layout/paint aplicar as fontes recem-carregadas.
            page.wait_for_timeout(300)
            png = page.screenshot(
                full_page=False,
                type="png",
                clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H},
            )
            return png
        finally:
            browser.close()


# =============================================================================
# Humanizer (todas as marcas)
# =============================================================================


# Regras de marca pro humanizer batch: handle, tagline e anti-leak
# por marca. Cada carrossel passa pela mesma skill humanizer, mas o
# prompt injeta as regras especificas pra preservar a identidade da
# conta e proibir mencao a marcas irmas/concorrentes.
_BRAND_HUMANIZER_RULES: dict[str, dict[str, str]] = {
    "consvictabr": {
        "handle": "@consvictabr",
        "assinatura": "Administração condominial que entrega resultado.",
        "anti_leak": (
            "PROIBIDO mencionar Sindicompany, By Sindicompany, "
            "@sindicompanybr, @bysindicompany, 'Por mais lares' ou qualquer "
            "concorrente. A marca aqui e SO Consvicta."
        ),
        "tom": (
            "Tom premium boutique: confiante, proximo, tecnico-mas-humano. "
            "Fala com sindico profissional, conselho consultivo, "
            "proprietario atento de predio premium em SP/RJ."
        ),
    },
    "bysindicompany": {
        "handle": "@bysindicompany",
        "assinatura": "By Sindicompany. Sindicatura no próximo nível.",
        "anti_leak": (
            "Mantenha a identidade @bysindicompany. PROIBIDO mencionar "
            "@consvictabr ou Consvicta. Sindicompany pode ser citada como "
            "marca-mae quando fizer sentido."
        ),
        "tom": (
            "Tom aspiracional, provocativo, estrategico, empresarial. Fala "
            "com SINDICO PROFISSIONAL, NAO com o morador. Mentor que ja "
            "chegou."
        ),
    },
    "sindicompanybr": {
        "handle": "@sindicompanybr",
        "assinatura": "Por mais lares. 🏡",
        "anti_leak": (
            "Mantenha a identidade @sindicompanybr. PROIBIDO mencionar "
            "@consvictabr ou Consvicta. By Sindicompany pode ser citada "
            "como marca-irma quando fizer sentido."
        ),
        "tom": (
            "Tom direto, pessoa inteligente corrigindo um amigo. Fala "
            "com o MORADOR COMUM, nao com o sindico."
        ),
    },
}


# Regex-based brand leak filter. Por marca, define os termos
# proibidos e o que colocar no lugar. Os termos sao matched com word
# boundaries pra nao mutilar palavras parciais. Case-insensitive.
# Aplicado APOS o humanizer como ultima linha de defesa.
_BRAND_LEAK_FILTERS: dict[str, list[tuple[str, str]]] = {
    "consvictabr": [
        # ORDEM IMPORTA — patterns mais especificos PRIMEIRO senao
        # regex mais ampla come o prefixo (e.g. \bSindicompany matches
        # 'sindicompany' dentro de '#sindicompany').
        # Hashtags (1o pra preservar lowercase)
        (r"#bysindicompany\b", "#consvicta"),
        (r"#sindicompany\b", "#consvicta"),
        # Handles
        (r"@bysindicompany\b", "@consvictabr"),
        (r"@sindicompanybr\b", "@consvictabr"),
        # Nomes compostos antes dos simples
        (r"\bBy Sindicompany\b", "Consvicta"),
        (r"\bby sindicompany\b", "Consvicta"),
        (r"\bSindicompany\b", "Consvicta"),
        (r"\bsindicompany\b", "Consvicta"),
        # Tagline errada (variantes com/sem emoji)
        (r"\s*Por mais lares\.?\s*🏡?", ""),
        (r"\s*por mais lares\.?\s*🏡?", ""),
    ],
    "bysindicompany": [
        (r"#consvicta\b", "#bysindicompany"),
        (r"@consvictabr\b", "@bysindicompany"),
        (r"\bConsvicta\b", "By Sindicompany"),
        (r"\bconsvicta\b", "By Sindicompany"),
    ],
    "sindicompanybr": [
        (r"#consvicta\b", "#sindicompany"),
        (r"@consvictabr\b", "@sindicompanybr"),
        (r"\bConsvicta\b", "Sindicompany"),
        (r"\bconsvicta\b", "Sindicompany"),
    ],
}


def _sanitize_brand_leak(
    slides: list[dict[str, Any]], legenda: str, brand: str
) -> tuple[list[dict[str, Any]], str]:
    """Substitui mencoes proibidas pelas equivalentes da marca atual.
    Roda DEPOIS do humanizer como ultima linha de defesa contra leak.
    Tambem normaliza espacos duplicados e pontuacao orfã que possa
    sobrar das substituicoes."""
    filters = _BRAND_LEAK_FILTERS.get(brand) or []
    if not filters:
        return slides, legenda

    def _clean(text: str) -> str:
        if not text:
            return text
        out = text
        for pattern, repl in filters:
            out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
        # Limpa artefatos: espaços duplos, virgula+espaço solto antes
        # de ponto, virgulas duplas etc.
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r",\s*\.", ".", out)
        out = re.sub(r",\s*,", ",", out)
        out = re.sub(r"\s+([,.!?;:])", r"\1", out)
        return out.strip()

    leaked = 0
    for s in slides:
        new_titulo = _clean(str(s.get("titulo") or ""))
        new_body = _clean(str(s.get("body") or ""))
        if new_titulo != str(s.get("titulo") or ""):
            leaked += 1
        if new_body != str(s.get("body") or ""):
            leaked += 1
        s["titulo"] = new_titulo
        s["body"] = new_body

    new_legenda = _clean(legenda)
    if new_legenda != legenda:
        leaked += 1
    if leaked:
        print(
            f"[carrossel] sanitizer ({brand}) corrigiu {leaked} leak(s) de "
            f"marca apos o humanizer",
            flush=True,
        )

    return slides, new_legenda


def _humanizer_pass(
    slides: list[dict[str, Any]], legenda: str, brand: str
) -> tuple[list[dict[str, Any]], str]:
    """Aplica a skill Humanizer + revisão pt-BR em TODOS os slides e
    legenda de um carrossel, independente da marca.

    Pipeline:
      1. Pre: dicionario deterministico de acentos
         (_apply_accent_dict do text_gen) — pega 'manutencao' ->
         'manutenção', 'voce' -> 'você', etc. Sempre roda.
      2. OpenAI batch: 1 chamada GPT com SYSTEM_HUMANIZER + JSON com
         TODOS os slides+legenda. Modelo devolve versao revisada
         (sem gerundio, sem clichê, sem traço, acentos OK, mesmo
         sentido). Se OpenAI falhar/timeout, mantem o resultado da
         etapa 1.
      3. Post: passa o accent-dict de novo (rede de seguranca).

    As regras especificas da marca (handle, assinatura, anti-leak,
    tom) sao injetadas no prompt — vide _BRAND_HUMANIZER_RULES.

    Preserva: tipo de cada slide, numeros (38%, 6 dias, etc), citacoes
    literais (Art. 1.336, REsp X), nome da marca e o handle.
    """
    if not slides:
        return slides, legenda

    # Etapa 1 — pre: accent dict deterministico
    try:
        from api.text_gen import _apply_accent_dict, SYSTEM_HUMANIZER
    except Exception as e:  # noqa: BLE001
        print(f"[carrossel] text_gen indisponivel pro humanizer: {e}", flush=True)
        return slides, legenda

    for s in slides:
        s["titulo"] = _apply_accent_dict(str(s.get("titulo") or ""))
        s["body"] = _apply_accent_dict(str(s.get("body") or ""))
    legenda = _apply_accent_dict(legenda or "")

    # Etapa 2 — OpenAI batch
    cli = _openai_client()
    if cli is None:
        print(
            f"[carrossel] humanizer pulou (OPENAI_API_KEY ausente) — "
            f"slides com accent-fix deterministico aplicado",
            flush=True,
        )
        return slides, legenda

    # Marca nova: NAO cai nas regras da Sindicompany (handle/tom/assinatura
    # dela vazariam). Constroi regras dinamicas com o handle/nome reais e um
    # tom NEUTRO que preserva o nicho da marca — nunca injeta tema
    # condominial/voz de sindico se o texto nao for disso.
    rules = _BRAND_HUMANIZER_RULES.get(brand)
    if rules is None:
        nome = _BRAND_NAME or _BRAND
        rules = {
            "handle": _BRAND_HANDLE or f"@{brand}",
            "assinatura": "",
            "anti_leak": (
                f"A marca aqui e SO {nome}. NAO mencione outras marcas/"
                "concorrentes (Sindicompany, By Sindicompany, Consvicta)."
            ),
            "tom": (
                f"Mantenha a VOZ e o NICHO de {nome} conforme o conteudo "
                "recebido. NAO mude de assunto, NAO injete tema condominial, "
                "sindico, assembleia nem morador a menos que o proprio texto "
                "ja seja desse nicho."
            ),
        }

    payload = json.dumps(
        {
            "slides": [
                {
                    "i": i,
                    "tipo": str(s.get("tipo") or ""),
                    "titulo": str(s.get("titulo") or ""),
                    "body": str(s.get("body") or ""),
                }
                for i, s in enumerate(slides)
            ],
            "legenda": legenda,
        },
        ensure_ascii=False,
    )

    prompt = (
        f"Recebe um JSON com 'slides' (lista de {{i, tipo, titulo, body}}) e "
        f"'legenda' de um carrossel {rules['handle']}. Devolve o MESMO JSON, "
        f"mesmas chaves, com os textos revisados pelas regras da skill "
        f"Humanizer.\n\n"
        f"IDENTIDADE DA CONTA: {rules['handle']}\n"
        f"TOM: {rules['tom']}\n\n"
        "REGRAS DURAS:\n"
        "- Português brasileiro com TODOS os acentos corretos (á, é, í, ó, ú, "
        "â, ê, ô, ã, õ, ç, à). Sem exceções: 'voce'->você, 'sindico'->"
        "síndico, 'condominio'->condomínio, 'gestao'->gestão, 'manutencao'->"
        "manutenção, 'reuniao'->reunião, 'area'->área, 'experiencia'->"
        "experiência, 'ate'->até, 'tambem'->também, 'nao'->não.\n"
        "- ZERO travessões (—, –) — substitua por vírgula ou ponto.\n"
        "- ZERO gerúndio decorativo: 'garantindo', 'proporcionando', "
        "'destacando', 'refletindo' — reescreva com verbo direto.\n"
        "- ZERO clichês corporativos: 'soluções integradas', 'sinergia', "
        "'excelência', 'transformação digital', 'atendimento acolhedor', "
        "'levando em consideração', 'nesse contexto', 'vale destacar', "
        "'é importante ressaltar', 'dito isso', 'papel fundamental', "
        "'momento crucial', 'cenário em constante evolução', 'futuro "
        "promissor', 'estudos mostram', 'especialistas afirmam'.\n"
        "- ZERO clichê motivacional: 'acredite no seu potencial', 'saia "
        "da zona de conforto', 'o céu é o limite', 'mindset vencedor'.\n"
        "- ZERO aspas curvas (“”) — só aspas retas (\").\n"
        "- ZERO emoji decorativo nos slides. Legenda também sem emoji "
        "decorativo (excessao: a assinatura literal da marca pode "
        "conservar emoji se for parte oficial dela).\n"
        "- ZERO construção 'não apenas X, mas também Y'.\n"
        "- Frases curtas, voz ativa, sujeito explícito. Uma ideia por frase.\n"
        "- Mantenha o MESMO sentido. Não encurte, não infle, não troque "
        "argumentos. Não invente fato. Não remova número, percentual ou "
        "citação literal (Art. 1.336, STJ REsp X, Lei 4.591/64).\n"
        f"- ANTI-LEAK: {rules['anti_leak']}\n"
        f"- Assinatura/tagline desta conta: '{rules['assinatura']}' — "
        f"aparece SO na legenda, NUNCA num slide.\n"
        "- Preserve 'tipo' e 'i' exatamente.\n"
        "- DESTAQUE [[ ]] (ULTIMA etapa, depois de reescrever): GARANTA no SEU "
        "output que estejam entre [[ ]] — adicione se faltar, mantenha se ja "
        "houver. Marque: (1) no titulo do slide 'capa', o trecho MAIS FORTE do "
        "hook (2 a 5 palavras); (2) no body de CADA slide de conteudo, 1 trecho "
        "de alto impacto (verdade incomoda, identificacao, tensao, frase "
        "memoravel ou palavra-chave forte) — no maximo 2 por slide; (3) no "
        "ultimo slide (CTA), a ACAO principal. Esses [[ ]] viram o DESTAQUE "
        "VISUAL da arte, entao TODO carrossel precisa te-los. PRESERVE tambem "
        "os marcadores ~~ ~~ (frase de tensao -> sublinhado) exatamente onde "
        "vierem. Nunca marque a legenda.\n\n"
        "Devolva JSON estrito (sem markdown, sem comentários):\n"
        '{"slides":[{"i":0,"tipo":"capa","titulo":"...","body":"..."},...],'
        '"legenda":"..."}\n\n'
        f"INPUT:\n{payload}"
    )

    try:
        resp = cli.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_HUMANIZER},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print(
            f"[carrossel] humanizer OpenAI falhou ({type(e).__name__}: {e}) "
            f"— segue com accent-fix deterministico",
            flush=True,
        )
        return slides, legenda

    # Aplica revisão de volta, indexada por 'i'. Slide sem entry na
    # resposta mantem o valor pos-accent-dict (etapa 1).
    out_slides = data.get("slides")
    if isinstance(out_slides, list):
        by_idx: dict[int, dict[str, Any]] = {}
        for item in out_slides:
            if not isinstance(item, dict):
                continue
            i = item.get("i")
            if isinstance(i, int) and 0 <= i < len(slides):
                by_idx[i] = item
        for i, s in enumerate(slides):
            up = by_idx.get(i)
            if not up:
                continue
            titulo = up.get("titulo")
            body = up.get("body")
            # Trava deterministica: se o humanizer REDUZIU os marcadores
            # [[ ]] de um campo (drop nao-deterministico do GPT), mantem o
            # texto de ANTES — que ja tem os marcadores + acentos. Garante o
            # destaque mesmo quando o GPT ignora a regra de preservar.
            if isinstance(titulo, str) and titulo.strip():
                new_t = _apply_accent_dict(titulo)
                old_t = str(s.get("titulo") or "")
                if (old_t.count("[[") > new_t.count("[[")
                        or old_t.count("~~") > new_t.count("~~")):
                    print(
                        f"[carrossel] humanizer dropou destaque no titulo {i}; mantendo original",
                        flush=True,
                    )
                else:
                    s["titulo"] = new_t
            if isinstance(body, str):
                new_b = _apply_accent_dict(body)
                old_b = str(s.get("body") or "")
                if (old_b.count("[[") > new_b.count("[[")
                        or old_b.count("~~") > new_b.count("~~")):
                    print(
                        f"[carrossel] humanizer dropou destaque no body {i}; mantendo original",
                        flush=True,
                    )
                else:
                    s["body"] = new_b

    new_legenda = data.get("legenda")
    if isinstance(new_legenda, str) and new_legenda.strip():
        legenda = _apply_accent_dict(new_legenda)

    # Etapa 3 — Hard sanitizer: filtra mencoes proibidas. Mesmo com o
    # SYSTEM_HUMANIZER + ANTI-LEAK no prompt, o modelo as vezes
    # escorrega e deixa "Sindicompany" ou tagline errada num slide.
    # Esse pass faz substituicao deterministica conforme as regras
    # de marca — ultima linha de defesa antes do render.
    slides, legenda = _sanitize_brand_leak(slides, legenda, brand)

    print(
        f"[carrossel] humanizer ({brand}) aplicado em {len(slides)} slides + "
        f"legenda",
        flush=True,
    )
    return slides, legenda


# =============================================================================
# Pipeline
# =============================================================================


def _auto_hook(text: str) -> str:
    """Garante UM destaque [[ ]] num texto que nao tem nenhum, de forma
    deterministica (sem LLM). Heuristica: destaca a ultima clausula (apos
    virgula/;/:) se for curta, senao os ultimos ~60% das palavras (2 a 6),
    sem engolir a pontuacao final. Usado como rede de seguranca final pra
    o destaque NUNCA faltar."""
    t = (text or "").strip()
    if not t or "[[" in t:
        return text
    # Considera so a ULTIMA sentenca como base (o "payoff"); preserva as
    # anteriores fora do destaque pra nao grifar atravessando o ponto.
    sents = re.split(r"(?<=[.!?])\s+", t)
    if len(sents) > 1 and len(sents[-1].split()) >= 2:
        prefix = t[: t.rfind(sents[-1])]
        base = sents[-1]
    else:
        prefix = ""
        base = t
    words = base.split()
    if len(words) < 2:
        return text
    m = re.search(r"[,;:]\s+([^,;:]{3,})$", base)
    if m and 2 <= len(m.group(1).split()) <= 7:
        head = base[: m.start(1)]
        tail = m.group(1)
    else:
        n = max(2, min(6, round(len(words) * 0.6)))
        head = " ".join(words[:-n])
        head = (head + " ") if head else ""
        tail = " ".join(words[-n:])
    pm = re.match(r"^(.*?)([.!?,;:]*)$", tail.strip())
    core, punct = pm.group(1), pm.group(2)
    if not core:
        return text
    return f"{prefix}{head}[[{core}]]{punct}"


def _ensure_hooks(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rede de seguranca FINAL (apos humanizer + sanitizer): se um slide
    ainda nao tem [[ ]], adiciona deterministicamente. Capa garante o hook
    no titulo; slides de conteudo garantem 1 ancora no body. CTA e slides
    'frase'/respiro sao deixados pro modelo (nao forca)."""
    total = len(slides)
    for i, s in enumerate(slides):
        tipo = (s.get("tipo") or "").strip().lower()
        is_capa = tipo == "capa" or i == 0
        is_cta = tipo == "cta" or i == total - 1
        is_frase = tipo in ("frase", "respiro", "quote")
        # Considera [[ ]] (grifo) E ~~ ~~ (tensao) como "ja tem destaque".
        if is_capa:
            t = s.get("titulo") or ""
            if "[[" not in t and "~~" not in t:
                s["titulo"] = _auto_hook(t)
        elif not is_cta and not is_frase:
            body = s.get("body") or ""
            if body.strip() and "[[" not in body and "~~" not in body:
                s["body"] = _auto_hook(body)
    return slides


# Heuristica: o ultimo slide ja tem CTA? (verbo de acao ou pergunta no fim)
_CTA_RX = re.compile(
    r"comenta|salv[ae]|compartilh|manda|marca\b|segue|chama|link na bio|"
    r"merece|responde|\?\s*$",
    re.IGNORECASE,
)
_CTA_DEFAULTS = {
    "comentarios": "[[Comenta]] o que você faria.",
    "salvamentos": "[[Salva esse post]] pra usar depois.",
    "clientes": "[[Chama a gente]] pra resolver isso.",
    "autoridade": "[[Compartilha]] com quem precisa ver.",
    "educar": "[[Salva esse post]] pra não esquecer.",
}


def _ensure_cta(
    slides: list[dict[str, Any]], objetivo: str
) -> list[dict[str, Any]]:
    """Garante uma chamada para acao no ULTIMO slide. Se ele nao tiver CTA
    (modelo as vezes termina so com frase memoravel), adiciona um default
    por objetivo. Deterministico — o CTA NUNCA mais some."""
    if not slides:
        return slides
    last = slides[-1]
    txt = f"{last.get('titulo') or ''} {last.get('body') or ''}"
    if _CTA_RX.search(txt):
        return slides  # ja tem CTA (nao duplica)
    cta = _CTA_DEFAULTS.get((objetivo or "").strip().lower(), "[[Salva esse post]].")
    body = str(last.get("body") or "").rstrip()
    last["body"] = (body + " " + cta).strip() if body else cta
    print(f"[carrossel] CTA ausente no ultimo slide; adicionado default", flush=True)
    return slides


def gerar_carrossel(carrossel_id: str) -> int:
    """Pipeline completo. Retorna 0 se OK, 1 se falhou."""
    global _BRAND, _COVER_ARCHETYPE, _BRAND_PALETTE, _BRAND_PREFIX, _BRAND_HANDLE
    global _BRAND_TIPOGRAFIA, _BRAND_NAME, _PAGINATION_STYLE, _CAPA_STYLE
    global _CARROSSEL_SEED, _PATTERN_COLOR
    global _SC_NAVY, _SC_CYAN, _SC_BEIGE, _SC_LAVENDER, _SC_PURPLE, _SC_PAPER, _SC_PAPER_WARM
    print(f"[carrossel] iniciando geração de {carrossel_id}", flush=True)
    try:
        carrossel = _fetch_carrossel(carrossel_id)
        if not carrossel:
            print(f"[carrossel] {carrossel_id} não encontrado", flush=True)
            return 1

        # Define a marca ANTES de qualquer lookup de asset (buckets,
        # handle, logo). Default sindicompanybr pra registros legacy.
        # Mantem o slug REAL da marca (marca nova inclusive). Sanitiza pra
        # [a-z0-9-] porque o slug vira parte de URL de storage. Vazio ->
        # default sindicompanybr (registros legacy).
        b = (carrossel.get("brand") or "sindicompanybr").strip().lower()
        _BRAND = re.sub(r"[^a-z0-9-]", "", b) or "sindicompanybr"
        print(f"[carrossel] brand={_BRAND}", flush=True)

        # Identidade data-driven (tabela marcas): paleta + prefixo de bucket
        # + handle. Para as 3 marcas chumbadas prefixo/handle continuam vindo
        # das funcoes hardcoded; estes valores so sao usados por marca nova.
        _marca = _fetch_marca(_BRAND)
        _BRAND_PALETTE = _paleta_from_marca(_marca)
        _BRAND_PREFIX = (_marca or {}).get("bucket_prefix") or ""
        _BRAND_HANDLE = (_marca or {}).get("handle") or ""
        _BRAND_NAME = (_marca or {}).get("nome") or ""
        if _BRAND_PALETTE:
            print(
                f"[carrossel] paleta do DB ({len(_BRAND_PALETTE)} cores)",
                flush=True,
            )

        # Arquetipos de capa (Brand Hub) usam as constantes _SC_* (cores
        # Sindicompany) chumbadas em ~283 lugares. Pra MARCA NOVA, remapeia
        # essas constantes pra paleta da marca de uma vez — todos os
        # arquetipos passam a seguir as cores da marca. Sindicompany/By
        # mantem as cores originais (zero regressao); Consvicta nao usa
        # arquetipos.
        if _BRAND not in ("sindicompanybr", "bysindicompany"):
            _pal = _palette()
            _SC_NAVY = _pal["onix"]
            _SC_CYAN = _pal["mint"]
            _SC_BEIGE = _pal["sand"]
            _SC_LAVENDER = _pal["lavender"]
            _SC_PURPLE = _pal.get("purple") or _pal["mint"]
            _SC_PAPER = _pal["gray_5"]
            _SC_PAPER_WARM = _pal["gray_5"]

        # Tipografia data-driven só pra marca nova; as 3 chumbadas seguem
        # com as fontes embutidas. Query separada (vide _fetch_marca_tipografia).
        _BRAND_TIPOGRAFIA = None
        if _BRAND not in ("sindicompanybr", "bysindicompany", "consvictabr"):
            _BRAND_TIPOGRAFIA = _fetch_marca_tipografia(_BRAND)
            if _BRAND_TIPOGRAFIA:
                _faces = _BRAND_TIPOGRAFIA.get("faces") or []
                print(
                    f"[carrossel] tipografia do DB ({len(_faces)} faces)",
                    flush=True,
                )

        # Brand Hub 2026-05-17: prefere o arquetipo escolhido pela
        # editora no /carrossel/novo (coluna cover_archetype). Cai pra
        # env var SINDICOMPANY_COVER_ARCHETYPE como fallback (uso legado
        # via GitHub Variables). Sem nada setado, _slide_html mantem a
        # capa classica.
        ca_db = (carrossel.get("cover_archetype") or "").strip().lower()
        ca_env = os.environ.get("SINDICOMPANY_COVER_ARCHETYPE", "").strip().lower()
        _COVER_ARCHETYPE = ca_db or ca_env
        if _COVER_ARCHETYPE:
            print(
                f"[carrossel] cover_archetype={_COVER_ARCHETYPE}"
                f" (source={'db' if ca_db else 'env'})",
                flush=True,
            )

        # Paginacao: estilo escolhido por carrossel (deterministico pelo id)
        # pra variar entre carrosseis sem mudar dentro do mesmo.
        _PAGINATION_STYLE = brand_kit.pick_pagination_style(carrossel_id)
        # Estilo de capa (classic/house) tambem varia por carrossel.
        _CAPA_STYLE = brand_kit.pick_capa_style(carrossel_id)
        _CARROSSEL_SEED = str(carrossel_id)
        _PATTERN_COLOR = brand_kit.pick_pattern_color(carrossel_id)
        print(
            f"[carrossel] pagination={_PAGINATION_STYLE} capa={_CAPA_STYLE} "
            f"pattern={_PATTERN_COLOR}",
            flush=True,
        )

        _update_carrossel(carrossel_id, {"status": "em_producao", "erro_mensagem": None})

        # 1. Copy: prefere a copy escolhida pela editora no wizard.
        #    Cai no _gerar_copy só pra registros legacy sem copy_options.
        copy_options = carrossel.get("copy_options") or []
        copy_selected = carrossel.get("copy_selected")
        chosen = None
        if isinstance(copy_options, list) and copy_options:
            idx = copy_selected if isinstance(copy_selected, int) else 0
            if 0 <= idx < len(copy_options):
                chosen = copy_options[idx]
        if chosen and isinstance(chosen, dict) and chosen.get("slides"):
            slides = list(chosen.get("slides") or [])
            legenda = chosen.get("legenda") or ""
            print(
                f"[carrossel] usando copy salva (idx={copy_selected}): {len(slides)} slides",
                flush=True,
            )
        else:
            copy = _gerar_copy(carrossel)
            slides = copy["slides"]
            legenda = copy.get("legenda") or ""
            print(f"[carrossel] copy gerado pelo engine: {len(slides)} slides", flush=True)

        # Remove slides TOTALMENTE vazios (o normalizador preenche com
        # {tipo:texto, titulo:'', body:''} quando o modelo devolve menos
        # slides que o pedido). Sem isso, o ultimo slide sai em branco e o
        # CTA "some". Apos o filtro, o ultimo slide real volta a ser o CTA.
        slides = [
            s
            for s in slides
            if isinstance(s, dict)
            and ((str(s.get("titulo") or "").strip()) or (str(s.get("body") or "").strip()))
        ]
        print(f"[carrossel] {len(slides)} slides com conteudo (vazios removidos)", flush=True)

        # 1b. Humanizer + revisão pt-BR — todas as marcas.
        # Roda DEPOIS da copy selecionada e ANTES do render dos slides.
        # Aplica accent-dict (sempre) + 1 batch GPT com SYSTEM_HUMANIZER
        # (se OPENAI_API_KEY disponivel). Regras por marca:
        # handle/assinatura/anti-leak/tom — vide _BRAND_HUMANIZER_RULES.
        slides, legenda = _humanizer_pass(slides, legenda, _BRAND)

        # 1c. Rede de seguranca FINAL do destaque visual: garante [[ ]] em
        # todo slide que ficou sem (deterministico, sem LLM). Ultima etapa
        # de texto antes do render — o destaque NUNCA mais falta.
        slides = _ensure_hooks(slides)
        # Garante CTA no ultimo slide (deterministico) — o modelo as vezes
        # termina so com frase memoravel; aqui o CTA nunca mais some.
        slides = _ensure_cta(slides, str(carrossel.get("objetivo") or ""))
        print(
            f"[carrossel] ensure-hooks: "
            f"{sum(1 for s in slides if '[[' in (s.get('titulo') or '') or '[[' in (s.get('body') or ''))}"
            f"/{len(slides)} slides com destaque",
            flush=True,
        )

        # 2. Render + upload de cada slide
        n_total = len(slides)
        png_urls: list[str] = []
        png_bytes_list: list[bytes] = []
        foto_capa = (carrossel.get("foto_capa_url") or "").strip()
        slide_fotos = carrossel.get("slide_fotos") or []

        for i, s in enumerate(slides, start=1):
            # slide_fotos eh indexado 0-based: posicao 0 = slide 1 (capa),
            # posicao 1 = slide 2, posicao 2 = slide 3, etc. Capa usa
            # foto_capa_url separadamente, entao aqui so importa pros
            # internos + CTA.
            foto_slide = ""
            if 0 <= (i - 1) < len(slide_fotos):
                foto_slide = (slide_fotos[i - 1] or "").strip() if slide_fotos[i - 1] else ""

            html = _slide_html(
                slide_idx=i,
                total=n_total,
                tipo=str(s.get("tipo") or "texto"),
                titulo=str(s.get("titulo") or ""),
                body=str(s.get("body") or ""),
                formato=str(carrossel.get("formato") or ""),
                foto_capa_url=foto_capa,
                foto_slide_url=foto_slide,
                is_capa=(i == 1),
            )
            print(f"[carrossel] renderizando slide {i}/{n_total}…", flush=True)
            png = _render_slide_png(html)
            url = _upload_png(carrossel_id, i, png)
            png_urls.append(url)
            png_bytes_list.append(png)
            print(f"[carrossel] slide {i} salvo: {url[:80]}", flush=True)

        # 2b. Empacota todos os PNGs num ZIP pra download de uma vez
        zip_url = ""
        try:
            zip_url = _upload_slides_zip(carrossel_id, png_bytes_list)
            print(f"[carrossel] zip salvo: {zip_url[:80]}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[carrossel] falha ao subir zip (segue sem): {e}", flush=True)

        # 3. Atualiza registro. zip_url eh coluna nova (migration
        # 20260524) — se ainda nao foi rodada no Supabase a chamada
        # quebra com PGRST204. Tentamos com o campo; se cair com erro
        # de coluna ausente, fazemos retry sem ele.
        from datetime import datetime, timezone
        base_fields = {
            "png_paths": png_urls,
            "legenda": legenda,
            "status": "publicada",
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "erro_mensagem": None,
        }
        try:
            _update_carrossel(
                carrossel_id, {**base_fields, "zip_url": zip_url or None}
            )
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "zip_url" in msg or "PGRST204" in msg:
                print(
                    f"[carrossel] coluna zip_url ausente (rode migration "
                    f"20260524). Salvando sem zip_url. Detalhe: {msg[:120]}",
                    flush=True,
                )
                _update_carrossel(carrossel_id, base_fields)
            else:
                raise
        print(f"[carrossel] OK — {n_total} slides + legenda", flush=True)
        return 0

    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        print(f"[carrossel] ERROR: {e}\n{tb}", flush=True)
        try:
            _update_carrossel(carrossel_id, {
                "status": "erro",
                "erro_mensagem": str(e)[:500],
            })
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python -m api.carrossel_generate <carrossel_id>", file=sys.stderr)
        sys.exit(2)
    sys.exit(gerar_carrossel(sys.argv[1]))
