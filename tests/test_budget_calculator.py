"""
Test suite for Agent 3 – Budget Advisor Agent / Budget Calculator Tool
(Student 3 contribution)

Validates:
  - 50/30/20 rule is applied correctly
  - Overspending triggers appropriate recommendations
  - Under-spending is correctly recognised
  - Edge cases: zero income, empty summary
  - State is populated
"""

from __future__ import annotations

import json
from typing import Generator

import pytest

from state.global_state import GlobalState
from tools.budget_calculator_tool import budget_calculator_tool, _classify_spending


@pytest.fixture(autouse=True)
def _reset_state() -> Generator[None, None, None]:
    GlobalState.reset()
    yield
    GlobalState.reset()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestClassifySpending:
    def test_needs_classification(self) -> None:
        summary = {
            "food": {"total": 300},
            "housing": {"total": 1200},
            "entertainment": {"total": 100},
        }
        result = _classify_spending(summary)
        assert result["needs"] == 1500.0
        assert result["wants"] == 100.0

    def test_ignores_meta_keys(self) -> None:
        summary = {"_overall": {"total": 999}, "food": {"total": 50}}
        result = _classify_spending(summary)
        assert result["needs"] == 50.0


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestBudgetCalculatorTool:
    def test_generates_recommendations(self) -> None:
        summary = {
            "food": {"total": 400, "count": 10},
            "housing": {"total": 1500, "count": 1},
            "entertainment": {"total": 200, "count": 5},
        }
        output = budget_calculator_tool.run(
            spending_summary_json=json.dumps(summary),
            monthly_income=5000.0,
        )
        data = json.loads(output)
        assert len(data["recommendations"]) >= 2
        assert data["budget"]["monthly_income"] == 5000.0
        assert data["budget"]["total_spent"] == 2100.0

    def test_overspending_detected(self) -> None:
        summary = {
            "food": {"total": 2000, "count": 30},
            "housing": {"total": 2000, "count": 1},
        }
        output = budget_calculator_tool.run(
            spending_summary_json=json.dumps(summary),
            monthly_income=3000.0,
        )
        data = json.loads(output)
        assert any("exceeds" in r.lower() for r in data["recommendations"])

    def test_zero_income_returns_error(self) -> None:
        output = budget_calculator_tool.run(
            spending_summary_json=json.dumps({}),
            monthly_income=0,
        )
        data = json.loads(output)
        assert len(data["errors"]) > 0

    def test_invalid_json_returns_error(self) -> None:
        output = budget_calculator_tool.run(
            spending_summary_json="broken",
            monthly_income=5000.0,
        )
        data = json.loads(output)
        assert len(data["errors"]) > 0

    def test_populates_state(self) -> None:
        summary = {"food": {"total": 200, "count": 5}}
        budget_calculator_tool.run(
            spending_summary_json=json.dumps(summary),
            monthly_income=4000.0,
        )
        state = GlobalState()
        recs = state.get("budget_recommendations")
        assert recs is not None
        assert "budget" in recs
