"""Hand-worked cases for the tax engine. The arithmetic is shown beside each expected value."""

from datetime import date

import pytest

from taxengine import capital_gains, interest
from taxengine.compute import cheaper_regime, compare_regimes, compute, slab_tax
from taxengine.deductions import interest_deduction
from taxengine.forms import choose_itr_form
from taxengine.models import Deductions, Employer, HouseProperty, Profile, UnsupportedProfile
from taxengine.money import round_down_to_100, round_to_10
from taxengine.rules import NEW_REGIME_SLABS
from taxengine.salary import house_property_income, hra_exemption


def salaried(gross, age=30, basic=None, **extra):
    employer = Employer(
        "Acme", gross_salary=gross, basic_da=basic or gross // 2, tds=extra.pop("tds", 0)
    )
    return Profile(age=age, employers=(employer,), **extra)


class TestRounding:
    def test_round_to_10(self):
        assert [round_to_10(n) for n in (1234, 1235, 1236, -1235, 0)] == [
            1230,
            1240,
            1240,
            -1240,
            0,
        ]

    def test_round_down_to_100(self):
        assert round_down_to_100(10_099) == 10_000


class TestSlabs:
    def test_new_regime_top_band(self):
        # 4-8L: 20,000; 8-12L: 40,000; 12-16L: 60,000; 16-20L: 80,000; 20-24L: 1,00,000;
        # 24-26L at 30%: 60,000
        assert (
            slab_tax(2_600_000, NEW_REGIME_SLABS)
            == 20_000 + 40_000 + 60_000 + 80_000 + 100_000 + 60_000
        )

    def test_income_inside_nil_band(self):
        assert slab_tax(300_000, NEW_REGIME_SLABS) == 0


class TestNewRegime:
    def test_12_75_lakh_salary_pays_nothing(self):
        # 12,75,000 - 75,000 standard deduction = 12,00,000; slab tax 60,000; rebate 60,000
        result = compute(salaried(1_275_000), "new")
        assert result.normal_income == 1_200_000
        assert result.slab_tax == 60_000 and result.rebate == 60_000
        assert result.net_payable == 0

    def test_marginal_relief_just_above_12_lakh(self):
        # taxable 12,01,000; slab tax 60,150; relief limits tax to the 1,000 above 12L
        # tax 1,000 + cess 40 = 1,040
        result = compute(salaried(1_276_000), "new")
        assert result.slab_tax == 60_150
        assert result.marginal_relief == 59_150
        assert result.net_payable == 1_040

    def test_no_relief_once_slab_tax_is_lower_than_excess(self):
        # taxable 14,25,000: 60,000 + 15% of 2,25,000 = 93,750; cess 3,750; total 97,500
        result = compute(salaried(1_500_000), "new")
        assert result.marginal_relief == 0
        assert result.tax_liability == 97_500

    def test_tds_is_credited_and_refund_is_negative(self):
        # liability 97,500 against 1,00,000 TDS -> refund of 2,500
        assert compute(salaried(1_500_000, tds=100_000), "new").net_payable == -2_500

    def test_second_employer_gets_no_second_standard_deduction(self):
        two = Profile(
            age=30, employers=(Employer("A", 600_000, 300_000), Employer("B", 600_000, 300_000))
        )
        assert compute(two, "new").standard_deduction == 75_000

    def test_employer_nps_is_allowed_up_to_14_percent(self):
        # basic 6,00,000 -> cap 84,000; paid 1,00,000
        employer = Employer("A", 1_500_000, 600_000, employer_nps=100_000)
        result = compute(Profile(age=30, employers=(employer,)), "new")
        assert result.deductions == 84_000

    def test_other_deductions_are_ignored(self):
        profile = salaried(1_500_000, deductions=Deductions(sec_80c=150_000))
        assert compute(profile, "new").deductions == 0


class TestOldRegime:
    def test_slab_tax_with_80c(self):
        # 10,00,000 - 50,000 - 1,50,000 = 8,00,000; 12,500 + 60,000 = 72,500; cess 2,900
        profile = salaried(1_000_000, deductions=Deductions(sec_80c=150_000))
        result = compute(profile, "old")
        assert result.normal_income == 800_000
        assert result.tax_liability == 75_400

    def test_rebate_at_exactly_5_lakh(self):
        # 5,50,000 - 50,000 = 5,00,000; tax 12,500 fully rebated
        result = compute(salaried(550_000), "old")
        assert result.normal_income == 500_000 and result.net_payable == 0

    def test_no_rebate_one_rupee_over_5_lakh(self):
        # 5,00,001: tax 12,500 + 20% of 1 = 12,500 (floor); cess 500 -> 13,000
        assert compute(salaried(550_001), "old").tax_liability == 13_000

    def test_senior_has_a_higher_nil_band(self):
        # 3,50,000 - 50,000 = 3,00,000 -> nil for a 65-year-old
        assert compute(salaried(350_000, age=65), "old").slab_tax == 0

    def test_professional_tax_is_capped_and_old_regime_only(self):
        employer = Employer("A", 800_000, 400_000, professional_tax=3_000)
        profile = Profile(age=30, employers=(employer,))
        assert compute(profile, "old").professional_tax == 2_500
        assert compute(profile, "new").professional_tax == 0


