"""
Tool 3 – Budget Calculator Tool  (Student 3 contribution)

Accepts a spending summary and a monthly income figure, then applies the
50/30/20 budgeting rule to generate actionable budget recommendations.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import crewai_bootstrap  # noqa: F401
from crewai.tools import tool

from observability.logger import AgentLogger
from state.global_state import GlobalState

_logger = AgentLogger("budget_calculator_tool")

NEEDS_CATEGORIES = {"housing", "utilities", "transport", "health", "food", "education"}
WANTS_CATEGORIES = {"entertainment", "shopping"}


def _format_currency(amount: float) -> str:
    """Format numeric values using Sri Lankan rupee notation."""
    return f"Rs. {amount:,.2f}"


def _extract_total(value: Any) -> float:
    """Extract a numeric category total from either dict or scalar values."""
    if isinstance(value, dict):
        raw_total = value.get("total", 0.0)
    else:
        raw_total = value

    try:
        return float(raw_total)
    except (TypeError, ValueError):
        return 0.0


def _classify_spending(summary: Dict[str, Any]) -> Dict[str, float]:
    """Split spending into needs / wants / savings buckets."""
    needs = 0.0
    wants = 0.0
    other = 0.0
    for category, data in summary.items():
        category_name = str(category).strip().lower()
        if category_name.startswith("_"):
            continue
        total = _extract_total(data)
        if category_name in NEEDS_CATEGORIES:
            needs += total
        elif category_name in WANTS_CATEGORIES:
            wants += total
        else:
            other += total
    return {"needs": round(needs, 2), "wants": round(wants, 2), "other": round(other, 2)}


@tool("budget_calculator_tool")
def budget_calculator_tool(spending_summary_json: str, monthly_income: float) -> str:
    """Generate budget recommendations using the 50/30/20 rule.

    Compares actual spending against the recommended allocation:
      - 50 % for Needs (housing, food, transport, utilities, health)
      - 30 % for Wants (entertainment, shopping)
      - 20 % for Savings / debt repayment

    Args:
        spending_summary_json: JSON string of the per-category spending
            summary produced by the expense categorizer tool.
        monthly_income: The user's monthly income in the same currency
            as the transaction amounts.

    Returns:
        A JSON string containing budget targets, actuals, differences,
        and textual recommendations.
    """
    state = GlobalState()
    result: Dict[str, Any] = {"budget": {}, "recommendations": [], "errors": []}

    if monthly_income <= 0:
        error_msg = "monthly_income must be a positive number"
        result["errors"].append(error_msg)
        _logger.log_tool_call("budget_calculator_tool", {"monthly_income": monthly_income}, error_msg, success=False, error=error_msg)
        return json.dumps(result)

    try:
        summary: Dict[str, Any] = json.loads(spending_summary_json)
    except json.JSONDecodeError as exc:
        error_msg = f"Invalid JSON: {exc}"
        result["errors"].append(error_msg)
        _logger.log_tool_call("budget_calculator_tool", {"monthly_income": monthly_income}, error_msg, success=False, error=error_msg)
        return json.dumps(result)

    actuals = _classify_spending(summary)
    total_spent = round(actuals["needs"] + actuals["wants"] + actuals["other"], 2)

    targets = {
        "needs": round(monthly_income * 0.50, 2),
        "wants": round(monthly_income * 0.30, 2),
        "savings": round(monthly_income * 0.20, 2),
    }

    diffs = {
        "needs": round(targets["needs"] - actuals["needs"], 2),
        "wants": round(targets["wants"] - actuals["wants"], 2),
        "savings": round(monthly_income - total_spent, 2),
    }

    recommendations = []
    if diffs["needs"] < 0:
        recommendations.append(
            f"Your essential spending exceeds the 50% target by {_format_currency(abs(diffs['needs']))}. "
            "Consider reviewing housing or food costs."
        )
    else:
        recommendations.append(
            f"Essential spending is {_format_currency(diffs['needs'])} under the 50% target. Well done!"
        )

    if diffs["wants"] < 0:
        recommendations.append(
            f"Discretionary spending exceeds the 30% target by {_format_currency(abs(diffs['wants']))}. "
            "Try cutting back on entertainment or shopping."
        )
    else:
        recommendations.append(
            f"Discretionary spending is {_format_currency(diffs['wants'])} under the 30% target."
        )

    if diffs["savings"] < targets["savings"]:
        recommendations.append(
            f"You are saving {_format_currency(diffs['savings'])} this month. "
            f"Aim to save at least {_format_currency(targets['savings'])} (20% of income)."
        )
    else:
        recommendations.append(
            f"Great savings! You have {_format_currency(diffs['savings'])} left over, exceeding the 20% goal."
        )

    result["budget"] = {
        "monthly_income": monthly_income,
        "total_spent": total_spent,
        "targets": targets,
        "actuals": actuals,
        "differences": diffs,
    }
    result["recommendations"] = recommendations

    state.set("budget_recommendations", result, agent_name="BudgetAdvisorAgent")
    _logger.log_tool_call(
        "budget_calculator_tool",
        {"monthly_income": monthly_income, "total_spent": total_spent},
        f"Generated {len(recommendations)} recommendations",
    )
    _logger.log_state_update("budget_recommendations", json.dumps(result)[:200])

    return json.dumps(result, indent=2)
