"""Logování operací systému."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "storage" / "logs"
LOG_FILE = LOG_DIR / "system.log"


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_operation(action: str, detail: str, status: str = "ok") -> None:
    """Zapíše záznam operace do systémového logu."""
    _ensure_log_dir()
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "detail": detail,
        "status": status,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_logs(limit: int = 200) -> list[dict]:
    """Načte poslední záznamy logu (nejnovější nahoře)."""
    _ensure_log_dir()
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    entries: list[dict] = []
    for line in reversed(lines[-limit:]):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            entries.append(
                {
                    "timestamp": "",
                    "action": "raw",
                    "detail": line,
                    "status": "unknown",
                }
            )
    return entries
