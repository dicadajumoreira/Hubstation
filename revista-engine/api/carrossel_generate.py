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
import urllib.request
from typing import Any

from api.supabase_client import _client as _sb_client
from api.text_gen import _client as _openai_client, MODEL, _gerar_json


# Marca do carrossel atual — setada em main() antes de qualquer
# lookup de asset. Define qual conjunto de buckets/handle/logo usar.
_BRAND = "sindicompanybr"


def _asset_prefix() -> str:
    """Prefixo dos buckets de assets conforme a marca:
    - sindicompanybr -> '__'           (ex: __patterns/, __icons/)
    - bysindicompany -> '__by-'        (ex: __by-patterns/, __by-icons/)
    - consvictabr    -> '__consvicta-' (ex: __consvicta-patterns/, ...)"""
    if _BRAND == "bysindicompany":
        return "__by-"
    if _BRAND == "consvictabr":
        return "__consvicta-"
    return "__"


def _handle() -> str:
    if _BRAND == "bysindicompany":
        return "@bysindicompany"
    if _BRAND == "consvictabr":
        return "@consvictabr"
    return "@sindicompanybr"


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
        for ext in ("png", "jpg", "jpeg", "webp"):
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


def _pattern_for_slide(slide_idx: int) -> str:
    """Devolve uma data URL ciclando entre patterns aleatorizados pelo
    indice do slide, ou string vazia se nenhum pattern existir.

    Whitelist por slide: certos slides so podem usar patterns
    especificos (curadoria da marca). Pra esses, sorteia um do
    whitelist. Pra os demais, usa o shuffle global."""
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
    for ext in ("png", "jpg", "jpeg", "webp"):
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


def _icon_for_slide(slide_idx: int) -> str:
    """Mapeia: slot 1 -> slide 2, slot 2 -> slide 3, etc.
    Capa (slide_idx 1) NAO recebe Fundo Carrossel — retorna vazio."""
    icons = _icons_all_data_urls()
    if not icons or slide_idx < 2:
        return ""
    return icons[(slide_idx - 2) % len(icons)]

BUCKET = "condominios-fotos"
SLIDE_W = 3072
SLIDE_H = 3839  # 4:5 vertical

PALETTE = {
    "onix": "#1A1C29",
    "mint": "#84C7D3",
    "sand": "#DABDA9",
    "lavender": "#B8C0FF",
    "white": "#FFFFFF",
    "gray_5": "#F4F4F5",
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
    """Paleta ativa conforme a marca."""
    return PALETTE_CONSVICTA if _BRAND == "consvictabr" else PALETTE


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
        "FORMATO: HISTORIA REAL (o que mais engaja e salva).\n"
        "- De NOME ao personagem (Renata, Lucas, Carlos), nunca 'um morador'.\n"
        "- Detalhes concretos: '6 kg', '4 horas', '23%', 'Ap. 8B'.\n"
        "- A historia tem virada: setup -> conflito -> descoberta -> resolucao.\n"
        "- Personagens/situacoes podem ser compostos. NUNCA invente condominios/enderecos reais.\n"
        "ESTRUTURA: 1(capa) hook no momento de tensao maxima, sem resolver. "
        "2 quem e o personagem e o problema. 3 o erro que quase aconteceu. "
        "4 a virada. 5 o resultado concreto com numero. "
        "ultimo CTA 'Voce ja passou por isso? Comenta SIM ou NAO'."
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
        "FORMATO: MITO VS VERDADE (crencas erradas difundidas).\n"
        "- Sempre em PARES: Mito num slide, Verdade no seguinte.\n"
        "- O mito precisa SOAR RAZOAVEL. A verdade precisa ser ESPECIFICA (cite artigo/REsp).\n"
        "- MAXIMO 3 pares.\n"
        "ESTRUTURA: 1(capa) 'Voce acredita em algum desses mitos sobre condominio?'. "
        "2,3 Mito1->Verdade1. 4,5 Mito2->Verdade2. tipo dos slides: 'mito' / 'verdade'. "
        "ultimo CTA 'Qual mito voce acreditava? Comenta aqui'."
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
        "comentarios": "OBJETIVO: GERAR COMENTARIOS. CTA SEMPRE binario (SIM/NAO, "
        "CONCORDO/DISCORDO, MORADOR CERTO/SINDICO CERTO). Tema com dois lados "
        "defensaveis. Ultimo slide nomeia os dois lados. Sucesso = debate, nao alcance.",
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
        f"- Capa: o tema '{tema}' aparece literal ou em parafrase clara. Capa inteira (titulo + body) tem no max 20 palavras.\n"
        f"- Cada slide interno: tipo + titulo (3-7 palavras) + body (1-3 frases curtas, max 35 palavras).\n"
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
}


