"""
Test suite for Agent 2 – Expense Analyzer Agent / Expense Categorizer Tool
(Student 2 contribution)

Validates:
  - Correct keyword-based categorisation
  - Already-categorised transactions are preserved
  - Spending summary totals are accurate
  - State is populated correctly
  - Malformed JSON input is handled gracefully
"""

from __future__ import annotations

import json
from typing import Generator

import pytest

from state.global_state import GlobalState
from tools.expense_categorizer_tool import (
    expense_categorizer_tool,
    _categorize,
    _build_summary,
)


@pytest.fixture(autouse=True)
def _reset_state() -> Generator[None, None, None]:
    GlobalState.reset()
    yield
    GlobalState.reset()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestCategorize:
    def test_keyword_match_food(self) -> None:
        assert _categorize("Grocery Store Weekly", "uncategorized") == "food"

    def test_keyword_match_transport(self) -> None:
        assert _categorize("Uber ride to office", "uncategorized") == "transport"

    def test_preserves_existing_category(self) -> None:
        assert _categorize("Random description", "health") == "health"

    def test_unknown_returns_other(self) -> None:
        assert _categorize("Mystery payment XYZ", "uncategorized") == "other"


class TestBuildSummary:
    def test_summary_totals(self) -> None:
        txns = [
            {"description": "A", "amount": 100, "category": "food"},
            {"description": "B", "amount": 50, "category": "food"},
            {"description": "C", "amount": 30, "category": "transport"},
        ]
        summary = _build_summary(txns)
        assert summary["food"]["total"] == 150.0
        assert summary["food"]["count"] == 2
        assert summary["transport"]["total"] == 30.0
        assert summary["_overall"]["total"] == 180.0

    def test_negative_amounts_treated_as_absolute(self) -> None:
        txns = [{"description": "Refund", "amount": -25, "category": "shopping"}]
        summary = _build_summary(txns)
        assert summary["shopping"]["total"] == 25.0


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestExpenseCategorizerTool:
    def test_categorizes_transactions(self) -> None:
        txns = [
            {"date": "2026-01-01", "description": "Netflix sub", "amount": 15.99, "category": "uncategorized"},
            {"date": "2026-01-02", "description": "Bus ticket", "amount": 5.0, "category": "uncategorized"},
        ]
        output = expense_categorizer_tool.run(transactions_json=json.dumps(txns))
        data = json.loads(output)
        cats = [t["category"] for t in data["categorized_transactions"]]
        assert "entertainment" in cats
        assert "transport" in cats

    def test_populates_state(self) -> None:
        txns = [{"date": "2026-01-01", "description": "Rent", "amount": 1200, "category": "uncategorized"}]
        expense_categorizer_tool.run(transactions_json=json.dumps(txns))
        state = GlobalState()
        assert len(state.get("categorized_transactions")) == 1
        assert "housing" in state.get("spending_summary")

    def test_invalid_json_returns_error(self) -> None:
        output = expense_categorizer_tool.run(transactions_json="not-json")
        data = json.loads(output)
        assert len(data["errors"]) > 0
