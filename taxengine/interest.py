"""Late-filing fee (s.234F) and interest (s.234A, 234B, 234C)."""

from datetime import date

from taxengine import rules
from taxengine.money import round_down_to_100


def months_late(filing_date: date, due_date: date = rules.DUE_DATE) -> int:
    """Months or part of a month between the due date and the filing date."""
    if filing_date <= due_date:
        return 0
    months = (filing_date.year - due_date.year) * 12 + filing_date.month - due_date.month
    return months + (1 if filing_date.day > due_date.day else 0)


def fee_234f(total_income: int, filing_date: date, basic_exemption: int) -> int:
    if filing_date <= rules.DUE_DATE or total_income <= basic_exemption:
        return 0
    if total_income <= rules.FEE_234F_LOW_INCOME_LIMIT:
        return rules.FEE_234F_LOW
    return rules.FEE_234F_HIGH


def interest_234a(unpaid_tax: int, filing_date: date) -> int:
    """1% a month on the tax still unpaid at the due date."""
    if unpaid_tax <= 0:
        return 0
    return round_down_to_100(unpaid_tax) * months_late(filing_date) // 100


def interest_234b(unpaid_tax: int, filing_date: date) -> int:
    """1% a month from 1 April of the assessment year to the filing month, no advance tax paid."""
    if unpaid_tax < rules.INTEREST_THRESHOLD:
        return 0
    start = rules.ASSESSMENT_YEAR_START
    months = (filing_date.year - start.year) * 12 + filing_date.month - start.month + 1
    return round_down_to_100(unpaid_tax) * max(0, months) // 100


def interest_234c(unpaid_tax: int) -> int:
    """1% a month on each instalment of advance tax that was due but not paid."""
    if unpaid_tax < rules.INTEREST_THRESHOLD:
        return 0
    weighted = sum(pct * months for pct, months in rules.INSTALMENTS_234C)
    return round_down_to_100(unpaid_tax) * weighted // 10_000
