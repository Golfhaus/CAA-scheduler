from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(
    path: Path,
    value: Any,
    *,
    indent: int = 2,
    trailing_newline: bool = True,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=indent, ensure_ascii=False)
        if trailing_newline:
            handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_from_repo(repo_root: Path, configured_path: str) -> Path:
    candidate = Path(configured_path)
    return candidate if candidate.is_absolute() else repo_root / candidate
