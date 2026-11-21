"""Reviewer: a second model pass that looks for contradictions between the evidence and the draft."""

import json
from dataclasses import asdict

from agents.decide import Decision
from agents.llm import LLMError
from agents.reconcile import Facts, Flag

SYSTEM = (
    "You review a draft Indian income-tax return before it is filed. You are given the facts "
    "taken from the client's documents, the issues already flagged, and the computed result. "
    "Report only concrete contradictions or impossible values in this data (for example a "
    "deduction larger than the income, or an age that does not fit the claims). Do not recompute "
    "tax and do not raise issues that are already flagged. If you find nothing, return an empty "
    'list. Reply as JSON: {"concerns": [{"message": "...", "severity": "high" or "low"}]}.'
)


def summary(facts: Facts, decision: Decision) -> str:
    chosen = decision.chosen
    data = {
        "age": facts.profile.age,
        "profile": asdict(facts.profile),
        "already_flagged": [f.code for f in facts.flags],
        "itr_form": decision.itr_form,
        "regime": decision.regime,
        "total_income": chosen.total_income,
        "tax_liability": chosen.tax_liability,
        "taxes_paid": chosen.taxes_paid,
        "net_payable": chosen.net_payable,
    }
    return json.dumps(data, default=str, indent=1)


def review(llm, facts: Facts, decision: Decision) -> list:
    """Adds a flag for each concern. A reviewer that fails to answer is skipped, not trusted."""
    try:
        answer = llm.complete_json(SYSTEM, summary(facts, decision))
    except LLMError:
        return []
    added = []
    concerns = answer.get("concerns", []) if isinstance(answer, dict) else []
    for concern in concerns if isinstance(concerns, list) else []:
        # Smaller models sometimes answer with plain strings; treat those as low severity.
        if isinstance(concern, str):
            concern = {"message": concern, "severity": "low"}
        if not isinstance(concern, dict):
            continue
        message = str(concern.get("message", "")).strip()
        if not message:
            continue
        high = concern.get("severity") == "high"
        flag = Flag("REVIEWER_CONCERN", message, "needs_human" if high else "info")
        facts.flags.append(flag)
        added.append(flag)
    return added
