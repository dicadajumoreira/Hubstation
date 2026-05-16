"""
SubFoldersReader — leitor da convenção com subpastas (Villa Park 04/2026).

Cada subpasta é uma manutenção/evento. Nome da subpasta = título.
Fotos dentro da subpasta são as fotos do grupo. Doc opcional dentro da
subpasta (qualquer .txt ou Google Doc lido) vira a descrição longa.

Esta é a convenção RECOMENDADA para edições novas — mais explícita,
escala bem para muitas manutenções, e elimina a heurística de agrupamento
por timestamp.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Photo, PhotoGroup, infer_badge


# Subpastas que devem ser ignoradas (sistema, output, etc.)
_IGNORE_PREFIXES = (".", "_OUTPUT", "_output", "output", "PDFs", "PDF")


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic"}


def _is_description_file(path: Path) -> bool:
    return path.suffix.lower() in {".txt", ".md"}


def _read_description(folder: Path) -> str:
    """
    Tentar ler o arquivo de descrição da subpasta. Procura por .txt ou .md.
    Retorna string vazia se não encontrar.
    """
    candidates = [p for p in folder.iterdir() if p.is_file() and _is_description_file(p)]
    if not candidates:
        return ""
    # Pegar o primeiro (ou o mais longo se houver mais de um)
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    try:
        return candidates[0].read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return ""


def _should_ignore(name: str) -> bool:
    """Decidir se uma subpasta deve ser ignorada."""
    return any(name.startswith(p) for p in _IGNORE_PREFIXES)


class SubFoldersReader:
    """
    Lê uma pasta de condomínio na convenção com subpastas.

    Estratégia:
    1. Para cada subpasta direta da pasta-raiz:
       - Nome da subpasta -> título do grupo
       - Fotos dentro da subpasta -> fotos do grupo
       - .txt ou .md dentro da subpasta -> descrição longa
       - Badge inferido do título (com override [tag] no fim)
    2. Subpastas que começam com ., _OUTPUT, etc. são ignoradas
    3. Subpastas vazias são ignoradas com aviso
    """

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def read(self) -> list[PhotoGroup]:
        if not self.folder.exists() or not self.folder.is_dir():
            raise FileNotFoundError(f"Pasta não encontrada: {self.folder}")

        groups: list[PhotoGroup] = []

        # Listar subpastas ordenadas por nome (consistência entre runs)
        subfolders = sorted(
            [p for p in self.folder.iterdir() if p.is_dir() and not _should_ignore(p.name)],
            key=lambda p: p.name.lower(),
        )

        for subfolder in subfolders:
            title = subfolder.name.strip()

            # Listar fotos dentro da subpasta (não recursivo por enquanto)
            photos = sorted(
                [p for p in subfolder.iterdir() if p.is_file() and _is_image(p)],
                key=lambda p: p.name.lower(),
            )

            if not photos:
                # Subpasta sem fotos — pode ser um caso real (carta + foto sindico, etc.)
                # mas para Nosso Condomínio queremos pelo menos 1 foto. Skip silencioso.
                continue

            description = _read_description(subfolder)

            groups.append(
                PhotoGroup(
                    title=title,
                    description=description,
                    badge=infer_badge(title),
                    photos=[
                        Photo(
                            local_path=p,
                            drive_id=None,
                            bytes_size=p.stat().st_size,
                        )
                        for p in photos
                    ],
                )
            )

        return groups
