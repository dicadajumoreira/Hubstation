"""revista-engine: readers — leem pastas locais e produzem PhotoGroups."""

from .auto_detect import detect_convention, read_groups
from .flat_folder import FlatFolderReader
from .sub_folders import SubFoldersReader

__all__ = [
    "FlatFolderReader",
    "SubFoldersReader",
    "detect_convention",
    "read_groups",
]
