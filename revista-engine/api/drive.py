"""
Integração Google Drive — baixa pastas compartilhadas pra usar
fotos nas seções da revista.

A editora cola um link público de pasta do Drive no form (ex:
"Link da pasta de fotos de manutenção"). A engine baixa a pasta
inteira pra um diretório temporário e organiza as fotos por
subpasta (cada subpasta vira um card de manutenção).

Requer que a pasta esteja com permissão "Qualquer pessoa com o
link" no Drive. Não usa OAuth nem service account.
"""

from __future__ import annotations

import re
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def extract_folder_id(url: str) -> str | None:
    """Extrai o ID da pasta de uma URL do Google Drive.

    Formatos aceitos:
      https://drive.google.com/drive/folders/<ID>
      https://drive.google.com/drive/folders/<ID>?usp=sharing
      https://drive.google.com/open?id=<ID>
    """
    if not url:
        return None
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    return None


def baixar_pastas_manutencao(drive_url: str, dest: Path) -> list[dict[str, Any]]:
    """Baixa pasta de manutenções do Drive.

    Retorna uma lista [{nome_pasta, foto_path}, ...] com 1 foto por
    subpasta. Se a subpasta tem múltiplas fotos, pega a primeira.
    """
    if not drive_url:
        return []

    folder_id = extract_folder_id(drive_url)
    if not folder_id:
        print(f"[drive] URL inválida (sem folder_id): {drive_url}", flush=True)
        return []

    dest.mkdir(parents=True, exist_ok=True)
    full_url = f"https://drive.google.com/drive/folders/{folder_id}"
    print(f"[drive] baixando pasta {folder_id}", flush=True)

    try:
        import gdown  # noqa: PLC0415
    except ImportError:
        print("[drive] gdown não instalado", flush=True)
        return []

    try:
        # download_folder respeita estrutura de subpastas
        # remaining_ok=True permite passar do limite default de 50 arquivos
        gdown.download_folder(
            url=full_url,
            output=str(dest),
            quiet=False,
            use_cookies=False,
            remaining_ok=True,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[drive] download falhou: {type(e).__name__}: {e}", flush=True)
        return []

    # Diagnóstico: lista o que veio
    todos = list(dest.rglob("*"))
    arquivos = [p for p in todos if p.is_file()]
    pastas = [p for p in todos if p.is_dir()]
    print(f"[drive] baixados {len(arquivos)} arquivos em {len(pastas)} pastas/subpastas", flush=True)
    for p in pastas[:10]:
        print(f"[drive]   pasta: {p.relative_to(dest)}", flush=True)

    # gdown cria um diretório com o nome da pasta raiz dentro de dest.
    # Procuramos o primeiro subdir e listamos seus filhos como subpastas.
    root_dirs = [p for p in dest.iterdir() if p.is_dir()]
    if not root_dirs:
        print(f"[drive] nada baixado em {dest}", flush=True)
        return []

    root = root_dirs[0]
    out: list[dict[str, Any]] = []

    # Caso 1: tem subpastas dentro de root (estrutura esperada)
    subpastas = [p for p in sorted(root.iterdir()) if p.is_dir()]
    if subpastas:
        for sub in subpastas:
            imagens = sorted(
                p for p in sub.rglob("*")
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
            if not imagens:
                print(f"[drive] subpasta '{sub.name}' sem imagens", flush=True)
                continue
            out.append(
                {
                    "nome_pasta": formatar_titulo_pt(sub.name),
                    "fotos": [_path_to_url(p) for p in imagens],
                }
            )
        print(f"[drive] {len(out)} subpastas com fotos: {[o['nome_pasta'] for o in out]}", flush=True)
        return out

    # Caso 2: só fotos diretamente na root (sem subpastas) — usa filename como título
    imagens_diretas = sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if imagens_diretas:
        for img in imagens_diretas:
            out.append(
                {
                    "nome_pasta": formatar_titulo_pt(img.stem),
                    "fotos": [_path_to_url(img)],
                }
            )
        print(f"[drive] {len(out)} fotos diretas (sem subpastas): {[o['nome_pasta'] for o in out[:5]]}...", flush=True)
        return out

    print(f"[drive] root '{root.name}' sem subpastas e sem imagens diretas", flush=True)
    return out


def _path_to_url(p: Path) -> str:
    """Converte path absoluto em file:// URL com encoding correto.
    Necessário pra paths com espaços/acentos (ex: 'Pintura da fachada/foto.jpg')
    funcionarem como background-image url() no WeasyPrint."""
    return p.absolute().as_uri()


def _renomear_recursivo_nfc(root: Path) -> None:
    """Renomeia todo arquivo/pasta dentro de root pra forma Unicode NFC.

    ZIPs criados no macOS guardam nomes em NFD (caracteres decompostos:
    'ç' = 'c' + combining cedilla). Linux mantém literal, e isso causa
    chaves de URL ruins no WeasyPrint e títulos quebrados no PDF.
    """
    import unicodedata as _u
    # Renomeia bottom-up pra evitar invalidar paths-pais antes de descer
    todos = sorted(root.rglob("*"), key=lambda p: -len(p.parts))
    for p in todos:
        nome_nfc = _u.normalize("NFC", p.name)
        if nome_nfc == p.name:
            continue
        novo = p.parent / nome_nfc
        try:
            if novo.exists():
                # Caso raríssimo: já existe um arquivo com o nome NFC.
                # Mantém o atual sem renomear pra não sobrescrever.
                continue
            p.rename(novo)
        except OSError as e:
            print(f"[zip] falha ao renomear {p.name} → NFC: {e}", flush=True)


# Mapa de palavras-chave → categoria. Procura no nome da pasta (lowercase
# sem acentos) e devolve a primeira categoria que bater.
import unicodedata


def _normalize_kw(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower()


_CATEGORIA_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Jardim",      ["jardim", "jardinagem", "paisagismo", "grama", "poda", "plantio", "horta"]),
    ("Piscina",     ["piscina"]),
    ("Elevador",    ["elevador"]),
    ("Maquinário",  ["bomba", "motor", "maquinario", "maquinas", "gerador", "compressor"]),
    ("Pintura",     ["pintura", "tinta", "fachada"]),
    ("Reforma",     ["reforma", "obra", "reparo"]),
    ("Limpeza",     ["limpeza", "lavagem", "higienizacao"]),
    ("Hidráulica",  ["hidraulic", "encanament", "vazament"]),
    ("Elétrica",    ["eletric", "iluminacao", "lampada", "fiacao"]),
    ("Segurança",   ["seguranca", "camera", "portao", "interfone", "alarme"]),
    ("Estrutura",   ["estrutura", "telhado", "muro", "calcada", "estacionamento", "garagem"]),
]


def categorizar_pasta(nome_pasta: str) -> str:
    """Devolve uma palavra-chave editorial pro card de manutenção
    (ex: 'Jardim', 'Maquinário', 'Elevador'). Default: 'Manutenção'."""
    n = _normalize_kw(nome_pasta)
    for cat, kws in _CATEGORIA_KEYWORDS:
        if any(k in n for k in kws):
            return cat
    return "Manutenção"


# Dicionário de correções pt-BR. Chave = forma sem acento (lowercase),
# valor = forma correta com acentos. Aplicado a cada palavra do título.
_PT_ACCENT_FIXES: dict[str, str] = {
    # Manutenção / engenharia
    "manutencao": "manutenção", "manutencoes": "manutenções",
    "maquinario": "maquinário", "maquinarios": "maquinários",
    "maquinas": "máquinas", "maquina": "máquina",
    "hidraulica": "hidráulica", "hidraulico": "hidráulico",
    "eletrica": "elétrica", "eletrico": "elétrico",
    "seguranca": "segurança",
    "iluminacao": "iluminação",
    "fiacao": "fiação",
    "lampada": "lâmpada", "lampadas": "lâmpadas",
    "calcada": "calçada", "calcadas": "calçadas",
    "concreto": "concreto",
    "construcao": "construção",
    "instalacao": "instalação", "instalacoes": "instalações",
    "interfone": "interfone",
    "edificio": "edifício", "edificios": "edifícios",
    "predio": "prédio", "predios": "prédios",
    "garagem": "garagem",
    "estacionamento": "estacionamento",
    "porao": "porão",
    "telhado": "telhado",
    "fachada": "fachada",
    "pisicna": "piscina",  # typo comum
    "piscina": "piscina",
    "salao": "salão", "saloes": "salões",
    "saída": "saída", "saida": "saída",
    "entrada": "entrada",
    "elevador": "elevador",
    "encanamento": "encanamento",
    "vazamento": "vazamento",
    "higienizacao": "higienização",
    "limpeza": "limpeza",
    "lavagem": "lavagem",
    # Eventos
    "junina": "junina", "juninas": "juninas",
    "natal": "Natal",
    "pascoa": "Páscoa",
    "carnaval": "carnaval",
    "aniversario": "aniversário", "aniversarios": "aniversários",
    "confraternizacao": "confraternização",
    "reuniao": "reunião", "reunioes": "reuniões",
    "assembleia": "assembleia",
    "criancas": "crianças", "crianca": "criança",
    "maes": "mães", "mae": "mãe",
    "pais": "pais", "pai": "pai",
    "musica": "música",
    "festa": "festa",
    # Áreas / espaços
    "comum": "comum", "comuns": "comuns",
    "areia": "areia",
    "area": "área", "areas": "áreas",
    "patio": "pátio",
    "ginastica": "ginástica",
    "academia": "academia",
    "playground": "playground",
    "churrasqueira": "churrasqueira",
    "salao_de_festas": "salão de festas",
    # Outros
    "deposito": "depósito",
    "porteiro": "porteiro",
    "agua": "água",
    "gas": "gás",
    "lixo": "lixo",
    "muro": "muro",
    "horta": "horta",
    "sindico": "síndico",
    "sindica": "síndica",
    "sindicos": "síndicos",
    "gestor": "gestor",
    "morador": "morador",
    "moradores": "moradores",
    "comunicado": "comunicado",
    "predial": "predial",
    "publico": "público", "publicos": "públicos",
    "publica": "pública", "publicas": "públicas",
    "mes": "mês", "meses": "meses",
    "comum": "comum",
    "geral": "geral",
    "anuncio": "anúncio",
    "calendario": "calendário",
    "ordem": "ordem",
    "servico": "serviço",
    "servicos": "serviços",
    "vistoria": "vistoria",
    "inspecao": "inspeção",
    "verificacao": "verificação",
    "manutencao_preventiva": "manutenção preventiva",
    "preventiva": "preventiva",
    "corretiva": "corretiva",
    "tecnica": "técnica",
    "tecnico": "técnico",
    "jardim": "jardim",
    "jardinagem": "jardinagem",
    "paisagismo": "paisagismo",
    "grama": "grama",
    "poda": "poda",
    "plantio": "plantio",
    "tinta": "tinta",
    "pintura": "pintura",
    "obra": "obra",
    "reforma": "reforma",
    "reparo": "reparo",
    "estrutura": "estrutura",
    "bomba": "bomba",
    "motor": "motor",
    "gerador": "gerador",
    "compressor": "compressor",
    "camera": "câmera", "cameras": "câmeras",
    "portao": "portão", "portoes": "portões",
    "alarme": "alarme",
    # Adicoes de palavras frequentes que estavam vindo sem acento
    "infiltracao": "infiltração", "infiltracoes": "infiltrações",
    "conservacao": "conservação",
    "preservacao": "preservação",
    "pavimentacao": "pavimentação",
    "drenagem": "drenagem",
    "esgoto": "esgoto",
    "aquecimento": "aquecimento",
    "ventilacao": "ventilação",
    "exaustao": "exaustão",
    "fumaca": "fumaça",
    "incendio": "incêndio", "incendios": "incêndios",
    "deteccao": "detecção",
    "extintor": "extintor", "extintores": "extintores",
    "mangueira": "mangueira", "mangueiras": "mangueiras",
    "elevadores": "elevadores",
    "energia": "energia",
    "transformador": "transformador",
    "subestacao": "subestação",
    "padrao": "padrão", "padroes": "padrões",
    "automatica": "automática", "automaticas": "automáticas",
    "automatico": "automático", "automaticos": "automáticos",
    "esquadria": "esquadria", "esquadrias": "esquadrias",
    "vidracaria": "vidraçaria",
    "ar": "ar", "ar-condicionado": "ar-condicionado", "condicionado": "condicionado",
    "vacuo": "vácuo",
    "compressao": "compressão",
    "supervisao": "supervisão",
    "manuteçao": "manutenção", "manutenao": "manutenção",
    "operacao": "operação", "operacoes": "operações",
    "informacao": "informação", "informacoes": "informações",
    "comunicacao": "comunicação", "comunicacoes": "comunicações",
    "documentacao": "documentação",
    "documentos": "documentos",
    "organizacao": "organização",
    "regulamento": "regulamento",
    "regulamentacao": "regulamentação",
    "convencao": "convenção",
    "registros": "registros",
    "ata": "ata", "atas": "atas",
    "anexo": "anexo", "anexos": "anexos",
    "fotos": "fotos", "video": "vídeo", "videos": "vídeos",
    "atendimento": "atendimento",
    "comum": "comum", "comuns": "comuns",
    "lazer": "lazer",
    "salao_gourmet": "salão gourmet",
    "brinquedoteca": "brinquedoteca",
    "espaco": "espaço", "espacos": "espaços",
    "pet": "pet",
    "patio": "pátio", "patios": "pátios",
    "circulacao": "circulação", "circulacoes": "circulações",
    "saida": "saída", "saidas": "saídas",
    "balcao": "balcão", "balcoes": "balcões",
    "vestiario": "vestiário", "vestiarios": "vestiários",
    "lavanderia": "lavanderia",
    "deposito": "depósito", "depositos": "depósitos",
    "casa-de-maquinas": "casa de máquinas",
    "limpeza-geral": "limpeza geral",
    "dedetizacao": "dedetização",
    "desratizacao": "desratização",
    "desinsetizacao": "desinsetização",
    "controle": "controle",
    "pragas": "pragas",
    "vistorias": "vistorias",
    "sao": "são", "sao-joao": "são João",
    # Eventos / datas
    "noite": "noite", "noites": "noites",
    "matine": "matinê",
    "encontro": "encontro", "encontros": "encontros",
    "treinamento": "treinamento", "treinamentos": "treinamentos",
    "reciclagem": "reciclagem",
    "campanha": "campanha", "campanhas": "campanhas",
    "doacao": "doação", "doacoes": "doações",
    "arrecadacao": "arrecadação",
    "aniversariante": "aniversariante", "aniversariantes": "aniversariantes",
    "decoracao": "decoração", "decoracoes": "decorações",
    "almoco": "almoço",
    "cafe": "café",
    "natalina": "natalina",
}

# Palavras de ligação que ficam minúsculas no meio do título (Title Case pt-BR)
_PT_LOWERCASE_WORDS = {
    "a", "o", "as", "os", "e", "ou", "de", "da", "do", "das", "dos",
    "em", "no", "na", "nos", "nas", "para", "pra", "por", "pelo",
    "pela", "pelos", "pelas", "com", "sem", "ao", "à", "aos", "às",
    "um", "uma", "uns", "umas",
}


def formatar_titulo_pt(nome: str) -> str:
    """Normaliza um nome de pasta pra título legível em português.

    - Normaliza Unicode NFC (resolve nomes do macOS que vêm com chars
      decompostos: 'Manutenc╠ºa╠âo' → 'Manutenção')
    - Troca '_' e '-' por espaço
    - Aplica correções de acento conhecidas (manutencao → manutenção)
    - Title Case com preposições/artigos minúsculos no meio
    - Primeira palavra sempre capitalizada
    - Preserva palavras já acentuadas pela editora
    """
    if not nome:
        return ""
    # Normaliza NFC: macOS guarda nomes em NFD (combining chars), o
    # ZIP preserva isso, então acentos chegam como sequências de
    # caracteres separados. NFC junta tudo num único codepoint.
    nome = unicodedata.normalize("NFC", nome)
    # Limpeza inicial
    s = nome.replace("_", " ").replace("-", " ").strip()
    # Colapsa espaços múltiplos
    s = re.sub(r"\s+", " ", s)
    if not s:
        return ""

    palavras = s.split(" ")
    out: list[str] = []
    for i, palavra in enumerate(palavras):
        if not palavra:
            continue
        # Se a palavra já tem acento, mantém só normalizando case
        sem_acento = _normalize_kw(palavra)
        # Se a palavra original já tem acentos, só ajusta capitalização
        tem_acento_original = any(
            unicodedata.category(c).startswith("M") or c in "áàâãéêíóôõúüç"
            for c in unicodedata.normalize("NFD", palavra.lower())
        )
        if tem_acento_original:
            base = palavra.lower()
        else:
            base = _PT_ACCENT_FIXES.get(sem_acento, palavra.lower())

        # Decide capitalização
        if i > 0 and sem_acento in _PT_LOWERCASE_WORDS:
            out.append(base.lower())
        else:
            # Capitaliza primeira letra, preserva o resto
            out.append(base[:1].upper() + base[1:])
    return " ".join(out)


def _coletar_pastas(root: Path) -> list[dict[str, Any]]:
    """Dado um diretório com (sub)pastas + fotos, devolve a lista no
    formato que a S3 (Nosso Condomínio) espera. Mesma lógica usada
    pra Drive: subpastas → cards; sem subpastas → cada foto vira card.
    Nomes das pastas são normalizados para português correto."""
    out: list[dict[str, Any]] = []
    subpastas = [p for p in sorted(root.iterdir()) if p.is_dir()]
    if subpastas:
        for sub in subpastas:
            imagens = sorted(
                p for p in sub.rglob("*")
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
            if not imagens:
                print(f"[zip] subpasta '{sub.name}' sem imagens", flush=True)
                continue
            out.append(
                {
                    "nome_pasta": formatar_titulo_pt(sub.name),
                    "fotos": [_path_to_url(p) for p in imagens],
                }
            )
        return out

    imagens_diretas = sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    for img in imagens_diretas:
        out.append(
            {"nome_pasta": formatar_titulo_pt(img.stem), "fotos": [_path_to_url(img)]}
        )
    return out


def baixar_pastas_manutencao_zip(zip_url: str, dest: Path) -> list[dict[str, Any]]:
    """Baixa um ZIP via HTTP, descompacta e devolve a mesma estrutura
    de baixar_pastas_manutencao(). Cada subpasta dentro do ZIP vira um
    card de manutenção, usando o nome da pasta como título."""
    if not zip_url:
        return []

    dest.mkdir(parents=True, exist_ok=True)
    zip_path = dest / "manutencao.zip"

    try:
        req = urllib.request.Request(zip_url, headers={"User-Agent": "revista-engine/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            zip_path.write_bytes(resp.read())
        print(f"[zip] baixado {zip_path.stat().st_size} bytes de {zip_url[:80]}...", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[zip] download falhou: {type(e).__name__}: {e}", flush=True)
        return []

    extract_dir = dest / "extracted"
    extract_dir.mkdir(exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            # ZIPs criados no Windows costumam NAO setar o flag UTF-8 (bit 11 do
            # general purpose). Nesse caso o Python decodifica os nomes como
            # cp437, o que estraga acentos ('Manutenção' vira 'ManutenþÒo').
            # Corrigimos re-codificando cp437 -> utf-8 antes de extrair, e
            # tambem reconstruimos o dicionario NameToInfo (Python usa ele
            # pra resolver members; se nao atualizar, o extractall falha
            # silenciosamente em members renomeados).
            for info in zf.infolist():
                if not (info.flag_bits & 0x800):
                    novo = info.filename
                    try:
                        novo = info.filename.encode("cp437").decode("utf-8")
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        try:
                            novo = info.filename.encode("cp437").decode("latin-1")
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            novo = info.filename
                    info.filename = novo
            # Reconstroi o NameToInfo apos mutar os filenames.
            zf.NameToInfo = {info.filename: info for info in zf.infolist()}

            # Filtra entries: ignora arquivos de macOS (__MACOSX, .DS_Store).
            # Passamos os PROPRIOS ZipInfo (nao strings) pra evitar lookup
            # por nome — mais robusto depois das mutacoes acima.
            members = [
                info for info in zf.infolist()
                if not info.filename.startswith("__MACOSX/")
                and not info.filename.endswith("/.DS_Store")
                and not info.filename.endswith("/Thumbs.db")
            ]
            zf.extractall(extract_dir, members=members)
        print(f"[zip] extraídos {len(members)} membros em {extract_dir}", flush=True)
    except zipfile.BadZipFile as e:
        print(f"[zip] arquivo não é um ZIP válido: {e}", flush=True)
        return []
    except Exception as e:  # noqa: BLE001
        print(f"[zip] extração falhou: {type(e).__name__}: {e}", flush=True)
        return []

    # macOS guarda nomes de arquivo em Unicode NFD (chars decompostos).
    # Quando o ZIP é criado no Mac, os nomes vêm assim: 'Manutenção'
    # vira 'Manutenção' (c + cedilha combinante + tilde combinante).
    # Linux preserva NFD literalmente, e isso quebra (a) os títulos no
    # PDF e (b) URLs de file:// quando WeasyPrint tenta abrir.
    # Solução: renomear tudo pra NFC após extract.
    _renomear_recursivo_nfc(extract_dir)

    # Se o ZIP encapsulou tudo numa pasta-mãe (caso típico do macOS),
    # desce um nível.
    entries = [p for p in extract_dir.iterdir() if not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        root = entries[0]
    else:
        root = extract_dir

    pastas = _coletar_pastas(root)
    print(f"[zip] {len(pastas)} card(s): {[p['nome_pasta'] for p in pastas[:8]]}", flush=True)
    return pastas


def baixar_capa_manutencao_zip(zip_url: str, dest: Path) -> str | None:
    """Foto de capa do caderno 'Nosso Condomínio'. Prioridade:
    1. Imagem na raiz do ZIP nomeada 'capa.*' (escolha intencional)
    2. Qualquer imagem na raiz do ZIP
    3. Foto do MEIO da subpasta com MAIS fotos — evita repetir a
       primeira foto de cada subpasta, que já aparecem como
       thumbnail dentro dos cards de manutenção
    """
    extract_dir = dest / "extracted"
    if not extract_dir.exists():
        return None
    entries = [p for p in extract_dir.iterdir() if not p.name.startswith(".")]
    root = entries[0] if (len(entries) == 1 and entries[0].is_dir()) else extract_dir

    # 1. Tenta imagem na raiz nomeada 'capa.*'
    for p in sorted(root.iterdir()):
        if (p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
                and p.stem.lower() == "capa"):
            return _path_to_url(p)

    # 2. Qualquer imagem na raiz
    imgs_root = sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if imgs_root:
        return _path_to_url(imgs_root[0])

    # 3. Foto do meio da subpasta com mais fotos. As primeiras de cada
    #    subpasta já aparecem como thumbnails dos cards, então pegar do
    #    meio evita repetição visual.
    melhor_sub = None
    melhor_imgs: list[Path] = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        imgs_sub = sorted(
            p for p in sub.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if len(imgs_sub) > len(melhor_imgs):
            melhor_sub = sub
            melhor_imgs = imgs_sub
    if melhor_imgs:
        idx = len(melhor_imgs) // 2  # foto do meio
        return _path_to_url(melhor_imgs[idx])
    return None


def baixar_capa_manutencao(drive_url: str, dest: Path) -> str | None:
    """Pega a primeira imagem da raiz da pasta (foto de capa do caderno).

    Útil pra abertura da seção 'Nosso Condomínio'. Se não houver
    imagem na raiz, retorna None.
    """
    folder_id = extract_folder_id(drive_url)
    if not folder_id:
        return None

    # Reaproveita o download já feito por baixar_pastas_manutencao se dest
    # já existe e tem conteúdo. Senão, baixa só a raiz.
    if dest.exists() and any(dest.iterdir()):
        root_dirs = [p for p in dest.iterdir() if p.is_dir()]
        if root_dirs:
            root = root_dirs[0]
            imgs = sorted(
                p for p in root.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
            if imgs:
                return _path_to_url(imgs[0])
    return None
