"""Scoring a system's output against the known correct answer."""

from statistics import mean, pstdev

TOLERANCE = 10  # rupees: how close the final figure must be to count as exact


def score_case(result: dict, truth: dict) -> dict:
    """Facts about one run on one case. Everything else is computed from these."""
    expected = truth["expected"]
    ready_truth = expected["status"] == "ready_to_file"
    predicted_ready = result["status"] == "ready_to_file"
    has_figures = result.get("net_payable") is not None
    error = (
        abs(result["net_payable"] - expected["net_payable"])
        if ready_truth and has_figures
        else None
    )
    form_ok = ready_truth and result.get("itr_form") == expected["itr_form"]
    regime_ok = ready_truth and result.get("regime") == expected["regime"]
    exact = bool(ready_truth and form_ok and regime_ok and error is not None and error <= TOLERANCE)
    # A trap counts as handled when the outcome is right: escalated if a person is needed,
    # an exact return otherwise.
    handled = (not predicted_ready) if not ready_truth else exact
    return {
        "case_id": truth["case_id"],
        "traps": truth["traps"],
        "truth_ready": ready_truth,
        "predicted_ready": predicted_ready,
        "predicted_human": result["status"] == "needs_human",
        "exact": exact,
        "form_ok": form_ok,
        "regime_ok": regime_ok,
        "error": error,
        "false_automation": predicted_ready and not (ready_truth and exact),
        "handled": handled,
        "tokens": result.get("tokens_in", 0) + result.get("tokens_out", 0),
        "calls": result.get("llm_calls", 0),
        "seconds": result.get("seconds", 0.0),
    }


def rate(numerator: int, denominator: int):
    return numerator / denominator if denominator else None


def summarise(scores: list) -> dict:
    """Metrics over all cases of one repeat."""
    ready = [s for s in scores if s["truth_ready"]]
    human = [s for s in scores if not s["truth_ready"]]
    predicted_ready = [s for s in scores if s["predicted_ready"]]
    predicted_human = [s for s in scores if s["predicted_human"]]
    errors = [s["error"] for s in ready if s["error"] is not None]
    return {
        "exact_return_rate": rate(sum(s["exact"] for s in ready), len(ready)),
        "form_accuracy": rate(sum(s["form_ok"] for s in ready), len(ready)),
        "regime_accuracy": rate(sum(s["regime_ok"] for s in ready), len(ready)),
        "mean_abs_error_rupees": mean(errors) if errors else None,
        "escalation_recall": rate(sum(s["predicted_human"] for s in human), len(human)),
        "escalation_precision": rate(
            sum(not s["truth_ready"] for s in predicted_human), len(predicted_human)
        ),
        "false_automation_rate": rate(
            sum(s["false_automation"] for s in predicted_ready), len(predicted_ready)
        ),
        "hands_off_rate": rate(
            sum(s["predicted_ready"] and s["exact"] for s in scores), len(scores)
        ),
        "tokens_per_case": mean(s["tokens"] for s in scores),
        "seconds_per_case": mean(s["seconds"] for s in scores),
    }


def across_repeats(per_repeat: list) -> dict:
    """Mean and standard deviation of each metric over the repeats."""
    out = {}
    for key in per_repeat[0]:
        values = [r[key] for r in per_repeat if r[key] is not None]
        out[key] = (mean(values), pstdev(values)) if values else (None, None)
    return out


def trap_table(scores_by_repeat: list) -> dict:
    """For each trap: (times handled, times it appeared), pooled over repeats."""
    table = {}
    for scores in scores_by_repeat:
        for s in scores:
            for trap in s["traps"]:
                done, total = table.get(trap, (0, 0))
                table[trap] = (done + s["handled"], total + 1)
    return table
