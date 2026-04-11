"""
Streamlit Web UI for the Personal Finance Advisor Multi-Agent System.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from crewai import Crew, Process, Task

from agents import (
    create_data_ingestion_agent,
    create_expense_analyzer_agent,
    create_budget_advisor_agent,
    create_report_generator_agent,
)
from config import OUTPUT_DIR
from observability.logger import AgentLogger
from state.global_state import GlobalState


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Finance Advisor MAS",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
    }
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.3rem 0;
    }
    .status-running { color: #f59e0b; font-weight: bold; }
    .status-done { color: #10b981; font-weight: bold; }
    .status-waiting { color: #6b7280; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## Settings")
    monthly_income = st.number_input(
        "Monthly Income ($)",
        min_value=100.0,
        max_value=1_000_000.0,
        value=5000.0,
        step=500.0,
    )

    st.markdown("---")
    st.markdown("## Upload Transactions")
    uploaded_file = st.file_uploader(
        "Upload a CSV file",
        type=["csv"],
        help="CSV with columns: date, description, amount, category",
    )

    use_sample = st.checkbox("Use sample data instead", value=True)

    st.markdown("---")
    st.markdown("## About")
    st.markdown(
        "This system uses **4 AI agents** orchestrated by "
        "**CrewAI** running on a local **Ollama** LLM to analyse "
        "your finances and generate budget advice."
    )


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.title("Personal Finance Advisor")
st.caption("Multi-Agent System  |  CrewAI + Ollama  |  100% Local & Private")
st.markdown('</div>', unsafe_allow_html=True)

# Agent pipeline visualisation
cols = st.columns(4)
agent_info = [
    ("1. Data Ingestion", "Reads & validates CSV"),
    ("2. Expense Analyzer", "Categorises spending"),
    ("3. Budget Advisor", "50/30/20 rule analysis"),
    ("4. Report Generator", "Creates Markdown report"),
]
for col, (name, desc) in zip(cols, agent_info):
    with col:
        st.markdown(f"""
        <div class="agent-card">
            <strong>{name}</strong><br>
            <small>{desc}</small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Data preview
# ---------------------------------------------------------------------------

csv_path = None

if uploaded_file is not None and not use_sample:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb")
    tmp.write(uploaded_file.getvalue())
    tmp.close()
    csv_path = tmp.name
    df_preview = pd.read_csv(csv_path)
    st.subheader("Uploaded Transactions")
    st.dataframe(df_preview, use_container_width=True)
elif use_sample:
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_transactions.csv")
    if os.path.isfile(sample_path):
        csv_path = sample_path
        df_preview = pd.read_csv(sample_path)
        st.subheader("Sample Transactions (31 records)")
        st.dataframe(df_preview, use_container_width=True)
    else:
        st.error("Sample data file not found. Please upload a CSV file.")
else:
    st.info("Upload a CSV file or check 'Use sample data' to get started.")


# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

