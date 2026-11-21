"""Turns the flags that need a person into short questions for the tax expert."""

from dataclasses import dataclass

QUESTIONS = {
    "HRA_NO_LANDLORD_PAN": "Rent is above Rs 1 lakh a year and the landlord's PAN is missing. Can the client "
    "get it, or should HRA be dropped?",
    "UNEXPLAINED_SFT": "The AIS shows a large transaction (e.g. property purchase). What was it, and does "
    "it change the return?",
    "INCOME_OVER_50L": "Income is above Rs 50 lakh, so surcharge applies. Please prepare this return by hand.",
    "FOREIGN_RSU": "The client holds foreign RSUs or shares. Please handle Schedule FA and foreign income.",
    "VDA_TRADES": "The AIS shows crypto transfers. Are these business income or capital gains?",
    "SALARY_MISMATCH": "Form 16 salary differs from the AIS. Which one is right?",
    "INTEREST_MISMATCH": "The bank certificate and the AIS show different interest. Which one is right?",
    "RENT_MISMATCH": "Rent on the receipts differs from the rent declared. Which one is right?",
    "RENT_PROOF_MISSING": "HRA is claimed without rent receipts. Ask the client for them or drop HRA.",
    "CAPITAL_GAINS_MISSING": "The AIS shows share sales but there is no broker statement. Please ask for it.",
    "UNREADABLE_DOCUMENT": "A document could not be read reliably. Please check it by eye.",
    "NO_FORM16": "No readable Form 16 was provided. Please ask the client for one.",
    "NON_RESIDENT": "The client is not a resident individual. Please prepare this return by hand.",
    "ADVANCE_TAX": "Advance tax was paid. Please check the challan dates for interest.",
    "REVIEWER_CONCERN": "The reviewer raised a concern about the draft.",
}


@dataclass
class Question:
    code: str
    question: str
    detail: str
    evidence: list


def build_queue(flags: list) -> list:
    queue = []
    for flag in flags:
        if flag.resolution == "needs_human":
            question = QUESTIONS.get(flag.code, "Please review this case.")
            queue.append(Question(flag.code, question, flag.message, flag.evidence))
    return queue
