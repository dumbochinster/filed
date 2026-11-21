"""Run the benchmark. Resumable: finished runs are kept and skipped next time.

python -m bench.run_bench --cases data/cases --repeats 3
python -m bench.run_bench --limit 5 --repeats 1     # quick trial on 5 cases
"""

import argparse
import functools
import json
from datetime import date
from pathlib import Path

from agents.llm import CachedClient, NoModel, QuotaExhausted
from agents.pipeline import run_case as run_filed
from bench import baseline


def is_infrastructure_error(error):
    """Network or provider trouble (rate limits, outages). Anything else is a bug and should crash."""
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True
    return type(error).__module__.split(".")[0] in ("google", "anthropic", "httpx", "httpcore")


def case_folders(cases_dir, limit=None):
    folders = sorted(p for p in Path(cases_dir).iterdir() if (p / "truth.json").exists())
    return folders[:limit] if limit else folders


def run(cases_dir, repeats, systems, make_llm, out_dir, limit=None, log=print, reviewer="off"):
    """Run every (repeat, case, system) that has no saved result yet. Returns the number run."""
    runners = {
        "filed": functools.partial(run_filed, reviewer=reviewer),
        "baseline": baseline.run_case,
    }
    out_dir = Path(out_dir)
    folders = case_folders(cases_dir, limit)
    done = 0
    for rep in range(1, repeats + 1):
        for folder in folders:
            for name in systems:
                path = out_dir / name / f"{folder.name}_rep{rep}.json"
                if path.exists():
                    continue
                try:
                    result = runners[name](folder, make_llm(rep, folder))
                except QuotaExhausted as error:
                    log(f"stopping: {error}. Run the same command again after the quota resets.")
                    return done
                except Exception as error:
                    if not is_infrastructure_error(error):
                        raise
                    # Not the system's fault, so the run is left unscored and retried next time.
                    log(f"skipped {name} {folder.name} rep{rep}: {type(error).__name__}: {error}")
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result.to_dict(), default=str), encoding="utf-8")
                done += 1
                log(f"{name:8s} {folder.name} rep{rep}: {result.status}")
    return done


def main():
    from agents.llm import make_client

    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="data/cases")
    parser.add_argument("--out", default="runs")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--systems", default="filed,baseline")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--replay-model", default="cached answers")
    parser.add_argument(
        "--replay-from",
        help="replay cached model answers from this runs folder; no model is called",
    )
    parser.add_argument("--reviewer", choices=["off", "advisory", "gate"], default="off")
    args = parser.parse_args()

    clients = {}

    def make_llm(rep, folder):
        if args.replay_from and rep not in clients:
            source = Path(args.replay_from) / "cache" / f"rep{rep}"
            clients[rep] = CachedClient(NoModel(args.replay_model), source)
        if rep not in clients:
            clients[rep] = make_client(cache_dir=Path(args.out) / "cache" / f"rep{rep}")
        return clients[rep]

    systems = args.systems.split(",")
    # Record the settings first, so a run that is stopped early still says how it was configured.
    meta = {
        "model": make_llm(1, None).model
        + (" (replayed from saved answers)" if args.replay_from else ""),
        "repeats": args.repeats,
        "reviewer": args.reviewer,
        "cases": len(case_folders(args.cases, args.limit)),
        "date": date.today().isoformat(),
    }
    Path(args.out).mkdir(parents=True, exist_ok=True)
    Path(args.out, "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    run(args.cases, args.repeats, systems, make_llm, args.out, args.limit, reviewer=args.reviewer)


if __name__ == "__main__":
    main()
