"""Tax on listed-equity capital gains (s.111A and s.112A)."""

from taxengine import rules


def taxable_gains(stcg: int, ltcg: int, basic_exemption_shortfall: int = 0) -> tuple[int, int]:
    """Amounts that actually attract tax: (stcg, ltcg).

    A resident whose other income falls short of the basic exemption can use the unused part
    against these gains. We apply it to short-term gains first, then long-term.
    """
    ltcg = max(0, ltcg - rules.LTCG_112A_EXEMPTION)
    use = min(basic_exemption_shortfall, stcg)
    stcg -= use
    ltcg -= min(basic_exemption_shortfall - use, ltcg)
    return stcg, ltcg


def special_rate_tax(stcg_taxable: int, ltcg_taxable: int) -> int:
    short_term = stcg_taxable * rules.STCG_111A_PCT // 100
    long_term = ltcg_taxable * rules.LTCG_112A_PCT_TIMES_10 // 1000
    return short_term + long_term
