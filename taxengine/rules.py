"""Constants for AY 2026-27 (FY 2025-26). Sources and status are in docs/tax_rules.md."""

from datetime import date

DUE_DATE = date(2026, 7, 31)
BELATED_DEADLINE = date(2026, 12, 31)
ASSESSMENT_YEAR_START = date(2026, 4, 1)

# Slabs are (upper limit of the band, rate in percent). None means no upper limit.
NEW_REGIME_SLABS = [
    (400_000, 0),
    (800_000, 5),
    (1_200_000, 10),
    (1_600_000, 15),
    (2_000_000, 20),
    (2_400_000, 25),
    (None, 30),
]
OLD_REGIME_SLABS = {
    "regular": [(250_000, 0), (500_000, 5), (1_000_000, 20), (None, 30)],
    "senior": [(300_000, 0), (500_000, 5), (1_000_000, 20), (None, 30)],
    "super_senior": [(500_000, 0), (1_000_000, 20), (None, 30)],
}

STANDARD_DEDUCTION_NEW = 75_000
STANDARD_DEDUCTION_OLD = 50_000
PROFESSIONAL_TAX_CAP = 2_500

# s.87A rebate
REBATE_LIMIT_NEW = 1_200_000
REBATE_MAX_NEW = 60_000
REBATE_LIMIT_OLD = 500_000
REBATE_MAX_OLD = 12_500

# Chapter VI-A and house property (old regime unless stated)
LIMIT_80C = 150_000
LIMIT_80CCD_1B = 50_000
LIMIT_80D_SELF = 25_000
LIMIT_80D_SENIOR = 50_000
LIMIT_80TTA = 10_000
LIMIT_80TTB = 50_000
LIMIT_HOME_LOAN_INTEREST = 200_000
EMPLOYER_NPS_PCT_NEW = 14
EMPLOYER_NPS_PCT_OLD_PRIVATE = 10
EMPLOYER_NPS_PCT_OLD_GOVT = 14
HOUSE_PROPERTY_STANDARD_DEDUCTION_PCT = 30

# HRA
HRA_RENT_EXCESS_PCT = 10
HRA_METRO_PCT = 50
HRA_NON_METRO_PCT = 40

# Capital gains on listed equity
STCG_111A_PCT = 20
LTCG_112A_PCT_TIMES_10 = 125  # 12.5%, kept as an integer
LTCG_112A_EXEMPTION = 125_000

CESS_PCT = 4
SURCHARGE_THRESHOLD = 5_000_000  # the engine refuses incomes above this

# Late filing and interest
FEE_234F_HIGH = 5_000
FEE_234F_LOW = 1_000
FEE_234F_LOW_INCOME_LIMIT = 500_000
INTEREST_THRESHOLD = 10_000  # 234B / 234C apply when tax after TDS reaches this
# 234C instalments: (percent of tax due by then, months of interest)
INSTALMENTS_234C = [(15, 3), (45, 3), (75, 3), (100, 1)]

# ITR-1 eligibility
ITR1_INCOME_LIMIT = 5_000_000
ITR1_AGRICULTURAL_LIMIT = 5_000
