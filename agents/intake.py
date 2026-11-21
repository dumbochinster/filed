"""Intake: the model reads each PDF; plain code reads the structured files."""

import re
from dataclasses import dataclass, field

from agents.documents import CaseFiles
from agents.llm import LLMError

PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
TAN = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]$")

SYSTEM = (
    "You read Indian income-tax documents and return JSON only. Copy each number exactly as "
    "printed, as a whole number of rupees without commas or currency signs. Use 0 for an amount "
    "that is not on the document and null for missing text. Do not calculate or guess anything."
)

# field name -> (type, what to look for)
FORM16_FIELDS = {
    "employer_name": ("str", "name of the employer / deductor"),
    "tan": ("str", "TAN of the deductor"),
    "employee_pan": ("str", "PAN of the employee"),
    "gross_salary": ("int", "gross salary"),
    "basic_da": ("int", "basic salary plus dearness allowance"),
    "hra_received": ("int", "house rent allowance received"),
    "professional_tax": ("int", "professional tax / tax on employment"),
    "employer_nps": ("int", "employer contribution to NPS"),
    "tds_deducted": ("int", "total tax deducted at source"),
    "sec_80c": ("int", "deduction under section 80C"),
    "sec_80ccd_1b": ("int", "deduction under section 80CCD(1B)"),
    "health_self": ("int", "deduction under section 80D"),
    "foreign_rsu": (
        "bool",
        "true if the document mentions RSUs or shares of a foreign parent company",
    ),
}
CERTIFICATE_FIELDS = {
    "bank": ("str", "name of the bank"),
    "savings_interest": ("int", "interest on the savings account"),
    "deposit_interest": ("int", "interest on fixed deposits"),
}
RENT_FIELDS = {
    "landlord_name": ("str", "name of the landlord"),
    "landlord_pan": ("str_or_null", "PAN of the landlord, null if not provided"),
    "annual_rent": ("int", "total rent paid for the year"),
}


class ExtractionError(Exception):
    pass


@dataclass
class Extraction:
    form16s: list = field(default_factory=list)
    interest_certificates: list = field(default_factory=list)
    rent_receipts: list = field(default_factory=list)
    unreadable: list = field(default_factory=list)  # document names we could not use
    ais: dict = field(default_factory=dict)
    questionnaire: dict = field(default_factory=dict)
    broker_rows: list = field(default_factory=list)


def to_int(value, name):
    if isinstance(value, bool):
        raise ExtractionError(f"{name} is not a number")
    try:
        number = int(
            float(str(value).replace(",", "").replace("Rs.", "").replace("INR", "").strip())
        )
    except ValueError:
        raise ExtractionError(f"{name} is not a number: {value!r}") from None
    if number < 0:
        raise ExtractionError(f"{name} is negative")
    return number


def clean(raw: dict, fields: dict) -> dict:
    """Check the model's answer against the field list and coerce the types."""
    result = {}
    for name, (kind, _) in fields.items():
        value = raw.get(name)
        if kind == "int":
            result[name] = to_int(0 if value is None else value, name)
        elif kind == "bool":
            result[name] = bool(value)
        elif kind == "str_or_null":
            result[name] = str(value).strip().upper() if value else None
        else:
            if not value:
                raise ExtractionError(f"{name} is missing")
            result[name] = str(value).strip()
    return result


def ask(llm, doc, fields):
    listing = "\n".join(f'- "{name}" ({kind}): {hint}' for name, (kind, hint) in fields.items())
    prompt = f"Document text:\n\n{doc.text}\n\nReturn one JSON object with these fields:\n{listing}"
    return clean(llm.complete_json(SYSTEM, prompt), fields)


def read_form16(llm, doc):
    data = ask(llm, doc, FORM16_FIELDS)
    data["tan"], data["employee_pan"] = data["tan"].upper(), data["employee_pan"].upper()
    if not TAN.match(data["tan"]) or not PAN.match(data["employee_pan"]):
        raise ExtractionError("TAN or PAN is not in the expected format")
    return data


def run(llm, files: CaseFiles) -> Extraction:
    """Read every document. A document that cannot be read is recorded, not guessed."""
    out = Extraction(
        ais=files.ais or {}, questionnaire=files.questionnaire or {}, broker_rows=files.broker_rows
    )
    readers = {
        "form16": (out.form16s, read_form16),
        "interest_certificate": (
            out.interest_certificates,
            lambda m, d: ask(m, d, CERTIFICATE_FIELDS),
        ),
        "rent_receipts": (out.rent_receipts, lambda m, d: ask(m, d, RENT_FIELDS)),
    }
    for doc in files.documents:
        if doc.kind not in readers:
            out.unreadable.append(doc.name)
            continue
        target, reader = readers[doc.kind]
        try:
            target.append({**reader(llm, doc), "source": doc.name})
        except (ExtractionError, LLMError, ValueError):
            out.unreadable.append(doc.name)
    return out
