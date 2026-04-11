"""
Tool 2 – Expense Categorizer Tool  (Student 2 contribution)

Applies rule-based categorisation to transactions whose category is
'uncategorized' and computes a per-category spending summary.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from crewai.tools import tool

from observability.logger import AgentLogger
from state.global_state import GlobalState

_logger = AgentLogger("expense_categorizer_tool")

KEYWORD_MAP: Dict[str, List[str]] = {
    "food": ["restaurant", "cafe", "grocery", "supermarket", "pizza", "burger", "food", "bakery", "coffee"],
    "transport": ["uber", "lyft", "gas", "fuel", "parking", "bus", "train", "taxi", "transit"],
    "entertainment": ["netflix", "spotify", "cinema", "movie", "game", "concert", "theatre"],
    "utilities": ["electric", "water", "internet", "phone", "mobile", "broadband", "utility"],
    "shopping": ["amazon", "ebay", "mall", "clothing", "shoe", "electronics", "store"],
    "health": ["pharmacy", "doctor", "hospital", "gym", "fitness", "medical", "dental"],
    "housing": ["rent", "mortgage", "insurance", "maintenance", "repair"],
    "education": ["tuition", "book", "course", "university", "school", "udemy"],
}


def _categorize(description: str, current_category: str) -> str:
    """Return an improved category based on keyword matching.

    If the transaction already has a meaningful category it is kept.
    Otherwise the description is scanned against KEYWORD_MAP.
    """
    if current_category and current_category != "uncategorized":
        return current_category
    desc_lower = description.lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "other"


def _build_summary(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a per-category spending summary with totals and counts."""
    summary: Dict[str, Any] = {}
    total = 0.0
    for txn in transactions:
        cat = txn["category"]
        amt = abs(txn["amount"])
        total += amt
        if cat not in summary:
            summary[cat] = {"total": 0.0, "count": 0, "transactions": []}
        summary[cat]["total"] = round(summary[cat]["total"] + amt, 2)
        summary[cat]["count"] += 1
        summary[cat]["transactions"].append(txn["description"])
    summary["_overall"] = {"total": round(total, 2), "transaction_count": len(transactions)}
    return summary


@tool("expense_categorizer_tool")
def expense_categorizer_tool(transactions_json: str) -> str:
    """Categorize financial transactions and produce a spending summary.

    Transactions with category 'uncategorized' are re-classified using
    keyword matching.  A per-category summary with totals and counts is
    returned.

    Args:
        transactions_json: A JSON string containing a list of transaction
            dicts, each with keys: date, description, amount, category.

    Returns:
        A JSON string with 'categorized_transactions' and 'spending_summary'.
    """
    state = GlobalState()
    result: Dict[str, Any] = {"categorized_transactions": [], "spending_summary": {}, "errors": []}

    try:
        transactions: List[Dict[str, Any]] = json.loads(transactions_json)
    except json.JSONDecodeError as exc:
        error_msg = f"Invalid JSON input: {exc}"
        result["errors"].append(error_msg)
        _logger.log_tool_call("expense_categorizer_tool", {"input_length": len(transactions_json)}, error_msg, success=False, error=error_msg)
        return json.dumps(result)

    categorized: List[Dict[str, Any]] = []
    for txn in transactions:
        new_cat = _categorize(txn.get("description", ""), txn.get("category", "uncategorized"))
        categorized.append({**txn, "category": new_cat})

    summary = _build_summary(categorized)

    result["categorized_transactions"] = categorized
    result["spending_summary"] = summary

    state.set("categorized_transactions", categorized, agent_name="ExpenseAnalyzerAgent")
    state.set("spending_summary", summary, agent_name="ExpenseAnalyzerAgent")

    _logger.log_tool_call(
        "expense_categorizer_tool",
        {"transaction_count": len(transactions)},
        f"Categorized {len(categorized)} txns into {len(summary) - 1} categories",
    )
    _logger.log_state_update("categorized_transactions", f"{len(categorized)} categorized")
    _logger.log_state_update("spending_summary", json.dumps(summary)[:200])

    return json.dumps(result, indent=2)
