from pathlib import Path

from fastapi import HTTPException

from .documents import file_hash
from .models import Artifact


def verified_path(file: Artifact, root: Path) -> Path:
    path = (root / file.path).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise HTTPException(410, "The generated file is unavailable")
    try:
        actual_hash = file_hash(path)
    except OSError as exc:
        raise HTTPException(410, "The generated file is unavailable") from exc
    if actual_hash != file.sha256:
        raise HTTPException(409, "File integrity check failed")
    return path
