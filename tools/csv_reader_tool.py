"""
Tool 1 – CSV Reader Tool  (Student 1 contribution)

Reads a CSV file containing financial transactions, validates the schema,
and returns the parsed rows as a JSON string so the LLM can reason over them.
"""

from __future__ import annotations

import csv
import json
import os
from typing import List, Dict, Any

import crewai_bootstrap  # noqa: F401
from crewai.tools import tool

from observability.logger import AgentLogger
from state.global_state import GlobalState

_logger = AgentLogger("csv_reader_tool")

REQUIRED_COLUMNS = {"date", "description", "amount", "category"}


def _validate_row(row: Dict[str, str], idx: int) -> Dict[str, Any]:
    """Validate and coerce a single CSV row.

    Raises:
        ValueError: When the amount field cannot be parsed as a float.
    """
    try:
        amount = float(row["amount"])
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Row {idx}: invalid amount – {exc}") from exc

    return {
        "date": row.get("date", "").strip(),
        "description": row.get("description", "").strip(),
        "amount": amount,
        "category": row.get("category", "uncategorized").strip().lower(),
    }


@tool("csv_reader_tool")
def csv_reader_tool(file_path: str) -> str:
    """Read a CSV file of financial transactions and return them as JSON.

    The CSV must contain at least the columns: date, description, amount, category.
    Rows are validated and any parsing errors are reported.

    Args:
        file_path: Absolute or relative path to the CSV file.

    Returns:
        A JSON string with keys 'transactions' (list of dicts) and 'errors' (list).
    """
    state = GlobalState()
    result: Dict[str, Any] = {"transactions": [], "errors": []}

    if not os.path.isfile(file_path):
        error_msg = f"File not found: {file_path}"
        _logger.log_tool_call("csv_reader_tool", {"file_path": file_path}, error_msg, success=False, error=error_msg)
        result["errors"].append(error_msg)
        return json.dumps(result)

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            headers = set(col.strip().lower() for col in (reader.fieldnames or []))

            missing = REQUIRED_COLUMNS - headers
            if missing:
                error_msg = f"Missing columns: {missing}"
                result["errors"].append(error_msg)
                _logger.log_tool_call("csv_reader_tool", {"file_path": file_path}, error_msg, success=False, error=error_msg)
                return json.dumps(result)

            rows: List[Dict[str, Any]] = []
            for idx, raw_row in enumerate(reader, start=2):
                normalised = {k.strip().lower(): v for k, v in raw_row.items()}
                try:
                    rows.append(_validate_row(normalised, idx))
                except ValueError as ve:
                    result["errors"].append(str(ve))

            result["transactions"] = rows

        state.set("raw_transactions", rows, agent_name="DataIngestionAgent")
        _logger.log_tool_call("csv_reader_tool", {"file_path": file_path}, f"{len(rows)} transactions read")
        _logger.log_state_update("raw_transactions", f"{len(rows)} rows stored")

    except Exception as exc:
        error_msg = f"Unexpected error reading CSV: {exc}"
        result["errors"].append(error_msg)
        _logger.log_tool_call("csv_reader_tool", {"file_path": file_path}, error_msg, success=False, error=error_msg)

    return json.dumps(result, indent=2)
