"""Loading a client's uploaded files."""

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pypdf import PdfReader


@dataclass
class Document:
    name: str
    kind: str  # form16, interest_certificate, rent_receipts or unknown
    text: str


@dataclass
class CaseFiles:
    folder: Path
    documents: list = field(default_factory=list)
    ais: dict | None = None
    questionnaire: dict | None = None
    broker_rows: list = field(default_factory=list)


def classify(text: str) -> str:
    lowered = text.lower()
    if "form 16" in lowered or "form no. 16" in lowered or "section 203" in lowered:
        return "form16"
    if "interest certificate" in lowered:
        return "interest_certificate"
    if "rent receipt" in lowered:
        return "rent_receipts"
    return "unknown"


def read_pdf(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_case(folder) -> CaseFiles:
    folder = Path(folder)
    files = CaseFiles(folder=folder)
    for pdf in sorted(folder.glob("*.pdf")):
        text = read_pdf(pdf)
        files.documents.append(Document(pdf.name, classify(text), text))
    files.ais = read_json(folder / "ais.json")
    files.questionnaire = read_json(folder / "questionnaire.json")
    broker = folder / "broker_statement.csv"
    if broker.exists():
        with open(broker, newline="", encoding="utf-8") as f:
            files.broker_rows = list(csv.DictReader(f))
    return files


def capital_gains(rows: list) -> tuple[int, int]:
    """(short-term, long-term) gains from broker rows. Listed equity is long-term after 12 months."""
    short = long = 0
    for row in rows:
        gain = int(row["sell_value"]) - int(row["buy_value"])
        held = (date.fromisoformat(row["sell_date"]) - date.fromisoformat(row["buy_date"])).days
        if held > 365:
            long += gain
        else:
            short += gain
    return short, long