def _formato_label(formato: str) -> str:
    """Devolve o rotulo amigavel do formato (ja em titulo). Se for um
    valor desconhecido, faz best-effort trocando _ por espaco."""
    f = (formato or "").strip().lower()
    return FORMATO_LABELS.get(f, f.replace("_", " ").title() or "Carrossel")


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
    epilogue_url = (
        "https://fonts.googleapis.com/css2?family=Epilogue:wght@400;600;800;900&display=swap"
    )
    # Consvicta usa tipografia propria (Cormorant Garamond + Outfit +
    # Bebas Neue), embutida via base64 — sem dependencia de Google
    # Fonts no render. Demais marcas seguem com Epilogue (Google Fonts).
    if is_consvicta:
        head_fonts = f"<style>{_consvicta_fonts_css()}</style>"
        font_display = "'Cormorant Garamond', Georgia, serif"
        font_body = "'Outfit', system-ui, sans-serif"
        font_numeric = "'Bebas Neue', Impact, sans-serif"
    else:
        head_fonts = f'<link href="{epilogue_url}" rel="stylesheet">'
        font_display = "'Epilogue', sans-serif"
        font_body = "'Epilogue', sans-serif"
        font_numeric = "'Epilogue', sans-serif"
    # Logo 5 sempre no topo de TODOS os slides (capa + internos + CTA)
    # Logo no topo de TODOS os slides. @sindicompanybr usa o slot 5;
    # @bysindicompany usa o slot 1 (LOGO 1 do bucket __by-logos).
    # @bysindicompany usa LOGO 1 do bucket __by-logos no topo;
    # @consvictabr usa LOGO 1 do bucket __consvicta-logos; @sindicompanybr
    # usa o slot 5 do bucket __logos (logo principal Sindicompany).
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
        # Slide 1: foto na metade de cima + texto sobre overlay escuro embaixo
        bg = (
            f'<div class="hero-img" style="background-image: url(\'{foto_capa_url}\')"></div>'
            if foto_capa_url
            else f'<div class="hero-img" style="background: linear-gradient(135deg, {p["mint"]} 0%, {p["onix"]} 100%);"></div>'
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
        else:
            icon_url = _icon_slot_data_url(2)
        icon_img = (
            f'<img class="brand-icon" src="{icon_url}" alt="" />' if icon_url else ""
        )
        # Watermark do logo Consvicta atras de tudo (slot 2 do
        # bucket __consvicta-logos — slot 1 ja eh o logo do topo).
        # Se nao houver logo no slot 2, fica sem watermark.
        watermark_url = _logo_slot_data_url(2) if is_consvicta else ""
        watermark_div = (
            f'<div class="logo-watermark"></div>' if watermark_url else ""
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
    /* Barra fina mint sob o badge — assinatura editorial. */
    width: 180px; height: 6px;
    background: {p["mint"]};
    margin-bottom: 50px;
    border-radius: 3px;
  }}
  .capa-titulo {{
    font-family: {font_display};
    font-weight: {500 if is_consvicta else 900};
    font-size: {300 if is_consvicta else 257}px;
    line-height: {1.0 if is_consvicta else 0.95};
    letter-spacing: -0.015em;
    color: {p["white"]};
    text-wrap: balance;
    font-style: {('italic' if is_consvicta else 'normal')};
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
  {watermark_div}
  <div class="overlay"></div>
  <div class="content">
    <span class="badge">{_h(_formato_label(formato))}</span>
    <div class="accent-line"></div>
    <h1 class="capa-titulo">{_h_with_data(titulo, is_consvicta)}</h1>
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
    if is_cta:
        bg_color = p["onix"]
        fg_color = p["white"]
        accent = p["mint"]
        accent_text = p["onix"]
    else:
        pares = [p["mint"], p["sand"]]
        impares = [p["lavender"], p["white"], p["gray_5"]]
        if slide_idx % 2 == 0:
            bg_color = pares[(slide_idx // 2 - 1) % len(pares)]
        else:
            bg_color = impares[((slide_idx - 1) // 2 - 1) % len(impares)]

        fg_color = p["onix"]
        # Accent: nas cores muito claras (white / gray_5) usa mint pra
        # destacar; nas medias (mint / sand / lavender) usa onix solido.
        if bg_color in (p["white"], p["gray_5"]):
            accent = p["mint"]
            accent_text = p["onix"]
        else:
            accent = p["onix"]
            accent_text = p["white"]

    if is_cta:
        if _BRAND == "consvictabr":
            badge_label = "Consvicta"
        elif _BRAND == "bysindicompany":
            badge_label = "By Sindicompany"
        else:
            badge_label = "Sindicompany"
    else:
        badge_label = f"{slide_idx} / {total}"

    body_html = (
        f'<p class="slide-body">{_h_with_data(body, is_consvicta)}</p>'
        if body
        else ""
    )

    # Pattern de fundo:
    # - Slides internos: pattern ciclando, tile 800x800, 10% opacity
    # - CTA (ultimo): Pattern 1 fixo, mesma regra (tile 800x800, 10%)
    if is_cta:
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

    # Fundo Carrossel: usado como icon-bg grande nos slides internos.
    # CTA NAO recebe — fica so com onix + pattern.
    icon_url_internal = "" if is_cta else _icon_for_slide(slide_idx)
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
    watermark_url_internal = _logo_slot_data_url(2) if is_consvicta else ""
    watermark_div_internal = (
        f'<div class="logo-watermark"></div>' if watermark_url_internal else ""
    )
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
    background: {bg_color};
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
    /* Pattern da marca em 10% como textura de fundo nos slides internos.
       Uma unica instancia que cobre todo o slide (cover preserva aspect
       ratio do arquivo, recortando bordas se preciso). Sem repeat, sem
       distorcao. */
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image: url('{pattern_url}');
    background-repeat: no-repeat;
    background-position: center center;
    background-size: cover;
    opacity: 0.10;
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
    /* Barra fina abaixo do badge — assinatura editorial. */
    width: 180px; height: 6px;
    background: {accent};
    margin-bottom: 50px;
    border-radius: 3px;
  }}
  .slide-titulo {{
    font-family: {font_display};
    font-weight: {500 if is_consvicta else 800};
    font-size: {(titulo_font + 30) if is_consvicta else titulo_font}px;
    line-height: {1.02 if is_consvicta else 0.95};
    letter-spacing: -0.015em;
    color: {fg_color};
    margin-bottom: 56px;
    text-wrap: balance;
    max-width: 18ch;
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
  {pattern_div}
  {('<div class="ambient-grid"></div><div class="ambient-orb ambient-orb-gold"></div><div class="ambient-orb ambient-orb-tiff"></div>') if is_consvicta else ''}
  {watermark_div_internal}
  {slide_foto_div}
  {icon_bg_div}
  <div class="frame-corner"></div>
  <div class="bignum">{slide_idx:02d}</div>
  <div class="content">
    <span class="badge">{_h(badge_label)}</span>
    <div class="accent-line"></div>
    <h2 class="slide-titulo">{_h_with_data(titulo, is_consvicta)}</h2>
    {body_html}
  </div>
  {logo_top_img}
  <div class="handle">{handle}</div>
  {icon_img_internal}
</body></html>
"""


def _h(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
            page.set_content(html, wait_until="networkidle")
            # Aguarda TODAS as fontes (incluindo as inline base64) ficarem
            # prontas pro layout. document.fonts.ready resolve quando o
            # FontFaceSet termina de carregar todas as font-face
            # declaracoes. Sem esse await, o screenshot pode capturar
            # o frame ANTES das fontes da marca serem aplicadas.
            try:
                page.wait_for_function(
                    "document.fonts && document.fonts.status === 'loaded'",
                    timeout=15000,
                )
            except Exception:  # noqa: BLE001
                # Se o assert falhar (caso raro de bug do navegador),
                # segue com o screenshot — melhor render parcial do
                # que falha total.
                pass
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

    rules = _BRAND_HUMANIZER_RULES.get(brand, _BRAND_HUMANIZER_RULES["sindicompanybr"])

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
        "- Preserve 'tipo' e 'i' exatamente.\n\n"
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
            if isinstance(titulo, str) and titulo.strip():
                s["titulo"] = _apply_accent_dict(titulo)
            if isinstance(body, str):
                s["body"] = _apply_accent_dict(body)

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


def gerar_carrossel(carrossel_id: str) -> int:
    """Pipeline completo. Retorna 0 se OK, 1 se falhou."""
    global _BRAND
    print(f"[carrossel] iniciando geração de {carrossel_id}", flush=True)
    try:
        carrossel = _fetch_carrossel(carrossel_id)
        if not carrossel:
            print(f"[carrossel] {carrossel_id} não encontrado", flush=True)
            return 1

        # Define a marca ANTES de qualquer lookup de asset (buckets,
        # handle, logo). Default sindicompanybr pra registros legacy.
        b = (carrossel.get("brand") or "sindicompanybr").strip().lower()
        if b == "bysindicompany":
            _BRAND = "bysindicompany"
        elif b == "consvictabr":
            _BRAND = "consvictabr"
        else:
            _BRAND = "sindicompanybr"
        print(f"[carrossel] brand={_BRAND}", flush=True)

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

        # 1b. Humanizer + revisão pt-BR — todas as marcas.
        # Roda DEPOIS da copy selecionada e ANTES do render dos slides.
        # Aplica accent-dict (sempre) + 1 batch GPT com SYSTEM_HUMANIZER
        # (se OPENAI_API_KEY disponivel). Regras por marca:
        # handle/assinatura/anti-leak/tom — vide _BRAND_HUMANIZER_RULES.
        slides, legenda = _humanizer_pass(slides, legenda, _BRAND)

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
