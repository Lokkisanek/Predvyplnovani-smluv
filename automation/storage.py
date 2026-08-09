"""Uložiště souborů (uploady, výstupy, zálohy)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from automation.logger import log_operation

BASE = Path(__file__).resolve().parent.parent / "storage"
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
BACKUPS = BASE / "backups"


def ensure_dirs() -> None:
    for d in (UPLOADS, OUTPUTS, BACKUPS, BASE / "logs"):
        d.mkdir(parents=True, exist_ok=True)


def save_upload(filename: str, content: bytes, doc_type: str) -> Path:
    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = Path(filename).name
    target = UPLOADS / f"{stamp}_{doc_type}_{safe}"
    target.write_bytes(content)
    log_operation("upload", f"Uložen vstup: {target.name} ({doc_type})")
    return target


def save_outputs(files: list[tuple[str, bytes]]) -> list[Path]:
    """Uloží vygenerované dokumenty do výstupů a záloh."""
    ensure_dirs()
    saved: list[Path] = []
    for name, content in files:
        out_path = OUTPUTS / name
        out_path.write_bytes(content)
        backup_path = BACKUPS / name
        shutil.copy2(out_path, backup_path)
        saved.append(out_path)
        log_operation("save", f"Uložen výstup a záloha: {name}")
    return saved


def list_outputs() -> list[dict]:
    ensure_dirs()
    items = []
    for path in sorted(OUTPUTS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file():
            items.append(
                {
                    "name": path.name,
                    "size": path.stat().st_size,
                    "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(
                        timespec="seconds"
                    ),
                    "kind": "output",
                }
            )
    return items


def list_backups() -> list[dict]:
    ensure_dirs()
    items = []
    for path in sorted(BACKUPS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file():
            items.append(
                {
                    "name": path.name,
                    "size": path.stat().st_size,
                    "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(
                        timespec="seconds"
                    ),
                    "kind": "backup",
                }
            )
    return items


def get_output_path(name: str) -> Path | None:
    ensure_dirs()
    path = (OUTPUTS / Path(name).name).resolve()
    if path.parent != OUTPUTS.resolve() or not path.is_file():
        return None
    return path


def get_backup_path(name: str) -> Path | None:
    ensure_dirs()
    path = (BACKUPS / Path(name).name).resolve()
    if path.parent != BACKUPS.resolve() or not path.is_file():
        return None
    return path