class TestHra:
    def employer_with(self, hra, basic):
        return Employer("A", gross_salary=basic * 2, basic_da=basic, hra_received=hra)

    def test_actual_hra_is_the_smallest(self):
        # HRA 1,80,000; rent 3,60,000 - 60,000 = 3,00,000; metro 50% of 6,00,000 = 3,00,000
        profile = Profile(
            age=30, employers=(self.employer_with(180_000, 600_000),), rent_paid=360_000, metro=True
        )
        assert hra_exemption(profile) == 180_000

    def test_rent_minus_ten_percent_is_the_smallest(self):
        # HRA 2,40,000; rent 2,70,000 - 60,000 = 2,10,000; metro 3,00,000
        profile = Profile(
            age=30, employers=(self.employer_with(240_000, 600_000),), rent_paid=270_000, metro=True
        )
        assert hra_exemption(profile) == 210_000

    def test_non_metro_forty_percent_is_the_smallest(self):
        # HRA 3,00,000; rent 4,80,000 - 60,000 = 4,20,000; 40% of 6,00,000 = 2,40,000
        profile = Profile(
            age=30,
            employers=(self.employer_with(300_000, 600_000),),
            rent_paid=480_000,
            metro=False,
        )
        assert hra_exemption(profile) == 240_000

    def test_no_rent_no_exemption(self):
        profile = Profile(age=30, employers=(self.employer_with(240_000, 600_000),))
        assert hra_exemption(profile) == 0

    def test_hra_reduces_old_regime_income_only(self):
        profile = Profile(
            age=30, employers=(self.employer_with(180_000, 600_000),), rent_paid=360_000, metro=True
        )
        assert compute(profile, "old").hra_exemption == 180_000
        assert compute(profile, "new").hra_exemption == 0


class TestHouseProperty:
    def test_self_occupied_interest_capped_at_2_lakh_in_old_regime(self):
        profile = Profile(
            age=30, house_property=HouseProperty("self_occupied", loan_interest=250_000)
        )
        assert house_property_income(profile, "old") == -200_000
        assert house_property_income(profile, "new") == 0

    def test_let_out_income(self):
        # rent 3,00,000 - municipal 20,000 = 2,80,000; 30% off = 1,96,000; interest 1,00,000 -> 96,000
        prop = HouseProperty(
            "let_out", rent_received=300_000, municipal_tax=20_000, loan_interest=100_000
        )
        profile = Profile(age=30, house_property=prop)
        assert house_property_income(profile, "new") == 96_000

    def test_let_out_loss_cannot_be_set_off_in_new_regime(self):
        prop = HouseProperty("let_out", rent_received=120_000, loan_interest=300_000)
        profile = Profile(age=30, house_property=prop)
        assert house_property_income(profile, "new") == 0
        assert house_property_income(profile, "old") == -200_000


class TestInterestDeduction:
    def test_under_60_gets_80tta_on_savings_only(self):
        profile = Profile(age=40, savings_interest=15_000, deposit_interest=90_000)
        assert interest_deduction(profile) == 10_000

    def test_senior_gets_80ttb_on_everything(self):
        profile = Profile(age=65, savings_interest=20_000, deposit_interest=80_000)
        assert interest_deduction(profile) == 50_000


class TestHealthDeduction:
    def test_senior_parents_raise_the_limit(self):
        base = {"age": 30, "employers": (Employer("A", 1_000_000, 500_000),)}
        young = Profile(**base, deductions=Deductions(health_self=30_000, health_parents=60_000))
        senior = Profile(
            **base,
            deductions=Deductions(health_self=30_000, health_parents=60_000, parents_senior=True),
        )
        assert compute(young, "old").deductions == 25_000 + 25_000
        assert compute(senior, "old").deductions == 25_000 + 50_000


