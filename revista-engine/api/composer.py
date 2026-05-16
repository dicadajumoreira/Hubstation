"""
Composer — converte os registros do Supabase (revista, editorial mensal,
condomínio_meta) nos `inputs` esperados por cada seção da engine.

Onde o site ainda não coleta dados, caímos nos DEFAULT_INPUTS dos
scripts de preview pra ter algo razoável (placeholder + tema mensal
fixo). À medida que mais dados vêm do site, esses fallbacks somem.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


_BY_LOGO_CACHE: dict[int, str] = {}


def _by_logo_url(slot: int) -> str:
    """URL publica do logo do By Sindicompany no slot dado
    (__by-logos/logo-{slot}.X). Testa extensoes comuns via HEAD.
    String vazia se nao houver. Cache por slot."""
    if slot in _BY_LOGO_CACHE:
        return _BY_LOGO_CACHE[slot]
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        _BY_LOGO_CACHE[slot] = ""
        return ""
    for ext in ("png", "svg", "webp", "jpg", "jpeg"):
        url = (
            f"{base}/storage/v1/object/public/"
            f"condominios-fotos/__by-logos/logo-{slot}.{ext}"
        )
        try:
            req = urllib.request.Request(
                url, method="HEAD", headers={"User-Agent": "revista-engine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    _BY_LOGO_CACHE[slot] = url
                    return url
        except Exception:  # noqa: BLE001
            continue
    _BY_LOGO_CACHE[slot] = ""
    return ""


def _logo_para_revista(revista: dict[str, Any], cd: dict[str, Any], fundo_escuro: bool) -> str:
    """Decide qual logo usar nesta secao da revista.
    - Sindico By Sindicompany: usa o logo do By — LOGO 1 em fundo
      escuro, LOGO 2 em fundo branco.
    - Caso contrario: usa o logo do sindico cadastrado (cd['logo_url']),
      ou '' (engine cai no logo Sindicompany padrao)."""
    if revista.get("is_by_sindico"):
        by = _by_logo_url(1 if fundo_escuro else 2)
        if by:
            return by
    return (cd.get("logo_url") or "") if isinstance(cd, dict) else ""

# Garante import do package engine + dos scripts de preview (defaults)
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.drive import (
    baixar_capa_manutencao,
    baixar_capa_manutencao_zip,
    baixar_pastas_manutencao,
    baixar_pastas_manutencao_zip,
    categorizar_pasta,
)
from api.image_gen import (
    gerar_foto_agenda_hero,
    gerar_foto_lifestyle,
    gerar_foto_materia_capa,
    gerar_foto_receita,
)
from api.numeros_parser import parse_nossos_numeros_arquivo
from api.text_gen import (
    clean_text,
    gerar_agenda_cultural,
    gerar_carta_gestor,
    gerar_carta_sindico,
    gerar_curiosidades,
    gerar_dica_receita,
    gerar_dicas_praticas,
    gerar_receita_completa,
    gerar_materia_capa_completa,
    gerar_novidades,
    gerar_signos,
)
from engine.theme import load_theme
from engine.sections import (
    BackCover, Colophon, CommunityInvite, Cover, CoverStory, CulturalAgenda,
    EditorNote, Horoscope, IndustryFacts, Letter, LifestyleArticle, News,
    OurCondoEvents, OurCondoMaintenance, OurNumbers, Recipe, TeamSupport,
    Tips, Warnings,
)
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


MESES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
]


def _mes_ano(revista: dict[str, Any]) -> str:
    mes = int(revista["mes"])
    return f"{MESES[mes - 1]} {revista['ano']}"


def _edicao_label(revista: dict[str, Any]) -> str:
    mes = int(revista["mes"])
    ano = revista["ano"]
    condo = revista["condominio"].upper()
    # @sindicompanybr removido a pedido — o logo da Sindicompany já
    # aparece no canto da capa quando o condomínio não tem logo próprio.
    return f"EDIÇÃO {mes:02d} · {MESES[mes - 1]} {ano} · {condo}"


def _cargo_sindico(condo_meta: dict[str, Any] | None) -> str:
    if not condo_meta:
        return "Síndico(a)"
    g = condo_meta.get("sindico_genero")
    if g == "empresa":
        return "Sindicatura Profissional"
    return "Síndica" if g == "feminino" else "Síndico"


def _build_chamadas(revista: dict[str, Any], editorial: dict[str, Any] | None, condo: dict[str, Any] | None) -> list[str]:
    """Constrói as chamadas de 'Nesta Edição' baseado nos dados do mês."""
    ed = editorial or {}
    chamadas: list[str] = []

    # 1. Carta do(a) síndico(a) / da administradora
    _g = (condo or {}).get("sindico_genero")
    if _g == "empresa":
        carta_label = "Carta da Sindicatura Profissional"
    elif _g == "feminino":
        carta_label = "Carta da Síndica"
    else:
        carta_label = "Carta do Síndico"
    if ed.get("carta_sindico_tema"):
        chamadas.append(f"{carta_label} · {ed['carta_sindico_tema']}")
    else:
        chamadas.append(carta_label)

    # 2. Matéria de capa
    if ed.get("materia_capa_titulo"):
        chamadas.append(f"Matéria de capa · {ed['materia_capa_titulo']}")

    # 3. Receita do mês
    if ed.get("receita_titulo"):
        chamadas.append(f"Receita do mês · {ed['receita_titulo']}")

    # 4. Eventos (se a edição teve)
    if revista.get("tem_eventos"):
        chamadas.append("Nosso condomínio · Eventos do mês")

    # 5. Advertências (se houver)
    if revista.get("tem_advertencias"):
        chamadas.append("Advertências e multas")

    # Cap em 4 chamadas pra não estourar a capa
    return chamadas[:4]


def build_inputs_from_db(
    revista: dict[str, Any],
    editorial: dict[str, Any] | None,
    condo: dict[str, Any] | None,
) -> list[tuple[str, Any, dict[str, Any]]]:
    """Retorna [(label, section_instance, inputs), …] na ordem editorial."""

    ed = editorial or {}
    cd = condo or {}
    mes_ano = _mes_ano(revista)
    condominio = revista.get("condominio", "")

    # Foto pública do(a) síndico(a) — bucket condominios-fotos é público,
    # então construímos a URL completa a partir do path armazenado.
    sindico_foto_url = None
    if cd.get("sindico_foto_path"):
        url_base = os.environ.get("SUPABASE_URL", "")
        if url_base:
            sindico_foto_url = (
                f"{url_base}/storage/v1/object/public/condominios-fotos/"
                f"{cd['sindico_foto_path']}"
            )
        else:
            sindico_foto_url = cd["sindico_foto_path"]

    # ---- S01 Capa
    cover_inputs = dict(COVER_DEFAULT)
    cover_inputs["edicao_label"] = _edicao_label(revista)
    if ed.get("materia_capa_titulo"):
        cover_inputs["manchete"] = ed["materia_capa_titulo"]
        cover_inputs["tema_materia"] = ed.get("materia_capa_titulo", "")
    if ed.get("materia_capa_subtitulo"):
        cover_inputs["subtitulo"] = ed["materia_capa_subtitulo"]
    if ed.get("foto_capa_url"):
        cover_inputs["foto_capa"] = ed["foto_capa_url"]
    cover_inputs["chamadas"] = _build_chamadas(revista, editorial, condo)
    # Logo do topo da capa: sempre o logotipo do(a) sindico(a) cadastrado
    # no condominio (campo cd.logo_url), independente de o sindico ser By
    # Sindicompany ou nao.
    _logo_capa = (cd.get("logo_url") or "").strip()
    if _logo_capa:
        cover_inputs["logo_url"] = _logo_capa

    # ---- S02 Carta do Síndico
    letter_inputs = dict(LETTER_DEFAULT)
    if cd.get("sindico_nome"):
        letter_inputs["nome_sindico"] = cd["sindico_nome"]
        letter_inputs["genero"] = cd.get("sindico_genero") or "feminino"
        letter_inputs["cargo"] = _cargo_sindico(condo)
    letter_inputs["mes_ano"] = mes_ano
    if ed.get("carta_sindico_tema"):
        letter_inputs["titulo"] = ed["carta_sindico_tema"]
    if revista.get("carta_sindico_texto"):
        letter_inputs["texto"] = clean_text(revista["carta_sindico_texto"])
    else:
        letter_inputs["texto"] = gerar_carta_sindico(cd, ed, revista)
    if sindico_foto_url:
        letter_inputs["foto_sindico"] = sindico_foto_url

    # ---- S02B Carta do Gestor (só se a revista marcar tem_gestor)
    gestor_letter_inputs: dict[str, Any] | None = None
    if revista.get("tem_gestor") and revista.get("gestor_nome"):
        gestor_letter_inputs = dict(LETTER_DEFAULT)
        gestor_letter_inputs["nome_sindico"] = revista["gestor_nome"]
        # gestor_titulo vem do cadastro do condominio (genero do gestor):
        # 'Gestor de Atendimento' (M) ou 'Gestora de Atendimento' (F).
        cargo_gestor = (revista.get("gestor_titulo") or "Gestor de Atendimento").strip()
        gestor_letter_inputs["cargo"] = cargo_gestor
        gestor_letter_inputs["genero"] = (
            "feminino" if "gestora" in cargo_gestor.lower() else "masculino"
        )
        gestor_letter_inputs["mes_ano"] = mes_ano
        if ed.get("carta_gestor_tema"):
            gestor_letter_inputs["titulo"] = ed["carta_gestor_tema"]
        if revista.get("carta_gestor_texto"):
            gestor_letter_inputs["texto"] = clean_text(revista["carta_gestor_texto"])
        else:
            gestor_letter_inputs["texto"] = gerar_carta_gestor(cd, ed, revista)
        if revista.get("gestor_foto_url"):
            gestor_letter_inputs["foto_sindico"] = revista["gestor_foto_url"]

    mes_int = int(revista["mes"])
    ano_int = int(revista["ano"])

    # ---- S03 Agenda Cultural — gerada por mês via AI + foto hero via DALL-E
    agenda_ai = gerar_agenda_cultural(mes_int, ano_int)
    hero = dict(agenda_ai.get("hero", AGENDA_DEFAULT["hero"]))
    foto_hero = gerar_foto_agenda_hero(
        hero.get("titulo", ""),
        hero.get("categoria", ""),
    )
    if foto_hero:
        hero["foto"] = foto_hero
    else:
        # IA falhou em todas as tentativas. NAO usamos foto de capa do
        # editorial como fallback pra nao colocar uma imagem nao
        # relacionada ao destaque — preferimos o placeholder em gradient
        # (renderizado pela secao CulturalAgenda quando hero.foto vazio).
        print(
            "[composer] agenda hero IA falhou; hero ficara com gradiente placeholder",
            flush=True,
        )
    agenda_inputs = {
        "mes_referencia": mes_ano,
        "hero": hero,
        "cards_secundarios": agenda_ai.get("cards_secundarios", AGENDA_DEFAULT["cards_secundarios"]),
    }

    # ---- S04 Matéria de Capa — corpo gerado por AI, foto via DALL-E se faltar
    cover_story_inputs = dict(COVER_STORY_DEFAULT)
    cover_story_inputs["mes_referencia"] = mes_ano
    titulo_capa = ed.get("materia_capa_titulo") or COVER_STORY_DEFAULT["manchete"]
    subtitulo_capa = ed.get("materia_capa_subtitulo") or COVER_STORY_DEFAULT["subtitulo"]
    cover_story_inputs["manchete"] = titulo_capa
    cover_story_inputs["subtitulo"] = subtitulo_capa
    if ed.get("foto_capa_url"):
        cover_story_inputs["foto_principal"] = ed["foto_capa_url"]
    else:
        # Editora não subiu foto: gera com DALL-E e usa também na capa S01
        foto_ai = gerar_foto_materia_capa(titulo_capa, subtitulo_capa)
        if foto_ai:
            cover_story_inputs["foto_principal"] = foto_ai
            cover_inputs["foto_capa"] = foto_ai
    materia_ai = gerar_materia_capa_completa(titulo_capa, subtitulo_capa, mes_int, ano_int)
    raw_fontes = materia_ai.get("fontes") or []
    if isinstance(raw_fontes, list) and raw_fontes:
        cover_story_inputs["fontes"] = [str(f) for f in raw_fontes if f]
    raw_blocos = materia_ai.get("corpo_blocos") or []
    # Normaliza: a IA pode retornar strings simples ou dicts. A seção
    # cover_story.py exige lista de dicts com {tipo, texto, ...}.
    blocos: list[dict[str, Any]] = []
    for b in raw_blocos:
        if isinstance(b, dict) and b.get("texto"):
            blocos.append(b if b.get("tipo") else {"tipo": "paragrafo", **b})
        elif isinstance(b, str) and b.strip():
            blocos.append({"tipo": "paragrafo", "texto": b.strip()})
    if blocos:
        cover_story_inputs["corpo_blocos"] = blocos

    # ---- S05 Dicas Práticas — geradas por mês
    dicas_ai = gerar_dicas_praticas(mes_int, ano_int)
    tips_inputs = {
        "mes_referencia": mes_ano,
        "titulo_secao": dicas_ai.get("titulo_secao", TIPS_DEFAULT["titulo_secao"]),
        "intro": dicas_ai.get("intro", TIPS_DEFAULT["intro"]),
        "dicas": dicas_ai.get("dicas", TIPS_DEFAULT["dicas"]),
    }

    # S06 Curiosidades e S07 Novidades removidas a pedido — ja nao
    # entram na sequencia da revista, entao tambem nao geramos os
    # textos via IA (economiza ~10s por edicao).
    industry_inputs: dict[str, Any] = {}
    news_inputs: dict[str, Any] = {"noticias": []}

    # ---- S08 Manutenções: baixa Drive e popula manutencoes
    maint_inputs = dict(MAINT_DEFAULT)
    maint_inputs["mes_referencia"] = mes_ano
    maint_inputs["nome_condominio"] = condominio

    # Preferência: ZIP de manutenção subido pela editora. Fallback: link Drive (legado).
    zip_url = revista.get("manutencao_zip_url")
    drive_url = revista.get("drive_manutencao_url")
    if zip_url or drive_url:
        import tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix=f"manut_{revista.get('id','')[:8]}_"))
        if zip_url:
            pastas = baixar_pastas_manutencao_zip(zip_url, tmpdir)
            capa = baixar_capa_manutencao_zip(zip_url, tmpdir) if pastas else None
        else:
            pastas = baixar_pastas_manutencao(drive_url, tmpdir)
            capa = baixar_capa_manutencao(drive_url, tmpdir) if pastas else None
        if pastas:
            # Cada subpasta vira uma manutenção. Título = nome da pasta.
            # Passa TODAS as fotos — S08 escolhe layout pelo número delas.
            # tipo_badge inferido do nome (Jardim, Pintura, Maquinário, …).
            maint_inputs["manutencoes"] = [
                {
                    "titulo": p["nome_pasta"],
                    "tipo_badge": categorizar_pasta(p["nome_pasta"]),
                    "fotos": p.get("fotos") or ([p["foto_path"]] if p.get("foto_path") else []),
                    "descricao": "",
                }
                for p in pastas
            ]
            if capa:
                maint_inputs["foto_capa_caderno"] = capa

    # Capa manual (subida pela editora no form) sobrescreve a capa
    # auto-selecionada do ZIP.
    capa_manual = revista.get("manutencao_capa_url")
    if capa_manual:
        maint_inputs["foto_capa_caderno"] = capa_manual

    events_inputs = dict(EVENTS_DEFAULT)
    events_inputs["mes_referencia"] = mes_ano
    events_inputs["nome_condominio"] = condominio
    # Preferência: ZIP. Fallback: link Drive (legado).
    eventos_zip_url = revista.get("eventos_zip_url")
    drive_eventos_url = revista.get("drive_eventos_url")
    pastas_ev: list[dict] = []
    if eventos_zip_url or drive_eventos_url:
        import tempfile
        tmpdir_ev = Path(tempfile.mkdtemp(prefix=f"event_{revista.get('id','')[:8]}_"))
        if eventos_zip_url:
            pastas_ev = baixar_pastas_manutencao_zip(eventos_zip_url, tmpdir_ev)
        else:
            pastas_ev = baixar_pastas_manutencao(drive_eventos_url, tmpdir_ev)
    if pastas_ev:
        events_inputs["eventos"] = [
            {
                "titulo": p["nome_pasta"],
                "fotos": p.get("fotos") or ([p["foto_path"]] if p.get("foto_path") else []),
                "descricao": "",
            }
            for p in pastas_ev
        ]

    # ---- S10 Receita (todos os campos gerados a partir do título da
    # receita do editorial — garante que ingredientes, modo de preparo,
    # tempo de preparo e dica sejam SEMPRE coerentes com a receita
    # escolhida no mês, sem misturar com defaults antigos).
    recipe_inputs = dict(RECIPE_DEFAULT)
    recipe_inputs["mes_referencia"] = mes_ano
    titulo_receita = (ed.get("receita_titulo") or "").strip()
    descricao_receita = (ed.get("receita_descricao") or "").strip()
    if titulo_receita:
        recipe_inputs["titulo_receita"] = titulo_receita
        # Gera todos os campos da receita coerentes com o título
        receita_ai = gerar_receita_completa(titulo_receita, descricao_receita)
        if receita_ai:
            for key in ("intro", "tempo_preparo", "ingredientes",
                        "modo_preparo", "dica"):
                if receita_ai.get(key):
                    recipe_inputs[key] = receita_ai[key]
        # Editorial pode ter sobreposto a descrição manual — respeitar
        if descricao_receita:
            recipe_inputs["intro"] = descricao_receita
    # Foto da receita via DALL-E
    foto_receita_ai = gerar_foto_receita(
        recipe_inputs.get("titulo_receita", ""),
        recipe_inputs.get("intro", ""),
    )
    if foto_receita_ai:
        recipe_inputs["foto_receita"] = foto_receita_ai

    # ---- S11 Nossos Números: parse do HTML dentro da pasta de prestação
    numbers_inputs = dict(NUMBERS_DEFAULT)
    numbers_inputs["mes_referencia"] = mes_ano

    # Arquivo direto (PNG/JPG/PDF) cadastrado pela editora no form da
    # revista. Cada edição tem o seu (números mudam mês a mês).
    prestacao_arquivo = revista.get("prestacao_arquivo_url")
    if prestacao_arquivo:
        numbers_inputs["dashboard_url"] = prestacao_arquivo

    nums = None
    if prestacao_arquivo:
        import tempfile
        tmp_num = Path(tempfile.mkdtemp(prefix=f"numeros_{revista.get('id','')[:8]}_"))
        nums = parse_nossos_numeros_arquivo(prestacao_arquivo, tmp_num)

    if nums and nums.get("kpis"):
        numbers_inputs["kpis"] = nums["kpis"]
        if nums.get("principais_despesas"):
            numbers_inputs["principais_despesas"] = nums["principais_despesas"]
        if nums.get("resumo_contas"):
            numbers_inputs["resumo_contas"] = nums["resumo_contas"]
        if nums.get("previsto_realizado"):
            numbers_inputs["previsto_realizado"] = nums["previsto_realizado"]

    # ---- S12 Advertências (só renderiza se a edição teve)
    warnings_inputs = dict(WARNINGS_DEFAULT)
    warnings_inputs["mes_referencia"] = mes_ano
    if revista.get("multas_advertencias_obs"):
        warnings_inputs["observacao"] = revista["multas_advertencias_obs"]

    # ---- S12B Vida Condominial: gera foto se faltar
    life_inputs = dict(LIFE_DEFAULT)
    life_inputs["mes_referencia"] = mes_ano
    if not life_inputs.get("foto_principal"):
        foto_life = gerar_foto_lifestyle(
            life_inputs.get("titulo", ""),
            life_inputs.get("kicker", ""),
        )
        if foto_life:
            life_inputs["foto_principal"] = foto_life

    # ---- S13 Signos — gerados por mês
    signos_ai = gerar_signos(mes_int, ano_int)
    horoscope_inputs = {
        "mes_referencia": mes_ano,
        "previsoes": signos_ai.get("previsoes", HOROSCOPE_DEFAULT["previsoes"]),
    }

    # ---- S14 Expediente (com dados reais do condomínio + síndico)
    colophon_inputs = dict(COLOPHON_DEFAULT)
    colophon_inputs["mes_referencia"] = mes_ano
    colophon_inputs["nome_condominio"] = condominio
    colophon_inputs["numero_edicao"] = int(revista["mes"])
    colophon_inputs["ano_edicao"] = int(revista["ano"])
    # Expediente vira branding By Sindicompany pra todas as revistas:
    #  - logo "by sindicompany" (slot 2 dos Assets BySindicompany — versao p/
    #    fundo claro) antes do texto institucional no rodape;
    #  - editor "Equipe Editorial By Sindicompany";
    #  - titulo do bloco "Equipe Editorial By Sindicompany";
    #  - contato revista@sindicompany.com.br.
    _by_logo_rodape = _by_logo_url(2)
    if _by_logo_rodape:
        colophon_inputs["by_logo_url"] = _by_logo_rodape
    colophon_inputs["editor_responsavel"] = "Equipe Editorial By Sindicompany"
    colophon_inputs["contato"] = "revista@sindicompany.com.br"
    colophon_inputs["equipe_sc_titulo"] = "Equipe Editorial By Sindicompany"
    if cd.get("sindico_nome"):
        colophon_inputs["nome_sindico"] = cd["sindico_nome"]
        colophon_inputs["cargo_sindico"] = _cargo_sindico(condo)
    # Label dinâmico do bloco de crédito conforme gênero do(a) síndico(a)
    colophon_inputs["label_sindico"] = _cargo_sindico(condo)
    # Equipe do condomínio: lista fixa padrão. Se houver gestor
    # preenchido, ele entra como primeiro item; senão usa só os papéis
    # genéricos abaixo.
    equipe: list[str] = []
    if revista.get("tem_gestor") and revista.get("gestor_nome"):
        equipe.append(f"{revista['gestor_nome']} · Gestor de atendimento")
    equipe.extend([
        "Zeladoria | Gerência",
        "Equipe Manutenção",
        "Equipe de Limpeza",
        "Equipe de Portaria",
        "Equipe Administrativa",
    ])
    colophon_inputs["equipe_condominio"] = equipe

    # Equipe Sindicompany: lista fixa, sem 'Skill Humanizer'.
    colophon_inputs["equipe_sindicompany"] = [
        "Direção editorial",
        "Pauta e Produção",
        "Diagramação e Arte",
    ]

    # Fontes de pesquisa: agrega tudo que foi citado nesta edição
    # (matéria de capa, lifestyle, novidades, agenda cultural). Vira o
    # bloco "Fontes de Pesquisa" no expediente, em vez do "Colaboradores"
    # genérico do default.
    fontes_set: list[str] = []
    def _add_fonte(s: Any) -> None:
        s = str(s or "").strip()
        if s and s not in fontes_set:
            fontes_set.append(s)
    for f in (cover_story_inputs.get("fontes") or []):
        _add_fonte(f)
    for f in (life_inputs.get("fontes") or []):
        _add_fonte(f)
    for n in (news_inputs.get("noticias") or []):
        if isinstance(n, dict):
            _add_fonte(n.get("fonte"))
    # Agenda cultural não tem 'fontes' explícitas no schema atual,
    # mas a IA é instruída a pesquisar nesses portais — listamos como
    # base editorial recorrente quando há agenda cultural na edição.
    if agenda_inputs.get("cards_secundarios"):
        for portal in ("AdoroCinema", "Veja SP", "Catraca Livre"):
            _add_fonte(portal)

    if fontes_set:
        colophon_inputs["creditos_extras"] = [
            {"titulo": "Fontes de Pesquisa", "nomes": fontes_set}
        ]
    else:
        # Sem fontes coletadas: remove o bloco de extras pra não vazar
        # placeholders ('Colaboradores · Fotos de manutenção · …').
        colophon_inputs["creditos_extras"] = []

    # ---- S14B Convite para a comunidade do condomínio (só se houver
    # link da comunidade cadastrado no condo).
    community_invite_inputs: dict[str, Any] | None = None
    _comunidade_url = (cd.get("comunidade_url") or "").strip()
    if _comunidade_url:
        community_invite_inputs = {
            "condominio": condominio,
            "comunidade_url": _comunidade_url,
        }
        _qr_path = (cd.get("comunidade_qrcode_path") or "").strip()
        if _qr_path:
            _url_base = os.environ.get("SUPABASE_URL", "")
            community_invite_inputs["qrcode_url"] = (
                f"{_url_base}/storage/v1/object/public/condominios-fotos/{_qr_path}"
                if _url_base else _qr_path
            )

    # ---- S14C Equipe de Atendimento (so se ha comunidade cadastrada e
    # ha equipe global no banco).
    team_support_inputs: dict[str, Any] | None = None
    if _comunidade_url:
        try:
            from api.supabase_client import _client as _sb_client_eq
            sb = _sb_client_eq()
            res = sb.table("equipe_atendimento_global").select("*").order("ordem").order("created_at").execute()
            rows = list(res.data or [])
        except Exception as e:  # noqa: BLE001
            print(f"[composer] equipe_atendimento_global falhou: {type(e).__name__}: {e}", flush=True)
            rows = []
        if rows:
            _url_base = os.environ.get("SUPABASE_URL", "")
            membros = []
            for r in rows:
                foto = (r.get("foto_path") or "").strip()
                if foto and _url_base:
                    foto_url = f"{_url_base}/storage/v1/object/public/condominios-fotos/{foto}"
                else:
                    foto_url = foto or ""
                membros.append({
                    "nome": (r.get("nome") or "").strip(),
                    "cargo": (r.get("cargo") or "").strip(),
                    "foto_url": foto_url,
                })
            team_support_inputs = {
                "condominio": condominio,
                "membros": membros,
            }

    # ---- S15 Contracapa
    proximo_mes = (int(revista["mes"]) % 12) + 1
    proximo_ano = int(revista["ano"]) if int(revista["mes"]) < 12 else int(revista["ano"]) + 1
    back_cover_inputs: dict[str, Any] = {
        "proxima_edicao_label": f"Próxima edição: {MESES[proximo_mes - 1].lower()} {proximo_ano}",
    }
    # Contracapa tem fundo onix (escuro).
    #  - sindico By Sindicompany: o logotipo do sindico aparece em DESTAQUE
    #    (grande, centralizado) e o logo "by sindicompany" vai no rodape
    #    (menor, abaixo).
    #  - caso contrario: o logo do sindico (cd['logo_url']) ocupa o centro.
    if revista.get("is_by_sindico"):
        _logo_sindico = (cd.get("logo_url") or "").strip()
        if _logo_sindico:
            back_cover_inputs["logo_url"] = _logo_sindico
        # By Sindicompany logo (slot 1 = versao p/ fundo escuro).
        _by = _by_logo_url(1)
        if _by:
            back_cover_inputs["by_logo_url"] = _by
    else:
        _logo_contracapa = _logo_para_revista(revista, cd, fundo_escuro=True)
        if _logo_contracapa:
            back_cover_inputs["logo_url"] = _logo_contracapa

    sequence: list[tuple[str, Any, dict[str, Any]]] = [
        ("S01 Capa",                   Cover(),                cover_inputs),
        ("S02 Carta do Síndico",       Letter(),               letter_inputs),
    ]
    if gestor_letter_inputs is not None:
        sequence.append(("S02B Carta do Gestor", Letter(), gestor_letter_inputs))
    sequence.extend([
        ("S03 Agenda Cultural",        CulturalAgenda(),       agenda_inputs),
        ("S04 Matéria de Capa",        CoverStory(),           cover_story_inputs),
        ("S05 Dicas Práticas",         Tips(),                 tips_inputs),
        # S06 Curiosidades do Setor e S07 Novidades e Legislacao removidas a pedido.
        ("S08 Manutenções",            OurCondoMaintenance(),  maint_inputs),
    ])
    # Inclui a seção de eventos sempre que tem_eventos=true. Mesmo
    # sem fotos no ZIP, a editora marcou que houve eventos no mês —
    # então uma página de abertura é gerada.
    if revista.get("tem_eventos"):
        sequence.append(("S09 Eventos", OurCondoEvents(), events_inputs))
    sequence.append(("S10 Receita do Mês", Recipe(), recipe_inputs))
    # S11 Nossos Números só aparece se a editora subiu o dashboard
    # de prestação no form da revista. Sem dashboard, não há números
    # pra mostrar — pular a seção evita uma página com KPIs zerados.
    if revista.get("prestacao_arquivo_url"):
        sequence.append(("S11 Nossos Números", OurNumbers(), numbers_inputs))
    if revista.get("tem_advertencias"):
        sequence.append(("S12 Advertências e Multas", Warnings(), warnings_inputs))
    # Nota da edição (texto livre da editora). Aparece só se preenchido
    # no form de Nova Edição (campo notas_editor).
    notas_editor = (revista.get("notas_editor") or "").strip()
    if notas_editor:
        editor_note_inputs = {
            "texto": notas_editor,
            "mes_referencia": mes_ano,
            "nome_condominio": condominio,
        }
        sequence.append(("S12C Nota da Edição", EditorNote(), editor_note_inputs))
    sequence.extend([
        ("S12B Vida Condominial",      LifestyleArticle(),     life_inputs),
        ("S13 Signos do Mês",          Horoscope(),            horoscope_inputs),
        ("S14 Expediente",             Colophon(),             colophon_inputs),
    ])
    if community_invite_inputs is not None:
        sequence.append(("S14B Comunidade do Condomínio", CommunityInvite(), community_invite_inputs))
    if team_support_inputs is not None:
        sequence.append(("S14C Equipe de Atendimento", TeamSupport(), team_support_inputs))
    sequence.append(("S15 Contracapa", BackCover(), back_cover_inputs))
    # Pass final de revisão pt-BR: clean_text em todas as strings dos
    # inputs (corrige acentos comuns, normaliza pontuação). Pula campos
    # sensíveis (URLs, paths, fotos) pra não quebrar nomes próprios em
    # caminhos ou querystrings.
    sequence = [
        (label, section, _revisar_pt_br(inputs))
        for label, section, inputs in sequence
    ]
    return sequence


# Campos cujo conteúdo NÃO deve passar pelo clean_text (URLs, paths,
# IDs, classes CSS). Usa-se uma checagem por nome de chave.
_CAMPOS_SENSIVEIS = {
    "fotos", "foto", "foto_path", "foto_principal", "foto_capa", "foto_capa_url",
    "foto_capa_caderno", "foto_receita", "foto_sindico", "foto_gestor",
    "logo_url", "dashboard_url", "drive_manutencao_url", "drive_eventos_url",
    "drive_prestacao_url", "manutencao_zip_url", "eventos_zip_url",
    "prestacao_arquivo_url", "pdf_storage_path", "id", "slug",
}


def _revisar_pt_br(obj: Any) -> Any:
    """Aplica clean_text recursivamente em todas as strings do dict,
    pulando campos sensíveis (URLs, paths, IDs)."""
    if isinstance(obj, str):
        if obj.startswith(("http://", "https://", "file://", "/")):
            return obj
        return clean_text(obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _CAMPOS_SENSIVEIS:
                out[k] = v
            else:
                out[k] = _revisar_pt_br(v)
        return out
    if isinstance(obj, list):
        return [_revisar_pt_br(x) for x in obj]
    return obj


def render_pdf_bytes(sequence: list[tuple[str, Any, dict[str, Any]]]) -> tuple[bytes, int]:
    """Renderiza o HTML composto e converte pra PDF via WeasyPrint."""
    theme = load_theme()
    bodies: list[str] = []
    page_count = 0

    for label, section, inputs in sequence:
        errors = section.validate(inputs)
        if errors:
            print(f"  ⚠ {label}: warnings de validação: {errors}", flush=True)
        section_bodies = section.render_a4(inputs, theme)
        bodies.extend(section_bodies)
        page_count += len(section_bodies)
        print(f"  ✓ {label} · {len(section_bodies)} pág", flush=True)

    full_html = theme.page_document("\n".join(bodies), format="a4")

    # WeasyPrint só importado aqui pra deixar o composer importável
    # mesmo em ambientes sem libs de sistema (testes etc).
    from weasyprint import HTML
    from io import BytesIO

    buf = BytesIO()
    HTML(string=full_html, base_url=str(Path.cwd())).write_pdf(target=buf)
    return buf.getvalue(), page_count
