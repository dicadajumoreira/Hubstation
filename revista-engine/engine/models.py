"""
revista-engine: modelos de domínio.

Estruturas de dados imutáveis que representam o pacote de inputs depois
de lido do Drive. Desacopla a fase de leitura (que sabe sobre Drive)
da fase de renderização (que só sabe sobre essas estruturas).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# =============================================================================
# Tipos de badge inferidos por palavras-chave no nome da subpasta/foto
# =============================================================================

class BadgeKind(str, Enum):
    """Tipo de badge que a engine renderiza nas fotos de manutenção/eventos."""

    JARDIM = "JARDIM"            # mint pill com SVG de folha
    ENGENHARIA = "ENGENHARIA"    # dark "ENGENHARIA"
    OPERACIONAL = "OPERACIONAL"  # mint "OPERACIONAL"
    SEGURANCA = "SEGURANÇA"      # onix "SEGURANÇA"
    MANUTENCAO = "MANUTENÇÃO"    # default mint


# Palavras-chave (em minúsculas, sem acentos) -> badge.
# A ordem importa: a primeira que casar vence.
_BADGE_KEYWORDS: list[tuple[BadgeKind, list[str]]] = [
    (BadgeKind.JARDIM,      ["jardim", "paisagismo", "grama", "planta", "arvore"]),
    (BadgeKind.ENGENHARIA,  ["fachada", "engenharia", "vistoria", "estrutura"]),
    (BadgeKind.SEGURANCA,   ["seguranca", "camera", "portaria", "alarme", "cancela", "portao"]),
    (BadgeKind.OPERACIONAL, ["operacional", "visita", "inspecao"]),
    (BadgeKind.MANUTENCAO,  ["pintura", "reparo", "troca", "instalacao", "manutencao",
                             "substituicao", "iluminacao", "solda", "dedetizacao"]),
]


_OVERRIDE_RE = re.compile(r"\[([a-zA-ZÀ-ÿ]+)\]\s*$")


def _normalize(s: str) -> str:
    """Lower, sem acentos, sem caracteres especiais."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def infer_badge(name: str) -> BadgeKind:
    """
    Inferir o badge a partir do nome (de pasta ou de descrição).

    Override manual: se o nome terminar com `[tipo]` (ex: `... [engenharia]`),
    a tag entre colchetes ganha precedência.
    """
    # Override manual via [tipo]
    m = _OVERRIDE_RE.search(name)
    if m:
        forced = _normalize(m.group(1))
        for kind in BadgeKind:
            if _normalize(kind.value) == forced:
                return kind

    norm = _normalize(name)
    for kind, kws in _BADGE_KEYWORDS:
        if any(kw in norm for kw in kws):
            return kind

    return BadgeKind.MANUTENCAO


# =============================================================================
# Foto e grupo de fotos
# =============================================================================

@dataclass(frozen=True)
class Photo:
    """Uma foto carregada do pacote."""

    local_path: Path             # caminho no disco local após download
    drive_id: Optional[str]      # ID original no Drive (se veio de lá)
    bytes_size: int              # tamanho em bytes
    width: Optional[int] = None  # px (se conseguiu medir)
    height: Optional[int] = None # px

    @property
    def is_landscape(self) -> bool:
        if self.width and self.height:
            return self.width >= self.height
        return True  # default


@dataclass
class PhotoGroup:
    """
    Um grupo de fotos relacionadas. Pode vir de duas convenções:
    - Subpasta (Villa Park): nome da pasta = título, fotos dentro
    - Plana (Gardens): .txt com nome-descritivo agrupando fotos próximas

    A engine trata os dois jeitos como o mesmo PhotoGroup.
    """

    title: str                              # vem da subpasta ou do nome do .txt
    description: str = ""                   # corpo do .txt ou Doc, opcional
    badge: BadgeKind = BadgeKind.MANUTENCAO  # inferido do title
    photos: list[Photo] = field(default_factory=list)

    @property
    def num_photos(self) -> int:
        return len(self.photos)

    @property
    def display_size(self) -> str:
        """
        Tamanho de destaque na revista (regra do Doc 01):
        - 6+ fotos -> 'hero' (página inteira)
        - 3-5 fotos -> 'large' (card grande, 1 por página coletiva)
        - 1-2 fotos -> 'small' (até 2 cards por página coletiva)
        """
        n = self.num_photos
        if n >= 6:
            return "hero"
        if n >= 3:
            return "large"
        return "small"


# =============================================================================
# Pacote do condomínio
# =============================================================================

@dataclass
class CondominiumPackage:
    """
    Pacote completo do condomínio para uma edição.
    É o resultado final do processo de leitura — o que a engine de
    renderização consome.
    """

    # Identificação
    nome: str                       # "Gardens Living Club"
    nome_curto: str = ""            # "Gardens" (default = nome)
    edicao_numero: int = 0          # 5
    edicao_ano: int = 0             # 2026
    edicao_mes: str = ""            # "Maio"

    # Síndico(s)
    sindicos: list[dict] = field(default_factory=list)

    # Conteúdo do condomínio
    carta_texto: str = ""
    foto_capa: Optional[Photo] = None        # opcional, fallback Unsplash
    grupos_manutencao: list[PhotoGroup] = field(default_factory=list)
    grupos_eventos: list[PhotoGroup] = field(default_factory=list)

    # Nossos Números
    numeros_kpis: dict = field(default_factory=dict)
    numeros_despesas: list[dict] = field(default_factory=list)

    # Advertências
    advertencias_totais: dict = field(default_factory=dict)
    advertencias_assuntos: list[str] = field(default_factory=list)

    # Diagnóstico
    convencao_detectada: str = ""   # "flat" | "subfolders" | "mixed"
    avisos: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.erros) == 0

    @property
    def total_manutencoes(self) -> int:
        return len(self.grupos_manutencao)

    @property
    def total_fotos(self) -> int:
        return sum(g.num_photos for g in self.grupos_manutencao + self.grupos_eventos)


# =============================================================================
# Pacote editorial mensal (compartilhado)
# =============================================================================

@dataclass
class EditorialPackage:
    """Conteúdo editorial mensal compartilhado entre todos os condomínios."""

    mes: str = ""
    ano: int = 0
    numero_edicao: int = 0

    materia_capa: dict = field(default_factory=dict)
    agenda_cultural: dict = field(default_factory=dict)
    receita_mes: dict = field(default_factory=dict)
    dicas: list[dict] = field(default_factory=list)
    curiosidades: list[dict] = field(default_factory=list)
    novidades: list[dict] = field(default_factory=list)
    signos: dict[str, str] = field(default_factory=dict)

    avisos: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.erros) == 0