class TestCapitalGains:
    def test_ltcg_under_exemption_is_not_taxed(self):
        assert capital_gains.taxable_gains(0, 125_000) == (0, 0)

    def test_ltcg_over_exemption(self):
        # 2,25,000 - 1,25,000 = 1,00,000 at 12.5% = 12,500
        stcg, ltcg = capital_gains.taxable_gains(0, 225_000)
        assert capital_gains.special_rate_tax(stcg, ltcg) == 12_500

    def test_stcg_at_20_percent(self):
        assert capital_gains.special_rate_tax(100_000, 0) == 20_000

    def test_rebate_does_not_shelter_stcg(self):
        # normal income 12,00,000 -> nil slab tax after rebate; STCG tax 20,000; cess 800
        profile = salaried(1_275_000, stcg_111a=100_000)
        assert compute(profile, "new").tax_liability == 20_800

    def test_unused_basic_exemption_shelters_gains(self):
        # normal income 2,00,000; shortfall 2,00,000; STCG 3,00,000 -> 1,00,000 taxed = 20,000; cess 800
        profile = salaried(275_000, stcg_111a=300_000)
        result = compute(profile, "new")
        assert result.stcg_taxable == 100_000
        assert result.tax_liability == 20_800


class TestFilingForm:
    def test_plain_salary_is_itr1(self):
        assert choose_itr_form(salaried(900_000)) == ("ITR-1", [])

    def test_small_ltcg_stays_itr1(self):
        assert choose_itr_form(salaried(900_000, ltcg_112a=125_000))[0] == "ITR-1"

    def test_large_ltcg_or_any_stcg_needs_itr2(self):
        assert choose_itr_form(salaried(900_000, ltcg_112a=125_001))[0] == "ITR-2"
        assert choose_itr_form(salaried(900_000, stcg_111a=1))[0] == "ITR-2"


class TestLateFiling:
    def test_months_late(self):
        due = date(2026, 7, 31)
        assert interest.months_late(date(2026, 7, 31), due) == 0
        assert interest.months_late(date(2026, 8, 1), due) == 1
        assert interest.months_late(date(2026, 8, 31), due) == 1
        assert interest.months_late(date(2026, 9, 1), due) == 2
        assert interest.months_late(date(2026, 12, 31), due) == 5

    def test_interest_234a(self):
        # 50,000 unpaid, filed 1 Sep -> 2 months at 1%
        assert interest.interest_234a(50_000, date(2026, 9, 1)) == 1_000

    def test_fee_234f(self):
        late = date(2026, 12, 20)
        assert interest.fee_234f(800_000, late, 400_000) == 5_000
        assert interest.fee_234f(450_000, late, 400_000) == 1_000
        assert interest.fee_234f(350_000, late, 400_000) == 0
        assert interest.fee_234f(800_000, date(2026, 7, 31), 400_000) == 0

    def test_234b_and_234c_for_a_one_lakh_gap(self):
        filed = date(2026, 7, 31)
        assert interest.interest_234b(100_000, filed) == 4_000  # Apr to Jul = 4 months
        assert interest.interest_234c(100_000) == 5_050  # 5.05% across the instalments
        assert interest.interest_234b(9_000, filed) == 0

    def test_belated_filer_with_no_tax_still_pays_the_fee(self):
        # taxable 10,00,000 is fully rebated, but the late fee is 5,000
        result = compute(salaried(1_075_000), "new", date(2026, 12, 15))
        assert result.tax_liability == 0
        assert result.net_payable == 5_000

    def test_belated_return_has_no_old_regime(self):
        results = compare_regimes(salaried(1_000_000), date(2026, 12, 15))
        assert list(results) == ["new"]
        with pytest.raises(UnsupportedProfile):
            compute(salaried(1_000_000), "old", date(2026, 12, 15))


class TestRegimeChoice:
    def test_heavy_deductions_favour_the_old_regime(self):
        # 25L salary, 4.75L HRA exemption, 80C, 80CCD(1B), 80D and a 2L home loan:
        # old regime tax about 2.78L against about 3.08L under the new regime
        employer = Employer("Acme", 2_500_000, 1_250_000, hra_received=500_000)
        profile = Profile(
            age=35,
            employers=(employer,),
            rent_paid=600_000,
            metro=True,
            deductions=Deductions(sec_80c=150_000, sec_80ccd_1b=50_000, health_self=25_000),
            house_property=HouseProperty("self_occupied", loan_interest=200_000),
        )
        assert cheaper_regime(compare_regimes(profile)) == "old"

    def test_plain_salary_favours_the_new_regime(self):
        assert cheaper_regime(compare_regimes(salaried(1_200_000))) == "new"


class TestScopeLimits:
    def test_income_above_50_lakh_is_refused(self):
        with pytest.raises(UnsupportedProfile):
            compute(salaried(6_000_000), "new")

    def test_advance_tax_is_refused(self):
        with pytest.raises(UnsupportedProfile):
            compute(salaried(1_000_000, advance_tax=5_000), "new")

    def test_empty_profile_owes_nothing(self):
        assert compute(Profile(age=30), "new").net_payable == 0
