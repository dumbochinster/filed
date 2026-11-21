"""Seeded random taxpayers. The same seed always gives the same people."""

import string
from dataclasses import replace
from datetime import date, timedelta

from synth.spec import CaseSpec, Trade
from taxengine.compute import compute
from taxengine.models import Deductions, Employer, Profile, UnsupportedProfile
from taxengine.money import round_down_to_100

FIRST = ["Asha", "Ravi", "Meera", "Karthik", "Divya", "Arjun", "Sneha", "Imran", "Pooja", "Vikram"]
LAST = ["Rao", "Iyer", "Nair", "Sharma", "Khan", "Patel", "Reddy", "Menon", "Das", "Gupta"]
COMPANIES = [
    "Zenith Software",
    "Orbit Analytics",
    "Kaveri Textiles",
    "Nimbus Cloud",
    "Harbor Logistics",
]
BANKS = ["HDFC Bank", "State Bank of India", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank"]
STOCKS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ITC", "LT", "SBIN"]

# Traps that need the old regime to be the cheaper choice to make sense.
WANTS_OLD_REGIME = {"OLD_REGIME_CHEAPER", "PARENTS_SENIOR_80D"}


def letters(rng, n):
    return "".join(rng.choice(string.ascii_uppercase) for _ in range(n))


def digits(rng, n):
    return "".join(rng.choice(string.digits) for _ in range(n))


def make_pan(rng):
    return letters(rng, 5) + digits(rng, 4) + letters(rng, 1)


def make_tan(rng):
    return letters(rng, 4) + digits(rng, 5) + letters(rng, 1)


def thousands(value):
    return int(round(value, -3))


def pick_salary(rng, traps):
    if "INCOME_OVER_50L" in traps:
        return thousands(rng.uniform(5_500_000, 9_000_000))
    if WANTS_OLD_REGIME & set(traps):
        return thousands(rng.uniform(2_200_000, 3_200_000))
    if "TDS_MISMATCH" in traps:
        return thousands(rng.uniform(1_800_000, 3_000_000))
    return thousands(
        rng.choice([rng.uniform(400_000, 1_300_000), rng.uniform(1_300_000, 2_400_000)])
    )


def make_employer(rng, gross, rents, nps):
    basic = thousands(gross * rng.uniform(0.40, 0.50))
    return Employer(
        name=rng.choice(COMPANIES),
        gross_salary=gross,
        basic_da=basic,
        hra_received=thousands(basic * 0.4) if rents else 0,
        professional_tax=2_400,
        employer_nps=thousands(basic * 0.10) if nps else 0,
    )


def make_trades(rng, stcg, ltcg):
    """Buy/sell rows that add up to the wanted gains."""
    trades = []
    for gain, long_term in ((stcg, False), (ltcg, True)):
        if gain <= 0:
            continue
        sell = date(2025, 6, 1) + timedelta(days=rng.randint(0, 240))
        held = rng.randint(400, 700) if long_term else rng.randint(20, 300)
        buy_value = thousands(rng.uniform(100_000, 600_000))
        trades.append(
            Trade(
                rng.choice(STOCKS),
                rng.randint(5, 200),
                sell - timedelta(days=held),
                sell,
                buy_value,
                buy_value + gain,
            )
        )
    return trades


def pick_filing_date(rng, belated):
    if belated:
        return date(2026, 8, 5) + timedelta(days=rng.randint(0, 135))
    return date(2026, 7, 5) + timedelta(days=rng.randint(0, 26))


def withheld_tax(employer, age):
    """What an employer would deduct if the person had no other income."""
    profile = Profile(age=age, employers=(employer,))
    try:
        return round_down_to_100(compute(profile, "new").tax_liability)
    except UnsupportedProfile:
        # Above 50 lakh the real withholding includes surcharge; a rough figure is enough here.
        return round_down_to_100(int(employer.gross_salary * 0.28))


def make_case(index, rng, traps):
    traps = list(traps)
    has = set(traps).__contains__
    age = rng.randint(61, 72) if has("SENIOR_80TTB") else rng.randint(23, 55)
    rents = has("HRA_NO_LANDLORD_PAN") or has("OLD_REGIME_CHEAPER") or rng.random() < 0.5
    nps = rng.random() < 0.2
    gross = pick_salary(rng, traps)

    grosses = [gross]
    if has("TWO_EMPLOYERS"):
        first_part = thousands(gross * rng.uniform(0.3, 0.7))
        grosses = [first_part, gross - first_part]
    employers = [
        make_employer(rng, g, rents and i == 0, nps and i == 0) for i, g in enumerate(grosses)
    ]
    employers = [replace(e, name=f"{e.name} {i + 1}") for i, e in enumerate(employers)]
    form16_tds = [withheld_tax(e, age) for e in employers]
    employers = [replace(e, tds=t) for e, t in zip(employers, form16_tds)]
    if has("TDS_MISMATCH") and form16_tds[0] > 0:
        employers[0] = replace(
            employers[0], tds=form16_tds[0] - max(100, round_down_to_100(form16_tds[0] // 8))
        )

    rent_paid = landlord_pan = None
    if rents:
        rent_paid = thousands(employers[0].hra_received * rng.uniform(1.1, 1.6)) or 120_000
        if has("HRA_NO_LANDLORD_PAN"):
            rent_paid = max(rent_paid, 150_000)
        elif rent_paid > 100_000 or rng.random() < 0.4:
            landlord_pan = make_pan(rng)

    wants_old = bool(WANTS_OLD_REGIME & set(traps))
    deductions = Deductions(
        sec_80c=rng.choice([0, 50_000, 100_000, 150_000]) if not wants_old else 150_000,
        sec_80ccd_1b=50_000 if wants_old else rng.choice([0, 0, 50_000]),
        health_self=rng.choice([0, 15_000, 25_000]) if not wants_old else 25_000,
        health_parents=rng.choice([0, 0, 20_000]),
        parents_senior=False,
    )
    if has("PARENTS_SENIOR_80D"):
        deductions = replace(
            deductions, health_parents=rng.randint(40_000, 55_000), parents_senior=True
        )

    savings = thousands(rng.uniform(2_000, 30_000))
    deposit = thousands(rng.uniform(20_000, 90_000)) if rng.random() < 0.4 else 0
    if has("SENIOR_80TTB"):
        deposit = thousands(rng.uniform(60_000, 120_000))
    dividends = thousands(rng.uniform(2_000, 30_000)) if rng.random() < 0.35 else 0
    if has("AIS_INTEREST_MISSING") and deposit == 0:
        deposit = thousands(rng.uniform(15_000, 60_000))
    if has("DIVIDEND_UNREPORTED") and dividends == 0:
        dividends = thousands(rng.uniform(5_000, 40_000))

    stcg = ltcg = 0
    if has("LTCG_SMALL"):
        ltcg = thousands(rng.uniform(40_000, 120_000))
    if has("CG_NEEDS_ITR2"):
        stcg = thousands(rng.uniform(20_000, 150_000))
        ltcg = thousands(rng.uniform(150_000, 400_000)) if rng.random() < 0.6 else 0
    elif not has("LTCG_SMALL") and rng.random() < 0.15:
        ltcg = thousands(rng.uniform(20_000, 110_000))

    interest = savings + deposit
    first = rng.choice(FIRST)
    return CaseSpec(
        case_id=f"case_{index:03d}",
        name=f"{first} {rng.choice(LAST)}",
        pan=make_pan(rng),
        age=age,
        metro=rng.random() < 0.5,
        filing_date=pick_filing_date(rng, has("BELATED_FORCED_NEW")),
        employers=employers,
        tans=[make_tan(rng) for _ in employers],
        form16_tds=form16_tds,
        bank=rng.choice(BANKS),
        deductions=deductions,
        declared_interest=0 if has("AIS_INTEREST_MISSING") else interest,
        declared_dividends=0 if has("DIVIDEND_UNREPORTED") else dividends,
        savings_interest=savings,
        deposit_interest=deposit,
        dividends=dividends,
        trades=make_trades(rng, stcg, ltcg),
        rent_paid=rent_paid or 0,
        landlord_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}" if rents else "",
        landlord_pan=landlord_pan,
        home_loan_interest=rng.choice([0, 0, 120_000, 200_000]) if not wants_old else 200_000,
        property_purchase=rng.randint(40, 120) * 100_000 if has("UNEXPLAINED_SFT") else 0,
        vda_amount=thousands(rng.uniform(50_000, 400_000)) if has("VDA_TRADES") else 0,
        foreign_rsu=has("FOREIGN_RSU"),
        duplicate_form16=has("DUPLICATE_DOCUMENT"),
        traps=traps,
    )
