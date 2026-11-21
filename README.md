# Filed

**Filed is an agent-run income-tax firm: a salaried person uploads their documents and gets back a checked, filing-ready Indian income-tax return, with a human tax expert involved only on the decisions that need judgment.**

Built for Homingo Hack Days Edition 01, Agents track, statement A2 "The full-stack AI firm".

> Status: everything except the live model calls is built and tested. Benchmark results are added here only after a real run; nothing in this file is estimated.

## The problem

About 7.3 crore income-tax returns are filed in India each year. The documents rarely agree with each other (the AIS often shows interest or dividends the taxpayer forgot), the old-versus-new regime choice is confusing, and a chartered accountant costs Rs 500 to 5,000 and is busy at deadline time. Mismatches are what trigger tax notices.

## What the firm does

```
documents ─► intake ─► reconcile ─► decide ─► review ─► escalate ─► deliver
 (PDF, CSV,   reads     cross-checks  form +    second    only real   return JSON,
  JSON)       PDFs      every source  regime    model     questions   computation sheet,
              (model)   (code)        (engine)  pass      to a person client note
```

1. **Intake**: the model reads Form 16, bank certificates and rent receipts; code reads the AIS, broker CSV and questionnaire.
2. **Reconcile** (code): dedupes uploads, matches TDS against the AIS, finds income the client did not declare, checks landlord PAN, and spots anything out of scope.
3. **Decide** (tax engine): ITR form, both regimes computed, the cheaper one chosen. Belated filers are limited to the new regime.
4. **Review**: a second model pass looks for contradictions in the draft.
5. **Escalate**: only flags that need judgment become one-line questions for the tax expert.
6. **Deliver**: draft return data, an old-versus-new computation sheet, and a plain note to the client.

The model never does arithmetic that ends up on the return; the engine does, and it has hand-worked tests. It prepares returns but does not file them on the government portal (that needs registration as an e-return intermediary).

## Repository

| Path | What it is |
|------|-----------|
| `taxengine/` | Tax computation for AY 2026-27, no model involved |
| `synth/` | Synthetic taxpayers with 16 planted traps and a known correct answer for each |
| `agents/` | Model client, intake, reconciliation, decision, review, escalation, delivery, pipeline |
| `bench/` | Baseline, scoring, resumable runner, report and chart |
| `app/` | Streamlit demo: new return, tax expert queue, results |
| `docs/tax_rules.md` | Every rule used, its source and how well it was verified |
| `docs/pitch.md`, `docs/demo_script.md` | Pitch and 2-minute demo script |
| `tests/` | 80+ tests, including end-to-end checks over all 50 synthetic cases |

## Run it

```bash
python -m venv venv
venv\Scripts\activate                 # Windows; source venv/bin/activate elsewhere
pip install -r requirements.txt
pytest                                # no API key needed

copy .env.example .env                # then put your key in .env
python -m agents.llm --list           # models your key can use; set FILED_MODEL
python -m agents.llm --ping           # one real call to check the setup

python -m synth.generate --count 50   # synthetic clients into data/cases
python -m agents.pipeline data/cases/case_001
python -m bench.run_bench --repeats 3 # resumable; use --limit 5 for a trial
python -m bench.report                # writes bench/results.md and chart.png
streamlit run app/main.py
```

## How we test without spending model calls

`tests/fakes.py` holds a test-only stand-in for the model that answers extraction prompts from the generator's own record. Running the whole pipeline with it over all 50 synthetic cases checks that every step except the model's reading matches the known correct answer. It is never used in the benchmark.

## Results

Not run yet. The benchmark compares Filed with a single-prompt baseline on the same model and documents, over synthetic taxpayers, at least 3 repeats, with failures listed. See `bench/results.md` once it exists.

## Limits

- Synthetic data only; no real taxpayer documents were used.
- The correct answers come from our tax engine applied to the true facts, so the benchmark measures reading, reconciling and deciding, not the engine. The engine is checked by hand-worked tests, not yet against the official calculator.
- Not modelled: surcharge (income above Rs 50 lakh goes to a person), more than one house property, advance-tax challan dates, business income, foreign assets, crypto.
- Several rules rest on secondary sources; `docs/tax_rules.md` marks each as confirmed, interpretation or simplified.

## AI tools, models and libraries used

To be completed before submission (the line about the coding assistant is worded with the author).

- Runtime model: Google Gemini through the `google-genai` SDK; the exact model name is recorded in `bench/results.md`. The Anthropic SDK is supported as an alternative provider.
- Libraries: `pypdf`, `fpdf2`, `streamlit`, `matplotlib`, `python-dotenv`, `pytest`, `ruff`
