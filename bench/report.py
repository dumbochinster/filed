"""Turn saved runs into bench/results.md, bench/chart.png and bench/summary.csv.

python -m bench.report --cases data/cases --runs runs
"""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bench.metrics import across_repeats, score_case, summarise, trap_table

SYSTEM_LABELS = {"filed": "Filed (agents + tax engine)", "baseline": "Single prompt"}
COLORS = {"filed": "#1b6e8c", "baseline": "#c4572f"}


def load_truth(cases_dir):
    return {
        p.parent.name: json.loads(p.read_text(encoding="utf-8"))
        for p in Path(cases_dir).glob("*/truth.json")
    }


def load_runs(runs_dir, system, truth):
    """Scores grouped by repeat, however many cases each repeat covers."""
    by_rep = {}
    for path in sorted((Path(runs_dir) / system).glob("*_rep*.json")):
        case_id, rep = path.stem.rsplit("_rep", 1)
        if case_id in truth:
            result = json.loads(path.read_text(encoding="utf-8"))
            by_rep.setdefault(int(rep), []).append(score_case(result, truth[case_id]))
    return dict(sorted(by_rep.items()))


def pct(pair):
    mean, spread = pair
    if mean is None:
        return "n/a"
    return f"{mean * 100:.1f}%" + ("" if spread is None else f" ± {spread * 100:.1f}")


def number(pair, unit=""):
    mean, spread = pair
    if mean is None:
        return "n/a"
    return f"{mean:,.0f}{unit}" + ("" if spread is None else f" ± {spread:,.0f}")


METRIC_ROWS = [
    ("Exact return (form, regime, tax within Rs 10)", "exact_return_rate", pct),
    ("ITR form correct", "form_accuracy", pct),
    ("Regime choice correct", "regime_accuracy", pct),
    ("Mean absolute tax error, Rs", "mean_abs_error_rupees", number),
    ("Escalation recall (cases needing a person that were escalated)", "escalation_recall", pct),
    ("Escalation precision (escalations that were needed)", "escalation_precision", pct),
    (
        "False-automation rate (marked ready but wrong; lower is better)",
        "false_automation_rate",
        pct,
    ),
    ("Hands-off rate (finished correctly with no person)", "hands_off_rate", pct),
    ("Tokens per case", "tokens_per_case", number),
    ("Seconds per case", "seconds_per_case", number),
]


def failure_lines(scores_by_rep, limit=40):
    lines = []
    for rep, scores in scores_by_rep.items():
        for s in scores:
            if s["handled"] and not s["false_automation"]:
                continue
            what = []
            if s["truth_ready"]:
                what.append("exact return missed" if not s["exact"] else "")
                what.append("form wrong" if not s["form_ok"] else "")
                what.append("regime wrong" if not s["regime_ok"] else "")
                what.append(f"tax off by Rs {s['error']:,}" if s["error"] else "")
                if s["predicted_human"]:
                    what.append("sent to a person unnecessarily")
            else:
                what.append("marked ready although a person was needed")
            reason = ", ".join(w for w in what if w) or "wrong outcome"
            lines.append(
                f"- {s['case_id']} (repeat {rep}, traps: {', '.join(s['traps']) or 'none'}): {reason}"
            )
    return lines[:limit] + ([f"- ... and {len(lines) - limit} more"] if len(lines) > limit else [])


