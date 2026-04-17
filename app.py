"""
Streamlit Web UI for the Personal Finance Advisor Multi-Agent System.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import tempfile
import threading
import time

import pandas as pd
import streamlit as st

from config import OUTPUT_DIR, PIPELINE_MODE
from observability.logger import AgentLogger
from pipeline import run_pipeline
from state.global_state import GlobalState


st.set_page_config(
    page_title="Finance Advisor MAS",
    page_icon=":moneybag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    :root {
        --bg: #f5f3ff;
        --bg-accent: #ede9fe;
        --surface: rgba(255, 255, 255, 0.96);
        --surface-strong: #ffffff;
        --ink: #1f1733;
        --muted: #7c6ca8;
        --line: rgba(124, 58, 237, 0.12);
        --brand: #7c3aed;
        --brand-deep: #5b21b6;
        --brand-soft: #ede9fe;
        --gold: #d97706;
        --success: #059669;
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(124, 58, 237, 0.08), transparent 32%),
            radial-gradient(circle at top right, rgba(217, 119, 6, 0.03), transparent 26%),
            linear-gradient(180deg, #faf8ff 0%, var(--bg) 100%);
        color: var(--ink);
        font-family: "Trebuchet MS", "Segoe UI", sans-serif;
    }
    .stApp h1, .stApp h2, .stApp h3 {
        font-family: "Cambria", "Georgia", serif;
        letter-spacing: -0.02em;
        color: #1f1733;
    }
    div[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(45, 27, 78, 0.96) 0%, rgba(59, 33, 97, 0.96) 100%);
        border-right: 1px solid rgba(217, 119, 6, 0.08);
    }
    div[data-testid="stSidebar"] * {
        color: #f0e6ff !important;
    }
    div[data-testid="stSidebar"] .stCaption,
    div[data-testid="stSidebar"] label,
    div[data-testid="stSidebar"] small {
        color: rgba(240, 230, 255, 0.8) !important;
    }
    div[data-testid="stSidebar"] [data-baseweb="input"],
    div[data-testid="stSidebar"] section[data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(217, 119, 6, 0.15);
        border-radius: 16px;
    }
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }
    .main-header {
        padding: 0.2rem 0 0.8rem 0;
    }
    .eyebrow {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        background: rgba(124, 58, 237, 0.1);
        border: 1px solid rgba(217, 119, 6, 0.25);
        color: var(--brand-deep);
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .hero-shell {
        background:
            linear-gradient(135deg, rgba(245, 243, 255, 0.96) 0%, rgba(237, 233, 254, 0.96) 100%);
        border: 1px solid rgba(124, 58, 237, 0.15);
        box-shadow: 0 24px 60px rgba(124, 58, 237, 0.12);
        border-radius: 28px;
        padding: 1.5rem 1.6rem;
        min-height: 100%;
    }
    .hero-title {
        font-family: "Cambria", "Georgia", serif;
        color: #1f1733;
        font-size: clamp(2.4rem, 4vw, 4rem);
        line-height: 0.95;
        margin: 0.8rem 0 0.7rem 0;
    }
    .hero-copy {
        color: #4c3d66;
        font-size: 1.02rem;
        line-height: 1.7;
        max-width: 52rem;
        margin: 0;
    }
    .hero-stat {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 1rem;
        margin-right: 0.8rem;
        padding: 0.55rem 0.8rem;
        border-radius: 999px;
        background: rgba(217, 119, 6, 0.08);
        border: 1px solid rgba(217, 119, 6, 0.2);
        color: var(--gold);
        font-weight: 700;
        font-size: 0.88rem;
    }
    .section-kicker {
        color: var(--gold);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.78rem;
        font-weight: 800;
        margin-bottom: 0.3rem;
    }
    .section-title {
        margin: 0 0 0.6rem 0;
        font-size: 2rem;
        color: #1f1733;
    }
    .section-copy {
        margin: 0;
        color: #4c3d66;
        line-height: 1.6;
    }
    .agent-card {
        background: linear-gradient(160deg, rgba(245, 243, 255, 0.96) 0%, rgba(237, 233, 254, 0.96) 100%);
        padding: 1.1rem;
        border-radius: 22px;
        color: var(--ink);
        margin: 0.5rem 0;
        border: 1px solid rgba(124, 58, 237, 0.12);
        box-shadow: 0 14px 30px rgba(124, 58, 237, 0.08);
        min-height: 172px;
    }
    .agent-index {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.1rem;
        height: 2.1rem;
        border-radius: 999px;
        background: rgba(217, 119, 6, 0.12);
        color: var(--gold);
        font-weight: 800;
        font-size: 0.92rem;
        margin-bottom: 0.8rem;
    }
    .agent-title {
        font-family: "Cambria", "Georgia", serif;
        color: #1f1733;
        font-size: 1.2rem;
        margin-bottom: 0.35rem;
    }
    .agent-copy {
        color: #4c3d66;
        line-height: 1.55;
        font-size: 0.94rem;
        margin-bottom: 0.9rem;
    }
    .agent-tag {
        display: inline-block;
        padding: 0.35rem 0.62rem;
        border-radius: 999px;
        background: rgba(124, 58, 237, 0.08);
        color: var(--brand-deep);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }
    .surface-note {
        background: rgba(245, 243, 255, 0.92);
        border: 1px solid rgba(124, 58, 237, 0.12);
        border-radius: 22px;
        padding: 1rem 1.1rem;
        color: #4c3d66;
        box-shadow: 0 14px 28px rgba(124, 58, 237, 0.06);
    }
    .preview-banner {
        margin: 0.3rem 0 1rem 0;
        padding: 0.95rem 1rem;
        background: linear-gradient(135deg, rgba(245, 243, 255, 0.92) 0%, rgba(237, 233, 254, 0.92) 100%);
        border: 1px solid rgba(217, 119, 6, 0.15);
        border-radius: 18px;
        color: #4c3d66;
        font-size: 0.95rem;
    }
    .preview-banner strong {
        color: #1f1733;
    }
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%) !important;
        color: #ffffff !important;
        border: none !important;
        min-height: 3.35rem;
        font-weight: 800 !important;
        font-size: 1rem !important;
        letter-spacing: 0.02em;
        border-radius: 18px;
        box-shadow: 0 18px 30px rgba(124, 58, 237, 0.3) !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #6d28d9 0%, #4c1d95 100%) !important;
        color: #ffffff !important;
    }
    .stButton > button:focus {
        color: #ffffff !important;
        box-shadow: 0 0 0 0.2rem rgba(124, 58, 237, 0.25) !important;
    }
    .stButton > button p {
        color: #ffffff !important;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(245, 243, 255, 0.94) 0%, rgba(237, 233, 254, 0.98) 100%);
        border: 1px solid rgba(217, 119, 6, 0.12);
        padding: 1rem 1rem 0.9rem 1rem;
        border-radius: 18px;
        box-shadow: 0 14px 28px rgba(124, 58, 237, 0.08);
    }
    div[data-testid="stMetricLabel"] {
        color: #7c6ca8;
        font-weight: 700;
    }
    div[data-testid="stMetricValue"] {
        color: #1f1733;
        font-family: "Cambria", "Georgia", serif;
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"],
    div[data-testid="stExpander"],
    div[data-testid="stAlert"] {
        border-radius: 20px;
        overflow: hidden;
    }
    div[data-testid="stExpander"] {
        border: 1px solid rgba(124, 58, 237, 0.12);
        background: rgba(245, 243, 255, 0.92);
    }
    .trace-wrap {
        display: grid;
        gap: 0.75rem;
        padding-top: 0.35rem;
    }
    .trace-row {
        display: grid;
        grid-template-columns: 15rem 10rem 1fr;
        gap: 0.9rem;
        align-items: start;
        padding: 0.85rem 1rem;
        border-radius: 16px;
        border: 1px solid rgba(124, 58, 237, 0.12);
        background: linear-gradient(180deg, rgba(245, 243, 255, 0.88) 0%, rgba(237, 233, 254, 0.94) 100%);
    }
    .trace-time {
        color: #7c6ca8;
        font-size: 0.84rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .trace-agent {
        color: #7c3aed;
        font-weight: 800;
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .trace-msg {
        color: #1f1733;
        line-height: 1.55;
        font-size: 0.94rem;
    }
    .trace-status-ok,
    .trace-status-fail {
        display: inline-block;
        margin-left: 0.45rem;
        padding: 0.12rem 0.45rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        vertical-align: middle;
    }
    .trace-status-ok {
        background: rgba(5, 150, 105, 0.10);
        color: #047857;
    }
    .trace-status-fail {
        background: rgba(220, 38, 38, 0.10);
        color: #b91c1c;
    }
    .state-shell {
        border: 1px solid rgba(124, 58, 237, 0.12);
        background: linear-gradient(180deg, rgba(245, 243, 255, 0.9) 0%, rgba(237, 233, 254, 0.96) 100%);
        border-radius: 18px;
        padding: 0.35rem;
    }
    .viz-shell {
        background: linear-gradient(180deg, rgba(245, 243, 255, 0.84) 0%, rgba(237, 233, 254, 0.92) 100%);
        border: 1px solid rgba(124, 58, 237, 0.10);
        border-radius: 22px;
        padding: 0.75rem;
        box-shadow: 0 14px 28px rgba(124, 58, 237, 0.06);
    }
    @media (max-width: 900px) {
        .trace-row {
            grid-template-columns: 1fr;
            gap: 0.35rem;
        }
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stMarkdownContainer"] p {
        color: #4c3d66;
    }
    div[data-testid="stAlert"] {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(217, 119, 6, 0.04) 100%) !important;
        border: 1px solid rgba(124, 58, 237, 0.15) !important;
        border-radius: 14px !important;
        padding: 1rem 1.2rem !important;
    }
    div[data-testid="stAlert"] > div {
        color: #1f1733 !important;
    }
    div[data-testid="stAlert"] svg {
        fill: #7c3aed !important;
    }
    /* Info box styling */
    div[data-testid="stAlert"] .stMarkdownContainer p {
        color: #1f1733 !important;
    }
    /* Chart/Plot styling */
    .plotly-graph-div {
        background: linear-gradient(135deg, rgba(245, 243, 255, 0.5) 0%, rgba(237, 233, 254, 0.3) 100%) !important;
    }
    .plotly-graph-div .plotly-container {
        background: rgba(245, 243, 255, 0.3) !important;
    }
    /* Bar chart color */
    .plotly .bar {
        fill: #7c3aed !important;
    }
    svg g.bars g rect {
        fill: #7c3aed !important;
    }
    /* Subheader styling */
    .stSubheader {
        color: #1f1733 !important;
    }
    /* Table styling */
    div[data-testid="stTable"] {
        background: linear-gradient(135deg, rgba(245, 243, 255, 0.6) 0%, rgba(237, 233, 254, 0.4) 100%) !important;
    }
    div[data-testid="stTable"] table {
        background: transparent !important;
    }
    div[data-testid="stTable"] th {
        background: rgba(124, 58, 237, 0.15) !important;
        color: #1f1733 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stTable"] td {
        color: #4c3d66 !important;
    }
    /* Download button styling */
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        box-shadow: 0 12px 24px rgba(124, 58, 237, 0.25) !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(135deg, #6d28d9 0%, #4c1d95 100%) !important;
        color: #ffffff !important;
    }
    div[data-testid="stDownloadButton"] > button p {
        color: #ffffff !important;
    }
    .status-running { color: #f59e0b; font-weight: bold; }
    .status-done { color: #10b981; font-weight: bold; }
    .status-waiting { color: #6b7280; }
</style>
""",
    unsafe_allow_html=True,
)

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
        "This system uses **4 AI agents** orchestrated locally with "
        "**CrewAI-compatible architecture**, custom Python tools, shared state, "
        "and structured observability."
    )
    st.caption(f"Pipeline mode: `{PIPELINE_MODE}`")

