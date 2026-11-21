"""TEST-ONLY stand-in for the model. It is never used in the benchmark.

OracleLLM answers extraction prompts with the exact values the generator wrote into the
documents, and answers the reviewer with "no concerns". Using it proves that every step other
than reading is correct, without spending a single real model call.
"""

import json
from pathlib import Path


class OracleLLM:
    def __init__(self, truth_file):
        record = json.loads(Path(truth_file).read_text(encoding="utf-8"))
        self.entries = record["oracle_extractions"]
        self.model = "test-oracle"
        self.calls = self.tokens_in = self.tokens_out = 0

    def complete_json(self, system, prompt):
        self.calls += 1
        if "review a draft" in system:
            return {"concerns": []}
        squashed = prompt.replace(" ", "")
        for entry in self.entries:
            if all(key.replace(" ", "") in squashed for key in entry["keys"]):
                return entry["fields"]
        raise AssertionError("oracle has no answer for this prompt")


class ScriptedLLM:
    """Returns the given answers in order. Used to test intake error handling."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []
        self.model = "test-scripted"
        self.calls = self.tokens_in = self.tokens_out = 0

    def complete_json(self, system, prompt):
        self.calls += 1
        self.prompts.append(prompt)
        return self.answers.pop(0)