def write_chart(summary, path):
    metrics = [
        ("Exact return", "exact_return_rate"),
        ("Hands-off", "hands_off_rate"),
        ("Escalation recall", "escalation_recall"),
        ("False automation\n(lower is better)", "false_automation_rate"),
    ]
    systems = list(summary)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    width = 0.8 / len(systems)
    for i, system in enumerate(systems):
        values = [(summary[system][key][0] or 0) * 100 for _, key in metrics]
        errors = [(summary[system][key][1] or 0) * 100 for _, key in metrics]
        xs = [x + i * width for x in range(len(metrics))]
        bars = ax.bar(
            xs,
            values,
            width,
            yerr=errors,
            capsize=3,
            color=COLORS[system],
            label=SYSTEM_LABELS[system],
        )
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 2,
                f"{value:.0f}%",
                ha="center",
                fontsize=9,
            )
    ax.set_xticks([x + width * (len(systems) - 1) / 2 for x in range(len(metrics))])
    ax.set_xticklabels([label for label, _ in metrics])
    ax.set_ylim(0, 115)
    ax.set_ylabel("% of cases")
    ax.set_title(
        "Filed vs a single prompt on synthetic taxpayers (mean over repeats, bars show spread)"
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def complete_repeats(runs, n_cases, partial):
    """Keep repeats that cover every case. With `partial`, keep the cases every system finished."""
    if not partial:
        complete = {
            s: {r: sc for r, sc in reps.items() if len(sc) == n_cases} for s, reps in runs.items()
        }
        return {s: reps for s, reps in complete.items() if reps}
    kept = {s: {} for s in runs}
    for rep in set.intersection(*(set(reps) for reps in runs.values())):
        common = set.intersection(*({sc["case_id"] for sc in reps[rep]} for reps in runs.values()))
        for s, reps in runs.items():
            kept[s][rep] = [sc for sc in reps[rep] if sc["case_id"] in common]
    return {s: reps for s, reps in kept.items() if reps}


def build(cases_dir, runs_dir, out_dir, title="Benchmark results", partial=False):
    truth = load_truth(cases_dir)
    runs = {s: load_runs(runs_dir, s, truth) for s in SYSTEM_LABELS}
    runs = {s: r for s, r in runs.items() if r}
    runs = complete_repeats(runs, len(truth), partial)
    if not runs:
        raise SystemExit("no complete repeats found; run bench.run_bench first (or pass --partial)")
    summary = {s: across_repeats([summarise(sc) for sc in r.values()]) for s, r in runs.items()}
    meta_path = Path(runs_dir) / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if "replayed" in meta.get("model", ""):
        for metrics in summary.values():  # a replay takes no real time
            metrics["seconds_per_case"] = (None, None)
    out_dir = Path(out_dir)

    head = (
        "| Metric | "
        + " | ".join(SYSTEM_LABELS[s] for s in runs)
        + " |\n|---|"
        + "---|" * len(runs)
    )
    rows = [
        f"| {label} | " + " | ".join(fmt(summary[s][key]) for s in runs) + " |"
        for label, key, fmt in METRIC_ROWS
    ]
    traps = {s: trap_table(list(r.values())) for s, r in runs.items()}
    trap_rows = []
    for trap in sorted({t for table in traps.values() for t in table}):
        cells = []
        for s in runs:
            done, total = traps[s].get(trap, (0, 0))
            cells.append(f"{done}/{total}")
        trap_rows.append(f"| {trap} | " + " | ".join(cells) + " |")
    trap_head = (
        "| Trap | " + " | ".join(SYSTEM_LABELS[s] for s in runs) + " |\n|---|" + "---|" * len(runs)
    )
    failures = failure_lines(runs.get("filed", {})) or ["- none in the repeats that were run"]

    n_cases = len(next(iter(next(iter(runs.values())).values())))
    reps = {s: len(r) for s, r in runs.items()}
    text = f"""# {title}

Model: `{meta.get("model", "unknown")}`. Model reviewer: {meta.get("reviewer", "unknown")}. Cases: {n_cases} synthetic taxpayers. Complete repeats: {reps}. Run date: {meta.get("date", "unknown")}.
Every number below comes from `runs/`; nothing is estimated. Values are mean ± standard deviation across repeats.

## Headline

{head}
{chr(10).join(rows)}

![chart](chart.png)

## By trap

Each cell is how many times the trap was handled correctly out of how many times it appeared (all repeats pooled).
Handled means: escalated to a person when one is needed, otherwise an exact return.

{trap_head}
{chr(10).join(trap_rows)}

## Where Filed failed

{chr(10).join(failures)}

## How to read this

- Cases and answers are synthetic. The correct answer for each case comes from our tax engine applied to the true facts; the engine itself is checked by hand-worked tests (`tests/test_engine.py`). So this benchmark measures reading, reconciling and deciding, not the engine.
- The single-prompt baseline gets the same documents and the same model but no tax engine, no reconciliation step and no escalation rules.
- Repeats use temperature 0, so they mostly measure the provider's run-to-run variation rather than sampling noise.
- A case is "exact" only if the form, the regime and the final amount (within Rs 10) are all right.
"""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.md").write_text(text, encoding="utf-8")
    write_chart(summary, out_dir / "chart.png")
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["system", "metric", "mean", "std"])
        for system, metrics in summary.items():
            for key, (mean, spread) in metrics.items():
                writer.writerow([system, key, mean, spread])
    return out_dir / "results.md"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="data/cases")
    parser.add_argument("--runs", default="runs")
    parser.add_argument("--out", default="bench")
    parser.add_argument("--title", default="Benchmark results")
    parser.add_argument(
        "--partial", action="store_true", help="score only the cases every system finished"
    )
    args = parser.parse_args()
    print("wrote", build(args.cases, args.runs, args.out, args.title, args.partial))


if __name__ == "__main__":
    main()
