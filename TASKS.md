# Tasks

Plan: see PLAN.md. Submit on 5 Dec; the deadline is 6 Dec, 11:59 pm IST.

## 22 Nov: setup and tax engine
- [x] venv, requirements, .gitignore, .gitattributes, .env.example
- [x] README skeleton
- [x] tax rules verified and written down (docs/tax_rules.md)
- [x] taxengine with hand-worked tests (46 passing)
- [ ] cross-check a few cases against the official calculator (interactive app, needs a person)
- [x] public GitHub repo: https://github.com/dumbochinster/filed

## 23-24 Nov: synthetic taxpayers
- [x] synth/people.py, traps.py, truth.json
- [x] synth/render.py: Form 16 PDF, AIS JSON, broker CSV, interest certificate, rent receipts
- [x] 50 cases generated

## 25 Nov
- [x] agents/llm.py (Gemini, fake for tests)
- [x] live model calls work (Gemini; local Qwen through Ollama also supported)

## 26-27 Nov: agents
- [x] intake, reconcile
- [x] decide, review, escalate, deliver, pipeline
- [x] first return end to end (with the test-only oracle; live model run waits for the key)

## 28-29 Nov: benchmark
- [x] baseline, metrics, run_bench (resumable)
- [x] benchmark run: dev set (50 cases, 1 repeat), held-out set (29 cases, 1 repeat); 3 repeats not possible on the free tier

## 30 Nov - 1 Dec: demo app
- [x] new return page with live steps
- [x] CA queue and results pages

## 2-5 Dec
- [x] README with limitations
- [x] results added to the README, pitch and demo script
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
- **22 Nov (night):** Repo pushed. Free Gemini quota is 20 requests a day per model, so the benchmark runs on gemini-3.5-flash-lite; a second run on local Qwen 9B (Ollama) is in progress. Added Groq, Cerebras, Mistral and Ollama providers, request timeout and a quota stop. Licence and CI added.
  Blocked on: nothing technical; waiting for the runs. Needs the author: README AI-tools wording, Keploy star, official-calculator spot check, demo video.
  Next: read the results, fix generic weaknesses, put real numbers in the README.
- **22 Nov (final):** Benchmark done on the free Gemini tier and written up. Filed: 100% exact returns on both the dev set and a held-out set, 0% wrong among returns called ready; single prompt: 15-17% exact. The model reviewer over-escalated (hands-off 16%), so it is now off by default (80% hands-off). Limits: synthetic clean documents, one repeat, held-out run stopped at 29 of 50 cases.
  Needs the author: README AI-tools wording, Keploy star, official-calculator spot check, demo video, submission on the dashboard (opens 4 Dec), rotate the Gemini key.
