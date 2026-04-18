"""
Validation tests for the shared pipeline orchestration module.

These tests exercise the low-resource reliable mode so the full application
workflow can be verified without depending on weak-model tool-calling.
"""

from __future__ import annotations

import os
from typing import Generator

import pytest

from observability.logger import AgentLogger
from pipeline import run_pipeline
from state.global_state import GlobalState


@pytest.fixture(autouse=True)
def _reset_everything() -> Generator[None, None, None]:
    GlobalState.reset()
    AgentLogger.clear_trace()
    yield
    GlobalState.reset()
    AgentLogger.clear_trace()


def test_reliable_pipeline_populates_state() -> None:
    csv_path = os.path.join("data", "sample_transactions.csv")
    result = run_pipeline(csv_path, monthly_income=5000.0, mode="reliable")

    state = GlobalState().snapshot()

    assert "successfully written" in result.lower()
    assert len(state["raw_transactions"]) > 0
    assert len(state["categorized_transactions"]) > 0
    assert state["spending_summary"]
    assert state["budget_recommendations"]
    assert state["report_path"].endswith(".md")
    assert os.path.isfile(state["report_path"])


def test_reliable_pipeline_records_agent_and_tool_trace() -> None:
    csv_path = os.path.join("data", "sample_transactions.csv")
    run_pipeline(csv_path, monthly_income=5000.0, mode="reliable")

    trace = AgentLogger.read_trace()
    events = [record["event"] for record in trace]
    tools = {record.get("tool") for record in trace if record["event"] == "TOOL_CALL"}
    agents = {record.get("agent") for record in trace if record["event"] == "AGENT_START"}

    assert events.count("AGENT_START") >= 4
    assert events.count("AGENT_END") >= 4
    assert {
        "csv_reader_tool",
        "expense_categorizer_tool",
        "budget_calculator_tool",
        "report_writer_tool",
    } <= tools
    assert {
        "Data Ingestion Specialist",
        "Expense Analyzer",
        "Budget Advisor",
        "Financial Report Writer",
    } <= agents
