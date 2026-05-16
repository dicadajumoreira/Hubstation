"""
FlatFolderReader — leitor da convenção plana (Gardens 04/2026).

Detecta uma pasta de condomínio onde fotos e arquivos .txt estão na raiz,
e o nome do .txt é a descrição da manutenção. Agrupa fotos próximas
(por timestamp) com o .txt mais próximo.

Este é o reader de COMPATIBILIDADE — funciona com pastas existentes sem
exigir migração. Para edições novas, recomendamos a convenção com
subpastas (SubFoldersReader) que é mais explícita.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import BadgeKind, Photo, PhotoGroup, infer_badge


# Padrão de timestamp em nome de foto: PHOTO-YYYY-MM-DD-HH-MM-SS.jpg
_PHOTO_TS_RE = re.compile(
    r"PHOTO-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})", re.IGNORECASE
)

# Mínimo de caracteres para um .txt ser considerado "descrição de manutenção"
# (evita pegar txts pequenos como "ok.txt" ou ".DS_Store" interpretados)
_MIN_DESCRIPTION_LENGTH = 20


def _extract_timestamp(filename: str) -> Optional[datetime]:
    """Extrair timestamp de um nome de foto se ele seguir o padrão PHOTO-...jpg."""
    m = _PHOTO_TS_RE.search(filename)
    if not m:
        return None
    try:
        y, mo, d, h, mi, s = map(int, m.groups())
        return datetime(y, mo, d, h, mi, s)
    except ValueError:
        return None


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic"}


def _is_description_txt(path: Path) -> bool:
    """
    Um .txt conta como descrição se:
    - Extensão for .txt
    - Nome (sem extensão) tiver ao menos _MIN_DESCRIPTION_LENGTH caracteres
    - Não começar com . (oculto) ou _ (sistema)
    """
    if path.suffix.lower() != ".txt":
        return False
    name = path.stem.strip()
    if not name or name.startswith(".") or name.startswith("_"):
        return False
    return len(name) >= _MIN_DESCRIPTION_LENGTH


def _clean_description(name: str) -> str:
    """Limpar o nome do arquivo .txt para virar título/descrição legível."""
    # Remover quebras de linha que apareceram no nome (alguns sistemas fazem isso)
    name = name.replace("\n", " ").replace("\r", " ")
    # Comprimir espaços múltiplos
    name = re.sub(r"\s+", " ", name)
    # Remover ponto final extra se houver
    name = name.rstrip(".")
    return name.strip()


class FlatFolderReader:
    """
    Lê uma pasta de condomínio na convenção plana.

    Estratégia:
    1. Lista todos os arquivos da pasta (não recursivo).
    2. Separa em: imagens, .txt-descrição, outros (ignorados).
    3. Para cada .txt-descrição, agrupa fotos próximas em timestamp
       (janela de ±48h por padrão).
    4. Fotos sem .txt próximo viram um grupo "Outros Registros do Mês".
    """

    def __init__(self, folder: Path, time_window_minutes: int = 60 * 48):
        """
        time_window_minutes: janela de tempo em minutos para agrupar foto com .txt.
        Default 48h, que é tolerante o bastante para .txts criados em momentos
        diferentes da captura das fotos. Cada foto vai para o .txt MAIS PRÓXIMO
        em timestamp dentro dessa janela (não para o primeiro encontrado).
        """
        self.folder = Path(folder)
        self.time_window = time_window_minutes * 60  # em segundos

    def read(self) -> list[PhotoGroup]:
        if not self.folder.exists() or not self.folder.is_dir():
            raise FileNotFoundError(f"Pasta não encontrada: {self.folder}")

        files = list(self.folder.iterdir())

        images: list[tuple[Path, Optional[datetime]]] = []
        txts: list[Path] = []

        for p in files:
            if not p.is_file():
                continue
            if _is_image(p):
                images.append((p, _extract_timestamp(p.name)))
            elif _is_description_txt(p):
                txts.append(p)

        # Sem nenhum txt: tudo vira um único grupo "Manutenções do Mês"
        if not txts:
            if not images:
                return []
            return [
                PhotoGroup(
                    title="Manutenções do Mês",
                    description="",
                    badge=BadgeKind.MANUTENCAO,
                    photos=[
                        Photo(local_path=p, drive_id=None, bytes_size=p.stat().st_size)
                        for p, _ in images
                    ],
                )
            ]

        # Para cada foto, achar o txt mais próximo em timestamp (dentro da janela).
        # Isso evita que uma foto seja roubada pelo primeiro txt em janela quando
        # há outro txt mais relevante.

        # Ordenar txts por mtime para resultado determinístico
        txts_sorted = sorted(txts, key=lambda p: p.stat().st_mtime)

        groups_by_txt: dict[Path, list[Photo]] = {t: [] for t in txts_sorted}
        descriptions: dict[Path, str] = {}
        titles: dict[Path, str] = {}

        # Pre-computar mtime e título de cada txt
        for txt in txts_sorted:
            titles[txt] = _clean_description(txt.stem)
            try:
                descriptions[txt] = txt.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                descriptions[txt] = ""

        txt_times = {t: datetime.fromtimestamp(t.stat().st_mtime) for t in txts_sorted}

        used_images: set[Path] = set()
        for img, ts in images:
            ref_time = ts or datetime.fromtimestamp(img.stat().st_mtime)

            # Encontrar o txt mais próximo
            best_txt: Optional[Path] = None
            best_delta: float = float("inf")
            for txt, t_time in txt_times.items():
                delta = abs((ref_time - t_time).total_seconds())
                if delta <= self.time_window and delta < best_delta:
                    best_delta = delta
                    best_txt = txt

            if best_txt is not None:
                groups_by_txt[best_txt].append(
                    Photo(
                        local_path=img,
                        drive_id=None,
                        bytes_size=img.stat().st_size,
                    )
                )
                used_images.add(img)

        groups: list[PhotoGroup] = []
        for txt in txts_sorted:
            groups.append(
                PhotoGroup(
                    title=titles[txt],
                    description=descriptions[txt],
                    badge=infer_badge(titles[txt]),
                    photos=groups_by_txt[txt],
                )
            )

        # Fotos órfãs (sem nenhum txt próximo) viram um grupo "Avulsas"
        orphans = [
            Photo(local_path=p, drive_id=None, bytes_size=p.stat().st_size)
            for p, _ in images
            if p not in used_images
        ]
        if orphans:
            groups.append(
                PhotoGroup(
                    title="Outros Registros do Mês",
                    description="",
                    badge=BadgeKind.MANUTENCAO,
                    photos=orphans,
                )
            )

        return groups
