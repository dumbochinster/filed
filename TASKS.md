# Tasks

Plan: see PLAN.md. Submit on 5 Dec; the deadline is 6 Dec, 11:59 pm IST.

## 22 Nov: setup and tax engine
- [x] venv, requirements, .gitignore, .gitattributes, .env.example
- [x] README skeleton
- [x] tax rules verified and written down (docs/tax_rules.md)
- [x] taxengine with hand-worked tests (46 passing)
- [ ] cross-check a few cases against the official calculator (interactive app, needs a person)
- [ ] create the public GitHub repo (needs `gh` installed and logged in)

## 23-24 Nov: synthetic taxpayers
- [x] synth/people.py, traps.py, truth.json
- [x] synth/render.py: Form 16 PDF, AIS JSON, broker CSV, interest certificate, rent receipts
- [x] 50 cases generated

## 25 Nov
- [x] agents/llm.py (Gemini, fake for tests)
- [ ] one live model call works (needs the key in .env)  <- BLOCKED on key

## 26-27 Nov: agents
- [x] intake, reconcile
- [x] decide, review, escalate, deliver, pipeline
- [x] first return end to end (with the test-only oracle; live model run waits for the key)

## 28-29 Nov: benchmark
- [x] baseline, metrics, run_bench (resumable)
- [ ] 3 repeats for Filed and the baseline  <- BLOCKED on key

## 30 Nov - 1 Dec: demo app
- [x] new return page with live steps
- [x] CA queue and results pages

## 2-5 Dec
- [x] README with limitations
- [ ] add the results from bench/results.md to the README
- [x] demo script and pitch written
- [ ] record the video (needs the author)
- [ ] submit

## Daily status
- **22 Nov:** Project set up. Tax rules checked against public sources and written to docs/tax_rules.md; the engine is built and 46 hand-worked tests pass.
  Blocked on: Gemini key (needed by 25 Nov), `gh` not installed.
  Next: synthetic taxpayers with planted traps.
- **22 Nov (later):** Everything that does not need the key is built: 50 synthetic clients with 16 planted traps, the full agent pipeline, the benchmark harness, the Streamlit app, pitch and demo script. 86 tests pass; with the test-only oracle the pipeline matches the known answer on all 50 cases.
  Blocked on: Gemini key (all real runs), GitHub login (CLI installed, waiting for the one-time code to be entered).
  Next: with the key, one live call, a 5-case trial, then the full benchmark.
