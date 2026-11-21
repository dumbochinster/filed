"""The baseline: put every document into one prompt and ask the model for the answer."""

import json
import time

from agents.documents import load_case
from agents.llm import LLMError
from agents.pipeline import CaseResult

SYSTEM = (
    "You are an experienced Indian chartered accountant. You are given all the documents of one "
    "salaried client for assessment year 2026-27 (financial year 2025-26). Work out which return "
    "form applies (ITR-1 or ITR-2), whether the old or the new tax regime is cheaper, and the "
    "final tax payable after tax already deducted. Reply as JSON with these fields: "
    '"itr_form" ("ITR-1" or "ITR-2"), "regime" ("old" or "new"), "net_payable" (whole rupees; '
    'positive if the client must pay, negative for a refund), "needs_human" (true if any part of '
    'the case should be checked by a tax expert before filing), "reason" (one sentence).'
)


def build_prompt(folder) -> str:
    files = load_case(folder)
    parts = [f"--- {doc.name} ---\n{doc.text}" for doc in files.documents]
    parts.append("--- ais.json ---\n" + json.dumps(files.ais, indent=1))
    parts.append("--- questionnaire.json ---\n" + json.dumps(files.questionnaire, indent=1))
    if files.broker_rows:
        parts.append("--- broker_statement.csv ---\n" + json.dumps(files.broker_rows))
    return "\n\n".join(parts)


def run_case(folder, llm) -> CaseResult:
    started = time.time()
    before = (llm.tokens_in, llm.tokens_out, llm.calls)
    result = CaseResult(case_id=folder.name, status="needs_human")
    try:
        answer = llm.complete_json(SYSTEM, build_prompt(folder))
        result.itr_form = answer.get("itr_form")
        result.regime = answer.get("regime")
        result.net_payable = int(float(answer["net_payable"]))
        result.status = "needs_human" if answer.get("needs_human") else "ready_to_file"
    except (LLMError, KeyError, TypeError, ValueError):
        # An unusable answer counts as the baseline failing to produce a return.
        result.status = "no_answer"
    result.tokens_in = llm.tokens_in - before[0]
    result.tokens_out = llm.tokens_out - before[1]
    result.llm_calls = llm.calls - before[2]
    result.seconds = round(time.time() - started, 2)
    return result
