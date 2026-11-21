"""What the client receives: draft return data, a computation sheet and a short note."""

from agents.decide import Decision
from agents.reconcile import Facts


def rupees(amount: int) -> str:
    return f"Rs {amount:,}"


def itr_json(facts: Facts, decision: Decision) -> dict:
    """Draft return data. The layout is ours, not the official offline-utility schema."""
    c = decision.chosen
    return {
        "schema": "filed-draft-v1 (not the official ITR utility schema)",
        "form": decision.itr_form,
        "assessment_year": "2026-27",
        "regime": decision.regime,
        "taxpayer": {"name": facts.name, "pan": facts.pan, "age": facts.profile.age},
        "filing_date": facts.filing_date.isoformat(),
        "income": {
            "salary": c.salary_income,
            "house_property": c.house_property_income,
            "other_sources": c.other_income,
            "stcg_111a": facts.profile.stcg_111a,
            "ltcg_112a": facts.profile.ltcg_112a,
        },
        "deductions_chapter_via": c.deductions,
        "total_income": c.total_income,
        "tax": {
            "liability": c.tax_liability,
            "interest_234a": c.interest_234a,
            "interest_234b": c.interest_234b,
            "interest_234c": c.interest_234c,
            "fee_234f": c.fee_234f,
        },
        "taxes_paid": c.taxes_paid,
        "net_payable": c.net_payable,
    }


def computation_sheet(decision: Decision) -> str:
    rows = [
        ("Salary after exemptions", "salary_income"),
        ("House property", "house_property_income"),
        ("Other income", "other_income"),
        ("Deductions", "deductions"),
        ("Taxable income (excl. share gains)", "normal_income"),
        ("Tax on slabs", "slab_tax"),
        ("Rebate and marginal relief", None),
        ("Tax on share gains", "special_tax"),
        ("Cess", "cess"),
        ("Total tax", "tax_liability"),
        ("Tax already paid (TDS)", "taxes_paid"),
        ("Late fee and interest", None),
        ("Payable (negative = refund)", "net_payable"),
    ]
    names = list(decision.comparison)
    lines = [
        "| | " + " | ".join(n.title() + " regime" for n in names) + " |",
        "|---|" + "---|" * len(names),
    ]
    for label, attr in rows:
        cells = []
        for c in decision.comparison.values():
            if label.startswith("Rebate"):
                value = c.rebate + c.marginal_relief
            elif label.startswith("Late"):
                value = c.fee_234f + c.interest_234a + c.interest_234b + c.interest_234c
            else:
                value = getattr(c, attr)
            cells.append(rupees(value))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append(f"\nChosen: **{decision.regime} regime**, form **{decision.itr_form}**.")
    if decision.saving_vs_other:
        lines.append(f"It saves {rupees(decision.saving_vs_other)} compared with the other regime.")
    return "\n".join(lines)


def client_note(facts: Facts, decision: Decision, ready: bool) -> str:
    """A plain note with the numbers filled in by code, so the wording cannot change a figure."""
    c = decision.chosen
    first = facts.name.split()[0] if facts.name else "there"
    if c.net_payable > 0:
        outcome = f"you owe {rupees(c.net_payable)}"
    elif c.net_payable < 0:
        outcome = f"you get a refund of {rupees(-c.net_payable)}"
    else:
        outcome = "you owe nothing and no refund is due"
    lines = [
        f"Hi {first},",
        "",
        (
            f"We prepared your return for assessment year 2026-27 on form {decision.itr_form} "
            f"under the {decision.regime} regime. After tax already deducted, {outcome}."
        ),
    ]
    if decision.saving_vs_other:
        lines.append(
            f"This regime saves you {rupees(decision.saving_vs_other)} compared with the other one."
        )
    notes = [f.message for f in facts.flags if f.resolution in ("auto_fixed", "info")]
    if notes:
        lines += ["", "Things we found and handled:"] + [f"- {n}" for n in notes]
    pending = [f.message for f in facts.flags if f.resolution == "needs_human"]
    if pending or not ready:
        lines += ["", "Our tax expert is checking these before filing:"] + [
            f"- {p}" for p in pending
        ]
    else:
        lines += ["", "Your return is ready to file."]
    return "\n".join(lines)
