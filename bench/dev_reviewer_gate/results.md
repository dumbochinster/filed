# Dev set, model reviewer can block (first configuration)

Model: `gemini-3.5-flash-lite`. Model reviewer: gate. Cases: 50 synthetic taxpayers. Complete repeats: {'filed': 1, 'baseline': 1}. Run date: 2026-11-22.
Every number below comes from `runs/`; nothing is estimated. Values are mean ± standard deviation across repeats.

## Headline

| Metric | Filed (agents + tax engine) | Single prompt |
|---|---|---|
| Exact return (form, regime, tax within Rs 10) | 100.0% | 15.0% |
| ITR form correct | 100.0% | 55.0% |
| Regime choice correct | 100.0% | 72.5% |
| Mean absolute tax error, Rs | 0 | 21,484 |
| Escalation recall (cases needing a person that were escalated) | 100.0% | 50.0% |
| Escalation precision (escalations that were needed) | 23.8% | 83.3% |
| False-automation rate (marked ready but wrong; lower is better) | 0.0% | 86.4% |
| Hands-off rate (finished correctly with no person) | 16.0% | 12.0% |
| Tokens per case | 1,802 | 1,042 |
| Seconds per case | 15 | 1 |

![chart](chart.png)

## By trap

Each cell is how many times the trap was handled correctly out of how many times it appeared (all repeats pooled).
Handled means: escalated to a person when one is needed, otherwise an exact return.

| Trap | Filed (agents + tax engine) | Single prompt |
|---|---|---|
| AIS_INTEREST_MISSING | 8/8 | 2/8 |
| BELATED_FORCED_NEW | 2/2 | 0/2 |
| CG_NEEDS_ITR2 | 2/2 | 0/2 |
| DIVIDEND_UNREPORTED | 4/4 | 1/4 |
| DUPLICATE_DOCUMENT | 5/5 | 2/5 |
| FOREIGN_RSU | 2/2 | 0/2 |
| HRA_NO_LANDLORD_PAN | 2/2 | 1/2 |
| INCOME_OVER_50L | 2/2 | 0/2 |
| LTCG_SMALL | 2/2 | 0/2 |
| OLD_REGIME_CHEAPER | 2/2 | 0/2 |
| PARENTS_SENIOR_80D | 2/2 | 0/2 |
| SENIOR_80TTB | 2/2 | 0/2 |
| TDS_MISMATCH | 2/2 | 0/2 |
| TWO_EMPLOYERS | 4/4 | 3/4 |
| UNEXPLAINED_SFT | 2/2 | 2/2 |
| VDA_TRADES | 2/2 | 2/2 |

## Where Filed failed

- none in the repeats that were run

## How to read this

- Cases and answers are synthetic. The correct answer for each case comes from our tax engine applied to the true facts; the engine itself is checked by hand-worked tests (`tests/test_engine.py`). So this benchmark measures reading, reconciling and deciding, not the engine.
- The single-prompt baseline gets the same documents and the same model but no tax engine, no reconciliation step and no escalation rules.
- Repeats use temperature 0, so they mostly measure the provider's run-to-run variation rather than sampling noise.
- A case is "exact" only if the form, the regime and the final amount (within Rs 10) are all right.
