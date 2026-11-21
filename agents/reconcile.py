"""Reconciliation: merge the documents into one set of facts and flag every disagreement."""

from dataclasses import dataclass, field
from datetime import date

from agents.documents import capital_gains
from agents.intake import PAN, Extraction
from taxengine import rules
from taxengine.models import Deductions, Employer, HouseProperty, Profile

RENT_PAN_LIMIT = 100_000  # landlord PAN is needed above this annual rent
TOLERANCE = 1  # rupees of rounding difference ignored when comparing amounts


@dataclass
class Flag:
    code: str
    message: str
    resolution: str  # "auto_fixed", "info" or "needs_human"
    evidence: list = field(default_factory=list)


@dataclass
class Facts:
    profile: Profile
    filing_date: date
    name: str
    pan: str
    flags: list


def drop_duplicates(form16s):
    """Two Form 16 with the same TAN, PAN and amounts are one document uploaded twice."""
    seen, unique, dropped = set(), [], []
    for f in form16s:
        key = (f["tan"], f["employee_pan"], f["gross_salary"], f["tds_deducted"])
        (dropped if key in seen else unique).append(f)
        seen.add(key)
    return unique, dropped


def build_employers(form16s, ais_tds, flags):
    employers = []
    for f in form16s:
        tds = f["tds_deducted"]
        deposited = ais_tds.get(f["tan"])
        if deposited is not None and abs(deposited - tds) > TOLERANCE:
            flags.append(
                Flag(
                    "TDS_MISMATCH",
                    f"{f['employer_name']} reports tax deducted of Rs {tds:,}, but the AIS shows only "
                    f"Rs {deposited:,} deposited. We claim the AIS amount; ask the employer to correct it.",
                    "auto_fixed",
                    [f["source"], "ais.json"],
                )
            )
            tds = deposited
        employers.append(
            Employer(
                f["employer_name"],
                f["gross_salary"],
                f["basic_da"],
                f["hra_received"],
                f["professional_tax"],
                f["employer_nps"],
                tds,
            )
        )
    return employers


def check_salary_against_ais(form16s, ais, flags):
    paid = {e["tan"]: e["amount_paid"] for e in ais.get("tds", []) if e.get("section") == "192"}
    for f in form16s:
        if f["tan"] in paid and abs(paid[f["tan"]] - f["gross_salary"]) > TOLERANCE:
            flags.append(
                Flag(
                    "SALARY_MISMATCH",
                    f"Salary on the {f['employer_name']} Form 16 (Rs {f['gross_salary']:,}) differs from "
                    f"the AIS (Rs {paid[f['tan']]:,}).",
                    "needs_human",
                    [f["source"], "ais.json"],
                )
            )


def interest_amounts(x: Extraction, flags):
    """Bank interest from certificates, cross-checked with the AIS."""
    ais = {"savings": 0, "deposit": 0}
    for row in x.ais.get("interest", []):
        ais[row["type"]] = ais.get(row["type"], 0) + row["amount"]
    if not x.interest_certificates:
        return ais["savings"], ais["deposit"]
    savings = sum(c["savings_interest"] for c in x.interest_certificates)
    deposit = sum(c["deposit_interest"] for c in x.interest_certificates)
    if abs(savings - ais["savings"]) > TOLERANCE or abs(deposit - ais["deposit"]) > TOLERANCE:
        flags.append(
            Flag(
                "INTEREST_MISMATCH",
                "The bank certificate and the AIS show different interest.",
                "needs_human",
                ["interest_certificate.pdf", "ais.json"],
            )
        )
    return savings, deposit


def rent_checks(x: Extraction, flags):
    rent = x.questionnaire.get("rent_paid_annual", 0)
    if not rent:
        return
    if not x.rent_receipts:
        flags.append(
            Flag(
                "RENT_PROOF_MISSING",
                "Rent is claimed but no rent receipts were uploaded.",
                "needs_human",
                ["questionnaire.json"],
            )
        )
        return
    receipt = x.rent_receipts[0]
    if abs(receipt["annual_rent"] - rent) > TOLERANCE:
        flags.append(
            Flag(
                "RENT_MISMATCH",
                "The rent on the receipts differs from the rent declared.",
                "needs_human",
                [receipt["source"], "questionnaire.json"],
            )
        )
    if rent > RENT_PAN_LIMIT and not (
        receipt["landlord_pan"] and PAN.match(receipt["landlord_pan"])
    ):
        flags.append(
            Flag(
                "HRA_NO_LANDLORD_PAN",
                f"Rent is Rs {rent:,} a year, so HRA needs the landlord's PAN, which is missing.",
                "needs_human",
                [receipt["source"]],
            )
        )


