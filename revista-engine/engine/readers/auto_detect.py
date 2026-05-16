"""
auto_detect — decide qual reader usar olhando a estrutura da pasta.

Regras simples:
- Se a pasta tem >= 3 subpastas com fotos dentro -> SubFoldersReader (Villa Park)
- Se a pasta tem >= 3 .txt-descrição na raiz       -> FlatFolderReader (Gardens)
- Misto / ambíguo                                  -> tenta os dois e mescla
"""

from __future__ import annotations

from pathlib import Path

from ..models import PhotoGroup
from .flat_folder import FlatFolderReader, _is_description_txt, _is_image
from .sub_folders import SubFoldersReader, _should_ignore


def detect_convention(folder: Path) -> str:
    """
    Olha a pasta e decide qual convenção predomina.
    Retorna: 'flat', 'subfolders' ou 'mixed'.
    """
    folder = Path(folder)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {folder}")

    # Contar subpastas com fotos
    subfolders_with_photos = 0
    for sub in folder.iterdir():
        if not sub.is_dir() or _should_ignore(sub.name):
            continue
        if any(_is_image(p) for p in sub.iterdir() if p.is_file()):
            subfolders_with_photos += 1

    # Contar .txt-descrição na raiz
    txt_descriptions = sum(
        1 for p in folder.iterdir() if p.is_file() and _is_description_txt(p)
    )

    has_subfolders = subfolders_with_photos >= 3
    has_flats = txt_descriptions >= 3

    if has_subfolders and has_flats:
        return "mixed"
    if has_subfolders:
        return "subfolders"
    if has_flats:
        return "flat"
    # Pouco material — default para flat (mais tolerante)
    return "flat"


def read_groups(folder: Path) -> tuple[list[PhotoGroup], str]:
    """
    Le os grupos de fotos da pasta usando o reader certo.
    Retorna (grupos, convencao_detectada).
    """
    convention = detect_convention(folder)

    if convention == "flat":
        groups = FlatFolderReader(folder).read()
    elif convention == "subfolders":
        groups = SubFoldersReader(folder).read()
    else:  # mixed
        # Mescla: pega subpastas + qualquer .txt solto na raiz
        sub_groups = SubFoldersReader(folder).read()
        flat_groups = FlatFolderReader(folder).read()
        # Evitar duplicação: se um grupo flat tem o mesmo título de um sub_group,
        # prefere o sub_group (subpasta é mais explícita)
        sub_titles = {g.title.lower() for g in sub_groups}
        flat_filtered = [g for g in flat_groups if g.title.lower() not in sub_titles]
        groups = sub_groups + flat_filtered

    return groups, convention
