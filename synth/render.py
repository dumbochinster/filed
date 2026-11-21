"""Turns a CaseSpec into the files a client would upload."""

import csv
import json
from pathlib import Path

from fpdf import FPDF

# Three employer layouts: different words, different number styles.
FORM16_LAYOUTS = [
    {
        "title": "FORM NO. 16 - PART B",
        "gross": "Gross salary",
        "basic": "Basic salary and DA",
        "hra": "House rent allowance received",
        "pt": "Tax on employment (professional tax)",
        "nps": "Employer contribution to NPS",
        "c80": "Deduction u/s 80C",
        "c80ccd": "Deduction u/s 80CCD(1B)",
        "d80": "Deduction u/s 80D",
        "tds": "Total tax deducted at source",
        "rsu": "Perquisite on RSUs granted by foreign parent company",
        "style": "rs",
    },
    {
        "title": "CERTIFICATE UNDER SECTION 203 (FORM 16)",
        "gross": "Total salary u/s 17(1)",
        "basic": "Basic + dearness allowance",
        "hra": "HRA component",
        "pt": "Professional tax paid",
        "nps": "NPS - employer share",
        "c80": "Chapter VI-A: 80C",
        "c80ccd": "Chapter VI-A: 80CCD(1B)",
        "d80": "Chapter VI-A: 80D",
        "tds": "TDS deposited",
        "rsu": "Foreign RSU perquisite (parent company)",
        "style": "plain",
    },
    {
        "title": "Form 16 Salary Statement",
        "gross": "Gross taxable salary",
        "basic": "Basic/DA",
        "hra": "HRA paid",
        "pt": "PT",
        "nps": "Employer NPS",
        "c80": "80C investments",
        "c80ccd": "80CCD(1B) NPS",
        "d80": "80D mediclaim",
        "tds": "Income tax deducted",
        "rsu": "RSU perquisite from overseas parent",
        "style": "inr",
    },
]


def indian(amount):
    """12345678 -> '1,23,45,678'."""
    digits = str(abs(int(amount)))
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join(groups + [tail]) if groups else tail
    return ("-" if amount < 0 else "") + text


def money(amount, style):
    if style == "rs":
        return f"Rs. {indian(amount)}"
    if style == "inr":
        return f"INR {int(amount)}"
    return f"{indian(amount)}.00"


def write_pdf(path, lines):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def form16(spec, i):
    """Returns the PDF lines and the fields a perfect reader would extract."""
    layout = FORM16_LAYOUTS[(int(spec.case_id[-3:]) + i) % len(FORM16_LAYOUTS)]
    e = spec.employers[i]
    d = spec.deductions if i == 0 else None
    fields = {
        "employer_name": e.name,
        "tan": spec.tans[i],
        "employee_pan": spec.pan,
        "gross_salary": e.gross_salary,
        "basic_da": e.basic_da,
        "hra_received": e.hra_received,
        "professional_tax": e.professional_tax,
        "employer_nps": e.employer_nps,
        "tds_deducted": spec.form16_tds[i],
        "sec_80c": d.sec_80c if d else 0,
        "sec_80ccd_1b": d.sec_80ccd_1b if d else 0,
        "health_self": d.health_self if d else 0,
        "foreign_rsu": bool(spec.foreign_rsu and i == 0),
    }
    style = layout["style"]
    rows = [
        (layout[k], fields[f])
        for k, f in [
            ("gross", "gross_salary"),
            ("basic", "basic_da"),
            ("hra", "hra_received"),
            ("pt", "professional_tax"),
            ("nps", "employer_nps"),
            ("c80", "sec_80c"),
            ("c80ccd", "sec_80ccd_1b"),
            ("d80", "health_self"),
            ("tds", "tds_deducted"),
        ]
    ]
    lines = [
        layout["title"],
        "Assessment year 2026-27 (financial year 2025-26)",
        "",
        f"Employer: {e.name}",
        f"TAN of deductor: {spec.tans[i]}",
        f"Employee: {spec.name}",
        f"PAN of employee: {spec.pan}",
        "",
    ]
    lines += [f"{label}: {money(value, style)}" for label, value in rows]
    if fields["foreign_rsu"]:
        lines.append(f"{layout['rsu']}: {money(round(e.gross_salary * 0.1, -3), style)}")
    return lines, fields


