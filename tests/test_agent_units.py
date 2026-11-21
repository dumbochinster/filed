"""Unit tests for the model client, intake validation and the reviewer."""

from datetime import date

import pytest

from agents import intake, review
from agents.decide import decide
from agents.documents import CaseFiles, Document
from agents.llm import CachedClient, Client, LLMError, parse_json
from agents.reconcile import Facts
from taxengine.models import Employer, Profile
from tests.fakes import ScriptedLLM

FORM16 = {
    "employer_name": "Acme",
    "tan": "ABCD12345E",
    "employee_pan": "ABCDE1234F",
    "gross_salary": "Rs. 12,34,567",
    "basic_da": 600000,
    "hra_received": 0,
    "professional_tax": 0,
    "employer_nps": 0,
    "tds_deducted": 0,
    "sec_80c": 0,
    "sec_80ccd_1b": 0,
    "health_self": 0,
    "foreign_rsu": False,
}


class FakeProvider(Client):
    def __init__(self, replies):
        super().__init__("fake")
        self.replies = list(replies)

    def generate(self, system, prompt):
        return self.replies.pop(0), 10, 5


class TestJsonHandling:
    def test_parse_plain_and_fenced(self):
        assert parse_json('{"a": 1}') == {"a": 1}
        assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_bad_json_is_retried_once(self):
        client = FakeProvider(["not json", '{"ok": true}'])
        assert client.complete_json("s", "p") == {"ok": True}
        assert client.calls == 2 and client.tokens_in == 20

    def test_two_bad_replies_raise(self):
        with pytest.raises(LLMError):
            FakeProvider(["nope", "still nope"]).complete_json("s", "p")


class TestCache:
    def test_second_identical_call_is_free_but_counts_tokens(self, tmp_path):
        inner = FakeProvider(['{"x": 1}'])
        cached = CachedClient(inner, tmp_path)
        assert cached.complete_json("s", "p") == {"x": 1}
        assert cached.complete_json("s", "p") == {"x": 1}
        assert inner.calls == 1
        assert cached.calls == 2 and cached.tokens_in == 20

    def test_different_prompt_is_a_different_entry(self, tmp_path):
        cached = CachedClient(FakeProvider(['{"x": 1}', '{"x": 2}']), tmp_path)
        assert cached.complete_json("s", "a") != cached.complete_json("s", "b")


class TestIntakeValidation:
    def test_money_text_is_converted(self):
        assert intake.to_int("Rs. 12,34,567", "x") == 1234567
        assert intake.to_int("INR 5000", "x") == 5000

    def test_bad_amounts_are_rejected(self):
        for bad in ("abc", -5, True):
            with pytest.raises(intake.ExtractionError):
                intake.to_int(bad, "x")

    def test_form16_is_cleaned(self):
        doc = Document("f.pdf", "form16", "text")
        data = intake.read_form16(ScriptedLLM([FORM16]), doc)
        assert data["gross_salary"] == 1234567

    def test_bad_pan_makes_the_document_unreadable_not_guessed(self):
        files = CaseFiles(folder=None, documents=[Document("f.pdf", "form16", "text")])
        extraction = intake.run(ScriptedLLM([{**FORM16, "employee_pan": "12345"}]), files)
        assert extraction.form16s == [] and extraction.unreadable == ["f.pdf"]

    def test_unknown_document_is_unreadable(self):
        files = CaseFiles(folder=None, documents=[Document("x.pdf", "unknown", "text")])
        assert intake.run(ScriptedLLM([]), files).unreadable == ["x.pdf"]


def make_facts():
    profile = Profile(age=30, employers=(Employer("A", 900_000, 400_000),))
    return Facts(profile, date(2026, 7, 10), "A B", "ABCDE1234F", [])


class TestReviewer:
    def run_review(self, answer):
        facts = make_facts()
        review.review(ScriptedLLM([answer]), facts, decide(facts))
        return facts.flags

    def test_high_concern_needs_a_person(self):
        flags = self.run_review({"concerns": [{"message": "odd", "severity": "high"}]})
        assert [(f.code, f.resolution) for f in flags] == [("REVIEWER_CONCERN", "needs_human")]

    def test_low_concern_is_only_information(self):
        flags = self.run_review({"concerns": [{"message": "minor", "severity": "low"}]})
        assert flags[0].resolution == "info"

    def test_no_concerns_adds_nothing(self):
        assert self.run_review({"concerns": []}) == []

    def test_empty_messages_are_ignored(self):
        assert self.run_review({"concerns": [{"message": " ", "severity": "high"}]}) == []

    def test_a_reviewer_that_fails_is_skipped(self):
        class Failing:
            def complete_json(self, system, prompt):
                raise LLMError("down")

        facts = make_facts()
        assert review.review(Failing(), facts, decide(facts)) == []
