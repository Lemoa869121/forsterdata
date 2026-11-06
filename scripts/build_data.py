#!/usr/bin/env python3
"""Convertit les exports CSV (Glide) de data/csv/ en un fichier data/data.json
utilisé par l'application.

Usage :  python3 scripts/build_data.py

Dépôt public : les exports bruts (avec notes internes) se déposent dans
data/brut/ (dossier ignoré par git). Le script en tire des CSV nettoyés,
sans colonnes internes, dans data/csv/ (versionnés), puis data/data.json.
Sans data/brut/, il repart directement de data/csv/ (cas de GitHub Actions).

- nettoie les espaces / retours à la ligne parasites,
- convertit les dates de validité (formats JJ/MM/AAAA et M/J/AA) en AAAA-MM-JJ,
- convertit les dimensions en nombres (0 = non applicable -> vide),
- retire les colonnes internes (notes internes, révisions à venir, etc.).
"""
import csv
import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "csv"
RAW_DIR = ROOT / "data" / "brut"
OUT = ROOT / "data" / "data.json"

# Colonnes jamais publiées dans l'application
INTERNAL = {
    "Note interne",
    "A ajouter pour prochaine revision",
    "Date modification",
    "Id to display",
    "Propriétaire(s)",
    "ID",
    "Id",
}

# Renommage des colonnes (clé CSV nettoyée -> libellé affiché)
RENAME = {
    "Codificatiotion de classsement": "Codification de classement",
    "Ext. Rec. Rév.": "Ext. - Rec. - Rév.",
    "Degré feu": "Classe",  # dans RC / FB la colonne « Degré feu » contient la classe
    "RW ctr": "Rw Ctr",
}

# Champs courts : on réduit tous les espaces / retours à la ligne à un seul espace
SHORT = {
    "Type de châssis", "Série", "Classe", "Degré feu", "Verrier", "n° PV",
    "A", "E", "V", "V type abc", "Rw", "Rw C", "Rw Ctr", "Type de résistance",
    "Entrée controlée", "Entrée controlée type", "Sortie type", "Type de verrouillage",
    "Codification de classement",
}

NUMERIC = {
    "Largeur Verre", "Hauteur Verre", "Largeur 1V", "Largeur 2V",
    "Hauteur BP1V", "Hauteur BP2V", "Hauteur Cloison",
}

CATEGORIES = [
    # id, libellé, groupe, fichier
    ("feu", "Feu", "ForsterSecuData", "BDD Feu.csv"),
    ("rc", "Anti-effraction", "ForsterSecuData", "Base de donnéeRC.csv"),
    ("fb", "Pare-balles", "ForsterSecuData", "Base de donnéeFB.csv"),
    ("aev", "Performance AEV", "ForsterData", "AEV.csv"),
    ("acoustique", "Performance acoustique", "ForsterData", "Acoustique.csv"),
]


def read_csv(name):
    with open(CSV_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sanitize_raw_exports():
    """Copie data/brut/*.csv vers data/csv/ en supprimant les colonnes internes."""
    if not RAW_DIR.is_dir():
        return
    files = sorted(RAW_DIR.glob("*.csv"))
    for src in files:
        with open(src, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            continue
        keep = [i for i, h in enumerate(rows[0]) if clean_key(h) not in INTERNAL]
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        with open(CSV_DIR / src.name, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            for r in rows:
                w.writerow([r[i] if i < len(r) else "" for i in keep])
    if files:
        print(f"{len(files)} export(s) de data/brut/ nettoyé(s) -> data/csv/")


def clean_key(k):
    k = re.sub(r"\s+", " ", k).strip()
    k = re.sub(r"\s*:$", "", k)
    return RENAME.get(k, k)


def clean_long(v):
    v = v.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in v.split("\n")]
    out, blank = [], False
    for l in lines:
        if not l:
            if out and not blank:
                out.append("")
            blank = True
        else:
            out.append(l)
            blank = False
    return "\n".join(out).strip()


def parse_date(v):
    """Les exports mélangent JJ/MM/AAAA (« 20/01/2031 0:00:00 ») et le format
    américain M/J/AAAA (« 10/14/2029, 12:00:00 AM », « 2/16/29 »)."""
    v = v.strip()
    if not v:
        return None
    d = re.split(r"[ ,]", v)[0]
    us_first = bool(re.search(r"(AM|PM)$", v)) or bool(re.fullmatch(r"\d+/\d+/\d{2}", d))
    fmts = ["%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y"] if us_first else ["%d/%m/%Y", "%m/%d/%Y", "%m/%d/%y"]
    for fmt in fmts + ["%Y-%m-%d"]:
        try:
            return datetime.strptime(d, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def parse_num(v):
    v = v.strip().replace(" ", "").replace(",", ".")
    try:
        n = float(v)
    except ValueError:
        return None
    return int(n) if n > 0 else None


def clean_row(raw):
    row = {}
    for k, v in raw.items():
        if k is None:
            continue
        key = clean_key(k)
        if key in INTERNAL or key in RENAME and RENAME[key] in INTERNAL:
            continue
        v = v or ""
        if key in NUMERIC:
            row[key] = parse_num(v)
        elif key == "Validité":
            row[key] = parse_date(v)
        elif key in SHORT:
            row[key] = re.sub(r"\s+", " ", v).strip()
        else:
            row[key] = clean_long(v)
    return row


def main():
    sanitize_raw_exports()
    cats = []
    for cid, label, group, fname in CATEGORIES:
        rows = [clean_row(r) for r in read_csv(fname)]
        if cid in ("aev", "acoustique"):
            # ces exports contiennent une ligne vide entre chaque élément : on les retire
            for r in rows:
                for k, v in r.items():
                    if isinstance(v, str) and "\n" in v:
                        r[k] = re.sub(r"\n{2,}", "\n", v)
        if cid == "feu":
            for r in rows:
                # Le CSV Feu garde le nom « Degré feu » (renommé « Classe » ci-dessus) :
                # on découpe en famille (E / EI) et durée (30, 60…)
                deg = r.pop("Classe", "")
                r["Degré feu"] = deg
                m = re.match(r"^(EI|E)(\d+)$", deg.replace(" ", ""))
                r["_classe"] = m.group(1) if m else ""
                r["_temps"] = int(m.group(2)) if m else None
        if cid == "acoustique":
            for r in rows:
                r["Rw"] = int(r["Rw"]) if r.get("Rw", "").lstrip("-").isdigit() else None
        rows = [r for r in rows if r.get("n° PV") or r.get("Type de châssis")]
        cats.append({"id": cid, "label": label, "group": group, "rows": rows})

    ref = {
        "series": [r["Name"] for r in read_csv("Serie.csv")],
        "verriers": [r["Name"] for r in read_csv("Verriers.csv")],
        "dimCodes": {r["Application"].strip(): r["CodeDim"].strip()
                     for r in read_csv("Correspondances pour dimensions.csv")},
        "dimApplications": [
            {"label": "Cloison / châssis vitré", "code": "CV"},
        ] + [{"label": r["Application"].strip(), "code": r["CodeDim"].strip()}
             for r in read_csv("Applications pour dimensions.csv")],
        "moisAlerteValidite": int(read_csv("Filtre Validité.csv")[0]["Mois_Val_To_Use"] or 3),
    }
    data = {"generated": date.today().isoformat(), "categories": cats, "ref": ref}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    for c in cats:
        print(f"{c['label']:<25} {len(c['rows']):>4} lignes")
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