def interest_certificate(spec):
    fields = {
        "bank": spec.bank,
        "savings_interest": spec.savings_interest,
        "deposit_interest": spec.deposit_interest,
    }
    lines = [
        f"{spec.bank} - Interest Certificate",
        "Financial year 2025-26",
        "",
        f"Account holder: {spec.name}",
        f"PAN: {spec.pan}",
        f"Interest on savings account: Rs. {indian(spec.savings_interest)}",
        f"Interest on fixed deposits: Rs. {indian(spec.deposit_interest)}",
    ]
    return lines, fields


def rent_receipt(spec):
    monthly = spec.rent_paid // 12
    pan = spec.landlord_pan or "not provided"
    fields = {
        "landlord_name": spec.landlord_name,
        "landlord_pan": spec.landlord_pan,
        "annual_rent": spec.rent_paid,
    }
    lines = [
        "Rent Receipts",
        f"Tenant: {spec.name} (PAN {spec.pan})",
        "",
        f"Received rent of Rs. {indian(monthly)} per month for 12 months of FY 2025-26.",
        f"Total rent paid: Rs. {indian(spec.rent_paid)}",
        f"Landlord: {spec.landlord_name}",
        f"Landlord PAN: {pan}",
    ]
    return lines, fields


def ais(spec):
    data = {
        "pan": spec.pan,
        "assessment_year": "2026-27",
        "tds": [],
        "interest": [],
        "dividends": [],
        "securities": [],
        "sft": [],
        "vda": [],
    }
    for e, tan in zip(spec.employers, spec.tans):
        data["tds"].append(
            {
                "deductor": e.name,
                "tan": tan,
                "section": "192",
                "amount_paid": e.gross_salary,
                "tds_deposited": e.tds,
            }
        )
    if spec.savings_interest:
        data["interest"].append(
            {"source": spec.bank, "type": "savings", "amount": spec.savings_interest}
        )
    if spec.deposit_interest:
        data["interest"].append(
            {"source": spec.bank, "type": "deposit", "amount": spec.deposit_interest}
        )
    if spec.dividends:
        data["dividends"].append({"source": "Listed company dividends", "amount": spec.dividends})
    if spec.trades:
        data["securities"].append(
            {
                "description": "Sale of listed securities",
                "amount": sum(t.sell_value for t in spec.trades),
            }
        )
    if spec.property_purchase:
        data["sft"].append(
            {"type": "immovable property purchase", "amount": spec.property_purchase}
        )
    if spec.vda_amount:
        data["vda"].append(
            {"description": "Transfer of virtual digital assets", "amount": spec.vda_amount}
        )
    return data


def questionnaire(spec):
    return {
        "name": spec.name,
        "pan": spec.pan,
        "age": spec.age,
        "residency": "resident",
        "metro_city": spec.metro,
        "rent_paid_annual": spec.rent_paid,
        "parents_senior": spec.deductions.parents_senior,
        "health_insurance_parents": spec.deductions.health_parents,
        "home_loan_interest": spec.home_loan_interest,
        "declared_interest_income": spec.declared_interest,
        "declared_dividend_income": spec.declared_dividends,
        "filing_date": spec.filing_date.isoformat(),
    }


def render_case(spec, folder):
    """Write all documents of the case. Returns the oracle extractions (for tests only)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    oracle = []
    for i in range(len(spec.employers)):
        lines, fields = form16(spec, i)
        write_pdf(folder / f"form16_{i + 1}.pdf", lines)
        oracle.append({"keys": [spec.pan, spec.tans[i]], "fields": fields})
        if i == 0 and spec.duplicate_form16:
            write_pdf(folder / "form16_1_copy.pdf", lines)
    if spec.savings_interest or spec.deposit_interest:
        lines, fields = interest_certificate(spec)
        write_pdf(folder / "interest_certificate.pdf", lines)
        oracle.append({"keys": [spec.pan, "Interest Certificate"], "fields": fields})
    if spec.rent_paid:
        lines, fields = rent_receipt(spec)
        write_pdf(folder / "rent_receipts.pdf", lines)
        oracle.append({"keys": [spec.pan, "Rent Receipts"], "fields": fields})
    (folder / "ais.json").write_text(json.dumps(ais(spec), indent=2), encoding="utf-8")
    (folder / "questionnaire.json").write_text(
        json.dumps(questionnaire(spec), indent=2), encoding="utf-8"
    )
    if spec.trades:
        with open(folder / "broker_statement.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["symbol", "qty", "buy_date", "sell_date", "buy_value", "sell_value"])
            for t in spec.trades:
                writer.writerow(
                    [t.symbol, t.qty, t.buy_date, t.sell_date, t.buy_value, t.sell_value]
                )
    return oracle