def out_of_scope_checks(x: Extraction, flags):
    if x.ais.get("sft"):
        flags.append(
            Flag(
                "UNEXPLAINED_SFT",
                "The AIS shows a large transaction (such as a property "
                "purchase) that the client has not explained.",
                "needs_human",
                ["ais.json"],
            )
        )
    if x.ais.get("vda"):
        flags.append(
            Flag(
                "VDA_TRADES",
                "The AIS shows crypto (virtual digital asset) transfers, which "
                "have their own tax rules.",
                "needs_human",
                ["ais.json"],
            )
        )
    if any(f["foreign_rsu"] for f in x.form16s) or x.questionnaire.get("foreign_assets"):
        flags.append(
            Flag(
                "FOREIGN_RSU",
                "Foreign shares or RSUs need Schedule FA, which is not covered.",
                "needs_human",
                [f["source"] for f in x.form16s if f["foreign_rsu"]],
            )
        )
    if x.ais.get("securities") and not x.broker_rows:
        flags.append(
            Flag(
                "CAPITAL_GAINS_MISSING",
                "The AIS shows share sales but no broker statement was uploaded.",
                "needs_human",
                ["ais.json"],
            )
        )
    if x.questionnaire.get("residency", "resident") != "resident":
        flags.append(
            Flag(
                "NON_RESIDENT",
                "Only resident individuals are covered.",
                "needs_human",
                ["questionnaire.json"],
            )
        )
    for name in x.unreadable:
        flags.append(
            Flag(
                "UNREADABLE_DOCUMENT", f"{name} could not be read reliably.", "needs_human", [name]
            )
        )
    if not x.form16s:
        flags.append(Flag("NO_FORM16", "No readable Form 16 was found.", "needs_human", []))


def reconcile(x: Extraction) -> Facts:
    flags = []
    form16s, duplicates = drop_duplicates(x.form16s)
    for dup in duplicates:
        flags.append(
            Flag(
                "DUPLICATE_DOCUMENT",
                f"{dup['source']} is a second copy of a Form 16 already provided; counted once.",
                "auto_fixed",
                [dup["source"]],
            )
        )
    if len(form16s) > 1:
        flags.append(
            Flag(
                "TWO_EMPLOYERS",
                "Salary from more than one employer: it is combined and the "
                "standard deduction is taken once, so some extra tax may be due.",
                "info",
                [f["source"] for f in form16s],
            )
        )

    ais_tds = {
        e["tan"]: e["tds_deposited"] for e in x.ais.get("tds", []) if e.get("section") == "192"
    }
    employers = build_employers(form16s, ais_tds, flags)
    check_salary_against_ais(form16s, x.ais, flags)

    savings, deposit = interest_amounts(x, flags)
    if savings + deposit > x.questionnaire.get("declared_interest_income", 0) + TOLERANCE:
        flags.append(
            Flag(
                "AIS_INTEREST_MISSING",
                f"Interest of Rs {savings + deposit:,} appears in the AIS "
                "but was not declared; it is included.",
                "auto_fixed",
                ["ais.json"],
            )
        )
    dividends = sum(row["amount"] for row in x.ais.get("dividends", []))
    if dividends > x.questionnaire.get("declared_dividend_income", 0) + TOLERANCE:
        flags.append(
            Flag(
                "DIVIDEND_UNREPORTED",
                f"Dividends of Rs {dividends:,} appear in the AIS but were "
                "not declared; they are included.",
                "auto_fixed",
                ["ais.json"],
            )
        )

    rent_checks(x, flags)
    out_of_scope_checks(x, flags)

    filing_date = date.fromisoformat(x.questionnaire.get("filing_date", rules.DUE_DATE.isoformat()))
    if filing_date > rules.DUE_DATE:
        flags.append(
            Flag(
                "BELATED_FORCED_NEW",
                "Filed after 31 July, so only the new regime is available "
                "and a late fee and interest apply.",
                "info",
                ["questionnaire.json"],
            )
        )

    stcg, ltcg = capital_gains(x.broker_rows)
    q = x.questionnaire
    loan = q.get("home_loan_interest", 0)
    profile = Profile(
        age=q.get("age", 30),
        employers=tuple(employers),
        savings_interest=savings,
        deposit_interest=deposit,
        dividends=dividends,
        house_property=HouseProperty("self_occupied", loan_interest=loan) if loan else None,
        stcg_111a=stcg,
        ltcg_112a=ltcg,
        deductions=Deductions(
            sec_80c=sum(f["sec_80c"] for f in form16s),
            sec_80ccd_1b=sum(f["sec_80ccd_1b"] for f in form16s),
            health_self=sum(f["health_self"] for f in form16s),
            health_parents=q.get("health_insurance_parents", 0),
            parents_senior=q.get("parents_senior", False),
        ),
        rent_paid=q.get("rent_paid_annual", 0),
        metro=q.get("metro_city", False),
    )
    return Facts(profile, filing_date, q.get("name", ""), q.get("pan", ""), flags)
