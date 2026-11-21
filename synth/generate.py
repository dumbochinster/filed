"""Generate synthetic cases: python -m synth.generate --count 50 --seed 7"""

import argparse
import json
import random
import shutil
from pathlib import Path

from synth.people import WANTS_OLD_REGIME, make_case
from synth.render import render_case
from synth.spec import FLAG_RESOLUTION
from taxengine.compute import cheaper_regime, compare_regimes
from taxengine.forms import choose_itr_form
from taxengine.models import UnsupportedProfile

PRIMARY_TRAPS = [
    "AIS_INTEREST_MISSING",
    "DIVIDEND_UNREPORTED",
    "TWO_EMPLOYERS",
    "TDS_MISMATCH",
    "DUPLICATE_DOCUMENT",
    "OLD_REGIME_CHEAPER",
    "BELATED_FORCED_NEW",
    "LTCG_SMALL",
    "CG_NEEDS_ITR2",
    "HRA_NO_LANDLORD_PAN",
    "PARENTS_SENIOR_80D",
    "SENIOR_80TTB",
    "UNEXPLAINED_SFT",
    "INCOME_OVER_50L",
    "FOREIGN_RSU",
    "VDA_TRADES",
]
SECONDARY_TRAPS = [
    "TWO_EMPLOYERS",
    "AIS_INTEREST_MISSING",
    "DIVIDEND_UNREPORTED",
    "DUPLICATE_DOCUMENT",
]
CLEAN_SHARE = 0.3


def plan_traps(count, rng):
    """One list of traps per case: about 30% clean, the rest one main trap plus maybe a small one."""
    clean = round(count * CLEAN_SHARE)
    plans = [[] for _ in range(clean)]
    for i in range(count - clean):
        traps = [PRIMARY_TRAPS[i % len(PRIMARY_TRAPS)]]
        extra = rng.choice(SECONDARY_TRAPS)
        if rng.random() < 0.3 and extra not in traps:
            traps.append(extra)
        plans.append(traps)
    rng.shuffle(plans)
    return plans


def build_truth(spec):
    """What a perfect firm would produce for this case, from the true facts."""
    flags = {t: FLAG_RESOLUTION[t] for t in spec.traps if t in FLAG_RESOLUTION}
    expected = {
        "status": "ready_to_file",
        "flags": flags,
        "itr_form": None,
        "regime": None,
        "tax_liability": None,
        "net_payable": None,
    }
    needs_human = "needs_human" in flags.values()
    try:
        profile = spec.to_profile()
        results = compare_regimes(profile, spec.filing_date)
        regime = cheaper_regime(results)
        if not needs_human:
            expected.update(
                itr_form=choose_itr_form(profile)[0],
                regime=regime,
                tax_liability=results[regime].tax_liability,
                net_payable=results[regime].net_payable,
            )
    except UnsupportedProfile:
        needs_human = True
    if needs_human:
        expected["status"] = "needs_human"
    return expected


def make_one(index, seed, traps):
    """Build a case, retrying with new random draws when a trap needs the old regime to win."""
    wants_old = bool(WANTS_OLD_REGIME & set(traps))
    for attempt in range(40):
        spec = make_case(index, random.Random(f"{seed}-{index}-{attempt}"), traps)
        truth = build_truth(spec)
        if not wants_old or truth["regime"] == "old":
            return spec, truth
    return spec, truth


def generate(count, seed, out_dir):
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    plans = plan_traps(count, random.Random(seed))
    for index, traps in enumerate(plans, start=1):
        spec, truth = make_one(index, seed, traps)
        folder = out_dir / spec.case_id
        oracle = render_case(spec, folder)
        record = {
            "case_id": spec.case_id,
            "traps": spec.traps,
            "expected": truth,
            "oracle_extractions": oracle,
        }
        (folder / "truth.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return out_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="data/cases")
    args = parser.parse_args()
    generate(args.count, args.seed, args.out)
    print(f"wrote {args.count} cases to {args.out}")


if __name__ == "__main__":
    main()
