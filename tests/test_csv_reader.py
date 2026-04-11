"""
Test suite for Agent 1 – Data Ingestion Agent / CSV Reader Tool
(Student 1 contribution)

Validates:
  - Correct parsing of well-formed CSV
  - Handling of missing columns
  - Handling of missing files
  - Handling of malformed amount values
  - State is populated after a successful read
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Generator

import pytest

from state.global_state import GlobalState
from tools.csv_reader_tool import csv_reader_tool, _validate_row


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_state() -> Generator[None, None, None]:
    """Ensure a fresh global state for every test."""
    GlobalState.reset()
    yield
    GlobalState.reset()


@pytest.fixture
def valid_csv(tmp_path: os.PathLike) -> str:
    """Create a minimal valid CSV and return its path."""
    content = (
        "date,description,amount,category\n"
        "2026-01-01,Grocery Store,50.00,food\n"
        "2026-01-02,Uber Ride,12.50,transport\n"
    )
    path = os.path.join(str(tmp_path), "valid.csv")
    with open(path, "w") as f:
        f.write(content)
    return path


@pytest.fixture
def missing_column_csv(tmp_path: os.PathLike) -> str:
    """CSV missing the 'amount' column."""
    content = "date,description,category\n2026-01-01,Test,food\n"
    path = os.path.join(str(tmp_path), "bad_cols.csv")
    with open(path, "w") as f:
        f.write(content)
    return path


@pytest.fixture
def bad_amount_csv(tmp_path: os.PathLike) -> str:
    """CSV with a non-numeric amount."""
    content = (
        "date,description,amount,category\n"
        "2026-01-01,Grocery Store,fifty,food\n"
        "2026-01-02,Uber Ride,12.50,transport\n"
    )
    path = os.path.join(str(tmp_path), "bad_amt.csv")
    with open(path, "w") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Unit tests for _validate_row
# ---------------------------------------------------------------------------

class TestValidateRow:
    def test_valid_row(self) -> None:
        row = {"date": "2026-01-01", "description": "Test", "amount": "99.99", "category": "food"}
        result = _validate_row(row, 2)
        assert result["amount"] == 99.99
        assert result["category"] == "food"

    def test_invalid_amount_raises(self) -> None:
        row = {"date": "2026-01-01", "description": "Test", "amount": "abc", "category": "food"}
        with pytest.raises(ValueError, match="invalid amount"):
            _validate_row(row, 2)

    def test_missing_category_defaults(self) -> None:
        row = {"date": "2026-01-01", "description": "Test", "amount": "10"}
        result = _validate_row(row, 2)
        assert result["category"] == "uncategorized"


# ---------------------------------------------------------------------------
# Integration tests for csv_reader_tool
# ---------------------------------------------------------------------------

class TestCsvReaderTool:
    def test_reads_valid_csv(self, valid_csv: str) -> None:
        output = csv_reader_tool.run(file_path=valid_csv)
        data = json.loads(output)
        assert len(data["transactions"]) == 2
        assert data["errors"] == []

    def test_populates_global_state(self, valid_csv: str) -> None:
        csv_reader_tool.run(file_path=valid_csv)
        state = GlobalState()
        assert len(state.get("raw_transactions")) == 2

    def test_missing_file_returns_error(self) -> None:
        output = csv_reader_tool.run(file_path="/nonexistent/path.csv")
        data = json.loads(output)
        assert len(data["errors"]) > 0
        assert "not found" in data["errors"][0].lower()

    def test_missing_columns_returns_error(self, missing_column_csv: str) -> None:
        output = csv_reader_tool.run(file_path=missing_column_csv)
        data = json.loads(output)
        assert any("missing" in e.lower() for e in data["errors"])

    def test_bad_amount_logged_as_error(self, bad_amount_csv: str) -> None:
        output = csv_reader_tool.run(file_path=bad_amount_csv)
        data = json.loads(output)
        assert len(data["transactions"]) == 1
        assert len(data["errors"]) == 1
