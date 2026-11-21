"""Runs one client case through every step and records what happened."""

import json
import sys
import time
from dataclasses import asdict, dataclass, field

from agents import deliver, escalate, intake, review
from agents.decide import decide
from agents.documents import load_case
from agents.reconcile import reconcile


@dataclass
class CaseResult:
    case_id: str
    status: str  # "ready_to_file" or "needs_human"
    itr_form: str | None = None
    regime: str | None = None
    tax_liability: int | None = None
    net_payable: int | None = None
    flags: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    events: list = field(default_factory=list)
    computation_sheet: str = ""
    itr_json: dict = field(default_factory=dict)
    client_note: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    llm_calls: int = 0
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def run_case(folder, llm, on_event=None, reviewer="off") -> CaseResult:
    """Intake, reconcile, decide, review, escalate, deliver. `on_event(step, message)` is optional.

    reviewer: "off" skips the model reviewer, "advisory" adds its concerns as notes only,
    "gate" lets a high-severity concern send the case to the expert.
    """
    started = time.time()
    before = (llm.tokens_in, llm.tokens_out, llm.calls)
    events = []

    def log(step, message):
        events.append({"step": step, "message": message, "time": round(time.time() - started, 2)})
        if on_event:
            on_event(step, message)

    files = load_case(folder)
    log("intake", f"Reading {len(files.documents)} documents and the structured files")
    extraction = intake.run(llm, files)
    log(
        "intake",
        f"Read {len(extraction.form16s)} Form 16, {len(extraction.interest_certificates)} "
        f"interest certificate(s), {len(extraction.rent_receipts)} rent receipt(s)",
    )

    facts = reconcile(extraction)
    for flag in facts.flags:
        log("reconcile", f"{flag.code}: {flag.message}")
    if not facts.flags:
        log("reconcile", "Documents agree with each other")

    decision = decide(facts)
    if decision:
        log(
            "decide",
            f"{decision.itr_form}, {decision.regime} regime; "
            f"net payable Rs {decision.chosen.net_payable:,}",
        )
        if reviewer != "off":
            for flag in review.review(llm, facts, decision, gate=reviewer == "gate"):
                log("review", f"{flag.resolution}: {flag.message}")
            log("review", "Reviewer finished")
    else:
        log("decide", "The tax engine cannot handle this case; sending it to an expert")

    queue = escalate.build_queue(facts.flags)
    status = "needs_human" if queue else "ready_to_file"
    log(
        "escalate",
        f"{len(queue)} question(s) for the tax expert" if queue else "Nothing needs a person",
    )

    result = CaseResult(
        case_id=files.folder.name,
        status=status,
        events=events,
        flags=[asdict(f) for f in facts.flags],
        questions=[asdict(q) for q in queue],
    )
    if decision:
        result.itr_form, result.regime = decision.itr_form, decision.regime
        result.tax_liability, result.net_payable = (
            decision.chosen.tax_liability,
            decision.chosen.net_payable,
        )
        result.computation_sheet = deliver.computation_sheet(decision)
        result.itr_json = deliver.itr_json(facts, decision)
        result.client_note = deliver.client_note(facts, decision, status == "ready_to_file")
    log(
        "deliver",
        "Return, computation sheet and client note prepared" if decision else "No draft produced",
    )

    result.tokens_in = llm.tokens_in - before[0]
    result.tokens_out = llm.tokens_out - before[1]
    result.llm_calls = llm.calls - before[2]
    result.seconds = round(time.time() - started, 2)
    return result


def main():
    from agents.llm import make_client

    if len(sys.argv) != 2:
        sys.exit("usage: python -m agents.pipeline <case folder>")
    result = run_case(sys.argv[1], make_client(cache_dir="runs/cache"))
    print(json.dumps(result.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
