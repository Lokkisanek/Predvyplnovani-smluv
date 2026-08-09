"""Vyplnění PDF šablon F08 (č.2) a F02 (č.3)."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "document_templates"

TEMPLATE_F08 = TEMPLATES_DIR / "F08_Zjistovaci_protokol.pdf"
TEMPLATE_F02 = TEMPLATES_DIR / "F02_Zaverecny_protokol.pdf"


def _safe_name(data: dict) -> str:
    base = data.get("zhotovitel_firma") or data.get("cislo_ifs") or data.get("cislo_smlouvy_obj") or "dokument"
    base = base.replace(" ", "_")[:40]
    return "".join(ch for ch in base if ch.isalnum() or ch in "_-") or "dokument"


def map_f02_fields(data: dict) -> dict[str, str]:
    """Mapování dat → pole Závěrečného protokolu (F02 / č.3)."""
    zaruka_na = data.get("zaruka_na", "")
    # „dílo“ do záruk nedáváme
    if zaruka_na.strip().lower() in {"dílo", "dilo"}:
        zaruka_na = ""

    return {
        # Zhotovitel
        "Textové pole14": data.get("zhotovitel_firma", ""),
        "Textové pole8": data.get("zhotovitel_adresa", ""),
        "Textové pole10": data.get("zhotovitel_kontakt", ""),
        "Textové pole9": data.get("zhotovitel_or", ""),
        "Textové pole12": data.get("zhotovitel_ico", ""),
        "Textové pole11": data.get("zhotovitel_dic", ""),
        # Stavba – jen název, místo nevyplňovat
        "Textové pole15": data.get("nazev_stavby", ""),
        # Předmět
        "Textové pole13": data.get("predmet_dila", ""),
        # Číslo IFS (číslo smlouvy/objednávky nevyplňovat)
        "Textové pole30": data.get("cislo_ifs", ""),
        "Textové pole25": data.get("dodatky", ""),
        # Lhůty
        "datum_od": data.get("datum_zahajeni", ""),
        "dokonceni_plan": data.get("datum_dokonceni", ""),
        # Záruky (bez „dílo“, bez poznámek)
        "Textové pole21": data.get("zaruka_mesice", ""),
        "Textové pole19": zaruka_na,
        "Textové pole22": data.get("zaruka_mesice_2", ""),
        "Textové pole20": data.get("zaruka_na_2", ""),
    }


def map_f08_fields(data: dict) -> dict[str, str]:
    """Mapování dat → pole Zjišťovacího protokolu (F08 / č.2)."""
    cena = data.get("cena_bez_dph", "")
    return {
        # Zhotovitel
        "Textové pole74": data.get("zhotovitel_firma", ""),
        "Textové pole68": data.get("zhotovitel_adresa", ""),
        "Textové pole70": data.get("zhotovitel_kontakt", ""),
        "Textové pole69": data.get("zhotovitel_or", ""),
        "Textové pole72": data.get("zhotovitel_ico", ""),
        "Textové pole71": data.get("zhotovitel_dic", ""),
        # Stavba – jen název, místo nevyplňovat
        "Textové pole76": data.get("nazev_stavby", ""),
        # Předmět
        "Textové pole73": data.get("predmet_dila", ""),
        # Odsouhlasené údaje – bez čísla smlouvy/objednávky a bez poznámek
        "Textové pole82": data.get("cislo_ifs", ""),
        "Textové pole81": cena,
        # Součty
        "součet": cena or "0",
        "celkem": cena or "0",
    }


def _fill_pdf(template_path: Path, field_values: dict[str, str]) -> bytes:
    if not template_path.exists():
        raise FileNotFoundError(f"Šablona nenalezena: {template_path}")

    # Odfiltruj prázdné hodnoty – ať se nepřepisují existující prázdná pole zbytečně
    values = {k: v for k, v in field_values.items() if v}

    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.append(reader)

    # NeedAppearances: prohlížeč vykreslí unicode (čeština) sám
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, values, auto_regenerate=False)
        except Exception:
            writer.update_page_form_field_values(page, values)

    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update(
            {NameObject("/NeedAppearances"): BooleanObject(True)}
        )

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def generate_documents(data: dict) -> list[tuple[str, bytes]]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = _safe_name(data)

    f08 = _fill_pdf(TEMPLATE_F08, map_f08_fields(data))
    f02 = _fill_pdf(TEMPLATE_F02, map_f02_fields(data))

    return [
        (f"{stamp}_{safe}_F08_Zjistovaci_protokol.pdf", f08),
        (f"{stamp}_{safe}_F02_Zaverecny_protokol.pdf", f02),
    ]
