"""What a synthetic taxpayer looks like before it is turned into documents."""

from dataclasses import dataclass, field
from datetime import date

from taxengine.models import Deductions, HouseProperty, Profile

# Traps that leave a flag in the return, and how a correct system resolves each.
FLAG_RESOLUTION = {
    "AIS_INTEREST_MISSING": "auto_fixed",
    "DIVIDEND_UNREPORTED": "auto_fixed",
    "TWO_EMPLOYERS": "info",
    "TDS_MISMATCH": "auto_fixed",
    "DUPLICATE_DOCUMENT": "auto_fixed",
    "BELATED_FORCED_NEW": "info",
    "HRA_NO_LANDLORD_PAN": "needs_human",
    "UNEXPLAINED_SFT": "needs_human",
    "INCOME_OVER_50L": "needs_human",
    "FOREIGN_RSU": "needs_human",
    "VDA_TRADES": "needs_human",
}

# Traps that only change the figures (form, regime or deduction limits).
FIGURE_TRAPS = [
    "OLD_REGIME_CHEAPER",
    "LTCG_SMALL",
    "CG_NEEDS_ITR2",
    "PARENTS_SENIOR_80D",
    "SENIOR_80TTB",
]


@dataclass
class Trade:
    symbol: str
    qty: int
    buy_date: date
    sell_date: date
    buy_value: int
    sell_value: int

    @property
    def gain(self) -> int:
        return self.sell_value - self.buy_value

    @property
    def is_long_term(self) -> bool:
        return (self.sell_date - self.buy_date).days > 365


@dataclass
class CaseSpec:
    case_id: str
    name: str
    pan: str
    age: int
    metro: bool
    filing_date: date
    employers: list  # taxengine Employer; tds is the amount credited per the AIS
    tans: list
    form16_tds: list  # TDS printed on each Form 16
    bank: str
    deductions: Deductions
    declared_interest: int
    declared_dividends: int
    savings_interest: int = 0
    deposit_interest: int = 0
    dividends: int = 0
    trades: list = field(default_factory=list)
    rent_paid: int = 0
    landlord_name: str = ""
    landlord_pan: str | None = None
    home_loan_interest: int = 0
    property_purchase: int = 0
    vda_amount: int = 0
    foreign_rsu: bool = False
    duplicate_form16: bool = False
    traps: list = field(default_factory=list)

    @property
    def stcg(self) -> int:
        return sum(t.gain for t in self.trades if not t.is_long_term)

    @property
    def ltcg(self) -> int:
        return sum(t.gain for t in self.trades if t.is_long_term)

    def to_profile(self) -> Profile:
        """The true facts, in the form the tax engine takes."""
        house = None
        if self.home_loan_interest:
            house = HouseProperty("self_occupied", loan_interest=self.home_loan_interest)
        return Profile(
            age=self.age,
            employers=tuple(self.employers),
            savings_interest=self.savings_interest,
            deposit_interest=self.deposit_interest,
            dividends=self.dividends,
            house_property=house,
            stcg_111a=self.stcg,
            ltcg_112a=self.ltcg,
            deductions=self.deductions,
            rent_paid=self.rent_paid,
            metro=self.metro,
        )
