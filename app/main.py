"""Filed demo app. Run with: streamlit run app/main.py"""

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import LLMError, make_client
from agents.pipeline import run_case
from synth.generate import generate

CASES = ROOT / "data" / "cases"
RUNS = ROOT / "runs"
APP_RESULTS = RUNS / "app"
APPROVALS = RUNS / "approvals.json"
STATUS_LABEL = {"ready_to_file": "Ready to file", "needs_human": "Needs the tax expert"}


def case_ids():
    return (
        sorted(p.name for p in CASES.iterdir() if (p / "truth.json").exists())
        if CASES.exists()
        else []
    )


def saved_results():
    """Results from the app and from the benchmark's first repeat, newest source winning."""
    results = {}
    for folder in (RUNS / "filed", APP_RESULTS):
        pattern = "*_rep1.json" if folder.name == "filed" else "*.json"
        for path in sorted(folder.glob(pattern)) if folder.exists() else []:
            results[path.stem.replace("_rep1", "")] = json.loads(path.read_text(encoding="utf-8"))
    return results


def load_approvals():
    return json.loads(APPROVALS.read_text(encoding="utf-8")) if APPROVALS.exists() else {}


def save_approvals(data):
    APPROVALS.parent.mkdir(parents=True, exist_ok=True)
    APPROVALS.write_text(json.dumps(data), encoding="utf-8")


def show_result(result):
    label = STATUS_LABEL.get(result["status"], result["status"])
    (st.success if result["status"] == "ready_to_file" else st.warning)(label)
    if result.get("itr_form"):
        cols = st.columns(3)
        cols[0].metric("Form", result["itr_form"])
        cols[1].metric("Regime", result["regime"].title())
        net = result["net_payable"]
        cols[2].metric("Refund" if net < 0 else "Payable", f"Rs {abs(net):,}")
        st.markdown(result["computation_sheet"])
    if result["flags"]:
        st.subheader("What we found")
        for flag in result["flags"]:
            st.write(
                f"**{flag['code']}** ({flag['resolution'].replace('_', ' ')}): {flag['message']}"
            )
    if result["questions"]:
        st.subheader("Questions for the tax expert")
        for q in result["questions"]:
            st.write(f"- {q['question']}")
    if result.get("client_note"):
        with st.expander("Note to the client"):
            st.text(result["client_note"])
    if result.get("itr_json"):
        st.download_button(
            "Download draft return (JSON)",
            json.dumps(result["itr_json"], indent=2),
            file_name=f"{result['case_id']}_draft_return.json",
        )


def page_new_return():
    st.header("New return")
    ids = case_ids()
    if not ids:
        st.info("No sample clients yet.")
        if st.button("Generate 20 sample clients"):
            generate(20, 7, CASES)
            st.rerun()
        return
    case = st.selectbox("Client", ids)
    st.caption(
        "Documents: "
        + ", ".join(sorted(p.name for p in (CASES / case).iterdir() if p.name != "truth.json"))
    )
    saved = saved_results().get(case)
    if saved and st.checkbox("Show the saved result instead of running again", value=True):
        show_result(saved)
        return
    if not st.button("Prepare return", type="primary"):
        return
    try:
        llm = make_client(cache_dir=RUNS / "cache" / "app")
    except LLMError as error:
        st.error(f"{error}. Copy .env.example to .env and add your key, then restart the app.")
        return
    with st.status("Preparing the return", expanded=True) as status:
        result = run_case(
            CASES / case, llm, on_event=lambda step, msg: st.write(f"**{step}**: {msg}")
        )
        status.update(label="Done", state="complete")
    APP_RESULTS.mkdir(parents=True, exist_ok=True)
    (APP_RESULTS / f"{case}.json").write_text(
        json.dumps(result.to_dict(), default=str), encoding="utf-8"
    )
    show_result(result.to_dict())


def page_expert_queue():
    st.header("Tax expert queue")
    results = saved_results()
    if not results:
        st.info("No prepared returns yet. Prepare one under New return, or run the benchmark.")
        return
    approvals = load_approvals()
    waiting = {c: r for c, r in results.items() if r["status"] == "needs_human"}
    cols = st.columns(3)
    cols[0].metric("Clients", len(results))
    cols[1].metric("Finished with no person", len(results) - len(waiting))
    cols[2].metric("Questions for the expert", sum(len(r["questions"]) for r in waiting.values()))
    for case, result in sorted(waiting.items()):
        done = approvals.get(case, [])
        with st.expander(f"{case}: {len(result['questions']) - len(done)} open question(s)"):
            for i, q in enumerate(result["questions"]):
                st.write(f"**{q['question']}**")
                st.caption(q["detail"])
                if i in done:
                    st.write("Resolved")
                elif st.button("Mark resolved", key=f"{case}-{i}"):
                    approvals[case] = done + [i]
                    save_approvals(approvals)
                    st.rerun()


def page_results():
    st.header("Benchmark results")
    report = ROOT / "bench" / "results.md"
    if not report.exists():
        st.info(
            "The benchmark has not been run yet: python -m bench.run_bench, then python -m bench.report."
        )
        return
    st.markdown(report.read_text(encoding="utf-8").replace("![chart](chart.png)", ""))
    chart = ROOT / "bench" / "chart.png"
    if chart.exists():
        st.image(str(chart))


st.set_page_config(page_title="Filed", layout="wide")
st.sidebar.title("Filed")
st.sidebar.caption("An agent-run income-tax firm")
page = st.sidebar.radio("Page", ["New return", "Tax expert queue", "Results"])
{"New return": page_new_return, "Tax expert queue": page_expert_queue, "Results": page_results}[
    page
]()
