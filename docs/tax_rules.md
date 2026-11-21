# Tax rules used by the engine (FY 2025-26, AY 2026-27)

Status legend: **confirmed** = several independent sources agree; **interpretation** = secondary
sources only or disputed, we picked the most common reading; **long-standing** = unchanged for
many years, widely published, not re-checked in this pass; **simplified** = we model a narrower
case than the law and say so.

Checked 22 Nov 2026 by web search of tax news and advisory sites. The official calculator on
incometax.gov.in is an interactive app, so we could not cross-check against it automatically.
Golden tests are hand-worked instead (the working is in `tests/test_engine.py`).
**Before any real filing, a qualified professional must check the figures.**

## Filing dates

| Rule | Value | Status |
|------|-------|--------|
| Due date, individuals without audit (ITR-1, ITR-2) | 31 Jul 2026, not extended (the 31 Aug extension is for ITR-3/ITR-4 business filers) | confirmed |
| Last date for a belated return (s.139(4)) | 31 Dec 2026 | confirmed |
| After that | updated return ITR-U (s.139(8A)) | confirmed |
| Revised-return deadline | possibly 31 Mar 2027 after Budget 2026, sources conflict | not used |

## New regime (s.115BAC, default)

| Rule | Value | Status |
|------|-------|--------|
| Slabs | 0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, above 24L 30% | confirmed |
| Standard deduction on salary | 75,000 | confirmed |
| Rebate s.87A | up to 60,000 if income is at most 12,00,000 | confirmed |
| Marginal relief | tax limited to income above 12,00,000 | confirmed |
| Rebate and special-rate income | rebate is not given on tax on 111A / 112A gains, and the 12L test uses income excluding them (Finance Bill 2025 memorandum) | interpretation (older tribunal rulings differ) |
| Employer NPS, s.80CCD(2) | up to 14% of basic + DA | confirmed |
| Other deductions (80C, 80D, HRA, 24(b) on self-occupied, professional tax) | not allowed | long-standing |

## Old regime

| Rule | Value | Status |
|------|-------|--------|
| Slabs below 60 | 0-2.5L nil, 2.5-5L 5%, 5-10L 20%, above 10L 30% | long-standing |
| Slabs 60-79 / 80+ | nil up to 3L / 5L, then same | long-standing |
| Standard deduction | 50,000 | confirmed |
| Professional tax s.16(iii) | up to 2,500 | long-standing |
| Rebate s.87A | up to 12,500 if income is at most 5,00,000 | long-standing |
| HRA s.10(13A) | least of HRA received, rent minus 10% of basic+DA, 50% (metro) or 40% of basic+DA | long-standing |
| 80C / 80CCD(1B) | 1,50,000 / 50,000 | long-standing |
| 80D | self 25,000 (50,000 if 60+), parents 25,000 (50,000 if senior) | long-standing |
| 80TTA / 80TTB | 10,000 savings interest (under 60) / 50,000 deposit interest (60+) | long-standing |
| 24(b) | self-occupied loan interest up to 2,00,000 | long-standing |
| 80CCD(2) | 10% of basic+DA private, 14% government | confirmed |

## Both regimes

| Rule | Value | Status |
|------|-------|--------|
| Cess | 4% | long-standing |
| STCG on listed equity, s.111A | 20% | confirmed |
| LTCG on listed equity, s.112A | 12.5% above 1,25,000 | confirmed |
| Unused basic exemption set against special-rate gains | yes, applied to 111A first, then 112A | simplified (order is our assumption) |
| Tax rounding, s.288B | final amount rounded to nearest 10 | long-standing |
| Income rounding, s.288A | **not modelled**, so results can differ by a few rupees | simplified |
| Surcharge | **not modelled**, income above 50,00,000 is refused by the engine | scope |

## Late filing

| Rule | Value | Status |
|------|-------|--------|
| s.234F fee | 5,000, or 1,000 if total income is at most 5,00,000; nil if income is within the basic exemption | confirmed (the Rs 10,000 figure quoted by one site was not found elsewhere) |
| s.234A | 1% per month or part month on unpaid tax from the due date; the base is rounded down to 100 | confirmed |
| Old regime in a belated return | not available, the new regime applies (s.115BAC(6)) | interpretation (a few tribunals allowed the new/old choice when Form 10-IE was filed on time) |
| s.234B / 234C | simple case only: no advance tax paid and tax after TDS of 10,000 or more; 234B from 1 Apr 2026 to the filing month, 234C at 15/45/75/100% instalments | simplified |
| 234C and later-arising gains | the proviso for capital gains and dividends that arise late is **not modelled** | simplified |

## ITR form

| Rule | Status |
|------|--------|
| ITR-1: resident, income up to 50L, salary, house property, other sources, 112A gains up to 1,25,000, no brought-forward losses | confirmed |
| ITR-1 may now carry up to two house properties; we only model one | confirmed |
| STCG or 112A gains above 1,25,000 need ITR-2 | confirmed |

## Always sent to a human

Income above 50 lakh, business or professional income, foreign assets or income, non-residents,
crypto, unlisted shares, brought-forward losses, advance-tax challans, more than one house
property, and anything the engine does not model.

## Sources

- Slabs, rebate, standard deduction: [Bajaj Finserv](https://www.bajajfinserv.in/about-new-tax-slab), [ClearTax](https://cleartax.in/guide/taxes/)
- Belated return and 31 Dec 2026: [ClearTax due dates](https://cleartax.in/s/due-date-tax-filing), [Outlook Money](https://www.outlookmoney.com/tax/itr-3-itr-4-deadline-missed-you-can-still-file-a-belated-return-till-december-31)
- Old regime closed in belated returns: [Business Today](https://businesstoday.in/personal-finance/tax/story/filing-belated-itr-note-your-old-tax-regime-deductions-exemptions-wont-apply-this-time-check-details-442846-2024-08-24), [Taxmann](https://www.taxmann.com/post/blog/section-115bac-explained-old-vs-new-tax-regime-and-slab-rates)
- ITR-1 with 112A gains: [Business Standard](https://www.business-standard.com/economy/news/individual-taxpayers-with-ltcg-up-to-1-25-lakh-can-use-simplified-itr-1-125043001472_1.html), [ClearTax ITR-1](https://cleartax.in/s/itr1)
- Due dates: [CBDT circular 7/2026](https://incometaxindia.gov.in/documents/d/guest/circular-7-2026-pdf), [Business Today](https://www.businesstoday.in/amp/personal-finance/tax/story/income-tax-return-calendar-for-ay-2026-27-july-31-is-not-the-deadline-for-everyone-check-key-due-dates-537785-2026-06-18)
- 87A and special-rate income: [Taxmann](https://www.taxmann.com/post/blog/section-87a-rebate-restriction-on-special-rate-income-is-prospective-itat/), [Business Today](https://www.businesstoday.in/personal-finance/tax/story/as-mf-investor-are-my-gains-excluded-from-the-section-87a-rebate-calculation-under-new-tax-regime-in-fy2025-26-474519-2025-05-02)
- 234A / 234F: [Income Tax Department, interest and fees](https://www.incometaxindia.gov.in/w/interest-and-fees)
- Employer NPS: [Value Research](https://www.valueresearchonline.com/stories/229044/employer-nps-deduction-new-tax-regime/)
