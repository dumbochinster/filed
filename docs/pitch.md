# Filed: pitch

## The problem

About 7.3 crore income-tax returns were filed for AY 2025-26 ([Business Standard](https://www.business-standard.com/finance/personal-finance/over-60-million-income-tax-returns-filed-for-2025-26-so-far-i-t-dept-125091300339_1.html), [CAclubindia](https://www.caclubindia.com/news/it-department-sees-record-surge-with-over-7-3-crore-itrs-filed-for-ay-2025-26-25465.asp)). Most of them are salaried people with one employer, a bank, a few shares and a rent receipt.

Their documents disagree. The AIS often lists interest or dividends the taxpayer forgot; two employers each give a standard deduction; Form 16 and the AIS show different tax deducted. These mismatches are what trigger tax notices. Choosing between the old and new regime is a coin flip for most people, and missing the due date silently removes the old regime.

Today the choice is to do it yourself and worry, or to pay a chartered accountant (roughly Rs 500 to 2,500 for a simple salaried return, up to about Rs 5,000 with capital gains, per fee guides such as [Taxclue](https://taxclue.in/itr-filing-cost/)) and queue for their time in July.

## The idea

Filed is not a tool for accountants. It is the firm. A client uploads Form 16, the AIS, a broker statement and receipts. Agents read the documents, reconcile them against each other, choose the form and regime, compute the tax with a tested engine, review their own draft, and hand back a filing-ready return and a plain-language note. A human tax expert sees only the questions that need judgment, such as a missing landlord PAN or an unexplained property purchase, each phrased as one line with the evidence attached.

Two design choices make it trustworthy:
- The model reads and judges; tested code does every calculation. The tax engine has hand-worked tests with the arithmetic shown.
- Anything outside what it models (income above Rs 50 lakh, foreign assets, crypto, business income) always goes to a person. It never guesses.

## Who buys it

First customers: salaried first-job and mid-career people and small investors, who today use DIY software or a CA.
Later: freelancers (ITR-4), NRIs, and employers who offer it as a benefit to staff.

## Why it can be a company

- **Cheaper to deliver.** The clerical 90% (reading, matching, computing) is automated, so expert time per return drops from a working session to a few minutes of answering flagged questions. The saving is a hypothesis to test with real users; we have not measured expert time yet.
- **Recurring revenue.** After the return come notice replies (a mismatch notice is the natural second product), advance-tax reminders, and next year's filing with last year's data already on file.
- **A data advantage.** Every escalation records which questions humans actually had to answer. Over time that shrinks the escalation rate and becomes the moat.
- **Timing.** The AIS puts each taxpayer's data in one place; models can now read messy documents reliably; belated and revised returns for AY 2026-27 are open until 31 Dec 2026.

## Evidence

Measured on synthetic taxpayers with planted traps and known correct answers, against a single-prompt baseline on the same model. The headline number is the false-automation rate: how often a return marked "ready to file" is actually wrong. The numbers are in [bench/results.md](../bench/results.md) once the benchmark has run; the README quotes them.

## What it does not do yet

It prepares returns but does not file them on the government portal (that needs registration as an e-return intermediary). It models one house property, no surcharge, and no advance-tax challans. A qualified professional should review any real return. See [tax_rules.md](tax_rules.md) for what each rule rests on.
