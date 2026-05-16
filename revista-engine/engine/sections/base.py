"""
Classe abstrata `Section` — contrato que cada uma das 16 seções da revista
implementa.

Cada seção sabe responder 5 perguntas (Doc 01 §8):
1. validate(inputs)        -> erros (lista vazia se válido)
2. paginate(inputs)        -> quantas páginas vai ocupar
3. required_assets(inputs) -> URLs de assets externos a baixar
4. render_a4(inputs, theme)     -> HTML por página em A4
5. render_mobile(inputs, theme) -> HTML por página em Mobile
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PageDimensions:
    """Dimensões CSS de uma página (px)."""

    width: int
    height: int

    @property
    def aspect(self) -> float:
        return self.width / self.height


# Dimensões padrão (Doc 01 §5)
A4 = PageDimensions(width=794, height=1123)        # A4 em CSS px (96 DPI ~ 210×297mm)
MOBILE = PageDimensions(width=540, height=960)      # smartphone vertical @2x = 1080×1920


class Section(ABC):
    """
    Contrato que toda seção implementa. A engine só orquestra — não toma
    decisões de paginação, validação ou render. Cada seção é responsável
    por si.
    """

    #: Identificador legível ('back_cover', 'cover', 'letter', etc.)
    type: str = ""

    #: Nome humano exibido em logs e mensagens de erro ('Contracapa', etc.)
    label: str = ""

    @abstractmethod
    def validate(self, inputs: dict) -> list[str]:
        """
        Verifica se os inputs estão completos e consistentes.
        Retorna lista de mensagens de erro em pt-BR, vazia se tudo ok.
        """

    @abstractmethod
    def paginate(self, inputs: dict) -> int:
        """Quantas páginas A4 esta seção vai ocupar com estes inputs."""

    @abstractmethod
    def render_a4(self, inputs: dict, theme) -> list[str]:
        """
        Renderiza em A4. Retorna uma lista de strings, uma por página.
        Cada string é o HTML <body> da página (sem <html> wrapper).
        O wrapper é responsabilidade do composer/theme.page_document().
        """

    @abstractmethod
    def render_mobile(self, inputs: dict, theme) -> list[str]:
        """Mesma ideia do render_a4 mas para Mobile (540×960)."""

    def required_assets(self, inputs: dict) -> list[str]:
        """
        URLs de assets externos a baixar antes de renderizar (fotos remotas,
        etc.). Default: nenhum. Subclasses sobrescrevem se precisarem.
        """
        return []

    # -------------------------------------------------------------------------
    # Helpers para subclasses

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type!r}>"
