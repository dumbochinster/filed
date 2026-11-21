"""Which return form the taxpayer has to use."""

from taxengine import rules
from taxengine.models import Profile


def choose_itr_form(profile: Profile) -> tuple[str, list[str]]:
    """Returns ("ITR-1" or "ITR-2", the reasons it cannot be ITR-1)."""
    reasons = []
    if profile.stcg_111a > 0:
        reasons.append("short-term capital gains need ITR-2")
    if profile.ltcg_112a > rules.LTCG_112A_EXEMPTION:
        reasons.append("long-term capital gains above 1,25,000 need ITR-2")
    return ("ITR-2" if reasons else "ITR-1"), reasons
