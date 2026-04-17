"""
Reliable orchestration helpers for the Personal Finance Advisor MAS.

This keeps the original 4-agent CrewAI pipeline available while adding a
deterministic low-resource mode that executes each agent's custom tool
directly. The MAS structure, custom tools, shared state, and observability
remain intact, but the application no longer depends on weak-model
tool-calling for the demo to succeed.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable

import crewai_bootstrap  # noqa: F401
from crewai import Crew, Process, Task

from agents import (
    create_budget_advisor_agent,
    create_data_ingestion_agent,
    create_expense_analyzer_agent,
    create_report_generator_agent,
)
from config import PIPELINE_MODE
from observability.logger import AgentLogger
from state.global_state import GlobalState
from tools.budget_calculator_tool import budget_calculator_tool
from tools.csv_reader_tool import csv_reader_tool
from tools.expense_categorizer_tool import expense_categorizer_tool
from tools.report_writer_tool import report_writer_tool


class PipelineExecutionError(RuntimeError):
    """Raised when the finance pipeline cannot complete successfully."""


def build_crew(csv_path: str, monthly_income: float) -> Crew:
    """Construct the original CrewAI pipeline for higher-resource machines."""

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
            "Combine all data from the previous agents - the spending summary "
            "and budget recommendations - into a single JSON string and pass it "
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

    return Crew(
        agents=[agent1, agent2, agent3, agent4],
        tasks=[task1, task2, task3, task4],
        process=Process.sequential,
        verbose=True,
    )


def _parse_tool_json(raw_output: str, tool_name: str) -> Dict[str, Any]:
    """Parse JSON returned by a custom tool and fail loudly if it is malformed."""
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise PipelineExecutionError(
            f"{tool_name} returned invalid JSON: {exc}"
        ) from exc


def _record_errors(agent_name: str, errors: Iterable[str]) -> None:
    """Persist stage errors in shared state for inspection in the UI."""
    state = GlobalState()
    for error in errors:
        state.append("errors", f"{agent_name}: {error}", agent_name=agent_name)


def _log_agent_step(agent_name: str, task_description: str, runner: Any) -> Any:
    """Run one deterministic agent step with start/end logging."""
    logger = AgentLogger(agent_name)
    start = logger.log_agent_start(task_description)
    result = runner()
    logger.log_agent_end(start, str(result)[:500])
    return result


def _pipeline_has_results() -> bool:
    """Return True when the global state contains a complete analysis."""
    state = GlobalState().snapshot()
    return bool(
        state.get("raw_transactions")
        and state.get("categorized_transactions")
        and state.get("spending_summary")
        and state.get("budget_recommendations")
        and state.get("report_path")
    )


def run_crewai_pipeline(csv_path: str, monthly_income: float) -> str:
    """Execute the original CrewAI orchestration."""
    crew = build_crew(csv_path, monthly_income)
    return str(crew.kickoff())


def run_reliable_pipeline(csv_path: str, monthly_income: float) -> str:
    """Execute the full 4-agent workflow deterministically via custom tools."""
    state = GlobalState()
    state.set("pipeline_mode", "reliable", agent_name="orchestrator")

    ingestion_raw = _log_agent_step(
        "Data Ingestion Specialist",
        f"Read and validate transactions from '{csv_path}'",
        lambda: csv_reader_tool.run(file_path=csv_path),
    )
    ingestion = _parse_tool_json(ingestion_raw, "csv_reader_tool")
    _record_errors("Data Ingestion Specialist", ingestion.get("errors", []))
    transactions = ingestion.get("transactions", [])
    if not transactions:
        detail = "; ".join(ingestion.get("errors", [])) or "No valid transactions were found."
        raise PipelineExecutionError(f"Data ingestion failed. {detail}")

    categorizer_raw = _log_agent_step(
        "Expense Analyzer",
        "Categorize transactions and build a spending summary",
        lambda: expense_categorizer_tool.run(transactions_json=json.dumps(transactions)),
    )
    categorized = _parse_tool_json(categorizer_raw, "expense_categorizer_tool")
    _record_errors("Expense Analyzer", categorized.get("errors", []))
    spending_summary = categorized.get("spending_summary", {})
    if not spending_summary:
        detail = "; ".join(categorized.get("errors", [])) or "No spending summary was produced."
        raise PipelineExecutionError(f"Expense analysis failed. {detail}")

    budget_raw = _log_agent_step(
        "Budget Advisor",
        "Apply the 50/30/20 rule and generate recommendations",
        lambda: budget_calculator_tool.run(
            spending_summary_json=json.dumps(spending_summary),
            monthly_income=monthly_income,
        ),
    )
    budget_result = _parse_tool_json(budget_raw, "budget_calculator_tool")
    _record_errors("Budget Advisor", budget_result.get("errors", []))
    if not budget_result.get("budget"):
        detail = "; ".join(budget_result.get("errors", [])) or "No budget analysis was produced."
        raise PipelineExecutionError(f"Budget advice failed. {detail}")

    analysis_payload = {
        "budget": budget_result["budget"],
        "spending_summary": spending_summary,
        "recommendations": budget_result.get("recommendations", []),
    }
    report_result = _log_agent_step(
        "Financial Report Writer",
        "Write the Markdown finance report to disk",
        lambda: report_writer_tool.run(analysis_json=json.dumps(analysis_payload)),
    )

    report_path = state.get("report_path")
    if not report_path:
        raise PipelineExecutionError(f"Report generation failed. {report_result}")

    return report_result


def run_pipeline(csv_path: str, monthly_income: float, mode: str | None = None) -> str:
    """Run the requested orchestration mode.

    Modes:
      - reliable: deterministic tool execution, best for low-RAM laptops
      - crewai: original CrewAI orchestration
      - auto: try CrewAI first, then fall back if it produces no usable state
    """
    requested_mode = (mode or PIPELINE_MODE).strip().lower()
    orchestrator_logger = AgentLogger("orchestrator")
    GlobalState().set("pipeline_mode", requested_mode, agent_name="orchestrator")

    if requested_mode == "reliable":
        return run_reliable_pipeline(csv_path, monthly_income)

    if requested_mode == "crewai":
        return run_crewai_pipeline(csv_path, monthly_income)

    if requested_mode == "auto":
        try:
            result = run_crewai_pipeline(csv_path, monthly_income)
            if _pipeline_has_results():
                return result
            orchestrator_logger.log_tool_call(
                "pipeline_fallback",
                {"requested_mode": requested_mode},
                "CrewAI completed without producing stateful results; switching to reliable mode.",
                success=False,
                error="empty_state_after_crewai",
            )
        except Exception as exc:
            orchestrator_logger.log_tool_call(
                "pipeline_fallback",
                {"requested_mode": requested_mode},
                "CrewAI execution failed; switching to reliable mode.",
                success=False,
                error=str(exc),
            )
        return run_reliable_pipeline(csv_path, monthly_income)

    raise ValueError(f"Unsupported PIPELINE_MODE '{requested_mode}'. Use reliable, crewai, or auto.")
