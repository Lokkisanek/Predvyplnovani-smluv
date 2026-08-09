"""Webová aplikace – předvyplňování protokolů TEDOM (č.2, č.3)."""

from __future__ import annotations

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from automation.logger import log_operation, read_logs
from automation.pipeline import process_document
from automation.storage import (
    ensure_dirs,
    get_backup_path,
    get_output_path,
    list_backups,
    list_outputs,
)

app = Flask(__name__)
app.secret_key = "firemni-system-predvyplnovani-smluv"

ensure_dirs()

DISPLAY_FIELDS = [
    ("typ_dokumentu", "Typ zdroje"),
    ("zdrojovy_soubor", "Zdrojový soubor"),
    ("zhotovitel_firma", "Zhotovitel – firma"),
    ("zhotovitel_adresa", "Zhotovitel – adresa"),
    ("zhotovitel_ico", "Zhotovitel – IČ"),
    ("zhotovitel_dic", "Zhotovitel – DIČ"),
    ("zhotovitel_or", "Zhotovitel – OR"),
    ("zhotovitel_kontakt", "Zhotovitel – kontakt"),
    ("nazev_stavby", "Název stavby"),
    ("misto_stavby", "Místo stavby"),
    ("predmet_dila", "Předmět díla"),
    ("cislo_smlouvy_obj", "Č. smlouvy / objednávky"),
    ("cislo_ifs", "Číslo IFS"),
    ("cena_bez_dph", "Cena bez DPH"),
    ("datum_zahajeni", "Datum zahájení"),
    ("datum_dokonceni", "Datum dokončení"),
    ("zaruka_mesice", "Záruka (měsíce)"),
    ("zaruka_na", "Záruka na"),
    ("zaruka_mesice_2", "Záruka 2 (měsíce)"),
    ("zaruka_na_2", "Záruka 2 na"),
    ("poznamky", "Poznámky"),
]


@app.route("/")
def index():
    return render_template("index.html", outputs=list_outputs()[:20])


@app.route("/upload", methods=["POST"])
def upload():
    soubor = request.files.get("dokument")
    doc_type = request.form.get("doc_type") or "auto"

    if not soubor or not soubor.filename:
        flash("Chybí vstupní dokument (objednávka č.1 nebo smlouva č.4).", "error")
        return redirect(url_for("index"))

    content = soubor.read()
    result = process_document(soubor.filename, content, doc_type)

    if not result.ok:
        flash(result.error, "error")
        log_operation("notify", f"Upozornění: {result.error}", status="error")
        return redirect(url_for("index"))

    rows = []
    for key, label in DISPLAY_FIELDS:
        val = result.data.get(key)
        if val:
            rows.append((label, val))

    return render_template(
        "result.html",
        rows=rows,
        warnings=result.warnings,
        files=result.output_files,
        typ=result.data.get("typ_dokumentu", ""),
    )


@app.route("/download/<path:name>")
def download(name: str):
    path = get_output_path(name)
    if path is None:
        abort(404)
    log_operation("download", f"Stažení: {path.name}")
    return send_file(path, as_attachment=True, download_name=path.name)


@app.route("/preview/<path:name>")
def preview(name: str):
    """Náhled PDF v prohlížeči (inline)."""
    path = get_output_path(name)
    if path is None:
        abort(404)
    return send_file(path, mimetype="application/pdf", as_attachment=False, download_name=path.name)


@app.route("/backup/download/<path:name>")
def download_backup(name: str):
    path = get_backup_path(name)
    if path is None:
        abort(404)
    log_operation("download_backup", f"Stažení zálohy: {path.name}")
    return send_file(path, as_attachment=True, download_name=path.name)


@app.route("/backup/preview/<path:name>")
def preview_backup(name: str):
    path = get_backup_path(name)
    if path is None:
        abort(404)
    return send_file(path, mimetype="application/pdf", as_attachment=False, download_name=path.name)


@app.route("/logs")
def logs():
    return render_template("logs.html", logs=read_logs())


@app.route("/backups")
def backups():
    return render_template("backups.html", backups=list_backups())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)