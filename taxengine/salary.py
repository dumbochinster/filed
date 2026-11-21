"""Income under the heads salary and house property."""

from taxengine import rules
from taxengine.models import Profile


def hra_exemption(profile: Profile) -> int:
    """s.10(13A): the least of three amounts, summed over employers."""
    hra = sum(e.hra_received for e in profile.employers)
    basic = sum(e.basic_da for e in profile.employers)
    if hra == 0 or profile.rent_paid == 0:
        return 0
    city_pct = rules.HRA_METRO_PCT if profile.metro else rules.HRA_NON_METRO_PCT
    rent_excess = profile.rent_paid - basic * rules.HRA_RENT_EXCESS_PCT // 100
    return max(0, min(hra, rent_excess, basic * city_pct // 100))


def salary_breakdown(profile: Profile, regime: str) -> dict:
    """Gross salary, exemptions and the resulting income from salary."""
    gross = sum(e.gross_salary for e in profile.employers)
    old = regime == "old"
    hra = hra_exemption(profile) if old else 0
    limit = rules.STANDARD_DEDUCTION_OLD if old else rules.STANDARD_DEDUCTION_NEW
    # The standard deduction is given once, however many employers there are.
    standard = min(limit, gross - hra) if gross else 0
    prof_tax = 0
    if old:
        prof_tax = min(
            sum(e.professional_tax for e in profile.employers), rules.PROFESSIONAL_TAX_CAP
        )
    income = max(0, gross - hra - standard - prof_tax)
    return {
        "gross_salary": gross,
        "hra_exemption": hra,
        "standard_deduction": standard,
        "professional_tax": prof_tax,
        "salary_income": income,
    }


def house_property_income(profile: Profile, regime: str) -> int:
    """Income (or loss) from the one house property we model."""
    prop = profile.house_property
    if prop is None:
        return 0
    old = regime == "old"
    if prop.kind == "self_occupied":
        # Interest on a self-occupied home can only be set off in the old regime.
        return -min(prop.loan_interest, rules.LIMIT_HOME_LOAN_INTEREST) if old else 0
    net_annual_value = prop.rent_received - prop.municipal_tax
    after_standard = (
        net_annual_value - net_annual_value * rules.HOUSE_PROPERTY_STANDARD_DEDUCTION_PCT // 100
    )
    income = after_standard - prop.loan_interest
    if income >= 0:
        return income
    # A let-out loss can be set off against other heads only in the old regime, up to 2 lakh.
    return max(income, -rules.LIMIT_HOME_LOAN_INTEREST) if old else 0
