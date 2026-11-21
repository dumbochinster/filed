"""How well does a model read the PDFs? Compares extracted fields with what the generator wrote.

    python -m bench.extraction_check --cases data/heldout --limit 20 --out bench/extraction_qwen.md

The provider and model come from .env (or FILED_PROVIDER / FILED_MODEL in the environment).
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from agents import intake
from agents.documents import load_case
from agents.llm import make_client


def kind_of(entry):
    keys = entry["keys"]
    if "Interest Certificate" in keys:
        return "interest_certificate"
    if "Rent Receipts" in keys:
        return "rent_receipts"
    return "form16"


def find_extracted(extraction, entry):
    """The extracted record that belongs to this oracle entry, or None if it was not read."""
    kind = kind_of(entry)
    if kind == "form16":
        return next((f for f in extraction.form16s if f["tan"] == entry["keys"][1]), None)
    records = {
        "interest_certificate": extraction.interest_certificates,
        "rent_receipts": extraction.rent_receipts,
    }[kind]
    return records[0] if records else None


def check(cases_dir, llm, limit=None):
    """Returns (per-field [correct, total], per-kind [exact documents, total], mismatches)."""
    folders = sorted(p for p in Path(cases_dir).iterdir() if (p / "truth.json").exists())[:limit]
    fields = defaultdict(lambda: [0, 0])
    docs = defaultdict(lambda: [0, 0])
    mismatches = []
    for folder in folders:
        truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
        extraction = intake.run(llm, load_case(folder))
        for entry in truth["oracle_extractions"]:
            kind = kind_of(entry)
            got = find_extracted(extraction, entry)
            exact = got is not None
            for name, expected in entry["fields"].items():
                right = got is not None and got.get(name) == expected
                fields[(kind, name)][0] += right
                fields[(kind, name)][1] += 1
                if not right:
                    exact = False
                    mismatches.append(
                        f"{folder.name} {kind}.{name}: expected {expected!r}, got {got.get(name)!r}"
                        if got
                        else f"{folder.name} {kind}.{name}: document not read"
                    )
            docs[kind][0] += exact
            docs[kind][1] += 1
    return fields, docs, mismatches


def to_markdown(model, fields, docs, mismatches, n_cases):
    lines = [
        f"# Document reading check: `{model}`",
        "",
        (
            f"{n_cases} synthetic cases. Each field is compared with the value the generator wrote "
            "into the PDF; a document counts as exact only if every field is right."
        ),
        "",
        "| Document | Read exactly |",
        "|---|---|",
    ]
    lines += [
        f"| {kind} | {ok}/{total} ({ok / total:.0%}) |"
        for kind, (ok, total) in sorted(docs.items())
    ]
    lines += ["", "| Field | Correct |", "|---|---|"]
    for (kind, name), (ok, total) in sorted(fields.items()):
        lines.append(f"| {kind}.{name} | {ok}/{total} |")
    lines += ["", "## Mistakes", ""]
    lines += [f"- {m}" for m in mismatches[:40]] or ["- none"]
    if len(mismatches) > 40:
        lines.append(f"- ... and {len(mismatches) - 40} more")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="data/heldout")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--cache")
    parser.add_argument("--out")
    args = parser.parse_args()
    llm = make_client(cache_dir=args.cache)
    fields, docs, mismatches = check(args.cases, llm, args.limit)
    n_cases = len(
        [p for p in Path(args.cases).iterdir() if (p / "truth.json").exists()][: args.limit]
    )
    text = to_markdown(llm.model, fields, docs, mismatches, n_cases)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
