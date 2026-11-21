"""Tax computation for one regime, and the old-versus-new comparison."""

from datetime import date

from taxengine import capital_gains, deductions, interest, rules
from taxengine.models import Computation, Profile, UnsupportedProfile
from taxengine.money import round_to_10
from taxengine.salary import house_property_income, salary_breakdown


def slab_tax(income: int, slabs: list) -> int:
    tax = 0
    lower = 0
    for upper, pct in slabs:
        top = income if upper is None else min(income, upper)
        if top > lower:
            tax += (top - lower) * pct // 100
        if upper is None or income <= upper:
            break
        lower = upper
    return tax


def slabs_for(profile: Profile, regime: str) -> list:
    if regime == "new":
        return rules.NEW_REGIME_SLABS
    return rules.OLD_REGIME_SLABS[profile.age_group]


def basic_exemption(profile: Profile, regime: str) -> int:
    return slabs_for(profile, regime)[0][0]


def rebate_and_relief(normal_income: int, tax: int, regime: str) -> tuple[int, int]:
    """s.87A rebate, and marginal relief just above the new-regime limit."""
    if regime == "new":
        if normal_income <= rules.REBATE_LIMIT_NEW:
            return min(tax, rules.REBATE_MAX_NEW), 0
        return 0, max(0, tax - (normal_income - rules.REBATE_LIMIT_NEW))
    if normal_income <= rules.REBATE_LIMIT_OLD:
        return min(tax, rules.REBATE_MAX_OLD), 0
    return 0, 0


def compute(profile: Profile, regime: str, filing_date: date = rules.DUE_DATE) -> Computation:
    if regime not in ("old", "new"):
        raise ValueError("regime must be 'old' or 'new'")
    if regime == "old" and filing_date > rules.DUE_DATE:
        raise UnsupportedProfile("the old regime cannot be chosen in a belated return")
    if profile.advance_tax:
        raise UnsupportedProfile("advance-tax payments need their dates checked by a person")

    result = Computation(regime=regime, filing_date=filing_date)
    salary = salary_breakdown(profile, regime)
    for name, value in salary.items():
        setattr(result, name, value)
    result.house_property_income = house_property_income(profile, regime)
    result.other_income = profile.savings_interest + profile.deposit_interest + profile.dividends

    before_deductions = max(
        0, result.salary_income + result.house_property_income + result.other_income
    )
    result.deductions = deductions.total_deductions(profile, regime, before_deductions)
    result.normal_income = before_deductions - result.deductions

    # Gains: unused basic exemption can shelter them, the 1.25 lakh exemption is applied first.
    shortfall = max(0, basic_exemption(profile, regime) - result.normal_income)
    result.stcg_taxable, result.ltcg_taxable = capital_gains.taxable_gains(
        profile.stcg_111a, profile.ltcg_112a, shortfall
    )
    ltcg_after_exemption = max(0, profile.ltcg_112a - rules.LTCG_112A_EXEMPTION)
    result.total_income = result.normal_income + profile.stcg_111a + ltcg_after_exemption
    if result.total_income > rules.SURCHARGE_THRESHOLD:
        raise UnsupportedProfile("income above 50 lakh attracts surcharge, which is not modelled")

    result.slab_tax = slab_tax(result.normal_income, slabs_for(profile, regime))
    result.rebate, result.marginal_relief = rebate_and_relief(
        result.normal_income, result.slab_tax, regime
    )
    result.special_tax = capital_gains.special_rate_tax(result.stcg_taxable, result.ltcg_taxable)
    tax = result.slab_tax - result.rebate - result.marginal_relief + result.special_tax
    result.cess = (tax * rules.CESS_PCT + 50) // 100
    result.tax_liability = round_to_10(tax + result.cess)

    result.taxes_paid = profile.total_tds
    unpaid = result.tax_liability - result.taxes_paid
    result.fee_234f = interest.fee_234f(
        result.total_income, filing_date, basic_exemption(profile, regime)
    )
    result.interest_234a = interest.interest_234a(unpaid, filing_date)
    result.interest_234b = interest.interest_234b(unpaid, filing_date)
    result.interest_234c = interest.interest_234c(unpaid)
    if result.interest_234c and (profile.stcg_111a or profile.ltcg_112a or profile.dividends):
        result.notes.append(
            "234C was charged as if all income arose early; gains and dividends that arose "
            "late in the year may reduce it"
        )
    extras = result.interest_234a + result.interest_234b + result.interest_234c + result.fee_234f
    result.net_payable = round_to_10(result.tax_liability + extras - result.taxes_paid)
    return result


def compare_regimes(profile: Profile, filing_date: date = rules.DUE_DATE) -> dict:
    """Both regimes where allowed. The old regime is not open in a belated return."""
    results = {"new": compute(profile, "new", filing_date)}
    if filing_date <= rules.DUE_DATE:
        results["old"] = compute(profile, "old", filing_date)
    return results


def cheaper_regime(results: dict) -> str:
    """The regime with the lower net payable; the new regime wins a tie."""
    best = "new"
    if "old" in results and results["old"].net_payable < results["new"].net_payable:
        best = "old"
    return best
