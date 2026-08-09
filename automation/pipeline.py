"""Pipeline dle zadání: z č.1 nebo č.4 → vyplnit č.2 a č.3."""

from __future__ import annotations

from dataclasses import dataclass, field

from automation.extract import extract_data, validate_extracted_data
from automation.fill import generate_documents
from automation.logger import log_operation
from automation.storage import save_outputs, save_upload
from automation.validate import validate_file


@dataclass
class ProcessResult:
    ok: bool
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    output_files: list[str] = field(default_factory=list)


def process_document(
    filename: str,
    content: bytes,
    doc_type: str = "auto",
) -> ProcessResult:
    """
    1) validace PDF
    2) uložení vstupu
    3) extrakce dat z objednávky (č.1) nebo SoD (č.4)
    4) validace dat
    5) vyplnění F08 (č.2) + F02 (č.3)
    6) uložení do záloh
    """
    ok, err = validate_file(filename, content)
    if not ok:
        log_operation("validate", err, status="error")
        return ProcessResult(ok=False, error=err)

    log_operation("validate", f"Formát OK: {filename}")

    try:
        save_upload(filename, content, doc_type or "auto")
    except OSError as exc:
        log_operation("upload", str(exc), status="error")
        return ProcessResult(ok=False, error=f"Chyba při ukládání vstupu: {exc}")

    try:
        data = extract_data(filename, content, doc_type)
        log_operation(
            "extract",
            f"Extrakce z {data.get('typ_dokumentu')} ({filename}) dokončena",
        )
    except Exception as exc:  # noqa: BLE001
        log_operation("extract", str(exc), status="error")
        return ProcessResult(ok=False, error=f"Chyba extrakce dat: {exc}")

    _, warnings = validate_extracted_data(data)
    for w in warnings:
        log_operation("validate_data", w, status="warning")

    try:
        generated = generate_documents(data)
        log_operation("fill", "Vyplněny protokoly F08 (č.2) a F02 (č.3)")
    except Exception as exc:  # noqa: BLE001
        log_operation("fill", str(exc), status="error")
        return ProcessResult(ok=False, error=f"Chyba vyplnění šablon: {exc}", data=data)

    try:
        saved = save_outputs(generated)
        names = [p.name for p in saved]
        log_operation("backup", f"Uloženo: {', '.join(names)}")
    except OSError as exc:
        log_operation("backup", str(exc), status="error")
        return ProcessResult(
            ok=False,
            error=f"Chyba ukládání do úložiště: {exc}",
            data=data,
            warnings=warnings,
        )

    return ProcessResult(ok=True, data=data, warnings=warnings, output_files=names)
