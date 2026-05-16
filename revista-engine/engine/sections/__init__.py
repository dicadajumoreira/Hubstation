"""Camada de seções: cada uma das 16 partes da revista."""

from .back_cover import BackCover
from .base import A4, MOBILE, PageDimensions, Section
from .colophon import Colophon
from .community_invite import CommunityInvite
from .cover import Cover
from .cover_story import CoverStory
from .cultural_agenda import CulturalAgenda
from .editor_note import EditorNote
from .horoscope import Horoscope
from .industry_facts import IndustryFacts
from .letter import Letter
from .lifestyle_article import LifestyleArticle
from .news import News
from .our_condo_events import OurCondoEvents
from .our_condo_maintenance import OurCondoMaintenance
from .our_numbers import OurNumbers
from .recipe import Recipe
from .team_support import TeamSupport
from .tips import Tips
from .warnings import Warnings

__all__ = [
    "Section",
    "PageDimensions",
    "A4",
    "MOBILE",
    "BackCover",
    "Colophon",
    "CommunityInvite",
    "Cover",
    "CoverStory",
    "CulturalAgenda",
    "EditorNote",
    "Horoscope",
    "IndustryFacts",
    "Letter",
    "LifestyleArticle",
    "News",
    "OurCondoEvents",
    "OurCondoMaintenance",
    "OurNumbers",
    "Recipe",
    "TeamSupport",
    "Tips",
    "Warnings",
]