if csv_path and st.button("Run Finance Analysis", type="primary", use_container_width=True):

    GlobalState.reset()
    AgentLogger.clear_trace()

    state = GlobalState()
    state.set("monthly_income", monthly_income, agent_name="orchestrator")
    logger = AgentLogger("orchestrator")

    progress = st.progress(0, text="Initialising agents...")
    status_area = st.container()

    agent_names = [
        "Data Ingestion Specialist",
        "Expense Analyzer",
        "Budget Advisor",
        "Financial Report Writer",
    ]

    with status_area:
        status_placeholder = st.empty()

    def show_status(step: int, label: str) -> None:
        lines = []
        for i, name in enumerate(agent_names):
            if i < step:
                lines.append(f"- :green[**{name}**] -- Done")
            elif i == step:
                lines.append(f"- :orange[**{name}**] -- {label}")
            else:
                lines.append(f"- :gray[{name}] -- Waiting")
        status_placeholder.markdown("\n".join(lines))

    # --- Build and run crew ---
    show_status(0, "Reading CSV data...")
    progress.progress(10, text="Agent 1: Reading CSV data...")

    start_time = logger.log_agent_start("Full pipeline execution")

    agent1 = create_data_ingestion_agent()
    agent2 = create_expense_analyzer_agent()
    agent3 = create_budget_advisor_agent()
    agent4 = create_report_generator_agent()

    task1 = Task(
        description=(
            f"Read the financial transactions CSV file located at '{csv_path}'. "
            "Validate the data and return all transactions as a clean JSON list. "
            "Report any rows that failed validation."
        ),
        expected_output=(
            "A JSON object with two keys: 'transactions' (list of validated "
            "transaction dicts with date, description, amount, category) and "
            "'errors' (list of error strings, possibly empty)."
        ),
        agent=agent1,
    )

    task2 = Task(
        description=(
            "Using the transaction data provided by the previous agent, "
            "categorize every transaction into a meaningful spending category "
            "and produce a per-category spending summary with totals and counts. "
            "Pass the raw transaction list from the previous task's output "
            "as the 'transactions_json' argument to your tool."
        ),
        expected_output=(
            "A JSON object with 'categorized_transactions' (list) and "
            "'spending_summary' (dict keyed by category with total and count)."
        ),
        agent=agent2,
        context=[task1],
    )

    task3 = Task(
        description=(
            f"The user's monthly income is ${monthly_income:,.2f}. "
            "Using the spending summary from the previous agent, apply the "
            "50/30/20 budgeting rule and generate budget recommendations. "
            "Pass the spending_summary JSON and the monthly_income number "
            "to your budget_calculator_tool."
        ),
        expected_output=(
            "A JSON object with 'budget' (targets, actuals, differences), "
            "'recommendations' (list of actionable advice strings)."
        ),
        agent=agent3,
        context=[task2],
    )

    task4 = Task(
        description=(
            "Combine all data from the previous agents – the spending summary "
            "and budget recommendations – into a single JSON string and pass it "
            "to the report_writer_tool to generate a Markdown financial report. "
            "The JSON should contain keys: 'budget', 'spending_summary', and "
            "'recommendations'."
        ),
        expected_output=(
            "A confirmation message stating the report was written successfully, "
            "including the file path and a brief preview of the report content."
        ),
        agent=agent4,
        context=[task2, task3],
    )

    crew = Crew(
        agents=[agent1, agent2, agent3, agent4],
        tasks=[task1, task2, task3, task4],
        process=Process.sequential,
        verbose=True,
    )

    show_status(0, "Running...")
    progress.progress(20, text="Agents are running... this can take a few minutes on local models")

    result_box: dict[str, str] = {"result": "", "error": ""}

    def _run_crew() -> None:
        try:
            result_box["result"] = str(crew.kickoff())
        except Exception as exc:
            result_box["error"] = str(exc)

    worker = threading.Thread(target=_run_crew, daemon=False)
    worker.start()

    while worker.is_alive():
        trace = AgentLogger.read_trace()

        seen_csv = any(
            r.get("event") == "TOOL_CALL" and r.get("tool") == "csv_reader_tool"
            for r in trace
        )
        seen_categorizer = any(
            r.get("event") == "TOOL_CALL" and r.get("tool") == "expense_categorizer_tool"
            for r in trace
        )
        seen_budget = any(
            r.get("event") == "TOOL_CALL" and r.get("tool") == "budget_calculator_tool"
            for r in trace
        )
        seen_report = any(
            r.get("event") == "TOOL_CALL" and r.get("tool") == "report_writer_tool"
            for r in trace
        )

        if seen_report:
            show_status(3, "Generating report...")
            progress.progress(90, text="Agent 4: Writing report...")
        elif seen_budget:
            show_status(2, "Calculating 50/30/20 budget...")
            progress.progress(72, text="Agent 3: Budget analysis...")
        elif seen_categorizer:
            show_status(1, "Categorizing transactions...")
            progress.progress(50, text="Agent 2: Expense categorization...")
        elif seen_csv:
            show_status(1, "Preparing spending summary...")
            progress.progress(35, text="Agent 1 complete, moving to Agent 2...")
        else:
            show_status(0, "Reading CSV data...")
            progress.progress(20, text="Agent 1: Processing CSV...")

        # Keep UI responsive while waiting for local model inference.
        time.sleep(0.6)

    worker.join(timeout=0.1)

    if result_box["error"]:
        progress.progress(100, text="Run failed")
        st.error(f"Analysis failed: {result_box['error']}")
        st.info("Tip: Keep this tab open while the analysis is running.")
        st.stop()

    result = result_box["result"]

    logger.log_agent_end(start_time, str(result)[:500])

    progress.progress(100, text="All agents complete!")
    show_status(4, "")

    # --- Display results ---
    st.markdown("---")
    st.subheader("Results")

    snapshot = state.snapshot()

    # Budget overview metrics
    budget_recs = snapshot.get("budget_recommendations", {})
    budget_data = budget_recs.get("budget", {})

    if budget_data:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Monthly Income", f"${budget_data.get('monthly_income', 0):,.2f}")
        m2.metric("Total Spent", f"${budget_data.get('total_spent', 0):,.2f}")
        remaining = budget_data.get("monthly_income", 0) - budget_data.get("total_spent", 0)
        m3.metric("Remaining", f"${remaining:,.2f}")
        savings_pct = (remaining / budget_data.get("monthly_income", 1)) * 100
        m4.metric("Savings Rate", f"{savings_pct:.1f}%")

    # Spending breakdown
    spending = snapshot.get("spending_summary", {})
    if spending:
        st.subheader("Spending by Category")
        chart_data = {
            cat: info["total"]
            for cat, info in spending.items()
            if not cat.startswith("_")
        }
        if chart_data:
            col_chart, col_table = st.columns([1, 1])
            with col_chart:
                df_chart = pd.DataFrame(
                    {"Category": list(chart_data.keys()), "Amount ($)": list(chart_data.values())}
                )
                st.bar_chart(df_chart.set_index("Category"))
            with col_table:
                table_rows = []
                for cat, info in sorted(spending.items()):
                    if cat.startswith("_"):
                        continue
                    table_rows.append({
                        "Category": cat.title(),
                        "Amount": f"${info.get('total', 0):,.2f}",
                        "Transactions": info.get("count", 0),
                    })
                st.table(pd.DataFrame(table_rows))

    # Recommendations
    recs = budget_recs.get("recommendations", [])
    if recs:
        st.subheader("Recommendations")
        for rec in recs:
            st.info(rec)

    # Generated report
    report_path = snapshot.get("report_path", "")
    if report_path and os.path.isfile(report_path):
        st.subheader("Generated Report")
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
        with st.expander("View Full Markdown Report", expanded=False):
            st.markdown(report_content)
        st.download_button(
            "Download Report",
            data=report_content,
            file_name=os.path.basename(report_path),
            mime="text/markdown",
        )

    # Execution trace
    trace = AgentLogger.read_trace()
    if trace:
        st.subheader("Execution Trace (AgentOps)")
        with st.expander(f"View Trace Log ({len(trace)} events)", expanded=False):
            for record in trace:
                event = record.get("event", "")
                agent = record.get("agent", "")
                ts = record.get("timestamp", "")
                if event == "AGENT_START":
                    st.markdown(f"**{ts}** | `{agent}` started: _{record.get('task', '')[:100]}_")
                elif event == "AGENT_END":
                    st.markdown(f"**{ts}** | `{agent}` finished in {record.get('elapsed_seconds', '?')}s")
                elif event == "TOOL_CALL":
                    status = "OK" if record.get("success") else "FAIL"
                    st.markdown(f"**{ts}** | `{agent}` called `{record.get('tool', '')}` [{status}]")
                elif event == "STATE_UPDATE":
                    st.markdown(f"**{ts}** | `{agent}` updated state key `{record.get('key', '')}`")

    # State snapshot
    with st.expander("View Global State Snapshot"):
        st.json(snapshot)
