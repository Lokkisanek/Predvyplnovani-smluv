# Předvyplňování protokolů TEDOM

Ze zdrojového PDF (**č.1 Objednávka** nebo **č.4 Smlouva o dílo**) systém vytáhne
zvýrazněné údaje a předvyplní:

- **č.2** Zjišťovací protokol ke konečné faktuře (F08)
- **č.3** Závěrečný protokol o předání a převzetí díla (F02)

## Spuštění

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Otevřete http://127.0.0.1:5000

## Testovací soubory

Ve složce `Dokumenty/`:

- `c.1_...pdf` – objednávka
- `c.4_...pdf` – smlouva o dílo
- `c.2_...pdf` / `c.3_...pdf` – šablony protokolů (zkopírovány do `document_templates/`)

## Extrahovaná pole

Zhotovitel (firma, adresa, IČ, DIČ, OR, kontakt), název/místo stavby, předmět díla,
číslo smlouvy/objednávky, číslo IFS, cena bez DPH, termíny, záruka.
