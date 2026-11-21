"""Plain data types shared by the tax engine. All money is in whole rupees."""

from dataclasses import dataclass, field
from datetime import date

from taxengine import rules


class UnsupportedProfile(Exception):
    """The case is outside what the engine models; a human has to handle it."""

    def __init__(self, message: str, code: str = "OUT_OF_SCOPE"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Employer:
    name: str
    gross_salary: int  # taxable salary before exemptions and standard deduction
    basic_da: int
    hra_received: int = 0
    professional_tax: int = 0
    employer_nps: int = 0
    tds: int = 0


@dataclass(frozen=True)
class HouseProperty:
    kind: str  # "self_occupied" or "let_out"
    rent_received: int = 0
    municipal_tax: int = 0
    loan_interest: int = 0


@dataclass(frozen=True)
class Deductions:
    sec_80c: int = 0
    sec_80ccd_1b: int = 0
    health_self: int = 0
    health_parents: int = 0
    parents_senior: bool = False


@dataclass(frozen=True)
class Profile:
    age: int
    employers: tuple = ()
    savings_interest: int = 0
    deposit_interest: int = 0
    dividends: int = 0
    house_property: HouseProperty | None = None
    stcg_111a: int = 0
    ltcg_112a: int = 0
    deductions: Deductions = field(default_factory=Deductions)
    rent_paid: int = 0
    metro: bool = False
    other_tds: int = 0  # TDS on interest, dividends and the like
    advance_tax: int = 0
    govt_employee: bool = False

    @property
    def age_group(self) -> str:
        if self.age >= 80:
            return "super_senior"
        return "senior" if self.age >= 60 else "regular"

    @property
    def total_tds(self) -> int:
        return sum(e.tds for e in self.employers) + self.other_tds


@dataclass
class Computation:
    regime: str
    filing_date: date
    gross_salary: int = 0
    hra_exemption: int = 0
    standard_deduction: int = 0
    professional_tax: int = 0
    salary_income: int = 0
    house_property_income: int = 0
    other_income: int = 0
    deductions: int = 0
    normal_income: int = 0
    stcg_taxable: int = 0
    ltcg_taxable: int = 0
    total_income: int = 0
    slab_tax: int = 0
    rebate: int = 0
    marginal_relief: int = 0
    special_tax: int = 0
    cess: int = 0
    tax_liability: int = 0
    taxes_paid: int = 0
    interest_234a: int = 0
    interest_234b: int = 0
    interest_234c: int = 0
    fee_234f: int = 0
    net_payable: int = 0  # positive: pay; negative: refund
    notes: list = field(default_factory=list)

    @property
    def is_belated(self) -> bool:
        return self.filing_date > rules.DUE_DATE
