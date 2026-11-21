# Filed

**Filed is an agent-run income-tax firm: a salaried person uploads their documents and gets back a checked, filing-ready Indian income-tax return, with a human tax expert involved only on the decisions that need judgment.**

Built for Homingo Hack Days Edition 01, Agents track, statement A2 "The full-stack AI firm".

> Work in progress. Results are added only from real benchmark runs.

## The problem

Around 9 crore Indians file an income-tax return every year. Documents disagree with each other (the AIS often shows interest or dividends the taxpayer forgot), the old-versus-new regime choice is confusing, and a chartered accountant costs a few thousand rupees and is busy at deadline time. Mismatches are what trigger tax notices.

## What the firm does

1. Reads the client's documents (Form 16, AIS, broker statement, interest certificates, rent receipts).
2. Reconciles them and flags every mismatch.
3. Chooses the return form and compares the old and new regimes.
4. Computes the tax with a tested engine (the model never does the arithmetic).
5. Reviews its own draft against the evidence.
6. Sends only real judgment calls to a human expert, each as a one-line question.
7. Delivers a filing-ready return, a computation sheet and a plain-language note to the client.

It prepares the return but does not file it on the portal; filing for someone else needs registration as an e-return intermediary.

## Repository

| Path | What it is |
|------|-----------|
| `taxengine/` | Deterministic tax computation for AY 2026-27, no model involved |
| `synth/` | Synthetic taxpayers with planted traps and known correct answers |
| `agents/` | The agent steps and the pipeline |
| `bench/` | Benchmark against a single-prompt baseline |
| `app/` | Demo app |
| `docs/tax_rules.md` | Every rule used, with its source and how well it was verified |

## Run the tests

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Results

To be filled from `bench/results.md`.

## AI tools, models and libraries used

To be completed before submission (the coding assistant line is worded with the author).

- Runtime model: Google Gemini via the `google-genai` SDK (model name to be recorded here)
- Libraries: `pypdf`, `fpdf2`, `streamlit`, `matplotlib`, `python-dotenv`, `pytest`, `ruff`
