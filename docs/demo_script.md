# Demo script (2 minutes)

Numbers below come from `bench/results.md` (held-out set, one repeat). Start the app with `streamlit run app/main.py`. Pick two clients in advance: a clean one, and one with a trap (for example case with an unreported interest in the AIS plus a missing landlord PAN). Do a dry run so the model answers are in the cache and the demo does not wait.

**0:00 Problem (15 s)**
"About 7 crore Indians file a tax return every year. Their documents disagree with each other, and those mismatches are what bring tax notices. A CA costs Rs 500 to 5,000 and is busy in July. Filed is the firm that does the whole job: documents in, a checked return out, and a human only where judgment is needed."

**0:15 A clean client (35 s)**
Open **New return**, choose the clean client. Show the documents list. Click **Prepare return**. As steps appear, say what each does: intake reads the PDFs, reconcile cross-checks Form 16 against the AIS, decide picks form and regime.
Result: ready to file. Point at the old-versus-new table and the saving, then the note to the client. "The model reads. Tested code does all the arithmetic."

**0:50 A client with traps (40 s)**
Choose the trap client and prepare the return. Show the flags as they appear: interest found in the AIS that the client never declared (included automatically), Form 16 and AIS disagree on tax deducted (the AIS amount is claimed), and the landlord PAN is missing, which cannot be fixed by software.
Switch to **Tax expert queue**: "That one question is all the human sees, with the evidence. Across the held-out clients: 79% finished with nobody touching them; the rest were the cases that truly needed the expert."

**1:30 Evidence (25 s)**  (say the caveat; judges trust it)
Open **Results** and show the chart. "We generated synthetic taxpayers with planted traps and known correct answers, and ran Filed against the same model asked in one prompt, on 29 cases we never used while building. Exact returns: 100% versus 17%. The number that matters is false automation, of the returns called ready, how many were wrong: 0% versus 83%. We also show our first design, where a model reviewer over-escalated, and how we fixed it. The caveat: these documents are synthetic and clean."

**1:55 Close (5 s)**
"Filed: the tax firm with the clerical work automated and the expert kept for judgment. It prepares returns today; filing and notice replies are next."

## If something goes wrong live
- Model slow or rate-limited: use the saved result (the checkbox on New return) and say so.
- No internet: the Results and expert queue pages work from saved files.
