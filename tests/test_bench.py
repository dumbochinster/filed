"""Checks of the benchmark machinery itself, using the test-only fakes."""

import json

import pytest

from bench import report, run_bench
from bench.metrics import across_repeats, score_case, summarise, trap_table
from synth.generate import generate
from tests.fakes import OracleLLM


def truth(status="ready_to_file", form="ITR-1", regime="new", net=1000, traps=()):
    return {
        "case_id": "c1",
        "traps": list(traps),
        "expected": {"status": status, "itr_form": form, "regime": regime, "net_payable": net},
    }


def result(status="ready_to_file", form="ITR-1", regime="new", net=1000):
    return {"status": status, "itr_form": form, "regime": regime, "net_payable": net}


class TestScoreCase:
    def test_exact_within_tolerance(self):
        assert score_case(result(net=1010), truth())["exact"]
        assert not score_case(result(net=1011), truth())["exact"]

    def test_wrong_regime_is_not_exact_even_if_amount_matches(self):
        scored = score_case(result(regime="old"), truth())
        assert not scored["exact"] and scored["false_automation"]

    def test_ready_when_a_person_was_needed_is_false_automation(self):
        scored = score_case(result(), truth(status="needs_human"))
        assert scored["false_automation"] and not scored["handled"]

    def test_escalating_a_human_case_is_handled(self):
        scored = score_case(result(status="needs_human"), truth(status="needs_human"))
        assert scored["handled"] and not scored["false_automation"]

    def test_missing_answer_is_not_exact(self):
        scored = score_case({"status": "no_answer"}, truth())
        assert not scored["exact"] and scored["error"] is None and not scored["predicted_human"]


class TestSummary:
    def test_rates(self):
        scores = [
            score_case(result(), truth()),
            score_case(result(net=5), truth()),
            score_case(result(status="needs_human"), truth(status="needs_human")),
            score_case(result(), truth(status="needs_human")),
        ]
        summary = summarise(scores)
        assert summary["exact_return_rate"] == 0.5
        assert summary["escalation_recall"] == 0.5
        assert summary["escalation_precision"] == 1.0
        assert summary["false_automation_rate"] == pytest.approx(2 / 3)
        assert summary["hands_off_rate"] == 0.25

    def test_across_repeats(self):
        mean, spread = across_repeats([{"x": 0.5}, {"x": 1.0}])["x"]
        assert mean == 0.75 and spread == 0.25

    def test_trap_table_pools_repeats(self):
        scores = [
            score_case(result(), truth(traps=["T"])),
            score_case(result(net=0), truth(traps=["T"])),
        ]
        assert trap_table([scores]) == {"T": (1, 2)}


class CannedLLM:
    """Baseline stand-in that always gives one fixed answer."""

    model = "test-canned"
    calls = tokens_in = tokens_out = 0

    def complete_json(self, system, prompt):
        return {"itr_form": "ITR-1", "regime": "new", "net_payable": 0, "needs_human": False}


def test_runs_resume_and_report_builds(tmp_path):
    cases = generate(6, 11, tmp_path / "cases")
    runs = tmp_path / "runs"

    def make_llm(rep, folder):
        return OracleLLM(folder / "truth.json") if "filed" in str(make_llm.system) else CannedLLM()

    # run the two systems separately so each gets the right stand-in
    make_llm.system = "filed"
    assert run_bench.run(cases, 2, ["filed"], make_llm, runs, log=lambda m: None) == 12
    make_llm.system = "baseline"
    assert run_bench.run(cases, 2, ["baseline"], make_llm, runs, log=lambda m: None) == 12
    assert run_bench.run(cases, 2, ["filed", "baseline"], make_llm, runs, log=lambda m: None) == 0

    out = tmp_path / "out"
    report.build(cases, runs, out)
    text = (out / "results.md").read_text(encoding="utf-8")
    assert "Exact return" in text and "By trap" in text
    assert (out / "chart.png").stat().st_size > 1000
    assert "filed" in (out / "summary.csv").read_text(encoding="utf-8")
    saved = json.loads((runs / "filed" / "case_001_rep1.json").read_text(encoding="utf-8"))
    assert saved["case_id"] == "case_001"


def test_infrastructure_errors_are_skipped_not_scored(tmp_path):
    cases = generate(2, 11, tmp_path / "cases")
    messages = []

    def broken(rep, folder):
        raise ConnectionError("network down")

    assert run_bench.run(cases, 1, ["filed"], broken, tmp_path / "runs", log=messages.append) == 0
    assert len(messages) == 2 and not (tmp_path / "runs" / "filed").exists()


def test_bugs_are_not_swallowed(tmp_path):
    cases = generate(2, 11, tmp_path / "cases")

    def buggy(rep, folder):
        raise KeyError("a real bug")

    with pytest.raises(KeyError):
        run_bench.run(cases, 1, ["filed"], buggy, tmp_path / "runs", log=lambda m: None)


def test_extraction_check_scores_a_perfect_and_a_flawed_reader(tmp_path):
    from bench import extraction_check

    cases = generate(3, 5, tmp_path / "cases")
    _fields, docs, mismatches = extraction_check.check(
        cases, OracleLLM(cases / "case_001" / "truth.json"), 1
    )
    assert mismatches == [] and all(ok == total for ok, total in docs.values())

    class WrongTds(OracleLLM):
        def complete_json(self, system, prompt):
            answer = dict(super().complete_json(system, prompt))
            if "tds_deducted" in answer:
                answer["tds_deducted"] += 1
            return answer

    _, docs, mismatches = extraction_check.check(
        cases, WrongTds(cases / "case_001" / "truth.json"), 1
    )
    assert docs["form16"][0] == 0 and any("tds_deducted" in m for m in mismatches)
