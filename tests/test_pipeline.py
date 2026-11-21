"""End-to-end checks of every step except the model's reading, using the test-only oracle."""

import json
from pathlib import Path

import pytest

from agents.documents import capital_gains, classify, load_case
from agents.pipeline import run_case
from synth.generate import generate
from tests.fakes import OracleLLM

CASE_COUNT = 50
SEED = 7


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return generate(CASE_COUNT, SEED, tmp_path_factory.mktemp("cases"))


@pytest.fixture(scope="module")
def results(cases):
    out = {}
    for folder in sorted(Path(cases).iterdir()):
        llm = OracleLLM(folder / "truth.json")
        truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
        out[folder.name] = (run_case(folder, llm), truth)
    return out


def test_generation_is_repeatable(tmp_path):
    first = generate(10, 3, tmp_path / "a")
    second = generate(10, 3, tmp_path / "b")
    for name in ("case_001", "case_010"):
        for file in ("truth.json", "ais.json", "questionnaire.json"):
            assert (first / name / file).read_bytes() == (second / name / file).read_bytes()


def test_every_trap_is_present(results):
    seen = {trap for _, truth in results.values() for trap in truth["traps"]}
    assert len(seen) == 16


def test_status_matches_truth_for_every_case(results):
    wrong = [cid for cid, (r, t) in results.items() if r.status != t["expected"]["status"]]
    assert wrong == []


def test_figures_match_truth_for_every_ready_case(results):
    for cid, (result, truth) in results.items():
        expected = truth["expected"]
        if expected["status"] != "ready_to_file":
            continue
        assert result.itr_form == expected["itr_form"], cid
        assert result.regime == expected["regime"], cid
        assert result.net_payable == expected["net_payable"], cid


def test_flags_match_truth_for_every_case(results):
    for cid, (result, truth) in results.items():
        got = {f["code"]: f["resolution"] for f in result.flags}
        assert got == truth["expected"]["flags"], cid


def test_human_cases_get_a_question(results):
    for cid, (result, truth) in results.items():
        if truth["expected"]["status"] == "needs_human":
            assert result.questions, cid


def test_clean_cases_have_no_flags(results):
    clean = [r for r, t in results.values() if not t["traps"]]
    assert clean and all(not r.flags and r.status == "ready_to_file" for r in clean)


def test_ready_cases_carry_a_note_and_a_sheet(results):
    result, _ = next((r, t) for r, t in results.values() if r.status == "ready_to_file")
    assert "Hi " in result.client_note and "regime" in result.computation_sheet
    assert result.itr_json["assessment_year"] == "2026-27"


def test_broker_rows_split_short_and_long_term():
    rows = [
        {
            "buy_date": "2025-01-01",
            "sell_date": "2025-06-01",
            "buy_value": "100",
            "sell_value": "150",
        },
        {
            "buy_date": "2024-01-01",
            "sell_date": "2025-06-01",
            "buy_value": "100",
            "sell_value": "400",
        },
    ]
    assert capital_gains(rows) == (50, 300)


def test_document_kinds_are_recognised():
    assert classify("FORM NO. 16 - PART B") == "form16"
    assert classify("CERTIFICATE UNDER SECTION 203 (FORM 16)") == "form16"
    assert classify("HDFC Bank - Interest Certificate") == "interest_certificate"
    assert classify("Rent Receipts") == "rent_receipts"
    assert classify("Grocery list") == "unknown"


def test_pdf_text_survives_loading(cases):
    files = load_case(Path(cases) / "case_001")
    assert files.documents and all(d.kind != "unknown" for d in files.documents)
