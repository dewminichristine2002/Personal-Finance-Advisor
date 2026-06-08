"""
Test suite for Agent 4 – Report Generator Agent / Report Writer Tool
(Student 4 contribution)

Validates:
  - Markdown report is generated with correct structure
  - Report file is written to the output directory
  - Budget tables and recommendations appear in the output
  - Invalid JSON input is handled gracefully
  - State records the report path
"""

from __future__ import annotations

import json
import os
from typing import Generator

import pytest

from config import OUTPUT_DIR
from state.global_state import GlobalState
from tools.report_writer_tool import (
    report_writer_tool,
    _build_markdown,
    _build_pdf_bytes_from_analysis,
)


@pytest.fixture(autouse=True)
def _reset_state() -> Generator[None, None, None]:
    GlobalState.reset()
    yield
    GlobalState.reset()


SAMPLE_DATA = {
    "budget": {
        "monthly_income": 5000,
        "total_spent": 3000,
        "targets": {"needs": 2500, "wants": 1500, "savings": 1000},
        "actuals": {"needs": 2000, "wants": 800, "other": 200},
        "differences": {"needs": 500, "wants": 700, "savings": 2000},
    },
    "spending_summary": {
        "food": {"total": 500, "count": 10},
        "transport": {"total": 200, "count": 5},
        "entertainment": {"total": 100, "count": 3},
    },
    "recommendations": [
        "Essential spending is Rs. 500.00 under the 50% target. Well done!",
        "Discretionary spending is Rs. 700.00 under the 30% target.",
    ],
}


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestBuildMarkdown:
    def test_contains_title(self) -> None:
        md = _build_markdown(SAMPLE_DATA)
        assert "# Personal Finance Report" in md

    def test_contains_budget_table(self) -> None:
        md = _build_markdown(SAMPLE_DATA)
        assert "Monthly Income" in md
        assert "Rs. 5,000.00" in md

    def test_contains_category_table(self) -> None:
        md = _build_markdown(SAMPLE_DATA)
        assert "Food" in md
        assert "Transport" in md

    def test_contains_recommendations(self) -> None:
        md = _build_markdown(SAMPLE_DATA)
        assert "Recommendations" in md
        assert "Well done" in md

    def test_empty_data_no_crash(self) -> None:
        md = _build_markdown({})
        assert "Personal Finance Report" in md

    def test_pdf_bytes_start_with_pdf_header(self) -> None:
        pdf_bytes = _build_pdf_bytes_from_analysis(SAMPLE_DATA)
        assert pdf_bytes.startswith(b"%PDF-1.4")
        assert pdf_bytes.endswith(b"%%EOF")
        assert len(pdf_bytes) > 1000


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestReportWriterTool:
    def test_writes_file(self) -> None:
        output = report_writer_tool.run(analysis_json=json.dumps(SAMPLE_DATA))
        assert "successfully" in output.lower()
        state = GlobalState()
        path = state.get("report_path")
        assert os.path.isfile(path)
        with open(path, "r") as f:
            content = f.read()
        assert "Personal Finance Report" in content

    def test_invalid_json_returns_error(self) -> None:
        output = report_writer_tool.run(analysis_json="not-json")
        assert "invalid" in output.lower() or "error" in output.lower()

    def test_state_records_path(self) -> None:
        report_writer_tool.run(analysis_json=json.dumps(SAMPLE_DATA))
        state = GlobalState()
        assert state.get("report_path").endswith(".md")
