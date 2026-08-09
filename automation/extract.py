"""Extrakce dat z objednávky (č.1) nebo smlouvy o dílo (č.4)."""

from __future__ import annotations

import io
import re
from pathlib import Path

from pypdf import PdfReader


def pdf_to_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def detect_doc_type(text: str, filename: str = "") -> str:
    """Vrátí 'objednavka' (č.1) nebo 'smlouva' (č.4)."""
    lower = text.lower()
    name = filename.lower()
    if "smlouva o dílo" in lower or "smlouva o dilo" in lower or "sod" in name:
        return "smlouva"
    if "objednávka dodávek" in lower or "objednavka" in name or "číslo ifs" in lower:
        return "objednavka"
    if "objednávka" in lower:
        return "objednavka"
    return "objednavka"


def _clean(value: str) -> str:
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n+", " ", value)
    return value.strip(" \t\n\r,;:")


def _search(patterns: list[str], text: str, flags: int = re.IGNORECASE | re.MULTILINE) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return _clean(match.group(1))
    return ""


def _norm_date(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    # 10. 7. 2026 -> 10.7.2026
    m = re.match(r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{2,4})", value)
    if m:
        d, mo, y = m.groups()
        if len(y) == 2:
            y = "20" + y
        return f"{int(d)}.{int(mo)}.{y}"
    return value


def _norm_price(value: str) -> str:
    value = value.replace(".-", "").replace(",-", "")
    value = re.sub(r"[^\d\s.,]", "", value)
    value = value.strip()
    # 86.000 -> 86 000,00 style preferred by forms
    value = value.replace(".", " ").replace(",", ".")
    # if ends with .00 keep as Czech ,00
    if re.search(r"\.\d{2}$", value):
        value = value.replace(".", ",")
    else:
        # plain integer-ish
        digits = re.sub(r"\s+", "", value)
        if digits.isdigit():
            # format with spaces: 49450 -> 49 450,00
            n = int(digits)
            formatted = f"{n:,}".replace(",", " ")
            return f"{formatted},00"
    return value


def extract_from_objednavka(text: str) -> dict[str, str]:
    """Extrakce zvýrazněných polí z objednávky (dokument č.1)."""
    data: dict[str, str] = {"typ_zdroje": "objednavka"}

    data["cislo_ifs"] = _search(
        [
            r"Číslo\s+IFS\s*[:\s]*([A-Z0-9]+)",
            r"IFS\s*[:\s]*([A-Z]\d{5,})",
        ],
        text,
    )

    data["cislo_smlouvy_obj"] = data["cislo_ifs"]  # u objednávky často stačí IFS / číslo objednávky

    # V PDF TEDOM jsou hodnoty často před popisky:
    # "24 měsíců 10. 7. 2026\n24. 7. 2026\nZáruka:\n...\nDatum zahájení:\nDatum dokončení:"
    block = re.search(
        r"(\d+)\s*měsíc[ůu]?\s+(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})\s+(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})",
        text,
        re.IGNORECASE,
    )
    if block:
        data["zaruka_mesice"] = block.group(1)
        data["datum_zahajeni"] = _norm_date(block.group(2))
        data["datum_dokonceni"] = _norm_date(block.group(3))
    else:
        data["zaruka_mesice"] = _search(
            [
                r"Záruka\s*:\s*(\d+)\s*měsíc",
                r"(\d+)\s*měsíc",
            ],
            text,
        )
        data["datum_zahajeni"] = _norm_date(
            _search(
                [
                    r"Datum\s+zahájení\s*:?\s*(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})",
                    r"zahájení\s*:?\s*(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})",
                ],
                text,
            )
        )
        data["datum_dokonceni"] = _norm_date(
            _search(
                [
                    r"Datum\s+dokončení\s*:?\s*(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})",
                    r"dokončení\s*:?\s*(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})",
                ],
                text,
            )
        )

    # Zhotovitel blok – po "Zhotovitel:"
    zh = re.search(
        r"Zhotovitel\s*:?\s*(?:IČ\s*:\s*(\d{8})\s*DIČ\s*:\s*([A-Z0-9]+))?\s*\n?"
        r"([^\n]+)\n"
        r"([^\n]+)\n"
        r"([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if zh:
        if zh.group(1):
            data["zhotovitel_ico"] = zh.group(1)
        if zh.group(2):
            data["zhotovitel_dic"] = zh.group(2)
        firma = _clean(zh.group(3))
        # přeskočit řádky typu "IČ: ..."
        if not re.match(r"^I[ČC]", firma, re.I):
            data["zhotovitel_firma"] = firma
        addr1 = _clean(zh.group(4))
        addr2 = _clean(zh.group(5))
        # vynechat "ČESKÁ REPUBLIKA" alone as third, keep street + city
        parts = [p for p in (addr1, addr2) if p and "telefon" not in p.lower()]
        if parts and parts[-1].upper().startswith("ČESK"):
            parts = parts[:-1]
        data["zhotovitel_adresa"] = ", ".join(parts)

    if not data.get("zhotovitel_ico"):
        data["zhotovitel_ico"] = _search([r"Zhotovitel:.*?I[ČC]\s*:\s*(\d{8})"], text, re.I | re.S)
    if not data.get("zhotovitel_dic"):
        data["zhotovitel_dic"] = _search(
            [r"Zhotovitel:.*?DI[ČC]\s*:\s*([A-Z]{0,2}\d{8,10})"], text, re.I | re.S
        )
    if not data.get("zhotovitel_firma"):
        data["zhotovitel_firma"] = _search(
            [r"Zhotovitel:.*?\n([A-Za-zÁ-ž0-9].*(?:s\.r\.o\.|a\.s\.|spol\.).*)"],
            text,
            re.I | re.S,
        )

    # Předmět – typicky popis položky
    data["predmet_dila"] = _search(
        [
            r"(Kvasiny\s*[-–].+)",
            r"Objednáváme u vás dodávky a práce dle následujícího rozpisu:\s*\n(.+)",
        ],
        text,
    )
    # název stavby z předmětu (před první pomlčkou)
    if data.get("predmet_dila"):
        first = data["predmet_dila"].split("-")[0].strip()
        data["nazev_stavby"] = first
        data["misto_stavby"] = first

    data["cena_bez_dph"] = _norm_price(
        _search(
            [
                r"Celkem\s+CZK\s*([\d\s]+[.,]\d{2})",
                r"Celkem\s*:?\s*([\d\s]+[.,]\d{2})",
            ],
            text,
        )
    )

    data["poznamky"] = _search([r"Poznámky\s*\n(.+)"], text)

    # kontakt / OR u objednávky často chybí
    data.setdefault("zhotovitel_kontakt", "")
    data.setdefault("zhotovitel_or", "")
    data.setdefault("zaruka_na", "")
    data.setdefault("dodatky", "")
    data["poznamky"] = ""

    return data


def extract_from_smlouva(text: str) -> dict[str, str]:
    """Extrakce polí ze smlouvy o dílo (dokument č.4)."""
    data: dict[str, str] = {"typ_zdroje": "smlouva"}

    data["cislo_smlouvy_obj"] = _search(
        [
            r"Smlouva\s+o\s+dílo\s+č\.\s*([A-Za-z0-9_\-/]+)",
            r"SoD\s*[:\s]*([A-Za-z0-9_\-/]+)",
        ],
        text,
    )

    # Reálné IFS (např. E261115), ne text typu „toto objednatel sdělí“
    data["cislo_ifs"] = _search(
        [
            r"Číslo\s+IFS\s+([A-Z]\d{5,})",
            r"\bIFS\s*[:\s]+([A-Z]\d{5,})\b",
        ],
        text,
    )

    # Jen blok Zhotovitel (do II. Předmět / další kapitoly)
    zh_block_m = re.search(
        r"Zhotovitel\s*:(.*?)(?:\n\s*II\.|\n\s*Předmět díla|\n\s*2\.\d)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    zh_block = zh_block_m.group(1) if zh_block_m else text

    data["zhotovitel_firma"] = _search([r"^\s*([^\n]+?)\s*$"], zh_block) or _search(
        [r"Zhotovitel\s*:\s*([^\n]+)"], text
    )
    # první neprázdný řádek po Zhotovitel:
    for line in zh_block.splitlines():
        line = line.strip()
        if line and not line.lower().startswith("sídlo"):
            data["zhotovitel_firma"] = _clean(line)
            break

    data["zhotovitel_adresa"] = _search([r"sídlo\s*:\s*([^\n]+)"], zh_block)
    data["zhotovitel_or"] = _search(
        [
            r"rejstříku vedeném u\s+([^\n]+)",
            r"zapsaná v obchodním rejstříku vedeném u\s+([^\n]+)",
        ],
        zh_block,
    )
    data["zhotovitel_ico"] = re.sub(
        r"\s+", "", _search([r"I[ČC]O?\s*:\s*([\d\s]{8,})"], zh_block)
    )
    data["zhotovitel_dic"] = re.sub(
        r"\s+",
        "",
        _search([r"DI[ČC]\s*:\s*(CZ\s*\d{8,10}|\d{8,10})"], zh_block),
    )

    email = _search(
        [r"e-?mail\s*:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"],
        zh_block,
    )
    tel = _search([r"tel\s*:\s*([+\d][\d\s/]{6,})"], zh_block)
    data["zhotovitel_kontakt"] = ", ".join(p for p in (tel, email) if p)

    # Stavba – nejdřív z projektové dokumentace (kompletní název)
    stavba = _search(
        [
            r"projektovou\s+dokumentací\s+[„\"“](.+?)[“\"”]",
            r"na\s+stavbě\s*[-–]\s*((?:[^\n]|\n)+?)\.",
        ],
        text,
        re.I | re.S,
    )
    stavba = _clean(stavba) if stavba else ""
    data["nazev_stavby"] = stavba
    if stavba:
        mesto = re.search(
            r"(Aquapark\s+Vrchlabí|Vrchlabí|Praha|Brno|Třebíč|Kvasiny)\b",
            stavba,
            re.I,
        )
        data["misto_stavby"] = mesto.group(1) if mesto else stavba
    else:
        data["misto_stavby"] = ""

    predmet = _search(
        [
            r"provedení\s+[„\"“]([^„\"“]+)[“\"”]",
            r"realizaci\s+(.+?)\s+na\s+stavbě",
        ],
        text,
        re.I | re.S,
    )
    predmet = _clean(predmet) if predmet else ""
    if predmet and stavba:
        data["predmet_dila"] = f"{predmet} – {stavba}"
    else:
        data["predmet_dila"] = predmet or stavba

    data["cena_bez_dph"] = _norm_price(
        _search(
            [
                r"cena\s+pevná\s+ve\s+výši\s*([\d.\s]+(?:,-)?(?:\s*Kč)?)",
                r"ve\s+výši\s*([\d.\s]+,-)",
            ],
            text,
        )
    )

    data["datum_dokonceni"] = _norm_date(
        _search(
            [
                r"dokončit\s+dílo\s+v\s+termínu\s+(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})",
                r"dokončit\s+dílo\s+v\s+termínu\s+(\d{1,2}\.\d{1,2}\.\d{2,4})",
            ],
            text,
        )
    )
    data["datum_zahajeni"] = _norm_date(
        _search(
            [
                r"dokumentaci\s+pro\s+provedení\s+díla\s+v\s+termínu\s+(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})",
                r"v\s+termínu\s+(\d{1,2}\.\d{1,2}\.\d{2,4})",
            ],
            text,
        )
    )

    # Záruky – vezmi hlavní montážní, případně první nalezenou
    zaruka = _search(
        [
            r"[Zz]áruky\s+na\s+montážní[^0-9]{0,40}(\d+)\s*měsíc",
            r"na\s+dobu\s+(\d+)\s*měsíc",
        ],
        text,
    )
    data["zaruka_mesice"] = zaruka
    data["zaruka_na"] = "montážní a SW práce" if zaruka else ""

    zaruka2 = _search(
        [
            r"nejméně\s+však\s+na\s+dobu\s+(\d+)\s*měsíc",
            r"[Zz]áruky\s+na\s+zařízení[^0-9]{0,80}(\d+)\s*měsíc",
        ],
        text,
    )
    data["zaruka_mesice_2"] = zaruka2
    data["zaruka_na_2"] = "zařízení" if zaruka2 else ""

    data["dodatky"] = ""
    data["poznamky"] = ""

    return data


def extract_data(filename: str, content: bytes, doc_type: str | None = None) -> dict[str, str]:
    text = pdf_to_text(content)
    if not doc_type or doc_type == "auto":
        doc_type = detect_doc_type(text, filename)

    if doc_type == "smlouva":
        data = extract_from_smlouva(text)
    else:
        data = extract_from_objednavka(text)

    data["zdrojovy_soubor"] = Path(filename).name
    data["typ_dokumentu"] = doc_type
    data["_raw_preview"] = text[:2500]
    return data


def validate_extracted_data(data: dict) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    required_soft = [
        ("zhotovitel_firma", "Firma zhotovitele"),
        ("zhotovitel_ico", "IČ zhotovitele"),
        ("predmet_dila", "Předmět díla"),
    ]
    for key, label in required_soft:
        if not data.get(key):
            warnings.append(f"Nebylo nalezeno: {label}.")
    return True, warnings
