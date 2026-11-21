"""Chapter VI-A deductions."""

from taxengine import rules
from taxengine.models import Profile


def employer_nps_deduction(profile: Profile, regime: str) -> int:
    """s.80CCD(2): allowed in both regimes, capped as a share of basic + DA."""
    basic = sum(e.basic_da for e in profile.employers)
    paid = sum(e.employer_nps for e in profile.employers)
    if regime == "new":
        pct = rules.EMPLOYER_NPS_PCT_NEW
    elif profile.govt_employee:
        pct = rules.EMPLOYER_NPS_PCT_OLD_GOVT
    else:
        pct = rules.EMPLOYER_NPS_PCT_OLD_PRIVATE
    return min(paid, basic * pct // 100)


def interest_deduction(profile: Profile) -> int:
    """80TTB for seniors (savings and deposits), 80TTA otherwise (savings only)."""
    if profile.age >= 60:
        return min(profile.savings_interest + profile.deposit_interest, rules.LIMIT_80TTB)
    return min(profile.savings_interest, rules.LIMIT_80TTA)


def health_deduction(profile: Profile) -> int:
    d = profile.deductions
    self_limit = rules.LIMIT_80D_SENIOR if profile.age >= 60 else rules.LIMIT_80D_SELF
    parents_limit = rules.LIMIT_80D_SENIOR if d.parents_senior else rules.LIMIT_80D_SELF
    return min(d.health_self, self_limit) + min(d.health_parents, parents_limit)


def total_deductions(profile: Profile, regime: str, income_before_deductions: int) -> int:
    """Deductions for the regime, never more than the income they are set against."""
    total = employer_nps_deduction(profile, regime)
    if regime == "old":
        d = profile.deductions
        total += min(d.sec_80c, rules.LIMIT_80C)
        total += min(d.sec_80ccd_1b, rules.LIMIT_80CCD_1B)
        total += health_deduction(profile)
        total += interest_deduction(profile)
    return min(total, max(0, income_before_deductions))
