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
- [ ] synth/people.py, traps.py, truth.json
- [ ] synth/render.py: Form 16 PDF, AIS JSON, broker CSV, interest certificate, rent receipts
- [ ] 50 cases generated

## 25 Nov
- [ ] agents/llm.py (Gemini, fake for tests)
- [ ] one live model call works (needs the key in .env)

## 26-27 Nov: agents
- [ ] intake, reconcile
- [ ] decide, review, escalate, deliver, pipeline
- [ ] first return end to end

## 28-29 Nov: benchmark
- [ ] baseline, metrics, run_bench (resumable)
- [ ] 3 repeats for Filed and the baseline

## 30 Nov - 1 Dec: demo app
- [ ] new return page with live steps
- [ ] CA queue and results pages

## 2-5 Dec
- [ ] README with results and limitations
- [ ] demo script, pitch, video
- [ ] submit

## Daily status
- **22 Nov:** Project set up. Tax rules checked against public sources and written to docs/tax_rules.md; the engine is built and 46 hand-worked tests pass.
  Blocked on: Gemini key (needed by 25 Nov), `gh` not installed.
  Next: synthetic taxpayers with planted traps.
