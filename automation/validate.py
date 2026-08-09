"""Validace vstupních souborů."""

from __future__ import annotations

ALLOWED_EXTENSIONS = {".pdf"}


def validate_file(filename: str | None, content: bytes | None) -> tuple[bool, str]:
    if not filename:
        return False, "Soubor nemá název."
    if content is None or len(content) == 0:
        return False, "Soubor je prázdný."

    name = filename.lower().strip()
    if "." not in name:
        return False, "Soubor nemá příponu (očekáváno PDF)."

    ext = "." + name.rsplit(".", 1)[-1]
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Neplatný formát '{ext}'. Povolený formát: PDF (objednávka č.1 nebo smlouva č.4)."

    if not content.startswith(b"%PDF"):
        return False, "Soubor tvrdí, že je PDF, ale obsah neodpovídá."

    max_size = 30 * 1024 * 1024
    if len(content) > max_size:
        return False, "Soubor je příliš velký (max. 30 MB)."

    return True, ""