hero_col = st.container()
with hero_col:
    st.markdown(
        """
        <div class="main-header hero-shell">
            <span class="eyebrow">Local Multi-Agent Finance Studio</span>
            <h1 class="hero-title">Personal Finance Advisor</h1>
            <p class="hero-copy">
                Upload monthly transactions, route them through four specialized agents,
                and generate a polished budget report with traceable state updates and
                fully local execution.
            </p>
            <span class="hero-stat">4 Agent Workflow</span>
            <span class="hero-stat">Custom Python Tools</span>
            <span class="hero-stat">Private & Offline-Friendly</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div style="margin: 2rem 0 0.5rem 0;">
        <div class="section-kicker">Workflow Design</div>
        <h2 class="section-title">Four focused agents, one coherent output</h2>
        <p class="section-copy">
            Each stage performs a distinct responsibility so the system is easier to
            explain in demos, validate in tests, and observe during execution.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(4)
agent_info = [
    ("01", "Data Ingestion", "Reads uploaded files, checks schema quality, and passes valid transactions forward.", "CSV intake"),
    ("02", "Expense Analyzer", "Normalizes categories and builds the category-level spending summary used by later agents.", "Categorization"),
    ("03", "Budget Advisor", "Applies the 50/30/20 budgeting rule and produces actionable financial guidance.", "Budget logic"),
    ("04", "Report Generator", "Packages the final analysis into a Markdown report that can be reviewed or downloaded.", "Report output"),
]
for col, (index, name, desc, tag) in zip(cols, agent_info):
    with col:
        st.markdown(
            f"""
        <div class="agent-card">
            <div class="agent-index">{index}</div>
            <div class="agent-title">{name}</div>
            <div class="agent-copy">{desc}</div>
            <span class="agent-tag">{tag}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown(
    """
    <div style="margin: 1.8rem 0 0.6rem 0;">
        <div class="section-kicker">Data Intake</div>
        <h2 class="section-title">Preview the data before analysis</h2>
        <p class="section-copy">
            Use the built-in finance sample for a clean demo or upload a CSV that
            includes <code>date</code>, <code>description</code>, <code>amount</code>, and <code>category</code>.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

csv_path = None
preview_label = ""

if uploaded_file is not None and not use_sample:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb")
    tmp.write(uploaded_file.getvalue())
    tmp.close()
    csv_path = tmp.name
    df_preview = pd.read_csv(csv_path)
    preview_label = "Uploaded Transactions"
    st.markdown(
        f"""
        <div class="preview-banner">
            <strong>{preview_label}</strong><br>
            {len(df_preview)} rows • {len(df_preview.columns)} columns • Source: uploaded file
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(df_preview, use_container_width=True)
elif use_sample:
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_transactions.csv")
    if os.path.isfile(sample_path):
        csv_path = sample_path
        df_preview = pd.read_csv(sample_path)
        preview_label = "Sample Transactions"
        st.markdown(
            f"""
            <div class="preview-banner">
                <strong>{preview_label}</strong><br>
                {len(df_preview)} rows • {len(df_preview.columns)} columns • Source: built-in finance dataset
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(df_preview, use_container_width=True)
    else:
        st.error("Sample data file not found. Please upload a CSV file.")
else:
    st.markdown(
        """
        <div class="surface-note">
            Choose the sample dataset for a reliable demo, or upload your own finance CSV
            with the required transaction columns to begin.
        </div>
        """,
        unsafe_allow_html=True,
    )


if csv_path and st.button("Run Finance Analysis", type="primary", use_container_width=True):
    GlobalState.reset()
    AgentLogger.clear_trace()

    state = GlobalState()
    state.set("monthly_income", monthly_income, agent_name="orchestrator")
    logger = AgentLogger("orchestrator")

    progress = st.progress(0, text="Initialising agents...")
    status_placeholder = st.empty()

    agent_names = [
        "Data Ingestion Specialist",
        "Expense Analyzer",
        "Budget Advisor",
        "Financial Report Writer",
    ]

    def show_status(step: int, label: str) -> None:
        lines = []
        for i, name in enumerate(agent_names):
            if i < step:
                lines.append(f"- :orange[**{name}**] -- Done")
            elif i == step:
                lines.append(f"- :violet[**{name}**] -- {label}")
            else:
                lines.append(f"- :gray[{name}] -- Waiting")
        status_placeholder.markdown("\n".join(lines))

    show_status(0, "Reading CSV data...")
    progress.progress(10, text="Agent 1: Reading CSV data...")

    start_time = logger.log_agent_start("Full pipeline execution")
    show_status(0, "Running...")
    progress.progress(20, text=f"Running in {PIPELINE_MODE} mode...")

    result_box: dict[str, str] = {"result": "", "error": ""}

    def _run_pipeline() -> None:
        try:
            result_box["result"] = str(run_pipeline(csv_path, monthly_income, mode=PIPELINE_MODE))
        except Exception as exc:
            result_box["error"] = str(exc)

    worker = threading.Thread(target=_run_pipeline, daemon=False)
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

        time.sleep(0.2)

    worker.join(timeout=0.1)

    if result_box["error"]:
        progress.progress(100, text="Run failed")
        st.error(f"Analysis failed: {result_box['error']}")
        st.info("Tip: Keep this tab open while the analysis is running.")
        st.stop()

    result = result_box["result"]
    logger.log_agent_end(start_time, str(result)[:500])

    progress.progress(100, text="All agents complete!")
    show_status(4, "Completed successfully")

    st.markdown(
        """
        <div style="margin: 1.8rem 0 0.6rem 0;">
            <div class="section-kicker">Results</div>
            <h2 class="section-title">Analysis output</h2>
            <p class="section-copy">
                Review the calculated budget, category breakdown, recommendations,
                report artifact, and trace log produced by the agent workflow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    snapshot = state.snapshot()
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
                st.markdown('<div class="viz-shell">', unsafe_allow_html=True)
                st.vega_lite_chart(
                    df_chart,
                    {
                        "mark": {"type": "bar", "cornerRadiusTopLeft": 8, "cornerRadiusTopRight": 8},
                        "encoding": {
                            "x": {
                                "field": "Category",
                                "type": "nominal",
                                "sort": None,
                                "axis": {"labelAngle": -90, "labelColor": "#6b5a8d", "title": None},
                            },
                            "y": {
                                "field": "Amount ($)",
                                "type": "quantitative",
                                "axis": {
                                    "labelColor": "#6b5a8d",
                                    "gridColor": "rgba(124, 58, 237, 0.10)",
                                    "title": None,
                                },
                            },
                            "color": {
                                "value": "#7c3aed",
                            },
                            "tooltip": [
                                {"field": "Category", "type": "nominal"},
                                {"field": "Amount ($)", "type": "quantitative", "format": ",.2f"},
                            ],
                        },
                        "config": {
                            "view": {"stroke": None},
                            "background": "transparent",
                            "axis": {"domainColor": "rgba(124, 58, 237, 0.18)", "tickColor": "rgba(124, 58, 237, 0.18)"},
                        },
                    },
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
            with col_table:
                table_rows = []
                for cat, info in sorted(spending.items()):
                    if cat.startswith("_"):
                        continue
                    table_rows.append(
                        {
                            "Category": cat.title(),
                            "Amount": f"${info.get('total', 0):,.2f}",
                            "Transactions": info.get("count", 0),
                        }
                    )
                st.markdown('<div class="viz-shell">', unsafe_allow_html=True)
                st.table(pd.DataFrame(table_rows))
                st.markdown("</div>", unsafe_allow_html=True)

    recs = budget_recs.get("recommendations", [])
    if recs:
        st.subheader("Recommendations")
        for rec in recs:
            st.info(rec)

    report_path = snapshot.get("report_path", "")
    if report_path and os.path.isfile(report_path):
        st.subheader("Generated Report")
        with open(report_path, "r", encoding="utf-8") as handle:
            report_content = handle.read()
        with st.expander("View Full Markdown Report", expanded=False):
            st.markdown(report_content)
        st.download_button(
            "Download Report",
            data=report_content,
            file_name=os.path.basename(report_path),
            mime="text/markdown",
        )

    trace = AgentLogger.read_trace()
    if trace:
        st.subheader("Execution Trace (AgentOps)")
        with st.expander(f"View Trace Log ({len(trace)} events)", expanded=False):
            st.markdown('<div class="trace-wrap">', unsafe_allow_html=True)
            for record in trace:
                event = record.get("event", "")
                agent = record.get("agent", "")
                ts = record.get("timestamp", "")
                if event == "AGENT_START":
                    message = f"started: <em>{record.get('task', '')[:120]}</em>"
                    st.markdown(
                        f"""
                        <div class="trace-row">
                            <div class="trace-time">{ts}</div>
                            <div class="trace-agent">{agent}</div>
                            <div class="trace-msg">{message}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                elif event == "AGENT_END":
                    message = f"finished in {record.get('elapsed_seconds', '?')}s"
                    st.markdown(
                        f"""
                        <div class="trace-row">
                            <div class="trace-time">{ts}</div>
                            <div class="trace-agent">{agent}</div>
                            <div class="trace-msg">{message}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                elif event == "TOOL_CALL":
                    status_class = "trace-status-ok" if record.get("success") else "trace-status-fail"
                    status_text = "OK" if record.get("success") else "FAIL"
                    message = (
                        f"called <code>{record.get('tool', '')}</code>"
                        f'<span class="{status_class}">{status_text}</span>'
                    )
                    st.markdown(
                        f"""
                        <div class="trace-row">
                            <div class="trace-time">{ts}</div>
                            <div class="trace-agent">{agent}</div>
                            <div class="trace-msg">{message}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                elif event == "STATE_UPDATE":
                    message = f"updated state key <code>{record.get('key', '')}</code>"
                    st.markdown(
                        f"""
                        <div class="trace-row">
                            <div class="trace-time">{ts}</div>
                            <div class="trace-agent">{agent}</div>
                            <div class="trace-msg">{message}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("View Global State Snapshot"):
        st.markdown('<div class="state-shell">', unsafe_allow_html=True)
        st.json(snapshot)
        st.markdown("</div>", unsafe_allow_html=True)
