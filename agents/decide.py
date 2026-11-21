"""Decide the return form and the tax regime, using the tax engine for every number."""

from dataclasses import dataclass

from agents.reconcile import Facts, Flag
from taxengine.compute import cheaper_regime, compare_regimes
from taxengine.forms import choose_itr_form
from taxengine.models import UnsupportedProfile


@dataclass
class Decision:
    itr_form: str
    form_reasons: list
    regime: str
    comparison: dict  # regime name -> Computation

    @property
    def chosen(self):
        return self.comparison[self.regime]

    @property
    def saving_vs_other(self) -> int:
        """Rupees saved by the chosen regime compared with the other one (0 if only one is open)."""
        others = [c.net_payable for name, c in self.comparison.items() if name != self.regime]
        return max(0, others[0] - self.chosen.net_payable) if others else 0


def decide(facts: Facts) -> Decision | None:
    """Returns None, with a flag added to the facts, when the engine cannot handle the case."""
    try:
        comparison = compare_regimes(facts.profile, facts.filing_date)
    except UnsupportedProfile as problem:
        facts.flags.append(Flag(problem.code, str(problem), "needs_human"))
        return None
    form, reasons = choose_itr_form(facts.profile)
    return Decision(form, reasons, cheaper_regime(comparison), comparison)
